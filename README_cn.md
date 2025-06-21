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

Kea2 是一个易于使用的移动应用模糊测试工具。它的关键*创新点*是在自动化UI测试与脚本（通常由人工编写）之间实现融合，从而赋能自动化UI测试的人类智能，以有效地发现*崩溃类缺陷*及*非崩溃功能（逻辑）缺陷*。

Kea2 目前构建于 [Fastbot](https://github.com/bytedance/Fastbot_Android) 之上，*一个工业级的自动化UI测试工具*，以及 [uiautomator2](https://github.com/openatx/uiautomator2)，*一个易用且稳定的Android自动化库*。
Kea2 当前面向 [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) 应用。

## 主要特性

<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>

- **特性1**（查找稳定性问题）：具有 [Fastbot](https://github.com/bytedance/Fastbot_Android) 的全部能力，用于压力测试和发现*稳定性问题*（即*崩溃缺陷*）；

- **特性2**（自定义测试场景\事件序列\黑白名单\黑白控件[^1]）：在运行Fastbot时可以自定义测试场景（例如测试特定的应用功能、执行特定的事件序列、进入特定UI页面、达到特定应用状态、屏蔽特定活动/UI控件/UI区域），通过*python*语言和 [uiautomator2](https://github.com/openatx/uiautomator2) 提供的完整能力和灵活性；

- **特性3**（支持断言机制[^2]）：支持在运行Fastbot时自动断言，基于继承自 [Kea](https://github.com/ecnusse/Kea) 的 [基于性质的测试](https://en.wikipedia.org/wiki/Software_testing#Property_testing) 思想，用于查找*逻辑缺陷*（即*非崩溃功能缺陷*）。

对于 **特性2和3**，Kea2 允许你专注于要测试的应用功能，而无需担心如何到达这些功能页面。让Fastbot帮你完成。结果是你的脚本通常简短、健壮且易维护，对应的应用功能也进行了更充分的压力测试！

**Kea2 三个特性的能力对比**

|  | **特性1** | **特性2** | **特性3** |
| --- | --- | --- | ---- |
| **发现崩溃** | :+1: | :+1: | :+1: |
| **在深层状态发现崩溃** |  | :+1: | :+1: |
| **发现非崩溃功能（逻辑）缺陷** |  |  | :+1: |



## 设计与规划
Kea2 当前采用：
- [unittest](https://docs.python.org/3/library/unittest.html) 作为脚本管理的测试框架；
- [uiautomator2](https://github.com/openatx/uiautomator2) 作为UI测试驱动；
- [Fastbot](https://github.com/bytedance/Fastbot_Android) 作为后台自动化UI测试工具。

未来，Kea2 将扩展以支持
- [pytest](https://docs.pytest.org/en/stable/)，另一流行的python测试框架；
- [Appium](https://github.com/appium/appium)、[Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)（适用于HarmonyOS/Open Harmony）；
- 任何其他自动化UI测试工具（不限于Fastbot）


## 安装

运行环境：
- 支持Windows、MacOS和Linux
- python 3.8+，Android 5.0+（已安装Android SDK）
- **关闭VPN**（特性2和3要求）

使用 `pip` 安装Kea2：
```bash
python3 -m pip install kea2-python
```

查看Kea2的选项：
```bash
kea2 -h
```

## 快速测试

Kea2 连接并运行于Android设备上。建议做快速测试以确保Kea2与你的设备兼容。

1. 连接真实Android设备或Android模拟器（只需一台设备），并通过运行 `adb devices` 确认设备已连接。

2. 运行 `quicktest.py` 测试示例应用 `omninotes`（此应用以 `omninotes.apk` 发布于Kea2仓库）。脚本 `quicktest.py` 会自动安装并短时测试此示例应用。

在你希望的工作目录下初始化Kea2：
```python
kea2 init
```

> 如果是第一次运行Kea2，此步骤必需。

运行快速测试：
```python
python3 quicktest.py
```

若能看到应用 `omninotes` 成功运行并被测试，表示Kea2可以正常工作！
若不能，请帮助[提交问题报告](https://github.com/ecnusse/Kea2/issues)，附带错误信息。谢谢！



## 特性1（运行基础版Fastbot：查找稳定性错误）

用Fastbot的全部能力对应用进行压力测试，发现*稳定性问题*（即*崩溃缺陷*）；

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

理解上述选项含义请查看[文档](docs/manual_en.md#launching-kea2)

> 该用法类似于原始Fastbot的[shell命令](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command)。

查看更多选项：
```bash
kea2 run -h
```

## 特性2（运行增强版Fastbot：自定义测试场景\事件序列\黑白控件）

当使用Fastbot等自动化UI测试工具测试应用时，可能会发现某些特定UI页面或功能难以触达或覆盖。原因是Fastbot对你的应用缺乏了解。幸运的是，脚本测试擅长此类问题。在特性2中，Kea2 支持编写小脚本引导Fastbot探索指定位置。同时，你也可以用小脚本屏蔽特定控件。

在Kea2中，一个脚本由两部分组成：
- **前置条件**：何时执行该脚本。
- **交互场景**：脚本测试方法中指定的交互逻辑，用以到达目标。

### 简单示例

假设 `Privacy` 页面在自动化测试中难以触达。Kea2 可以轻松引导Fastbot到达该页面。

```python
    @prob(0.5)
    # precondition: 当位于 `Home` 页面时
    @precondition(lambda self: 
        self.d(text="Home").exists
    )
    def test_goToPrivacy(self):
        """
        通过打开 `Drawer`，
        点击选项 `Setting`，再点击 `Privacy`，
        引导Fastbot进入 `Privacy` 页面。
        """
        self.d(description="Drawer").click()
        self.d(text="Settings").click()
        self.d(text="Privacy").click()
```

- 通过装饰器 `@precondition` 指定前置条件——“当我们处于 `Home` 页面时”。
此时，`Home` 页面是 `Privacy` 页面的入口，且Fastbot易于到达 `Home` 页面。脚本激活的条件即检查唯一控件 `Home` 是否存在。
- 在脚本的测试方法 `test_goToPrivacy` 中，指定交互逻辑（打开 `Drawer`，点击 `Setting`，点击 `Privacy`）引导Fastbot到达 `Privacy` 页。
- 通过装饰器 `@prob` 指定在处于 `Home` 页面时执行此指引的概率（此示例为50%）。因此，Kea2 仍允许Fastbot探索其他页面。

完整示例请见脚本 `quicktest.py`，并通过命令 `kea2 run` 使用Fastbot运行此脚本：

```bash
# 启动Kea2并加载单脚本 quicktest.py。
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## 特性3（运行增强版Fastbot：加入自动断言）

Kea2 支持在运行Fastbot时自动断言，发现*逻辑缺陷*（即*非崩溃错误*）。为达到此目的，你可以在脚本中添加断言。断言失败时即发现可能的功能性缺陷。

在特性3中，一个脚本包含三个元素：

- **前置条件**：何时执行脚本。
- **交互场景**：脚本测试方法中指定的交互逻辑。
- **断言**：期望的应用行为。

### 示例

在社交应用中，消息发送是常见功能。在消息发送页面，当输入框非空时，`send` 按钮应始终出现。

<div align="center">
    <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
</div>

<div align="center">
    期望行为（上图）与缺陷表现（下图）。
</div>
    

针对上述永远成立的性质，我们可以写如下脚本验证功能正确性：当消息发送页中存在 `input_box` 控件时，向输入框输入任意非空字符串，并断言 `send_button` 应始终存在。


```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exist

        # 我们还可以做更多断言，如：
        # 输入字符串应该在消息发送页面中存在
        assert self.d(text=random_str).exist
```
> 我们使用 [hypothesis](https://github.com/HypothesisWorks/hypothesis) 生成随机文本。

此示例可通过特性2中类似的命令行运行。

## 文档（更多文档）

[更多文档](docs/manual_en.md)，包含：
- Kea2的案例教程（基于微信介绍）、
- Kea2脚本定义方法，支持的脚本装饰器（如`@precondition`、`@prob`、`@max_tries`）、
- Kea2的启动方式、命令行选项
- 查看/理解Kea2运行结果（如界面截图、测试覆盖率、脚本执行成功与否）
- [如何黑白控件/区域](docs/blacklisting.md)

## Kea2使用的开源项目

- [Fastbot](https://github.com/bytedance/Fastbot_Android)
- [uiautomator2](https://github.com/openatx/uiautomator2)
- [hypothesis](https://github.com/HypothesisWorks/hypothesis)

## Kea2相关论文

> General and Practical Property-based Testing for Android Apps. ASE 2024. [pdf](https://dl.acm.org/doi/10.1145/3691620.3694986)

> An Empirical Study of Functional Bugs in Android Apps. ISSTA 2023. [pdf](https://dl.acm.org/doi/10.1145/3597926.3598138)

> Fastbot2: Reusable Automated Model-based GUI Testing for Android Enhanced by Reinforcement Learning. ASE 2022. [pdf](https://dl.acm.org/doi/10.1145/3551349.3559505)

> Guided, Stochastic Model-Based GUI Testing of Android Apps. ESEC/FSE 2017.  [pdf](https://dl.acm.org/doi/10.1145/3106237.3106298)

### 维护者/贡献者

Kea2 由 [ecnusse](https://github.com/ecnusse) 团队积极开发维护：

- [Xixian Liang](https://xixianliang.github.io/resume/) ([@XixianLiang][])
- Bo Ma ([@majuzi123][])
- Chen Peng ([@Drifterpc][])
- [Ting Su](https://tingsu.github.io/) ([@tingsu][])

[@XixianLiang]: https://github.com/XixianLiang
[@majuzi123]: https://github.com/majuzi123
[@Drifterpc]: https://github.com/Drifterpc
[@tingsu]: https://github.com/tingsu

[Zhendong Su](https://people.inf.ethz.ch/suz/), [Yiheng Xiong](https://xyiheng.github.io/), [Xiangchen Shen](https://xiangchenshen.github.io/), [Mengqian Xu](https://mengqianx.github.io/), [Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp), [Jingling Sun](https://jinglingsun.github.io/), [Jue Wang](https://cv.juewang.info/) 也积极参与了该项目并贡献巨大！

Kea2 还获得了多位来自字节跳动（[Zhao Zhang](https://github.com/zhangzhao4444)、Fastbot团队的Yuhui Su）、OPay（Tiesong Liu）、微信（Haochuan Lu, Yuetang Deng）、华为、小米等多位工业界人士宝贵的洞见、建议、反馈和经验分享。感谢！

[^1]: 许多UI自动化测试工具提供“自定义事件序列”功能（如 [Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和 [AppCrawler](https://github.com/seveniruby/AppCrawler)），但实际使用中存在诸多问题，如自定义能力有限、操作不够灵活等。此前许多Fastbot用户抱怨“自定义事件序列”在使用时出现的问题，见[#209](https://github.com/bytedance/Fastbot_Android/issues/209), [#225](https://github.com/bytedance/Fastbot_Android/issues/225), [#286](https://github.com/bytedance/Fastbot_Android/issues/286)等。

[^2]: UI自动化测试中支持自动断言非常重要，但几乎无测试工具提供该能力。注意到 [AppCrawler](https://ceshiren.com/t/topic/15801/5) 的开发者曾希望提供断言机制，获得用户热切响应，许多用户从2021年就不断催促，但始终未实现。