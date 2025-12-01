import sys
import subprocess
import threading

from typing import IO, Generator, Optional, List, Union, List, Optional, Set, Tuple

from adbutils import AdbDevice, adb

from .utils import getLogger

logger = getLogger(__name__)


class ADBDevice(AdbDevice):
    _instance = None
    serial: Optional[str] = None
    transport_id: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def setDevice(cls, serial: Optional[str] = None, transport_id: Optional[str] = None):
        ADBDevice.serial = serial or ADBDevice.serial
        ADBDevice.transport_id = transport_id or ADBDevice.transport_id
    
    def __init__(self) -> AdbDevice:
        """
        Initializes the ADBDevice instance.
        
        Parameters:
            device (str, optional): The device serial number. If None, it is resolved automatically when only one device is connected.
            transport_id (str, optional): The transport ID for the device.
        """
        if not ADBDevice.serial and not ADBDevice.transport_id:
            devices = [d.serial for d in adb.list() if d.state == "device"]
            if len(devices) > 1:
                raise RuntimeError("Multiple devices connected. Please specify a device")
            if len(devices) == 0:
                raise RuntimeError("No device connected.")
            ADBDevice.serial = devices[0]
        super().__init__(client=adb, serial=ADBDevice.serial, transport_id=ADBDevice.transport_id)

    @property
    def stream_shell(self) -> "StreamShell":
        if "shell_v2" in self.get_features():
            return ADBStreamShell_V2(session=self)
        logger.warning("Using ADBStreamShell_V1. All output will be printed to stdout.")
        return ADBStreamShell_V1(session=self)

    def kill_proc(self, proc_name):
        r = self.shell(f"ps -ef")
        pids = [l for l in r.splitlines() if proc_name in l]
        if pids:
            logger.info(f"{proc_name} running, trying to kill it.")
            pid = pids[0].split()[1]
            self.shell(f"kill {pid}")


class StreamShell:
    def __init__(self, session: "ADBDevice"):
        self.dev: ADBDevice = session
        self._thread: threading.Thread = None
        self._exit_code = 255
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self._finished = False

    def __call__(self, cmdargs: Union[List[str], str], stdout: IO = None, 
                 stderr: IO = None, timeout: Union[float, None] = None) -> "StreamShell":
        pass

    def _write_stdout(self, data: bytes, decode=True):
        text = data.decode('utf-8', errors='ignore') if decode else data
        self.stdout.write(text)
        self.stdout.flush()

    def _write_stderr(self, data: bytes, decode=True):
        text = data.decode('utf-8', errors='ignore') if decode else data
        self.stderr.write(text)
        self.stderr.flush()
    
    def wait(self):
        """ Wait for the shell command to finish and return the exit code.
        Returns:
            int: The exit code of the shell command.
        """
        if self._thread:
            self._thread.join()
        return self._exit_code

    def is_running(self) -> bool:
        """ Check if the shell command is still running.
        Returns:
            bool: True if the command is still running, False otherwise.
        """
        return not self._finished and self._thread and self._thread.is_alive()
    
    def poll(self):
        """
        Check if the shell command is still running.
        Returns:
            int: The exit code if the command has finished, None otherwise.
        """
        if self._thread and self._thread.is_alive():
            return None
        return self._exit_code
    
    def join(self):
        if self._thread and self._thread.is_alive():
            self._thread.join()


class ADBStreamShell_V1(StreamShell):

    def __call__(
        self, cmdargs: Union[List[str], str], stdout: IO = None, 
        stderr: IO = None, timeout: Union[float, None] = None
    ) -> "StreamShell":
        return self.shell_v1(cmdargs, stdout, stderr, timeout)
    
    def shell_v1(
        self, cmdargs: Union[List[str], str],
        stdout: IO = None, stderr: IO = None,
        timeout: Union[float, None] = None
    ):
        self._finished = False
        self.stdout: IO = stdout if stdout else sys.stdout
        self.stderr: IO = stdout if stderr else sys.stdout

        cmd = " ".join(cmdargs) if isinstance(cmdargs, list) else cmdargs
        self._generator = self._shell_v1(cmd, timeout)
        self._thread = threading.Thread(target=self._process_output, daemon=True)
        self._thread.start()
        return self
    
    
    def _shell_v1(self, cmdargs: str, timeout: Optional[float] = None) -> Generator[Tuple[str, str], None, None]:
        if not isinstance(cmdargs, str):
            raise RuntimeError("_shell_v1 args must be str")
        MAGIC = "X4EXIT:"
        newcmd = cmdargs + f"; echo {MAGIC}$?"
        with self.dev.open_transport(timeout=timeout) as c:
            c.send_command(f"shell:{newcmd}")
            c.check_okay()
            with c.conn.makefile("r", encoding="utf-8") as f:
                for line in f:
                    rindex = line.rfind(MAGIC)
                    if rindex == -1:
                        yield "output", line
                        continue

                    yield "exit", line[rindex + len(MAGIC):]
                    return

    def _process_output(self):
        try:
            for msg_type, data in self._generator:

                if msg_type == 'output':
                    self._write_stdout(data, decode=False)
                elif msg_type == 'exit':
                    # TODO : handle exit code properly
                    # self._exit_code = int(data.strip())
                    self._exit_code = 0
                    break

        except Exception as e:
            print(f"ADBStreamShell execution error: {e}")
            self._exit_code = -1


class ADBStreamShell_V2(StreamShell):
    def __init__(self, session: "ADBDevice"):
        self.dev: ADBDevice = session
        self._thread = None
        self._exit_code = 255

    def __call__(
        self, cmdargs: Union[List[str], str], stdout: IO = None, 
        stderr: IO = None, timeout: Union[float, None] = None
    ) -> "StreamShell":
        return self.shell_v2(cmdargs, stdout, stderr, timeout)
    
    def shell_v2(
        self, cmdargs: Union[List[str], str],
        stdout: IO = None, stderr: IO = None,
        timeout: Union[float, None] = None
    ):
        """ Start a shell command on the device and stream its output. 
        Args:
            cmdargs (Union[List[str], str]): The command to execute, either as a list of arguments or a single string.
            stdout (IO, optional): The output stream for standard output. Defaults to sys.stdout.
            stderr (IO, optional): The output stream for standard error. Defaults to sys.stderr.
            timeout (Union[float, None], optional): Timeout for the command execution. Defaults to None.
        Returns:
            ADBStreamShell: An instance of ADBStreamShell that can be used to interact with the shell command.
        """
        self._finished = False
        self.stdout: IO = stdout if stdout else sys.stdout
        self.stderr: IO = stderr if stderr else sys.stderr

        cmd = " ".join(cmdargs) if isinstance(cmdargs, list) else cmdargs
        self._generator = self._shell_v2(cmd, timeout)
        self._thread = threading.Thread(target=self._process_output, daemon=True)
        self._thread.start()
        return self

    def _process_output(self):
        try:
            for msg_type, data in self._generator:

                if msg_type == 'stdout':
                    self._write_stdout(data)
                elif msg_type == 'stderr':
                    self._write_stderr(data)
                elif msg_type == 'exit':
                    self._exit_code = data
                    break

        except Exception as e:
            print(f"ADBStreamShell execution error: {e}")
            self._exit_code = -1

    def _shell_v2(self, cmd, timeout) -> Generator[Tuple[str, bytes], None, None]:
        with self.dev.open_transport(timeout=timeout) as c:
            c.send_command(f"shell,v2:{cmd}")
            c.check_okay()

            while True:
                header = c.read_exact(5)
                msg_id = header[0]
                length = int.from_bytes(header[1:5], byteorder="little")

                if length == 0:
                    continue

                data = c.read_exact(length)

                if msg_id == 1:
                    yield ('stdout', data)
                elif msg_id == 2:
                    yield ('stderr', data)
                elif msg_id == 3:
                    yield ('exit', data[0])
                    break


def run_adb_command(cmd: List[str], timeout=10):
    """
    Runs an adb command and returns its output.
    
    Parameters:
        cmd (list): List of adb command arguments, e.g., ["devices"].
        timeout (int): Timeout in seconds.
        
    Returns:
        str: The standard output from the command. If an error occurs, returns None.
    """
    full_cmd = ["adb"] + cmd
    logger.debug(f"{' '.join(full_cmd)}")
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            print(f"Command failed: {' '.join(full_cmd)}\nError: {result.stderr}", flush=True)
        return "\n".join([
            result.stdout.strip(),
            result.stderr.strip()
        ])
    except subprocess.TimeoutExpired:
        print(f"Command timed out: {' '.join(full_cmd)}", flush=True)
        return None

def get_devices():
    """
    Retrieves the list of connected Android devices.
    
    Returns:
        list: A list of device serial numbers.
    """
    output = run_adb_command(["devices", "-l"])
    devices = []
    if output:
        lines = output.splitlines()
        # The first line is usually "List of devices attached". The following lines list individual devices.
        for line in lines[1:]:
            if line.strip():
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append(parts[0])
    return devices

def ensure_device(func):
    """
    A decorator that resolves the device parameter automatically if it's not provided.
    
    If 'device' is None or not present in the keyword arguments and only one device is connected,
    that device will be automatically used. If no devices are connected or multiple devices are
    connected, it raises a RuntimeError.
    """
    def wrapper(*args, **kwargs):
        devices = get_devices()
        if kwargs.get("device") is None and kwargs.get("transport_id") is None:
            if not devices:
                raise RuntimeError("No connected devices.")
            if len(devices) > 1:
                raise RuntimeError("Multiple connected devices detected. Please specify a device.")
            kwargs["device"] = devices[0]
        if kwargs.get("device"):
            output = run_adb_command(["-s", kwargs["device"], "get-state"])
        elif kwargs.get("transport_id"):
            output = run_adb_command(["-t", kwargs["transport_id"], "get-state"])
        if output.strip() != "device":
            raise RuntimeError(f"[ERROR] {kwargs['device']} not connected. Please check.\n{output}")
        return func(*args, **kwargs)
    return wrapper

@ensure_device
def adb_shell(cmd: List[str], device:Optional[str]=None, transport_id:Optional[str]=None):
    """
    run adb shell commands

    Parameters:
        cmd (List[str])
        device (str, optional): The device serial number. If None, it's resolved automatically when only one device is connected.
    """
    if device:
        return run_adb_command(["-s", device, "shell"] + cmd)
    if transport_id:
        return run_adb_command(["-t", transport_id, "shell"] + cmd)
        


@ensure_device
def install_app(apk_path: str, device: Optional[str]=None, transport_id:Optional[str]=None):
    """
    Installs an APK application on the specified device.
    
    Parameters:
        apk_path (str): The local path to the APK file.
        device (str, optional): The device serial number. If None, it's resolved automatically when only one device is connected.
        
    Returns:
        str: The output from the install command.
    """
    if device:
        return run_adb_command(["-s", device, "install", apk_path])
    if transport_id:
        return run_adb_command(["-t", transport_id, "install", apk_path])


@ensure_device
def uninstall_app(package_name: str, device: Optional[str] = None, transport_id:Optional[str]=None):
    """
    Uninstalls an app from the specified device.
    
    Parameters:
        package_name (str): The package name of the app.
        device (str, optional): The device serial number. If None, it's resolved automatically when only one device is connected.
        
    Returns:
        str: The output from the uninstall command.
    """
    if device:
        return run_adb_command(["-s", device, "uninstall", package_name])
    if transport_id:
        return run_adb_command(["-t", transport_id, "uninstall", package_name])

@ensure_device
def push_file(local_path: str, remote_path: str, device: Optional[str] = None, transport_id:Optional[str]=None):
    """
    Pushes a file to the specified device.
    
    Parameters:
        local_path (str): The local file path.
        remote_path (str): The destination path on the device.
        device (str, optional): The device serial number. If None, it's resolved automatically when only one device is connected.
        
    Returns:
        str: The output from the push command.
    """
    local_path = str(local_path)
    remote_path = str(remote_path)
    if device:
        return run_adb_command(["-s", device, "push", local_path, remote_path])
    if transport_id:
        return run_adb_command(["-t", transport_id, "push", local_path, remote_path])


@ensure_device
def pull_file(remote_path: str, local_path: str, device: Optional[str] = None, transport_id:Optional[str]=None):
    """
    Pulls a file from the device to a local path.
    
    Parameters:
        remote_path (str): The file path on the device.
        local_path (str): The local destination path.
        device (str, optional): The device serial number. If None, it's resolved automatically when only one device is connected.
        
    Returns:
        str: The output from the pull command.
    """
    if device:
        return run_adb_command(["-s", device, "pull", remote_path, local_path])
    if transport_id:
        return run_adb_command(["-t", transport_id, "pull", remote_path, local_path])

# Forward-related functions


@ensure_device
def list_forwards(device: Optional[str] = None):
    """
    Lists current port forwarding rules on the specified device.
    
    Parameters:
        device (str, optional): The device serial number. If None, it is resolved automatically.
        
    Returns:
        list: A list of forwarding rules. Each rule is a dictionary with keys: device, local, remote.
    """
    output = run_adb_command(["-s", device, "forward", "--list"])
    forwards = []
    if output:
        lines = output.splitlines()
        for line in lines:
            parts = line.split()
            if len(parts) == 3:
                # Each line is expected to be: <device> <local> <remote>
                rule = {"device": parts[0], "local": parts[1], "remote": parts[2]}
                if rule["device"] == device:
                    forwards.append(rule)
            else:
                forwards.append(line)
    return forwards


@ensure_device
def create_forward(local_spec: str, remote_spec: str, device: Optional[str] = None):
    """
    Creates a port forwarding rule on the specified device.
    
    Parameters:
        local_spec (str): The local forward specification (e.g., "tcp:8000").
        remote_spec (str): The remote target specification (e.g., "tcp:9000").
        device (str, optional): The device serial number. If None, it is resolved automatically.
        
    Returns:
        str: The output from the forward creation command.
    """
    return run_adb_command(["-s", device, "forward", local_spec, remote_spec])


@ensure_device
def remove_forward(local_spec, device: Optional[str] = None):
    """
    Removes a specific port forwarding rule on the specified device.
    
    Parameters:
        local_spec (str): The local forward specification to remove (e.g., "tcp:8000").
        device (str, optional): The device serial number. If None, it is resolved automatically.
        
    Returns:
        str: The output from the forward removal command.
    """
    return run_adb_command(["-s", device, "forward", "--remove", local_spec])


@ensure_device
def remove_all_forwards(device: Optional[str] = None):
    """
    Removes all port forwarding rules on the specified device.
    
    Parameters:
        device (str, optional): The device serial number. If None, it is resolved automatically.
        
    Returns:
        str: The output from the command to remove all forwards.
    """
    return run_adb_command(["-s", device, "forward", "--remove-all"])


@ensure_device
def get_packages(device: Optional[str]=None, transport_id: Optional[str]=None) -> Set[str]:
    """
    Retrieves packages that match the specified regular expression pattern.
    
    Parameters:
        pattern (str): Regular expression pattern to match package names.
        device (str, optional): The device serial number. If None, it is resolved automatically.
        
    Returns:
        set: A set of package names that match the pattern.
    """
    import re
    
    if device:
        cmd = ["-s", device, "shell", "pm", "list", "packages"]
    if transport_id:
        cmd = ["-t", transport_id, "shell", "pm", "list", "packages"]
    output = run_adb_command(cmd)
    
    packages = set()
    if output:
        compiled_pattern = re.compile(r"package:(.+)\n")
        matches = compiled_pattern.findall(output)
        for match in matches:
            if match:
                packages.add(match)
    
    return packages


if __name__ == '__main__':
    # For testing: print the list of currently connected devices.
    adb_shell(["ls", "vendor"], transport_id="2")
    devices = get_devices()
    if devices:
        print("Connected devices:", flush=True)
        for dev in devices:
            print(f" - {dev}", flush=True)
    else:
        print("No devices connected.", flush=True)

    # Example usage of forward-related functionalities:
    try:
        # List current forwards
        forwards = list_forwards()
        print("Current forward rules:", flush=True)
        for rule in forwards:
            print(rule, flush=True)
            
        # Create a forward rule (example: forward local tcp 8000 to remote tcp 9000)
        output = create_forward("tcp:8000", "tcp:9000")
        print("Create forward output:", output, flush=True)
        
        # List forwards again
        forwards = list_forwards()
        print("Forward rules after creation:", flush=True)
        for rule in forwards:
            print(rule, flush=True)
        
        # Remove the forward rule
        output = remove_forward("tcp:8000")
        print("Remove forward output:", output, flush=True)
        
        # Remove all forwards (if needed)
        # output = remove_all_forwards()
        # print("Remove all forwards output:", output)
        
    except RuntimeError as e:
        print("Error:", e, flush=True)
