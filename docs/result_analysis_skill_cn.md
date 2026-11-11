# Kea2 结果分析 Skill 使用手册

[English](result_analysis_skill_en.md)

`kea2-result-analysis` 帮助 agent 读取 Kea2 实验数据、查看异常证据，并生成带来源的分析报告。

## 使用前准备

- 配置并连接支持结果契约 1.5 的 Kea2 MCP 服务。
- 准备一个已有实验的 `task_id`，可使用通过 MCP 启动测试时返回的任务 ID。
- 安装 wheel 的 Python 环境必须与启动 MCP 服务的环境一致；更新包后重启服务。

## 安装 Skill

安装 wheel 不会自动安装 Skill，需要单独复制技能文件夹。

1. 在 Kea2 仓库中找到 `skills/kea2-result-analysis` 文件夹。
2. 根据下表选择安装目录：项目级仅用于对应测试项目，用户级可供多个项目使用。
3. 将整个文件夹复制进去，保留 `SKILL.md` 和 `references` 子目录。
4. 打开测试项目并开启新会话，按下表选择技能；若未出现，重启客户端。

| 客户端 | 项目级技能根目录 | 用户级技能根目录 | 发现与调用 |
| --- | --- | --- | --- |
| Codex | `<测试项目>/.codex/skills/` | `~/.codex/skills/` | 在测试项目打开会话，用 `$kea2-result-analysis` 选择/调用；未出现时重启 Codex |
| Claude Code | `<测试项目>/.claude/skills/` | `~/.claude/skills/` | 在该项目启动 Claude Code，输入 `/kea2-result-analysis` |
| Cursor | `<测试项目>/.cursor/skills/` | `~/.cursor/skills/` | 在项目 Agent 聊天输入 `/kea2-result-analysis`，或使用 `@` 选择技能 |
| GitHub Copilot（VS Code） | `<测试项目>/.github/skills/` | `~/.copilot/skills/` | 打开该项目，在 Chat 的 Open Customizations 中检查技能；用自然语言明确要求使用 kea2-result-analysis |


`~` 表示运行客户端的用户主目录。Codex 用户级安装后的 Windows 路径为
`%USERPROFILE%\.codex\skills\kea2-result-analysis\SKILL.md`，`references` 文件夹位于同一层。
只选择一个安装位置，避免同名技能重复或加载到旧副本。

使用远程、WSL 或容器环境时，应将技能安装到实际运行 agent 的环境中。
云端客户端的技能同步方式请参阅其帮助文档。

客户端帮助：[Codex 官方说明](https://learn.chatgpt.com/docs/build-skills)、[Claude Code 官方说明](https://code.claude.com/docs/en/skills)、[Cursor 官方说明](https://cursor.com/help/customization/skills)、[VS Code 官方说明](https://code.visualstudio.com/docs/agent-customization/agent-skills)。不同版本的列表位置可能变化，以这些页面和实际客户端为准。

## 开始分析

CLI 新实验会自动登记。已有历史结果可明确要求调用 `kea2_register_result` 登记指定目录；
返回多个候选或 ID 冲突时，需要你选择目录、stamp 或登记别名。登记后仍需明确指定 task_id 才开始分析。
Hybrid 父任务应先列出子任务再选择。详见[实验任务登记](task_registration_cn.md)。

如果不知道任务 ID，可以先让 agent「调用 `kea2_list_tasks` 列出已有任务」。默认每页 20 条，支持按状态筛选及分页。列表展示后，由你指定具体的 `task_id` 才开始分析，不会自动分析列表中的最近任务。只查询当前 MCP 用户环境中已登记的任务，不会扫描磁盘导入历史结果。

在 Codex 中输入：

> 使用 $kea2-result-analysis 分析任务 <实际 task_id>，给出带证据的结果报告。

Claude Code 和 Cursor 使用 `/kea2-result-analysis` 选择技能后，再输入任务 ID 和分析要求。
在其他客户端中，可选择技能后输入：

> 使用 kea2-result-analysis 分析任务 <实际 task_id>。

将 `<实际 task_id>` 替换为你的实验任务 ID。也可以指定关注范围：

> 分析任务 <实际 task_id> 中属性未执行的情况，检查配置和覆盖数据，说明可能原因及依据。

独立分析已有实验时，需要明确提供具体 task_id，不能自动选择最新或唯一任务。在用户确认的 kea2-test 全流程中，可以直接沿用本次启动工具返回的任务 ID，无需重复输入；关联丢失或存在歧义时需重新选择。详见[交互式测试](mcp_extension_cn.md)。

分析仅使用 Kea2 MCP 工具返回的实验结果和证据，不读取应用或测试脚本源码，不直接读取或自行解析原始结果文件、HTML 或任务数据库。MCP 无法提供的信息会标为缺失，不通过其他途径补查。分析不会启动新测试、修改脚本或重新生成 HTML。报告使用你的提问语言。

## 阅读分析报告

报告包含实验概况、数据质量、执行与覆盖、主要异常、原因假设和后续建议。
报告分别列出 property 和 invariant 统计表：property 包含前置条件满足次数、执行次数、通过次数、fail 和 error；invariant 仅包含名称、fail 和 error，异常详情另行说明。表格不展示依据、证据或来源列，Activity 表只展示名称、覆盖情况和访问次数。表格未读完时会注明已展示数量和总数。

前八节集中展示结果，不在表格下追加统计公式、计数差异解释或趋势分析。有价值的解读和建议统一放在最后的“分析与建议”；没有实际分析价值的口径说明默认省略。

退出码、内部标志、快照和原始数据状态不默认展示；影响结论的数据缺失会用简短文字说明。有异常时保留必要的描述、堆栈和截图。正常完成且明确未检测到 Crash/ANR、无矛盾记录时，可以显示“0（未发现）”；不能把所有 null 一律当作 0。通过次数沿用 HTML 的统计口径：`max(执行次数 - fail - error, 0)`。
主要判断会附带记录 ID 或来源，并说明没有检查的数据和无法确定的结论。
不变量只统计 fail/error，执行次数、前置条件满足次数和通过次数为不适用。

默认分析会限制读取量，最多深入查看 5 个异常和 3 张图片。需要更全面的检查时，
可以明确要求继续分析剩余异常或增加图片读取范围。
测试仍在运行或结果文件持续变化时，报告可能只包含临时观察；最终分析建议在测试结束后进行。
当前支持单次实验分析。

## 维护专业知识

专业知识使用 UTF-8 Markdown，集中维护在 [domain-knowledge.md](../skills/kea2-result-analysis/references/domain-knowledge.md)。每条采用稳定编号及六个固定部分：适用范围、专业知识、所需数据与判断条件、分析规则、报告输出要求、后续建议。

条目模板、编写原则、Crash/ANR 示例、更新流程及验证方法见[专业知识维护指南](domain_knowledge_maintenance_cn.md)。更新后同步到客户端实际安装的 Skill 目录并开启新会话；仅修改知识文件无需重新打 wheel。

## 常见问题

### 技能列表中找不到

- 确认项目级 Skill 位于当前打开的测试项目中。
- 检查是否多复制了一层 `kea2-result-analysis` 文件夹，或文件实际名为 `SKILL.md.txt`。
- 开启新会话，必要时重启客户端或重新加载编辑器窗口。
- 检查技能是否被禁用、项目是否受信任，以及客户端是否支持 Agent Skills。

### 能看到技能，但无法获取测试结果

确认同一会话中可以调用 Kea2 MCP 工具。安装 Skill 不会自动配置 MCP。
如果提示任务不存在，请检查 task_id，以及 MCP 服务是否使用保存该任务记录的用户环境。

### 修改了技能文件，但仍使用旧内容

更新安装目录中的副本，再开启新会话。修改 Kea2 仓库中的文件不会自动更新已复制的副本。
检查是否同时存在项目级和用户级的同名技能。

### 客户端不支持 Skill

让能够访问本地文件的 agent 读取 [SKILL.md](../skills/kea2-result-analysis/SKILL.md)
及其中引用的文档，按其指令分析指定任务。
