"""Check portable skill references and execute its examples through real MCP dispatch.

These tests check interface compatibility, not an LLM's compliance or analysis quality.
"""

import asyncio
import importlib.util
from mcp_dependencies import MCP_AVAILABLE
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from kea2.results import ResultSnapshot
from kea2.results.models import SCHEMA_VERSION
import test_result_evidence as fixtures

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "kea2-result-analysis"


class TestAnalysisSkillReferences(unittest.TestCase):
    def test_skill_contract_and_local_references(self):
        entry = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        contract = re.search(r'result-contract: "([^"]+)"', entry).group(1)
        self.assertEqual(contract, SCHEMA_VERSION,
                         "Review skill semantics when changing result contracts")
        for path in SKILL.rglob("*.md"):
            for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding="utf-8")):
                target = (path.parent / link).resolve()
                self.assertIn(SKILL.resolve(), target.parents)
                self.assertTrue(target.is_file(), str(target))


@unittest.skipUnless(MCP_AVAILABLE and importlib.util.find_spec("jsonschema"),
                     "requires optional MCP and JSON Schema validator")
class TestAnalysisSkillExamples(unittest.TestCase):
    setUp = fixtures.TestResultEvidence.setUp
    write = fixtures.TestResultEvidence.write
    lines = fixtures.TestResultEvidence.lines
    step = staticmethod(fixtures.TestResultEvidence.step)

    def test_examples_validate_and_execute_against_registered_tools(self):
        from jsonschema import validate
        from kea2.mcp import server, task_store

        self.write("options.json", {"running_mins": 5})
        self.write("output_run/widget_coverage_report.txt",
                   "activity:Home|class:KEY_BACK|resourceId:KEY_BACK|content-desc:KEY_BACK|")
        snapshot = ResultSnapshot(self.task)
        replacements = {
            "$task_id": self.task["task_id"], "$snapshot_id": snapshot.snapshot_id,
            "$finding_id": snapshot.records["findings"][0]["id"],
            "$execution_id": snapshot.records["executions"][0]["id"],
            "$artifact_id": next(a["id"] for a in snapshot.records["artifacts"]
                                 if a["kind"] == "screenshot" and a["availability"] == "available"),
        }

        def resolve(value):
            if isinstance(value, dict):
                return {k: resolve(v) for k, v in value.items()}
            if isinstance(value, str) and value.startswith("$"):
                return replacements[value]
            return value

        async def check():
            registered = {t.name: t for t in await server.mcp.list_tools()}
            examples = json.loads((SKILL / "references" / "query-examples.json").read_text(encoding="utf-8"))
            with patch.object(task_store, "get_task", return_value=self.task):
                for example in examples:
                    name, args = example["tool"], resolve(example["arguments"])
                    with self.subTest(tool=name, section=args.get("section")):
                        validate(args, registered[name].input_schema)
                        result = await server.mcp.call_tool(name, args)
                        data = result.model_dump(by_alias=True)
                        self.assertFalse(data.get("isError"), data)
                        content = data["structuredContent"]
                        self.assertNotIn("error", content)
                        if name == "kea2_query_report":
                            self.assertEqual(content["section"], args["section"])
                        elif name == "kea2_get_artifact":
                            self.assertTrue(any(c["type"] == "image" for c in data["content"]))

        asyncio.run(check())
