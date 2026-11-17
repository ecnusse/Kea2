"""Offline contracts for the read-only result API."""

import asyncio
import hashlib
from mcp_dependencies import MCP_AVAILABLE
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kea2.results import ResultError, ResultSnapshot
from kea2.results import service
from kea2.results.models import SCHEMA_VERSION


class TestStructuredResults(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "output_run").mkdir()
        self.task = {
            "task_id": "task", "stamp": "run", "output_dir": str(self.root),
            "status": "failed", "exit_code": 3,
        }
        self.write("result_run.json", {
            "test.a": {"kind": "property", "executed": 5, "fail": 2, "error": 1},
            "test.b": {"kind": "property", "executed": 0},
            "test.invariant": {"kind": "invariant", "executed": 0, "fail": 1},
            "legacy": {"executed": 1, "error": 1},
        })
        self.lines("property_exec_info_run.json", [
            {"propName": "test.a", "state": "fail", "tb": "frame\nAssertionError: 中文",
             "startStepsCount": 10, "kind": "property"},
            {"propName": "test.a", "state": "fail", "tb": "frame\nAssertionError: 中文",
             "startStepsCount": 10, "kind": "property"},
            {"propName": "test.invariant", "state": "fail", "tb": "AssertionError",
             "startStepsCount": 10, "kind": "invariant"},
        ])
        self.coverage = {
            "stepsCount": 20, "coverage": 50.0,
            "totalActivities": ["Home", "Settings"], "testedActivities": ["Home"],
            "totalActivitiesCount": 2, "testedActivitiesCount": 1,
            "activityCountHistory": {"Home": 7},
        }
        self.lines("output_run/coverage.log", [self.coverage])
        self.lines("output_run/widget_coverage.log", [{"stepsCount": 20, "coverage": 12}])
        self.write("output_run/crash-dump.log",
                   "StepsCount: 8\nCrashScreen: screenshot.png\n20261020090000\ncrash:\n"
                   "// CRASH: com.example (pid 123)\n"
                   "// Long Msg: java.lang.Exception: broken\n// frame\n// crash end\n"
                   "20261020090100\nanr:\n// ANR: com.example (pid 456)\n"
                   "Reason: Input dispatching timed out (details)\nanr end\n")

    def write(self, path, content):
        if not isinstance(content, str):
            content = json.dumps(content)
        (self.root / path).write_text(content, encoding="utf-8")

    def lines(self, path, items):
        self.write(path, "\n".join(json.dumps(x) for x in items) + "\n")

    def snapshot(self):
        return ResultSnapshot(self.task)

    def test_summary_uses_explicit_counts_and_exit_code(self):
        report = self.snapshot().report()
        self.assertEqual(report["execution"]["status"], "completed")
        self.assertEqual(report["execution"]["finding_flags"],
                         {"property_violation": True, "crash_or_anr": True})
        stats = report["summary"]["checks"]
        self.assertEqual(stats["property"]["violated_check_count"], 1)
        self.assertEqual(stats["property"]["fail_occurrences"], 2)
        self.assertEqual(stats["invariant"]["violated_check_count"], 1)
        self.assertEqual(stats["unknown"]["count"], 1)
        self.assertEqual(report["summary"]["unique_triggered_widget_count"], 12)
        self.assertEqual(report["summary"]["activity_coverage_percent"], 50)
        self.assertEqual(report["summary"]["observed_crash_occurrences"], 1)
        self.assertEqual(report["summary"]["observed_anr_occurrences"], 1)

    def test_invariant_only_reports_failure_statistics(self):
        self.write("result_run.json", {"inv": {"kind": "invariant", "executed": None,
                    "precond_satisfied": "unused", "fail": 2, "error": 1}})
        snapshot = self.snapshot()
        row = snapshot.query("checks")["items"][0]
        for key in ("executed", "precond_satisfied", "pass_count"):
            self.assertIsNone(row[key])
        self.assertEqual(row["pass_count_basis"], "not_applicable")
        self.assertEqual((row["fail"], row["error"]), (2, 1))
        summary = snapshot.report()["summary"]["checks"]["invariant"]
        self.assertIsNone(summary["execution_count"])
        self.assertIsNone(summary["executed_check_count"])
        self.assertNotIn("FAILURES_EXCEED_EXECUTED", [w["code"] for w in snapshot.warnings])

    def test_exit_codes_and_cancelled_precedence(self):
        for code, expected in [(0, "completed"), (1, "completed"), (2, "completed"),
                               (3, "completed"), (4, "execution_error"), (-15, "execution_error")]:
            self.task["exit_code"] = code
            self.assertEqual(self.snapshot().report()["execution"]["status"], expected)
        self.task["status"] = "cancelled"
        self.assertEqual(self.snapshot().report()["execution"]["status"], "cancelled")
        self.task.update(status="running", exit_code=None)
        self.assertTrue(self.snapshot().report()["is_live"])

    def test_missing_sources_are_not_zero(self):
        for path in self.root.rglob("*"):
            if path.is_file():
                path.unlink()
        report = self.snapshot().report()
        self.assertIsNone(report["summary"]["checks"])
        self.assertIsNone(report["summary"]["observed_crash_occurrences"])
        self.assertIsNone(report["summary"]["activity_coverage_percent"])
        self.assertTrue(all(v == "missing" for v in report["availability"].values()))

    def test_empty_valid_results_are_zero(self):
        self.write("result_run.json", {})
        self.write("output_run/crash-dump.log", "")
        report = self.snapshot().report()
        self.assertEqual(report["summary"]["checks"]["property"]["count"], 0)
        self.assertEqual(report["summary"]["observed_crash_occurrences"], 0)

    def test_optional_crash_log_absence_uses_completed_run_outcome(self):
        (self.root / "output_run/crash-dump.log").unlink()
        for code in (0, 1):
            with self.subTest(code=code):
                self.task.update(status="finished", exit_code=code)
                snapshot = self.snapshot()
                report = snapshot.report()
                self.assertEqual(report["availability"]["crashes"], "missing")
                for kind in ("crash", "anr"):
                    self.assertEqual(report["summary"]["observed_" + kind + "_occurrences"], 0)
                    self.assertEqual(snapshot.query("findings", {"type": kind})["total"], 0)
                # Isolate the completeness check: this optional log alone is not a gap.
                snapshot.availability.update({k: "available" for k in snapshot.availability if k != "crashes"})
                self.assertEqual(snapshot.report()["data_completeness"], "available_sources")
        for status, code in (("finished", 2), ("finished", 3), ("failed", 4),
                             ("running", None), ("finished", None), ("cancelled", 0)):
            with self.subTest(status=status, code=code):
                self.task.update(status=status, exit_code=code)
                report = self.snapshot().report()
                self.assertIsNone(report["summary"]["observed_crash_occurrences"])
                self.assertIsNone(report["summary"]["observed_anr_occurrences"])

    def test_crash_read_failure_is_not_an_absent_optional_log(self):
        self.task.update(status="finished", exit_code=0)
        original_open = Path.open

        def read(path, *args, **kwargs):
            if path.name == "crash-dump.log":
                raise PermissionError("denied")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", read):
            report = self.snapshot().report()
        self.assertEqual(report["availability"]["crashes"], "unreadable")
        self.assertIsNone(report["summary"]["observed_crash_occurrences"])

    def test_malformed_crash_log_is_not_zero(self):
        self.task.update(status="finished", exit_code=0)
        self.write("output_run/crash-dump.log", "20261110123456\ncrash:\nincomplete")
        report = self.snapshot().report()
        self.assertEqual(report["availability"]["crashes"], "partial")
        self.assertIsNone(report["summary"]["observed_crash_occurrences"])
        self.assertIsNone(report["summary"]["observed_anr_occurrences"])

    def test_crash_records_override_negative_exit_flag(self):
        self.task.update(status="finished", exit_code=0)
        report = self.snapshot().report()
        self.assertEqual(report["summary"]["observed_crash_occurrences"], 1)
        self.assertEqual(report["summary"]["observed_anr_occurrences"], 1)

    def test_partial_json_and_jsonl_preserve_valid_records(self):
        self.write("result_run.json", '{"test.a":')
        with (self.root / "property_exec_info_run.json").open("a", encoding="utf-8") as f:
            f.write('{"propName":')
        snapshot = self.snapshot()
        self.assertIsNone(snapshot.report()["summary"]["checks"])
        self.assertEqual(snapshot.availability["checks"], "invalid")
        self.assertEqual(snapshot.availability["property_executions"], "partial")
        self.assertEqual(len(snapshot.query("findings", {"type": "property"})["items"]), 2)

    def test_invalid_typed_records_do_not_crash_or_hide_good_records(self):
        self.write("result_run.json", {"bad": {"executed": "five"}, "good": {"executed": 1}})
        self.lines("output_run/coverage.log", [self.coverage, {"stepsCount": "bad"}, []])
        snapshot = self.snapshot()
        self.assertEqual(snapshot.availability["checks"], "partial")
        self.assertEqual(snapshot.availability["activity_coverage"], "partial")
        self.assertEqual(snapshot.records["activities"][0]["source"]["line"], 1)
        self.assertEqual(snapshot.report()["summary"]["activity_coverage_percent"], 50)
        self.assertEqual(snapshot.query("checks")["total"], 1)

    def test_pagination_and_filters(self):
        snapshot = self.snapshot()
        result = snapshot.query("checks", limit=1)
        names = [result["items"][0]["name"]]
        while result["next_cursor"]:
            result = self.snapshot().query("checks", cursor=result["next_cursor"], limit=1)
            names.extend(r["name"] for r in result["items"])
        self.assertEqual(len(names), 4)
        self.assertEqual(len(set(names)), 4)
        self.assertEqual(snapshot.query("checks", {"has_findings": False})["total"], 1)
        self.assertEqual(snapshot.query("activities", {"covered": False})["items"][0]["name"], "Settings")

    def test_cursor_bound_to_source_and_query(self):
        page = self.snapshot().query("checks", limit=1)
        with self.assertRaises(ResultError) as ctx:
            self.snapshot().query("findings", cursor=page["next_cursor"])
        self.assertEqual(ctx.exception.code, "INVALID_CURSOR")
        self.write("result_run.json", {})
        with self.assertRaises(ResultError) as ctx:
            self.snapshot().query("checks", cursor=page["next_cursor"])
        self.assertEqual(ctx.exception.code, "STALE_SNAPSHOT")

    def test_trace_pagination_preserves_unicode_and_duplicate_occurrences(self):
        snapshot = self.snapshot()
        findings = snapshot.query("findings", {"type": "property"})["items"]
        self.assertEqual(len(findings), 2)
        self.assertNotEqual(findings[0]["id"], findings[1]["id"])
        offset, text = 0, ""
        while offset is not None:
            detail = snapshot.finding(findings[0]["id"], snapshot.snapshot_id, offset, 3)
            text += detail["trace"]
            offset = detail["next_offset"]
        self.assertEqual(text, "frame\nAssertionError: 中文")
        self.assertNotIn("trace", findings[0])

    def test_stale_finding_rejected(self):
        snapshot = self.snapshot()
        self.task["status"] = "cancelled"
        with self.assertRaises(ResultError) as ctx:
            self.snapshot().finding("execution:1", snapshot.snapshot_id)
        self.assertEqual(ctx.exception.code, "STALE_SNAPSHOT")

    def test_crash_and_anr_keep_raw_evidence_and_process_identity(self):
        snapshot = self.snapshot()
        crash = snapshot.query("findings", {"type": "crash"})["items"][0]
        self.assertEqual(crash["pid"], 123)
        self.assertEqual(crash["process_name"], "com.example")
        self.assertEqual(crash["monkey_step"], 8)
        self.assertEqual(crash["screenshot_reference"], "screenshot.png")
        detail = snapshot.finding(crash["id"], snapshot.snapshot_id)
        self.assertIn("// Long Msg:", detail["trace"])
        anr = snapshot.query("findings", {"type": "anr"})["items"][0]
        self.assertIsNone(anr["monkey_step"])
        self.assertIn("(details)", anr["description"])

    def test_incomplete_crash_record_is_not_silently_accepted(self):
        with (self.root / "output_run/crash-dump.log").open("a") as f:
            f.write("20261020100000\ncrash:\n// partial")
        snapshot = self.snapshot()
        self.assertEqual(snapshot.availability["crashes"], "partial")
        self.assertEqual(snapshot.report()["summary"]["observed_crash_occurrences"], 1)

    def test_file_limit_is_explicit(self):
        with patch.object(service, "MAX_SOURCE_BYTES", 8):
            snapshot = self.snapshot()
        self.assertEqual(snapshot.availability["checks"], "too_large")
        self.assertIsNone(snapshot.report()["summary"]["checks"])

    def test_many_invalid_records_have_bounded_explicit_warnings(self):
        self.write("output_run/coverage.log", "{bad json\n" * 100)
        report = self.snapshot().report()
        self.assertTrue(report["warnings_truncated"])
        self.assertEqual(len(report["warnings"]), 50)
        self.assertGreaterEqual(report["warning_count"], 100)

    def test_nonfinite_json_is_unavailable(self):
        self.write("result_run.json", '{"bad": {"executed": NaN}}')
        report = self.snapshot().report()
        self.assertEqual(report["availability"]["checks"], "invalid")
        self.assertIsNone(report["summary"]["checks"])

    def test_invalid_stamp_cannot_escape_root(self):
        self.task["stamp"] = "../other"
        with self.assertRaises(ResultError) as ctx:
            self.snapshot()
        self.assertEqual(ctx.exception.code, "INVALID_STAMP")

    def test_resolved_paths_must_stay_in_result_directory(self):
        original = Path.resolve
        target = self.root / "result_run.json"

        def resolve(path, *args, **kwargs):
            if path == target:
                return self.root.parent / "outside.json"
            return original(path, *args, **kwargs)

        with patch.object(Path, "resolve", resolve):
            snapshot = self.snapshot()
        self.assertEqual(snapshot.availability["checks"], "invalid")
        self.assertIn("PATH_OUTSIDE_RESULT_DIRECTORY", [w["code"] for w in snapshot.warnings])

    def test_queries_do_not_modify_any_artifacts(self):
        self.write("bug_report.html", "<html>existing report</html>")
        self.write("output_run/screenshot.png", "original screenshot placeholder")

        def state():
            return {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                    for p in self.root.rglob("*") if p.is_file()}

        before = state()
        snapshot = self.snapshot()
        snapshot.report()
        for section in service.SECTIONS:
            snapshot.query(section)
        snapshot.finding("execution:1", snapshot.snapshot_id)
        self.assertEqual(before, state())

    def test_statistics_match_existing_html_collector(self):
        from collections import deque
        from kea2.report.bug_report_generator import BugReportGenerator

        self.write("bug_report_config.json", {"log_stamp": "run", "test_time": "2026-10-20"})
        self.lines("output_run/steps.log", [
            {"Type": "Monkey", "Info": {"act": "BACK"}, "Screenshot": "",
             "MonkeyStepsCount": 1, "Time": "2026-10-20T09:00:00"},
            {"Type": "Monkey", "Info": {"act": "BACK"}, "Screenshot": "",
             "MonkeyStepsCount": 20, "Time": "2026-10-20T09:01:00"},
        ])
        generator = BugReportGenerator(self.root)
        generator.screenshots = deque()
        generator._screenshot_id_by_filename = {}
        html_data = generator._collect_test_data()
        self.assertIsNotNone(html_data)
        structured = self.snapshot().report()["summary"]
        stats = structured["checks"]
        self.assertEqual(html_data["bugs_found"],
                         stats["property"]["violated_check_count"] + stats["unknown"]["violated_check_count"])
        self.assertEqual(html_data["invariant_violations_count"], stats["invariant"]["violated_check_count"])
        self.assertEqual(html_data["coverage"], structured["activity_coverage_percent"])
        self.assertEqual(html_data["widget_coverage_count"], structured["unique_triggered_widget_count"])
        self.assertEqual(len(html_data["crash_events"]), structured["observed_crash_occurrences"])
        self.assertEqual(len(html_data["anr_events"]), structured["observed_anr_occurrences"])

    def test_invalid_queries_return_typed_errors(self):
        snapshot = self.snapshot()
        for kwargs in [
            {"section": "images"}, {"section": "checks", "limit": 0},
            {"section": "checks", "filters": {"has_findings": "yes"}},
            {"section": "checks", "filters": {"anything": 1}},
            {"section": "checks", "cursor": "not a cursor"},
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ResultError):
                snapshot.query(**kwargs)





@unittest.skipUnless(MCP_AVAILABLE, "requires optional MCP dependencies")
class TestStructuredMcp(unittest.TestCase):
    setUp = TestStructuredResults.setUp
    write = TestStructuredResults.write
    lines = TestStructuredResults.lines

    def test_registered_tools_serialize_through_mcp(self):
        from kea2.mcp import server, task_store

        async def check():
            names = {tool.name for tool in await server.mcp.list_tools()}
            self.assertTrue({"kea2_get_report", "kea2_query_report", "kea2_get_finding"} <= names)
            result = await server.mcp.call_tool("kea2_get_report", {"task_id": "task"})
            wire = result.model_dump(by_alias=True)
            self.assertEqual(wire["structuredContent"]["schema_version"], SCHEMA_VERSION)
            self.assertEqual(wire["structuredContent"]["summary"]["observed_crash_occurrences"], 1)
            json.dumps(wire, allow_nan=False)

        with patch.object(task_store, "get_task", return_value=self.task):
            asyncio.run(check())

    def test_tools_return_structured_data_and_errors(self):
        from kea2.mcp import server, task_store
        with patch.object(task_store, "get_task", return_value=self.task):
            report = asyncio.run(server.kea2_get_report("task"))
            self.assertEqual(report["execution"]["status"], "completed")
            query = asyncio.run(server.kea2_query_report("task", "findings", limit=1))
            detail = asyncio.run(server.kea2_get_finding(
                "task", query["items"][0]["id"], query["snapshot_id"]))
            self.assertIn("AssertionError", detail["trace"])
            bad = asyncio.run(server.kea2_query_report("task", "unsupported"))
            self.assertEqual(bad["error"]["code"], "INVALID_SECTION")
        with patch.object(task_store, "get_task", return_value=None):
            missing = asyncio.run(server.kea2_get_report("missing"))
            self.assertEqual(missing["error"]["code"], "TASK_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
