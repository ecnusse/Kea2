import uuid
import json
import asyncio
import os
import signal
import shutil
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from kea2.mcp import task_store, runner
from adbutils import adb
from kea2.utils import getProjectRoot
from kea2.version_manager import get_cur_version
from datetime import datetime


mcp = MCPServer("kea2")
_procs: dict[str, asyncio.subprocess.Process] = {}


def _safe_model_name(device) -> str:
    try:
        d = adb.device(serial=device.serial)
        return d.shell("getprop ro.product.model").strip()
    except Exception:
        return ""


async def _wait_and_finalize(task_id: str, proc: asyncio.subprocess.Process):
    rc = await proc.wait()
    status = "finished" if rc == 0 else "failed"
    task_store.update_task_status(task_id, status, exit_code=rc)
    _procs.pop(task_id, None)


def _precheck_run_test(serial: str, packages: list[str]) -> str | None:
    """返回 None 表示通过，否则返回错误信息。"""
    if not os.path.isdir("configs"):
        return "configs/ 目录不存在，请先调用 kea2_init"
    try:
        serials = [d.serial for d in adb.list()]
        if serial not in serials:
            return f"设备 {serial} 未连接"
    except Exception as e:
        return f"设备检查失败: {e}"
    return None


@mcp.tool()
async def kea2_init(force: bool = False) -> dict:
    """在当前工作目录初始化 Kea2 项目，生成 configs/ 目录和模板文件。
    如果 configs/ 已存在，force=False 时返回错误；force=True 时覆盖。

    参数：force(布尔，是否覆盖已有配置，默认 False)
    返回：{initialized: bool, configs_dir: str, files: [str]}"""
    cwd = Path(os.getcwd())
    configs_dir = cwd / "configs"
    if configs_dir.exists():
        if not force:
            return {
                "initialized": False,
                "error": "configs/ 目录已存在",
                "configs_dir": str(configs_dir),
            }
        shutil.rmtree(configs_dir)

    src_configs = Path(__file__).resolve().parents[1] / "assets" / "fastbot_configs"
    shutil.copytree(src_configs, configs_dir)

    quicktest_src = Path(__file__).resolve().parents[1] / "assets" / "quicktest.py"
    quicktest_dst = cwd / "quicktest.py"
    shutil.copyfile(quicktest_src, quicktest_dst)

    version_file = configs_dir / "version.json"
    with open(version_file, "w", encoding="utf-8") as fp:
        json.dump(
            {"version": get_cur_version(), "init date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            fp,
            indent=4,
        )

    files = [str(p) for p in sorted(configs_dir.rglob("*")) if p.is_file()]
    files.append(str(quicktest_dst))
    return {"initialized": True, "configs_dir": str(configs_dir), "files": files}


@mcp.tool()
async def kea2_check_device() -> dict:
    """检查当前通过 ADB 连接的 Android 设备列表，返回每台设备的 serial、state、model。
    当用户询问设备连接情况时使用。"""
    devices = []
    for d in adb.list():
        devices.append(
            {
                "serial": d.serial,
                "state": getattr(d, "state", None),
                "model": _safe_model_name(d),
            }
        )
    return {"devices": devices}


@mcp.tool()
async def kea2_run_test(
    serial: str,
    packages: list[str],
    running_minutes: int = 10,
    output_dir: str | None = None,
    property_path: str | None = None,
    property_pattern: str = "test*.py",
    driver_name: str = "d",
    max_step: int | None = None,
    throttle_ms: int | None = None,
    take_screenshots: bool | None = None,
    profile_period: int | None = None,
    restart_app_period: int | None = None,
    act_whitelist_file: str | None = None,
    act_blacklist_file: str | None = None,
) -> dict:
    """在指定 Android 设备上启动 Kea2 测试。参数：
    serial(设备序列号), packages(目标应用包名列表),
    running_minutes(测试时长,默认10), output_dir(可选输出目录),
    property_path(可选性质 .py 文件或目录，相对服务工作目录；省略保持原有模糊测试用法),
    property_pattern(目录中的文件名匹配模式，默认 test*.py；指定文件时忽略),
    driver_name(脚本的设备属性名，默认 d，即 self.d)。
    可选运行参数（省略沿用 CLI 默认值）：max_step(最大探索步数，正整数),
    throttle_ms(事件间隔毫秒，非负整数), take_screenshots(每步截图),
    profile_period(覆盖率和截图采集周期，正整数步数),
    restart_app_period(重启应用周期，非负整数，0 不定期重启),
    act_whitelist_file / act_blacklist_file(互斥，设备端目标路径；
    内容来自项目 configs 下对应名单文件，不是本机文件路径)。
    指定性质时仍由 Fastbot 探索，满足前置条件后按性质规则执行。
    立即返回 task_id，测试在后台运行。"""
    run_options = {
        "max_step": max_step,
        "throttle_ms": throttle_ms,
        "take_screenshots": take_screenshots,
        "profile_period": profile_period,
        "restart_app_period": restart_app_period,
        "act_whitelist_file": act_whitelist_file,
        "act_blacklist_file": act_blacklist_file,
    }
    try:
        runner.run_option_args(run_options)
        runner.property_args(property_path, property_pattern, driver_name)
    except (ValueError, OSError) as exc:
        return {"error": str(exc), "hint": "检查运行参数、性质路径、文件匹配模式和 driver_name"}
    task_store.init_db()
    err = _precheck_run_test(serial, packages)
    if err:
        if "configs/" in err:
            return {"error": "configs/ 目录不存在", "hint": "调用 kea2_init 初始化项目", "auto_fixable": True}
        return {"error": err, "hint": "调用 kea2_init 或检查设备连接"}

    task_id = str(uuid.uuid4())
    stamp = task_id
    params = {
        "serial": serial,
        "packages": packages,
        "running_minutes": running_minutes,
        "output_dir": output_dir,
        "property_path": str(Path(property_path).expanduser().resolve()) if property_path is not None else None,
        "property_pattern": property_pattern,
        "driver_name": driver_name,
        **run_options,
    }

    task_store.create_task(
        task_id=task_id,
        stamp=stamp,
        status="queued",
        device_serial=serial,
        packages=packages,
        output_dir=output_dir,
        extra_json=params,
    )

    try:
        proc, out_dir, log_file, result_file = await runner.launch_kea2_subprocess(params, stamp)
    except (ValueError, OSError) as exc:
        task_store.update_task_status(task_id, "failed", exit_code=4)
        return {"task_id": task_id, "status": "failed", "error": str(exc)}
    _procs[task_id] = proc
    task_store.update_task_status(
        task_id,
        "running",
        pid=proc.pid,
        output_dir=str(out_dir),
        log_file=str(log_file),
        result_file=str(result_file),
    )
    asyncio.create_task(_wait_and_finalize(task_id, proc))

    return {
        "task_id": task_id,
        "stamp": stamp,
        "output_dir": str(out_dir),
        "status": "running",
    }


def _process_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        # On Windows, signal 0 is CTRL_C_EVENT: os.kill(pid, 0) can
        # interrupt the test and its MCP server instead of checking liveness.
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if not handle:
            error = ctypes.get_last_error()
            if error == 87:  # ERROR_INVALID_PARAMETER: no such PID
                return False
            if error == 5:  # ERROR_ACCESS_DENIED: preserve POSIX behavior
                return True
            raise ctypes.WinError(error)
        try:
            result = kernel32.WaitForSingleObject(handle, 0)
            if result == 258:  # WAIT_TIMEOUT: still running
                return True
            if result == 0:  # WAIT_OBJECT_0: exited
                return False
            raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel32.CloseHandle(handle)

    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _read_progress(result_file: str | None):
    if not result_file:
        return None, False
    path = Path(result_file)
    if not path.exists():
        return None, False
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None, True
    executed = fail = error = 0
    if isinstance(data, dict):
        for item in data.values():
            if isinstance(item, dict):
                executed += int(item.get("executed", 0) or 0)
                fail += int(item.get("fail", 0) or 0)
                error += int(item.get("error", 0) or 0)
    return {"executed": executed, "fail": fail, "error": error}, True


@mcp.tool()
async def kea2_get_status(task_id: str) -> dict:
    """查询 Kea2 测试任务的当前状态和进度。参数：task_id。
    返回 status、phase、pid、progress(executed/fail/error计数)、
    result_available。"""
    rec = task_store.get_task(task_id)
    if rec is None:
        return {"error": "not found"}

    pid = rec.get("pid")
    progress, result_available = _read_progress(rec.get("result_file"))

    status = rec.get("status")
    exit_code = rec.get("exit_code")
    if exit_code is not None:
        status = "finished" if int(exit_code) == 0 else "failed"
    if status in {"finished", "failed", "cancelled"}:
        phase = "done"
    elif _process_alive(pid):
        phase = "running"
    else:
        phase = "starting"

    message = "result file not generated yet"
    if result_available:
        message = "result file available"
    elif phase == "done":
        if exit_code is not None and int(exit_code) != 0:
            message = f"子进程启动失败，请查看 log 文件: {rec.get('log_file')}"
        else:
            message = "task finished without readable result file"

    return {
        "task_id": task_id,
        "status": status,
        "phase": phase,
        "pid": pid,
        "progress": progress,
        "result_available": result_available,
        "result_file": rec.get("result_file"),
        "message": message,
    }


@mcp.tool()
async def kea2_get_results(task_id: str) -> dict:
    """获取 Kea2 测试任务的结果文件列表。参数：task_id。
    返回 output_dir 下的所有文件路径。"""
    rec = task_store.get_task(task_id)
    if rec is None:
        return {"error": "not found"}

    out_dir = rec.get("output_dir")
    files = []
    if out_dir and Path(out_dir).exists():
        for p in Path(out_dir).rglob("*"):
            if p.is_file():
                files.append(
                    {
                        "path": str(p),
                        "type": p.suffix.lstrip(".") or "file",
                        "size": p.stat().st_size,
                    }
                )

    return {
        "task_id": task_id,
        "output_dir": out_dir,
        "files": files,
    }


@mcp.tool()
async def kea2_cancel_test(task_id: str) -> dict:
    """取消正在运行的 Kea2 测试任务并清理设备端 Fastbot 进程。参数：task_id。"""
    rec = task_store.get_task(task_id)
    if rec is None:
        return {"error": "not found"}

    prev_status = rec.get("status")
    proc = _procs.get(task_id)
    if proc is not None:
        await runner.cancel_proc(proc)
        _procs.pop(task_id, None)
    else:
        pid = rec.get("pid")
        if pid:
            try:
                os.kill(int(pid), signal.SIGTERM)
            except Exception:
                pass

    try:
        from kea2.adbUtils import ADBDevice

        ADBDevice.setDevice(serial=rec.get("device_serial"))
        dev = ADBDevice()
        dev.kill_proc("com.android.commands.monkey")
    except Exception:
        pass

    task_store.update_task_status(task_id, "cancelled")
    return {"task_id": task_id, "cancelled": True, "prev_status": prev_status}


if __name__ == "__main__":
    mcp.run(transport="stdio")
