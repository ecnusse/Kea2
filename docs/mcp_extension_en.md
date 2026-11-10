# Use an agent and MCP to complete the Kea2 testing workflow

[简体中文](mcp_extension_cn.md)

After configuring the client and installing the skills, say “I want to test with Kea2.” The agent guides parameter selection, checks readiness, launches and monitors the test, then retrieves evidence and writes a report. Answer the questions and confirm the configuration; you do not need to know tool names or issue separate launch, status and analysis commands.

Automatic execution starts after configuration confirmation. The agent explains and asks about every unspecified applicable startup parameter instead of silently choosing defaults. Kea2 supplies test data and evidence; the model in the client performs the analysis. HTML reports remain available for human readers.

## 1. Prepare the client and test environment

1. Connect an Android device or emulator through ADB and install the target app.
2. Install Kea2 with MCP dependencies in Python 3.10+, for example `python -m pip install "kea2-python[mcp]"`. For development builds, install the wheel containing this feature.
3. Configure the client. See the [MCP deployment guide](../kea2/mcp/README.md).
4. Copy both complete folders, `skills/kea2-test` and `skills/kea2-result-analysis`, including all references, into the same client skill root. For Codex use project `.codex/skills/` or user `~/.codex/skills/`. See the [skill installation guide](result_analysis_skill_en.md) for other clients.
5. Restart MCP after installing or updating the wheel. Start a new conversation after updating skills. Wheels do not install skills automatically.

Ask the agent to check connected devices to verify the connection. Saved results can be read offline; launching requires a device. You may start the conversation before initializing the project: initialization happens after confirmation of the preparation steps.

## 2. Start with one request

> I want to test with Kea2.

You can explicitly invoke `kea2-test` or provide some settings upfront:

> Test com.example.app on emulator-5554 for 20 minutes using quicktest.py. Keep the app's data.

The agent first checks devices, the server working directory and readiness without making changes. It retains supplied parameters and asks only about the remaining ones. The client configuration determines the server working directory; changing the output directory does not change it.

## 3. Answer the parameter questions

The agent explains each parameter's purpose, units or choices, default behavior and effects, then waits for your response. Questions are grouped by topic. This workflow covers all parameters exposed by `kea2_run_test`, not every CLI option.

| Topic | Parameters | Your choice |
| --- | --- | --- |
| Device and apps | `serial`, `packages` | Confirm the device and one or more target package IDs, even when only one device exists |
| Testing mode | `property_path` | Pure fuzzing or an existing Property file/directory |
| Script settings | `property_pattern`, `driver_name` | Directory filename pattern and device attribute, e.g. d for self.d |
| Execution controls | `running_minutes`, `max_step`, `throttle_ms`, `restart_app_period` | Duration, event limit, event interval and restart interval |
| Screenshots and coverage | `take_screenshots`, `profile_period` | Per-step screenshots and periodic collection interval |
| Activity scope | `act_whitelist_file`, `act_blacklist_file` | No restriction, whitelist or blacklist; lists are mutually exclusive |
| Output and data | `output_dir`, `clear_app_data` | Output parent and whether to clear all target apps before launch |

For example:

> running_minutes sets the planned duration in minutes, default 10. Use that value or specify another?
>
> clear_app_data clears target apps before launch, irreversibly deleting login state, settings and local data. It defaults to off. Enable or disable it?

You may answer several fields at once or explicitly accept “remaining defaults.” Required device and app identity must still be resolved. Silence does not accept a default.

Pure fuzzing needs no script settings. A single script file needs no filename glob. No Activity restriction needs no list path. The final configuration explains these non-applicable fields. Changing the testing mode prompts review of dependent settings.

If you do not know the package ID, ask for installed packages and choose one. This includes system apps and does not provide display names; the agent must not guess name/package mappings. Activity-list parameters are device destination paths; contents come from project `configs/awl.strings` or `configs/abl.strings`, not arbitrary local paths.

## 4. Check and confirm the complete configuration

The agent checks device access, installed apps, configuration, script selection and Activity-list files. These checks are read-only: they do not import or execute user scripts, initialize, register, clear data or launch tests. Readiness means the checked conditions passed, not guaranteed device execution.

Resolve only affected settings when problems occur. The agent then presents every applicable value, explicitly accepted default and non-applicable field, including:

- Device, apps, testing mode and execution settings.
- Output parent directory.
- Whether initialization will write configuration, version information and quicktest.py.
- Whether clearing is enabled and every affected package.

Preparation and launch begin only after you confirm. Existing configuration is not automatically force-overwritten. Changed settings require a revised confirmation, and readiness is checked again after initialization.

## 5. Automatically launch and monitor

The agent calls `kea2_run_test`, records its returned task_id and result directory, and monitors that exact task. You do not need to copy the ID or request status updates manually.

Ask to cancel if needed. A clearing failure prevents launch and identifies apps already cleared; the agent does not automatically retry clearing or rerun tests. A lost launch response or unclear status requires resolving task identity before another launch, preventing duplicate runs.

When execution ends, the agent uses exit information and result availability to proceed. Property failures, crashes and ANRs do not necessarily mean the launch tool failed. Reports for cancelled or incomplete runs identify the available scope and limitations.

The client must support continuing tool calls and waiting. Closing it does not guarantee automatic recovery. Retain the task ID and explicitly resume when needed. Lost or ambiguous task bindings require selection, never guessing the latest run.

## 6. Automatically retrieve and analyze results

The workflow passes this launch's task ID directly to `kea2-result-analysis`; you need not repeat it or request analysis again. The agent reads the overview and availability, queries configuration, checks, coverage trends and findings, then retrieves traces, event context and images as needed.

The report includes experiment context, Property and Invariant tables, execution and coverage, evidence-backed findings, hypotheses and next steps. Missing data is not zero, and finding occurrences are not unique bugs. Conclusions use MCP records as evidence and distinguish observations from hypotheses; internal source identifiers are hidden by default.

Experiment facts come exclusively from Kea2 MCP tools, without independently inspecting source, HTML, raw logs or the database. Analysis reads applicable rules from the [professional knowledge file](../skills/kea2-result-analysis/references/domain-knowledge.md); see the [analysis skill guide](result_analysis_skill_en.md) for maintenance and the [report template](../skills/kea2-result-analysis/references/report-template.md) for output structure.

Independent analysis of CLI or historical experiments still requires explicit task selection. This differs from carrying the current workflow's launch ID into analysis.

## Common situations

| Situation | Action |
| --- | --- |
| The agent does not select the workflow | Explicitly invoke kea2-test; check both complete skills are installed and start a new conversation |
| New tools are absent | Check MCP uses the Python environment containing the updated wheel, then restart it |
| Device or app unavailable | Connect the device or install the app, then ask for another check |
| Missing script or Activity list | Correct the relevant paths/configuration in the server project and recheck |
| Change a parameter | Tell the agent; before launch it updates the configuration and asks for confirmation again |
| Incomplete results | Analyze available evidence with explicit gaps instead of automatically rerunning |

The following reference sections explain the tools, parameters and data used by the agent. You do not need to call them manually.

## The 15 tools

| Tool | Inputs and purpose | Result or effect |
| --- | --- | --- |
| `kea2_init` | Initialize the working directory; optional force defaults to false | Writes configuration, version information and quicktest.py. Existing configuration is protected by default |
| `kea2_check_device` | List ADB devices; no arguments | Device serial, state and model |
| `kea2_list_apps` | Requires serial; optional keyword, limit, offset | Paginated installed package IDs, without display names |
| `kea2_check_test_setup` | Optional serial, packages, options | Read-only environment, defaults, issues and readiness; no initialization or launch |
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
| `clear_app_data` | Defaults to false. When true, irreversibly clears all target apps' data on the selected device before launch, including login state, settings and local data. Failure prevents launch and reports apps already cleared |
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

## How the agent investigates a finding

1. Call `kea2_get_report(task_id)`, inspect availability and record the snapshot.
2. Call `kea2_query_report` with `{"task_id":"<task_id>","section":"findings","filters":{"type":"property","check_name":"<property name>"}}`. Replace placeholders with actual values. Retain the finding ID and snapshot from the returned page.
3. Call `kea2_get_finding` with those IDs and task_id. Trace pages default to 8,000 characters (maximum 32,000); follow next_offset. Request 0–20 surrounding log entries on each side with context_before and context_after.
4. For an available screenshot, pass the returned artifact_id and snapshot to `kea2_get_artifact`. PNG, JPEG and WebP can be returned as MCP images with metadata and SHA-256. Text artifacts are paged by Unicode character; invalid UTF-8 produces an error.

An execution interval can contain interleaved events. Missing boundaries remain missing. Screenshot links use explicit references; ambiguous matches remain unresolved. The agent can describe a screenshot only after obtaining its content in a client that supports image inspection.

## Data quality and snapshots

The Crash/ANR log is optional and produced for exceptions. For a completed run with exit code 0 or 1, an absent log returns zero Crash and ANR occurrences and does not alone make results incomplete. Physical availability remains `missing`; reports show "0 (none detected)". Existing logs count valid event blocks without deduplication. Read failures, wholly malformed logs or insufficient execution metadata can still produce null counts. Historical registration without a known exit code does not establish zero exceptions from log absence.

Source availability is available, missing, partial, invalid, unreadable or too_large. Missing statistics are null. A readable empty crash log can support zero observed occurrences; an absent file cannot. Damaged line records can be skipped with source warnings. Up to 50 warning examples are returned alongside the count and truncation flag.

Relevant text sources have a 64 MiB limit; screenshots have an 8 MiB limit. Artifact reads check paths, image decoding and changes during reads. Snapshots incorporate task metadata and source state; cursors and evidence references are snapshot-bound. On STALE_SNAPSHOT, refresh the overview and affected queries. Files are read independently, so live runs may yield provisional observations.

Other common errors include TASK_NOT_FOUND (check ID and user environment), INVALID_FILTER (check section filters), ARTIFACT_UNAVAILABLE (record the gap) and INVALID_IMAGE (content cannot be read as an image).

## Analysis skill and report

`kea2-result-analysis` version **1.7.0** packages the instructions, data semantics, query examples and report template. The skill reads a [separate knowledge file](../skills/kea2-result-analysis/references/domain-knowledge.md). Install the whole skill directory, including references, separately from the wheel. The guide uses project-level `.codex/skills/` or user-level `~/.codex/skills/` for Codex. Instructions for other clients are in the [skill user guide](result_analysis_skill_en.md).

- **Task binding.** Reuse this confirmed workflow's launch ID. Independent analysis requires explicit user selection. Lost or ambiguous bindings require clarification, never choosing a latest or only task.
- **Evidence.** Obtain experiment facts exclusively through Kea2 MCP report, query, finding and artifact responses. Treat gaps as gaps. Do not inspect source, HTML, databases or raw files independently.
- **Scope.** Start with 25 rows per page. Default to 20 result/evidence calls after the overview, at most five investigated findings, three images and two snapshot recovery cycles. The user can request deeper inspection. Report unread pages.
- **Statistics.** Separate property and invariant tables. The property table contains the name, precondition satisfaction, executions, passes, fails and errors. The invariant table contains the name, fails and errors, with exception details described separately. Tables omit basis and evidence columns. Include all relevant checks and disclose displayed versus total records.
- **Conclusions.** Report context, data quality, execution and coverage, findings, hypotheses, limits and next checks. Distinguish observations from hypotheses. Hide exit codes, internal flags, snapshots and raw source states by default; explain material limitations briefly. Actual problems retain descriptions, relevant stack excerpts and screenshots. Record IDs and sources can be supplied on request.

These instructions guide the client agent. Actual adherence depends on the client and model. See the [report template](../skills/kea2-result-analysis/references/report-template.md).
