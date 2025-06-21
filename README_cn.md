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

Kea2 是一个易用的移动应用模糊测试工具。其主要*创新点*是能够将自动化 UI 测试与脚本（通常由人编写）融合，从而赋能自动化 UI 测试以人类智慧，有效发现*崩溃错误*以及*非崩溃的功能性（逻辑）错误*。

Kea2 目前基于 [Fastbot](https://github.com/bytedance/Fastbot_Android)，*一个工业级自动化 UI 测试工具*，以及 [uiautomator2](https://github.com/openatx/uiautomator2)，*一款易用且稳定的 Android 自动化库*。
Kea2 当前面向 [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) 应用。

## 创新与重要特性

<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>

- **特性 1**（查找稳定性问题）：具备 [Fastbot](https://github.com/bytedance/Fastbot_Android) 的全部能力，用于压力测试和发现*稳定性问题*（即*崩溃错误*）；

- **特性 2**（自定义测试场景\事件序列\黑白名单\黑白控件[^1]）：在运行 Fastbot 时自定义测试场景，如测试特定应用功能、执行指定事件序列、进入指定 UI 页面、达到指定应用状态、黑名单特定 Activity/UI 控件/UI 区域，借助 *python* 语言和 [uiautomator2](https://github.com/openatx/uiautomator2) 提供的全面灵活能力；

- **特性 3**（支持断言机制[^2]）：基于继承自 [Kea](https://github.com/ecnusse/Kea) 的[基于性质的测试](https://en.wikipedia.org/wiki/Software_testing#Property_testing)思想，支持在运行 Fastbot 过程中自动断言，用于定位*逻辑错误*（即*非崩溃功能性错误*）。

对于 **特性 2 和 3**，Kea2 允许你专注于想测试的应用功能，无需担心如何达到这些功能，只需让 Fastbot 帮助完成。这样，脚本通常简短、健壮且易维护，对应功能也能得到更强的压力测试！

**Kea2 三个特性的能力表现**

|  | **特性 1** | **特性 2** | **特性 3** |
| --- | --- | --- | ---- |
| **发现崩溃** | :+1: | :+1: | :+1: |
| **发现在深层状态的崩溃** |  | :+1: | :+1: |
| **发现非崩溃的功能性（逻辑）错误** |  |  | :+1: |



## 设计与发展路线
Kea2 目前集成：
- 以 [unittest](https://docs.python.org/3/library/unittest.html) 作为测试框架管理脚本；
- 以 [uiautomator2](https://github.com/openatx/uiautomator2) 作为 UI 测试驱动；
- 以 [Fastbot](https://github.com/bytedance/Fastbot_Android) 作为后端自动化 UI 测试工具。

未来，Kea2 将支持
- [pytest](https://docs.pytest.org/en/stable/)，另一个流行的 python 测试框架；
- [Appium](https://github.com/appium/appium)、[Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)（面向 HarmonyOS/Open Harmony）；
- 以及其他任何自动化 UI 测试工具（不限于 Fastbot）


## 安装

运行环境：
- 支持 Windows、MacOS 和 Linux
- python 3.8+，Android 5.0+（已安装 Android SDK）
- **关闭 VPN**（特性 2 和 3 需要）

通过 `pip` 安装 Kea2：
```bash
python3 -m pip install kea2-python
```

查看 Kea2 的选项：
```bash
kea2 -h
```

## 快速测试

Kea2 将连接并运行于 Android 设备。建议你先进行快速测试，确保 Kea2 兼容你的设备。

1. 连接一台真实 Android 设备或 Android 模拟器（只需一个设备），运行 `adb devices` 确认设备已连接。

2. 运行 `quicktest.py`，测试示例应用 `omninotes`（在 Kea2 仓库中以 `omninotes.apk` 形式发布）。`quicktest.py` 会自动安装并短时间测试该示例应用。

在你选择的工作目录下初始化 Kea2：
```python
kea2 init
```

> 如果是首次使用 Kea2，此步骤必不可少。

运行快速测试：
```python
python3 quicktest.py
```

如果你看到 `omninotes` 应用成功运行和被测试，说明 Kea2 可用！
如果未成功，请帮助我们[提交 bug 报告](https://github.com/ecnusse/Kea2/issues)并附上错误信息。感谢！

## 特性 1（运行基础版 Fastbot：查找稳定性错误）

使用 Fastbot 全能力测试应用，进行压力测试查找*稳定性问题*（即*崩溃错误*）；

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

关于参数含义，可查看[手册](docs/manual_en.md#launching-kea2)。

> 用法与 Fastbot 原生的[shell 命令](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command)类似。

查看更多选项：
```bash
kea2 run -h
```

## 特性 2（运行增强版 Fastbot：自定义测试场景\事件序列\黑白控件）

在使用 Fastbot 等自动化 UI 测试工具测试应用时，你可能发现某些特定 UI 页面或功能较难到达或覆盖。原因在于 Fastbot 对应用缺少知识。脚本测试的优势恰恰在此。特性 2 中，Kea2 支持编写小脚本来引导 Fastbot 探索任意目标，也可用小脚本阻止特定控件在测试时被操作。

在 Kea2 中，脚本由两个部分组成：
- **前置条件（Precondition）**：何时执行脚本。
- **交互场景**：具体的交互逻辑（在脚本的测试方法中指定），达到指定目标。

### 简单示例

假设 `Privacy` 是自动化测试中难以达到的 UI 页面。Kea2 可轻松引导 Fastbot 到达该页面。

```python
    @prob(0.5)
    # 前置条件：当处于 `Home` 页面时
    @precondition(lambda self: 
        self.d(text="Home").exists
    )
    def test_goToPrivacy(self):
        """
        引导 Fastbot 到 `Privacy` 页面，通过打开 `Drawer`，点击 `Settings` 选项，点击 `Privacy`。
        """
        self.d(description="Drawer").click()
        self.d(text="Settings").click()
        self.d(text="Privacy").click()
```

- 通过装饰器 `@precondition`，指定前置条件——当处于 `Home` 页面时执行。此处，`Home` 页面是 `Privacy` 页的入口页且可由 Fastbot 轻松到达。脚本激活时，会检测是否存在唯一控件 `Home`。
- 脚本测试方法 `test_goToPrivacy` 中指定交互逻辑（打开 `Drawer`，点击 `Settings`，点击 `Privacy`）引导 Fastbot 达到 `Privacy` 页面。
- 通过装饰器 `@prob` 指定执行概率（此例为 50%），使 Fastbot 除了偶尔执行该引导，也可继续探索其他页面。

完整示例见脚本 `quicktest.py`，可用命令 `kea2 run` 运行：

```bash
# 启动 Kea2 并加载单个脚本 quicktest.py。
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## 特性 3（运行增强版 Fastbot：加入自动断言）

Kea2 支持在运行 Fastbot 时自动断言，定位*逻辑错误*（即*非崩溃错误*）。你可以在脚本中加入断言，断言失败即可能定位到功能缺陷。

特性 3 中，脚本由三个部分组成：

- **前置条件（Precondition）**：何时执行脚本。
- **交互场景**：具体的交互逻辑（脚本测试方法中指定）。
- **断言**：期望的应用行为。

### 示例

在社交媒体应用中，发送消息为常见功能。发送页面中，当输入框非空（即有消息）时，`send` 按钮应始终出现。

<div align="center">
    <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
</div>

<div align="center">
    期望行为（上）与有缺陷行为（下）。
</div>
    

针对上述始终满足的性质，我们编写脚本验证功能正确性：当消息发送页面存在 `input_box` 控件时，输入任意非空字符串，断言 `send_button` 应始终存在。

```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exists

        # 我们甚至可以做更多断言，例如：
        # 输入的字符串应该在消息发送页面出现
        assert self.d(text=random_str).exists
```
> 我们使用 [hypothesis](https://github.com/HypothesisWorks/hypothesis) 生成随机文本。

你可以用与特性 2 类似的命令行运行此示例。

## 文档（更多文档）

你可以查阅 [用户手册](docs/manual_en.md)，包括：
- 在微信上的 Kea2 使用示例（中文）；
- 如何定义 Kea2 脚本及使用装饰器（如 `@precondition`、`@prob`、`@max_tries`）；
- 如何运行 Kea2 及命令行选项；
- 如何查找和理解 Kea2 测试结果；
- 如何在模糊测试时[白名单与黑名单管理]((docs/blacklisting.md))特定活动、UI 控件及 UI 区域。

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

[Zhendong Su](https://people.inf.ethz.ch/suz/), [Yiheng Xiong](https://xyiheng.github.io/), [Xiangchen Shen](https://xiangchenshen.github.io/), [Mengqian Xu](https://mengqianx.github.io/), [Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp), [Jingling Sun](https://jinglingsun.github.io/), [Jue Wang](https://cv.juewang.info/) 也积极参与并贡献巨大！

此外，Kea2 还获得了多位工业界专家宝贵的见解、建议、反馈和经验分享，来自字节跳动（[Zhao Zhang](https://github.com/zhangzhao4444) ，Fastbot 团队的 Yuhui Su）、OPay（Tiesong Liu）、微信（Haochuan Lu，Yuetang Deng）、华为、小米等。衷心感谢！

[^1]: 许多 UI 自动化测试工具提供“自定义事件序列”能力（如 [Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和 [AppCrawler](https://github.com/seveniruby/AppCrawler)），但实际使用中存在诸多问题，如自定义能力有限、使用不灵活等。此前，许多 Fastbot 用户抱怨“自定义事件序列”使用问题，如[#209](https://github.com/bytedance/Fastbot_Android/issues/209), [#225](https://github.com/bytedance/Fastbot_Android/issues/225), [#286](https://github.com/bytedance/Fastbot_Android/issues/286)等。

[^2]: UI 自动化测试过程中支持自动断言是一项很重要的能力，但几乎无测试工具提供此功能。我们注意到 [AppCrawler](https://ceshiren.com/t/topic/15801/5) 开发者曾计划提供断言机制，获得用户热烈响应，众多用户自 2021 年起不断催促，但始终未能实现。