import sqlite3
import json
import asyncio
import os
import signal
import shutil
import base64
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, ImageContent, TextContent
from kea2.mcp import task_store, runner
from kea2.results import ResultError, ResultSnapshot
from kea2.results.models import ContractError, ErrorResponse, json_schema, validated
from adbutils import adb
from kea2.utils import getProjectRoot
from kea2.version_manager import get_cur_version
from datetime import datetime
from kea2.run_identity import new_stamp
from kea2 import task_registry


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
    record = task_store.get_task(task_id)
    if record:
        task_registry.finish_session({"record": record, "registered": True}, rc)
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

    for _ in range(100):
        task_id = stamp = new_stamp()
        reserved_dir = (Path(output_dir or "output").expanduser().resolve() / f"res_{stamp}")
        try:
            task_store.create_task(
                task_id=task_id, stamp=stamp, status="queued", device_serial=serial,
                packages=packages, output_dir=str(reserved_dir), extra_json=params,
                created_at=task_registry.now(), reserve_output=True, origin="mcp",
            )
            break
        except (sqlite3.IntegrityError, FileExistsError):
            continue
        except OSError as exc:
            return {"error": str(exc), "hint": "无法创建新的实验结果目录"}
    else:
        return {"error": "Cannot allocate a unique timestamp after 100 attempts"}
    params["_reserved_output_dir"] = str(reserved_dir)
    task_registry.write_manifest({
        "task_id": task_id, "stamp": stamp, "output_dir": str(reserved_dir),
        "origin": "mcp", "status": "queued", "packages": packages, "device_serial": serial,
    })

    try:
        proc, out_dir, log_file, result_file = await runner.launch_kea2_subprocess(params, stamp)
    except (ValueError, OSError) as exc:
        task_store.update_task_status(task_id, "failed", exit_code=4, finished_at=task_registry.now())
        failed = task_store.get_task(task_id)
        if failed:
            task_registry.write_manifest(failed)
        return {"task_id": task_id, "status": "failed", "error": str(exc)}
    _procs[task_id] = proc
    task_store.update_task_status(
        task_id,
        "running",
        pid=proc.pid,
        output_dir=str(out_dir),
        log_file=str(log_file),
        result_file=str(result_file),
        started_at=task_registry.now(),
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
async def kea2_list_tasks(status: str | None = None, limit: int = 20,
                          offset: int = 0, origin: str | None = None,
                          parent_task_id: str | None = None) -> dict[str, Any]:
    """查询当前 MCP 用户环境中已登记的任务 ID 和元数据，不需要 task_id。

    按创建时间倒序，时间相同时按 task_id 倒序。status 可选：queued/running/
    cancelling/cancelled/finished/failed/unknown；省略则返回所有状态。
    limit 默认 20，范围 1–100；offset 为非负整数，使用返回的 next_offset 翻页。
    返回 tasks、total、limit、offset、next_offset。无任务时 tasks=[]。
    origin 可选 cli/mcp/imported；parent_task_id 可列出 hybrid 父任务的子实验。
    status 是数据库记录的原始状态，failed 也可能是发现缺陷导致的非零退出；
    不表示结果文件一定可用。分页期间任务变化可能导致重复或遗漏，可重新查询。
    仅供用户查找并选择任务，不能自动选择最近任务分析。必须等待用户指定具体 task_id。
    """
    try:
        return await asyncio.to_thread(task_store.list_tasks_page, status, limit, offset, origin, parent_task_id)
    except ValueError as exc:
        messages = {
            "INVALID_STATUS": "status must be queued/running/cancelling/cancelled/finished/failed/unknown",
            "INVALID_LIMIT": "limit must be an integer between 1 and 100",
            "INVALID_OFFSET": "offset must be a non-negative integer",
            "INVALID_ORIGIN": "origin must be cli/mcp/imported",
        }
        code = str(exc)
        if code not in messages:
            raise
        return {"error": {"code": code, "message": messages[code]}}


@mcp.tool(structured_output=True)
async def kea2_register_result(result_dir: str, stamp: str | None = None,
                               task_id: str | None = None) -> dict[str, Any]:
    """登记用户明确指定的历史实验目录，不运行测试，不修改历史文件。
    只检查指定目录及其直接 res_* 子目录。多个候选返回 selection_required，
    用户须指定准确 result_dir/stamp。相同目录和 stamp 返回 already_registered。
    ID 冲突时返回 identity_conflict，可由用户明确提供 task_id 别名，原文件不改名。
    旧实验状态为 unknown，数据缺失由 availability/warnings 说明。只有 HTML 不支持。
    登记成功后仍须用户明确指定 task_id 才能开始分析，不自动选择最新任务。
    """
    return await asyncio.to_thread(task_registry.register_result, result_dir, stamp, task_id)


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
    if exit_code is not None and status != "cancelled":
        status = "finished" if int(exit_code) == 0 else "failed"
    if status == "unknown":
        phase = "unknown"
    elif status in {"finished", "failed", "cancelled"}:
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


@mcp.tool(structured_output=True)
async def kea2_get_result_schema(document: str = "experiment") -> dict[str, Any]:
    """获取结构化结果的数据契约，无需启动测试或传入 task_id。
    document 为 experiment（完整模型）、report、query、finding、artifact 或 error。
    返回 JSON Schema，定义字段类型、枚举、单位、必填与可空规则。
    尚未采集的完整模型字段为 null；参见数据可用性。
    Schema 定义不表示所有采集能力已实现。"""
    try:
        return json_schema(document)
    except ValueError:
        return validated(ErrorResponse, {"error": {
            "code": "INVALID_SCHEMA_DOCUMENT",
            "message": "Supported documents: experiment, report, query, finding, artifact, error",
        }})


@mcp.tool(structured_output=True)
async def kea2_get_report(task_id: str) -> dict[str, Any]:
    """读取实验概览、性质统计、覆盖率、Crash/ANR 计数和数据可用性。
    只读本地已有产物，不生成 HTML、不连接设备。缺失数据为 null，不代表零。
    返回 snapshot_id；随后用 kea2_query_report 查询明细。
    操作时间线通过 query_report 的 steps 获取，截图内容通过 get_artifact 获取。
    控件列表通过 query_report 的 widgets 获取；当前不支持多实验分析。"""
    return await _query_result(task_id, "report")


@mcp.tool(structured_output=True)
async def kea2_query_report(
    task_id: str, section: str, filters: dict | None = None,
    cursor: str | None = None, limit: int = 50,
) -> dict[str, Any]:
    """分页查询结构化实验结果，limit 为 1..100。
    section: checks / findings / activities / trends / steps / executions / artifacts / widgets / property_execution_trend / configuration。
    configuration: exact document(run_options/report_configuration) and key filters; saved values, not observed execution.
    widgets: exact activity/class_name/resource_id/content_description/parse_status filters.
    property_execution_trend: inclusive start_step/end_step filters; distinct started properties.
    filters: checks 支持 name(子串)、kind、has_findings(布尔)；
    findings 支持 type(property/invariant/unknown/crash/anr)、check_name、state；
    activities 支持 name(子串)、covered(布尔)；trends 支持 metric
    (activity_coverage_percent / unique_triggered_widget_count)。
    steps 支持 type、start_step/end_step(包含边界的 Monkey 步数)、execution_id；
    executions 支持 id、check_name、kind、state；artifacts 支持 id、kind、availability。
    execution_id 查询返回起止事件之间的日志上下文，不宣称所有事件都属于该性质。
    缺失任一执行边界时只返回已有边界，不推测未记录的区间。
    传 next_cursor 读取下一页；STALE_SNAPSHOT 表示数据已变化，需重新分页。
    findings 是异常发生记录，不是去重后的缺陷。堆栈通过 kea2_get_finding 获取。"""
    return await _query_result(task_id, "query", section, filters, cursor, limit)


@mcp.tool(structured_output=True)
async def kea2_get_finding(
    task_id: str, finding_id: str, snapshot_id: str,
    offset: int = 0, limit: int = 8000,
    context_before: int = 0, context_after: int = 0,
) -> dict[str, Any]:
    """读取异常详情及完整堆栈的一个字符片段。
    finding_id 和 snapshot_id 来自 kea2_query_report 的 findings 查询。
    offset 为字符偏移，limit 为 1..32000；按 next_offset 继续读取直到 null。
    context_before/context_after 为 0..20，围绕唯一关联步骤返回前后日志记录；
    关联不明确时不猜测上下文。返回相关执行片段和截图产物元数据，
    实际图片需调用 kea2_get_artifact。关联表示日志对应关系，不代表根因。"""
    return await _query_result(task_id, "finding", finding_id, snapshot_id, offset, limit,
                               context_before, context_after)


@mcp.tool()
async def kea2_get_artifact(
    task_id: str, artifact_id: str, snapshot_id: str, offset: int = 0, limit: int = 8000,
) -> CallToolResult:
    """读取已登记的证据内容。artifact_id、snapshot_id 来自 query_report 或 get_finding。
    截图以 MCP 原生 image 内容返回，完整原文件，上限 8 MiB；不接受任意路径。
    日志按 Unicode 字符分页（offset>=0，limit=1..32000，上限64 MiB），
    沿 next_offset 读取直到 null。无效图片或非 UTF-8 文本明确报错。
    snapshot 变化需重新查询；元数据不等于已读取图片。"""
    result = await _query_result(task_id, "artifact", artifact_id, snapshot_id, offset, limit)
    if isinstance(result, dict):
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False))],
                              structured_content=result, is_error=True)
    metadata, image_bytes = result
    content = [TextContent(type="text", text=json.dumps(metadata, ensure_ascii=False))]
    if image_bytes is not None:
        content.append(ImageContent(type="image", data=base64.b64encode(image_bytes).decode("ascii"),
                                    mime_type=metadata["artifact"]["mime_type"]))
    return CallToolResult(content=content, structured_content=metadata)


async def _query_result(task_id, operation, *args):
    rec = task_store.get_task(task_id)
    if rec is None:
        return validated(ErrorResponse, {"error": {"code": "TASK_NOT_FOUND", "message": "Task not found"}})
    if rec.get("task_kind") == "hybrid":
        return validated(ErrorResponse, {"error": {"code": "CHILD_TASK_REQUIRED", "message":
            "Select a child experiment via kea2_list_tasks(parent_task_id=task_id); the parent is not a single experiment"}})

    def read():
        try:
            snapshot = ResultSnapshot(rec)
            return getattr(snapshot, operation)(*args)
        except ResultError as exc:
            return validated(ErrorResponse, {"error": {"code": exc.code, "message": str(exc)}})
        except ContractError as exc:
            return validated(ErrorResponse, {"error": {"code": "RESULT_CONTRACT_ERROR", "message": str(exc)}})
        except OSError:
            return validated(ErrorResponse, {"error": {"code": "RESULT_READ_ERROR", "message": "Cannot read result directory"}})

    # Parsing large logs must not block other MCP calls or task finalization.
    return await asyncio.get_running_loop().run_in_executor(None, read)


@mcp.tool()
async def kea2_cancel_test(task_id: str) -> dict:
    """取消正在运行的 Kea2 测试任务并清理设备端 Fastbot 进程。参数：task_id。"""
    rec = task_store.get_task(task_id)
    if rec is None:
        return {"error": "not found"}

    prev_status = rec.get("status")
    task_store.update_task_status(task_id, "cancelling")
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

    task_store.update_task_status(task_id, "cancelled", finished_at=task_registry.now())
    record = task_store.get_task(task_id)
    if record and record.get("output_dir") and Path(record["output_dir"]).is_dir():
        task_registry.write_manifest(record)
    return {"task_id": task_id, "cancelled": True, "prev_status": prev_status}


if __name__ == "__main__":
    mcp.run(transport="stdio")
