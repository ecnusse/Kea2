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

Prepare and activate a Python 3.10 or newer virtual environment in your test project,
then install the MCP dependencies:

```bash
python -m pip install "kea2-python[mcp]"
python -c "import sys; print(sys.executable)"
```

The second command shows the current Python interpreter's location. Use that path as
`command` in the client configuration below so the MCP server uses the same environment.

A new command-line client launched from an activated terminal can also use
`python -m kea2.cli mcp` if it inherits that environment and its configuration does not
select another interpreter. An already running GUI client does not switch environments
when you activate one in a terminal, so the examples use absolute interpreter paths.

The examples use a Windows test project at `C:/path/to/test_project`; replace the paths
with your own. Virtual environment interpreters are typically `.venv/Scripts/python.exe`
on Windows and `.venv/bin/python` on macOS/Linux.

Set the MCP server's working directory to the test project root. Specify `cwd` where
supported. Kea2 looks for `configs/` there, and `kea2_init` writes files there. If configuration
is still missing after initialization, check the server's working directory, not just the
folder open in the client.

The client starts the STDIO server automatically; no separate terminal server process,
HTTP address or port configuration is needed.

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

Create `.mcp.json` in the test project root for project-scoped MCP configuration.
It sits alongside `.claude/`; do not put MCP server definitions in `.claude/settings.json`.

Windows example (replace `command` with the Python interpreter containing Kea2's MCP dependencies):

```json
{
  "mcpServers": {
    "kea2": {
      "type": "stdio",
      "command": "C:/path/to/test_project/.venv/Scripts/python.exe",
      "args": ["-m", "kea2.cli", "mcp"]
    }
  }
}
```

On macOS/Linux, use the same structure and change `command` to
`/absolute/path/to/test_project/.venv/bin/python`.
If `.mcp.json` exists, add only the `kea2` entry under `mcpServers`, preserving other servers.
Adjust machine-specific absolute paths for each environment rather than committing them as shared defaults.

Start `claude` from the test project root, approve the project MCP server when prompted,
and check the connection with `/mcp`. You can also run `claude mcp get kea2` in that directory.

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

### Apply configuration and installation updates

Activate the virtual environment used by the MCP server before installing or updating Kea2.
You can then use `python -m pip` directly without an absolute interpreter path.

For example, to reinstall a local wheel with the same version:

```bash
python -m pip install --force-reinstall "./kea2_python-1.2.4-py3-none-any.whl[mcp]"
```

Replace the wheel filename as appropriate. `--force-reinstall` ensures that the package is
reinstalled even when its version has not changed.

After configuration or installation changes, restart the client's MCP connection. If no restart
option is available, quit and reopen the client. Ask the agent to call `kea2_check_device` to verify
the connection. A device list confirms a successful call; an empty list means ADB currently finds
no devices. See [Quick verification](#quick-verification).

## Implemented tools

The server exposes 15 tools for test execution, task management, historical registration and structured evidence retrieval. Replace angle-bracketed IDs in the examples with actual values.

### `kea2_init`

Initializes a Kea2 project in the current working directory by creating
`configs/` and sample files. Supports `force` mode to overwrite existing configs.

### `kea2_check_device`

Lists local ADB-visible devices.

### `kea2_list_apps`

Read installed package IDs, including system apps. Requires serial; keyword filters package
substrings, limit defaults to 50 (1–100), offset to 0. Returns packages, total and next_offset
(null at the end). Display names are unavailable; do not guess name/package mappings.

### `kea2_check_test_setup`

Read-only preparation checks. Omit serial/packages to discover the environment; options accepts
optional run_test parameters. Returns working_directory, initialized, tool_defaults, issues and ready.
Checks configuration, device, installed packages, script selection and Activity-list files without
importing scripts, initializing, registering, clearing or launching. Readiness is not confirmation
or guaranteed device execution.

```json
{"serial":"<device_serial>","packages":["com.example.app"],"options":{"running_minutes":10,"clear_app_data":false}}
```

Install both kea2-test and kea2-result-analysis for interactive testing and automatic analysis.
See the [workflow guide](../../docs/mcp_extension_en.md).

### `kea2_run_test`

Starts a Kea2 run asynchronously and immediately returns a task handle
containing `task_id`. Supports the existing fuzzing workflow and optional
property selection.

#### Parameters

| Parameter | Required | Default | Description |
| --- | --- | --- | --- |
| `serial` | Yes | — | Target Android device serial. |
| `packages` | Yes | — | List of target app package names. |
| `running_minutes` | No | `10` | Test duration in minutes. |
| `output_dir` | No | `output` | Parent directory for test output. |
| `log_stamp` | No | Automatic timestamp | Custom experiment name, e.g. `login_test`: directory `<output_dir>/res_login_test/`, matching log stamp and an independently generated timestamp task_id. ASCII letters, digits, underscores, hyphens and dots only; not `.`/`..` or a trailing dot. Conflicts fail without overwriting. |
| `property_path` | No | Not set | Property `.py` file or directory, relative to the server working directory or absolute. |
| `property_pattern` | No | `test*.py` | Filename glob for directory discovery; ignored for a single file. |
| `driver_name` | No | `d` | Device attribute used by selected scripts, e.g. `self.d`. |
| `max_step` | No | CLI default | Maximum exploration steps; positive integer. |
| `throttle_ms` | No | CLI default | Delay between events in milliseconds; non-negative integer. |
| `take_screenshots` | No | CLI default | Enable screenshots at every step when `true`. |
| `profile_period` | No | CLI default | Coverage and screenshot collection period in steps; positive integer. |
| `restart_app_period` | No | CLI default | App restart period in steps; `0` disables periodic restarts. |
| `clear_app_data` | No | `false` | Clear data for every app in `packages` on the selected device before starting. This irreversibly removes login state, settings and local data. Enable with `"clear_app_data": true`. A clearing failure prevents launch and reports packages already cleared. |
| `act_whitelist_file` | No | Not set | Device destination for `configs/awl.strings`; mutually exclusive with blacklist. |
| `act_blacklist_file` | No | Not set | Device destination for `configs/abl.strings`; mutually exclusive with whitelist. |

Omitted optional run settings are not forwarded, leaving the CLI defaults intact.
`take_screenshots: false` omits the CLI's opt-in `--take-screenshots` flag.
Activity list paths are **Android device paths**, not local input files. For example,
`"act_whitelist_file": "/sdcard/.kea2/awl.strings"` uploads the project's
`configs/awl.strings` to that destination. Prepare the corresponding config file first.

For example, add these fields to either run example below to use a 500 ms delay,
enable per-step screenshots, and collect coverage/screenshots every 20 steps:

```json
{
  "throttle_ms": 500,
  "take_screenshots": true,
  "profile_period": 20
}
```

#### Fuzzing without explicit property selection

Omit `property_path` to preserve the existing fuzzing behavior:

```json
{
  "serial": "YOUR_DEVICE_SERIAL",
  "packages": ["com.example.app"],
  "running_minutes": 5
}
```

#### Selecting properties

For a single file:

```json
{
  "serial": "YOUR_DEVICE_SERIAL",
  "packages": ["com.example.app"],
  "running_minutes": 5,
  "property_path": "quicktest.py",
  "driver_name": "d"
}
```

For a directory, use `"property_path": "properties"` and optionally
`"property_pattern": "test_*.py"`. Discovery follows `unittest` conventions:
use importable Python module names and `__init__.py` in nested test packages.
This selects files, not individual classes or methods.

#### Notes

Paths and patterns are checked before creating a task. Scripts are imported
only in the test subprocess; only select scripts you trust. MCP forwards the
selection to the existing CLI without changing its discovery behavior. Import
errors or zero discovered properties/invariants may still allow fuzzing to
continue. Inspect the task log to confirm which properties loaded; `running`
or `finished` status alone does not confirm successful property loading.
The selected parameters are saved with the task metadata.

Properties run alongside Fastbot exploration, subject to their preconditions,
probability and attempt limits; selecting a file does not guarantee execution.
Reinstall the updated package and restart the MCP connection to refresh the
tool schema before using these parameters.

### `kea2_get_status`

Reads persisted task status and summarizes progress from
`result_<stamp>.json` when available.

### `kea2_get_results`

Lists files under the task output directory.

### `kea2_cancel_test`

Cancels a running subprocess and attempts to clean the device-side monkey process.

### `kea2_list_tasks`

Discover tasks registered for the current user. Optional filters are status (queued/running/cancelling/cancelled/finished/failed/unknown), origin (cli/mcp/imported) and parent_task_id. Use limit (default 20, range 1–100) and offset (default 0); follow next_offset until null. The response includes tasks and total. Ask the user to select an ID before analysis.

```json
{"origin":"cli","limit":20}
```

### `kea2_register_result`

Register an existing experiment directory. Requires result_dir; optional stamp selects an experiment and task_id supplies an alias. Inspects the directory and immediate res_* children without modifying historical files. registered and already_registered return an ID; selection_required returns candidates; identity_conflict can be resolved with an explicit alias; unsupported and invalid explain the problem. HTML alone is insufficient. Imported lifecycle state is unknown.

```json
{"result_dir":"E:/experiments/res_old","stamp":"old"}
```

### `kea2_get_result_schema`

Read the structured result contract (currently 1.5). No task_id required. document defaults to experiment and also accepts report, query, finding, artifact and error. Returns the corresponding JSON Schema.

```json
{"document":"query"}
```

### `kea2_get_report`

Read an overview by task_id, including execution and exit information, check statistics, Activity coverage, widget count, Crash/ANR occurrences, log observations, source availability, warnings and snapshot_id. Missing statistics are null. On CHILD_TASK_REQUIRED, list children by parent_task_id and select a child experiment.

```json
{"task_id":"<task_id>"}
```

### `kea2_query_report`

Page through a task_id and section. filters and cursor are optional; limit defaults to 50 (1–100). Returns items, total, next_cursor and snapshot_id. Keep the section and filters unchanged while following next_cursor until null.

```json
{"task_id":"<task_id>","section":"checks","filters":{"kind":"property"}}
```

| section | Contents | Filter fields |
| --- | --- | --- |
| `checks` | Check statistics | name, kind, has_findings |
| `findings` | Individual check failures, crashes and ANRs | type, check_name, state |
| `activities` | Activity coverage | name, covered |
| `trends` | Coverage and widget trends | metric |
| `steps` | Event timeline | type, start_step, end_step, execution_id |
| `executions` | Execution boundaries | id, check_name, kind, state |
| `artifacts` | Evidence metadata | id, kind, availability |
| `widgets` | Widget inventory and parse status | activity, class_name, resource_id, content_description, parse_status |
| `property_execution_trend` | Distinct properties started | start_step, end_step |
| `configuration` | Saved run/report configuration | document, key |

Property passes are derived as `max(executed - fail - error, 0)`. Invariants report fail/error counts and exception details; precondition, execution and pass counts are null. Findings are occurrences. Unreadable sources cannot support a zero count.

### `kea2_get_finding`

Supply task_id plus finding_id and snapshot_id from a findings page. Returns trace text, related execution, log context and evidence references for one occurrence. offset defaults to 0, limit to 8000 characters (1–32000); follow next_offset. context_before and context_after each default to 0 and accept 0–20 entries. Ambiguous screenshot links remain unresolved.

```json
{"task_id":"<task_id>","finding_id":"<finding_id>","snapshot_id":"<snapshot_id>","context_before":3,"context_after":3}
```

### `kea2_get_artifact`

Supply task_id, artifact_id and snapshot_id from an artifact query or finding detail to retrieve content. Text is paged by character: offset defaults to 0 and limit to 8000 (1–32000). Images require offset=0 and return native MCP image content and metadata (8 MiB maximum); viewing requires client support. Relevant text sources over 64 MiB are marked too_large. On STALE_SNAPSHOT, refresh the overview and relevant list.

Image responses contain a metadata text block and a native image block in `content`, without `structuredContent`, to avoid clients preferring structured metadata and dropping images. Text evidence retains structured output. If only metadata appears after updating, verify the MCP environment uses the new wheel and restart the client session.

```json
{"task_id":"<task_id>","artifact_id":"<artifact_id>","snapshot_id":"<snapshot_id>"}
```

## Task and output model

New runs default to a timestamp for both task_id and stamp. CLI runs register automatically; MCP parent and child processes share one task. The experiment directory contains `kea2_task.json` for identity recovery. Legacy UUID tasks remain queryable.

- Task metadata is stored in SQLite at `~/.kea2/tasks.db`.
- Task output directory layout follows Kea2 conventions:
  - `<output_parent>/res_<stamp>/`
  - `fastbot_<stamp>.log` (written exclusively by Fastbot)
  - `kea2_<stamp>.log` (Python subprocess stdout/stderr captured by MCP)
  - `result_<stamp>.json`
  - `property_exec_info_<stamp>.json` (if produced by test flow)

New tasks store `kea2_<stamp>.log` as their diagnostic `log_file`; inspect it
for startup errors and Python tracebacks. Both logs are listed by
`kea2_get_results`. Keeping them separate prevents concurrent writes from
corrupting the log reader's UTF-8 position. Existing task records are unchanged.

## Typical interaction flow

1. `kea2_init` — initialize the current directory (creates `configs/`)
   if needed.
2. `kea2_check_device` — confirm device visibility.
3. `kea2_run_test` — start one test session; returns a task handle
   immediately.
4. `kea2_get_status` — poll progress and final state.
5. `kea2_get_results` — discover generated files.
6. `kea2_cancel_test` — early stop if needed.

For an existing experiment, discover tasks with `kea2_list_tasks` or register a selected historical directory with `kea2_register_result`. After the user supplies a specific task_id, read the overview, query records and retrieve traces or screenshots as needed. The client agent writes the analysis using MCP evidence. See the [complete workflow](../../docs/mcp_extension_en.md), [analysis skill guide](../../docs/result_analysis_skill_en.md) and [registration guide](../../docs/task_registration_en.md).

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

- Running a test requires a target visible to `adb devices`; saved results can be read offline.
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
- `kea2_get_results` lists files. Use `kea2_get_artifact` to read registered text evidence; non-UTF-8 content returns a read error.
- Long-running tasks are asynchronous: `kea2_run_test` returns a task
  handle immediately. Clients should poll `kea2_get_status` instead of
  waiting for the test to finish.

## Test coverage in this repository

The MCP E2E tests are located at:

- `tests/fake_kea2_run.py` (fake runner scenarios)
- `tests/mcp/test_e2e.py`

Covered flows include device query, init behavior, normal run, cancel,
fail status, and task store operations.
