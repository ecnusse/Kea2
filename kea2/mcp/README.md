# Kea2 MCP Server

This module provides a local MCP server for Kea2. It enables AI clients
(for example Claude Desktop, Claude Code, and Cursor) to trigger Kea2 test
tasks with natural-language requests.

## Deployment model

Kea2 MCP runs in **local STDIO mode**:

- The AI client launches `kea2 mcp` as a subprocess.
- JSON-RPC messages are exchanged through stdin/stdout.
- The server does **not** listen on network ports.
- The server is intended for local machine usage only.

## Runtime stack and compatibility

- MCP SDK: `mcp` 2.x (`MCPServer`)
- Entry point: `kea2 mcp` CLI subcommand
- Python requirement for MCP feature: `>=3.10`
- Base Kea2 package compatibility remains `>=3.8`

Import used by current implementation:

```python
from mcp.server.mcpserver import MCPServer
```

## Installation

Install Kea2 with the MCP extra:

```bash
pip install "kea2-python[mcp]"
```

## Client configuration

### Claude Desktop / Cursor

Add the following entry to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kea2": {
      "command": "kea2",
      "args": ["mcp"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add kea2 -- kea2 mcp
```

### If `kea2` is not in PATH

When Kea2 is installed inside a virtual environment or with `--user`, the
`kea2` command may not be visible to the AI client. In that case use the
module form instead:

```json
{
  "mcpServers": {
    "kea2": {
      "command": "python3",
      "args": ["-m", "kea2.cli", "mcp"]
    }
  }
}
```

Both forms are portable and contain no absolute paths.

## Implemented tools

The server currently exposes six tools:

1. `kea2_init`
   - Initializes a Kea2 project in the current working directory by
     creating `configs/` and sample files.
   - Supports `force` mode to overwrite existing configs.
2. `kea2_check_device`
   - Lists local ADB-visible devices.
3. `kea2_run_test`
   - Starts a Kea2 run task asynchronously and returns a task handle.
4. `kea2_get_status`
   - Reads persisted task status and summarizes progress from
     `result_<stamp>.json` when available.
5. `kea2_get_results`
   - Lists files under the task output directory.
6. `kea2_cancel_test`
   - Cancels a running subprocess and attempts to clean the device-side
     monkey process.

## Task and output model

- Task metadata is stored in SQLite at `~/.kea2/tasks.db`.
- Task output directory layout follows Kea2 conventions:
  - `<output_parent>/res_<stamp>/`
  - `fastbot_<stamp>.log`
  - `result_<stamp>.json`
  - `property_exec_info_<stamp>.json` (if produced by test flow)

## Typical interaction flow

1. `kea2_init` — initialize the current directory (creates `configs/`)
   if needed.
2. `kea2_check_device` — confirm device visibility.
3. `kea2_run_test` — start one test session; returns a task handle
   immediately.
4. `kea2_get_status` — poll progress and final state.
5. `kea2_get_results` — discover generated files.
6. `kea2_cancel_test` — early stop if needed.

## Run prechecks and auto-fix hint

Before creating a task, `kea2_run_test` runs local prechecks:

- `configs/` must exist in the current project directory.
- The target device serial must be visible from ADB.

If `configs/` is missing, the tool returns an auto-fix style response:

```json
{
  "error": "configs/ 目录不存在",
  "hint": "调用 kea2_init 初始化项目",
  "auto_fixable": true
}
```

## Preconditions

Before use:

- `adb devices` can see at least one target device.
- Kea2 is installed in the local environment.
- The AI host supports MCP subprocess integration.
- The project root is writable (so `kea2_init` can create `configs/`).
- The MCP server's working directory matches the project root, otherwise
  `configs/` cannot be located.

## Quick verification

After configuring the AI client, ask:

> List the connected Android devices.

The client should call `kea2_check_device` (not `adb devices` via shell)
and return a device list. If the client falls back to shell commands, the
MCP server is probably not connected — check the client's `/mcp` panel for
status.

## Current limitations

- Local single-machine execution only.
- No remote sharing / remote transport support.
- No multi-client coordination guarantee.
- Log files may contain non-UTF-8 bytes produced by Fastbot. The server
  reads them with `errors="replace"` and only returns file metadata, not
  raw content.
- Long-running tasks are asynchronous: `kea2_run_test` returns a task
  handle immediately. Clients should poll `kea2_get_status` instead of
  waiting for the test to finish.

## Test coverage in this repository

The MCP E2E tests are located at:

- `tests/fake_kea2_run.py` (fake runner scenarios)
- `tests/mcp/test_e2e.py`

Covered flows include device query, init behavior, normal run, cancel,
fail status, and task store operations.