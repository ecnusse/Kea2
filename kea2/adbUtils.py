import sys
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
        self.stderr: IO = stderr if stderr else sys.stderr

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
