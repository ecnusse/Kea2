# 文档

[中文文档](manual_cn.md)

## Kea2 教程 

1. 一个关于如何在 [WeChat](Scenario_Examples_zh.md) 上应用 Kea2 的特性 2 和 3 的简短教程。

## Kea2 脚本

Kea2 使用 [Unittest](https://docs.python.org/3/library/unittest.html) 管理脚本。所有 Kea2 的脚本都可以在 unittest 的规则下找到（即测试方法应以 `test_` 开头，测试类应继承自 `unittest.TestCase`）。

Kea2 使用 [Uiautomator2](https://github.com/openatx/uiautomator2) 操作安卓设备。详情请参考 [Uiautomator2 的文档](https://github.com/openatx/uiautomator2?tab=readme-ov-file#quick-start)。

基本上，你可以通过以下两步编写 Kea2 脚本：

1. 创建一个继承 `unittest.TestCase` 的测试类。

```python
import unittest

class MyFirstTest(unittest.TestCase):
    ...
```

2. 通过定义测试方法撰写自己的脚本

默认情况下，只有以 `test_` 开头的测试方法会被 unittest 发现。你可以使用 `@precondition` 装饰函数。装饰器 `@precondition` 接受一个返回布尔值的函数作为参数。当该函数返回 `True` 时，前置条件满足，该脚本将被激活，Kea2 会根据装饰器 `@prob` 定义的概率执行该脚本。

注意如果测试方法没有用 `@precondition` 装饰，该测试方法在自动化 UI 测试时不会被激活，会被视为普通的 `unittest` 测试方法。
因此，当测试方法应始终执行时，需要显式指定 `@precondition(lambda self: True)`。当测试方法没有被 `@prob` 装饰时，默认概率为 1（前置条件满足时始终执行）。

```python
import unittest
from kea2 import precondition

class MyFirstTest(unittest.TestCase):

    @prob(0.7)
    @precondition(lambda self: ...)
    def test_func1(self):
        ...
```

你可以阅读 [Kea - 编写你的第一个 property](https://kea-docs.readthedocs.io/en/latest/part-keaUserManuel/first_property.html) 了解更多细节。

## 装饰器

### `@precondition`

```python
@precondition(lambda self: ...)
def test_func1(self):
    ...
```

装饰器 `@precondition` 接受一个返回布尔值的函数作为参数。当函数返回 `True` 时，前置条件满足，函数 `test_func1` 将被激活，Kea2 会根据装饰器 `@prob` 指定的概率执行 `test_func1`。
如果未指定 `@prob`，默认概率值为 1。在这种情况下，只要前置条件满足，函数 `test_func1` 总会被执行。

### `@prob`

```python
@prob(0.7)
@precondition(lambda self: ...)
def test_func1(self):
    ...
```

装饰器 `@prob` 接受一个浮点数作为参数，表示当前置条件（由 `@precondition` 指定）满足时执行 `test_func1` 的概率。概率值应在 0 和 1 之间。
如果未指定 `@prob`，默认概率值为 1，表示只要前置条件满足，函数 `test_func1` 总会被执行。

当多个函数的前置条件均满足时，Kea2 会根据它们的概率值随机选择一个函数执行。
具体地，Kea2 会生成一个 0 到 1 之间的随机值 `p`，用它来决定根据概率值选择哪个函数。

例如，如果函数 `test_func1`、`test_func2` 和 `test_func3` 的前置条件均满足，概率值分别为 `0.2`、`0.4` 和 `0.6`。
- 情况 1：如果 `p` 随机为 `0.3`，`test_func1` 的概率 `0.2` 小于 `p`，它失去被选择的机会，Kea2 会从 `test_func2` 和 `test_func3` 中随机选择一个执行。
- 情况 2：如果 `p` 随机为 `0.1`，Kea2 会从 `test_func1`、`test_func2` 和 `test_func3` 中随机选择一个执行。
- 情况 3：如果 `p` 随机为 `0.7`，Kea2 会忽略这三个函数，不执行它们。

### `@max_tries`

```python
@max_tries(1)
@precondition(lambda self: ...)
def test_func1(self):
    ...
```

装饰器 `@max_tries` 接受一个整数作为参数。该数字表示当前置条件满足时，`test_func1` 函数最多被执行的次数。默认值为 `inf`（无限次）。

## 启动 Kea2

我们提供两种方式启动 Kea2。

### 1. 通过 shell 命令启动

Kea2 兼容 `unittest` 框架。你可以以 unittest 风格管理测试用例。可以使用 `kea run` 命令，辅以驱动选项和子命令 `unittest`（用于 unittest 选项）启动 Kea2。

shell 命令格式：
```
kea2 run <Kea2 命令> unittest <unittest 命令> 
```

示例 shell 命令：

```bash
# 启动 Kea2 并加载单个脚本 quicktest.py。
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py

# 启动 Kea2 并从目录 mytests/omni_notes 加载多个脚本
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -s mytests/omni_notes -p test*.py
```

### `kea2 run` 选项

| 参数 | 含义 | 默认值 | 
| --- | --- | --- |
| -s | 设备序列号，可通过 `adb devices` 获取 | |
| -t | 设备传输 ID，可通过 `adb devices -l` 获取 | |
| -p | 被测应用的包名（例如 com.example.app） | |
| -o | 日志和结果的输出目录 | `output` |
| --agent |  {native, u2}。默认使用 `u2`，支持 Kea2 的三个重要特性。若希望运行原版 Fastbot，请使用 `native`。 | `u2` |
| --running-minutes | 运行 Kea2 的时间（分钟） | `10` |
| --max-step | 最大猴子事件数（仅在 `--agent u2` 时可用） | `inf`（无限） |
| --throttle | 两个猴子事件之间的延迟时间（毫秒） | `200` |
| --driver-name | Kea2 脚本中使用的驱动名称。如果指定为 `--driver-name d`，则应使用 `d` 与设备交互，例如 `self.d(..).click()`。 | |
| --log-stamp | 日志文件和结果文件的时间戳（例如指定 `--log-stamp 123`，日志文件将命名为 `fastbot_123.log` 和 `result_123.json`） | 当前时间戳 |
| --profile-period | 用于覆盖率分析和收集 UI 截图的周期（以猴子事件数计）。截图保存于移动设备的 SD 卡上，应根据设备存储空间合理设置。 | `25` |
| --take-screenshots | 在每个猴子事件时截取 UI 截图，并周期性自动从移动设备拉取至主机（周期由 `--profile-period` 指定）。 |  |
| --device-output-root | 设备端输出根目录。Kea2 会临时将截图和结果日志保存至 `"<device-output-root>/output_*********/"` 目录。请确保根目录可访问。 | `/sdcard` |
| unittest | 指定要加载的脚本。此子命令 `unittest` 完全兼容 unittest。更多选项请参见 `python3 -m unittest -h`。仅在 `--agent u2` 时可用。 |

### `kea` 选项

| 参数 | 含义 | 默认值 | 
| --- | --- | --- |
| -d | 启用调试模式 | |

> ```bash
> # 添加 -d 可启用调试模式
> kea2 -d run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
> ```

### 2. 通过 `unittest.main` 启动

与 unittest 一样，我们也可以通过方法 `unittest.main` 启动 Kea2。

以下为示例（名为 `mytest.py`）。你可以看到选项直接定义在脚本中。

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
            # serial="emulator-5554",   # 指定序列号
            maxStep=100,
            # running_mins=10,  # 指定最大运行时间（分钟），默认 10 分钟
            # throttle=200,   # 指定延迟时间（毫秒），默认 200 毫秒
            # agent='native'  # 'native' 表示运行原生 Fastbot
        )
    )
    # 声明 KeaTestRunner
    unittest.main(testRunner=KeaTestRunner)
```

我们可以直接运行脚本 `mytest.py` 来启动 Kea2，例如：
```python
python3 mytest.py
```

以下为 `Options` 中所有可用选项。

```python
# 脚本中驱动名称（如果为 self.d，则为 d）
driverName: str
# 驱动（当前仅支持 U2Driver）
Driver: U2Driver
# 包名列表，指定被测应用
packageNames: List[str]
# 目标设备
serial: str = None
# 测试代理。默认值为 "u2"
agent: "u2" | "native" = "u2"
# 探索的最大步数（阶段 2~3 可用）
maxStep: int # 默认 "inf"
# 探索时长(分钟)
running_mins: int = 10
# 探索时等待时间（毫秒）
throttle: int = 200
# 保存日志和结果的输出目录
output_dir: str = "output"
# 日志文件和结果文件的时间戳，默认：当前时间戳
log_stamp: str = None
# 覆盖率分析的周期
profile_period: int = 25
# 是否在每步截屏
take_screenshots: bool = False
# 设备端输出根目录
device_output_root: str = "/sdcard"
# 调试模式
debug: bool = False
```

## 查看脚本运行统计

如果你想查看测试期间脚本是否被执行过或执行次数，可在测试结束后打开 `result.json` 文件。

示例如下：

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

**如何读取 `result.json`**

字段 | 描述 | 含义
--- | --- | --- |
precond_satisfied | 探索过程中，测试方法的前置条件满足次数 | 是否达到该状态？
executed | UI 测试期间测试方法执行次数 | 测试方法是否被执行过？
fail | UI 测试期间断言失败次数 | 失败时，测试方法检测到疑似功能缺陷
error | UI 测试期间因意外错误（如测试方法使用的某些 UI 控件找不到）中止次数 | 出现错误时，脚本需更新/修复，因为脚本导致了意外错误

## 配置文件

执行 `Kea2 init` 后，一些配置文件会生成在 `configs` 目录下。
这些配置文件属于 `Fastbot`，具体介绍请参见 [配置文件介绍](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E4%B8%93%E5%AE%B6%E7%B3%BB%E7%BB%9F)。

## App 崩溃缺陷

Kea2 会将触发的崩溃缺陷记录在输出目录（由 `-o` 指定）生成的 `fastbot_*.log` 文件中。你可以搜索关键词 `FATAL EXCEPTION` 来查找具体崩溃信息。

这些崩溃缺陷也会记录在你的设备上。[详情请参见 Fastbot 手册](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E7%BB%93%E6%9E%9C%E8%AF%B4%E6%98%8E)。