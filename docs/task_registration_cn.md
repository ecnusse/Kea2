# 实验任务登记与历史结果接入

[English](task_registration_en.md)

## 新实验自动登记

通过 `kea2 run` 启动的新实验会自动登记到运行用户的 `~/.kea2/tasks.db`。
不需要安装 MCP 可选依赖来登记 CLI 任务。通过 MCP 启动时，父进程与 CLI 子进程共用同一条任务。

```bash
kea2 run -p com.example.app --running-minutes 10
```

通过 `kea2_list_tasks` 或结果目录中的 `kea2_task.json` 获取 task_id。
默认使用含微秒的时间戳。CLI 保留原有 `--log-stamp` 规则，支持中文和空格；
当文件标识不适合作为任务 ID 或 ID 已存在时，登记层生成独立 ID，不改变结果文件名与目录。
CLI 允许复用已有结果目录；同名文件可能被本次运行覆盖，旧任务记录不保留这些文件的历史副本。

结果目录保存 `kea2_task.json`，记录任务身份与已知运行信息，并使用相对结果文件名。
数据库初始化或写入失败时会警告并继续测试，目录元数据可用于之后补登记。
MCP 启动仍分配独立任务和新目录，并校验父进程与子进程的目录交接。

CLI 与 MCP 必须运行在同一用户环境，才能直接共用数据库。跨机器、跨用户或移动目录后，需要补登记。
强制结束 CLI 进程可能来不及更新状态，列表中的状态是持久化记录，不代表实时进程状态。
旧 UUID 任务保留原 ID；旧记录未知的来源和时间保持空值。

## 查询任务

让 agent 调用 `kea2_list_tasks`，可以按 `origin` 筛选 `cli`、`mcp` 或 `imported`，
并使用 `status`、`limit`、`offset` 分页查询。旧记录的 origin 可能为空。

```json
{"origin": "cli", "limit": 20, "offset": 0}
```

选择具体 task_id 后再要求分析。登记或列出任务不会自动开始分析。
非零退出码也可能表示发现缺陷，不能仅凭 failed 状态认定测试启动失败。

## 登记历史目录

命令行与 MCP 使用同一套登记逻辑。CLI 示例：

```bash
kea2 register-result -p "E:/experiments/res_old"
kea2 register-result -p "E:/experiments/res_old" --stamp old
```

MCP 工具 `kea2_register_result` 示例：

```json
{"result_dir": "E:/experiments/res_old", "stamp": "old"}
```

`stamp` 可以省略。工具只检查指定目录及其直接 `res_*` 子目录，不递归扫描磁盘。
结果目录应保留原始相对结构，例如 `result_<stamp>.json`、`property_exec_info_<stamp>.json`、
`output_<stamp>/` 下的日志和截图。配置文件存在时也应一并保留。只有 HTML 的目录不支持。
可读取的部分结果可以登记，缺失或损坏来源由 availability/warnings 说明；完全不可读取的结果不登记。

| 返回状态 | 操作 |
| --- | --- |
| registered | 使用返回的 task_id 查询；分析仍需明确指定 ID |
| already_registered | 同一实际目录和 stamp 已登记，沿用原 ID |
| selection_required | 按候选列表指定准确目录和 stamp 后重新调用 |
| identity_conflict | ID 已指向其他目录，用户可明确提供别名；不会自动改写旧记录 |
| unsupported / invalid | 查看原因，补齐可支持的结果来源或修正输入 |

指定别名只改变数据库中的 task_id，不修改原始 stamp 和文件名：

```bash
kea2 register-result -p "E:/archive/res_old" --stamp old --task-id archived_old
```

历史登记仅更新数据库，不写入历史目录、不重跑测试、不重新生成 HTML。
元数据提供任务身份，但其中的完成状态未经运行过程验证；导入任务统一为 unknown，
不推测退出码和结束时间。元数据中的原信息作为未验证信息保留。
目录移动导致的 ID 冲突不会自动迁移路径，第一版可明确使用别名登记新位置。

## Hybrid 实验

新 hybrid 运行登记父任务及独立子实验。使用 `kea2_list_tasks(parent_task_id=...)` 查询子任务。
父任务查询结果时返回 CHILD_TASK_REQUIRED，应明确选择子任务进行单实验分析。
历史 hybrid 父目录提供可识别子实验候选；元数据标记为 hybrid 的父目录不会被当作单实验读取。
第一版不汇总多次实验，也不把合并 HTML 解析为单实验数据。

## 使用更新后的功能

重新构建并安装 wheel，重启 MCP 服务。需要 Skill 流程时，同时更新已安装的
`kea2-result-analysis` 文件夹并开启新会话。正常使用现有 `get_report`、`query_report`、
`get_finding` 和 `get_artifact` 分析选定任务。
