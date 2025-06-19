from dataclasses import asdict
import subprocess
import threading
import requests
from time import sleep
from .adbUtils import push_file
from pathlib import Path
from .utils import getLogger

from typing import IO, TYPE_CHECKING
if TYPE_CHECKING:
    from .keaUtils import Options


logger = getLogger(__name__)


class FastbotManager:
    def __init__(self, options: "Options", log_file: str):
        self.options:"Options" = options
        self.log_file: str = log_file
        self.port = None
        self.thread = None


    def _activateFastbot(self) -> threading.Thread:
        """
        activate fastbot.
        :params: options: the running setting for fastbot
        :params: port: the listening port for script driver
        :return: the fastbot daemon thread
        """
        options = self.options
        cur_dir = Path(__file__).parent
        push_file(
            Path.joinpath(cur_dir, "assets/monkeyq.jar"),
            "/sdcard/monkeyq.jar",
            device=options.serial
        )
        push_file(
            Path.joinpath(cur_dir, "assets/fastbot-thirdpart.jar"),
            "/sdcard/fastbot-thirdpart.jar",
            device=options.serial,
        )
        push_file(
            Path.joinpath(cur_dir, "assets/kea2-thirdpart.jar"),
            "/sdcard/kea2-thirdpart.jar",
            device=options.serial,
        )
        push_file(
            Path.joinpath(cur_dir, "assets/framework.jar"), 
            "/sdcard/framework.jar",
            device=options.serial
        )
        push_file(
            Path.joinpath(cur_dir, "assets/fastbot_libs/arm64-v8a"),
            "/data/local/tmp",
            device=options.serial
        )
        push_file(
            Path.joinpath(cur_dir, "assets/fastbot_libs/armeabi-v7a"),
            "/data/local/tmp",
            device=options.serial
        )
        push_file(
            Path.joinpath(cur_dir, "assets/fastbot_libs/x86"),
            "/data/local/tmp",
            device=options.serial
        )
        push_file(
            Path.joinpath(cur_dir, "assets/fastbot_libs/x86_64"),
            "/data/local/tmp",
            device=options.serial
        )

        whitelist = options.act_whitelist_file
        blacklist = options.act_blacklist_file
        if bool(whitelist) ^ bool(blacklist):
            if whitelist:
                file_to_push = cur_dir.parent / 'configs' / 'awl.strings'
                remote_path = whitelist
            else:
                file_to_push = cur_dir.parent / 'configs' / 'abl.strings'
                remote_path = blacklist

            push_file(
                file_to_push,
                remote_path,
                device=options.serial,
            )

        t = self._startFastbotService()
        logger.info("Running Fastbot...")

        return t


    def check_alive(self, port):
        """
        check if the script driver and proxy server are alive.
        """
        for _ in range(10):
            sleep(2)
            try:
                requests.get(f"http://localhost:{port}/ping")
                return
            except requests.ConnectionError:
                logger.info("waiting for connection.")
                pass
        raise RuntimeError("Failed to connect fastbot")


    def _startFastbotService(self) -> threading.Thread:
        shell_command = [
            "CLASSPATH="
            "/sdcard/monkeyq.jar:"
            "/sdcard/framework.jar:"
            "/sdcard/fastbot-thirdpart.jar:"
            "/sdcard/kea2-thirdpart.jar",
            
            "exec", "app_process",
            "/system/bin", "com.android.commands.monkey.Monkey",
            "-p", *self.options.packageNames,
            "--agent-u2" if self.options.agent == "u2" else "--agent",
            "reuseq",
            "--running-minutes", f"{self.options.running_mins}",
            "--throttle", f"{self.options.throttle}",
            "--bugreport",
        ]

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

        full_cmd = ["adb"] + (["-s", self.options.serial] if self.options.serial else []) + ["shell"] + shell_command

        outfile = open(self.log_file, "w", encoding="utf-8", buffering=1)

        logger.info("Options info: {}".format(asdict(self.options)))
        logger.info("Launching fastbot with shell command:\n{}".format(" ".join(full_cmd)))
        logger.info("Fastbot log will be saved to {}".format(outfile.name))

        # process handler
        proc = subprocess.Popen(full_cmd, stdout=outfile, stderr=outfile)
        t = threading.Thread(target=self.close_on_exit, args=(proc, outfile), daemon=True)
        t.start()

        return t

    def close_on_exit(self, proc: subprocess.Popen, f: IO):
        self.return_code = proc.wait()
        f.close()
        if self.return_code != 0:
            raise RuntimeError(f"Fastbot Error: Terminated with [code {self.return_code}] See {self.log_file} for details.")

    def get_return_code(self):
        if self.thread:
            logger.info("Waiting for Fastbot to exit.")
            self.thread.join()
        return self.return_code

    def start(self):
        self.thread = self._activateFastbot()

    def join(self):
        if self.thread:
            self.thread.join()



