"""Validate real parser output against the independent Python/JSON contract."""

import asyncio
import copy
import importlib.util
from mcp_dependencies import MCP_AVAILABLE
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from kea2.results import ResultSnapshot
from kea2.results.models import (
    SCHEMA_VERSION, ActivityTrend, AppFinding, CheckRecord, ContractError,
    EvidenceLink, ExperimentData, FindingResponse, QueryResponse, ReportResponse,
    WidgetTrend, decode, json_schema, to_dict,
)
import test_structured_results as fixtures


class TestResultModels(unittest.TestCase):
    setUp = fixtures.TestStructuredResults.setUp
    write = fixtures.TestStructuredResults.write
    lines = fixtures.TestStructuredResults.lines

    def snapshot(self):
        return ResultSnapshot(self.task)

    def test_parser_builds_canonical_model_and_round_trips(self):
        snapshot = self.snapshot()
        model = snapshot.to_model()
        self.assertIsInstance(model, ExperimentData)
        self.assertIsInstance(model.report, ReportResponse)
        self.assertIsInstance(model.checks[0], CheckRecord)
        wire = to_dict(model)
        self.assertEqual(wire, to_dict(decode(ExperimentData, json.loads(json.dumps(wire)))))
        for section in ("steps", "executions", "widgets", "diagnostics",
                        "observation", "property_execution_trend", "finding_groups"):
            self.assertIsNone(wire[section])
        self.assertTrue(wire["artifacts"])
        self.assertNotIn("line", wire["checks"][0]["source"])
        self.assertEqual(wire["checks"][0]["source"]["key"], "test.a")
        self.assertEqual(wire["report"]["schema_version"], SCHEMA_VERSION)

    def test_published_schema_and_example_match_runtime_contract(self):
        docs = Path(__file__).resolve().parents[1] / "docs"
        published = json.loads((docs / "structured_result.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(published, json_schema("experiment"))
        example = json.loads((docs / "examples" / "structured_result_v1.5.json").read_text(encoding="utf-8"))
        self.assertEqual(example, to_dict(decode(ExperimentData, example)))

    def test_required_nullable_and_unknown_fields_are_distinct(self):
        original = self.snapshot().report()
        for mutate in (
            lambda x: x.pop("summary"),
            lambda x: x["summary"].update(undocumented=1),
            lambda x: x["summary"].update(checks=[]),
            lambda x: x["execution"].update(status="successful"),
            lambda x: x.update(schema_version="1.0"),
        ):
            value = copy.deepcopy(original)
            mutate(value)
            with self.assertRaises(ContractError):
                decode(ReportResponse, value)
        original["summary"]["checks"] = None
        self.assertIsNone(decode(ReportResponse, original).summary.checks)

    def test_strict_types_and_metric_units(self):
        record = self.snapshot().records["checks"][0]
        for value in (True, "5", 1.5, -1):
            with self.subTest(value=value), self.assertRaises(ContractError):
                decode(CheckRecord, dict(record, executed=value))
        source = {"artifact": "coverage.log", "line": 1}
        for cls, metric, value in (
            (ActivityTrend, "activity_coverage_percent", 101),
            (ActivityTrend, "activity_coverage_percent", float("nan")),
            (WidgetTrend, "unique_triggered_widget_count", 1.5),
            (WidgetTrend, "activity_coverage_percent", 10),
        ):
            with self.subTest(metric=metric, value=value), self.assertRaises(ContractError):
                decode(cls, {"metric": metric, "monkey_step": 1, "value": value, "raw": {}, "source": source})

    def test_section_discriminator_requires_matching_items(self):
        snapshot = self.snapshot()
        page = snapshot.query("checks")
        page["section"] = "findings"
        with self.assertRaises(ContractError):
            decode(QueryResponse, page)
        crash = snapshot.query("findings", {"type": "crash"})["items"][0]
        crash["type"] = "property"
        with self.assertRaises(ContractError):
            decode(AppFinding, crash)

    def test_invalid_derived_statistics_and_trace_ranges_rejected(self):
        snapshot = self.snapshot()
        record = dict(snapshot.records["checks"][0], pass_count=100)
        with self.assertRaises(ContractError):
            decode(CheckRecord, record)
        response = snapshot.finding("execution:1", snapshot.snapshot_id, limit=3)
        response["next_offset"] = 10
        with self.assertRaises(ContractError):
            decode(FindingResponse, response)

    def test_full_model_section_counts_must_match(self):
        wire = to_dict(self.snapshot().to_model())
        wire["checks"].pop()
        with self.assertRaises(ContractError):
            decode(ExperimentData, wire)

    def test_full_trace_and_group_references_must_match_findings(self):
        wire = to_dict(self.snapshot().to_model())
        wire["traces"][0]["text"] += "extra"
        with self.assertRaises(ContractError):
            decode(ExperimentData, wire)
        wire = to_dict(self.snapshot().to_model())
        wire["finding_groups"] = [{"id": "group1", "occurrence_ids": ["missing"],
                                   "algorithm_version": "1", "grouping_basis": "exact trace"}]
        with self.assertRaises(ContractError):
            decode(ExperimentData, wire)
    def test_evidence_association_states_and_targets(self):
        base = {"relation": "screenshot", "status": "unavailable", "target_id": None,
                "candidates": [], "reason": "Not collected"}
        decode(EvidenceLink, base)
        for changes in (
            {"status": "resolved"}, {"target_id": "image1"},
            {"status": "ambiguous", "candidates": ["image1"]},
        ):
            with self.assertRaises(ContractError):
                decode(EvidenceLink, dict(base, **changes))
        wire = to_dict(self.snapshot().to_model())
        link = dict(base, status="resolved", target_id="image1", reason=None)
        wire["findings"][0]["evidence"] = [link]
        with self.assertRaises(ContractError):
            decode(ExperimentData, wire)
        wire["artifacts"] = [{"id": "image1", "kind": "screenshot",
                              "relative_path": "screenshots/1.png", "mime_type": "image/png",
                              "size_bytes": 50, "availability": "available"}]
        wire["report"]["sections"]["artifacts"]["record_count"] = 1
        decode(ExperimentData, wire)
        wire["artifacts"][0]["kind"] = "log"
        with self.assertRaises(ContractError):
            decode(ExperimentData, wire)

    def test_execution_requires_existing_step_ids(self):
        wire = to_dict(self.snapshot().to_model())
        wire["executions"] = [{"id": "exec1", "check_name": "test.a", "kind": "property",
                               "state": "incomplete", "start_step_id": "step1", "end_step_id": None,
                               "evidence": [], "source": {"artifact": "steps.log", "line": 1}}]
        with self.assertRaises(ContractError):
            decode(ExperimentData, wire)
        wire["steps"] = [{"id": "step1", "monkey_step": 1, "time_raw": None,
                         "type": "ScriptInfo", "activity": None, "action": None,
                         "parameters": None, "source": {"artifact": "steps.log", "line": 1},
                         "evidence": [], "raw": {}}]
        wire["report"]["sections"]["steps"]["record_count"] = 1
        wire["report"]["sections"]["executions"]["record_count"] = 1
        decode(ExperimentData, wire)

    def test_raw_extension_fields_remain_json_and_do_not_mutate_input(self):
        value = copy.deepcopy(self.snapshot().records["checks"][0])
        value["raw"]["future_field"] = {"values": [1, "text", None]}
        model = decode(CheckRecord, value)
        model.raw["future_field"]["values"].append("new")
        self.assertEqual(len(value["raw"]["future_field"]["values"]), 3)
        value["raw"]["not_json"] = object()
        with self.assertRaises(ContractError):
            decode(CheckRecord, value)

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "optional independent JSON Schema validator")
    def test_generated_json_schema_accepts_all_real_responses(self):
        from jsonschema import Draft7Validator

        snapshot = self.snapshot()
        fixtures = {
            "experiment": [to_dict(snapshot.to_model())],
            "report": [snapshot.report()],
            "query": [snapshot.query(section) for section in snapshot.records],
            "finding": [snapshot.finding(f["id"], snapshot.snapshot_id)
                        for f in snapshot.records["findings"]],
            "error": [{"error": {"code": "TEST", "message": "test"}}],
        }
        for document, examples in fixtures.items():
            schema = json_schema(document)
            Draft7Validator.check_schema(schema)
            validator = Draft7Validator(schema)
            for example in examples:
                with self.subTest(document=document):
                    validator.validate(example)
        bad = snapshot.report()
        bad["summary"]["unique_triggered_widget_count"] = "12%"
        self.assertFalse(Draft7Validator(json_schema("report")).is_valid(bad))

    @unittest.skipUnless(MCP_AVAILABLE, "requires optional MCP")
    def test_schema_tool_and_contract_errors_through_mcp(self):
        from kea2.mcp import server, task_store

        async def check():
            schema_result = await server.mcp.call_tool("kea2_get_result_schema", {"document": "report"})
            schema = schema_result.model_dump(by_alias=True)["structuredContent"]
            self.assertEqual(schema, json_schema("report"))
            bad = await server.kea2_get_result_schema("invalid")
            self.assertEqual(bad["error"]["code"], "INVALID_SCHEMA_DOCUMENT")
            with patch.object(task_store, "get_task", return_value=dict(self.task, packages="not-an-array")):
                result = await server.kea2_get_report("task")
            self.assertEqual(result["error"]["code"], "RESULT_CONTRACT_ERROR")

        asyncio.run(check())


if __name__ == "__main__":
    unittest.main()
