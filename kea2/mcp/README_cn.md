# Kea2 MCP Server

本模块为 Kea2 提供本地 MCP 服务器，使 AI 客户端（如 Claude Desktop、
Claude Code、Cursor、Codex）可以通过自然语言驱动 Kea2 测试任务。

## 部署形态

Kea2 MCP 运行在**本地 STDIO 模式**下：

- AI 客户端以子进程方式启动 `kea2 mcp`。
- 通过 stdin/stdout 交换 JSON-RPC 消息。
- 服务器**不监听任何网络端口**。
- 仅用于本地单机场景。

## 运行栈与兼容性

- MCP SDK：`mcp` 2.x（`MCPServer`）
- 入口：`kea2 mcp` 子命令
- MCP 功能要求的 Python 版本：`>=3.10`
- Kea2 基础包仍兼容 `>=3.8`

当前实现使用的导入方式：

```python
from mcp.server.mcpserver import MCPServer
```

## 安装

安装带 MCP 扩展的 Kea2：

```bash
python -m pip install "kea2-python[mcp]"
```

## 客户端配置

### 选择 Python 环境和测试项目

以下示例以 Windows 上的 `C:/path/to/test_project` 为测试项目目录。
请将所有占位路径替换为自己的绝对路径。测试项目是存放 `configs/`
和测试输出的可写目录，不一定是 Kea2 源码仓库。

- 使用已安装 `kea2-python[mcp]` 的 Python 解释器绝对路径。Windows
  通常为 `.venv/Scripts/python.exe`；macOS/Linux 则使用
  `/absolute/path/to/test_project/.venv/bin/python`。
- 使用该解释器的 `-m pip` 安装依赖。在终端激活虚拟环境，不会使已经
  运行的图形客户端自动使用该环境。
- 将服务器工作目录设为测试项目。Kea2 当前按工作目录查找 `configs/`，
  `kea2_init` 也在这里写入文件。支持 `cwd` 的客户端应在配置中明确填写。
- 只有客户端能够找到正确的解释器、且工作目录正确时，才适合直接使用
  `kea2 mcp` 或 `python -m kea2.cli mcp`。裸写 `python3` 不保证使用
  目标虚拟环境。
- STDIO 服务由客户端启动，无需先在终端另起服务，也无需配置 HTTP 地址或端口。

启动 MCP 前，确认客户端为 MCP 服务设置的工作目录是测试项目根目录；
仅在客户端中打开项目不一定能保证这一点。
若设备检查正常，但启动测试提示找不到 `configs/`，请检查 MCP 服务的工作目录。

### Claude Desktop

在 Claude Desktop 的开发者设置中编辑 `claude_desktop_config.json`。
将以下条目合并到已有的 `mcpServers` 中，保留其他服务器配置。
下面的命令直接启动 Kea2，不负责设置工作目录。

```json
{
  "mcpServers": {
    "kea2": {
      "command": "C:/path/to/test_project/.venv/Scripts/python.exe",
      "args": ["-m", "kea2.cli", "mcp"]
    }
  }
}
```

不同系统的配置文件位置参见
[本地 MCP 配置指南](https://modelcontextprotocol.io/docs/develop/connect-local-servers)。

### Cursor

使用测试项目中的 `.cursor/mcp.json`，或个人全局配置
`~/.cursor/mcp.json`。Cursor **不使用** `claude_desktop_config.json`。
在对应文件中加入上面的 `mcpServers` JSON 配置，替换解释器绝对路径，
并确认服务工作目录与测试项目一致。参见
[Cursor MCP 配置指南](https://prod.cursor.com/help/customization/mcp)。

### Claude Code

在测试项目目录中以 local 作用域注册 Kea2 MCP，避免将本机绝对路径写入
团队共享的项目配置。

Windows（PowerShell）：

```powershell
Set-Location 'C:\path\to\test_project'
claude mcp add --transport stdio --scope local kea2 -- "C:/path/to/test_project/.venv/Scripts/python.exe" -m kea2.cli mcp
```

macOS/Linux：

```bash
cd /absolute/path/to/test_project
claude mcp add --transport stdio --scope local kea2 -- /absolute/path/to/test_project/.venv/bin/python -m kea2.cli mcp
```

使用 `claude mcp get kea2` 检查注册的命令，在 Claude Code 内使用
`/mcp` 检查连接。参见
[Claude Code MCP 指南](https://code.claude.com/docs/en/mcp)。

### Codex

在测试项目的 `.codex/config.toml` 中添加以下内容，或使用个人全局配置
`~/.codex/config.toml`。Codex 支持通过 `cwd` 明确设置服务工作目录。

```toml
[mcp_servers.kea2]
command = 'C:\path\to\test_project\.venv\Scripts\python.exe'
args = ["-m", "kea2.cli", "mcp"]
cwd = 'C:\path\to\test_project'
startup_timeout_sec = 30
```

macOS/Linux 下，将 `command` 改为虚拟环境的 `.venv/bin/python` 绝对路径，
将 `cwd` 改为测试项目绝对路径。项目配置需要在客户端中被信任并允许加载。
参见 [Codex MCP 指南](https://developers.openai.com/codex/mcp) 和
[配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)。

### 配置与安装更新后的生效步骤

完成配置或更新 Kea2 后，重新启动客户端的 MCP 服务连接。
如果客户端没有重启入口，完全退出并重新打开客户端。
仅替换磁盘上的 wheel 或安装文件，不会重新加载现有 Python 进程中的代码。

重新安装**相同版本**的本地 wheel 时，使用 `--force-reinstall`，
并明确指定 MCP 配置中的同一个解释器。例如，已安装 MCP 依赖后，
在测试项目目录运行：

```powershell
& '.\.venv\Scripts\python.exe' -m pip install --force-reinstall --no-deps '.\kea2_python-1.2.4-py3-none-any.whl'
```

```bash
./.venv/bin/python -m pip install --force-reinstall --no-deps ./kea2_python-1.2.4-py3-none-any.whl
```

按实际情况替换 wheel 文件名。`--no-deps` 仅适用于依赖已安装且兼容的环境；
全新环境应安装带 MCP extra 的 wheel，例如
`python -m pip install "./kea2_python-1.2.4-py3-none-any.whl[mcp]"`，
并将 `python` 替换为配置中的解释器。安装后重启 MCP 连接，让客户端调用 `kea2_check_device`。成功返回 `devices` 表示此次 MCP 调用已完成；列表为空表示 ADB 当前未发现设备。参见[快速验证](#快速验证)。

## 已实现的工具

服务器提供 13 个工具，覆盖测试启动、任务管理、历史结果登记和结构化证据查询。下文 JSON 示例中的尖括号表示需要替换的实际 ID。

### `kea2_init`

在当前工作目录初始化 Kea2 项目，生成 `configs/` 目录和模板文件。
支持 `force` 模式覆盖已有配置。

### `kea2_check_device`

列出本机 ADB 可见的设备。

### `kea2_run_test`

异步启动一轮 Kea2 测试，立即返回包含 `task_id` 的任务句柄。
支持原有模糊测试用法，也可以选择加载性质。

#### 参数

| 参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `serial` | 是 | — | 目标 Android 设备序列号。 |
| `packages` | 是 | — | 目标应用包名列表。 |
| `running_minutes` | 否 | `10` | 测试时长，单位为分钟。 |
| `output_dir` | 否 | `output` | 测试输出的父目录。 |
| `property_path` | 否 | 未设置 | 性质 `.py` 文件或目录，支持绝对路径或相对 MCP 服务工作目录的路径。 |
| `property_pattern` | 否 | `test*.py` | 目录发现时的文件名匹配模式；指定单个文件时忽略。 |
| `driver_name` | 否 | `d` | 所选脚本中的设备属性名，例如 `self.d`。 |
| `max_step` | 否 | CLI 默认值 | 最大探索步数，正整数。 |
| `throttle_ms` | 否 | CLI 默认值 | 事件间隔毫秒数，非负整数。 |
| `take_screenshots` | 否 | CLI 默认值 | `true` 时开启每步截图。 |
| `profile_period` | 否 | CLI 默认值 | 覆盖率和截图采集周期，单位为步，正整数。 |
| `restart_app_period` | 否 | CLI 默认值 | 重启应用的步数周期，非负整数；`0` 关闭定期重启。 |
| `act_whitelist_file` | 否 | 未设置 | `configs/awl.strings` 上传到设备的目标路径，与黑名单互斥。 |
| `act_blacklist_file` | 否 | 未设置 | `configs/abl.strings` 上传到设备的目标路径，与白名单互斥。 |

未指定的可选运行参数不转发，沿用 CLI 默认值。`take_screenshots: false`
不会传入 CLI 的 `--take-screenshots` 开启标志。
Activity 名单路径是 **Android 设备路径**，不是本机输入文件。例如
`"act_whitelist_file": "/sdcard/.kea2/awl.strings"` 会将项目的
`configs/awl.strings` 上传到该位置；请事先准备对应配置文件。

例如，在下方任一启动示例中添加以下字段，即可设置 500 毫秒事件间隔、
开启每步截图，并每 20 步采集覆盖率和截图：

```json
{
  "throttle_ms": 500,
  "take_screenshots": true,
  "profile_period": 20
}
```

#### 不显式指定性质的模糊测试

省略 `property_path`，保持原有模糊测试行为：

```json
{
  "serial": "YOUR_DEVICE_SERIAL",
  "packages": ["com.example.app"],
  "running_minutes": 5
}
```

#### 指定性质

指定单个文件：

```json
{
  "serial": "YOUR_DEVICE_SERIAL",
  "packages": ["com.example.app"],
  "running_minutes": 5,
  "property_path": "quicktest.py",
  "driver_name": "d"
}
```

指定目录时，使用 `"property_path": "properties"`，并可设置
`"property_pattern": "test_*.py"`。发现规则沿用 `unittest`：文件名应为可导入的
Python 模块名，嵌套测试包应包含 `__init__.py`。目前按文件选择，不按单个类或方法筛选。

#### 注意事项

创建任务前检查路径和匹配模式。脚本仅在测试子进程中导入，请仅选择可信脚本。
MCP 将选择参数转发给现有 CLI，不改变其性质发现行为。导入失败或未发现任何
性质／不变量时，仍可能继续模糊测试。请查看任务日志，确认实际加载的性质；
仅凭 `running` 或 `finished` 状态不能确认性质已成功加载。
选择参数会保存在任务元数据中。

性质与 Fastbot 探索一起运行，仍受前置条件、概率和执行次数限制；指定文件不保证
其中的性质一定执行。使用新参数前，请重新安装更新后的包并重启 MCP 连接，刷新工具 schema。

### `kea2_get_status`

读取持久化的任务状态，并在 `result_<stamp>.json` 可用时汇总进度。

### `kea2_get_results`

列出任务输出目录下的文件。

### `kea2_cancel_test`

取消正在运行的子进程，并尝试清理设备端的 monkey 进程。

### `kea2_list_tasks`

查询当前用户任务库。可选 status（queued/running/cancelling/cancelled/finished/failed/unknown）、origin（cli/mcp/imported）、parent_task_id、limit（默认 20，1–100）和 offset（默认 0）。返回 tasks、total 和 next_offset。用于找 ID；分析前请用户明确选择任务。

```json
{"origin":"cli","limit":20}
```

### `kea2_register_result`

登记指定的历史实验目录。result_dir 必填；可选 stamp 选择实验，task_id 为用户指定的别名。检查指定目录及直接 res_* 子目录，不修改历史文件。registered 和 already_registered 返回可查询的 ID；selection_required 要求选择候选；identity_conflict 可通过明确指定别名解决；unsupported 或 invalid 会说明原因。只有 HTML 时无法登记。导入任务的结束状态为 unknown。

```json
{"result_dir":"E:/experiments/res_old","stamp":"old"}
```

### `kea2_get_result_schema`

查看结构化数据契约（当前 1.5）。无需 task_id；document 默认为 experiment，也支持 report、query、finding、artifact、error。返回对应 JSON Schema。

```json
{"document":"query"}
```

### `kea2_get_report`

按 task_id 读取概览。返回执行状态和退出信息、性质统计、Activity 覆盖率、控件数量、Crash/ANR 次数、日志观测、来源可用性、警告和 snapshot_id。数据缺失时返回 null。Hybrid 父任务返回 CHILD_TASK_REQUIRED，用 list_tasks 的 parent_task_id 查询子任务后再选择。

```json
{"task_id":"<task_id>"}
```

### `kea2_query_report`

按 task_id 和 section 分页查询。filters、cursor 可选；limit 默认 50，范围 1–100。返回 items、total、next_cursor 和 snapshot_id。翻页时保持筛选条件不变，使用返回的 next_cursor 直到 null。

```json
{"task_id":"<task_id>","section":"checks","filters":{"kind":"property"}}
```

| section | 内容 | 可选筛选字段 |
| --- | --- | --- |
| `checks` | 检查项统计 | name, kind, has_findings |
| `findings` | 逐次性质异常、Crash、ANR | type, check_name, state |
| `activities` | Activity 覆盖 | name, covered |
| `trends` | 覆盖和控件数量趋势 | metric |
| `steps` | 事件时间线 | type, start_step, end_step, execution_id |
| `executions` | 性质执行片段 | id, check_name, kind, state |
| `artifacts` | 已登记证据元数据 | id, kind, availability |
| `widgets` | 控件清单和解析状态 | activity, class_name, resource_id, content_description, parse_status |
| `property_execution_trend` | 已启动的不同 property 数量 | start_step, end_step |
| `configuration` | 运行和报告配置 | document, key |

Property 的通过次数按 `max(executed - fail - error, 0)` 派生。Invariant 只统计 Fail、Error 和异常详情，前置条件、执行、通过次数为 null。Findings 是发生记录；不可读的来源不能按零处理。

### `kea2_get_finding`

传入 findings 页返回的 finding_id 和 snapshot_id，以及 task_id，读取一次异常的堆栈、相关执行片段、前后日志和证据引用。offset 默认 0，limit 默认 8000 个字符（1–32000），沿 next_offset 续读。context_before 和 context_after 默认 0，各允许 0–20 条。关联不明确时不猜测截图。

```json
{"task_id":"<task_id>","finding_id":"<finding_id>","snapshot_id":"<snapshot_id>","context_before":3,"context_after":3}
```

### `kea2_get_artifact`

传入 task_id 以及查询或异常详情返回的 artifact_id、snapshot_id，读取实际内容。文本按字符分页，offset 默认 0，limit 默认 8000（1–32000）。截图要求 offset=0，以 MCP 原生图片和元数据返回（上限 8 MiB）；需客户端支持才能查看。超过 64 MiB 的相关文本来源会标为 too_large。遇到 STALE_SNAPSHOT 时重新获取概览和相应列表。

```json
{"task_id":"<task_id>","artifact_id":"<artifact_id>","snapshot_id":"<snapshot_id>"}
```

## 任务与输出模型

新实验默认以时间戳作为 task_id 和 stamp。CLI 自动登记，MCP 启动时父子进程共用一条记录。实验目录里的 `kea2_task.json` 保存身份信息，旧 UUID 任务仍可查询。

- 任务元数据存储在 SQLite：`~/.kea2/tasks.db`。
- 任务输出目录遵循 Kea2 约定：
  - `<output_parent>/res_<stamp>/`
  - `fastbot_<stamp>.log`（仅由 Fastbot 写入）
  - `kea2_<stamp>.log`（MCP 捕获的 Python 子进程 stdout/stderr）
  - `result_<stamp>.json`
  - `property_exec_info_<stamp>.json`（若测试流程产生）

新任务的诊断 `log_file` 指向 `kea2_<stamp>.log`，启动错误和 Python 异常堆栈
应查看此文件。`kea2_get_results` 会列出两份日志。分开写入可避免并发写入破坏
日志读取的 UTF-8 字节位置。已有任务记录保持不变。

## 典型交互流程

1. `kea2_init` —— 如需要，初始化当前目录（生成 `configs/`）。
2. `kea2_check_device` —— 确认设备连接情况。
3. `kea2_run_test` —— 启动一轮测试，立即返回任务句柄。
4. `kea2_get_status` —— 轮询进度和最终状态。
5. `kea2_get_results` —— 获取生成的文件列表。
6. `kea2_cancel_test` —— 如需提前停止。

分析已有实验时，先用 `kea2_list_tasks` 查找任务，或用 `kea2_register_result` 登记指定的历史目录。用户给出具体 task_id 后，依次读取概览、查询明细，再按需读取异常堆栈和截图。Agent 使用 MCP 返回的证据生成分析报告。参见[如何让 Agent 通过 Kea2 MCP 扩展启动测试、获取并分析测试结果](../../docs/mcp_extension_cn.md)、[分析 Skill 手册](../../docs/result_analysis_skill_cn.md)和[任务登记手册](../../docs/task_registration_cn.md)。

## 前置校验与自动修复提示

在创建任务前，`kea2_run_test` 会做本地前置校验：

- 当前项目目录下必须存在 `configs/`。
- 目标设备序列号必须能从 ADB 中看到。

如果 `configs/` 不存在，工具会返回自动修复风格的响应：

```json
{
  "error": "configs/ 目录不存在",
  "hint": "调用 kea2_init 初始化项目",
  "auto_fixable": true
}
```

## 前置条件

使用前需要满足：

- 启动测试时，`adb devices` 能看到目标设备；读取已保存结果可以离线进行。
- Kea2 已安装在本地环境中。
- AI 客户端支持 MCP 子进程集成。
- 项目根目录可写（`kea2_init` 会创建 `configs/`）。
- MCP 服务器的工作目录与项目根目录一致，否则找不到 `configs/`。

## 快速验证

配置好 AI 客户端后，直接说：

> 帮我看看有哪些 Android 设备连着

明确要求客户端调用 `kea2_check_device`，并检查工具返回值。
通过 shell 执行 `adb devices` 不能证明 MCP 已连接。如果工具不可用或调用失败，
检查客户端的 MCP 设置与日志（Claude Code 中使用 `/mcp`），并核对解释器路径、
依赖和工作目录。设备查询成功本身并不能证明 `configs/` 配置正确。

要端到端验证更新后的安装，可明确指定设备和应用，启动一次短时测试，
在运行中调用 `kea2_get_status`，确认查询不会中断测试且任务最终正常结束。
`result_available: true` 仅表示结果文件已存在，不代表测试已结束。

## 已知限制

- 仅支持本地单机运行。
- 不支持远程共享 / 远程传输。
- 不保证多客户端并发协调。
- `kea2_get_results` 返回文件清单。读取已登记的文本证据请用 `kea2_get_artifact`；非 UTF-8 文本会返回读取错误。
- 长时间任务是异步的：`kea2_run_test` 立即返回任务句柄，
  客户端应轮询 `kea2_get_status`，而不是阻塞等待测试结束。

## 本仓库中的测试覆盖

MCP 的 E2E 测试位于：

- `tests/fake_kea2_run.py`（假 runner 场景）
- `tests/mcp/test_e2e.py`

覆盖的流程包括：设备查询、init 行为、正常 run、cancel、失败状态、
以及 task store 操作。
