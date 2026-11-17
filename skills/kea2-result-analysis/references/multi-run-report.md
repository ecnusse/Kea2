# Multi-run report

Use for two or more explicitly selected tasks, including the full device/task ledger passed from
kea2-test. Produce one report in the user's language. Apply the main skill's MCP-only boundary,
knowledge, evidence inspection and user-facing formatting rules to each source experiment.

## Collect a consistent source set

Call kea2_get_report for every distinct task ID. Preserve a map of task_id to its own snapshot_id;
different experiments naturally have different snapshots. Recover stale data only for the affected
task, then recompute any aggregates using it. Avoid counting the same result directory twice if
aliases identify the same experiment; retain those aliases in the internal source mapping.

Keep device serial/model, task ID, source directory and outcome for every selected device, including
failed starts. Separate report groups for different package sets. Unknown package identity or
conflicting app versions/check definitions must be resolved or explicitly limit combined claims;
do not assert equivalence merely because check names match.

Query complete, unfiltered activities, widgets and checks for each usable source, following
next_cursor to exhaustion. Fetch findings by type and preserve all source identifiers. The normal
20-call investigation budget applies per task, not once for the batch. Complete aggregation inputs
take priority over optional screenshots and detailed investigations. If pagination exceeds the
budget, request a larger scope or label the affected aggregate incomplete; never extrapolate from
a page or report it as the full total. Available empty inventories are valid; unavailable, partial
or too_large inventories do not establish empty sets. Missing optional crash logs follow the
domain knowledge and returned structured counts, not a blanket missing-data warning.

## Merge rules

1. **Activity coverage:** let A be the union of activity names with in_inventory=true across
   complete activity records, and C the union with covered=true. Coverage is 100 * |C| / |A|,
   rounded to two decimals. Never average or add percentages. With an empty A, report not
   applicable; inconsistent inventories (C outside A) require qualification, not a silently capped
   percentage. If any participating source inventory is incomplete, do not label the union final.
2. **Activity visits:** sum returned visit_count by exact Activity name across sources. Apply
   the single-run template's missing-visit display convention only to a readable source inventory;
   missing whole sources are not zero. Show combined coverage, summed visits and covered-on
   devices. Retain per-source values internally.
3. **Widget coverage count:** union the nonempty, whitespace-trimmed WidgetRecord.raw strings
   from the complete widgets pages, using exact string equality as the original merger does for
   widget inventory lines. Treat strings as opaque identifiers, including ambiguous/invalid parsed
   records; do not interpret their contents or deduplicate by resource_id, display text, task-local
   id, or parsed fields. Count the union, not summed per-run totals or trend endpoints. This is a
   count, not a percentage. If full inventories cannot be read, show per-device counts and say
   the combined unique count is unavailable rather than estimating it.
4. **Checks:** group by exact name and sum precond_satisfied, executed, fail and error over
   contributing sources. For properties compute passes as max(merged executed - merged fail -
   merged error, 0), matching the existing merger. Count distinct property names for the total,
   names with executed>0 for executed properties, and names with fail+error>0 for violations.
   Keep invariant rows separate: sum only fail/error; their execution/precondition/pass fields
   remain not applicable. Never fabricate invariant execution counts. Conflicting kinds for one
   name must be split and labeled rather than silently combined. Null applicable counters or
   incomplete sources make the corresponding totals incomplete. A check absent from a complete
   inventory contributes no occurrences; absence from an unread inventory is unknown.
5. **Crash/ANR:** keep each experiment's structured counts and source-qualified occurrences.
   Sum known per-source counts for the batch. Use (task_id, finding_id) to avoid counting repeated
   retrieval of the same record. Never collapse similar exceptions across different result
   directories into one occurrence. Retain device, task and source directory for every event,
   and use kea2_get_finding for actual exception/trace details. Sampling traces does not deduplicate
   findings or change totals. The MCP occurrence total is not a unique root-cause count: do not
   claim it reproduces the HTML merger's additional within-directory trace-based deduplication.

Only combine fully retrieved inputs for exact set/count aggregates. If some experiments fail to
produce data, retain them in the device summary and label any available-subset aggregate clearly.
Never turn a partial subset into a claim about all selected phones.

## Report layout

Adapt the existing nine-section report template as follows, keeping internal evidence IDs and
counting explanations out of the user-facing tables unless requested:

1. **Test overview:** selected devices and outcomes; a per-device summary table with serial,
   task_id, duration, steps, property results, Activity coverage, widget count, property/invariant
   violations, Crash and ANR. Follow with combined coverage, unique widgets and check/exception
   totals where established. Label summed device testing time separately from elapsed batch time;
   do not sum durations and call it wall-clock duration.
2. **Activity coverage trends:** label each MCP chart with its device. These are per-device curves,
   not a combined curve. Do not average curves or align independent Monkey counters as wall time.
3. **Widget trends:** per-device MCP charts, with the same image/link fallback as the single-run template.
4. **Property execution trends:** per-device MCP charts where applicable; pure fuzzing follows domain knowledge.
5. **Activity details:** merged names, covered status, summed visits and covered-on devices.
6. **Crash/ANR details:** preserve source device/task, actual exception details and inspected evidence.
   If none, say none according to the established count semantics.
7. **Property/invariant violation details:** retain affected devices and source tasks for each check,
   with actual available descriptions/evidence. Provide a source mapping like the original merged report.
8. **Property and invariant statistics:** merged tables using the rules above; show device-specific
   differences where needed to avoid hiding failures. Do not add evidence or basis columns.
9. **Analysis and recommendations:** apply domain knowledge; distinguish observations from hypotheses.
   Device differences alone do not establish device-specific bugs or a causal explanation.

Keep task/device provenance visible where it helps locate problems, while retaining detailed
snapshot/record locators internally. Use returned HTML/image paths only; do not generate or claim
a merged HTML report through a nonexistent MCP tool. Completing this report does not require
editing original reports or adding a merged experiment to the task database.
