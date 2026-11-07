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

每次开始新的分析都必须由你提供具体的 `task_id`。未指定时，agent 应先询问并等待你提供，不能自行分析最近完成、刚执行过或唯一的任务；即使工具之前返回过任务 ID，也不能代替你的指定。明确要求继续同一次分析时，可以沿用你为该次分析指定的 ID。ID 不存在时，应请你更正，不能自动切换到其他任务。

分析仅使用 Kea2 MCP 工具返回的实验结果和证据，不读取应用或测试脚本源码，不直接读取或自行解析原始结果文件、HTML 或任务数据库。MCP 无法提供的信息会标为缺失，不通过其他途径补查。分析不会启动新测试、修改脚本或重新生成 HTML。报告使用你的提问语言。

## 阅读分析报告

报告包含实验概况、数据质量、执行与覆盖、主要异常、原因假设和后续建议。
报告分别列出 property 和 invariant 统计表：property 包含前置条件满足次数、执行次数、派生通过次数、fail 和 error；invariant 仅包含 fail、error 及异常详情或证据。表格未读完时会注明已展示数量和总数。
主要判断会附带记录 ID 或来源，并说明没有检查的数据和无法确定的结论。
不变量只统计 fail/error，执行次数、前置条件满足次数和通过次数为不适用。

默认分析会限制读取量，最多深入查看 5 个异常和 3 张图片。需要更全面的检查时，
可以明确要求继续分析剩余异常或增加图片读取范围。
测试仍在运行或结果文件持续变化时，报告可能只包含临时观察；最终分析建议在测试结束后进行。
当前支持单次实验分析。

## 维护专业知识

专业知识使用 **UTF-8 编码的 Markdown（.md）**，集中维护在 [domain-knowledge.md](../skills/kea2-result-analysis/references/domain-knowledge.md)。可以用中文或英文编写。Agent 按文字理解和应用这些知识，下面的格式是便于维护的约定，无需 JSON 或 YAML 校验。

每条知识用独立的二级标题和稳定编号，例如 `KEA-PROP-003`。更新同一条知识时保留编号，新知识使用未占用的编号。建议覆盖以下内容。

| 内容 | 写法 |
| --- | --- |
| 适用范围 | 说明对象、测试模式、应用或版本限制；有契约要求时注明 |
| 所需证据 | 列出 MCP 工具、section 和具体字段，以及来源可用性要求 |
| 判断条件 | 写清字段值、单位和阈值；缺失值与零值分别处理 |
| 可支持的解释 | 写出满足条件时可以给出的结论 |
| 解释限制 | 指明仍需查证的原因和无法推出的结论 |
| 后续查证 | 说明可以继续查询哪些 MCP 证据 |

下面是可复制的条目模板。将占位内容替换为团队认可的知识后，放入知识文件。

```markdown
## KEA-<类别>-<编号> · <知识标题>

### 适用范围
<适用的检查项类型、测试模式、应用版本或数据契约。>

### 所需证据与判断条件
- 通过 <MCP 工具及 section> 获取 <具体字段>。
- 当 <字段满足的条件> 且 <来源可用性要求> 时采用该解释。
- 数据缺失或条件无法核对时，<说明应保留哪些不确定性>。

### 可支持的解释
<可从当前证据支持的结论；经验性的可能原因应标明为假设。>

### 解释限制
<仍需更多证据才能判断的事项。>

### 后续查证
<通过哪些 MCP 查询获取进一步证据，以及无法获取时如何说明。>
```

现有 `KEA-PROP-001` 和 `KEA-INV-001` 可作为实际示例。专业知识用于解释实验，报告中的观测值仍需引用当前任务的 MCP 返回记录。应用特有知识应明确包名或版本范围，避免套用到其他应用。若多条知识对同一条件给出冲突结论，先统一判断依据再发布。

更新后，将文件同步到客户端安装位置的 `kea2-result-analysis/references/domain-knowledge.md`，开启新会话并使用 Skill 分析指定任务。仅更新知识内容时无需重新打 wheel。可以在报告中核对知识编号和对应证据，确认条目是否被正确应用。新增知识所需的数据若尚不能通过 MCP 获取，需要另外扩展数据接口。

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
