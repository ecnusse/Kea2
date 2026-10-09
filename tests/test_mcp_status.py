"""Offline regression tests for non-destructive MCP status queries."""
import asyncio
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MCP_AVAILABLE = (importlib.util.find_spec("mcp") is not None
                 and importlib.util.find_spec("aiofiles") is not None)
if MCP_AVAILABLE:
    from kea2.mcp import server, task_store


@unittest.skipUnless(MCP_AVAILABLE, "requires the optional MCP dependencies")
class TestMcpStatus(unittest.TestCase):
    def test_invalid_pid(self):
        for pid in (None, 0, -1):
            with self.subTest(pid=pid):
                self.assertFalse(server._process_alive(pid))

    def test_terminal_tasks_do_not_probe_old_pid(self):
        cases = [("finished", None, "finished"), ("failed", None, "failed"),
                 ("cancelled", None, "cancelled"), ("running", 0, "finished"),
                 ("running", 1, "failed")]
        for status, exit_code, expected in cases:
            with self.subTest(status=status, exit_code=exit_code):
                rec = {"status": status, "exit_code": exit_code, "pid": 12345}
                with patch.object(task_store, "get_task", return_value=rec), \
                        patch.object(server, "_process_alive") as probe:
                    result = asyncio.run(server.kea2_get_status("terminal"))
                self.assertEqual(result["status"], expected)
                self.assertEqual(result["phase"], "done")
                probe.assert_not_called()

    def test_repeated_status_queries_leave_child_running(self):
        # A readiness handshake ensures we test a fully initialized child.
        # Exit on stdin EOF, so the test does not need to send any signals.
        child = subprocess.Popen(
            [sys.executable, "-u", "-c",
             "import sys; print('ready', flush=True); sys.stdin.read()"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(child.stdout.readline().strip(), "ready")
            with tempfile.TemporaryDirectory() as tmp, \
                    patch.object(task_store, "DB_PATH", Path(tmp) / "tasks.db"):
                task_store.init_db()
                task_store.create_task(task_id="live", stamp="live",
                                       status="running", pid=child.pid)
                for _ in range(10):
                    # Prevent a future regression from signalling this test's
                    # console; the real Windows process API is still exercised.
                    if os.name == "nt":
                        with patch.object(server.os, "kill", side_effect=AssertionError(
                                "Windows status checks must not send signals")):
                            result = asyncio.run(server.kea2_get_status("live"))
                    else:
                        result = asyncio.run(server.kea2_get_status("live"))
                    self.assertEqual(result["phase"], "running")
                    self.assertIsNone(child.poll())
                child.stdin.close()
                self.assertEqual(child.wait(timeout=10), 0)
                self.assertFalse(server._process_alive(child.pid))
        finally:
            if child.stdin and not child.stdin.closed:
                child.stdin.close()
            try:
                child.wait(timeout=10)
            finally:
                child.stdout.close()
                child.stderr.close()


if __name__ == "__main__":
    unittest.main()
