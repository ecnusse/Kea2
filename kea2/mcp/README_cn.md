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
并将 `python` 替换为配置中的解释器。安装后重启 MCP 连接，再按下文验证。

## 已实现的工具

服务器当前暴露 6 个工具：

1. `kea2_init`
   - 在当前工作目录初始化 Kea2 项目，生成 `configs/` 目录和模板文件。
   - 支持 `force` 模式覆盖已有配置。
2. `kea2_check_device`
   - 列出本机 ADB 可见的设备。
3. `kea2_run_test`
   - 异步启动一轮 Kea2 测试任务，返回任务句柄。
4. `kea2_get_status`
   - 读取持久化的任务状态，并在 `result_<stamp>.json` 可用时汇总进度。
5. `kea2_get_results`
   - 列出任务输出目录下的文件。
6. `kea2_cancel_test`
   - 取消正在运行的子进程，并尝试清理设备端的 monkey 进程。

## 任务与输出模型

- 任务元数据存储在 SQLite：`~/.kea2/tasks.db`。
- 任务输出目录遵循 Kea2 约定：
  - `<output_parent>/res_<stamp>/`
  - `fastbot_<stamp>.log`
  - `result_<stamp>.json`
  - `property_exec_info_<stamp>.json`（若测试流程产生）

## 典型交互流程

1. `kea2_init` —— 如需要，初始化当前目录（生成 `configs/`）。
2. `kea2_check_device` —— 确认设备连接情况。
3. `kea2_run_test` —— 启动一轮测试，立即返回任务句柄。
4. `kea2_get_status` —— 轮询进度和最终状态。
5. `kea2_get_results` —— 获取生成的文件列表。
6. `kea2_cancel_test` —— 如需提前停止。

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

- `adb devices` 能看到至少一台目标设备。
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
- Fastbot 日志可能包含非 UTF-8 字节。服务器以 `errors="replace"`
  读取，且只返回文件元数据，不返回原始内容。
- 长时间任务是异步的：`kea2_run_test` 立即返回任务句柄，
  客户端应轮询 `kea2_get_status`，而不是阻塞等待测试结束。

## 本仓库中的测试覆盖

MCP 的 E2E 测试位于：

- `tests/fake_kea2_run.py`（假 runner 场景）
- `tests/mcp/test_e2e.py`

覆盖的流程包括：设备查询、init 行为、正常 run、cancel、失败状态、
以及 task store 操作。
