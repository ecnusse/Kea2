# 使用 Agent 通过 MCP 完成 Kea2 测试全流程

[English](mcp_extension_en.md)

在完成客户端配置和 Skill 安装后，输入“我想用 Kea2 进行测试”，Agent 会引导你确认测试参数，检查准备条件，启动并跟踪测试，最后自动获取结果并生成分析报告。你只需回答必要问题并确认配置，不需要知道 MCP 工具名称，也不需要逐步发送“启动”“查状态”“分析结果”等指令。

这里的全自动是指确认配置后的执行与分析自动衔接。用户未提供的适用启动参数仍由 Agent 逐项解释并询问，不会静默采用默认值。Kea2 提供测试数据和证据，客户端中的大模型负责分析；原有 HTML 报告仍可供人阅读。

## 1. 准备客户端和测试环境

1. 准备可通过 ADB 连接的 Android 设备或模拟器，并安装目标应用。
2. 在 Python 3.10 或更高版本环境安装含 MCP 依赖的 Kea2，例如 `python -m pip install "kea2-python[mcp]"`。使用开发版本时，安装包含本功能的新 wheel。
3. 配置 Agent 客户端。具体配置见 [MCP 部署手册](../kea2/mcp/README_cn.md)。
4. 将仓库中的 `skills/kea2-test` 和 `skills/kea2-result-analysis` 两个完整目录复制到客户端技能目录，保留全部 references 文件。Codex 项目级目录使用 `.codex/skills/`，用户级使用 `~/.codex/skills/`；其他客户端位置见[技能安装手册](result_analysis_skill_cn.md)。两个 Skill 应安装在同一技能根目录下。
5. 安装或更新 wheel 后重启 MCP 服务，更新 Skill 后开启新会话。Skill 不会随 wheel 自动安装。

可以先让 Agent 检查设备连接，验证 MCP 可调用。没有设备时仍可以读取已保存结果，但启动新测试需要设备。项目尚未初始化也可以开始对话，Agent 会在确认准备操作后调用初始化工具。

## 2. 用一句话开始

输入：

> 我想用 Kea2 进行测试。

也可以明确调用 `kea2-test`，或者在第一句话中提供部分设置：

> 我想用 Kea2 测试设备 emulator-5554 上的 com.example.app，运行 20 分钟，使用 quicktest.py，不清空 App 数据。

Agent 首先只读检查设备、服务工作目录及项目准备情况。已经提供的参数不重复询问；尚未明确的参数进入后续交互。工作目录由 MCP 客户端配置决定，修改结果输出目录不会改变服务工作目录。

## 3. 回答参数问题

Agent 分批介绍参数用途、单位或取值、默认行为及影响，再等待你的回答。当前流程覆盖 `kea2_run_test` 暴露的全部参数，并不等同于 CLI 的所有选项。

| 询问主题 | 参数 | 你需要作出的选择 |
| --- | --- | --- |
| 设备与应用 | `serial`、`packages` | 确认设备和一个或多个目标包名；只有一台设备也会询问 |
| 测试方式 | `property_path` | 纯自动探索，或使用已有 Property 文件/目录 |
| 脚本设置 | `property_pattern`、`driver_name` | 目录中的文件匹配规则，以及脚本设备属性名，如 `self.d` 对应 `d` |
| 运行控制 | `running_minutes`、`max_step`、`throttle_ms`、`restart_app_period` | 时长、探索步数上限、事件间隔和重启周期 |
| 截图与覆盖 | `take_screenshots`、`profile_period` | 是否每步截图，以及周期采集间隔 |
| Activity 范围 | `act_whitelist_file`、`act_blacklist_file` | 不限制、白名单或黑名单；两种名单互斥 |
| 输出和数据 | `output_dir`、`log_stamp`、`clear_app_data` | 结果输出父目录，以及是否在启动前清空所有目标 App 数据 |

例如，Agent 会询问：

> running_minutes 控制计划测试分钟数，默认 10 分钟。希望使用默认值还是指定时长？
>
> clear_app_data 控制启动前是否清空目标 App 数据。开启会删除登录状态、设置和本地数据，不可恢复；默认关闭。你希望开启还是关闭？

可以一次回答多个参数，也可以明确说“剩余参数使用默认值”。这表示接受剩余可选项的默认行为，但必需的设备和目标应用仍需确认。未回答不等于同意默认值。

纯自动探索不询问脚本设置；指定单个文件时，文件匹配模式不适用。选择不限制 Activity 时，无需填写名单路径。Agent 会在最终配置中说明这些参数为何不适用。中途修改测试方式后，会重新确认受影响的设置。

不知道包名时，可以让 Agent 列出设备上的已安装包供你选择。当前应用查询只提供包名，包含系统应用，不提供显示名称；不能根据名称猜测包名。Activity 名单参数是设备端目标路径，内容来自项目 `configs/awl.strings` 或 `configs/abl.strings`，并非任意本机文件路径。

## 4. 检查并确认完整配置

参数收集完毕后，Agent 检查设备、目标应用是否安装、项目配置、脚本路径及名单文件。准备检查是只读操作，不导入或执行用户脚本，也不初始化、登记、清理数据或启动测试。检查通过只表示这些条件满足，不保证真实设备运行一定成功。

发现问题时，Agent 解释问题并补问相关信息，不要求你重新输入所有参数。随后展示完整配置表，列出用户指定值、明确接受的默认行为以及不适用项，并说明：

- 本轮使用的设备、应用、测试方式和运行设置。
- 结果输出父目录。
- 是否需要初始化项目；初始化会写入配置、版本信息和 quicktest.py。
- 是否清空 App 数据，以及涉及的全部目标包。

你确认后，Agent 才执行准备和启动操作。已有配置不会自动强制覆盖；参数改变后需要重新确认。初始化完成后还会复查准备条件。

## 5. 自动启动并跟踪测试

Agent 调用 `kea2_run_test`，记录返回的 `task_id` 和结果目录，并持续用该 ID 查询状态。你不必复制任务 ID，也不必再主动要求查询进度。

运行期间可以提出取消请求，Agent 会调用取消工具。清理失败时测试不会启动，Agent 会说明已清理的包；不会擅自重试清理或重新运行实验。启动响应丢失、状态不明确时，会先核实任务身份，不能直接再次启动以免产生重复任务。

测试结束后，Agent 根据退出信息和结果可用性进入分析。发现性质失败、崩溃或 ANR 不等同于启动工具故障。已取消或仅有部分结果时，报告明确说明读取范围和限制。

客户端需要支持持续工具调用和等待。关闭客户端不保证自动恢复；保留任务 ID 后可以明确要求继续。任务关联丢失或存在歧义时，需要重新选择，不会猜测最近一次实验。

## 6. 自动获取并分析结果

完整测试流程直接沿用本次启动返回的任务 ID，自动执行 `kea2-result-analysis`，不再要求你输入 ID 或再次授权分析。Agent 先读取概览和数据可用性，再查询运行配置、检查项、覆盖趋势和异常，按需获取堆栈、操作上下文及截图。

报告包括实验概况、Property 与 Invariant 表格、执行与覆盖情况、异常证据、原因假设及下一步建议。缺失数据不能当作零，异常发生次数不能直接当作独立 Bug 数。重要结论以 MCP 返回的记录为依据，区分事实与待验证推测；内部来源标识不默认展示。

实验事实只来自 Kea2 MCP 工具，不通过源码、HTML、原始日志或任务数据库自行补查。分析 Skill 会读取[专业知识文件](../skills/kea2-result-analysis/references/domain-knowledge.md)，使用其中适用的解释规则；知识维护方式见[分析 Skill 手册](result_analysis_skill_cn.md)。报告结构见[报告模板](../skills/kea2-result-analysis/references/report-template.md)。

独立分析 CLI 或历史实验时，仍需明确选择具体 task_id。这与当前全流程自动沿用本次任务 ID 是两种不同的使用方式。

## 常见情况

| 情况 | 处理方式 |
| --- | --- |
| Agent 没有识别全流程 | 明确调用 `kea2-test`，检查两个完整 Skill 是否安装并开启新会话 |
| 新工具未出现 | 确认 MCP 使用安装新 wheel 的 Python 环境，重启服务 |
| 没有设备或目标包 | 连接设备或安装应用后，让 Agent 重新检查 |
| 脚本或名单文件缺失 | 修正服务工作目录中的对应路径或配置，再检查 |
| 用户想改参数 | 告诉 Agent 修改项；启动前更新配置并重新确认 |
| 测试已结束但数据不完整 | 对可用结果进行有限分析，注明缺失证据，不自动重跑 |

以下内容说明 Agent 使用的工具、参数和数据，可在需要了解细节时查阅，无需手动逐个调用。

## 15 个 MCP 工具

| 工具 | 输入和作用 | 返回结果或影响 |
| --- | --- | --- |
| `kea2_init` | 在当前工作目录初始化测试项目。可选 `force`，默认 false | 写入配置、版本信息和 quicktest.py；已有配置默认拒绝覆盖 |
| `kea2_check_device` | 查询 ADB 连接的设备，无需参数 | 每台设备的 serial、状态和型号 |
| `kea2_list_apps` | 指定 serial，可选 keyword、limit、offset | 已安装包名及分页信息，不含显示名称 |
| `kea2_check_test_setup` | 可选 serial、packages、options | 只读返回环境、默认参数、准备问题及 ready，不执行初始化或测试 |
| `kea2_run_test` | 指定设备和包名，启动后台测试 | 成功时立即返回 task_id、stamp、实际目录和运行状态 |
| `kea2_get_status` | 按 task_id 查询进度 | 任务状态、运行阶段、PID、粗略的 executed/fail/error 计数和结果文件可用性 |
| `kea2_cancel_test` | 按 task_id 取消正在运行的测试 | 停止测试进程，尝试清理设备端 Fastbot，并更新取消状态 |
| `kea2_list_tasks` | 查询当前 MCP 用户已登记的任务，无需 task_id | 任务列表和分页信息，可按状态、来源、父任务筛选 |
| `kea2_register_result` | 登记用户指定的历史目录，可选 stamp 和 task_id 别名 | 返回登记结果、已有 ID、候选或冲突信息 |
| `kea2_get_results` | 按 task_id 列出结果目录中的文件 | 路径、类型、大小。适合回答“生成了哪些文件” |
| `kea2_get_result_schema` | 查询数据契约，无需 task_id | experiment、report、query、finding、artifact 或 error 的 JSON Schema |
| `kea2_get_report` | 按 task_id 读取一次实验的概览 | 状态、统计、覆盖、快照、来源可用性和警告 |
| `kea2_query_report` | 按 task_id、section 和可选 filters 查询明细 | 当前页记录、匹配总数、快照和下一页游标 |
| `kea2_get_finding` | 传入 task_id、finding_id 和 snapshot_id | 某次异常的详情、堆栈片段、关联执行记录、日志上下文及证据引用 |
| `kea2_get_artifact` | 传入 task_id、artifact_id 和 snapshot_id | 实际截图或文本片段，以及证据元数据 |

## 启动和控制测试

| 启动参数 | 用途 |
| --- | --- |
| `serial`、`packages` | 必填。选择已连接的设备和目标应用包名列表 |
| `running_minutes`、`output_dir` | 测试时长默认 10 分钟。输出父目录默认 output |
| `property_path`、`property_pattern`、`driver_name` | 选择性质脚本文件或目录。目录匹配模式默认 test*.py，驱动属性默认 d。省略脚本路径时运行模糊测试 |
| `max_step`、`throttle_ms` | 最大探索步数和事件间隔（毫秒） |
| `take_screenshots`、`profile_period` | 每步截图开关，以及覆盖率和截图采集周期（步数） |
| `restart_app_period` | 按步数设置应用重启周期，0 表示不定期重启 |
| `clear_app_data` | 默认 false；设为 true 时，启动前清空指定设备上所有目标应用的数据（含登录状态、设置和本地数据，不可恢复）。清理失败不启动测试，并报告已清理的包 |
| `act_whitelist_file`、`act_blacklist_file` | 互斥的 Activity 名单选项。参数是设备端目标路径，内容来自项目配置 |

测试在后台运行。指定性质脚本后仍由 Fastbot 探索界面，满足条件时执行性质。服务会检查脚本参数、项目配置和设备连接。子进程输出与 Fastbot 日志分别保存。Windows 的进度查询使用进程句柄检查存活状态。

进度和最终结论有不同口径。任务状态中的 failed 可能来自发现缺陷后的非零退出。在结构化报告中，退出码 0 表示完成且无对应缺陷标志，1 表示性质违反，2 表示 Crash/ANR，3 表示两者都有，4 表示执行错误。退出标志、异常次数和数据是否完整分别呈现。

## 三种实验来源及任务身份

| 来源 | 如何获得 task_id | 需要知道的行为 |
| --- | --- | --- |
| MCP 新实验 | `kea2_run_test` 返回 ID | MCP 父进程与 CLI 子进程共同使用一条任务记录 |
| CLI 新实验 | 运行 `kea2 run`，通过 `kea2_list_tasks` 或 `kea2_task.json` 获取 ID | 自动登记，CLI 本身无需安装 MCP 可选依赖 |
| 历史实验 | 调用 `kea2_register_result` 或运行 `kea2 register-result -p <结果目录>` | 对指定目录补登记，原始文件保持原样 |

新实验默认 `task_id = stamp = log_stamp`，结果位于 `<输出父目录>/res_<stamp>/`。默认标识是带六位微秒的本地时间戳，格式为 `%Y%m%d%H_%M%S%f`。CLI 支持原有自定义标识和目录复用；标识包含中文、空格或 ID 冲突时，登记层分配独立 task_id，不改变文件标识和目录。MCP 的 task_id 始终自动生成时间戳；自定义 log_stamp 仅决定结果目录和文件标识。同名可用于不同输出父目录，同一实际目录已存在时拒绝启动，时间戳 ID 冲突时自动重试。旧 UUID 任务继续使用原 ID。

任务数据库位于运行用户的 `~/.kea2/tasks.db`，保存任务身份、来源、状态和结果位置。实验目录里的 `kea2_task.json` 保存身份和已知运行信息，便于搬迁或恢复。数据库初始化或写入失败时，CLI 会警告并继续测试。若进程被强制结束，最终状态可能尚未写入。

列表默认每页 20 条，最多 100 条。返回 `total` 和 `next_offset`，支持 `status`、`origin`（cli/mcp/imported）和 `parent_task_id`。查询范围是当前用户的登记库。任务记录仍在时，对应结果目录也可能已经移动。

历史登记检查指定目录和直接的 `res_*` 子目录。一个目录可以重复登记；同一实际目录和 stamp 会返回原任务。遇到多个实验时返回候选，需明确选择。ID 已用于其他目录时，可以显式传入别名，原始 stamp 和文件名保持不变。返回状态为 `registered`、`already_registered`、`selection_required`、`identity_conflict`、`unsupported` 或 `invalid`。导入时保留可核实的数据，执行状态记为 unknown。只有 HTML 时无法接入。

Hybrid 运行可包含父任务和多个子实验。查询父任务的报告时会得到 `CHILD_TASK_REQUIRED`，用 `kea2_list_tasks(parent_task_id=...)` 查看子任务，再指定具体子任务分析。登记示例及别名操作见[实验任务登记手册](task_registration_cn.md)。

## 结构化报告与十类明细

服务按任务记录定位目录和 stamp，从已有结果文件中生成结构化视图。当前数据契约版本为 **1.5**，规定字段、类型、单位、可空规则和错误结构。可通过 Schema 工具查看单个响应的定义。契约文件见 [JSON Schema](structured_result.schema.json)，可对照[完整模型示例](examples/structured_result_v1.5.json)。

概览给出任务状态、退出信息、已知时间、包名和设备，以及按类型统计的检查项、Fail/Error、Crash/ANR 次数、Activity 覆盖率和已触发控件数量。日志可用时还提供首末时间、持续秒数、最大 Monkey 步数和有效记录数。报告区分启动请求、保存的配置和日志观测，并返回各模块记录数、来源状态、警告、`schema_version` 和 `snapshot_id`。

| section | 能回答的问题及主要来源 | 常用筛选 |
| --- | --- | --- |
| checks | 哪些 property 执行、失败或没有执行？哪些 invariant 报错？读取 result_<stamp>.json | name、kind、has_findings |
| findings | 哪些异常发生过？读取 property_exec_info_<stamp>.json 和 crash-dump.log，保留每次性质异常、Crash 或 ANR | type、check_name、state |
| activities | 哪些 Activity 被覆盖、遍历了多少次？读取 coverage.log 最后一条有效记录 | name、covered |
| trends | Activity 覆盖率或已触发控件数量随 Monkey 步数怎样变化？读取 coverage.log、widget_coverage.log | metric |
| steps | 某个区间内发生了哪些操作？读取 steps.log，保留逐条事件和来源行 | type、start_step、end_step、execution_id |
| executions | 性质何时开始、结束，执行边界是否完整？读取日志中明确的脚本标记 | id、check_name、kind、state |
| artifacts | 哪些日志和明确引用的截图可用？ | id、kind、availability |
| widgets | 记录了哪些控件？读取 widget_coverage_report.txt，保留原文和解析状态 | activity、class_name、resource_id、content_description、parse_status |
| property_execution_trend | 到某个探索步数，已有多少种不同 property 启动过？该趋势排除 invariant | start_step、end_step |
| configuration | 实验保存了哪些设置？读取 options.json 与 bug_report_config.json | document、key |

上表中的日志位于对应的 `output_<stamp>/`。明细查询默认每页 50 条，范围为 1–100。继续翻页时保持 section 和 filters 不变，把返回的 `next_cursor` 作为下一次请求的 cursor，直到它为空。

**统计口径。** Property 提供前置条件满足次数、执行次数、Fail 和 Error，通过次数按 `max(executed - fail - error, 0)` 派生。Invariant 只统计 Fail、Error 和异常详情，前三项中的前置条件、执行次数以及派生通过次数均不适用，返回 null。Unknown 类型单列。发生过异常的检查项数量、异常发生次数和独立缺陷数量是三种不同指标。控件趋势使用数量，Activity 覆盖率使用百分比。

配置记录保留字段名、值、编码方式和来源。重复键会使相应配置无效；两个配置文档的值不同时保留差异并提示。Infinity 等非标准 JSON 数值采用带标记的编码。

## 从异常追溯到证据

Crash/ANR 日志是按异常产生的可选文件。任务正常完成、退出码为 0 或 1 时，没有该日志会返回 Crash=0、ANR=0，不会仅因此标记结果不完整。来源状态仍如实保留为 `missing`，报告展示“0（未发现）”。已有日志按有效异常记录块统计次数，不做去重；日志读取失败、完全损坏，或任务状态不足以确认未检测到异常时，计数仍可能为 null。历史登记没有已知退出码时，不凭文件缺席断言零异常。

Agent 查看某个 Property 的失败证据时，按下面的顺序读取；调用中的占位符由 Agent 替换为实际 ID。

1. 调用 `kea2_get_report(task_id)`，确认结果来源可用并记录快照。
2. 调用 `kea2_query_report`，传入 `{"task_id":"<task_id>","section":"findings","filters":{"type":"property","check_name":"<性质名称>"}}`。从返回页取得 finding_id 和 snapshot_id。
3. 调用 `kea2_get_finding`，传入这两个 ID 和 task_id。堆栈默认每次 8,000 字符，最多 32,000 字符，沿 next_offset 继续读取。可用 context_before 和 context_after 各取 0–20 条关联步骤前后的日志。
4. 详情中有可用截图时，使用返回的 artifact_id 和快照调用 `kea2_get_artifact`。PNG、JPEG、WebP 可作为 MCP 图片内容返回，包含证据元数据和 SHA-256。文本证据按 Unicode 字符分页，非 UTF-8 内容会报错。

执行区间可以包含交错事件；缺少边界时仅返回实际记录。服务依据明确的日志引用关联截图，有多个候选时保留歧义。只有客户端实际读取并支持展示图片，agent 才能描述图中内容。

## 数据质量、快照和读取限制

来源可用性区分 available、missing、partial、invalid、unreadable 和 too_large。缺失统计返回 null。可读但为空的 Crash 记录可以支持“观察到 0 次”；缺失 Crash 文件时无法作此判断。损坏的逐行记录可跳过并给出来源警告。响应最多展示 50 条警告样例，同时给出总数和截断标记。

当前相关文本来源上限为 64 MiB，单张截图上限为 8 MiB。证据按 ID 从已登记目录读取，并检查路径、图片解码和文件变化。查询根据任务元数据和来源生成快照，分页和证据 ID 与快照关联。遇到 `STALE_SNAPSHOT` 时重新读取概览和相关明细。各文件独立读取，正在运行的实验可能只能提供临时观察。

常见错误还包括 `TASK_NOT_FOUND`（检查 ID 和用户环境）、`INVALID_FILTER`（检查 section 的筛选字段）、`ARTIFACT_UNAVAILABLE`（记录缺失证据）和 `INVALID_IMAGE`（无法将文件作为图片读取）。

## Agent 分析 Skill 与报告

`kea2-result-analysis` 将分析过程组织为可版本管理的指令，当前 Skill 版本为 **1.7.0**。分析时读取[独立知识文件](../skills/kea2-result-analysis/references/domain-knowledge.md)。安装 wheel 后，需要单独将整个技能目录连同 references 复制到客户端技能目录。Codex 在本手册中采用项目级 `.codex/skills/` 或用户级 `~/.codex/skills/`。其他客户端的目录和调用方式见[分析 Skill 使用手册](result_analysis_skill_cn.md)。

- **绑定分析任务。** 全流程沿用用户确认启动的本次任务 ID；独立分析已有实验时由用户明确选择。关联丢失或有歧义时询问，不自动选择最近或唯一任务。
- **只使用 MCP 实验事实。** Agent 从报告、查询、异常和证据工具取得信息。源码、HTML、数据库和原始文件均不作为 agent 自行补查的渠道。来源不足时在报告中注明。
- **说明读取范围。** 默认从每页 25 条开始，概览后最多调用 20 次结果或证据工具，深入查看最多 5 条异常和 3 张图片。用户可以明确扩大范围。快照变化时，整个分析最多进行两轮恢复。
- **分别展示 property 和 invariant。** Property 表包含名称、前置条件、执行、通过次数、Fail、Error；invariant 表包含名称、Fail、Error，异常详情另行说明。表格不展示依据或证据列。表格查询所有相关检查项，注明展示数与总数。
- **给出可核对的判断。** 报告包含实验概况、数据质量、执行与覆盖、主要异常、原因假设和后续验证建议。区分观测事实和待验证假设。退出码、内部标志、快照和原始数据状态不默认展示；影响结论的限制用简短文字说明。实际异常保留必要描述、堆栈和截图，需要溯源时可要求附上记录 ID 和来源。

这些是 Skill 对 agent 的操作指令，实际遵循程度还取决于客户端和模型。报告格式可查看[报告模板](../skills/kea2-result-analysis/references/report-template.md)。

自定义实验目录名时，可以告诉 Agent：“输出父目录用 output，本次实验名称用 login_test”。Agent 将传入 `log_stamp="login_test"`，生成 `output/res_login_test/`，日志标识为 `login_test`，任务 ID 始终为自动生成的时间戳。省略时自动生成时间戳；输出目录冲突时报错，不覆盖。名称仅使用英文字母、数字、下划线、连字符和点，不能为 `.`/`..` 或以点结尾。
