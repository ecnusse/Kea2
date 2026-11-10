---
name: kea2-test
description: Guide a user interactively through Kea2 Android testing, explain and confirm every applicable startup parameter, start and monitor the test through MCP, then produce an evidence-based report. Use when the user wants to run Kea2, including “我想用kea2进行测试”.
metadata:
  version: "1.2.0"
---

# Interactive Kea2 testing

Use the user's language. Complete preparation, parameter collection, confirmed launch,
monitoring and result analysis as one workflow. Do not require the user to orchestrate tools.
The deliverable is the analysis report, not merely a successful launch or an end-of-test status.
Unless the user explicitly changes scope or a concrete blocker prevents continuation, keep working
through analysis in the same workflow. Do not end with “测试已结束，要不要分析？” or only an
exit code, file path or get_status counters.
This workflow covers every parameter exposed by `kea2_run_test`, not every CLI option.
Requires Kea2 MCP and the installed sibling `kea2-result-analysis` skill including references.
Before launching, locate and read that skill by client discovery or sibling `../kea2-result-analysis/SKILL.md`;
if missing, explain how to install both skills and resolve the missing analysis instructions first.
Do not install packages, write properties or change client configuration without user authorization.

## Prepare and collect

1. Discover the actual MCP tool names (client prefixes may differ). Call `kea2_check_device`
   and `kea2_check_test_setup` without optional selections to obtain working directory and defaults.
   If tools are absent, explain the missing MCP connection and wait; do not pretend to execute them.
2. Read [parameter guide](references/parameters.md) and [interaction guide](references/interaction-guide.md).
   Maintain a ledger of every current run-tool parameter: value, applicability, and state
   (`pending`, `user_value`, `accepted_default`, `not_applicable`). Tool-discovered values are
   candidates, not user choices. Inspect the actual tool signature for added parameters; explain
   and ask about those too. Do not silently drop or supply a new parameter.
3. Ask for every missing applicable parameter, even if only one device exists. Explain purpose,
   units/choices, default behavior and consequential effects. Ask in related groups of 2–4 questions,
   using the client's interactive question facility if available, otherwise plain conversation.
   Stop and wait for answers; elapsed time never counts as acceptance. Do not ask already answered
   questions. Accept multiple answers in free text and explicit “remaining defaults” as batch consent
   for defaults (not for missing required device/app identity). Show those defaults in the final summary.
4. Confirm device and packages. `kea2_list_apps` lists package IDs, including system packages,
   not display names. Follow next_offset as needed. Do not guess app names from package strings;
   if the user cannot identify one, ask them to supply/confirm its package ID.
5. Ask pure fuzzing vs existing properties before conditional script questions. Revisit dependent
   fields if an earlier choice changes. Do not inspect/import the user's scripts; use setup validation.
   Ask whether to use no Activity restriction, whitelist or blacklist (mutually exclusive).
6. Resolve every pending applicable field. Null is only an accepted choice to inherit behavior,
   not a substitute for asking. Distinguish engine defaults from observed runtime behavior.

## Validate and confirm

Call `kea2_check_test_setup(serial, packages, options)` with the collected run parameters,
excluding serial/packages from options. Explain issues and correct only affected fields.
For an uninitialized project, explain that `kea2_init` creates configs and quicktest.py; include
this write in the launch confirmation. Existing configs are never automatically force-overwritten.
The configured server working directory is authoritative; changing output_dir does not change it.
Do not proceed with unresolved device, app, parameter, script or Activity-list errors.

Show the complete ledger with final values/default choices and reasons for non-applicable fields,
including output parent, pending initialization and whether data will be cleared. Explain that
clear_app_data deletes login state, settings and local data for ALL selected packages irreversibly.
Ask for explicit confirmation to prepare, start, monitor and analyze this experiment.
No clearing, initialization or launch before confirmation. Parameter changes invalidate that summary.
After confirmation, initialize only if needed, rerun setup, and require ready=true before launch.
If new issues require changed settings or destructive actions, obtain a new confirmation.

## Run and follow this experiment

Call `kea2_run_test` once with confirmed settings. Record its exact task_id, stamp, output_dir,
settings and returned state in conversation. This is the task binding for this authorized workflow.
Never choose a latest/only task to replace it. If a launch response is lost, do not blindly retry;
list candidate tasks and require the user to resolve ambiguity before another launch.

Use `kea2_get_status` with this task_id. Wait approximately 15–30 seconds between polls using
client-supported waits; no tight loops. Give concise updates on meaningful progress or problems.
Interpret status progress correctly: `progress.executed`, `progress.fail` and `progress.error`
sum check fields already written to the result JSON. They are not Fastbot/Monkey exploration
steps, completion percentages or live device activity. They do not establish invariant execution
counts or Crash/ANR totals. In pure fuzzing, zero or absent check counts do not mean the test
failed to start, explored zero steps or stalled. This also applies to property tests whose checks
have not run or whose results have not yet been written. Use status and phase together for
process/task state, without claiming process liveness proves UI exploration. result_available
only means the result file exists, not that it is complete or parseable. Do not restart or cancel
because check counts are zero or unchanged. If actual exploration progress is needed, query
MCP report observation or steps; describe available Monkey counters as recorded observations,
not real-time totals. If unavailable, say exploration step data is not currently available.
While running/queued/cancelling, continue waiting unless the user requests otherwise. Do not
require the user to send “check status” or “analyze results”. Cancellation requires a user request;
call `kea2_cancel_test`, observe the result and describe available partial evidence if analysis is desired.
Status failed may reflect property violations/crashes: inspect exit information and result availability,
not just the status label. Terminal state leads to analysis, not automatic rerun. If status is unknown,
unreachable or contradictory, explain the issue and ask how to proceed rather than poll forever.
Clearing failures may have already cleared some apps: report returned details, never retry automatically.

This is a live client workflow, not a persistent scheduler. If the client cannot keep waiting,
report the bound task_id and how to resume; do not claim unattended completion. On resumption,
reuse a reliably retained binding only if the user asks to continue this workflow; otherwise ask.

## Analyze and deliver

When get_status reports terminal execution (finished/failed, or a completed cancellation whose
results remain in scope), move immediately to the following steps. A status update may be an
intermediate message, not the final deliverable. A failed status is not by itself an analysis blocker.

1. Invoke the installed `kea2-result-analysis` skill. If the client has no skill invocation tool,
   read and follow its SKILL.md directly; another skill will not run just because you mention its name.
   Reuse the exact workflow-bound task_id without asking the user to repeat it. This is an authorized
   full experiment analysis unless the user requested a narrower report. Independent history requests
   still require task selection; hybrid parents follow the analysis skill's child-selection rule.
2. Read its references/data-semantics.md, references/domain-knowledge.md and
   references/report-template.md before interpreting and writing the report. Re-read relevant
   instructions if context was lost during monitoring. These instruction files are allowed reads;
   raw experiment files are not. If the installed analysis skill still rejects a workflow-bound ID,
   explain the version mismatch and request updating both skills, rather than silently stopping.
3. Call kea2_get_report for this ID even if get_status.progress is empty or result_available is false:
   other result sources may still be readable. Check errors, contract, snapshot and availability.
4. Follow the analysis skill's broad-analysis queries: configuration, checks, activities, trends,
   property_execution_trend and findings when applicable and available. Include non-failing checks;
   do not substitute get_status counters or a file inventory for these queries. Follow pagination
   within the analysis budget, and explicitly disclose incomplete tables or sampled findings.
5. For selected findings retrieve details and available evidence according to the analysis skill.
   Describe images only when image content actually reaches the model; metadata alone is not viewing.
6. Produce the report in the conversation using the report template. Keep all relevant report
   sections, marking unavailable or inapplicable data with reasons instead of dropping the analysis.
   Pure fuzzing still needs execution, coverage, crash/ANR evidence and limitations; explain the
   absence of property/invariant records rather than inventing rows or skipping the entire report.

Before ending, check that the answer includes: this task's identity and execution outcome; data
quality and inspected scope; all nine template sections (overview, Activity coverage trend,
widget trend, property execution trend, Activity details with visits, Crash/ANR details,
property violation details, Property/Invariant statistics, and analysis/recommendations).
Use explicit applicability/availability explanations where needed. Every numerical result must
come from MCP responses or the template's explicitly labeled structured-data derivations. “Complete report”
means these sections are addressed, not that unread records may be presented as fully analyzed.
If tools, connection, contract or result availability block analysis, identify the failed operation,
what was and was not obtained, and the next recovery step. Never claim analysis completed when
only monitoring completed. Explicit user requests to stop or omit analysis take precedence.

All experiment facts must come from Kea2 MCP result tools. Do not inspect source, HTML, raw
logs or task databases through other tools. Read professional knowledge and the report template
from the analysis skill. Produce property/invariant tables, evidence-backed findings, data gaps
and next steps. Clearly label partial results and never equate missing data with zero failures.
Finish with a self-contained report identifying this task and the scope actually examined.
