"""Saved configuration provenance, legacy serialization and MCP queries."""

import asyncio
import importlib.util
import json
import unittest
from unittest.mock import patch

from kea2.results import ResultSnapshot, ResultError
from kea2.results.models import to_dict
import test_structured_results as fixtures


class TestResultConfiguration(unittest.TestCase):
    setUp = fixtures.TestStructuredResults.setUp
    write = fixtures.TestStructuredResults.write
    lines = fixtures.TestStructuredResults.lines

    def test_saved_values_remain_separate_from_requests(self):
        self.task["extra_json"] = {"running_mins": 10}
        self.write("options.json", {"running_mins": 8, "take_screenshots": False,
                                    "propertytest_args": ["discover", "-p", "测试.py"], "future": {"a": None}})
        self.write("bug_report_config.json", {"test_time": "2026-10-21 12:00:00"})
        before = (self.root / "options.json").read_bytes()
        snapshot = ResultSnapshot(self.task)
        row = snapshot.query("configuration", {"document": "run_options", "key": "running_mins"})["items"][0]
        self.assertEqual(row["value"], 8)
        self.assertEqual(row["source"], {"artifact": "options.json", "key": "running_mins"})
        self.assertEqual(snapshot.report()["execution"]["requested_parameters"]["running_mins"], 10)
        self.assertEqual(before, (self.root / "options.json").read_bytes())
        self.assertEqual(len(snapshot.to_model().configuration), 5)

    def test_missing_empty_and_invalid_are_distinct(self):
        self.assertIsNone(ResultSnapshot(self.task).to_model().configuration)
        self.write("options.json", {})
        self.assertEqual(ResultSnapshot(self.task).to_model().configuration, [])
        for raw in ('[]', '{', '{"serial":1,"serial":2}'):
            self.write("options.json", raw)
            snapshot = ResultSnapshot(self.task)
            self.assertEqual(snapshot.availability["run_options"], "invalid")
            self.assertIsNone(snapshot.to_model().configuration)
        self.write("bug_report_config.json", {"take_screenshots": True})
        self.assertEqual(len(ResultSnapshot(self.task).to_model().configuration), 1)

    def test_infinity_is_json_safe_and_not_a_string_or_null(self):
        self.write("options.json", '{"maxStep":Infinity,"nested":[NaN,-Infinity,1e400],"literal":"Infinity"}')
        snapshot = ResultSnapshot(self.task)
        rows = {r["key"]: r for r in snapshot.query("configuration")["items"]}
        self.assertEqual(rows["maxStep"]["value"], {"$nonfinite": "Infinity"})
        self.assertEqual(rows["maxStep"]["encoding"], "tagged_nonfinite")
        self.assertEqual(rows["literal"]["encoding"], "json")
        self.assertEqual(rows["nested"]["value"][0], {"$nonfinite": "NaN"})
        json.dumps(to_dict(snapshot.to_model()), allow_nan=False)

    def test_conflicting_configuration_warns_and_keeps_both(self):
        self.write("options.json", {"log_stamp": "another", "take_screenshots": True})
        self.write("bug_report_config.json", {"log_stamp": "run", "take_screenshots": False})
        snapshot = ResultSnapshot(self.task)
        self.assertEqual(snapshot.query("configuration", {"key": "take_screenshots"})["total"], 2)
        codes = [w["code"] for w in snapshot.warnings]
        self.assertIn("CONFIGURATION_STAMP_MISMATCH", codes)
        self.assertIn("CONFIGURATION_DISAGREEMENT:take_screenshots", codes)

    def test_configuration_changes_invalidate_cursor(self):
        self.write("options.json", {"a": 1, "b": 2})
        snapshot = ResultSnapshot(self.task)
        page = snapshot.query("configuration", limit=1)
        self.assertEqual(snapshot.query("configuration", cursor=page["next_cursor"])["items"][0]["key"], "b")
        self.write("options.json", {"a": 1, "b": 3})
        with self.assertRaises(ResultError) as caught:
            ResultSnapshot(self.task).query("configuration", cursor=page["next_cursor"])
        self.assertEqual(caught.exception.code, "STALE_SNAPSHOT")

    @unittest.skipUnless(importlib.util.find_spec("mcp"), "requires optional MCP")
    def test_configuration_mcp_structured_response(self):
        from kea2.mcp import server, task_store
        self.write("options.json", {"running_mins": 10})

        async def check():
            with patch.object(task_store, "get_task", return_value=self.task):
                result = await server.mcp.call_tool("kea2_query_report", {
                    "task_id": "task", "section": "configuration", "filters": {"key": "running_mins"}})
                content = result.model_dump(by_alias=True)["structuredContent"]
                self.assertEqual(content["items"][0]["value"], 10)
        asyncio.run(check())
