import asyncio
import sys
import pathlib
import aiofiles
from kea2.utils import getProjectRoot
import fnmatch
import keyword


def run_option_args(params):
    """Translate optional run settings without overriding CLI defaults."""
    args = []
    for name, flag, minimum in (
        ("max_step", "--max-step", 1),
        ("throttle_ms", "--throttle", 0),
        ("profile_period", "--profile-period", 1),
        ("restart_app_period", "--restart-app-period", 0),
    ):
        value = params.get(name)
        if value is not None:
            if type(value) is not int or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
            args.extend([flag, str(value)])
    screenshots = params.get("take_screenshots")
    if screenshots is not None and type(screenshots) is not bool:
        raise ValueError("take_screenshots must be a boolean")
    if screenshots:
        args.append("--take-screenshots")
    if params.get("act_whitelist_file") is not None and params.get("act_blacklist_file") is not None:
        raise ValueError("act_whitelist_file and act_blacklist_file are mutually exclusive")
    for name in ("act_whitelist_file", "act_blacklist_file"):
        value = params.get(name)
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty device path")
            args.append(f"--{name.replace('_', '-')}={value}")
    return args


def property_args(property_path=None, property_pattern="test*.py", driver_name="d"):
    """Validate paths without importing user scripts; return CLI discovery args."""
    if property_path is None:
        return []
    if not property_path.strip():
        raise ValueError("property_path must not be empty")
    if not driver_name.isidentifier() or keyword.iskeyword(driver_name):
        raise ValueError("driver_name must be a valid Python attribute name")
    path = pathlib.Path(property_path).expanduser().resolve()
    if path.is_file():
        if path.suffix != ".py" or not path.stem.isidentifier():
            raise ValueError("property_path must be an importable .py file")
        directory, pattern = path.parent, path.name
    elif path.is_dir():
        if not property_pattern or any(c in property_pattern for c in "/\\"):
            raise ValueError("property_pattern must be a filename glob, not a path")
        directory, pattern = path, property_pattern
        if not any(p.is_file() and p.suffix == ".py" and
                   fnmatch.fnmatchcase(p.name, pattern) for p in path.rglob("*.py")):
            raise ValueError("No Python files match property_pattern")
    else:
        raise ValueError(f"property_path does not exist: {path}")
    return ["--driver-name", driver_name,
            "propertytest", "discover", "-s", str(directory), "-p", pattern]


async def _stream_to_file(stream: asyncio.StreamReader, log_file: pathlib.Path) -> None:
    async with aiofiles.open(log_file, "ab") as fp:
        while True:
            chunk = await stream.readline()
            if not chunk:
                break
            await fp.write(chunk)
            await fp.flush()


async def launch_kea2_subprocess(params, stamp):
    option_args = run_option_args(params)
    discovery_args = property_args(params.get("property_path"),
                                   params.get("property_pattern", "test*.py"),
                                   params.get("driver_name", "d"))
    output_parent = pathlib.Path(params.get("output_dir") or "output").expanduser().resolve()
    output_dir = output_parent / f"res_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fastbot owns fastbot_<stamp>.log and LogWatcher tails it. Appending
    # subprocess output there races with Fastbot's writes and can invalidate
    # the reader's UTF-8 offsets. Keep the two writers on separate files.
    log_file = output_dir / f"kea2_{stamp}.log"
    result_file = output_dir / f"result_{stamp}.json"

    cmd = [sys.executable, "-m", "kea2.cli", "run"]
    serial = params.get("serial")
    if serial:
        cmd.extend(["-s", str(serial)])
    transport_id = params.get("transport_id")
    if transport_id:
        cmd.extend(["-t", str(transport_id)])

    packages = params.get("packages") or []
    if not packages:
        raise ValueError("packages is required and must be non-empty")
    cmd.extend(["-p", *[str(p) for p in packages]])

    running_minutes = params.get("running_minutes")
    if running_minutes is not None:
        cmd.extend(["--running-minutes", str(running_minutes)])

    cmd.extend(["--output-dir", str(output_parent)])
    cmd.extend(["--log-stamp", str(stamp)])
    cmd.extend(option_args)
    cmd.extend(discovery_args)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(getProjectRoot() or pathlib.Path.cwd()),
    )
    asyncio.create_task(_stream_to_file(proc.stdout, log_file))
    return proc, output_dir, log_file, result_file


async def cancel_proc(proc, timeout=5.0):
    if proc.returncode is not None:
        return proc.returncode
    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
    return proc.returncode
