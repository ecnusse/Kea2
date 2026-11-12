# Test report template

Write the final report in the user's language, translating all headings and column labels.
Use a concrete task_id explicitly selected by the user or bound to the launch in the confirmed
kea2-test workflow. The workflow binding needs no repeated ID confirmation. Otherwise ask and
wait; never automatically select a latest or only task.

For a full experiment report include all nine sections below, in order. Do not reproduce
placeholder rows. Mark unavailable or inapplicable sections with reasons. For an explicitly
focused request, identify unrelated sections as out of scope. All facts come from Kea2 MCP
responses, never source, HTML or independently parsed files. Explain material gaps, partial
reads and sampling briefly in everyday language; complete structure does not mean a full scan.
Keep exit codes, finding flags, contract versions, snapshot hashes, raw availability/completeness
values, warning codes and source locators internal unless the user requests technical diagnostics.
Do not add basis/evidence/source columns to tables. Preserve actual exception descriptions,
relevant stack excerpts and inspected screenshots for problems; hiding metadata must not hide problems.

Sections 1–8 present results: metrics, charts, tables and actual exception details. Do not append
metric tutorials, pass-count formulas, comparisons between precondition and execution counts,
cross-section interpretations or recommendations. Keep only short labels/units and material
missing-data or sampling notices needed to read the results correctly. All useful interpretation
belongs in section 9. Omit routine explanations that add no actionable insight rather than moving
them wholesale to the end. The semantic rules below guide the agent internally, not report prose.

## 1. Test overview

Identify task_id, packages/device and the execution outcome in plain language.
Label provisional or incomplete reports and separate requested settings from observations.

### Basic metrics

| Metric | Result |
| --- | --- |
| Total test time | Observed duration or unavailable |
| Executed exploration steps | Recorded maximum Monkey step or unavailable |
| Passed properties / total properties | P / N, or unavailable / N |
| Activity coverage | Percentage or unavailable |
| Widget coverage | Unique triggered widget count |

Internal metric rules (do not reproduce as a basis column): observation.log_duration_seconds
is the recorded log interval. If deriving elapsed time from valid execution.started_at/finished_at,
label it process elapsed time separately. Configured running_minutes is only the requested limit.
Use observation.max_monkey_step for steps, never get_status.progress.executed. Use
summary.activity_coverage_percent and summary.unique_triggered_widget_count for coverage.
Widget coverage is a count, not a percentage: no reliable total-widget denominator is provided.

For this report, P counts distinct properties with executed > 0, fail = 0 and error = 0.
Properties with any failure/error or no executions do not qualify. Derive P only from complete,
available, same-snapshot structured checks of kind=property. Do not routinely explain the pass
criterion or label the table value as "derived". N is summary.checks.property.count,
not execution_count. Never sum pass_count
or subtract violated_check_count from N to obtain P. If pages or sources are incomplete, show P
as unavailable/partial without extrapolating. A confirmed readable empty inventory means not
applicable (0 properties), not 100% passed. Exclude invariants and unknown-kind checks.

### Problem records

| Metric | Count |
| --- | ---: |
| Property violations | Recorded assertion-failure occurrences |
| Invariant violations | Recorded assertion-failure occurrences |
| Crashes triggered | Recorded occurrences or supported detection outcome |
| ANRs triggered | Recorded occurrences or supported detection outcome |

Use summary.checks.property/invariant.fail_occurrences and summary.observed_crash_occurrences /
observed_anr_occurrences. For crashes and ANRs, a null count is not itself zero. A supported
display fallback is "0 (none detected)" when MCP execution metadata confirms a completed run,
exit_code is 0 or 1, finding_flags.crash_or_anr is explicitly false, the crash source is missing
(not invalid, unreadable or too_large), and no returned findings contradict this outcome.
This reports the run's detection outcome, not a measured count from a missing log. Do not show
the internal flags or missing-source status. For imported/unknown runs, read failures, contradictory
results or other unsupported cases, write "Cannot determine" and briefly explain the limitation.

Also disclose property/invariant error_occurrences separately; do not hide errors or relabel them
as assertion violations. If reporting violated_check_count, label it distinct checks with fail OR
error, not fail-only count. Occurrences are not unique bugs. Missing is unavailable, not zero;
counts from partial sources must be labeled observed partial counts.

## 2. Test coverage trend

Query trends with metric=activity_coverage_percent. Show Activity coverage over Monkey steps
as a chart when supported, otherwise a table. Put interpretations of increases or plateaus in
section 9. Do not invent intermediate samples, extrapolate unread pages or convert steps
to elapsed time without evidence.

| Recorded Monkey step | Activity coverage (%) |
| ---: | ---: |
| Returned monkey_step | Returned value |

Disclose queried/total/displayed samples and any downsampling rule. Missing samples are not zero.

## 3. Widget coverage trend

Query trends with metric=unique_triggered_widget_count. Show a chart or table of unique triggered
widget counts over Monkey steps. Use a count label, not a percentage label; no explanatory paragraph is needed.
Apply the same pagination and downsampling disclosures as section 2.

| Recorded Monkey step | Unique triggered widgets |
| ---: | ---: |
| Returned monkey_step | Returned value |

## 4. Property execution trend

Query property_execution_trend. This counts distinct properties that have started by each step,
not execution attempts, completed/passed properties or invariant checks.

| Recorded Monkey step | Distinct properties started |
| ---: | ---: |
| Returned monkey_step | Returned executed_property_count |

Use a chart or table; put interpretations of progression in section 9. Pure fuzzing with
a confirmed empty property inventory is not applicable. Missing step data means an unavailable
trend, not evidence that no property ran.

## 5. Activity coverage details

Query activities without covered=true filtering; show both covered and uncovered entries.
Group rows by coverage if helpful, and disclose displayed/total records.

| Activity | Covered? | Visit count |
| --- | --- | ---: |
| Returned name | Returned covered | Returned visit_count or supported display value |

A null visit_count means no count was recorded. If a valid coverage sample explicitly reports
covered=false for an in_inventory=true Activity, display "0 (not covered)" as the coverage-based
presentation. If covered=true and visit_count=null, display "Not recorded"; never turn this into
zero or mark the Activity uncovered. Retain uncertainty for incomplete/invalid coverage data.
The inventory and last valid sample do not establish that every Activity in the app is known.

## 6. Crash and ANR details

Query findings for type=crash and type=anr separately. Write “None recorded” for each only when
readable sources and the queried scope support absence, or the completed-run fallback in section 1
applies. Otherwise explain the relevant limitation without exposing raw status fields.
For every investigated occurrence include:

- Type, process, recorded time and Monkey step where available.
- Actual exception/ANR description and relevant stack trace from kea2_get_finding.
- Explicitly linked operation context and available images from kea2_get_artifact.
- What the evidence shows and any material remaining uncertainty.

Distinguish occurrences from unique defects. If sampled, state the selection basis and inspected/
total counts, and identify uninspected records. Image metadata alone does not permit describing
an image; the image content must actually reach the model.

## 7. Property violation details

Query findings with type=property and state=fail. Include property execution errors (state=error)
in a separate subsection. Retrieve actual exception text, stack and available context with
kea2_get_finding, and explicitly linked artifacts as needed.

For each investigated record show property name, failure description, recorded step/
time where available, relevant stack/context excerpts and image observations only if inspected.
Do not invent expected behavior or root causes. For no violations use the availability-qualified
absence rule from section 6. Explain discrepancies between summary counts and retrieved findings;
do not conceal missing evidence. Disclose sampled or incomplete investigation.

## 8. Property and invariant execution statistics

Query checks without has_findings filtering, including successful and unexecuted properties.
Use returned per-check statistics; do not reconstruct them from traces or raw files.

### Property statistics

| Property | Precondition Satisfied | Executed | Passes | Fail | Error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Returned name | precond_satisfied | executed | pass_count | fail | error |

Use the returned pass_count directly. The service computes max(executed - fail - error, 0),
the same convention as the HTML report; it is not an independently logged success counter.
Label the column simply "Passes" ("通过次数" in Chinese). Do not append the formula or a
discussion of attempts versus unique scenarios below the table. Explain the formula only when
explicitly asked, or in section 9 if essential to understanding a material inconsistency.
This attempt count differs from P in section 1.

### Invariant statistics and violation evidence

| Invariant | Fail | Error |
| --- | ---: | ---: |
| Returned name | fail | error |

Invariants provide no precondition, execution or pass counts; do not add those columns. Retrieve
findings with type=invariant and check_name, and use get_finding/available artifacts to substantiate
violations and errors in prose below the table as in section 7. Disclose uninvestigated records.
Interpret zero fail/error according to KEA-INV-001 in the domain knowledge, including its
applicability conditions. Do not infer execution/pass counts or conclusions about untested states.

Follow pagination within budget and label partial tables with displayed/total rows. Explain only
material source limitations in plain language. Distinguish readable empty inventories from missing sources;
do not invent zero rows. Show unknown-kind checks separately if present.

## 9. Analysis and recommendations

Summarize useful conclusions supported by the preceding sections: coverage gaps, unexecuted
properties, exceptions and trends. Separate observations, hypotheses, alternative explanations
and concrete next validation. Avoid arbitrary confidence percentages, unsupported severity labels
or blanket “all tests passed”. Recommendations do not authorize reruns or changes. If evidence
supports no useful hypothesis, say so.

This is the only section for count comparisons, trend interpretations, cross-section synthesis
and advice. Include them only when they help the user understand a meaningful result or choose
a next action. Do not routinely repeat that passes are computed, executions are attempts, or
precondition counts can exceed executions. Such a difference alone does not establish a defect,
a scheduling cause, or a precise number of usable execution opportunities.

When applying professional knowledge, verify its conditions against MCP facts and explain the
reasoning in ordinary language. Keep entry IDs, snapshot IDs, record IDs and source locators in
the analysis context for traceability; include them only if the user asks for an audit or diagnostics.
Mention only material data gaps, partial reads and useful remaining validation needs. Do not dump
routine encoding warnings or internal metadata. One inaccessible artifact must not erase unrelated
valid evidence. Do not suggest that increasing reporting/sampling frequency itself improves coverage.
