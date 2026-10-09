import asyncio
import sys
from pathlib import Path

import pytest

from kea2.mcp import server, task_store


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    db_file = tmp_path / "tasks.db"
    monkeypatch.setattr(task_store, "DB_PATH", db_file)
    task_store.init_db()
    server._procs.clear()


@pytest.fixture()
def patch_runner(tmp_path, monkeypatch):
    fake_script = Path(__file__).resolve().parents[1] / "fake_kea2_run.py"

    async def _patched_launch(params, stamp):
        parent = Path(params.get("output_dir") or (tmp_path / "output")).resolve()
        out_dir = parent / f"res_{stamp}"
        out_dir.mkdir(parents=True, exist_ok=True)
        log_file = out_dir / f"fastbot_{stamp}.log"
        result_file = out_dir / f"result_{stamp}.json"
        scenario = params.get("scenario", "normal")
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(fake_script),
            "--log-stamp",
            str(stamp),
            "--output-dir",
            str(parent),
            "--scenario",
            scenario,
            "--running-minutes",
            str(params.get("running_minutes", 10)),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        return proc, out_dir, log_file, result_file

    monkeypatch.setattr(server.runner, "launch_kea2_subprocess", _patched_launch)
    monkeypatch.setattr(server, "_precheck_run_test", lambda s, p: None)
    return tmp_path


@pytest.mark.asyncio
async def test_check_device(monkeypatch):
    class Dev:
        serial = "emulator-5554"
        state = "device"

        class prop:
            model = "Pixel"

    monkeypatch.setattr(server.adb, "list", lambda: [Dev()])
    res = await server.kea2_check_device()
    assert "devices" in res
    assert res["devices"][0]["serial"] == "emulator-5554"


@pytest.mark.asyncio
async def test_normal_flow(patch_runner):
    output_dir = str((patch_runner / "out").resolve())
    run_res = await server.kea2_run_test(
        serial="emulator-5554",
        packages=["com.example.app"],
        running_minutes=10,
        output_dir=output_dir,
    )
    task_id = run_res["task_id"]

    status1 = await server.kea2_get_status(task_id)
    assert status1["task_id"] == task_id

    await asyncio.sleep(3)
    status2 = await server.kea2_get_status(task_id)
    assert status2["result_available"] is True
    assert status2["progress"] is not None

    results = await server.kea2_get_results(task_id)
    paths = [f["path"] for f in results["files"]]
    assert any("result_" in p for p in paths)
    assert any("property_exec_info_" in p for p in paths)


@pytest.mark.asyncio
async def test_cancel(patch_runner, monkeypatch):
    original_run = server.kea2_run_test

    async def run_with_long(**kwargs):
        kwargs["output_dir"] = str((patch_runner / "cancel_out").resolve())
        return await original_run(**kwargs)

    async def launch_long(params, stamp):
        params = dict(params)
        params["scenario"] = "long"
        return await server.runner.launch_kea2_subprocess.__wrapped__(params, stamp)  # type: ignore[attr-defined]

    # preserve patched function and wrap for scenario override
    base_launch = server.runner.launch_kea2_subprocess

    async def long_launch(params, stamp):
        p = dict(params)
        p["scenario"] = "long"
        return await base_launch(p, stamp)

    monkeypatch.setattr(server.runner, "launch_kea2_subprocess", long_launch)

    run_res = await run_with_long(
        serial="emulator-5554",
        packages=["com.example.app"],
        running_minutes=10,
    )
    task_id = run_res["task_id"]

    cancel_res = await server.kea2_cancel_test(task_id)
    assert cancel_res["cancelled"] is True
    rec = task_store.get_task(task_id)
    assert rec["status"] == "cancelled"


@pytest.mark.asyncio
async def test_fail(patch_runner, monkeypatch):
    base_launch = server.runner.launch_kea2_subprocess

    async def fail_launch(params, stamp):
        p = dict(params)
        p["scenario"] = "fail"
        return await base_launch(p, stamp)

    monkeypatch.setattr(server.runner, "launch_kea2_subprocess", fail_launch)
    run_res = await server.kea2_run_test(
        serial="emulator-5554",
        packages=["com.example.app"],
        running_minutes=10,
        output_dir=str((patch_runner / "fail_out").resolve()),
    )
    task_id = run_res["task_id"]
    await asyncio.sleep(1)
    status = await server.kea2_get_status(task_id)
    assert status["status"] == "failed"


def test_task_store():
    task_store.create_task(task_id="t1", stamp="s1", status="queued")
    task_store.update_task_status("t1", "running", pid=123)
    one = task_store.get_task("t1")
    assert one is not None
    assert one["status"] == "running"
    all_tasks = task_store.list_tasks()
    assert any(t["task_id"] == "t1" for t in all_tasks)


@pytest.mark.asyncio
async def test_init(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    r1 = await server.kea2_init()
    assert r1["initialized"] is True
    assert (tmp_path / "configs").is_dir()

    r2 = await server.kea2_init()
    assert r2["initialized"] is False
    assert "error" in r2

    r3 = await server.kea2_init(force=True)
    assert r3["initialized"] is True
