# Multi-device workflow

## Select and prepare

Ask whether to test one phone or multiple phones when the request does not establish this.
Show discovered model/serial pairs. For single-device mode select one serial; for multi-device
mode obtain the exact selected serials. Reject duplicates and resolve disconnected selections.
Explain that each selected device gets an independent test task and all tasks run concurrently.

Ask whether the devices share settings or need individual overrides. Explain and collect every
missing applicable run parameter as in the parameter guide. Shared answers apply only to the
devices the user agrees to; do not ask the same shared question for every phone. Keep one fully
resolved parameter ledger per device, including packages and clearing. For a merged report,
confirm the same target package set; different apps must have separate report groups.

Call kea2_check_test_setup separately for each selected serial with its settings. Package installation
and device readiness must be checked on every phone. Scripts and configs use the server's working
directory. Initialize a shared uninitialized project once after confirmation, then recheck every device.
Do not change shared configs while tests run. Distinct Activity-list contents require separate projects;
do not promise per-device contents merely by changing the device destination filename.

For default log_stamp=null, keep automatic timestamps. For custom names, ensure every planned
(output_dir, log_stamp) pair is distinct: propose explicit device suffixes or separate output parents
and have the user confirm the final values. Never silently rename a confirmed output directory.

Show a single confirmation covering the complete shared settings and per-device overrides,
output locations, initialization and app-data clearing on each device. It authorizes launching,
monitoring all selected tasks and producing the merged analysis. If a device is not ready, resolve
it or obtain explicit selection of the ready subset before launching.

## Launch and monitor

After confirmation, call kea2_run_test once per selected serial, sequentially. Each call returns
after launch; immediately launch the next device without waiting for the previous test to finish.
Do not send a serial array to this single-device tool. Never launch two tasks on the same phone.
Use kea2_list_tasks to check for existing active tasks on selected serials before launch; if a phone
is already busy, resolve that conflict with the user rather than canceling or starting a second task.
Query queued, running and cancelling separately and follow next_offset for each status. This
read-only scheduling check never authorizes analysis or automatic selection of an existing task.
This is a preflight check, not an atomic device reservation against other clients.

Maintain a batch ledger in conversation: serial, model, confirmed settings, returned task_id,
stamp, output_dir, and current state. A local batch label is not a persisted MCP batch ID.
Never substitute a directory name for task_id. Keep IDs returned on failed starts too.

A definite launch failure on one phone does not revoke authorization to launch the other ready
phones. Record the failure, continue the others, and do not retry automatically. A lost/ambiguous
launch response requires resolving that phone's task identity before any retry; never guess its ID.
If the user stops the workflow, honor that instruction before starting further tasks.

Poll every nonterminal task once per round, then wait approximately 15–30 seconds. Do not finish
monitoring when just one phone completes, and do not keep polling terminal tasks. Report meaningful
changes with device labels. Apply the main skill's status/progress semantics to every task.
Ask which tasks to cancel if a cancellation request has ambiguous scope. An unreachable/unknown
task prevents claiming the whole batch finished; keep other tasks tracked and resolve the blocker.

## Deliver one merged report

When every launch is resolved and every launched task is terminal, invoke kea2-result-analysis
with the explicit list of workflow-bound task IDs and the device ledger. Read that skill's
references/multi-run-report.md alongside its semantics, knowledge and report template. Retrieve
results for failed tasks too; failure alone does not make their results unusable.

Return one report covering all selected devices, including start failures and unavailable results.
Do not ask the user to repeat task IDs or request analysis again. Use source-specific charts and
the merged statistics rules; do not issue separate final answers after each phone finishes.
The deliverable is an agent report in conversation, not a newly generated merged HTML file.
If context is lost, recover from the retained explicit ledger; if unavailable, ask for the task IDs.
