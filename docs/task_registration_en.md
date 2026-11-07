# Task registration and historical results

[中文](task_registration_cn.md)

## Automatic registration

New `kea2 run` experiments register in the executing user's `~/.kea2/tasks.db`.
CLI registration does not require optional MCP dependencies. MCP launches share one task
between the parent server and CLI subprocess.

```bash
kea2 run -p com.example.app --running-minutes 10
```

Obtain the task ID through `kea2_list_tasks` or the result directory's `kea2_task.json`.
Default stamps use timestamps with microseconds. CLI log stamps retain their original rules,
including Unicode and spaces. If a stamp is unsuitable as an ID or the ID already exists,
registration generates a separate ID without changing filenames or directories.
The CLI permits existing result directories. Same-name files may be overwritten; old task
records do not retain historical copies of those files.

Each new directory contains `kea2_task.json` with identity, known lifecycle information and a
relative result filename. Database initialization or write failures emit a warning and allow
testing to continue, with metadata for later registration. MCP launches still allocate separate
tasks and new directories and validate the parent-to-child directory handoff.

CLI and MCP must use the same user environment to share the database. Different users/machines
and moved results require explicit registration. Forced process termination may leave stale lifecycle
metadata; listed states are persisted records, not live process verification. Existing UUID tasks
retain their IDs; unknown historical origins and timestamps remain null.

## Discover tasks

Call `kea2_list_tasks`, optionally filtering origin by `cli`, `mcp` or `imported`, together
with status/limit/offset. Older records may have no origin.

```json
{"origin": "cli", "limit": 20, "offset": 0}
```

Explicitly choose a task ID before analysis. Discovery and registration do not select a task
automatically. Nonzero exits can indicate findings, so failed does not necessarily mean startup failed.

## Register historical directories

CLI and MCP share the registration implementation:

```bash
kea2 register-result -p "E:/experiments/res_old"
kea2 register-result -p "E:/experiments/res_old" --stamp old
```

The MCP tool `kea2_register_result` accepts:

```json
{"result_dir": "E:/experiments/res_old", "stamp": "old"}
```

Stamp is optional. Discovery only inspects the selected directory and immediate `res_*` children.
Preserve relative files such as `result_<stamp>.json`, `property_exec_info_<stamp>.json`,
logs/screenshots in `output_<stamp>/`, and configuration files when available. HTML alone is unsupported.
Partially readable results can be registered with availability/warnings; entirely unreadable results cannot.

| Status | Action |
| --- | --- |
| registered | Use the returned ID; explicitly select it before analysis |
| already_registered | Reuse the existing ID for the same actual directory and stamp |
| selection_required | Specify an exact candidate directory and stamp |
| identity_conflict | An ID belongs to another location; explicitly supply an alias if desired |
| unsupported / invalid | Correct inputs or provide supported result sources |

An alias changes only the database ID, never the original stamp or filenames:

```bash
kea2 register-result -p "E:/archive/res_old" --stamp old --task-id archived_old
```

Historical registration updates only the database, without writing historical files, rerunning tests
or regenerating HTML. Manifest identity is recovered, but lifecycle claims are not verified:
imports use unknown state and do not infer exit codes or completion times. Original manifest
information is retained as unverified metadata. Moving directories does not automatically replace
registered paths; an explicit alias can register the new location in this version.

## Hybrid experiments

New hybrid runs register a parent and independent children. Query children with
`kea2_list_tasks(parent_task_id=...)`. Result queries on a parent return CHILD_TASK_REQUIRED;
explicitly select a child ID. Historical hybrid parents expose recognizable child candidates;
parents marked hybrid in metadata are excluded from single-experiment registration.
This version does not aggregate experiments or treat merged HTML as single-experiment data.

## Apply the update

Rebuild/install the wheel and restart MCP. Also update the installed `kea2-result-analysis`
folder and start a new session when using the skill. Existing report, query, finding and artifact
tools then analyze the selected task.
