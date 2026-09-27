# Kea2 MCP Server

本模块为 Kea2 提供本地 MCP 服务器，使 AI 客户端（如 Claude Desktop、
Claude Code、Cursor）可以通过自然语言驱动 Kea2 测试任务。

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
pip install "kea2-python[mcp]"
```

## 客户端配置

### Claude Desktop / Cursor

在 `claude_desktop_config.json` 中加入：

```json
{
  "mcpServers": {
    "kea2": {
      "command": "kea2",
      "args": ["mcp"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add kea2 -- kea2 mcp
```

### 如果 `kea2` 命令不在 PATH 中

当 Kea2 装在虚拟环境或使用 `--user` 安装时，AI 客户端可能找不到
`kea2` 命令。此时改用模块形式：

```json
{
  "mcpServers": {
    "kea2": {
      "command": "python3",
      "args": ["-m", "kea2.cli", "mcp"]
    }
  }
}
```

两种写法都可移植，且不含绝对路径。

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

客户端应该调用 `kea2_check_device`（而不是通过 shell 跑 `adb devices`），
并返回设备列表。如果客户端退回 shell 命令，通常说明 MCP 服务器没有
连接成功——检查客户端的 `/mcp` 面板状态。

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