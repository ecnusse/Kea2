"""MCP must never append stdout to the file owned by Fastbot."""
import asyncio
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

MCP_AVAILABLE = (importlib.util.find_spec("mcp") is not None
                 and importlib.util.find_spec("aiofiles") is not None)
if MCP_AVAILABLE:
    from kea2.mcp import runner


@unittest.skipUnless(MCP_AVAILABLE, "requires optional MCP dependencies")
class TestMcpLogging(unittest.TestCase):
    def test_subprocess_output_is_isolated_from_fastbot(self):
        async def check(tmp):
            output = Path(tmp) / "res_logging"
            output.mkdir()
            fastbot = output / "fastbot_logging.log"
            original = "▌ Fastbot 日志\n".encode("utf-8")
            fastbot.write_bytes(original)
            stream = asyncio.StreamReader()
            # Include non-UTF-8 bytes: capture must preserve bytes, not decode.
            captured = b"Python stdout\nTraceback stderr\n\x96\n"
            stream.feed_data(captured)
            stream.feed_eof()
            proc = SimpleNamespace(stdout=stream)
            finished = asyncio.Event()
            writer = runner._stream_to_file

            async def observed_writer(source, target):
                try:
                    await writer(source, target)
                finally:
                    finished.set()

            with patch.object(runner.asyncio, "create_subprocess_exec",
                              new_callable=AsyncMock, return_value=proc) as spawn, \
                    patch.object(runner, "_stream_to_file", side_effect=observed_writer), \
                    patch.object(runner, "getProjectRoot", return_value=Path(tmp)):
                returned, out_dir, log_file, result_file = await runner.launch_kea2_subprocess(
                    {"serial": "device", "packages": ["app"], "output_dir": tmp}, "logging")
                await asyncio.wait_for(finished.wait(), timeout=5)
            self.assertIs(returned, proc)
            self.assertEqual(out_dir, output)
            self.assertEqual(log_file, output / "kea2_logging.log")
            self.assertEqual(result_file, output / "result_logging.json")
            self.assertEqual(log_file.read_bytes(), captured)
            self.assertEqual(fastbot.read_bytes(), original)
            self.assertEqual(spawn.call_args.kwargs["stderr"], asyncio.subprocess.STDOUT)

        with tempfile.TemporaryDirectory() as tmp:
            asyncio.run(check(tmp))


if __name__ == "__main__":
    unittest.main()
