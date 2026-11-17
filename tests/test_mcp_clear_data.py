"""Offline checks for opt-in destructive app reset before MCP test launch."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, call, patch

from mcp_dependencies import MCP_AVAILABLE

if MCP_AVAILABLE:
    from kea2.mcp import server, task_store


@unittest.skipUnless(MCP_AVAILABLE, "requires optional MCP dependencies")
class TestClearAppData(unittest.TestCase):
    def test_device_selection_deduplication_and_partial_failure(self):
        with patch.object(server.adb, "device") as select:
            device = select.return_value
            device.shell.side_effect = ["Success\n", "Failed"]
            with self.assertRaisesRegex(ValueError, r"already cleared: \['app.one'\]"):
                server._clear_app_data("chosen-device", ["app.one", "app.one", "app.two"])
            select.assert_called_once_with(serial="chosen-device")
            self.assertEqual(device.shell.call_args_list, [
                call(["pm", "clear", "app.one"], timeout=30),
                call(["pm", "clear", "app.two"], timeout=30)])

    def test_invalid_parameters_do_not_clear_or_launch(self):
        for packages, enabled in [(["app"], "false"), ([], True), (["app;bad"], True)]:
            with self.subTest(packages=packages, enabled=enabled), \
                    patch.object(server, "_clear_app_data") as clear, \
                    patch.object(server.runner, "launch_kea2_subprocess", new_callable=AsyncMock) as launch:
                result = asyncio.run(server.kea2_run_test("device", packages, clear_app_data=enabled))
                self.assertIn("error", result)
                clear.assert_not_called()
                launch.assert_not_awaited()

    def test_default_success_and_failure_lifecycle(self):
        async def check(root, enabled, fail):
            events = []

            def clear(serial, packages):
                events.append("clear")
                self.assertEqual((serial, packages), ("device", ["app"]))
                if fail:
                    raise ValueError("clear failed")

            async def launch(params, stamp):
                events.append("launch")
                directory = Path(params["_reserved_output_dir"])
                return SimpleNamespace(pid=123), directory, directory / "log", directory / "result"

            with patch.object(task_store, "DB_PATH", root / "tasks.db"), \
                    patch.object(server, "_precheck_run_test", return_value=None), \
                    patch.object(server, "_clear_app_data", side_effect=clear), \
                    patch.object(server.runner, "launch_kea2_subprocess", side_effect=launch), \
                    patch.object(server, "_wait_and_finalize", new_callable=AsyncMock):
                kwargs = {} if enabled is None else {"clear_app_data": enabled}
                result = await server.kea2_run_test("device", ["app"], output_dir=str(root), **kwargs)
                try:
                    record = task_store.get_task(result["task_id"])
                    self.assertEqual(result["status"], "failed" if fail else "running")
                    self.assertEqual(record["extra_json"]["clear_app_data"], bool(enabled))
                    self.assertEqual(events, ["clear"] if fail else
                                     (["clear", "launch"] if enabled else ["launch"]))
                    if fail:
                        self.assertEqual(record["exit_code"], 4)
                    await asyncio.sleep(0)
                finally:
                    server._procs.pop(result["task_id"], None)

        for enabled, fail in [(None, False), (False, False), (True, False), (True, True)]:
            with self.subTest(enabled=enabled, fail=fail), tempfile.TemporaryDirectory() as tmp:
                asyncio.run(check(Path(tmp), enabled, fail))
