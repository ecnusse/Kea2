import itertools
import requests

from time import sleep
from dataclasses import asdict
from pathlib import Path

from retry import retry
from retry.api import retry_call
from uiautomator2.core import HTTPResponse, _http_request
from packaging.version import parse as parse_version

from .utils import getLogger, getProjectRoot
from .adbUtils import ADBDevice, ADBStreamShell_V2


from typing import IO, TYPE_CHECKING, Dict
if TYPE_CHECKING:
    from .keaUtils import Options, PropertyExecutionInfo


logger = getLogger(__name__)


class FastbotManager:
    def __init__(self, options: "Options", log_file: str):
        self.options:"Options" = options
        self.log_file: str = log_file
        self.port = None
        self.thread = None
        self._device_output_dir = None
        ADBDevice.setDevice(options.serial, options.transport_id)
        self.dev = ADBDevice()
        self.android_release = parse_version(self.dev.getprop("ro.build.version.release"))
        self.executed_prop = False

    def _activateFastbot(self) -> ADBStreamShell_V2:
        """
        activate fastbot.
        :params: options: the running setting for fastbot
        :params: port: the listening port for script driver
        :return: the fastbot daemon thread
        """

        self._push_libs()
        t = self._startFastbotService()
        logger.info("Running Fastbot...")
        return t

    def check_alive(self):
        """
        check if the script driver and proxy server are alive.
        """
        def _check_alive_request():
            _http_request(dev=self.dev, device_port=8090, method="GET", path="/ping")

        try:
            logger.info("Connecting to fastbot server...")
            retry_call(_check_alive_request, tries=10, delay=2, logger=logger)
            logger.info("Connected to fastbot server.")
        except requests.ConnectionError:
            raise RuntimeError("Failed to connect fastbot")

    def request(self, method: str, path: str, data: Dict=None, timeout: int=10) -> HTTPResponse:
        return _http_request(self.dev, 8090, method, path, data, timeout)

    @retry(Exception, tries=2, delay=2)
    def init(self, options: "Options", stamp):
        post_data = {
            "takeScreenshots": options.take_screenshots,
            "preFailureScreenshots": options.pre_failure_screenshots,
            "postFailureScreenshots": options.post_failure_screenshots,
            "logStamp": stamp,
            "deviceOutputRoot": options.device_output_root,
        }
        r = _http_request(
            self.dev,
            device_port=8090,
            method="POST",
            path="/init",
            data=post_data
        )
        print(f"[INFO] Init fastbot: {post_data}", flush=True)
        import re
        self._device_output_dir = re.match(r"outputDir:(.+)", r.text).group(1)
        print(f"[INFO] Fastbot initiated. outputDir: {r.text}", flush=True)
    
    @retry(Exception, tries=2, delay=2)
    def stepMonkey(self, monkeyStepInfo):
        r = self.request(
            method="POST",
            path="/stepMonkey",
            data=monkeyStepInfo
        )
        return r.json()["result"]

    @retry(Exception, tries=2, delay=2)
    def stopMonkey(self):
        """
        send a stop monkey request to the server.
        """
        r = self.request(
            method="GET",
            path="/stopMonkey",
        )

        print(f"[Server INFO] {r.text}", flush=True)
    
    @retry(Exception, tries=2, delay=2)
    def logScript(self, execution_info: "PropertyExecutionInfo"):
        r = self.request(
            method="POST",
            path="/logScript",
            data={
                "propName": execution_info.propName,
                "startStepsCount": execution_info.startStepsCount,
                "state": execution_info.state,
            }
        )
        res = r.text
        if res != "OK":
            print(f"[ERROR] Error when logging script: {execution_info}", flush=True)
    
    @retry(Exception, tries=2, delay=2)
    def dumpHierarchy(self):
        sleep(self.options.throttle / 1000)
        r = self.request(
            method="GET",
            path="/dumpHierarchy",
        )
        return r.json()['result']
    
    @retry(Exception, tries=2, delay=2)
    def sendInfo(self, info: str):
        r = self.request(
            method="POST",
            path="/sendInfo",
            data=info
        )

    @property
    def device_output_dir(self):
        return self._device_output_dir
    
    def _push_libs(self):
        logger.info("Pushing Fastbot libraries to device...")
        cur_dir = Path(__file__).parent
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/monkeyq.jar"),
            "/sdcard/monkeyq.jar"
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot-thirdpart.jar"),
            "/sdcard/fastbot-thirdpart.jar",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/kea2-thirdpart.jar"),
            "/sdcard/kea2-thirdpart.jar",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/framework.jar"),
            "/sdcard/framework.jar",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot_libs/arm64-v8a/libfastbot_native.so"),
            "/data/local/tmp/arm64-v8a/libfastbot_native.so",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot_libs/armeabi-v7a/libfastbot_native.so"),
            "/data/local/tmp/armeabi-v7a/libfastbot_native.so",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot_libs/x86/libfastbot_native.so"),
            "/data/local/tmp/x86/libfastbot_native.so",
        )
        self.dev.sync.push(
            Path.joinpath(cur_dir, "assets/fastbot_libs/x86_64/libfastbot_native.so"),
            "/data/local/tmp/x86_64/libfastbot_native.so",
        )

        cwd = getProjectRoot()
        whitelist = self.options.act_whitelist_file
        blacklist = self.options.act_blacklist_file
        if bool(whitelist) ^ bool(blacklist):
            if whitelist:
                file_to_push = cwd / 'configs' / 'awl.strings'
                remote_path = whitelist
            else:
                file_to_push = cwd / 'configs' / 'abl.strings'
                remote_path = blacklist

            self.dev.sync.push(
                file_to_push,
                remote_path
            )

    def _startFastbotService(self) -> ADBStreamShell_V2:
        shell_command = [
            "CLASSPATH="
            "/sdcard/monkeyq.jar:"
            "/sdcard/framework.jar:"
            "/sdcard/fastbot-thirdpart.jar:"
            "/sdcard/kea2-thirdpart.jar",
            "exec", "app_process",
            "/system/bin", "com.android.commands.monkey.Monkey",
            "--agent-u2" if self.options.agent == "u2" else "--agent",
            "reuseq",
            "--running-minutes", f"{self.options.running_mins}",
            "--throttle", f"{self.options.throttle}",
            "--bugreport",
            "--output-directory", f"{self.options.device_output_root}/output_{self.options.log_stamp}",
        ]

        pkgs = itertools.chain.from_iterable(["-p", pkg] for pkg in self.options.packageNames)
        shell_command.extend(pkgs)

        if self.options.profile_period:
            shell_command += ["--profile-period", f"{self.options.profile_period}"]

        whitelist = self.options.act_whitelist_file
        blacklist = self.options.act_blacklist_file
        if bool(whitelist) ^ bool(blacklist):
            if whitelist:
                shell_command += ["--act-whitelist-file", f"{whitelist}"]
            else:
                shell_command += ["--act-blacklist-file", f"{blacklist}"]

        shell_command += ["-v", "-v", "-v"]

        if self.options.extra_args:
            shell_command += self.options.extra_args

        full_cmd = ["adb"] + (["-s", self.options.serial] if self.options.serial else []) + ["shell"] + shell_command


        outfile = open(self.log_file, "w", encoding="utf-8", buffering=1)

        logger.info("Options info: {}".format(asdict(self.options)))
        logger.info("Launching fastbot with shell command:\n{}".format(" ".join(full_cmd)))
        logger.info("Fastbot log will be saved to {}".format(outfile.name))

        t = self.dev.stream_shell(shell_command, stdout=outfile, stderr=outfile)
        return t

    def close_on_exit(self, proc: ADBStreamShell_V2, f: IO):
        self.return_code = proc.wait()
        f.close()
        if self.return_code != 0:
            raise RuntimeError(f"Fastbot Error: Terminated with [code {self.return_code}] See {self.log_file} for details.")

    def get_return_code(self):
        if self.thread.is_running():
            logger.info("Waiting for Fastbot to exit.")
            return self.thread.wait()
        return self.thread.poll() if self.android_release >= parse_version("7.0") else 0

    def start(self):
        # kill the fastbot process if runing.
        self.dev.kill_proc("com.android.commands.monkey")
        self.thread = self._activateFastbot()

    def join(self):
        self.thread.join()




