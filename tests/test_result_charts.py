"""Offline trend rendering, source preservation and MCP image transport."""
import asyncio
import base64
import hashlib
import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp_dependencies import MCP_AVAILABLE
from kea2.results import ResultSnapshot, ResultError
from kea2.results.charts import METRICS
import test_result_evidence as fixtures


@unittest.skipUnless(importlib.util.find_spec("matplotlib"), "requires optional chart dependencies")
class TestResultCharts(unittest.TestCase):
    setUp = fixtures.TestResultEvidence.setUp
    write = fixtures.TestResultEvidence.write
    lines = fixtures.TestResultEvidence.lines
    step = staticmethod(fixtures.TestResultEvidence.step)

    def test_all_charts_preserve_sources_and_snapshot(self):
        from PIL import Image
        self.write("bug_report.html", "original HTML")
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        snapshot = ResultSnapshot(self.task)
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        original = FigureCanvasAgg.print_png

        def capture(canvas, *args, **kwargs):
            for axis in canvas.figure.axes:
                self.assertEqual(tuple(axis.lines[0].get_xydata()[0]), (0, 0))
                self.assertEqual(axis.get_xlim()[0], 0)
            return original(canvas, *args, **kwargs)

        for metric in METRICS:
            with self.subTest(metric=metric):
                with patch.object(FigureCanvasAgg, "print_png", capture):
                    metadata, content = snapshot.trend_chart(metric, snapshot.snapshot_id)
                self.assertTrue(metadata["origin_added"])
                self.assertEqual(metadata["status"], "available")
                self.assertEqual(metadata["sample_count"], 1)
                self.assertEqual(metadata["rendered_sample_count"], 1)
                self.assertEqual(Image.open(io.BytesIO(content)).size, (1400, 350))
                self.assertEqual(Path(metadata["image_path"]).read_bytes(), content)
                self.assertEqual(metadata["html_report_path"], str(self.root / "bug_report.html"))
                self.assertEqual(metadata["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(ResultSnapshot(self.task).snapshot_id, snapshot.snapshot_id)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_activity_chart_uses_both_recorded_series_and_adaptive_axes(self):
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        self.lines("output_run/coverage.log", [
            dict(self.coverage, stepsCount=25, coverage=7.14, testedActivitiesCount=1),
            dict(self.coverage, stepsCount=50, coverage=10, testedActivitiesCount=2)])
        snapshot = ResultSnapshot(self.task)
        original = FigureCanvasAgg.print_png
        observed = {}

        def capture(canvas, *args, **kwargs):
            left, right = canvas.figure.axes
            observed.update(left=list(left.lines[0].get_ydata()), right=list(right.lines[0].get_ydata()),
                            limits=(left.get_ylim()[1], right.get_ylim()[1]))
            return original(canvas, *args, **kwargs)

        with patch.object(FigureCanvasAgg, "print_png", capture):
            metadata, _ = snapshot.trend_chart("activity_coverage_percent", snapshot.snapshot_id)
        self.assertEqual(observed["left"], [0, 7.14, 10])
        self.assertEqual(observed["right"], [0, 1, 2])
        self.assertAlmostEqual(observed["limits"][0], 10.5)
        self.assertAlmostEqual(observed["limits"][1], 2.1)
        self.assertEqual(metadata["secondary_y_label"], "Tested Activities")
        self.assertIn("_v4_", metadata["image_path"])

    def test_no_data_and_no_properties_do_not_fabricate_images(self):
        self.write("result_run.json", {})
        (self.root / "output_run/widget_coverage.log").unlink()
        snapshot = ResultSnapshot(self.task)
        metadata, content = snapshot.trend_chart("property_execution_trend", snapshot.snapshot_id)
        self.assertEqual(metadata["status"], "not_applicable")
        self.assertIsNone(content)
        metadata, content = snapshot.trend_chart("unique_triggered_widget_count", snapshot.snapshot_id)
        self.assertEqual(metadata["status"], "unavailable")
        self.assertIsNone(metadata["html_report_path"])
        self.assertIsNone(content)
        self.assertFalse((self.root / "mcp_charts").exists())

    def test_stale_invalid_partial_and_export_failure(self):
        snapshot = ResultSnapshot(self.task)
        with self.assertRaises(ResultError) as error:
            snapshot.trend_chart("../path", snapshot.snapshot_id)
        self.assertEqual(error.exception.code, "INVALID_METRIC")
        with self.assertRaises(ResultError) as error:
            snapshot.trend_chart("activity_coverage_percent", "old")
        self.assertEqual(error.exception.code, "STALE_SNAPSHOT")
        self.write("output_run/widget_coverage.log",
                   '{"stepsCount":20,"coverage":12}\ninvalid\n{"stepsCount":5,"coverage":4}\n')
        snapshot = ResultSnapshot(self.task)
        with patch("kea2.results.charts.os.replace", side_effect=PermissionError("read only")):
            metadata, content = snapshot.trend_chart("unique_triggered_widget_count", snapshot.snapshot_id)
        self.assertEqual(metadata["source_availability"], "partial")
        self.assertEqual(metadata["sample_count"], 2)
        self.assertEqual(metadata["counter_reset_count"], 1)
        self.assertIsNone(metadata["image_path"])
        self.assertTrue(content.startswith(b"\x89PNG"))
        self.assertFalse(list((self.root / "mcp_charts").glob("*.tmp")))

    @unittest.skipUnless(MCP_AVAILABLE, "requires optional MCP dependencies")
    def test_registered_tool_returns_native_image_and_task_errors(self):
        from kea2.mcp import server, task_store
        snapshot = ResultSnapshot(self.task)

        async def check():
            with patch.object(task_store, "get_task", return_value=self.task):
                result = await server.mcp.call_tool("kea2_get_trend_chart", {
                    "task_id": "task", "metric": "activity_coverage_percent",
                    "snapshot_id": snapshot.snapshot_id})
                wire = result.model_dump(by_alias=True)
                self.assertFalse(wire["isError"])
                self.assertIsNone(wire["structuredContent"])
                self.assertEqual([c["type"] for c in wire["content"]], ["text", "image"])
                metadata = json.loads(wire["content"][0]["text"])
                self.assertEqual(hashlib.sha256(base64.b64decode(wire["content"][1]["data"])).hexdigest(),
                                 metadata["sha256"])
            with patch.object(task_store, "get_task", return_value=None):
                result = await server.kea2_get_trend_chart("missing", "activity_coverage_percent", "id")
                self.assertTrue(result.is_error)
                self.assertEqual(result.structured_content["error"]["code"], "TASK_NOT_FOUND")
            with patch.object(task_store, "get_task", return_value=dict(self.task, task_kind="hybrid")):
                result = await server.kea2_get_trend_chart("task", "activity_coverage_percent", "id")
                self.assertEqual(result.structured_content["error"]["code"], "CHILD_TASK_REQUIRED")

        asyncio.run(check())
