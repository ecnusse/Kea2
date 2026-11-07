# Analysis report template

Use this template only after the user explicitly supplies a concrete task_id for the analysis.
If it is missing, ask for it and stop; never fill this template using an automatically selected recent task.

Write in the user's language. Adapt depth to the request; for a focused investigation, briefly mark
unrelated sections out of scope rather than expanding into an unsolicited full review.

## Experiment context

- Task ID, contract version, snapshot ID(s), execution status; provisional or finished.
- Target and relevant saved settings, separate from observed duration/events.

## Data quality and scope

- Missing/partial/invalid sources and material warnings, with their implications.
- Categories inspected; pages/records examined versus returned totals where known.
- Trace/image reads completed, partial, unavailable or unsupported by the client.
- Sampling basis, remaining pages and budget limits. Do not imply a complete scan.

## Execution and coverage

### Property statistics

Build this table from `kea2_query_report(section="checks", filters={"kind":"property"})`.
Include all returned properties, not just failures. Use the returned values without estimating
missing counts or recomputing them from raw data. Translate column labels to the user's language.

| Property | Precondition Satisfied | Executed | Passes (derived) | Fail | Error | Evidence |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Returned name | precond_satisfied | executed | pass_count | fail | error | MCP source/key and snapshot |

The example row describes field mappings, not data to reproduce in the report.

### Invariant statistics

Build this separate table from checks with kind=invariant. Invariants do not collect precondition,
execution or pass counts; do not add those columns or infer them from execution segments.

| Invariant | Fail | Error | Exception details / evidence |
| --- | ---: | ---: | --- |
| Returned name | fail | error | Retrieved finding IDs / brief exception detail, or explicitly not retrieved |

Show zero failures only when the returned data supports zero. Do not claim an invariant passed
because fail/error are zero. For details use findings filtered by check_name and type=invariant,
then get_finding as needed. If details were not inspected, disclose that instead of inventing them.

For each table state displayed/total records, source availability and snapshot. Follow next_cursor;
if the budget prevents completion, label it a partial table. If no usable records exist, explain
missing/unavailable versus a readable empty collection, and do not invent a zero row. Keep kind=unknown
in a separate legacy/unknown table when present, rather than classifying it as property or invariant.
Do not sum a partial table and present it as a whole-experiment total. All facts and evidence must
come from Kea2 MCP responses, never independent source-code or raw-file inspection.

### Coverage

- Activity coverage, widget counts and property-start trends relevant to the question.
- Describe unexecuted properties or observed plateaus without assuming a cause.

## Main findings

For each investigated occurrence: type/check, observed behavior, trace evidence, relevant context
and image observations if actually inspected. Clearly distinguish occurrence counts from unique bugs.

Citation format (use actual returned values):

`task=<task_id>; snapshot=<snapshot_id>; finding=<finding_id>; source=<artifact>:line=<line>`

For a configuration or aggregate use source/key or query section and filters instead of a finding ID.
For an image include artifact_id. Omit nonexistent locator fields rather than filling them in.
If no findings were returned, qualify that statement by source availability and query scope.

## Hypotheses and limits

When applying packaged analysis knowledge, cite its entry ID and the MCP fields that met its conditions.

State the inference separately from observations, supporting evidence, plausible alternatives and
what is still needed to confirm it. Avoid arbitrary numerical confidence scores and unsupported
severity labels. If evidence supports no useful hypothesis, say so.

## Next validation

Prioritize concrete missing evidence, reproduction checks or follow-up queries. These are proposals,
not permission to launch tests or mutate files. End with remaining analysis gaps, not a blanket pass.
