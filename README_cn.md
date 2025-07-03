[![PyPI](https://img.shields.io/pypi/v/kea2-python.svg)](https://pypi.python.org/pypi/kea2-python)
[![PyPI Downloads](https://static.pepy.tech/badge/kea2-python)](https://pepy.tech/projects/kea2-python)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)


<div>
    <img src="https://github.com/user-attachments/assets/d3de40a9-04a4-47ab-b14b-a1f8d08cb88b" style="border-radius: 14px; width: 20%; height: 20%;"/> 
</div>

### Github 仓库链接
[https://github.com/ecnusse/Kea2](https://github.com/ecnusse/Kea2)

### [点击此处：查看中文文档](README_cn.md)

## 关于

Kea2 是一个易用的手机应用模糊测试工具。其关键的*创新点*在于能够将自动化 UI 测试与脚本（通常由人工编写）结合起来，从而用人类智慧增强自动化 UI 测试，有效地发现*崩溃性错误*以及*非崩溃的功能性（逻辑）错误*。

Kea2 目前基于 [Fastbot](https://github.com/bytedance/Fastbot_Android)，*一款工业级自动化 UI 测试工具*，以及 [uiautomator2](https://github.com/openatx/uiautomator2)，*一款易用且稳定的 Android 自动化库*。
Kea2 目前面向 [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) 应用。

## 创新点与重要功能

<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>

- **功能 1**（查找稳定性问题）：支持 [Fastbot](https://github.com/bytedance/Fastbot_Android) 的全部功能用于压力测试和发现*稳定性问题*（即*崩溃错误*）；

- **功能 2**（自定义测试场景\事件序列\黑白名单\黑白控件[^1]）：运行 Fastbot 时，自定义测试场景（如测试特定应用功能、执行特定事件序列、进入特定 UI 页面、抵达特定应用状态、黑名单特定活动/UI 控件/UI 区域），通过 *python* 语言和 [uiautomator2](https://github.com/openatx/uiautomator2) 提供的强大能力灵活实现；

- **功能 3**（支持断言机制[^2]）：运行 Fastbot 时支持自动断言，基于从 [Kea](https://github.com/ecnusse/Kea) 继承的[基于性质的测试](https://en.wikipedia.org/wiki/Software_testing#Property_testing)理念，用于发现*逻辑错误*（即*非崩溃功能性错误*）。

  对于**功能 2 和 3**，Kea2 允许你专注于要测试的应用功能，不必担心如何到达这些功能。只需让 Fastbot 来实现。这样脚本通常简洁、健壮且易维护，相应的应用功能也得以更充分地压力测试！

**Kea2中三大功能的能力对比**

|  | **功能 1** | **功能 2** | **功能 3** |
| --- | --- | --- | ---- |
| **查找崩溃错误** | :+1: | :+1: | :+1: |
| **查找深层状态崩溃错误** |  | :+1: | :+1: |
| **查找非崩溃功能性（逻辑）错误** |  |  | :+1: |



## 设计与路线图
Kea2 目前配合使用：
- [unittest](https://docs.python.org/3/library/unittest.html) 作为测试框架管理脚本；
- [uiautomator2](https://github.com/openatx/uiautomator2) 作为 UI 测试驱动；
- [Fastbot](https://github.com/bytedance/Fastbot_Android) 作为后端自动化 UI 测试工具。

未来，Kea2 将扩展支持
- [pytest](https://docs.pytest.org/en/stable/)，另一个流行的 Python 测试框架；
- [Appium](https://github.com/appium/appium)、[Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)（支持 HarmonyOS/Open Harmony）；
- 以及其他任何自动化 UI 测试工具（不限于 Fastbot）。


## 安装

运行环境：
- 支持 Windows、MacOS 和 Linux
- python 3.8+，Android 5.0+（需安装 Android SDK）
- **关闭 VPN**（功能 2 和 3 需要）

通过 `pip` 安装 Kea2：
```bash
python3 -m pip install kea2-python
```

通过运行 
```bash
kea2 -h
```
查看 Kea2 的选项。

## 快速测试

Kea2 连接并运行于 Android 设备。我们建议你做一个快速测试，确保 Kea2 与你的设备兼容。

1. 连接一台真实 Android 设备或 Android 模拟器（仅需一台设备），并通过运行 `adb devices` 确认设备已连接。

2. 运行 `quicktest.py` 来测试一个示例应用 `omninotes`（在 Kea2 仓库中发布为 `omninotes.apk`）。脚本 `quicktest.py` 会自动安装并短暂测试该示例应用。

在你希望的工作目录下初始化 Kea2：
```python
kea2 init
```

> 如果是第一次运行 Kea2，此步骤必需。

运行快速测试：
```python
python3 quicktest.py
```

如果你看到应用 `omninotes` 成功运行并被测试，说明 Kea2 工作正常！
否则，请帮忙[提交 Bug 报告](https://github.com/ecnusse/Kea2/issues)并附上错误信息，谢谢！



## 功能 1（运行基础版 Fastbot：查找稳定性错误）

用 Fastbot 的全部能力对你的应用进行压力测试，发现*稳定性问题*（即*崩溃错误*）；

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

想了解选项的含义，可查看我们的[手册](docs/manual_en.md#launching-kea2)。

> 此用法类似 Fastbot 原生的[shell 命令](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command)。

更多选项请查看  
```bash
kea2 run -h
```

## 功能 2（运行增强版 Fastbot：自定义测试场景\事件序列\黑白控件）

当使用像 Fastbot 这类自动化 UI 测试工具测试你的应用时，你可能会发现某些特定的 UI 页面或功能难以到达或覆盖。这是因为 Fastbot 对你的应用缺乏认知。幸运的是，脚本测试正好弥补这点。在功能 2 中，Kea2 支持编写小脚本引导 Fastbot 探索我们想去的地方。你也可以用这类小脚本在 UI 测试时屏蔽特定控件。

在 Kea2 中，一个脚本由两个元素组成：
- **前置条件（Precondition）：** 何时执行脚本。
- **交互场景（Interaction scenario）：** 交互逻辑（写在脚本的测试方法里）引导到想去的地方。

### 简单示例

假设 `Privacy` 是一个在自动化 UI 测试时难以到达的页面。Kea2 可以轻松引导 Fastbot 到达这一页面。

```python
    @prob(0.5)
    # 前置条件：当我们处于页面 `Home`
    @precondition(lambda self: 
        self.d(text="Home").exists
    )
    def test_goToPrivacy(self):
        """
        通过打开 `Drawer`，点击选项 `Setting` 并点击 `Privacy`，
        引导 Fastbot 到达页面 `Privacy`。
        """
        self.d(description="Drawer").click()
        self.d(text="Settings").click()
        self.d(text="Privacy").click()
```

- 使用装饰器 `@precondition` 指定前置条件——当我们处于 `Home` 页面。这里，`Home` 页面是进入 `Privacy` 页面的入口页面，且 `Home` 页面可由 Fastbot 轻松到达。因此，脚本在检测到唯一控件 `Home` 存在时激活。
- 在脚本的测试方法 `test_goToPrivacy` 中，指定交互逻辑（即打开 `Drawer`，点击选项 `Setting` 并点击 `Privacy`）引导 Fastbot 到达 `Privacy` 页面。
- 使用装饰器 `@prob` 指定当处于 `Home` 页面时执行该引导的概率（本例为 50%）。因此，Kea2 仍允许 Fastbot 探索其他页面。

你可在脚本 `quicktest.py` 中找到完整示例，并通过命令 `kea2 run` 用 Fastbot 运行该脚本：

```bash
# 启动 Kea2 并加载单个脚本 quicktest.py。
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## 功能 3（运行增强版 Fastbot：加入自动断言）

Kea2 支持在运行 Fastbot 时自动断言，用于发现*逻辑错误*（即*非崩溃错误*）。为此，你可以在脚本中添加断言。当自动化 UI 测试中断言失败时，我们就发现了可能的功能性错误。

功能 3 中，脚本由三个元素组成：

- **前置条件（Precondition）：** 何时执行脚本。
- **交互场景（Interaction scenario）：** 交互逻辑（写在脚本的测试方法里）。
- **断言（Assertion）：** 期望的应用行为。

### 示例

在一款社交媒体应用中，发送消息是常见功能。在消息发送页面，当输入框非空时，`send` 按钮应始终出现。

<div align="center">
    <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
</div>

<div align="center">
    期望行为（上图）与错误行为（下图）。
</div>
    

针对上述始终成立的性质，我们可以写如下脚本验证功能正确性：当消息发送页面存在 `input_box` 控件时，输入任意非空字符串，并断言 `send_button` 应始终存在。

```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exist

        # 还可以做更多断言，例如：
        #       输入字符串应显示在消息发送页面上
        assert self.d(text=random_str).exist
```
> 这里我们用到 [hypothesis](https://github.com/HypothesisWorks/hypothesis) 来生成随机文本。

你可以用与功能 2 中类似的命令行运行此示例。

## 文档（更多文档）

你可以找到[用户手册](docs/manual_en.md)，包括：
- 使用 Kea2 测试微信的示例（中文）；
- 如何定义 Kea2 脚本及使用装饰器（如 `@precondition`、`@prob`、`@max_tries`）；
- 如何运行 Kea2 及其命令行参数；
- 如何查找并理解 Kea2 测试结果；
- 如何在模糊测试过程中[白名单或黑名单](docs/blacklisting.md)特定活动、UI 控件和 UI 区域。

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

Kea2 一直由 [ecnusse](https://github.com/ecnusse) 团队积极开发和维护：

- [Xixian Liang](https://xixianliang.github.io/resume/) ([@XixianLiang][])
- Bo Ma ([@majuzi123][])
- Chen Peng ([@Drifterpc][])
- [Ting Su](https://tingsu.github.io/) ([@tingsu][])

[@XixianLiang]: https://github.com/XixianLiang
[@majuzi123]: https://github.com/majuzi123
[@Drifterpc]: https://github.com/Drifterpc
[@tingsu]: https://github.com/tingsu

[Zhendong Su](https://people.inf.ethz.ch/suz/), [Yiheng Xiong](https://xyiheng.github.io/), [Xiangchen Shen](https://xiangchenshen.github.io/), [Mengqian Xu](https://mengqianx.github.io/), [Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp), [Jingling Sun](https://jinglingsun.github.io/), [Jue Wang](https://cv.juewang.info/) 也积极参与并为该项目做出了巨大贡献！

Kea2 也获得了来自多个工业人员的宝贵见解、建议、反馈和经验分享，他们分别来自字节跳动（[Zhao Zhang](https://github.com/zhangzhao4444)，Fastbot 团队的 Yuhui Su）、OPay（Tiesong Liu）、微信（Haochuan Lu、Yuetang Deng）、华为、小米等。致敬！

[^1]: 许多 UI 自动化测试工具支持“自定义事件序列”能力（如[Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和[AppCrawler](https://github.com/seveniruby/AppCrawler)），但实际使用中存在许多问题，如自定义能力有限、使用不灵活等。此前不少 Fastbot 用户抱怨“自定义事件序列”使用中的问题，如[#209](https://github.com/bytedance/Fastbot_Android/issues/209), [#225](https://github.com/bytedance/Fastbot_Android/issues/225), [#286](https://github.com/bytedance/Fastbot_Android/issues/286)等。

[^2]: 在 UI 自动化测试过程中支持自动断言是重要能力，但几乎没有测试工具提供此能力。我们注意到 [AppCrawler](https://ceshiren.com/t/topic/15801/5) 开发者曾希望提供断言机制，得到了用户热切响应，许多用户从2021年开始催促更新，但始终未能实现。