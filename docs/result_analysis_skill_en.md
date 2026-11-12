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

For independent analysis requests, supply a concrete task_id; never select the latest or only task automatically. In a user-confirmed kea2-test workflow, the agent may reuse the exact ID returned by its own launch and continue analysis without asking you to repeat it. Lost or ambiguous bindings require explicit selection. See [interactive testing](mcp_extension_en.md).

Analysis uses experiment facts and evidence exclusively from Kea2 MCP responses. It does not inspect application or test source code, directly read or independently parse raw result files, HTML or task databases. Information unavailable through MCP remains a stated gap. Analysis does not launch tests, edit scripts or regenerate HTML. Reports follow your language.

## Read the report

Reports cover context, data quality, execution/coverage, major findings, hypotheses and next steps.
Separate property and invariant tables are provided. Properties include precondition satisfaction, executions, passes, fail and error; invariants include only name, fail and error, with exception details described separately. Tables omit basis, evidence and source columns; Activity tables contain only name, coverage and visits. Partial tables disclose displayed and total records.

The first eight sections present results without adding formulas, count comparisons or trend interpretations below tables. Useful interpretations and advice appear together in the final analysis section; routine metric explanations without analytical value are omitted by default.

Exit codes, internal flags, snapshots and raw source states are hidden by default. Material gaps receive brief explanations. Actual problems retain relevant descriptions, stack excerpts and screenshots. A completed run explicitly reporting no detected Crash/ANR, without contradictory findings, may show "0 (none detected)"; null must not universally become zero. Pass counts follow the HTML convention: `max(executed - fail - error, 0)`.
Major claims cite record IDs or sources. Unexamined data and unresolved conclusions are stated.
Invariants report fail/error only; execution, precondition satisfaction and pass counts are N/A.

Default analysis limits retrieval, investigating up to 5 findings and 3 images in depth.
Ask to continue through remaining findings or inspect more images when needed.
Running experiments or changing files may produce provisional observations; request final analysis
once the test finishes. Single-experiment analysis is supported.

## Maintain domain knowledge

Maintain UTF-8 Markdown entries in [domain-knowledge.md](../skills/kea2-result-analysis/references/domain-knowledge.md). Each entry uses a stable ID and six sections: scope, domain knowledge, required data and conditions, analysis rules, report output requirements, and follow-up recommendations.

See the [domain knowledge maintenance guide](domain_knowledge_maintenance_en.md) for the template, authoring principles, Crash/ANR example, update workflow and validation. Sync changes to the active skill installation and open a new session; knowledge-only updates require no wheel rebuild.

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
