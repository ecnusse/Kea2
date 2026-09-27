import asyncio
import sys
import pathlib
import aiofiles
from kea2.utils import getProjectRoot


async def _stream_to_file(stream: asyncio.StreamReader, log_file: pathlib.Path) -> None:
    async with aiofiles.open(log_file, "ab") as fp:
        while True:
            chunk = await stream.readline()
            if not chunk:
                break
            await fp.write(chunk)
            await fp.flush()


async def launch_kea2_subprocess(params, stamp):
    output_parent = pathlib.Path(params.get("output_dir") or "output").expanduser().resolve()
    output_dir = output_parent / f"res_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    log_file = output_dir / f"fastbot_{stamp}.log"
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
