# 文档

[English](/docs/manual_en.md) | 简体中文

## 目录

### 1. Kea2 的工具理念
- [Kea2 的工具理念](#1-kea2-的工具理念)
### 2. 如何编写 Kea2 脚本
- [Kea2 脚本教程](#kea2-脚本教程)
- [Kea2 脚本 API（测试类结构与装饰器）](#kea2-脚本-api)
### 3. 如何启动 Kea2
- [命令行启动](#1-通过-shell-命令启动) (`kea2 run` 参数、子命令与返回码)
- [在 Python 代码中启动（`unittest.main`）](#2-通过-unittestmain-启动-kea2)
### 4. 如何阅读和管理 Kea2 测试报告
- [阅读 Kea2 测试报告（属性检查结果字段）](#阅读-kea2-报告)
- [生成 Kea2 测试报告](#生成-kea2-报告kea2-report)
- [合并多个测试报告](#合并多个测试报告kea2-merge)
### 5. 配置文件
- [Fastbot 配置文件](#fastbot-配置文件)
- [黑白名单](#activity-黑白名单)
- [更新用户配置文件](#用户配置文件更新)
### 6. 高级功能
- [高级功能 1：带状态测试](#高级功能-1带状态测试stateful-testing)
- [高级功能 2：不变式检查](#高级功能-2不变式检查invariant-checks)
- [高级功能 3：复用回归脚本](#高级功能-3复用回归脚本兼容已有脚本通过前置脚本步骤到达特定层次)
### 7. 常见问题与技巧
- [FAQ](#faq)
- [与第三方包交互](#与第三方包交互)
- [提升 Kea2 性能的建议](#提升-kea2-性能的建议)

# Kea2 的工具理念

- :star: [Blog: 别再苦哈哈写测试脚本了，生成它们吧！](https://mp.weixin.qq.com/s/R2kLCkXpDjpa8wCX4Eidtg)
- :star: [Kea2 分享交流会 (2025.09, bilibili 录播)](https://www.bilibili.com/video/BV1CZYNz9Ei5/)
- [Kea2 与 PBT 常见问答](https://sy8pzmhmun.feishu.cn/wiki/SLGwwqgzIiEuC3kwmV8cSZY0nTg?from=from_copylink)
- [Kea2 101（从 0 到 1 入门与最佳实践）](https://sy8pzmhmun.feishu.cn/wiki/EwaWwPCitiUJoBkIgALcHtglnDK?from=from_copylink)

# Kea2 脚本教程

我们提供两个教程，展示如何编写 Kea2 脚本，并演示 Kea2 脚本的示例用法。

1. [使用 Kea2 的功能 2 和 功能 3 进行测试（以微信为例）](Scenario_Examples_zh.md)
2. [编写 Kea2 脚本对应用特定功能进行压力测试（以飞书为例）](https://sy8pzmhmun.feishu.cn/wiki/Clqbwxx7ciul5DkEyq8c6edxnTc)

# Kea2 脚本 API

基本上，你可以通过以下两步编写 Kea2 脚本：

### 1. 创建继承 `unittest.TestCase` 的测试类

```python
import unittest 

class MyFirstTest(unittest.TestCase):
    ...
```

> Kea2 使用 [unittest](https://docs.python.org/3/library/unittest.html) 来管理脚本。测试类需继承自 `unittest.TestCase`。

你可以选择性地定义 `setUpClass`，用于在测试类级别做一次性初始化（如准备共享资源），也可以用于[对 u2 driver 进行全局设置](https://github.com/openatx/uiautomator2?tab=readme-ov-file#global-settings)。该方法是可选的，只有定义了才会在测试方法执行前调用一次。

### 2. 通过定义测试方法编写脚本

你可以用 `@precondition` 装饰函数。装饰器 `@precondition` 接收一个返回布尔值的函数作为参数。当函数返回 `True` 时，前置条件满足，脚本将被激活，接下来 Kea2 会根据装饰器 `@prob` 定义的概率运行脚本。

注意，如果测试方法未被 `@precondition` 装饰，该测试方法在自动化 UI 测试中永远不会被激活，而是被当作普通的 unittest 测试方法处理。因此，当测试方法应始终执行时，需要显式指定 `@precondition(lambda self: True)`。（如果想在每一步都检查某些性质，可以使用[不变式检查](#advanced-feature-2-ivariant-checks-不变式检查)）。如果未装饰 `@prob`，默认概率为 1（即前置条件满足时始终执行）。

以下是一个推荐的 Kea2 脚本模版：

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

> Kea2 使用 [uiautomator2](https://github.com/openatx/uiautomator2) 操控 Android 设备。详情请参考 [uiautomator2 文档](https://github.com/openatx/uiautomator2?tab=readme-ov-file#quick-start)。

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

# 启动 Kea2

我们提供两种方式启动 Kea2。

## 1. 通过 shell 命令启动

你可以通过 shell 命令 `kea2 run` 启动 Kea2。

`kea2 run` 由两部分组成：第一部分是 Kea2 的选项，第二部分是子命令及其参数。

### 1.1 `kea2 run` 参数说明

| 参数 | 意义 | 默认值 |
| --- | --- | --- |
| -s | 设备序列号，可通过 `adb devices` 查看 |  |
| -t | 设备的传输 ID，可通过 `adb devices -l` 查看 |  |
| -p | 指定被测试应用的包名（例如 com.example.app）。*支持多个包：`-p pkg1 pkg2 pkg3`* |  |
| -o | 日志和结果输出目录 | `output` |
| --running-minutes | 运行 Kea2 的时间（分钟） | `10` |
| --max-step | 发送的最大随机事件数 | `inf`（无限） |
| --throttle | 两次随机事件之间的延迟时间（毫秒） | `200` |
| --driver-name | Kea2 脚本中使用的驱动名称。如果指定 `--driver-name d`，则需用 `d` 操作设备，例如 `self.d(..).click()`。 | `d` |
| --log-stamp | 日志文件和结果文件的标识（例如指定 `--log-stamp 123`，日志文件命名为 `fastbot_123.log`，结果文件命名为 `result_123.json`） | 当前时间戳 |
| --profile-period | 覆盖率分析和截图采集周期（单位为随机事件数）。截图保存在设备 SD 卡，根据设备存储调整此值。 | `25` |
| --take-screenshots | 在每个随机事件执行时截图，截图会被周期性地自动从设备拉取到主机（周期由 `--profile-period` 指定）。 |  |
| --pre-failure-screenshots | 失败前截取的截图数量。0 表示每步都截图。该选项仅在 `--take-screenshots` 设置时有效。 | `0` |
| --post-failure-screenshots | 失败后截取的截图数量。应小于等于 `--pre-failure-screenshots`。该选项仅在 `--take-screenshots` 设置时有效。 | `0` |
| --restart-app-period | 运行过程中重启被测应用的周期（随机事件数）。 | `0`（不重启） |
| --device-output-root | 设备输出目录根路径，Kea2 将暂存截图和结果日志到 `"<device-output-root>/output_*********/"`。确保该目录可访问。 | `/sdcard` |
| --act-whitelist-file | Activity 白名单文件。可传自定义路径；若只写参数名不带值，则默认 `/sdcard/.kea2/awl.strings`。 |  |
| --act-blacklist-file | Activity 黑名单文件。可传自定义路径；若只写参数名不带值，则默认 `/sdcard/.kea2/abl.strings`。 |  |

### 1.2 子命令及其参数

Kea2 支持 3 个子命令：`propertytest`、`unittest` 和 `--`（额外参数）。

#### **1.2.1 `propertytest` 子命令及测试发现（基于性质的测试）**

Kea2 兼容 `unittest` 框架。你可以用 unittest 风格管理测试用例，并使用 [unittest 发现选项](https://docs.python.org/3/library/unittest.html#test-discovery) 发现测试用例。你可以用 `kea2 run` 加上驱动参数和子命令 `propertytest` 启动 Kea2。

shell 命令示例：
```
# <unittest discovery cmds> 是 unittest 发现命令，例如 `discover -p quicktest.py`
kea2 run <Kea2 cmds> propertytest <unittest discovery cmds> 
```

示例 shell 命令：

```bash
# 启动 Kea2 并加载单个脚本 quicktest.py
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10 propertytest discover -p quicktest.py

# 启动 Kea2 并从目录 mytests/omni_notes 加载多个脚本
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10 propertytest discover -s mytests/omni_notes -p test*.py
```

#### **1.2.2（实验性功能）`unittest` 子命令（混合测试）**

> 该功能仍在开发中，期待您的反馈！如有兴趣，请联系我们。

`unittest` 子命令用于功能 4（混合测试）。你可以用 `kea2 run` 加上驱动参数和子命令 `unittest` 启动 Kea2。与 `propertytest` 一样，你可以使用 [unittest 发现选项](https://docs.python.org/3/library/unittest.html#test-discovery) 加载测试用例。

#### **1.2.3 `--` 子命令（额外参数）**

如果需要向底层 Fastbot 传递额外参数，请在常规参数后添加 `--`，然后列出额外参数。例如，设置触摸事件比例为 30%：

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10 -- --pct-touch 30 unittest discover -p quicktest.py
```

### 返回码

`kea2 run`（以及 `python -m kea2.cli run`）的退出码如下：

| code | 含义 |
| --- | --- |
| `0` | 成功。测试运行完成，且没有测试失败。 |
| `1` | 检测到性质违反（Property violation）。 |
| `2` | 检测到 Crash 或 ANR。 |
| `3` | 同时检测到性质违反和 Crash 或 ANR。 |
| `4` | 非预期运行时错误。 |

说明：
- `KeyboardInterrupt`（Ctrl-C）按正常停止处理，不归类为非预期运行时错误。

## 2. 通过 `unittest.main` 启动 Kea2

像 unittest 一样，可以通过 `unittest.main` 方法启动 Kea2。

示例（保存为 `mytest.py`），你可以看到选项直接定义在脚本中。

```python
import unittest

from kea2 import KeaTestRunner, Options, keaTestLoader

class MyTest(unittest.TestCase):
    ...
    # <你的测试方法>

if __name__ == "__main__":
    KeaTestRunner.setOptions(
        Options(
            driverName="d",
            packageNames=[PACKAGE_NAME],
            # serial="emulator-5554",   # 指定设备序列号
            maxStep=100,
            # running_mins=10,  # 指定最大运行时间（分钟），默认10分钟
            # throttle=200,   # 指定延迟时间（毫秒），默认200毫秒
        )
    )
    # 声明 KeaTestRunner
    unittest.main(testRunner=KeaTestRunner, testLoader=keaTestLoader)
```

运行该脚本启动 Kea2，如：
```bash
python3 mytest.py
```

# 阅读与管理 Kea2 报告

**[:page_facing_up: 查看单次示例报告](https://ecnusse.github.io/Kea2_sample_report/)** - *由 OPay 提供*

**[:page_facing_up: 查看多次合并示例报告](https://ecnusse.github.io/kea2_sample_test_report/)**

## 阅读 Kea2 报告
### 属性检查结果字段含义

字段 | 说明 | 含义
--- | --- | ---
precond_satisfied | 在探索过程中，测试方法前置条件满足的次数 | 是否到达该状态
executed | 在 UI 测试过程中，测试方法实际执行次数 | 是否真的触发过该脚本
fail | 脚本断言失败次数 | 失败通常表示发现了潜在功能缺陷
error | 脚本异常中断次数（如目标控件找不到） | 脚本本身可能需要修复或更新

### 控件覆盖率含义

控件覆盖率统计的是探索过程中被触发的不同控件。一个控件由 `<activity, class, resourceId, content-desc>` 组合唯一标识。

### 基于报告优化测试

1. 先设置合理测试时长。覆盖率通常会在一段时间后趋于饱和，时长更长不一定收益更高。可以根据覆盖率趋势图找到饱和点，再设定预算。多次短跑往往比一次长跑更有效。
2. 设计脚本突破卡点。建议先用 `--take-screenshots` 观察卡住位置（例如登录页）；再补充对应脚本引导穿越该状态。脚本稳定后，可使用 `--pre-failure-screenshots` 与 `--post-failure-screenshots` 控制截图量，减少性能开销。

## 管理 Kea2 报告
### 生成 kea2 报告（`kea2 report`）

`kea2 report` 命令根据已有的测试结果生成 HTML 测试报告。该命令分析测试数据，创建一个全面的可视化报告，展示测试执行统计、覆盖率信息、性质违反和崩溃详情。

| 参数 | 意义 | 是否必需 |
| --- | --- | --- |
| -s, --sync | 生成报告前从设备同步数据 | 否 |
| -p, --path | 测试结果目录路径（res_* 目录） | 是 |

**使用示例：**

```bash
# 从测试结果目录生成报告
kea2 report -p res_20240101_120000

# 生成报告前同步设备数据
kea2 report -s -p res_20240101_120000

# 从多个测试结果目录生成报告
kea2 report -p ./output/res_20240101_120000 /Users/username/kea2_tests/res_20240102_130001
```

### 合并多个测试报告（`kea2 merge`）

`kea2 merge` 命令允许合并多个测试报告目录，生成合并后的报告。当你运行了多次测试并希望将结果合并成一个综合报告时非常有用。

| 参数 | 意义 | 是否必需 |
| --- | --- | --- |
| -p, --paths | 需要合并的测试报告目录路径（res_* 目录），至少需要两个路径 | 是 |
| -o, --output | 合并报告的输出目录 | 否 |

**使用示例：**

```bash
# 合并两个测试报告目录
kea2 merge -p res_20240101_120000 res_20240102_130000

# 合并多个测试报告目录并指定输出目录
kea2 merge -p res_20240101_120000 res_20240102_130000 res_20240103_140000 -o my_merged_report
```

# 配置文件（Fastbot、黑白名单）

## Fastbot 配置文件

执行 `Kea2 init` 后，会在 `configs` 目录生成一些配置文件。  
这些配置文件属于 `Fastbot`，具体介绍请参见[配置文件介绍](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E4%B8%93%E5%AE%B6%E7%B3%BB%E7%BB%9F)。

## 黑白名单（黑白名单/控件/界面特定区域）

黑名单能力由两个维度定义：作用范围（控件级 / 树级）与规则类型（全局 / 条件）。

#### 1. 作用范围（屏蔽什么）
**控件级**：仅屏蔽单个控件。  
**树级**：屏蔽控件及其整棵子树（即一个 UI 区域）。

#### 2. 规则类型（何时屏蔽）
**全局**：在每个页面都生效。  
**条件**：仅在满足 `@precondition` 的页面生效。

### 控件/区域黑白名单 API

| 作用范围 \ 规则类型 | 全局（始终） | 条件（`@precondition`） |
|-|-|-|
| 控件级 | `global_block_widgets` | `@precondition → block_*` |
| 树级 | `global_block_tree` | `@precondition → block_tree_*` |

**示例见：** [:blue_book: widget.block.py](../kea2/assets/fastbot_configs/widget.block.py)

#### :white_check_mark: 黑名单支持的选择器

以下列出常用属性。更完整用法请参考 [uiautomator2 文档](https://github.com/openatx/uiautomator2/)：

<details>
  <summary>基础选择器</summary>

- **文本相关属性**  
  `text`, `textContains`, `textStartsWith`

- **类名相关属性**  
  `className`

- **描述相关属性**  
  `description`, `descriptionContains`, `descriptionStartsWith`

- **状态相关属性**  
  `checkable`, `checked`, `clickable`, `longClickable`, `scrollable`, `enabled`, `focusable`, `focused`, `selected`

- **包名相关属性**  
  `packageName`

- **资源 ID 相关属性**  
  `resourceId`

- **索引相关属性**  
  `index`
</details>

<details>
  <summary>子节点与兄弟节点选择器</summary>

- **定位子节点或孙节点**

  ```python
  d(className="android.widget.ListView").child(text="Wi-Fi")
  ```

- **定位兄弟节点**

  ```python
  d(text="Settings").sibling(className="android.widget.ImageView")
  ```
</details>

<details>
  <summary>基础 XPath 表达式</summary>

**基础写法**
```python
d.xpath('//*[@text="Private FM"]')
```

**以 @ 开头的简写**
```python
d.xpath('@personal-fm') # 等价于 d.xpath('//*[@resource-id="personal-fm"]').exists
```

**子元素定位**
```python
d.xpath('@android:id/list').child('/android.widget.TextView')
```
</details>

#### :no_entry_sign: 黑名单不支持的选择器

请避免使用以下方法，它们**不支持**用于黑名单配置：

<details>
  <summary>基于位置关系的查询</summary>

```python
d(A).left(B)    # 选择 A 左侧的 B
d(A).right(B)   # 选择 A 右侧的 B
d(A).up(B)      # 选择 A 上方的 B
d(A).down(B)    # 选择 A 下方的 B
```
</details>

<details>
  <summary>子查询选择器</summary>

`child_by_text`, `child_by_description`, `child_by_instance`.
```python
d(className="android.widget.ListView", resourceId="android:id/list") \
  .child_by_text("Bluetooth", className="android.widget.LinearLayout")

d(className="android.widget.ListView", resourceId="android:id/list") \
  .child_by_text(
    "Bluetooth",
    allow_scroll_search=True,  # 默认 False
    className="android.widget.LinearLayout"
  )
```
</details>

<details>
  <summary>instance</summary>

```python
d(className="android.widget.Button", instance=2)
```
</details>

<details>
  <summary>基于正则的查询</summary>

`textMatches`, `classNameMatches`, `descriptionMatches`, `packageNameMatches`, `resourceIdMatches`
</details>

<details>
  <summary>链式 XPath 选择器</summary>

父子关系链式 XPath：
```python
d.xpath('//android.widget.Button').xpath('//*[@text="Private FM"]')
```

```python
d.xpath('//*[@text="Private FM"]').parent() # 定位父元素
d.xpath('//*[@text="Private FM"]').parent("@android:list") # 定位满足条件的父元素
```

带逻辑运算符的 XPath：
```python
(d.xpath("NFC") & d.xpath("@android:id/item"))
```

```python
(d.xpath("NFC") | d.xpath("App") | d.xpath("Content"))
```
</details>

### Activity 黑白名单

我们继承了 Fastbot 的 Activity 黑白名单机制。使用方式如下：

1. 在 `configs/awl.strings` 中填写需要加入黑白名单的 Activity。
2. 运行 kea2 时添加对应参数（`--act-blacklist-file`、`--act-whitelist-file`）。

> `configs/awl.strings` 文件由 `Kea2 init` 生成。可参考[示例配置文件](/kea2/assets/fastbot_configs/abl.strings)。

### Activity 黑白名单参数

| 参数 | 含义 | 默认值 |
| --- | --- | --- |
| `--act-blacklist-file [path]` | 启用 Activity 黑名单。若省略 `path`，默认 `/sdcard/.kea2/abl.strings`。 | |
| `--act-whitelist-file [path]` | 启用 Activity 白名单。若省略 `path`，默认 `/sdcard/.kea2/awl.strings`。 | |

使用示例：
```
kea2 run -p it.feio.android.omninotes.alpha --act-blacklist-file propertytest discover -p quicktest.py

# 自定义黑名单文件路径
kea2 run -p it.feio.android.omninotes.alpha --act-blacklist-file /sdcard/custom_abl.strings propertytest discover -p quicktest.py
```

### Activity 黑白名单机制
- 白名单与黑名单**不能同时设置**。二选一：若设置白名单，则白名单外 Activity 视为黑名单。
- Fastbot 会监控 Activity 启动。当黑名单 Activity 即将启动时会被拦截，因此该阶段 UI 可能看起来“无响应”。

## 用户配置文件更新

升级 Kea2 时，用户本地配置有时需要更新（新版 kea2 可能与旧配置不兼容）。

当检测到运行时错误时，Kea2 会检查本地配置文件与当前版本是否兼容。若不兼容，会在控制台打印警告。请按下列步骤更新本地配置：

1. 备份本地配置文件（防止更新过程出现意外）。
2. 删除项目根目录下 `/configs` 中所有配置文件。
3. 运行 `kea2 init` 生成最新配置文件。
4. 按需将旧配置合并到新配置文件中。

# 高级功能

## 高级功能 1：带状态测试（Stateful Testing）

带状态测试是基于性质测试中的进阶方法。核心思想是建模应用内部数据状态，并在多个性质之间共享状态，以引导探索并发现更复杂缺陷。

Kea2 提供共享 `state` 对象用于带状态测试。它是一个单例 `dict`，可跨性质存储内部数据与建模状态。你可以在某个性质中更新 `state`，并在后续性质中读取，以控制探索流程。

例如，在增删改查场景中，可以记录当前数据项并在后续性质中复用。典型场景是“搜索条目”（必须先知道有哪些条目才能搜索）。

```python
from kea2 import state

state["item_names"] = []  # 存储数据条目

class MyStatefulTest(unittest.TestCase):
    @precondition(...)
    def test_add_item(self):
        # 添加数据条目
        new_item_name = __get_random_item_name()
        self.d(resourceId="add_button").click()
        self.d(resourceId="item_name_input").set_text(new_item_name)
        self.d(resourceId="save_button").click()
        # 更新 state 中条目
        state["item_names"].append(new_item_name)

    # 使用 state 中已有条目进行搜索
    @precondition(lambda self: len(state["item_names"]) > 0 and ...)
    def search_item(self):
        search_name = random.choice(state["item_names"])
        self.d(resourceId="search_box").set_text(search_name)
        self.d.press("enter")
        assert self.d(text=search_name).exists
```

> 若想了解更多带状态测试，请参考 [Hypothesis Stateful Testing 文档](https://hypothesis.readthedocs.io/en/latest/stateful.html)

## 高级功能 2：不变式检查（Invariant Checks）

不变式检查（`@invariant`）用于定义“始终应成立”的性质。普通性质包含前置条件 P、交互场景 I、断言 Q；而不变式可视为 P 恒真、I 为空，并在每个状态检查 Q。

Kea2 会在应用进入每个新状态时检查所有不变式（即每次执行性质或发送随机事件后）。

普通性质与不变式的差异可以概括为：

**普通性质：**

`total steps` > `precondition satified times` > `property check times` > `fails` + `errors`

**不变式：**

`total steps` = `invariant checks times` > `fails` + `errors`

```python
from kea2 import invariant

@invariant
def invariant_non_negative_word_count(self):
    if self.d(resourceId="word_count").exists:
        # 获取未背单词数量
        word_count_text = self.d(resourceId="word_count").get_text()
        word_count = int(word_count_text)
        assert word_count >= 0, f"Word count is negative: {word_count}"
```

`@invariant` 用于标记不变式检查。所有不变式会在每次性质执行或随机事件后运行一遍（每轮都检查）。不变式适合检查“始终为真”的条件，如单页布局一致性、或由带状态测试推导出的状态一致性。建议保证不变式执行快速且无副作用。

## 高级功能 3：复用回归脚本（兼容已有脚本：通过前置脚本步骤到达特定层次）

Kea2 支持复用已有 UI 测试脚本。核心思路是：*已有 UI 脚本通常覆盖关键功能并能到达深层状态，因此可作为“引导脚本”驱动 Fastbot 探索关键且更深层的状态。*

例如，你可能已有“登录并添加好友”脚本。该功能允许你在已有脚本中设置断点（可中断点），并在每个断点后启动 Fastbot 继续探索。这样可以先完成登录，再探索登录后状态，帮助 Fastbot 覆盖其难以自行到达的深层状态。

### 示例

`hybridtest_examples` 目录下有四个示例脚本，分别对应不同形式的用户脚本，展示如何在现有代码中启动 kea2：

* [u2_unittest_example.py](hybridtest_examples\u2_unittest_example.py) 是基于 unittest 组织的 u2 脚本。
* [u2_pytest_example.py](hybridtest_examples\u2_pytest_example.py) 是基于 pytest 组织的 u2 脚本。
* [appium_unittest_example.py](hybridtest_examples\appium_unittest_example.py) 是基于 unittest 组织的 appium 脚本。
* [appium_pytest_example.py](hybridtest_examples\appium_pytest_example.py) 是基于 pytest 组织的 appium 脚本。

注意事项：

1. 可通过修改 `if` 条件控制是否执行 kea2 相关代码，便于在同一脚本中启停 kea2 操作。这里以环境变量为例。
2. kea2 由 u2 驱动；若从 appium 脚本启动 kea2，需要先关闭 appium 会话，并在 `desired_caps` 中配置 `"noReset": True` 以避免关闭会话时重置应用。
3. 你需要将下方模板插入现有用例。可在注释位置加入你自己的 hook（如启停 appium 会话、清理实例等），其余只需配置 `option` 与 `configs_path`（`configs` 目录位置，取决于你执行 `kea2 init` 的目录），并传给 `run_kea2_testing`。

```python
from kea2 import Kea2Tester, Options

if os.environ.get('KEA2_HYBRID_MODE', '').lower() == 'true': 
    '''
    注意：这里的 if 条件可以按项目实际情况调整，
    使用环境变量仅作为示例。
    '''

    # 在此关闭驱动会话等
    # ...
    
    tester = Kea2Tester()
    result = self.tester.run_kea2_testing(
        Options(
            driverName="d",
            packageNames=[PACKAGE_NAME],
            propertytest_args=["discover", "-p", "Omninotes_Sample.py"],
            serial=DEVICE_SERIAL,
            running_mins=2,
            maxStep=20
        ),
        configs_path = None  # 默认值；若 configs 在根目录，可省略此参数。
    )
    
    # 在此重启驱动会话或清理实例
    # ...
    
    return  # 使该测试用例后续步骤不再执行
```

# 其他技巧与 FAQ

## FAQ
### Kea2 经常回到桌面或退出当前页面，为什么？
你可能正在使用手势导航。Fastbot 的滚动事件可能被系统识别为“返回手势”，导致页面退出。建议切换为三键导航以避免该问题。

更多信息见 [Kea2 issue #99](https://github.com/ecnusse/Kea2/issues/99)。

## 与第三方包交互
Kea2 默认会阻止探索过程中与第三方包（如广告包）的交互。如果你想允许交互，请在启动 Kea2 时的[额外参数](#---子命令-额外参数)里添加 `--allow-any-starts`。

例如：
```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10  --driver -- --allow-any-starts propertytest discover -p quicktest.py
```

## 提升 Kea2 性能的建议

目前，我们在 `@precondition` 装饰器和 `widgets.block.py` 中实现了一种性能优化算法。该算法只支持 uiautomator2 的基础选择器（不支持父子关系）。如果你有大量复杂前置条件且观察到性能问题，建议改用 xpath。

| | **推荐** | **不推荐** |
| -- | -- | -- |
| **选择器** | `d(text="1").exist` | `d(text="1").child(text="2").exist` |

如果必须在 `@precondition` 中表达父子关系，请使用 xpath。

例如：

```python
# 不推荐使用：
# @precondition(lambda self: 
#      self.d(className="android.widget.ListView").child(text="Bluetooth")
# ):
# ...

# 推荐使用：
@precondition(lambda self: 
    self.d.xpath('//android.widget.ListView/*[@text="Bluetooth"]')
):
...
```

## 调试模式（`kea2 -d ...`）

使用 Kea2 时加上 `-d` 选项即可开启调试模式。调试模式下会打印更详细日志，便于定位问题。

| 参数 | 含义 | 默认值 |
| --- | --- | --- |
| -d | 启用调试模式 | |

> ```bash
> # 加上 -d 启用调试模式
> kea2 -d run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10  unittest discover -p quicktest.py
> ```