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

Kea2 是一个易用的移动应用模糊测试工具。其关键*创新点*在于能够将自动化 UI 测试与脚本（通常由人工编写）融合，从而赋能自动化 UI 测试以人类智能，有效发现*崩溃错误*以及*非崩溃功能（逻辑）错误*。

Kea2 当前基于 [Fastbot](https://github.com/bytedance/Fastbot_Android)，*一个工业级自动化 UI 测试工具*，以及 [uiautomator2](https://github.com/openatx/uiautomator2)，*一个易用且稳定的 Android 自动化库*构建。
Kea2 目前面向 [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) 应用。

## 重要特性

<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>

- **特性 1**（查找稳定性问题）：具备 [Fastbot](https://github.com/bytedance/Fastbot_Android) 的全部能力，支持压力测试和发现*稳定性问题*（即*崩溃错误*）；

- **特性 2**（自定义测试场景\事件序列\黑白名单\黑白控件[^1]）：运行 Fastbot 时支持自定义测试场景（如测试特定应用功能、执行特定事件轨迹、进入特定 UI 页面、达到特定应用状态、黑名单特定 Activity/UI 控件/UI 区域），依托 *python* 语言和 [uiautomator2](https://github.com/openatx/uiautomator2) 提供的全能力和灵活性；

- **特性 3**（支持断言机制[^2]）：运行 Fastbot 时支持自动断言，基于继承自 [Kea](https://github.com/ecnusse/Kea) 的[基于性质的测试](https://en.wikipedia.org/wiki/Software_testing#Property_testing)思想，发现*逻辑错误*（即*非崩溃功能错误*）。

对于**特性 2 和 3**，Kea2 允许你专注于测试哪些应用功能，而无需考虑如何达到这些功能。结果是脚本通常简短、稳健且易维护，同时相应功能得到更多压力测试！

**Kea2 三大功能能力对比**

|  | **特性 1** | **特性 2** | **特性 3** |
| --- | --- | --- | ---- |
| **发现崩溃** | :+1: | :+1: | :+1: |
| **发现深层状态崩溃** |  | :+1: | :+1: |
| **发现非崩溃功能（逻辑）错误** |  |  | :+1: |



## 设计与规划
Kea2 作为 Python 库发布，目前可配合以下组件使用：
- [unittest](https://docs.python.org/3/library/unittest.html) 作为测试框架；
- [uiautomator2](https://github.com/openatx/uiautomator2) 作为 UI 测试驱动；
- [Fastbot](https://github.com/bytedance/Fastbot_Android) 作为后端自动化 UI 测试工具。

未来，Kea2 将拓展支持：
- [pytest](https://docs.pytest.org/en/stable/)
- [Appium](https://github.com/appium/appium)、[Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)（针对 HarmonyOS/Open Harmony）
- 其他自动化 UI 测试工具（不限于 Fastbot）


## 安装

运行环境：
- 支持 Windows、MacOS 和 Linux
- python 3.8+，Android 5.0+（需安装 Android SDK）
- **VPN 关闭**（特性 2 和 3 需要）

通过 `pip` 安装 Kea2：
```bash
python3 -m pip install kea2-python
```

通过运行命令查看 Kea2 选项：
```bash
kea2 -h
```

## 快速测试

Kea2 连接并运行于 Android 设备。建议您先做快速测试，确保 Kea2 与您的设备兼容。

1. 连接真实 Android 设备或 Android 模拟器（仅需一台设备），并运行`adb devices`确认设备已连接。

2. 运行 `quicktest.py` 测试示例应用 `omninotes`（在 Kea2 仓库发布为 `omninotes.apk`）。`quicktest.py` 脚本会自动安装并短时间测试该示例应用。

在您首选的工作目录下初始化 Kea2：
```python
kea2 init
```

> 如果您是第一次使用 Kea2，此步骤始终需要执行。

运行快速测试：
```python
python3 quicktest.py
```

若您看到应用 `omninotes` 成功运行并被测试，说明 Kea2 工作正常！
否则，请帮助[提交 Bug 报告](https://github.com/ecnusse/Kea2/issues)，附上错误信息。谢谢！



## 特性 1（运行基础版 Fastbot：查找稳定性错误）

使用 Fastbot 的全部能力测试您的应用，进行压力测试并发现*稳定性问题*（即*崩溃错误*）；

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

理解上述选项含义请查看[文档](docs/manual_en.md#launching-kea2)

> 用法与原始 Fastbot 的[shell 命令](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command)类似。

查看更多选项：
```bash
kea2 run -h
```

## 特性 2（运行增强版 Fastbot：自定义测试场景\事件序列\黑白控件）

运行 Fastbot 等自动化 UI 测试工具测试应用时，您可能发现某些特定 UI 页面或功能难以达到或覆盖，原因是 Fastbot 缺乏对您应用的认知。幸运的是，这正是脚本测试的长处。特性 2 中，Kea2 支持编写小脚本以引导 Fastbot 探索目标区域。您也可以用这些小脚本在 UI 测试时屏蔽特定控件。

在 Kea2 中，一个脚本由两部分组成：
-  **先决条件（Precondition）：** 何时执行脚本；
- **交互场景（Interaction scenario）：** 到达目标的交互逻辑（脚本测试方法中指定）。

### 简单示例

假设在自动化 UI 测试过程中，`Privacy` 是一个难以到达的 UI 页面。Kea2 可以轻松引导 Fastbot 到达该页面。

```python
    @prob(0.5)
    # precondition: 当我们处于页面 `Home`
    @precondition(lambda self: 
        self.d(text="Home").exists
    )
    def test_goToPrivacy(self):
        """
        引导 Fastbot 进入 `Privacy` 页面：
        打开 `Drawer`，点击选项 `Settings`，再点击 `Privacy`。
        """
        self.d(description="Drawer").click()
        self.d(text="Settings").click()
        self.d(text="Privacy").click()
```

- 通过装饰器 `@precondition` 指定先决条件——当我们处于 `Home` 页面时。
本例中，`Home` 页面是 `Privacy` 页面的入口，且 `Home` 页面可被 Fastbot 容易到达。
因此脚本将在检测到唯一控件 `Home` 存在时激活。
- 在脚本测试方法 `test_goToPrivacy` 中，指定交互逻辑（即打开 `Drawer`，点击 `Settings` 选项，再点击 `Privacy`）以引导 Fastbot 到达 `Privacy` 页面。
- 通过装饰器 `@prob` 指定概率（本例中为 50%）在处于 `Home` 页面时做该引导。由此 Kea2 保留 Fastbot 探索其他页面的可能。

您可以在脚本 `quicktest.py` 中找到完整示例，并通过命令 `kea2 run` 用 Fastbot 运行该脚本：

```bash
# 启动 Kea2 并加载单脚本 quicktest.py。
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## 特性 3（运行增强版 Fastbot：加入自动断言）

Kea2 支持运行 Fastbot 时的自动断言，以发现*逻辑错误*（即*非崩溃错误*）。为此，您可以在脚本中加入断言语句。当自动化 UI 测试期间断言失败，我们即发现了一个潜在的功能性错误。

特性 3 中，一个脚本由三部分组成：

- **先决条件（Precondition）：** 何时执行脚本；
- **交互场景（Interaction scenario）：** 交互逻辑（脚本测试方法中描述）；
- **断言（Assertion）：** 预期应用行为。

### 示例

在社交应用中，发送消息是常见功能。在消息发送页，当输入框非空时（即有内容），发送按钮应一直显示。

<div align="center">
    <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
</div>

<div align="center">
    预期行为（上图）与错误行为（下图）。
</div>
    

针对上述始终成立的性质，我们可以写如下脚本验证功能正确性：当消息发送页面有 `input_box` 控件时，向输入框输入任意非空字符串，并断言 `send_button` 应始终存在。

```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exist

        # 还能做更多断言，例如：
        #   输入的字符串应显示在消息发送页面
        assert self.d(text=random_str).exist
```
> 我们使用 [hypothesis](https://github.com/HypothesisWorks/hypothesis) 生成随机文本。

您可以使用类似特性 2 的命令行运行此示例。

## 文档（更多文档）

[更多文档](docs/manual_en.md)，包括：
- Kea2 案例教程（基于微信介绍）；
- Kea2 脚本定义方法，支持的脚本装饰器（如 `@precondition`、`@prob`、`@max_tries`）；
- Kea2 启动方式、命令行选项；
- 查看/理解 Kea2 运行结果（如界面截图、测试覆盖率、脚本执行状态）；
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

Kea2 由 [ecnusse](https://github.com/ecnusse) 团队持续积极开发和维护：

- [Xixian Liang](https://xixianliang.github.io/resume/) ([@XixianLiang][])
- Bo Ma ([@majuzi123][])
- Chen Peng ([@Drifterpc][])
- [Ting Su](https://tingsu.github.io/) ([@tingsu][])

[@XixianLiang]: https://github.com/XixianLiang
[@majuzi123]: https://github.com/majuzi123
[@Drifterpc]: https://github.com/Drifterpc
[@tingsu]: https://github.com/tingsu

[Zhendong Su](https://people.inf.ethz.ch/suz/), [Yiheng Xiong](https://xyiheng.github.io/), [Xiangchen Shen](https://xiangchenshen.github.io/), [Mengqian Xu](https://mengqianx.github.io/), [Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp), [Jingling Sun](https://jinglingsun.github.io/), [Jue Wang](https://cv.juewang.info/) 也积极参与并对该项目贡献良多！

Kea2 也收到大量来自多家工业公司的宝贵见解、建议、反馈及经验分享，如字节跳动（[Zhao Zhang](https://github.com/zhangzhao4444)，Fastbot 团队的 Yuhui Su）、OPay（Tiesong Liu）、微信（Haochuan Lu, Yuetang Deng）、华为、小米等。感谢大家！

[^1]: 不少 UI 自动化测试工具提供“自定义事件序列”能力（如[Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和[AppCrawler](https://github.com/seveniruby/AppCrawler)），但实际使用中存在不少问题，如自定义能力有限、使用不灵活等。许多 Fastbot 用户曾抱怨“自定义事件序列”功能使用不畅，参见[#209](https://github.com/bytedance/Fastbot_Android/issues/209)、[#225](https://github.com/bytedance/Fastbot_Android/issues/225)、[#286](https://github.com/bytedance/Fastbot_Android/issues/286)等。

[^2]: 在 UI 自动化测试中支持自动断言是一项重要能力，但几乎无测试工具提供此能力。我们注意到[AppCrawler](https://ceshiren.com/t/topic/15801/5) 的开发者曾希望提供断言机制，用户反响热烈，自 2021 年起已有不少催更，但至今未实现。