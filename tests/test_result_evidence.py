"""Evidence reconstruction and native MCP image transport, without a device."""

import asyncio
import base64
import hashlib
import importlib.util
import json
import unittest
from unittest.mock import patch

from PIL import Image

from kea2.results import ResultError, ResultSnapshot
from kea2.results.models import decode, ExperimentData, json_schema, to_dict
from kea2.results import evidence
import test_structured_results as fixtures


class TestResultEvidence(unittest.TestCase):
    write = fixtures.TestStructuredResults.write
    lines = fixtures.TestStructuredResults.lines

    def setUp(self):
        fixtures.TestStructuredResults.setUp(self)
        self.images = self.root / "output_run" / "screenshots"
        self.images.mkdir()
        for name in ("before.png", "middle.png", "after.png", "screenshot.png"):
            Image.new("RGB", (2, 2), "red").save(self.images / name)
        self.step_records = [
            self.step("Monkey", 0, {"act": "BACK"}),
            self.step("ScriptInfo", 10, {"propName": "test.a", "kind": "property", "state": "start",
                                        "startStepsCount": 10}, "before.png"),
            self.step("Script", 10, json.dumps({"method": "click", "params": [20, 30]}), "middle.png"),
            self.step("ScriptInfo", 10, {"propName": "test.invariant", "kind": "invariant",
                                        "state": "fail", "startStepsCount": 10}),
            self.step("ScriptInfo", 12, {"propName": "test.a", "kind": "property",
                                        "state": "fail", "startStepsCount": 10}, "after.png"),
            self.step("Monkey", 13, "kill_apps"),
        ]
        self.lines("output_run/steps.log", self.step_records)
        self.lines("property_exec_info_run.json", [
            {"propName": "test.a", "kind": "property", "state": "fail", "startStepsCount": 10, "tb": "AssertionError"},
            {"propName": "test.invariant", "kind": "invariant", "state": "fail", "startStepsCount": 10, "tb": "Invariant failed"},
        ])

    @staticmethod
    def step(kind, number, info, screenshot=""):
        return {"Type": kind, "MonkeyStepsCount": number, "Info": info, "Screenshot": screenshot,
                "Time": "2026-10-20T09:00:{:02}".format(number), "Activity": "Home"}

    def snapshot(self):
        return ResultSnapshot(self.task)

    def test_timeline_preserves_individual_records_and_raw_info(self):
        snapshot = self.snapshot()
        page = snapshot.query("steps", {"start_step": 10, "end_step": 10})
        self.assertEqual(page["total"], 3)
        self.assertEqual([x["id"] for x in page["items"]], ["step:2", "step:3", "step:4"])
        self.assertEqual(page["items"][1]["parameters"], [20, 30])
        self.assertIsInstance(page["items"][1]["raw"]["Info"], str)
        self.assertEqual(snapshot.query("steps")["items"][-1]["action"], "kill_apps")
        self.assertEqual(snapshot.report()["observation"]["log_duration_seconds"], 13)
        self.assertEqual(snapshot.report()["observation"]["log_record_count"], 6)
        self.assertEqual(snapshot.report()["observation"]["max_monkey_step"], 13)

    def test_executions_with_interleaved_invariant_and_context(self):
        snapshot = self.snapshot()
        execution = snapshot.query("executions", {"check_name": "test.a"})["items"][0]
        self.assertEqual(execution["start_step_id"], "step:2")
        self.assertEqual(execution["end_step_id"], "step:5")
        self.assertEqual(execution["state"], "fail")
        interval = snapshot.query("steps", {"execution_id": execution["id"]})
        self.assertEqual([x["id"] for x in interval["items"]], ["step:2", "step:3", "step:4", "step:5"])
        invariant = snapshot.query("executions", {"kind": "invariant"})["items"][0]
        self.assertIsNone(invariant["start_step_id"])
        self.assertEqual(invariant["end_step_id"], "step:4")
        detail = snapshot.finding("execution:1", snapshot.snapshot_id, context_before=2, context_after=1)
        self.assertEqual([s["id"] for s in detail["context_steps"]], ["step:3", "step:4", "step:5", "step:6"])
        self.assertEqual(len(detail["related_executions"]), 1)
        self.assertEqual(len(detail["related_artifacts"]), 3)
        decode(ExperimentData, to_dict(snapshot.to_model()))

    def test_image_and_log_reading_preserve_exact_content(self):
        snapshot = self.snapshot()
        artifact = next(a for a in snapshot.records["artifacts"] if a["relative_path"].endswith("after.png"))
        meta, raw = snapshot.artifact(artifact["id"], snapshot.snapshot_id)
        self.assertEqual(raw, (self.images / "after.png").read_bytes())
        self.assertEqual(meta["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(meta["content_type"], "image")
        source = next(a for a in snapshot.records["artifacts"] if a["relative_path"].endswith("steps.log"))
        offset, text = 0, ""
        while offset is not None:
            meta, image = snapshot.artifact(source["id"], snapshot.snapshot_id, offset, 17)
            text += meta["text"]
            offset = meta["next_offset"]
            self.assertIsNone(image)
        self.assertEqual(text, (self.root / "output_run/steps.log").read_bytes().decode("utf-8"))

    def test_missing_and_invalid_images_report_errors_without_hiding_findings(self):
        (self.images / "after.png").unlink()
        snapshot = self.snapshot()
        finding = snapshot.finding("execution:1", snapshot.snapshot_id)
        evidence = finding["finding"]["evidence"]
        self.assertEqual(next(e for e in evidence if e["relation"] == "screenshot")["status"], "unavailable")
        artifact = next(a for a in snapshot.records["artifacts"] if a["relative_path"].endswith("after.png"))
        with self.assertRaises(ResultError) as ctx:
            snapshot.artifact(artifact["id"], snapshot.snapshot_id)
        self.assertEqual(ctx.exception.code, "ARTIFACT_UNAVAILABLE")
        (self.images / "after.png").write_bytes(b"not an image")
        snapshot = self.snapshot()
        with self.assertRaises(ResultError) as ctx:
            snapshot.artifact(artifact["id"], snapshot.snapshot_id)
        self.assertEqual(ctx.exception.code, "INVALID_IMAGE")

    def test_unsafe_path_references_are_not_read(self):
        self.step_records[1]["Screenshot"] = "../../outside.png"
        self.step_records[2]["Screenshot"] = "C:\\secret.png"
        self.lines("output_run/steps.log", self.step_records)
        snapshot = self.snapshot()
        for record in snapshot.records["steps"][1:3]:
            self.assertEqual(record["evidence"][0]["status"], "unavailable")
        for path in ("../outside", "/etc/passwd", "C:\\secret.png", "file:stream"):
            with self.assertRaises(ResultError):
                snapshot._safe_artifact_path(path)
        with self.assertRaises(ResultError):
            snapshot.artifact("../outside", snapshot.snapshot_id)

    def test_same_counter_multiple_steps_is_ambiguous_for_crash(self):
        self.write("output_run/crash-dump.log",
                   "StepsCount: 10\nCrashScreen: screenshot.png\n20261020090000\ncrash:\n"
                   "// CRASH: app (pid 1)\n// crash end\n")
        snapshot = self.snapshot()
        crash = snapshot.query("findings", {"type": "crash"})["items"][0]
        self.assertEqual(crash["evidence"][0]["status"], "ambiguous")
        self.assertEqual(len(crash["evidence"][0]["candidates"]), 3)
        detail = snapshot.finding(crash["id"], snapshot.snapshot_id, context_before=5)
        self.assertEqual(detail["context_steps"], [])
        self.assertEqual(len(detail["related_artifacts"]), 1)

    def test_repeated_occurrences_not_arbitrarily_paired(self):
        with (self.root / "property_exec_info_run.json").open("a") as stream:
            stream.write(json.dumps({"propName": "test.a", "kind": "property", "state": "fail",
                                     "startStepsCount": 10, "tb": "Another failure"}) + "\n")
        snapshot = self.snapshot()
        findings = snapshot.query("findings", {"check_name": "test.a"})["items"]
        self.assertTrue(all(f["evidence"][0]["status"] == "unavailable" for f in findings))

    def test_unfinished_and_corrupt_execution_boundaries(self):
        self.lines("output_run/steps.log", self.step_records[:3])
        snapshot = self.snapshot()
        execution = snapshot.records["executions"][0]
        self.assertEqual(execution["state"], "incomplete")
        self.assertIsNone(execution["end_step_id"])
        self.assertEqual(snapshot.query("steps", {"execution_id": execution["id"]})["total"], 1)
        text = "\n".join(json.dumps(x) for x in self.step_records[:3])
        text += "\n{broken\n" + json.dumps(self.step_records[4]) + "\n"
        self.write("output_run/steps.log", text)
        snapshot = self.snapshot()
        self.assertEqual(snapshot.availability["steps"], "partial")
        executions = snapshot.records["executions"]
        self.assertEqual(len(executions), 2)
        self.assertIsNone(executions[0]["end_step_id"])
        self.assertIsNone(executions[1]["start_step_id"])

    def test_artifact_changes_invalidate_snapshot_and_direct_read(self):
        snapshot = self.snapshot()
        artifact = next(a for a in snapshot.records["artifacts"] if a["relative_path"].endswith("after.png"))
        (self.images / "after.png").write_bytes(b"changed")
        self.assertNotEqual(snapshot.snapshot_id, self.snapshot().snapshot_id)
        with self.assertRaises(ResultError) as ctx:
            snapshot.artifact(artifact["id"], snapshot.snapshot_id)
        self.assertEqual(ctx.exception.code, "STALE_SNAPSHOT")

    def test_oversized_images_and_non_utf8_logs_fail_explicitly(self):
        with patch.object(evidence, "MAX_IMAGE_BYTES", 1):
            snapshot = self.snapshot()
        artifact = next(a for a in snapshot.records["artifacts"] if a["relative_path"].endswith("after.png"))
        self.assertEqual(artifact["availability"], "too_large")
        with self.assertRaises(ResultError):
            snapshot.artifact(artifact["id"], snapshot.snapshot_id)
        (self.root / "fastbot_run.log").write_bytes(b"\xff")
        snapshot = self.snapshot()
        artifact = next(a for a in snapshot.records["artifacts"] if a["relative_path"] == "fastbot_run.log")
        with self.assertRaises(ResultError) as ctx:
            snapshot.artifact(artifact["id"], snapshot.snapshot_id)
        self.assertEqual(ctx.exception.code, "INVALID_TEXT_ENCODING")

    def test_duplicate_start_markers_do_not_invent_a_complete_execution(self):
        records = [self.step_records[1], self.step_records[1], self.step_records[4]]
        self.lines("output_run/steps.log", records)
        snapshot = self.snapshot()
        self.assertTrue(all(e["start_step_id"] is None or e["end_step_id"] is None
                            for e in snapshot.records["executions"]))
        self.assertIn("AMBIGUOUS_EXECUTION_BOUNDARY", [w["code"] for w in snapshot.warnings])

    def test_context_and_step_ranges_are_bounded(self):
        snapshot = self.snapshot()
        with self.assertRaises(ResultError):
            snapshot.finding("execution:1", snapshot.snapshot_id, context_before=21)
        with self.assertRaises(ResultError):
            snapshot.query("steps", {"start_step": True})
        with self.assertRaises(ResultError):
            snapshot.query("steps", {"execution_id": "missing"})

    def test_evidence_queries_are_read_only(self):
        def hashes():
            return {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
        before = hashes()
        snapshot = self.snapshot()
        snapshot.to_model()
        for artifact in snapshot.records["artifacts"]:
            if artifact["availability"] == "available":
                snapshot.artifact(artifact["id"], snapshot.snapshot_id)
        self.assertEqual(before, hashes())

    @unittest.skipUnless(importlib.util.find_spec("mcp") and importlib.util.find_spec("jsonschema"),
                         "requires optional MCP dependencies")
    def test_native_mcp_image_transport_and_schema(self):
        from kea2.mcp import server, task_store
        from jsonschema import Draft7Validator

        async def check():
            snapshot = self.snapshot()
            artifact = next(a for a in snapshot.records["artifacts"] if a["relative_path"].endswith("after.png"))
            with patch.object(task_store, "get_task", return_value=self.task):
                result = await server.mcp.call_tool("kea2_get_artifact", {
                    "task_id": "task", "artifact_id": artifact["id"], "snapshot_id": snapshot.snapshot_id})
            wire = result.model_dump(by_alias=True)
            self.assertFalse(wire["isError"])
            Draft7Validator(json_schema("artifact")).validate(wire["structuredContent"])
            image = next(c for c in wire["content"] if c["type"] == "image")
            self.assertEqual(base64.b64decode(image["data"]), (self.images / "after.png").read_bytes())
            self.assertEqual(image["mimeType"], "image/png")
            for section in snapshot.records:
                Draft7Validator(json_schema("query")).validate(snapshot.query(section))
        asyncio.run(check())


if __name__ == "__main__":
    unittest.main()
