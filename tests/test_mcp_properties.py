"""Offline coverage for optional MCP property discovery."""
import asyncio
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

MCP_AVAILABLE = (importlib.util.find_spec("mcp") is not None
                 and importlib.util.find_spec("aiofiles") is not None)
if MCP_AVAILABLE:
    from kea2.mcp import runner, server


@unittest.skipUnless(MCP_AVAILABLE, "requires optional MCP dependencies")
class TestMcpProperties(unittest.TestCase):
    def test_run_options_defaults_and_validation(self):
        self.assertEqual(runner.run_option_args({}), [])
        self.assertEqual(runner.run_option_args({"take_screenshots": False, "max_step": None}), [])
        for options in ({"max_step": 0}, {"throttle_ms": -1}, {"profile_period": 0},
                        {"restart_app_period": -1}, {"max_step": True},
                        {"take_screenshots": "true"}, {"act_whitelist_file": ""},
                        {"act_whitelist_file": "a", "act_blacklist_file": "b"}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                runner.run_option_args(options)

    def test_run_options_parse_with_existing_cli(self):
        from kea2.kea_launcher import parse_args
        options = {"max_step": 50, "throttle_ms": 0, "take_screenshots": True,
                   "profile_period": 20, "restart_app_period": 0,
                   "act_whitelist_file": "/sdcard/.kea2/awl.strings"}
        parsed = parse_args(["run", "-p", "app"] + runner.run_option_args(options))
        for name, value in options.items():
            self.assertEqual(getattr(parsed, name), value)
        parsed = parse_args(["run", "-p", "app"] + runner.run_option_args(
            {"act_blacklist_file": "/sdcard/.kea2/abl.strings"}))
        self.assertEqual(parsed.act_blacklist_file, "/sdcard/.kea2/abl.strings")

    def test_invalid_options_do_not_create_task(self):
        with patch.object(server.task_store, "create_task") as create:
            response = asyncio.run(server.kea2_run_test("device", ["app"], profile_period=0))
        self.assertIn("error", response)
        create.assert_not_called()

    def test_omitted_path(self):
        self.assertEqual(runner.property_args(), [])

    def test_file_and_directory(self):
        with tempfile.TemporaryDirectory(prefix="kea2 properties ") as tmp:
            script = Path(tmp) / "quicktest.py"
            script.touch()
            args = runner.property_args(str(script), "ignored*.py", "device")
            self.assertEqual(args, ["--driver-name", "device",
                                   "propertytest", "discover", "-s", str(script.parent.resolve()),
                                   "-p", "quicktest.py"])
            self.assertEqual(runner.property_args(tmp, "quick*.py")[-1], "quick*.py")
            previous = os.getcwd()
            try:
                os.chdir(tmp)
                self.assertEqual(runner.property_args("quicktest.py"),
                                 runner.property_args(str(script)))
            finally:
                os.chdir(previous)

    def test_invalid_selections(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "note.txt"
            script.touch()
            for path, pattern, driver in [("", "test*.py", "d"),
                                          (str(script), "test*.py", "d"),
                                          (str(script.parent / "missing.py"), "test*.py", "d"),
                                          (tmp, "test*.py", "d"),
                                          (tmp, "../*.py", "d"),
                                          (tmp, "*.py", "self.d")]:
                with self.subTest(path=path, pattern=pattern, driver=driver):
                    with self.assertRaises(ValueError):
                        runner.property_args(path, pattern, driver)

    def test_invalid_path_does_not_create_task(self):
        with patch.object(server.task_store, "create_task") as create:
            response = asyncio.run(server.kea2_run_test("device", ["app"], property_path=""))
        self.assertIn("error", response)
        create.assert_not_called()

    def test_subprocess_command(self):
        async def check(tmp, selection):
            with patch.object(runner.asyncio, "create_subprocess_exec", new_callable=AsyncMock) as launch, \
                    patch.object(runner, "_stream_to_file", new_callable=AsyncMock), \
                    patch.object(runner, "getProjectRoot", return_value=Path(tmp)):
                await runner.launch_kea2_subprocess({"serial": "device", "packages": ["app"],
                    "running_minutes": 5, "output_dir": tmp, "property_path": selection,
                    "throttle_ms": 500, "take_screenshots": True, "max_step": 50}, "test")
                cmd = launch.call_args.args
                self.assertEqual(launch.call_args.kwargs["cwd"], tmp)
                self.assertEqual("propertytest" in cmd, selection is not None)
                from kea2.kea_launcher import parse_args
                parsed = parse_args(list(cmd[3:]))
                self.assertEqual(parsed.throttle_ms, 500)
                self.assertEqual(parsed.max_step, 50)
                self.assertTrue(parsed.take_screenshots)
                if selection:
                    from kea2.kea_launcher import parse_args, _sanitize_args
                    parsed = parse_args(list(cmd[3:]))
                    _sanitize_args(parsed)
                    self.assertEqual(parsed.driver_name, "d")
                    self.assertEqual(parsed.propertytest_args[-1], "quicktest.py")
                await asyncio.sleep(0)
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "quicktest.py"
            script.touch()
            for selection in (None, str(script)):
                asyncio.run(check(tmp, selection))

    def test_selection_is_saved(self):
        async def check(tmp):
            script = Path(tmp) / "quicktest.py"
            script.touch()
            fake_proc = SimpleNamespace(pid=123)
            with patch.object(server, "_precheck_run_test", return_value=None), \
                    patch.object(server.task_store, "init_db"), \
                    patch.object(server.task_store, "create_task") as create, \
                    patch.object(server.task_store, "update_task_status"), \
                    patch.object(server, "_wait_and_finalize", new_callable=AsyncMock), \
                    patch.object(server.runner, "launch_kea2_subprocess", new_callable=AsyncMock,
                                 return_value=(fake_proc, Path(tmp), script, script)) as launch:
                response = await server.kea2_run_test("device", ["app"],
                    property_path=str(script), property_pattern="ignored", driver_name="device",
                    max_step=50, throttle_ms=500, take_screenshots=True, profile_period=20,
                    restart_app_period=100, act_whitelist_file="/sdcard/.kea2/awl.strings")
                try:
                    params = create.call_args.kwargs["extra_json"]
                    self.assertEqual(params["property_path"], str(script.resolve()))
                    self.assertEqual(params["driver_name"], "device")
                    for name, value in {"max_step": 50, "throttle_ms": 500,
                            "take_screenshots": True, "profile_period": 20,
                            "restart_app_period": 100,
                            "act_whitelist_file": "/sdcard/.kea2/awl.strings",
                            "act_blacklist_file": None}.items():
                        self.assertEqual(params[name], value)
                    self.assertEqual(params, launch.call_args.args[0])
                    await asyncio.sleep(0)
                finally:
                    server._procs.pop(response["task_id"], None)
        with tempfile.TemporaryDirectory() as tmp:
            asyncio.run(check(tmp))


if __name__ == "__main__":
    unittest.main()
