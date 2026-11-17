"""Coverage details, corruption handling and existing HTML trend parity."""

import asyncio
from mcp_dependencies import MCP_AVAILABLE
import unittest
from unittest.mock import patch
from kea2.results import ResultSnapshot, ResultError
import test_structured_results as fixtures


class TestResultCoverage(unittest.TestCase):
    setUp = fixtures.TestStructuredResults.setUp
    write = fixtures.TestStructuredResults.write
    lines = fixtures.TestStructuredResults.lines

    def widgets(self, text):
        self.write("output_run/widget_coverage_report.txt", text)

    def steps(self, markers):
        self.lines("output_run/steps.log", [
            {"Type": "ScriptInfo", "MonkeyStepsCount": n,
             "Info": dict(propName=name, state="start", **extra)}
            for n, name, extra in markers])

    def test_inventory_preserves_values_and_filters(self):
        self.widgets("activity:Home|class:Button|resourceId:<AUTO>|content-desc:你好|x:y|\n"
                     "activity:Home|class:KEY_BACK|resourceId:KEY_BACK|content-desc:KEY_BACK|\n")
        snapshot = ResultSnapshot(self.task)
        page = snapshot.query("widgets", {"class_name": "Button"})
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["items"][0]["content_description"], "你好|x:y")
        self.assertEqual(page["items"][0]["resource_id"], "<AUTO>")
        self.assertEqual(page["items"][0]["source"]["line"], 1)
        self.assertTrue(any(w["code"] == "WIDGET_COUNTS_DISAGREE" for w in snapshot.warnings))
        self.assertEqual(len(snapshot.to_model().widgets), 2)

    def test_ambiguous_and_malformed_inventory_retains_raw(self):
        rows = ["broken", "activity:Home|class:Button|resourceId:x|content-desc:a|class:b|"]
        self.widgets("\n".join(rows))
        snapshot = ResultSnapshot(self.task)
        items = snapshot.query("widgets")["items"]
        self.assertEqual([x["raw"] for x in items], rows)
        self.assertEqual([x["parse_status"] for x in items], ["invalid", "ambiguous"])
        self.assertTrue(all(x["activity"] is None for x in items))
        self.assertEqual(snapshot.availability["widget_inventory"], "partial")

    def test_missing_empty_and_snapshot_changes(self):
        self.assertIsNone(ResultSnapshot(self.task).to_model().widgets)
        self.widgets("")
        self.assertEqual(ResultSnapshot(self.task).to_model().widgets, [])
        row = "activity:Home|class:Button|resourceId:|content-desc:|"
        self.widgets(row + "\n" + row)
        snapshot = ResultSnapshot(self.task)
        cursor = snapshot.query("widgets", limit=1)["next_cursor"]
        self.assertTrue(any(w["code"] == "DUPLICATE_WIDGET_RECORD" for w in snapshot.warnings))
        self.widgets(row)
        with self.assertRaises(ResultError) as caught:
            ResultSnapshot(self.task).query("widgets", cursor=cursor)
        self.assertEqual(caught.exception.code, "STALE_SNAPSHOT")

    def test_property_trend_matches_html_sampling_and_distinct_counts(self):
        from kea2.report.bug_report_generator import BugReportGenerator
        self.steps([(2, "test.a", {}), (3, "test.a", {}),
                    (4, "test.invariant", {"kind": ""}),
                    (5, "other.invariant", {"kind": " Invariant "}),
                    (7, "legacy", {})])
        coverage = [dict(self.coverage, stepsCount=n) for n in (0, 3, 7, 20)]
        self.lines("output_run/coverage.log", coverage)
        snapshot = ResultSnapshot(self.task)
        generator = object.__new__(BugReportGenerator)
        generator._cov_trend = coverage
        expected = generator._generate_property_execution_trend({2: {"test.a"}, 3: {"test.a"}, 7: {"test.a", "legacy"}})
        actual = snapshot.query("property_execution_trend")["items"]
        self.assertEqual([{"stepsCount": x["monkey_step"], "executedPropertiesCount": x["executed_property_count"]} for x in actual], expected)
        self.assertEqual(snapshot.query("property_execution_trend", {"start_step": 7})["total"], 2)

    def test_missing_steps_is_unknown_and_no_coverage_falls_back(self):
        self.assertIsNone(ResultSnapshot(self.task).to_model().property_execution_trend)
        self.steps([(3, "test.a", {}), (9, "test.a", {}), (10, "legacy", {})])
        (self.root / "output_run/coverage.log").unlink()
        items = ResultSnapshot(self.task).query("property_execution_trend")["items"]
        self.assertEqual([(x["monkey_step"], x["executed_property_count"]) for x in items], [(3, 1), (9, 1), (10, 2)])

    def test_malformed_steps_do_not_create_a_false_property(self):
        self.write("output_run/steps.log", '{"Type":"ScriptInfo","MonkeyStepsCount":1,"Info":"{invalid"}\nBAD\n')
        snapshot = ResultSnapshot(self.task)
        self.assertEqual(snapshot.availability["steps"], "partial")
        self.assertEqual(snapshot.query("property_execution_trend")["items"][0]["executed_property_count"], 0)

    @unittest.skipUnless(MCP_AVAILABLE, "requires optional MCP")
    def test_new_sections_return_native_structured_content(self):
        from kea2.mcp import server, task_store
        self.widgets("activity:Home|class:Button|resourceId:|content-desc:|")
        self.steps([(3, "test.a", {})])

        async def check():
            with patch.object(task_store, "get_task", return_value=self.task):
                for section in ("widgets", "property_execution_trend"):
                    result = await server.mcp.call_tool("kea2_query_report", {
                        "task_id": "task", "section": section, "limit": 1})
                    content = result.model_dump(by_alias=True)["structuredContent"]
                    self.assertEqual(content["section"], section)
                    self.assertEqual(len(content["items"]), 1)
        asyncio.run(check())
