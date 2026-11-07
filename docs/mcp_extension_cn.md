# 如何让 Agent 通过 Kea2 MCP 扩展启动测试、获取并分析测试结果

[English](mcp_extension_en.md)

Kea2 MCP 让 agent 可以在 Android 设备上启动测试，也可以读取已完成实验的结构化结果。用户通过 MCP 或命令行启动的新实验，以及从历史目录登记的旧实验，都可以用任务 ID 查询。Kea2 服务负责执行测试、整理统计和提供证据。撰写分析报告的是客户端 agent 中的大模型。原有 HTML 报告继续供人阅读。

## 从第一次使用到拿到分析报告

1. **连接测试项目。** 在 Python 3.10 或更高版本的环境安装含 MCP 依赖的 Kea2，例如 `python -m pip install "kea2-python[mcp]"`。让客户端在测试项目目录中，用该环境的 Python 执行 `python -m kea2.cli mcp`。服务使用本地标准输入输出通信。更新 wheel 后需要重启服务。
2. **启动或找到实验。** 新项目先调用 `kea2_init`，再用 `kea2_check_device` 取得设备序列号。如果已有实验，直接列出已登记任务，或登记指定的历史目录。
3. **运行新测试。** 例如让 agent “在设备 emulator-5554 上测试 com.example.app，运行 10 分钟，使用 quicktest.py”。把示例设备、包名和脚本替换为实际值。启动成功后保留返回的 `task_id`，用它查询进度。
4. **明确选择分析对象。** 例如“使用 kea2-result-analysis 分析任务〈具体 task_id〉，列出未执行的 property，并检查异常证据”。首次分析必须给出具体 ID。任务列表、启动结果和历史登记结果都可帮助用户找到 ID。
5. **阅读结果。** Agent 先读概览，再查询相关统计，按需读取异常堆栈和截图。报告注明证据来源、已读范围及无法判断的事项。

启动新实验需要可访问的 Android 设备。读取已经落盘的实验结果可以离线进行，无需重新运行测试。客户端配置和独立 Skill 安装步骤见 [MCP 部署手册](../kea2/mcp/README_cn.md)和[分析 Skill 手册](result_analysis_skill_cn.md)。

## 13 个 MCP 工具

| 工具 | 输入和作用 | 返回结果或影响 |
| --- | --- | --- |
| `kea2_init` | 在当前工作目录初始化测试项目。可选 `force`，默认 false | 写入配置、版本信息和 quicktest.py；已有配置默认拒绝覆盖 |
| `kea2_check_device` | 查询 ADB 连接的设备，无需参数 | 每台设备的 serial、状态和型号 |
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
| `act_whitelist_file`、`act_blacklist_file` | 互斥的 Activity 名单选项。参数是设备端目标路径，内容来自项目配置 |

测试在后台运行。指定性质脚本后仍由 Fastbot 探索界面，满足条件时执行性质。服务会检查脚本参数、项目配置和设备连接。子进程输出与 Fastbot 日志分别保存。Windows 的进度查询使用进程句柄检查存活状态。

进度和最终结论有不同口径。任务状态中的 failed 可能来自发现缺陷后的非零退出。在结构化报告中，退出码 0 表示完成且无对应缺陷标志，1 表示性质违反，2 表示 Crash/ANR，3 表示两者都有，4 表示执行错误。退出标志、异常次数和数据是否完整分别呈现。

## 三种实验来源及任务身份

| 来源 | 如何获得 task_id | 需要知道的行为 |
| --- | --- | --- |
| MCP 新实验 | `kea2_run_test` 返回 ID | MCP 父进程与 CLI 子进程共同使用一条任务记录 |
| CLI 新实验 | 运行 `kea2 run`，通过 `kea2_list_tasks` 或 `kea2_task.json` 获取 ID | 自动登记，CLI 本身无需安装 MCP 可选依赖 |
| 历史实验 | 调用 `kea2_register_result` 或运行 `kea2 register-result -p <结果目录>` | 对指定目录补登记，原始文件保持原样 |

新实验默认 `task_id = stamp = log_stamp`，结果位于 `<输出父目录>/res_<stamp>/`。默认标识是带六位微秒的本地时间戳，格式为 `%Y%m%d%H_%M%S%f`。CLI 支持原有自定义标识和目录复用；标识包含中文、空格或 ID 冲突时，登记层分配独立 task_id，不改变文件标识和目录。MCP 启动仍为新任务分配独立目录。旧 UUID 任务继续使用原 ID。

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

例如要查看某个 property 为什么出现失败，可以按下面的顺序读取。请将占位符替换为实际 ID。

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

`kea2-result-analysis` 将分析过程组织为可版本管理的指令，当前 Skill 版本为 **1.4.0**。分析时读取[独立知识文件](../skills/kea2-result-analysis/references/domain-knowledge.md)。安装 wheel 后，需要单独将整个技能目录连同 references 复制到客户端技能目录。Codex 在本手册中采用项目级 `.codex/skills/` 或用户级 `~/.codex/skills/`。其他客户端的目录和调用方式见[分析 Skill 使用手册](result_analysis_skill_cn.md)。

- **先选择任务。** 缺少具体 task_id 时询问并等待。即使只有一个结果、刚运行了测试或刚登记了旧实验，也由用户明确选择。继续同一次已指定的分析时可以沿用该 ID。
- **只使用 MCP 实验事实。** Agent 从报告、查询、异常和证据工具取得信息。源码、HTML、数据库和原始文件均不作为 agent 自行补查的渠道。来源不足时在报告中注明。
- **说明读取范围。** 默认从每页 25 条开始，概览后最多调用 20 次结果或证据工具，深入查看最多 5 条异常和 3 张图片。用户可以明确扩大范围。快照变化时，整个分析最多进行两轮恢复。
- **分别展示 property 和 invariant。** Property 表包含名称、前置条件、执行、派生通过、Fail、Error、证据；invariant 表包含名称、Fail、Error、异常详情或证据。表格查询所有相关检查项，注明展示数与总数。
- **给出可核对的判断。** 报告包含实验概况、数据质量、执行与覆盖、主要异常、原因假设和后续验证建议。重要判断引用任务、快照、记录 ID 或来源位置，区分观测事实和待验证假设。

这些是 Skill 对 agent 的操作指令，实际遵循程度还取决于客户端和模型。报告格式可查看[报告模板](../skills/kea2-result-analysis/references/report-template.md)。

## 当前支持范围

用户可以分析通过 CLI 或 MCP 启动的实验，也可以登记历史结果目录后进行分析。每次分析由用户指定一个 `task_id`。Agent 可以查看该实验的执行与覆盖统计，分页查询异常记录，并结合可用的堆栈、操作日志和截图生成带证据的报告。对于 hybrid 测试，用户可以先列出子任务，再选择一个子实验分析。
