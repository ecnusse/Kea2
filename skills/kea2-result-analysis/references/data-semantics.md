# Result semantics — contract 1.5

Read before interpreting an experiment. For exact types and unfamiliar fields use the live
kea2_get_result_schema tool. Schema discovery describes formats, not proof that all collections exist.

| Data | Interpretation |
| --- | --- |
| availability | available/missing/partial/invalid/unreadable/too_large describe individual sources |
| data_completeness=available_sources | Implemented sources were available, not proof of a completed test or complete analysis |
| null | Unknown or not applicable according to the field; never silently zero |
| empty query items | Interpret with source availability and filters; not automatically observed absence |
| checks.kind | property, invariant or unknown; preserve legacy unknown classification |
| invariant precond_satisfied/executed/pass_count | Not applicable: null; pass_count_basis=not_applicable |
| invariant fail/error | Recorded failures/errors; query findings for detailed occurrences and traces |
| invariant execution_count/executed_check_count in summary | Not applicable: null |
| property pass_count | Derived max(executed − fail − error, 0), not independently logged success evidence |
| violated_check_count | Distinct checks with fail/error, not occurrence count or confirmed unique defects |
| findings | Individual occurrences, not deduplicated defects; script errors may have environment or test causes |
| Activity coverage | Percentage 0–100; inventory and visit counts available separately |
| widget coverage | Number of distinct triggered widgets, not percent of all possible widgets |
| property_execution_trend | Distinct non-invariant properties started by each sample, not attempts or passes |
| monkey_step | Counter shared by multiple events; use step ID to identify individual events |
| execution segment | Explicit start/end references; missing boundaries cannot establish a complete interval |
| context steps | Nearby records; interleaved invariant or Monkey events need not belong exclusively to the property |

## Configuration, state and time

execution.requested_parameters contains saved request inputs. configuration contains fields from
options.json or bug_report_config.json with document/key provenance. Neither proves device execution.
observation contains log-derived first/last times, elapsed seconds, maximum Monkey counter and record count.
Configured running_mins is not actual duration. Report configuration test_time is configuration-save time.
Preserve unspecified timezones rather than inventing UTC conversion.

Configuration Infinity may be represented as {"$nonfinite":"Infinity"} with encoding=tagged_nonfinite.
It is not a literal string or zero; retain encoding and warnings. Raw configuration disagreements are not
resolved automatically. A missing random seed cannot be reconstructed from defaults.

New report execution status interprets exit codes 0–3 as completed testing (with finding flags),
while other codes may indicate execution_error. Legacy status tools can label nonzero codes failed.
Check code, status and evidence together; finding defects does not itself mean the MCP call failed.
Report metadata is task-store information, not a new process-liveness probe.

## Evidence and source quality

source.artifact is result-relative, line is one-based, and key locates a JSON field. Preserve them.
Evidence status resolved means an explicit association was established, not a proven cause.
ambiguous lists candidates; unavailable provides no reliable target. Screenshots are registered from
explicit log references only. Successful metadata retrieval does not show that image contents were read.

Text offsets count Unicode characters. Preserve next_offset when continuing a trace or artifact read.
Partial logs count readable records only. Widgets retain raw text when unescaped delimiters prevent
reliable parsing. Never turn a parse warning into a confirmed app bug.

Files are read independently; snapshot IDs detect changes but do not give multi-file transaction isolation.
Source/text limits are currently 64 MiB and images 8 MiB. too_large is a limitation, not an empty file.
