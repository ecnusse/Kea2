# 文档

[中文文档](manual_cn.md)

## Kea2 教程

1. [微信](Scenario_Examples_zh.md) 上应用 Kea2 功能 2 和 3 的小教程。

## Kea2 脚本

Kea2 使用 [Unittest](https://docs.python.org/3/library/unittest.html) 来管理脚本。所有 Kea2 脚本遵循 unittest 的用例发现规则（即测试方法应以 `test_` 开头，测试类应继承自 `unittest.TestCase`）。

Kea2 使用 [Uiautomator2](https://github.com/openatx/uiautomator2) 操控 Android 设备。详情请参考 [Uiautomator2 文档](https://github.com/openatx/uiautomator2?tab=readme-ov-file#quick-start)。

一般地，你可以通过以下两步编写 Kea2 脚本：

1. 创建继承 `unittest.TestCase` 的测试类。

```python
import unittest

class MyFirstTest(unittest.TestCase):
    ...
```

2. 通过定义测试方法编写脚本

默认情况下，只有以 `test_` 开头的测试方法会被 unittest 识别。你可以用 `@precondition` 装饰函数。装饰器 `@precondition` 接收一个返回布尔值的函数作为参数。当函数返回 `True` 时，前置条件满足，脚本将被激活，接下来Kea2 会根据装饰器 `@prob` 定义的概率运行脚本。

注意，如果测试方法未被 `@precondition` 装饰，该测试方法在自动化 UI 测试中永远不会被激活，而是被当作普通的 unittest 测试方法处理。因此，当测试方法应始终执行时，需要显式指定 `@precondition(lambda self: True)`。如果未装饰 `@prob`，默认概率为 1（即前置条件满足时始终执行）。

以下是一个推荐的 Kea2 脚本示例。你可以将其作为一个模版。

```python
import unittest
from uiautomator2 import Device  # 引入 uiautomator2 的 Device 类来做类型提示
from kea2 import precondition

class MyFirstTest(unittest.TestCase):
    d: Device  # 类型提示，表示 self.d 是 uiautomator2 的 Device 实例

    @prob(0.7)
    @precondition(lambda self: ...)
    def test_func1(self):
        self.d(...)  # 使用 uiautomator2 的 Device 实例操控设备
        ...
```

更多细节请阅读 [Kea - Write your first property](https://kea-docs.readthedocs.io/en/latest/part-keaUserManuel/first_property.html)。

## 装饰器

### `@precondition`

```python
@precondition(lambda self: ...)
def test_func1(self):
    ...
```

`@precondition` 是一个装饰器，接受一个返回布尔值的函数作为参数。当该函数返回 `True` 时，前置条件满足，函数 `test_func1` 会被激活，并且 Kea2 会基于 `@prob` 装饰器定义的概率值执行 `test_func1`。
如果未指定 `@prob`，默认概率值为 1，此时当前置条件满足时，`test_func1` 会始终执行。

### `@prob`

```python
@prob(0.7)
@precondition(lambda self: ...)
def test_func1(self):
    ...
```

`@prob` 装饰器接受一个浮点数参数，该数字表示当前置条件满足时执行函数 `test_func1` 的概率。概率值应介于 0 到 1 之间。
如果未指定 `@prob`，默认概率值为 1，即当前置条件满足时函数总是执行。

当多个函数的前置条件都满足时，Kea2 会根据它们的概率值随机选择其中一个函数执行。
具体地，Kea2 会生成一个 0 到 1 之间的随机值 `p`，并用 `p` 和这些函数的概率值共同决定哪个函数被选中。

例如，若三个函数 `test_func1`、`test_func2` 和 `test_func3` 的前置条件满足，它们的概率值分别为 `0.2`、`0.4` 和 `0.6`：
- 情况 1：若 `p` 随机取为 `0.3`，由于 `test_func1` 的概率值 `0.2` 小于 `p`，它失去被选中的机会，Kea2 会从 `test_func2` 和 `test_func3` 中随机选一个执行。
- 情况 2：若 `p` 随机取为 `0.1`，Kea2 会从 `test_func1`、`test_func2` 和 `test_func3` 中随机选一个执行。
- 情况 3：若 `p` 随机取为 `0.7`，Kea2 将忽略全部三个函数，不执行它们。

### `@max_tries`

```python
@max_tries(1)
@precondition(lambda self: ...)
def test_func1(self):
    ...
```

`@max_tries` 装饰器接受一个整数参数，表示当前置条件满足时函数 `test_func1` 最多执行的次数。默认值为 `inf`（无限次）。

## 启动 Kea2

我们提供两种方式启动 Kea2。

### 1. 通过 shell 命令启动

你可以通过 shell 命令 `kea2 run` 启动 Kea2。

`kea2 run` 由两部分组成：第一部分是 Kea2 的选项，第二部分是子命令及其参数。

### 1.1 `kea2 run` 参数说明

| 参数 | 意义 | 默认值 |
| --- | --- | --- |
| -s | 设备序列号，可通过 `adb devices` 查看 |  |
| -t | 设备的传输 ID，可通过 `adb devices -l` 查看 |  |
| -p | 指定被测试应用的包名（例如 com.example.app）。*支持多个包：`-p pkg1 pkg2 pkg3`* |  |
| -o | 日志和结果输出目录 | `output` |
| --agent | {native, u2}。默认使用 `u2`，支持 Kea2 三个重要功能。如果想运行原生 Fastbot，请使用 `native`。 | `u2` |
| --running-minutes | 运行 Kea2 的时间（分钟） | `10` |
| --max-step | 发送的最大随机事件数（仅在 `--agent u2` 有效） | `inf`（无限） |
| --throttle | 两次随机事件之间的延迟时间（毫秒） | `200` |
| --driver-name | Kea2 脚本中使用的驱动名称。如果指定 `--driver-name d`，则需用 `d` 操作设备，例如 `self.d(..).click()`。 |  |
| --log-stamp | 日志文件和结果文件的标识（例如指定 `--log-stamp 123`，日志文件命名为 `fastbot_123.log`，结果文件命名为 `result_123.json`） | 当前时间戳 |
| --profile-period | 覆盖率分析和截图采集周期（单位为随机事件数）。截图保存在设备 SD 卡，根据设备存储调整此值。 | `25` |
| --take-screenshots | 在每个随机事件执行时截图，截图会被周期性地自动从设备拉取到主机（周期由 `--profile-period` 指定）。 |  |
| --pre-failure-screenshots | 失败前截取的截图数量。0 表示每步都截图。该选项仅在 `--take-screenshots` 设置时有效。 | `0` |
| --post-failure-screenshots | 失败后截取的截图数量。应小于等于 `--pre-failure-screenshots`。该选项仅在 `--take-screenshots` 设置时有效。 | `0` |
| --device-output-root | 设备输出目录根路径，Kea2 将暂存截图和结果日志到 `"<device-output-root>/output_*********/"`。确保该目录可访问。 | `/sdcard` |

### 1.2 子命令及其参数

Kea2 支持 3 个子命令：`propertytest`、`unittest` 和 `--`（额外参数）。

#### **1.2.1 `propertytest` 子命令及测试发现（基于性质的测试）**

Kea2 兼容 `unittest` 框架。你可以用 unittest 风格管理测试用例，并使用 [unittest 发现选项](https://docs.python.org/3/library/unittest.html#test-discovery) 发现测试用例。你可以用 `kea run` 加上驱动参数和子命令 `propertytest` 启动 Kea2。

shell 命令示例：
```
# <unittest discovery cmds> 是 unittest 发现命令，例如 `discover -p quicktest.py`
kea2 run <Kea2 cmds> propertytest <unittest discovery cmds> 
```

示例 shell 命令：

```bash
# 启动 Kea2 并加载单个脚本 quicktest.py
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d propertytest discover -p quicktest.py

# 启动 Kea2 并从目录 mytests/omni_notes 加载多个脚本
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d propertytest discover -s mytests/omni_notes -p test*.py
```

#### **1.2.2（实验性功能）`unittest` 子命令（混合测试）**

> 该功能仍在开发中，期待您的反馈！如有兴趣，请联系我们。

`unittest` 子命令用于功能 4（混合测试）。你可以用 `kea run` 加上驱动参数和子命令 `unittest` 启动 Kea2。与 `propertytest` 一样，你可以使用 [unittest 发现选项](https://docs.python.org/3/library/unittest.html#test-discovery) 加载测试用例。

#### **1.2.3 `--` 子命令（额外参数）**

如果需要向底层 Fastbot 传递额外参数，请在常规参数后添加 `--`，然后列出额外参数。例如，设置触摸事件比例为 30%：

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d -- --pct-touch 30 unittest discover -p quicktest.py
```

### 2. 通过 `unittest.main` 启动 Kea2

像 unittest 一样，可以通过 `unittest.main` 方法启动 Kea2。

示例（保存为 `mytest.py`），你可以看到选项直接定义在脚本中。

```python
import unittest

from kea2 import KeaTestRunner, Options
from kea2.u2Driver import U2Driver

class MyTest(unittest.TestCase):
    ...
    # <你的测试方法>

if __name__ == "__main__":
    KeaTestRunner.setOptions(
        Options(
            driverName="d",
            Driver=U2Driver,
            packageNames=[PACKAGE_NAME],
            # serial="emulator-5554",   # 指定设备序列号
            maxStep=100,
            # running_mins=10,  # 指定最大运行时间（分钟），默认10分钟
            # throttle=200,   # 指定延迟时间（毫秒），默认200毫秒
            # agent='native'  # 'native' 运行原生 Fastbot
        )
    )
    # 声明 KeaTestRunner
    unittest.main(testRunner=KeaTestRunner)
```

运行该脚本启动 Kea2，如：
```bash
python3 mytest.py
```

以下是 `Options` 中的所有可用选项。

```python
# 脚本中的驱动名称（如 self.d，则为 d）
driverName: str = None
# 驱动（当前只有 U2Driver）
Driver: AbstractDriver = None
# 包名列表，指定被测试的应用
packageNames: List[str] = None
# 目标设备序列号
serial: str = None
# 目标设备传输 ID
transport_id: str = None
# 测试 agent，默认 "u2"
agent: Literal["u2", "native"] = "u2"
# 最大探索步数（功能 2~3 有效）
maxStep: Union[str, float] = float("inf")
# 探索时长（分钟）
running_mins: int = 10
# 探索时等待时间（毫秒）
throttle: int = 200
# 日志和结果保存目录
output_dir: str = "output"
# 日志文件和结果文件的时间戳标识，默认当前时间戳
log_stamp: str = None
# 覆盖率采样周期
profile_period: int = 25
# 是否每步截图
take_screenshots: bool = False
# 失败前截取的截图数量，0 表示每步都截图
pre_failure_screenshots: int = 0
# 失败后截取的截图数量，需要小于等于 pre_failure_screenshots
post_failure_screenshots: int = 0
# 设备上的输出目录根路径
device_output_root: str = "/sdcard"
# 是否启用调试模式
debug: bool = False
# Activity 白名单文件
act_whitelist_file: str = None
# Activity 黑名单文件
act_blacklist_file: str = None
# propertytest 子命令参数（例如 discover -s xxx -p xxx）
propertytest_args: str = None
# unittest 子命令参数（功能 4）
unittest_args: List[str] = None
# 额外参数（直接传递给 fastbot）
extra_args: List[str] = None
```

## 管理 Kea2 报告

### 生成 kea2 报告（`kea2 report`）

`kea2 report` 命令根据已有的测试结果生成 HTML 测试报告。该命令分析测试数据，创建一个全面的可视化报告，展示测试执行统计、覆盖率信息、性质违规和崩溃详情。

| 参数 | 意义 | 是否必需 | 默认值 |
| --- | --- | --- | --- |
| -p, --path | 测试结果目录路径（res_* 目录） | 是 |  |

**使用示例：**

```bash
# 从测试结果目录生成报告
kea2 report -p res_20240101_120000

# 从多个测试结果目录生成报告
kea2 report -p ./output/res_20240101_120000 /Users/username/kea2_tests/res_20240102_130001
```

**报告内容包括：**
- **测试摘要**：发现的总缺陷数、执行时间、覆盖率百分比
- **性质测试结果**：每个测试性质的执行统计（前置条件满足次数、执行次数、失败次数、错误次数）
- **代码覆盖率**：Activity 覆盖趋势及详细覆盖信息
- **性质违规**：失败的测试性质详细信息及错误堆栈
- **崩溃事件**：测试中检测到的应用崩溃
- **ANR 事件**：应用无响应事件
- **截图**：测试过程中采集的 UI 截图（如果启用）
- **Activity 遍历**：测试过程中访问的 Activity 历史

**输出内容：**
该命令生成：
- 指定测试结果目录下的 HTML 报告文件（`bug_report.html`）
- 覆盖率和执行趋势的交互式图表和可视化
- 用于调试的详细错误信息和堆栈跟踪

**输入目录结构示例：**
```
res_<timestamp>/
├── bug_report_config.json           # 报告配置 (包含测试信息)
├── result_<timestamp>.json          # 性质测试结果
├── output_<timestamp>/
│   ├── steps.log                    # 测试执行步骤
│   ├── coverage.log                 # 覆盖率数据
│   ├── crash-dump.log               # 崩溃和 ANR 事件
│   └── screenshots/                 # UI 截图（如果启用）
└── property_exec_info_<timestamp>.json  # 性质执行详情
```

### 合并多个测试报告（`kea2 merge`）

`kea2 merge` 命令允许合并多个测试报告目录，生成合并后的报告。当你运行了多次测试并希望将结果合并成一个综合报告时非常有用。

| 参数 | 意义 | 是否必需 | 默认值 |
| --- | --- | --- | --- |
| -p, --paths | 需要合并的测试报告目录路径（res_* 目录），至少需要两个路径 | 是 |  |
| -o, --output | 合并报告的输出目录 | 否 | `merged_report_<timestamp>` |

**使用示例：**

```bash
# 合并两个测试报告目录
kea2 merge -p res_20240101_120000 res_20240102_130000

# 合并多个测试报告目录并指定输出目录
kea2 merge -p res_20240101_120000 res_20240102_130000 res_20240103_140000 -o my_merged_report

# 启用调试模式合并
kea2 -d merge -p res_20240101_120000 res_20240102_130000
```

**合并内容包括：**
- 性质测试执行统计（前置条件满足、执行、失败、错误）
- 代码覆盖率数据（覆盖的 Activity、覆盖率百分比）
- 崩溃和 ANR 事件
- 测试执行步骤和时间信息

**输出内容：**
该命令生成：
- 包含合并数据的报告目录
- 带有可视化摘要的 HTML 报告（`merged_report.html`）
- 合并元数据，包括源目录和时间戳

## 调试模式（`kea2 -d ...`）

你可以通过添加 `-d` 选项启用调试模式。在调试模式下，Kea2 会打印更详细的日志，帮助诊断问题。

| 参数 | 意义 | 默认值 |
| --- | --- | --- |
| -d | 启用调试模式 |  |

> ```bash
> # 加上 -d 启用调试模式
> kea2 -d run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
> ```

## 查看脚本运行统计

如果想查看你的脚本是否被执行及执行次数，测试结束后打开 `result.json` 文件。

示例：

```json
{
    "test_goToPrivacy": {
        "precond_satisfied": 8,
        "executed": 2,
        "fail": 0,
        "error": 1
    },
    ...
}
```

**如何解读 `result.json`**

字段 | 说明 | 含义
--- | --- | --- 
precond_satisfied | 在探索过程中，测试方法的前置条件满足次数 | 是否到达了该状态                                             
executed | UI 测试过程中，测试方法被执行的次数 | 该测试方法是否执行过 
fail | UI 测试中，测试方法断言失败次数 | 失败时，测试方法发现了可能的功能缺陷 
error | UI 测试中，测试方法因发生意外错误（如找不到某些 UI 控件）中断的次数 | 出现错误时，意味着脚本需要更新或修复，因为脚本导致了意外错误 

## 配置文件

执行 `Kea2 init` 后，会在 `configs` 目录生成一些配置文件。
这些配置文件属于 `Fastbot`，具体介绍请参见 [配置文件介绍](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E4%B8%93%E5%AE%B6%E7%B3%BB%E7%BB%9F)。

## 用户配置文件更新

更新 Kea2 时，用户本地配置有时需要更新。（最新 Kea2 版本可能与旧配置文件不兼容。）

当检测到运行时错误时，Kea2 会检查本地配置文件是否与当前 Kea2 版本兼容。如果不兼容，控制台会打印警告信息。请根据以下步骤更新本地配置文件：

1. 备份本地配置文件（以防更新过程中出现意外问题）。
2. 删除项目根目录下 `/configs` 中的所有配置文件。
3. 运行 `kea2 init` 生成最新配置文件。
4. 根据需要将旧配置合并到新配置文件中。

## 应用崩溃缺陷

Kea2 会将触发的崩溃缺陷转储在由 `-o` 指定输出目录中的 `fastbot_*.log` 文件内。你可以在 `fastbot_*.log` 中搜索关键词 `FATAL EXCEPTION` 来获取崩溃缺陷的具体信息。

这些崩溃缺陷也会记录在你的设备上。[详情请参考 Fastbot 手册](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E7%BB%93%E6%9E%9C%E8%AF%B4%E6%98%8E)。

## 与第三方包交互

Kea2 默认会阻止探索过程中与第三方包（如广告包）的交互。如果你想与这些包交互，请在启动 Kea2 时的[额外参数](#---子命令-额外参数)中添加 `--allow-any-starts`。

例如：

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver -- --allow-any-starts propertytest discover -p quicktest.py
```