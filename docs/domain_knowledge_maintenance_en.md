# Maintaining domain knowledge for Kea2 agents

This guide defines the entry format, authoring practices, update workflow and validation method for maintainers of Kea2 analysis knowledge.

## 1. Purpose

Domain knowledge guides section 9, “Analysis and recommendations”: which observations deserve analysis, what evidence supports a conclusion, what cannot be inferred, and which recommendations are useful.

Knowledge is not experiment evidence. Before applying a rule, the agent must check the selected task's MCP responses. A description of a possible problem does not establish that it occurred.

Sections 1–8 continue to present results using the report template. They need not reproduce knowledge entries, formulas or reasoning. Entries may prevent unnecessary analysis of normal behavior, but must not arbitrarily change statistics, fill unknown values or add report sections.

## 2. File and format

Maintain knowledge in [domain-knowledge.md](../skills/kea2-result-analysis/references/domain-knowledge.md), using **UTF-8 Markdown**. Chinese or English is acceptable.

Each entry has a level-two heading followed by six fixed level-three headings:

| Heading | Content |
| --- | --- |
| Scope | Applicable checks, modes, execution states, applications or versions |
| Domain knowledge | Relevant mechanisms or experience; distinguish established behavior from heuristics |
| Required data and conditions | MCP tools, sections, fields, applicability conditions and handling of insufficient evidence |
| Analysis rules | Supported conclusions, prohibited inferences and interpretations needing additional evidence |
| Report output requirements | When section 9 should include an interpretation, how to express it and what to omit |
| Follow-up recommendations | Specific justified actions; write “None” when no recommendation is needed |

### Entry identifiers

Use `KEA-CATEGORY-NNN`, such as `KEA-PROP-001`. Number entries within each category, retain the ID when revising an entry and do not reuse allocated IDs.

| Category | Content |
| --- | --- |
| PROP | Property execution, violations and execution errors |
| INV | Invariants and their exceptions |
| COV | Activity/Widget coverage and trends |
| CRASH | Crashes or shared Crash/ANR mechanisms |
| ANR | ANR-specific interpretation |
| GENERAL | Cross-cutting analysis rules |

Maintain a single authoritative entry per rule. Reference related IDs rather than duplicating interpretations. For retired entries, record the replacement ID or preserve the retirement rationale in version history.

## 3. Copyable template

Retain all six headings. Write “None” or “Not applicable” with a reason where appropriate.

```markdown
## KEA-<CATEGORY>-<NNN> · <Title>

### Scope
<Applicable checks, modes, execution states, applications or versions.>

### Domain knowledge
<Mechanism or experience. State assumptions for heuristics; avoid asserting inevitable causes.>

### Required data and conditions
- Obtain <fields or evidence> through <MCP tool and section>.
- Apply this entry when <conditions> all hold.
- When evidence is insufficient or conditions cannot be checked, <handling>.

### Analysis rules
- Supported conclusion: <evidence-backed interpretation>.
- Not inferable from this evidence alone: <conclusions to avoid>.
- Additional evidence: <information to check, if needed>.

### Report output requirements
- <When an interpretation belongs in section 9 and how to express it.>
- <Routine explanations to omit; do not force output when inapplicable.>

### Follow-up recommendations
<Concrete checks or improvements justified by evidence; write “None” when unnecessary.>
```

## 4. Authoring principles

1. **One decision problem per entry.** Keep “preconditions satisfied but property not executed” separate from unrelated coverage rules.
2. **Use verifiable conditions.** Name actual MCP fields, units and relevant ranges. Avoid vague conditions such as “low coverage.” Thresholds need a team-supported basis; do not invent them to complete an entry.
3. **Separate mechanisms, observations and hypotheses.** Recording behavior is a mechanism; this run's values come from MCP; possible causes need further evidence.
4. **Do not force applicability.** Missing, inapplicable and zero are different. If required data is unavailable through MCP, document the need rather than directing the analysis agent to source code, HTML or raw files.
5. **Normal behavior need not generate analysis.** A rule can prevent a mistaken conclusion without producing a paragraph. Do not mechanically copy knowledge into reports.
6. **Tie recommendations to evidence.** State the problem an action addresses and how it can be checked. Write “None” instead of routinely recommending longer tests or reruns.
7. **Limit application-specific knowledge.** Identify the package, known versions or business conditions to prevent inappropriate reuse.

Authors may cite mechanism documentation or team-approved experience in “Domain knowledge.” Researching and maintaining entries does not authorize the analysis agent to inspect experiment source code. Experiment facts still come exclusively from MCP.

## 5. Example: no crash log for a normal zero-exception run

This example illustrates the format; it does not itself add the rule to the knowledge file loaded by the agent.

```markdown
## KEA-CRASH-001 · No crash log when no exceptions occur

### Scope
Completed runs with zero Crash and ANR counts returned by MCP and no contradictory findings.

### Domain knowledge
Crash/ANR logs are produced for exceptions.
An absent log is normal when no Crash/ANR occurred.

### Required data and conditions
- Check execution.status=completed through kea2_get_report.
- summary.observed_crash_occurrences and summary.observed_anr_occurrences are both 0.
- Crash/ANR findings from kea2_query_report agree with these results; retrieval scope
  must support the check. Unread pages do not mean no records.
- Null counts, read failures or contradictory records do not qualify.

### Analysis rules
- Do not infer missing experiment data or a collection failure solely from log absence.
- Read failures, malformed files and interrupted runs require separate assessment.
- Conclusions concern this run, not freedom from defects in every possible scenario.

### Report output requirements
- Present Crash: 0 and ANR: 0, with “None” in the details.
- Do not append missing-log explanations or generic disclaimers in section 9.
- Without another relevant problem, produce no separate analysis paragraph.

### Follow-up recommendations
None. Log absence alone does not justify repairing collection or rerunning the test.
```

“Domain knowledge” explains the interpretation; “Report output requirements” determines what deserves presentation. Internal reasoning boundaries need not become user-facing disclaimers.

## 6. Validate application

Reanalyze an existing experiment with an explicit task_id; a new device run is usually unnecessary. For important rules, cover:

| Case | Expected behavior |
| --- | --- |
| Conditions met | Correct interpretation; output or omission follows the entry |
| Conditions not met | No inappropriate application or generalization |
| Insufficient or contradictory data | No forced conclusion; explain only material evidence gaps |

For maintenance validation, ask:

> Use kea2-result-analysis to analyze task <actual task_id>. Separately list the knowledge IDs applied, the matching MCP conditions and unmet conditions so I can verify rule application.

This diagnostic information need not appear in ordinary reports. Check for fewer unsupported inferences, missed important problems or new unnecessary explanations. Correctly omitting analysis for normal behavior is also successful application.

Results depend on the actual client and model. Markdown checks cannot substitute for report behavior validation.

## 7. Responsibilities of related files

| File | Responsibility |
| --- | --- |
| `SKILL.md` | When to read knowledge, query results and complete analysis |
| `data-semantics.md` | MCP field meanings, counting conventions and limitations |
| `domain-knowledge.md` | Domain mechanisms, applicability, reasoning boundaries and recommendations |
| `report-template.md` | Nine-section structure, table columns and presentation |

Keep these responsibilities separate so knowledge can evolve independently without duplicating the same rule across files.
