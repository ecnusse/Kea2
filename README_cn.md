[![PyPI](https://img.shields.io/pypi/v/kea2-python.svg)](https://pypi.python.org/pypi/kea2-python)
[![PyPI Downloads](https://static.pepy.tech/badge/kea2-python)](https://pepy.tech/projects/kea2-python)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)

<div>
    <img src="https://github.com/user-attachments/assets/aa5839fc-4542-46f6-918b-c9f891356c84" style="border-radius: 14px; width: 20%; height: 20%;"/> 
</div>

### Github 仓库链接
[https://github.com/ecnusse/Kea2](https://github.com/ecnusse/Kea2)

### [点击此处：查看中文文档](README_cn.md)

## 关于

Kea2 是一个易用的 Python 库，支持、自定义和提升移动应用自动化 UI 测试。Kea2 的新颖之处在于能够融合脚本（通常由人工编写）与自动化 UI 测试工具，从而实现许多有趣且强大的功能。

Kea2 当前基于 [Fastbot](https://github.com/bytedance/Fastbot_Android) 和 [uiautomator2](https://github.com/openatx/uiautomator2) 构建，目标为 [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) 应用。

## 主要特性
- **特性 1**(查找稳定性问题)：具备 [Fastbot](https://github.com/bytedance/Fastbot_Android) 完整能力，进行压力测试和查找*稳定性问题*（即*崩溃类 bug*）；

- **特性 2**(自定义测试场景\事件序列\黑白名单\黑白控件[^1])：在运行 Fastbot 时自定义测试场景（如测试特定应用功能、执行特定事件序列、进入特定 UI 页面、达到特定应用状态、黑名单特定活动/UI 控件/UI 区域），精细化和灵活度由 *python* 语言和 [uiautomator2](https://github.com/openatx/uiautomator2) 全面支持；

- **特性 3**(支持断言机制[^2])：支持在运行 Fastbot 时自动断言，基于从 [Kea](https://github.com/ecnusse/Kea) 继承的[基于性质的测试](https://en.wikipedia.org/wiki/Software_testing#Property_testing)思想，用于发现*逻辑错误*（即*非崩溃类 bug*）。

**Kea2 中三大特性的能力对比**

|  | **特性 1** | **特性 2** | **特性 3** |
| --- | --- | --- | ---- |
| **发现崩溃** | :+1: | :+1: | :+1: |
| **在深层状态下发现崩溃** |  | :+1: | :+1: |
| **发现非崩溃功能（逻辑）错误** |  |  | :+1: |

<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>

## 设计与规划
作为 Python 库发布的 Kea2，当前工作链路：
- 使用 [unittest](https://docs.python.org/3/library/unittest.html) 作为测试框架；
- 使用 [uiautomator2](https://github.com/openatx/uiautomator2) 作为 UI 测试驱动；
- 使用 [Fastbot](https://github.com/bytedance/Fastbot_Android) 作为后端自动化 UI 测试工具。

后续计划扩展支持：
- [pytest](https://docs.pytest.org/en/stable/)
- [Appium](https://github.com/appium/appium)、[Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)（适用于 HarmonyOS/Open Harmony）
- 其他自动化 UI 测试工具（不限于 Fastbot）

## 安装

运行环境：
- 支持 Windows、MacOS 和 Linux
- python 3.8+，Android 5.0+（已安装 Android SDK）
- **关闭 VPN**（特性 2 和 3 需要）

使用 `pip` 安装 Kea2：
```bash
python3 -m pip install kea2-python
```

通过运行以下命令查看 Kea2 的参数选项：
```bash
kea2 -h
```

## 快速测试

Kea2 连接并运行于 Android 设备。建议先做快速测试，可确认 Kea2 与您设备兼容。

1. 连接真实 Android 设备或 Android 模拟器（只需一个设备），并通过 `adb devices` 确认设备已连接。

2. 运行 `quicktest.py` 来测试样例应用 `omninotes`（在 Kea2 仓库内发布为 `omninotes.apk`）。该脚本会自动安装并短时间测试此示例应用。

在首选工作目录下初始化 Kea2：
```python
kea2 init
```

> 第一次运行 Kea2 时必须执行该步骤。

运行快速测试：
```python
python3 quicktest.py
```

如果看到应用 `omninotes` 成功运行且被测试，则说明 Kea2 工作正常！
否则，请协助[提交 Bug 报告](https://github.com/ecnusse/Kea2/issues) 并附上错误信息。感谢！

## 特性 1（运行基础版 Fastbot：查找稳定性错误）

利用 Fastbot 完整能力测试应用，进行压力测试并查找*稳定性问题*（即*崩溃类 bug*）；

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

理解上述选项请参考[文档](docs/manual_en.md#launching-kea2)

> 用法类似原始 Fastbot 的[shell 命令](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command)。

查看更多选项可运行：
```bash
kea2 run -h
```

## 特性 2（运行增强版 Fastbot：自定义测试场景\事件序列\黑白控件）

当运行 Fastbot 等自动化 UI 测试工具测试应用时，可能发现某些特定 UI 页面或功能难以触达覆盖，原因是 Fastbot 缺乏对应用的知识。幸运的是，脚本测试正好具备该优势。特性 2 中，Kea2 支持编写小脚本，引导 Fastbot 探索任意目标，也能用小脚本屏蔽特定控件。

在 Kea2 中，脚本由两个要素组成：
-  **前置条件：** 何时执行脚本。
- **交互场景：** 脚本测试方法中指定的交互逻辑，达成目标位置。

### 简单示例

假设 `Privacy` 页面在自动化 UI 测试中难以达成。Kea2 可以轻松引导 Fastbot 到达该页面。

```python
    @prob(0.5)
    # 前置条件：当我们位于 `Home` 页面
    @precondition(lambda self: 
        self.d(text="Home").exists
    )
    def test_goToPrivacy(self):
        """
        通过打开 `Drawer`，点击 `Settings` 选项，再点击 `Privacy`，
        引导 Fastbot 到达 `Privacy` 页面。
        """
        self.d(description="Drawer").click()
        self.d(text="Settings").click()
        self.d(text="Privacy").click()
```

- 通过装饰器 `@precondition` 指定前置条件——只有当位于 `Home` 页面时执行。此处 `Home` 是 `Privacy` 页的入口，且 Fastbot 容易到达 `Home`，脚本会通过检测唯一控件 `Home` 是否存在，判断是否触发；
- 脚本测试方法 `test_goToPrivacy` 中指定交互逻辑（即打开 `Drawer`，点击 `Settings`，再点击 `Privacy`）引导 Fastbot 到达目标页面 `Privacy`；
- 通过装饰器 `@prob` 指定指导行为的概率（此处是 50%）。因此，Kea2 允许 Fastbot 仍然探索其他页面。

完整示例见脚本 `quicktest.py`，通过命令 `kea2 run` 使用 Fastbot 执行：

```bash
# 启动 Kea2 并加载单个脚本 quicktest.py。
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## 特性 3（运行增强版 Fastbot：加入自动断言）

Kea2 支持在运行 Fastbot 时进行自动断言，用于发现*逻辑错误*（即*非崩溃类 bug*）。实现方式是在脚本中添加断言。断言失败时，意味着可能发现功能性缺陷。

特性 3 中，脚本包含三个要素：

- **前置条件：** 何时执行脚本；
- **交互场景：** 脚本测试方法中指定的交互逻辑；
- **断言：** 期望的应用行为。

### 示例

在社交媒体应用中，消息发送是常见功能。消息发送页面当输入框不空时，`send` 按钮应始终显示。

<div align="center">
    <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
</div>
<div align="center">
    期望行为（上图）与有缺陷行为（下图）。
</div>

对于上述恒成立性质，可编写如下脚本进行功能正确性校验：当消息发送页面存在 `input_box` 控件时，我们输入任意非空字符串，并断言 `send_button` 始终存在。

```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exist

        # 还可做更多断言，比如：
        #       输入字符串应显示在消息发送页面上
        assert self.d(text=random_str).exist
```
> 我们使用 [hypothesis](https://github.com/HypothesisWorks/hypothesis) 生成随机文本。

此示例可用与特性 2 类似命令行运行。

## 文档（更多文档）

[更多文档](docs/manual_en.md)，涵盖：
- Kea2 案例教程（基于微信介绍）；
- Kea2 脚本定义方式，支持的脚本装饰器（如 `@precondition`、`@prob`、`@max_tries`）；
- Kea2 启动方式、命令行选项；
- 查看/理解 Kea2 运行结果（如界面截图、测试覆盖率、脚本执行成功情况）；
- [如何黑白控件/区域](docs/blacklisting.md)

## Kea2 使用的开源项目

- [Fastbot](https://github.com/bytedance/Fastbot_Android)
- [uiautomator2](https://github.com/openatx/uiautomator2)
- [hypothesis](https://github.com/HypothesisWorks/hypothesis)

## Kea2 相关论文

> General and Practical Property-based Testing for Android Apps. ASE 2024. [pdf](https://dl.acm.org/doi/10.1145/3691620.3694986)

> An Empirical Study of Functional Bugs in Android Apps. ISSTA 2023. [pdf](https://dl.acm.org/doi/10.1145/3597926.3598138)

> Fastbot2: Reusable Automated Model-based GUI Testing for Android Enhanced by Reinforcement Learning. ASE 2022. [pdf](https://dl.acm.org/doi/10.1145/3551349.3559505)

> Guided, Stochastic Model-Based GUI Testing of Android Apps. ESEC/FSE 2017.  [pdf](https://dl.acm.org/doi/10.1145/3106237.3106298)

### 维护者/贡献者

Kea2 由 [ecnusse](https://github.com/ecnusse) 团队积极开发和维护：

- [Xixian Liang](https://xixianliang.github.io/resume/) ([@XixianLiang][])
- Bo Ma ([@majuzi123][])
- Chen Peng ([@Drifterpc][])
- [Ting Su](https://tingsu.github.io/) ([@tingsu][])

[@XixianLiang]: https://github.com/XixianLiang
[@majuzi123]: https://github.com/majuzi123
[@Drifterpc]: https://github.com/Drifterpc
[@tingsu]: https://github.com/tingsu

[Zhendong Su](https://people.inf.ethz.ch/suz/)、[Yiheng Xiong](https://xyiheng.github.io/)、[Xiangchen Shen](https://xiangchenshen.github.io/)、[Mengqian Xu](https://mengqianx.github.io/)、[Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp)、[Jingling Sun](https://jinglingsun.github.io/)、[Jue Wang](https://cv.juewang.info/) 也积极参与该项目并贡献良多！

此外，Kea2 得到多位业界人士宝贵见解、建议和反馈支持，包括 Bytedance（[Zhao Zhang](https://github.com/zhangzhao4444)、Fastbot 团队的 Yuhui Su）、OPay（Tiesong Liu）、微信（Haochuan Lu、Yuetang Deng）、华为、小米等。致敬！

[^1]: 多数 UI 自动化测试工具支持“自定义事件序列”能力（如[Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和[AppCrawler](https://github.com/seveniruby/AppCrawler)），但实际使用时存在不少问题，如自定义能力有限、灵活性差等。不少 Fastbot 用户之前曾抱怨“自定义事件序列”使用中问题，如[#209](https://github.com/bytedance/Fastbot_Android/issues/209), [#225](https://github.com/bytedance/Fastbot_Android/issues/225), [#286](https://github.com/bytedance/Fastbot_Android/issues/286) 等。

[^2]: UI 自动化测试中支持自动断言是重要能力，但几乎无测试工具提供。注意到[AppCrawler](https://ceshiren.com/t/topic/15801/5) 开发者曾欲提供断言机制，用户热切响应，自 2021 年起多次催促，但始终未实现。