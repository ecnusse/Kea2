# Kea2 result analysis skill user guide

[中文](result_analysis_skill_cn.md)

`kea2-result-analysis` helps an agent retrieve Kea2 experiment data, inspect evidence and produce a sourced analysis report.

## Before you start

- Connect a Kea2 MCP service supporting result contract 1.5.
- Have an existing experiment task_id, such as the ID returned when starting a test through MCP.
- Install the wheel into the Python environment running MCP and restart the service after updates.

## Install the skill

Installing the wheel does not install the skill.

1. Find `skills/kea2-result-analysis` in the Kea2 repository.
2. Select a directory below: project scope applies to that project; personal scope serves multiple projects.
3. Copy the complete folder, including SKILL.md and references.
4. Open your test project and start a new session. Select the skill as shown below; restart if it is absent.

| Client | Project skill root | Personal skill root | Discover/invoke |
| --- | --- | --- | --- |
| Codex | `<project>/.codex/skills/` | `~/.codex/skills/` | Open the project, select/invoke `$kea2-result-analysis`; restart if absent |
| Claude Code | `<project>/.claude/skills/` | `~/.claude/skills/` | Start in the project and invoke `/kea2-result-analysis` |
| Cursor | `<project>/.cursor/skills/` | `~/.cursor/skills/` | Use `/kea2-result-analysis` or select it with `@` in Agent chat |
| GitHub Copilot in VS Code | `<project>/.github/skills/` | `~/.copilot/skills/` | Check Open Customizations in Chat; explicitly request kea2-result-analysis in natural language |


`~` is the home directory of the user running the client. The Codex personal installation on Windows is
`%USERPROFILE%\.codex\skills\kea2-result-analysis\SKILL.md`, with references alongside it.
Choose one installation location to avoid duplicate or outdated copies.
For remote, WSL or container sessions, install on the environment running the agent.
Consult your cloud client's documentation for skill synchronization.

Client help: [Codex](https://learn.chatgpt.com/docs/build-skills), [Claude Code](https://code.claude.com/docs/en/skills), [Cursor](https://cursor.com/help/customization/skills), [VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills). UI locations vary by version.

## Analyze an experiment

New CLI runs register automatically. Explicitly request `kea2_register_result` for a historical directory;
choose the exact directory/stamp or alias when candidates or ID conflicts are returned. Registration still
requires explicit task selection before analysis. Select a child for hybrid parents.
See [task registration](task_registration_en.md).

If you do not know the task ID, ask the agent to call `kea2_list_tasks`. It returns 20 tasks per page by default, with optional status filtering and pagination. Choose a concrete `task_id` from the list before analysis starts; the agent must not automatically analyze the latest task. Discovery covers tasks registered in the current MCP user environment, without scanning disk for historical results.

In Codex, enter:

> Use $kea2-result-analysis to analyze task <actual task_id> and produce a sourced report.

In Claude Code or Cursor, select `/kea2-result-analysis`, then provide the task ID and request.
In other clients, select the skill and ask:

> Use kea2-result-analysis to analyze task <actual task_id>.

Replace the placeholder with your experiment ID. You can narrow the scope:

> Investigate unexecuted properties in task <actual task_id>. Check configuration and coverage, and explain possible causes with evidence.

You must supply a concrete `task_id` for each new analysis. If it is missing, the agent must ask and wait, without automatically selecting the latest completed, just-run or only available task. An ID previously returned by a tool is not your selection. An explicit request to continue the same analysis may reuse the ID you supplied for it. An unknown ID requires your correction, not an automatic switch to another task.

Analysis uses experiment facts and evidence exclusively from Kea2 MCP responses. It does not inspect application or test source code, directly read or independently parse raw result files, HTML or task databases. Information unavailable through MCP remains a stated gap. Analysis does not launch tests, edit scripts or regenerate HTML. Reports follow your language.

## Read the report

Reports cover context, data quality, execution/coverage, major findings, hypotheses and next steps.
Separate property and invariant tables are provided. Properties include precondition satisfaction, executions, derived passes, fail and error; invariants include only fail/error and exception details or evidence. Partial tables disclose displayed and total records.
Major claims cite record IDs or sources. Unexamined data and unresolved conclusions are stated.
Invariants report fail/error only; execution, precondition satisfaction and pass counts are N/A.

Default analysis limits retrieval, investigating up to 5 findings and 3 images in depth.
Ask to continue through remaining findings or inspect more images when needed.
Running experiments or changing files may produce provisional observations; request final analysis
once the test finishes. Single-experiment analysis is supported.

## Maintain domain knowledge

Use **UTF-8 Markdown (.md)** in [domain-knowledge.md](../skills/kea2-result-analysis/references/domain-knowledge.md). Entries may be written in Chinese or English. The agent interprets the prose; the format below is a maintenance convention and requires no JSON or YAML validation.

Give each entry a second-level heading and a stable ID such as `KEA-PROP-003`. Keep the ID when revising the same entry and choose an unused ID for a new entry.

| Content | What to specify |
| --- | --- |
| Scope | Check type, test mode, application/version limits and applicable contract |
| Required evidence | MCP tool, section, fields and source availability requirements |
| Conditions | Field values, units and thresholds; distinguish missing values from zero |
| Supported interpretation | Conclusions justified when the conditions hold |
| Limits | Causes still requiring evidence and conclusions the entry cannot support |
| Further checks | Additional evidence obtainable through MCP |

Copy the template below and replace its placeholders with reviewed knowledge before adding it to the knowledge file.

```markdown
## KEA-<CATEGORY>-<NUMBER> · <Title>

### Scope
<Applicable check types, modes, app versions or result contracts.>

### Evidence and conditions
- Retrieve <fields> through <MCP tool and section>.
- Apply when <field conditions> and <source availability requirements> hold.
- If data is missing or a condition cannot be verified, <state the uncertainty>.

### Supported interpretation
<Conclusion supported by the evidence; label possible causes as hypotheses.>

### Limits
<Matters requiring additional evidence.>

### Further checks
<MCP queries for further evidence, and what to report if it remains unavailable.>
```

Existing entries `KEA-PROP-001` and `KEA-INV-001` provide worked examples. Knowledge guides interpretation; reported observations must still cite the selected task's MCP records. App-specific entries should identify their package/version scope. Resolve contradictory interpretations before publishing updates.

Copy the updated file to the installed skill's `kea2-result-analysis/references/domain-knowledge.md`, start a new session and analyze an explicit task ID. Knowledge-only updates require no wheel rebuild. Check the report's entry IDs and evidence to assess whether the knowledge was applied correctly. Entries requiring data that MCP cannot supply need a separate interface extension.

## Troubleshooting

### The skill is missing from the list

- Check that a project-scoped installation belongs to the open test project.
- Check for an extra nested kea2-result-analysis folder or a hidden .txt suffix on SKILL.md.
- Start a new session, restart the client or reload the editor window.
- Check skill enablement, workspace trust and Agent Skills support.

### The skill appears but results cannot be retrieved

Verify Kea2 MCP tools in the same session; installing the skill does not configure MCP.
If the task is missing, check its ID and whether the service runs under the user environment holding the task record.

### Skill changes are not taking effect

Update the installed copy and start a new session. Repository edits do not update copied installations.
Check for same-named project and personal copies.

### The client does not support skills

Ask an agent with local file access to read [SKILL.md](../skills/kea2-result-analysis/SKILL.md)
and its linked references, then follow those instructions for the specified task.
