"""Task discovery uses persisted metadata and never chooses an analysis target."""
import asyncio
from mcp_dependencies import MCP_AVAILABLE
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kea2.mcp import task_store


class TestTaskListing(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        patched = patch.object(task_store, "DB_PATH", Path(temp.name) / "tasks.db")
        patched.start()
        self.addCleanup(patched.stop)

    def populate(self):
        task_store.init_db()
        for task_id, status, date in [("a", "finished", "2026-01-01"),
                                      ("b", "failed", "2026-01-02"),
                                      ("c", "finished", "2026-01-02")]:
            task_store.create_task(task_id, task_id, status=status, created_at=date,
                                   packages=["example.app"], extra_json={"private": "unused"})

    def test_empty_database(self):
        page = task_store.list_tasks_page()
        self.assertEqual(page["tasks"], [])
        self.assertEqual(page["total"], 0)
        self.assertIsNone(page["next_offset"])

    def test_order_filter_pagination_and_projection(self):
        self.populate()
        first = task_store.list_tasks_page(limit=2)
        self.assertEqual([t["task_id"] for t in first["tasks"]], ["c", "b"])
        self.assertEqual(first["total"], 3)
        second = task_store.list_tasks_page(limit=2, offset=first["next_offset"])
        self.assertEqual([t["task_id"] for t in second["tasks"]], ["a"])
        self.assertIsNone(second["next_offset"])
        filtered = task_store.list_tasks_page(status="finished")
        self.assertEqual(filtered["total"], 2)
        self.assertEqual([t["task_id"] for t in filtered["tasks"]], ["c", "a"])
        self.assertEqual(first["tasks"][0]["packages"], ["example.app"])
        self.assertNotIn("extra_json", first["tasks"][0])
        self.assertEqual(task_store.list_tasks_page(offset=20)["tasks"], [])
        self.assertEqual(len(task_store.list_tasks()), 3)

    def test_invalid_parameters(self):
        for kwargs in ({"status": "bogus"}, {"limit": 0}, {"limit": 101},
                       {"limit": True}, {"offset": -1}, {"offset": 1.5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                task_store.list_tasks_page(**kwargs)

    @unittest.skipUnless(MCP_AVAILABLE, "requires MCP")
    def test_registered_tool_and_errors(self):
        from kea2.mcp import server
        self.populate()

        async def check():
            registered = {t.name: t for t in await server.mcp.list_tools()}
            self.assertIn("kea2_list_tasks", registered)
            result = await server.mcp.call_tool("kea2_list_tasks", {"limit": 1})
            data = result.model_dump(by_alias=True)["structuredContent"]
            self.assertEqual(data["tasks"][0]["task_id"], "c")
            self.assertEqual(data["next_offset"], 1)
            for kwargs, code in [({"status": "invalid"}, "INVALID_STATUS"),
                                 ({"limit": 0}, "INVALID_LIMIT"),
                                 ({"offset": -1}, "INVALID_OFFSET")]:
                response = await server.kea2_list_tasks(**kwargs)
                self.assertEqual(response["error"]["code"], code)

        asyncio.run(check())
