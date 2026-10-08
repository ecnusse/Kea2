# Kea2 MCP Server

This module provides a local MCP server for Kea2. It enables AI clients
(for example Claude Desktop, Claude Code, Cursor, and Codex) to trigger Kea2 test
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
python -m pip install "kea2-python[mcp]"
```

## Client configuration

### Choose the Python environment and test project

The examples below use a Windows test project at `C:/path/to/test_project`.
Replace every placeholder with your own absolute path. The test project is
the writable directory containing `configs/` and test outputs; it need not
be the Kea2 source repository.

- Use the absolute path to the Python interpreter where `kea2-python[mcp]`
  is installed. On Windows this is typically `.venv/Scripts/python.exe`;
  on macOS/Linux, use `/absolute/path/to/test_project/.venv/bin/python`.
- Install packages with that interpreter's `-m pip`. Activating a virtual
  environment in a terminal does not activate it in an already running GUI client.
- Set the server's working directory to the test project. Kea2 currently
  checks `configs/` relative to its working directory, and `kea2_init`
  writes files there. If the client supports `cwd`, set it explicitly.
- You may use `kea2 mcp` or `python -m kea2.cli mcp` directly if the
  client resolves the correct executable and working directory. A bare
  `python3` is not guaranteed to use your virtual environment.
- The client launches the STDIO server; do not start a separate server
  manually or configure an HTTP URL/port.

Before starting MCP, ensure the client's server working directory is the
test project root; opening the project alone does not guarantee this.
If device checks succeed but starting a test reports missing `configs/`,
check the MCP server's working directory.

### Claude Desktop

Open Claude Desktop's developer settings and edit
`claude_desktop_config.json`. Merge the following entry into the existing
`mcpServers` object, preserving any other servers. The command below starts
Kea2 directly; it does not set the working directory.

```json
{
  "mcpServers": {
    "kea2": {
      "command": "C:/path/to/test_project/.venv/Scripts/python.exe",
      "args": ["-m", "kea2.cli", "mcp"]
    }
  }
}
```

See the [local MCP setup guide](https://modelcontextprotocol.io/docs/develop/connect-local-servers)
for locating the configuration file on your operating system.

### Cursor

Use `.cursor/mcp.json` in the test project, or `~/.cursor/mcp.json`
for a personal global configuration. Cursor does **not** use
`claude_desktop_config.json`. Add the same `mcpServers` JSON entry shown
above, with the absolute path to your interpreter. Ensure the server's
working directory matches the test project.
See [Cursor's MCP configuration guide](https://prod.cursor.com/help/customization/mcp).

### Claude Code

From the test project directory, register Kea2 MCP with local scope.
This keeps machine-specific absolute paths out of a shared project config.

Windows (PowerShell):

```powershell
Set-Location 'C:\path\to\test_project'
claude mcp add --transport stdio --scope local kea2 -- "C:/path/to/test_project/.venv/Scripts/python.exe" -m kea2.cli mcp
```

macOS/Linux:

```bash
cd /absolute/path/to/test_project
claude mcp add --transport stdio --scope local kea2 -- /absolute/path/to/test_project/.venv/bin/python -m kea2.cli mcp
```

Use `claude mcp get kea2` to inspect the registered command and `/mcp`
inside Claude Code to inspect the connection.
See [Claude Code's MCP guide](https://code.claude.com/docs/en/mcp).

### Codex

Add the following to the test project's `.codex/config.toml`, or to
`~/.codex/config.toml` for a personal global configuration. Codex supports
`cwd` to set the server's working directory explicitly.

```toml
[mcp_servers.kea2]
command = 'C:\path\to\test_project\.venv\Scripts\python.exe'
args = ["-m", "kea2.cli", "mcp"]
cwd = 'C:\path\to\test_project'
startup_timeout_sec = 30
```

On macOS/Linux, replace `command` with the virtual environment's absolute
`.venv/bin/python` path and `cwd` with the absolute test project path.
The project configuration must be trusted/enabled by the client.
See the [Codex MCP guide](https://developers.openai.com/codex/mcp)
and [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

### Apply configuration and package updates

After configuring or updating Kea2, restart the client's MCP server
connection. If the client has no restart action, fully quit and reopen
the client. Replacing a wheel on disk does not reload an existing Python process.

When reinstalling a locally built wheel with the **same version**, use
`--force-reinstall` and the exact interpreter from your MCP configuration.
For example, after installing the MCP dependencies, run in the test project:

```powershell
& '.\.venv\Scripts\python.exe' -m pip install --force-reinstall --no-deps '.\kea2_python-1.2.4-py3-none-any.whl'
```

```bash
./.venv/bin/python -m pip install --force-reinstall --no-deps ./kea2_python-1.2.4-py3-none-any.whl
```

Replace the wheel filename as appropriate. `--no-deps` is only for an
environment whose dependencies are already installed and compatible; for a
fresh environment, install the wheel with its MCP extra instead, for example
`python -m pip install "./kea2_python-1.2.4-py3-none-any.whl[mcp]"`,
using the configured interpreter in place of `python`. Restart the MCP
connection afterward and use the verification steps below.

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

Explicitly ask the client to call `kea2_check_device` and inspect the tool
response. A shell invocation of `adb devices` does not verify the MCP connection.
If the tool is unavailable or fails, inspect the client's MCP settings and
logs (`/mcp` in Claude Code); verify the interpreter path, dependencies, and
working directory. A successful device query alone does not verify `configs/`.

To check an updated installation end to end, explicitly request a short test
on a chosen device and app, query `kea2_get_status` while it is running, and
confirm it completes without interruption. `result_available: true` only
means a result file exists; it does not mean the test has finished.

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
