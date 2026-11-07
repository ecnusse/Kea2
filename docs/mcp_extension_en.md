# How to use an agent with the Kea2 MCP extension to launch tests, retrieve results, and analyze them

[简体中文](mcp_extension_cn.md)

Kea2 MCP lets an agent start Android tests, find existing experiments and retrieve structured results and evidence. Tests started by MCP, new command-line tests and explicitly registered historical results all use a task ID for lookup. The service runs tests and supplies evidence. The model in the agent client interprets that evidence and writes the analysis. The HTML report remains available for human readers.

## From setup to a report

1. Install Kea2 with MCP dependencies in a Python 3.10+ environment, for example with `python -m pip install "kea2-python[mcp]"`. Configure the client to run that environment's `python -m kea2.cli mcp` from the test project. The server communicates over local standard input and output. Restart it after updating the wheel.
2. To start a test, initialize a new project with `kea2_init` and obtain a connected device serial with `kea2_check_device`. For existing experiments, list registered tasks or register a specific historical directory instead.
3. A sample request is “Test com.example.app on emulator-5554 for ten minutes using quicktest.py.” Use your actual device, package and script. Keep the returned task ID and use it to check progress.
4. Explicitly select a task for analysis, for example “Use kea2-result-analysis to analyze task <actual task_id>. List unexecuted properties and inspect failure evidence.”
5. The agent reads the overview, queries relevant details and inspects traces or screenshots as needed. Its report identifies sources, gaps and the portion examined.

Running tests requires an accessible Android device. Reading saved results can be done offline. See [MCP deployment](../kea2/mcp/README.md) and [skill installation](result_analysis_skill_en.md).

## The 13 tools

| Tool | Inputs and purpose | Result or effect |
| --- | --- | --- |
| `kea2_init` | Initialize the working directory; optional force defaults to false | Writes configuration, version information and quicktest.py. Existing configuration is protected by default |
| `kea2_check_device` | List ADB devices; no arguments | Device serial, state and model |
| `kea2_run_test` | Start a background test on a device for specified packages | Returns task_id, stamp, actual result directory and status on launch |
| `kea2_get_status` | Check a task by ID | State, phase, PID, coarse executed/fail/error progress and result-file availability |
| `kea2_cancel_test` | Cancel a running task | Stops the process, attempts device-side cleanup and records cancellation |
| `kea2_list_tasks` | Discover registered tasks; no task_id required | Paginated metadata, optionally filtered by status, origin or parent |
| `kea2_register_result` | Register a selected directory, optionally specifying a stamp or task ID alias | Registration outcome, existing ID, candidates or conflict |
| `kea2_get_results` | List files in a task's output directory | File paths, types and sizes |
| `kea2_get_result_schema` | Inspect the contract; no task_id required | JSON Schema for experiment, report, query, finding, artifact or error |
| `kea2_get_report` | Read an experiment overview by task_id | Execution, summaries, coverage, snapshot, availability and warnings |
| `kea2_query_report` | Query task_id and section, with optional filters, cursor and limit | A page of records, matching total, snapshot and next cursor |
| `kea2_get_finding` | Supply task_id, finding_id and snapshot_id | Trace excerpt, associated execution, event context and evidence references |
| `kea2_get_artifact` | Supply task_id, artifact_id and snapshot_id | Actual image or text content and artifact metadata |

## Run and control tests

| Launch parameters | Purpose |
| --- | --- |
| `serial`, `packages` | Required device serial and target package list |
| `running_minutes`, `output_dir` | Duration (default 10 minutes) and output parent (default output) |
| `property_path`, `property_pattern`, `driver_name` | Property file or directory, discovery pattern (default test*.py) and driver attribute (default d). Omit the path for fuzzing alone |
| `max_step`, `throttle_ms` | Maximum exploration steps and event interval in milliseconds |
| `take_screenshots`, `profile_period` | Per-step screenshots and periodic coverage/screenshot collection in steps |
| `restart_app_period` | Restart interval in steps; zero disables periodic restart |
| `act_whitelist_file`, `act_blacklist_file` | Mutually exclusive device-side Activity list paths with content from project configuration |

Fastbot explores the app and runs eligible properties when scripts are supplied. Startup checks validate script settings, project configuration and device connectivity. Subprocess output and Fastbot logs are captured separately. Windows process checks use a process handle to inspect liveness.

Progress is a preliminary observation. A persisted failed status can follow a nonzero exit due to findings. The structured report interprets exit code 0 as completed without finding flags, 1 as a property violation, 2 as Crash/ANR, 3 as both, and 4 as an execution error. Exit flags, observed occurrences and data completeness are reported separately.

## Run identity and discovery

| Origin | How to obtain the ID | Behavior |
| --- | --- | --- |
| MCP | Start with kea2_run_test | Parent and CLI subprocess share one task |
| CLI | Run kea2 run and obtain the ID from kea2_list_tasks or kea2_task.json | Registers automatically without optional MCP dependencies |
| Historical | Call kea2_register_result or run `kea2 register-result -p <directory>` | Registers the selected directory without changing its files |

New runs default to `task_id = stamp = log_stamp`, with results under `<output parent>/res_<stamp>/`. Generated stamps use local time with microseconds in `%Y%m%d%H_%M%S%f` format. CLI runs retain custom stamp rules and directory reuse. Unicode, spaces or ID collisions result in a separate registry task_id without changing file stamps or paths. MCP launches still allocate separate directories. Legacy UUID tasks remain addressable.

The executing user's `~/.kea2/tasks.db` records task identity, origin, state and result location. Each result directory has a `kea2_task.json` manifest with identity and known lifecycle information for recovery or migration. Database initialization or write failures emit a warning without stopping CLI testing. Forced termination can leave stale lifecycle records.

Task discovery defaults to 20 rows per page (maximum 100). Use total and next_offset for pagination. Supported filters are status, origin (cli/mcp/imported) and parent_task_id. A listed task can outlive the files at its recorded location.

History registration examines the chosen directory and immediate res_* children. Registering the same actual directory and stamp returns the existing ID. Select a specific experiment when several match. For an ID already pointing elsewhere, an explicit alias preserves the original stamp and filenames. Outcomes are registered, already_registered, selection_required, identity_conflict, unsupported and invalid. Imported lifecycle state is unknown. HTML alone is insufficient.

Hybrid runs register a parent and independent child experiments. A parent report returns CHILD_TASK_REQUIRED. Use `kea2_list_tasks(parent_task_id=...)` and select a child ID for analysis. See [registration examples and alias handling](task_registration_en.md).

## Structured results and ten query sections

The service locates the registered directory and stamp, then reads saved result sources into contract **1.5**. The contract specifies types, units, nullability and error shapes. Use the schema tool to inspect individual response types. See the [JSON Schema](structured_result.schema.json) and [example experiment](examples/structured_result_v1.5.json).

The overview reports execution, exit flags, known times, packages and device, check summaries, fail/error and Crash/ANR occurrences, Activity coverage and triggered widget count. When logs permit, it also reports first/last recorded times, elapsed seconds, maximum Monkey step and valid record count. Launch requests, saved settings and observations remain separate. The response includes section counts, availability, warnings, schema_version and snapshot_id.

| Section | Question and source | Filters |
| --- | --- | --- |
| checks | Which checks ran or failed? Reads result_<stamp>.json | name, kind, has_findings |
| findings | Which individual exceptions, crashes or ANRs occurred? Reads property_exec_info_<stamp>.json and crash-dump.log | type, check_name, state |
| activities | Which Activities were covered and how often? Uses the last valid coverage.log sample | name, covered |
| trends | How did Activity coverage or triggered widget count change over Monkey steps? Uses coverage.log and widget_coverage.log | metric |
| steps | What events occurred in an interval? Uses steps.log and source lines | type, start_step, end_step, execution_id |
| executions | Where were the recorded boundaries of each property execution? Uses explicit script markers | id, check_name, kind, state |
| artifacts | Which known logs and explicitly referenced screenshots are available? | id, kind, availability |
| widgets | Which controls were recorded? Uses widget_coverage_report.txt and retains raw text and parse state | activity, class_name, resource_id, content_description, parse_status |
| property_execution_trend | How many distinct properties had started by a given step? Excludes invariants | start_step, end_step |
| configuration | What settings were saved in options.json and bug_report_config.json? | document, key |

The listed device logs reside in the matching output_<stamp>/ directory. Query pages default to 50 records (range 1–100). Keep section and filters unchanged and pass next_cursor as cursor for the next page, until null.

Properties have precondition satisfaction, executions, fails and errors; passes are derived as `max(executed - fail - error, 0)`. Invariants have fails, errors and exception evidence only. Their precondition, execution and pass counts are null. Unknown checks are separate. Counts of affected checks, individual occurrences and unique defects measure different things. Widget trends are counts, while Activity coverage is a percentage.

Configuration records keep the key, value, encoding and source. Duplicate keys invalidate the affected document. Conflicting values are retained and flagged. Nonfinite values such as Infinity use tagged encodings.

## Investigate a finding

1. Call `kea2_get_report(task_id)`, inspect availability and record the snapshot.
2. Call `kea2_query_report` with `{"task_id":"<task_id>","section":"findings","filters":{"type":"property","check_name":"<property name>"}}`. Replace placeholders with actual values. Retain the finding ID and snapshot from the returned page.
3. Call `kea2_get_finding` with those IDs and task_id. Trace pages default to 8,000 characters (maximum 32,000); follow next_offset. Request 0–20 surrounding log entries on each side with context_before and context_after.
4. For an available screenshot, pass the returned artifact_id and snapshot to `kea2_get_artifact`. PNG, JPEG and WebP can be returned as MCP images with metadata and SHA-256. Text artifacts are paged by Unicode character; invalid UTF-8 produces an error.

An execution interval can contain interleaved events. Missing boundaries remain missing. Screenshot links use explicit references; ambiguous matches remain unresolved. The agent can describe a screenshot only after obtaining its content in a client that supports image inspection.

## Data quality and snapshots

Source availability is available, missing, partial, invalid, unreadable or too_large. Missing statistics are null. A readable empty crash log can support zero observed occurrences; an absent file cannot. Damaged line records can be skipped with source warnings. Up to 50 warning examples are returned alongside the count and truncation flag.

Relevant text sources have a 64 MiB limit; screenshots have an 8 MiB limit. Artifact reads check paths, image decoding and changes during reads. Snapshots incorporate task metadata and source state; cursors and evidence references are snapshot-bound. On STALE_SNAPSHOT, refresh the overview and affected queries. Files are read independently, so live runs may yield provisional observations.

Other common errors include TASK_NOT_FOUND (check ID and user environment), INVALID_FILTER (check section filters), ARTIFACT_UNAVAILABLE (record the gap) and INVALID_IMAGE (content cannot be read as an image).

## Analysis skill and report

`kea2-result-analysis` version **1.4.0** packages the instructions, data semantics, query examples and report template. The skill reads a [separate knowledge file](../skills/kea2-result-analysis/references/domain-knowledge.md). Install the whole skill directory, including references, separately from the wheel. The guide uses project-level `.codex/skills/` or user-level `~/.codex/skills/` for Codex. Instructions for other clients are in the [skill user guide](result_analysis_skill_en.md).

- **Selection.** Ask and wait for an explicit task ID before starting a new analysis, including when a task was just run or registered or only one exists. An explicit continuation can reuse the ID already supplied for that analysis.
- **Evidence.** Obtain experiment facts exclusively through Kea2 MCP report, query, finding and artifact responses. Treat gaps as gaps. Do not inspect source, HTML, databases or raw files independently.
- **Scope.** Start with 25 rows per page. Default to 20 result/evidence calls after the overview, at most five investigated findings, three images and two snapshot recovery cycles. The user can request deeper inspection. Report unread pages.
- **Statistics.** Separate property and invariant tables. The property table contains the name, precondition satisfaction, executions, derived passes, fails, errors and evidence. The invariant table contains the name, fails, errors and exception details or evidence. Include all relevant checks and disclose displayed versus total records.
- **Conclusions.** Report context, data quality, execution and coverage, findings, hypotheses, limits and next checks. Cite tasks, snapshots, record IDs or source locations and distinguish observations from hypotheses.

These instructions guide the client agent. Actual adherence depends on the client and model. See the [report template](../skills/kea2-result-analysis/references/report-template.md).

## Current scope

Users can analyze experiments launched through the CLI or MCP, or register a historical result directory for analysis. Each analysis uses one user-selected `task_id`. The agent can review execution and coverage statistics, page through findings, and cite available traces, event logs and screenshots in its report. For hybrid tests, users can list child tasks and select one child experiment to analyze.
