"""Offline registration, lifecycle, legacy migration and historical result integration."""
import asyncio
from mcp_dependencies import MCP_AVAILABLE
from concurrent.futures import ThreadPoolExecutor
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from kea2 import task_store, task_registry, keaUtils, kea_launcher
from kea2.run_identity import HANDOFF_ENV, prepare_handoff
from kea2.results import ResultSnapshot


class TestTaskRegistration(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for p in (patch.object(task_store, "DB_PATH", self.root / "tasks.db"),
                  patch.dict(os.environ, {}, clear=True),
                  patch.object(keaUtils.Options, "_set_driver"),
                  patch.object(keaUtils, "_check_package_installation")):
            p.start()
            self.addCleanup(p.stop)

    def fixture(self, directory="old", stamp="old"):
        path = self.root / directory
        path.mkdir(parents=True, exist_ok=True)
        (path / ("result_" + stamp + ".json")).write_text("{}", encoding="utf-8")
        return path

    def run_cli(self, stamp="cli", result=None, failure=None):
        args = kea_launcher.parse_args(["run", "-p", "app", "-o", str(self.root), "--log-stamp", stamp])
        result = result or SimpleNamespace(wasSuccessful=lambda: True, has_crash_or_anr=False)
        with patch.object(kea_launcher.unittest, "main", return_value=SimpleNamespace(result=result), side_effect=failure):
            return kea_launcher.run(args)

    def test_cli_lifecycle_and_query(self):
        self.assertEqual(self.run_cli(), 0)
        rows = task_store.list_tasks_page(origin="cli")["tasks"]
        self.assertEqual(len(rows), 1)
        record = task_store.get_task("cli")
        self.assertEqual(record["status"], "finished")
        self.assertTrue(record["started_at"] and record["finished_at"])
        path = self.root / "res_cli"
        manifest = json.loads((path / "kea2_task.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["task_id"], "cli")
        self.assertEqual(manifest["result_file"], "result_cli.json")
        self.assertEqual(ResultSnapshot(record).report()["execution"]["exit_code"], 0)

    def test_failed_and_interrupted_lifecycle(self):
        result = SimpleNamespace(wasSuccessful=lambda: False, has_crash_or_anr=True)
        self.assertEqual(self.run_cli("bugs", result), 3)
        self.assertEqual(task_store.get_task("bugs")["exit_code"], 3)
        with self.assertRaises(KeyboardInterrupt):
            self.run_cli("interrupted", failure=KeyboardInterrupt())
        self.assertEqual(task_store.get_task("interrupted")["status"], "cancelled")
        task_store.update_task_status("interrupted", "failed", exit_code=4)
        self.assertEqual(task_store.get_task("interrupted")["status"], "cancelled")

    def test_mcp_handoff_reuses_one_task(self):
        task_store.init_db()
        path = self.root / "res_mcp"
        task_store.create_task("mcp", "mcp", output_dir=str(path), origin="mcp", reserve_output=True)
        with patch.dict(os.environ, {HANDOFF_ENV: prepare_handoff(path)}):
            self.assertEqual(self.run_cli("mcp"), 0)
        self.assertEqual(len(task_store.list_tasks()), 1)
        self.assertEqual(task_store.get_task("mcp")["origin"], "mcp")

    def test_mcp_handoff_keeps_timestamp_id_with_custom_stamp(self):
        task_store.init_db()
        identity = "2026111114_1234567890"
        path = self.root / "res_login_test"
        task_store.create_task(identity, "login_test", output_dir=str(path), origin="mcp", reserve_output=True)
        with patch.dict(os.environ, {HANDOFF_ENV: prepare_handoff(path, task_id=identity)}):
            self.assertEqual(self.run_cli("login_test"), 0)
        self.assertEqual(len(task_store.list_tasks()), 1)
        record = task_store.get_task(identity)
        self.assertEqual(record["stamp"], "login_test")
        self.assertEqual(record["status"], "finished")
        self.assertIsNone(task_store.get_task("login_test"))
        manifest = json.loads((path / "kea2_task.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["task_id"], identity)
        self.assertEqual(manifest["result_file"], "result_login_test.json")
        (path / "result_login_test.json").write_text("{}", encoding="utf-8")
        report = ResultSnapshot(record).report()
        self.assertEqual(report["task_id"], identity)
        self.assertEqual(report["availability"]["checks"], "available")

    def test_database_unavailable_leaves_manifest(self):
        with patch.object(task_store, "init_db", side_effect=sqlite3.OperationalError("read only")):
            self.assertEqual(self.run_cli("offline"), 0)
        data = json.loads((self.root / "res_offline" / "kea2_task.json").read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "finished")

    def test_explicit_id_conflict_keeps_cli_path(self):
        task_store.init_db()
        task_store.create_task("taken", "taken", output_dir=str(self.root / "elsewhere"))
        self.assertEqual(self.run_cli("taken"), 0)
        rows = task_store.list_tasks_page(origin="cli")["tasks"]
        self.assertEqual(len(rows), 1)
        self.assertNotEqual(rows[0]["task_id"], "taken")
        self.assertTrue((self.root / "res_taken" / "options.json").exists())
        self.assertEqual(task_store.get_task("taken")["output_dir"], str(self.root / "elsewhere"))

    def test_existing_directory_and_registration_write_failure(self):
        path = self.root / "res_reused"
        path.mkdir()
        (path / "keep.txt").write_text("existing")
        with patch.object(task_store, "create_task", side_effect=sqlite3.OperationalError("commit failed")):
            self.assertEqual(self.run_cli("reused"), 0)
        self.assertEqual((path / "keep.txt").read_text(), "existing")
        self.assertTrue((path / "options.json").exists())
        manifest = json.loads((path / "kea2_task.json").read_text())
        self.assertEqual(manifest["exit_code"], 0)

    def test_legacy_stamp_can_be_queried_and_imported(self):
        stamp = "\u5b9e\u9a8c 1"
        self.assertEqual(self.run_cli(stamp), 0)
        record = task_store.list_tasks_page(origin="cli")["tasks"][0]
        self.assertNotEqual(record["task_id"], stamp)
        path = self.root / ("res_" + stamp)
        (path / ("result_" + stamp + ".json")).write_text("{}")
        self.assertEqual(ResultSnapshot(task_store.get_task(record["task_id"])).report()["execution"]["exit_code"], 0)
        self.assertEqual(task_registry.register_result(str(path))["status"], "already_registered")
        history = self.fixture("legacy", stamp)
        self.assertEqual(task_registry.register_result(str(history))["status"], "registered")

    def test_automatic_id_collision_does_not_change_stamp(self):
        task_store.init_db()
        task_store.create_task("taken", "taken")
        session = {}
        token = task_registry.SESSION.set(session)
        try:
            with patch.object(keaUtils, "new_stamp", return_value="taken"):
                options = keaUtils.Options(output_dir=str(self.root))
            self.assertEqual(options.log_stamp, "taken")
            self.assertNotEqual(session["record"]["task_id"], "taken")
        finally:
            task_registry.SESSION.reset(token)

    def test_historical_registration_is_read_only_and_idempotent(self):
        path = self.fixture()
        before = {p.name: p.read_bytes() for p in path.iterdir()}
        result = task_registry.register_result(str(path))
        self.assertEqual(result["status"], "registered", result)
        self.assertEqual(task_registry.register_result(str(path))["status"], "already_registered")
        record = task_store.get_task("old")
        self.assertEqual(record["origin"], "imported")
        self.assertEqual(record["status"], "unknown")
        self.assertIsNone(record["exit_code"])
        self.assertIsNone(record["finished_at"])
        self.assertEqual(ResultSnapshot(record).report()["execution"]["status"], "unknown")
        self.assertEqual({p.name: p.read_bytes() for p in path.iterdir()}, before)

    def test_selection_conflict_and_alias(self):
        parent = self.root / "history"
        first = self.fixture("history/res_a", "same")
        second = self.fixture("history/res_b", "same")
        result = task_registry.register_result(str(parent))
        self.assertEqual(result["status"], "selection_required")
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(task_registry.register_result(str(first))["status"], "registered")
        self.assertEqual(task_registry.register_result(str(second))["status"], "identity_conflict")
        result = task_registry.register_result(str(second), task_id="other")
        self.assertEqual(result["status"], "registered")
        self.assertEqual(task_store.get_task("other")["stamp"], "same")

    def test_unsupported_invalid_and_manifest(self):
        path = self.root / "html"
        path.mkdir()
        (path / "report.html").write_text("report")
        self.assertEqual(task_registry.register_result(str(path))["status"], "unsupported")
        self.assertEqual(task_registry.register_result(str(path), stamp="../x")["status"], "invalid")
        path = self.fixture()
        (path / "kea2_task.json").write_text(json.dumps({"version": 1, "task_id": "alias", "stamp": "old",
                                                       "status": "finished", "exit_code": 0}))
        self.assertEqual(task_registry.register_result(str(path))["task_id"], "alias")
        self.assertIsNone(task_store.get_task("alias")["exit_code"])
        (path / "kea2_task.json").write_text("broken")
        self.assertEqual(task_registry.register_result(str(path))["status"], "invalid")

    def test_legacy_database_migration_and_compatibility_alias(self):
        from kea2.mcp import task_store as legacy
        self.assertIs(legacy, task_store)
        conn = sqlite3.connect(str(task_store.DB_PATH))
        conn.execute("CREATE TABLE tasks (task_id TEXT PRIMARY KEY, stamp TEXT, pid INTEGER, status TEXT, "
                     "device_serial TEXT, packages TEXT, output_dir TEXT, log_file TEXT, result_file TEXT, "
                     "created_at TEXT, started_at TEXT, finished_at TEXT, exit_code INTEGER, extra_json TEXT)")
        conn.execute("INSERT INTO tasks (task_id, stamp, status) VALUES ('uuid-old','uuid-old','finished')")
        conn.commit()
        conn.close()
        task_store.init_db()
        task_store.init_db()
        self.assertIsNone(task_store.get_task("uuid-old")["origin"])
        self.assertEqual(task_store.get_task("uuid-old")["status"], "finished")

    @unittest.skipUnless(MCP_AVAILABLE, "requires optional MCP")
    def test_hybrid_child_relation_and_parent_query(self):
        from kea2.mcp import server
        task_store.init_db()
        task_store.create_task("parent", "parent", task_kind="hybrid")
        session = {"parent_task_id": "parent"}
        token = task_registry.SESSION.set(session)
        try:
            keaUtils.Options(output_dir=str(self.root), log_stamp="child")
        finally:
            task_registry.SESSION.reset(token)
        page = task_store.list_tasks_page(parent_task_id="parent")
        self.assertEqual(page["tasks"][0]["task_id"], "child")
        result = asyncio.run(server.kea2_get_report("parent"))
        self.assertEqual(result["error"]["code"], "CHILD_TASK_REQUIRED")

    @unittest.skipUnless(MCP_AVAILABLE, "requires optional MCP")
    def test_registration_tool_and_cli(self):
        from kea2.mcp import server
        from kea2.cli import cmd_register_result
        path = self.fixture()
        result = asyncio.run(server.mcp.call_tool("kea2_register_result", {"result_dir": str(path)}))
        self.assertEqual(result.model_dump(by_alias=True)["structuredContent"]["status"], "registered")
        self.assertEqual(cmd_register_result(SimpleNamespace(path=str(path), stamp=None, task_id=None)), 0)

    def test_concurrent_imports_do_not_duplicate(self):
        path = self.fixture()
        task_store.init_db()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: task_registry.register_result(str(path)), range(2)))
        self.assertEqual(sorted(r["status"] for r in results), ["already_registered", "registered"])
        self.assertEqual(len(task_store.list_tasks()), 1)

    def test_historical_hybrid_parent_returns_children(self):
        parent = self.fixture("parent", "merged")
        self.fixture("parent/res_one", "one")
        self.fixture("parent/res_two", "two")
        (parent / "kea2_task.json").write_text(json.dumps({"version": 1, "task_id": "parent",
                                                         "stamp": "parent", "task_kind": "hybrid"}))
        result = task_registry.register_result(str(parent))
        self.assertEqual(result["status"], "selection_required")
        self.assertEqual([c["stamp"] for c in result["candidates"]], ["one", "two"])
