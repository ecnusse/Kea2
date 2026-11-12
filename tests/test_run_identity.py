import asyncio
from mcp_dependencies import MCP_AVAILABLE
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

from kea2.run_identity import HANDOFF_ENV, claim_output, new_stamp, prepare_handoff
from kea2.mcp import task_store


class TestRunIdentity(unittest.TestCase):
    def test_format_and_exclusive_directory(self):
        self.assertRegex(new_stamp(), r"^\d{10}_\d{10}$")
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            path = Path(tmp) / "res_test"
            claim_output(path)
            sentinel = path / "options.json"
            sentinel.write_text("original", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                claim_output(path)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "original")

    def test_handoff_is_bound_to_directory_and_consumed_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "res_test"
            path.mkdir()
            handoff = prepare_handoff(path)
            with patch.dict(os.environ, {HANDOFF_ENV: handoff}):
                with self.assertRaises(ValueError):
                    claim_output(Path(tmp) / "other")
            with patch.dict(os.environ, {HANDOFF_ENV: handoff}):
                claim_output(path)
                with self.assertRaises(FileExistsError):
                    claim_output(path)
            with patch.dict(os.environ, {HANDOFF_ENV: handoff}):
                with self.assertRaises(ValueError):
                    claim_output(path)

    def test_directory_conflict_rolls_back_task(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(task_store, "DB_PATH", Path(tmp) / "tasks.db"):
            task_store.init_db()
            path = Path(tmp) / "existing"
            path.mkdir()
            with self.assertRaises(FileExistsError):
                task_store.create_task("t", "t", output_dir=str(path), reserve_output=True)
            self.assertIsNone(task_store.get_task("t"))

    @unittest.skipUnless(MCP_AVAILABLE, "requires optional MCP")
    def test_mcp_retries_database_and_directory_collisions(self):
        from kea2.mcp import server
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(task_store, "DB_PATH", Path(tmp) / "tasks.db"):
            task_store.init_db()
            task_store.create_task("old", "old")
            existing = Path(tmp) / "res_existing"
            existing.mkdir()
            with patch.object(server, "new_stamp", side_effect=["old", "existing", "fresh"]), \
                    patch.object(server, "_precheck_run_test", return_value=None), \
                    patch.object(server.runner, "launch_kea2_subprocess", new_callable=AsyncMock,
                                 side_effect=OSError("fake launch failure")):
                response = asyncio.run(server.kea2_run_test("device", ["app"], output_dir=tmp))
            self.assertEqual(response["task_id"], "fresh")
            self.assertIsNone(task_store.get_task("existing"))
            self.assertFalse((Path(tmp) / "res_old").exists())
            self.assertEqual(task_store.get_task("old")["status"], "queued")
            self.assertEqual(task_store.get_task("fresh")["stamp"], "fresh")

    @unittest.skipUnless(MCP_AVAILABLE, "requires optional MCP")
    def test_mcp_custom_stamp_and_conflicts(self):
        from kea2.mcp import server
        with tempfile.TemporaryDirectory() as tmp, patch.object(task_store, "DB_PATH", Path(tmp) / "tasks.db"), \
                patch.object(server, "_precheck_run_test", return_value=None), \
                patch.object(server, "new_stamp", side_effect=["run_1", "run_2", "run_3", "run_4"]) as automatic, \
                patch.object(server, "_clear_app_data") as clear, \
                patch.object(server.runner, "launch_kea2_subprocess", new_callable=AsyncMock,
                             side_effect=OSError("fake launch failure")) as launch:
            result = asyncio.run(server.kea2_run_test("device", ["app"], output_dir=tmp, log_stamp="login_test"))
            self.assertEqual(result["task_id"], "run_1")
            self.assertEqual(launch.call_args.args[1], "login_test")
            record = task_store.get_task("run_1")
            self.assertEqual(record["stamp"], "login_test")
            self.assertEqual(record["extra_json"]["log_stamp"], "login_test")
            self.assertEqual(Path(record["output_dir"]), Path(tmp) / "res_login_test")
            launch.reset_mock()
            for name in ("login_test", "existing"):
                if name == "existing":
                    (Path(tmp) / "res_existing").mkdir()
                response = asyncio.run(server.kea2_run_test("device", ["app"], output_dir=tmp,
                                                           log_stamp=name, clear_app_data=True))
                self.assertIn("already exists", response["error"])
            launch.assert_not_called()
            clear.assert_not_called()
            self.assertEqual(automatic.call_count, 3)
            response = asyncio.run(server.kea2_run_test("device", ["app"], output_dir=str(Path(tmp) / "other"), log_stamp="login_test"))
            self.assertEqual(response["task_id"], "run_4")
            self.assertEqual(task_store.get_task("run_4")["stamp"], "login_test")
            self.assertIsNone(task_store.get_task("existing"))

    @unittest.skipUnless(MCP_AVAILABLE, "requires optional MCP")
    def test_mcp_rejects_unsafe_custom_names_before_launch(self):
        from kea2.mcp import server
        with patch.object(server, "_precheck_run_test") as precheck:
            for name in ("", "../escape", "a/b", "a\\b", ".", "..", "trailing.", "a b"):
                with self.subTest(name=name):
                    response = asyncio.run(server.kea2_run_test("device", ["app"], log_stamp=name))
                    self.assertIn("log_stamp", response["error"])
            precheck.assert_not_called()

    @unittest.skipUnless(MCP_AVAILABLE, "requires optional MCP")
    def test_custom_stamp_retries_timestamp_id_collision(self):
        from kea2.mcp import server
        with tempfile.TemporaryDirectory() as tmp, patch.object(task_store, "DB_PATH", Path(tmp) / "tasks.db"):
            task_store.init_db()
            task_store.create_task("old", "unrelated")
            with patch.object(server, "new_stamp", side_effect=["old", "fresh"]), \
                    patch.object(server, "_precheck_run_test", return_value=None), \
                    patch.object(server.runner, "launch_kea2_subprocess", new_callable=AsyncMock,
                                 side_effect=OSError("fake launch failure")):
                response = asyncio.run(server.kea2_run_test("device", ["app"], output_dir=tmp, log_stamp="login_test"))
            self.assertEqual(response["task_id"], "fresh")
            self.assertEqual(task_store.get_task("fresh")["stamp"], "login_test")
            self.assertEqual(task_store.get_task("old")["stamp"], "unrelated")

    def test_options_reuse_existing_directory_and_keep_stamp(self):
        from kea2 import keaUtils
        with tempfile.TemporaryDirectory() as tmp, \
                patch.dict(os.environ, {}, clear=True), \
                patch.object(keaUtils.Options, "_set_driver"), \
                patch.object(keaUtils, "_check_package_installation"):
            existing = Path(tmp) / "res_taken"
            existing.mkdir()
            sentinel = existing / "options.json"
            sentinel.write_text("original", encoding="utf-8")
            options = keaUtils.Options(output_dir=tmp, log_stamp="taken")
            self.assertEqual(options.output_dir, existing)
            self.assertNotEqual(sentinel.read_text(encoding="utf-8"), "original")
            with patch.object(keaUtils, "new_stamp", return_value="taken"):
                options = keaUtils.Options(output_dir=tmp)
            self.assertEqual(options.log_stamp, "taken")
            reserved = Path(tmp) / "res_parent"
            reserved.mkdir()
            with patch.dict(os.environ, {HANDOFF_ENV: prepare_handoff(reserved)}):
                options = keaUtils.Options(output_dir=tmp, log_stamp="parent")
            self.assertEqual(options.output_dir, reserved)
