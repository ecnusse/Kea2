"""Read-only preparation and shared validation, without a device."""
import asyncio
import inspect
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp_dependencies import MCP_AVAILABLE

if MCP_AVAILABLE:
    from kea2.mcp import server


@unittest.skipUnless(MCP_AVAILABLE, "requires optional MCP dependencies")
class TestPreparation(unittest.TestCase):
    def test_package_pagination(self):
        with patch.object(server.adb, "device") as device:
            device.return_value.list_packages.return_value = ["app.z", "system.x", "app.a", "app.z"]
            result = asyncio.run(server.kea2_list_apps("selected", "app.", limit=1))
            self.assertEqual(result["packages"], ["app.a"])
            self.assertEqual(result["next_offset"], 1)
            self.assertEqual(result["total"], 2)
            self.assertFalse(result["names_available"])
            device.assert_called_with(serial="selected")
            result = asyncio.run(server.kea2_list_apps("selected", "app.", limit=1, offset=1))
            self.assertEqual(result["packages"], ["app.z"])
            self.assertIsNone(result["next_offset"])

    def test_setup_is_read_only_and_reports_blockers(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(server.adb, "device") as device, \
                patch.object(server.task_store, "init_db") as db, \
                patch.object(server, "_clear_app_data") as clear:
            previous = os.getcwd()
            try:
                os.chdir(tmp)
                device.return_value.list_packages.return_value = ["app"]
                result = asyncio.run(server.kea2_check_test_setup("selected", ["missing"],
                    {"act_whitelist_file": "/sdcard/list", "clear_app_data": True}))
                codes = {issue["code"] for issue in result["issues"]}
                self.assertTrue({"PROJECT_NOT_INITIALIZED", "APP_NOT_INSTALLED", "MISSING_ACTIVITY_LIST"} <= codes)
                self.assertEqual(list(Path(tmp).iterdir()), [])
                db.assert_not_called()
                clear.assert_not_called()
                Path("configs").mkdir()
                result = asyncio.run(server.kea2_check_test_setup("selected", ["app"]))
                self.assertTrue(result["ready"], result)
                self.assertEqual(result["tool_defaults"]["clear_app_data"], False)
                result = asyncio.run(server.kea2_check_test_setup("selected", ["app"], {"bogus": 1}))
                self.assertFalse(result["ready"])
            finally:
                os.chdir(previous)

    def test_setup_and_run_reject_same_invalid_settings(self):
        for options in ({"running_minutes": 0}, {"clear_app_data": "yes"},
                        {"throttle_ms": -1}, {"property_path": "missing.py"},
                        {"act_whitelist_file": "a", "act_blacklist_file": "b"}):
            with self.subTest(options=options), patch.object(server.adb, "device") as device, \
                    patch.object(server.task_store, "create_task") as create:
                device.return_value.list_packages.return_value = ["app"]
                setup = asyncio.run(server.kea2_check_test_setup("selected", ["app"], options))
                result = asyncio.run(server.kea2_run_test("selected", ["app"], **options))
                self.assertIn("error", result)
                self.assertIn(result["error"], [i.get("message") for i in setup["issues"]])
                create.assert_not_called()

    def test_interview_covers_current_tool_parameters(self):
        guide = (Path(__file__).resolve().parents[1] / "skills/kea2-test/references/parameters.md").read_text(encoding="utf-8")
        documented = {line.split("|")[1].strip() for line in guide.splitlines() if line.startswith("| ")}
        self.assertTrue(set(inspect.signature(server.kea2_run_test).parameters) <= documented)
