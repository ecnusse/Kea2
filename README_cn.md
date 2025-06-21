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

Kea2 是一款易用的移动应用模糊测试工具。其关键*创新点*在于能够将自动化UI测试与脚本（通常由人工编写）融合，从而赋能自动化UI测试以注入人的智能，有效地发现*崩溃错误*以及*非崩溃的功能（逻辑）错误*。

Kea2 当前构建在 [Fastbot](https://github.com/bytedance/Fastbot_Android)（*一款工业级自动化UI测试工具*）和 [uiautomator2](https://github.com/openatx/uiautomator2)（*一款易用且稳定的Android自动化库*）之上。  
Kea2 目前主要面向 [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) 应用。

## 创新点及重要特性

<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>

- **特性 1**（查找稳定性问题）：具备 [Fastbot](https://github.com/bytedance/Fastbot_Android) 的全部能力用于压力测试并查找*稳定性问题*（即*崩溃错误*）；

- **特性 2**（自定义测试场景\事件序列\黑白名单\黑白控件[^1]）：运行 Fastbot 时自定义测试场景（如测试特定应用功能、执行特定事件序列、进入特定UI页面、达到指定应用状态、屏蔽特定 Activity/UI 控件/UI 区域），该能力由 *python* 语言及 [uiautomator2](https://github.com/openatx/uiautomator2) 强大且灵活的支持提供；

- **特性 3**（支持断言机制[^2]）：运行 Fastbot 时支持自动断言机制，基于继承自 [Kea](https://github.com/ecnusse/Kea) 的[基于性质的测试](https://en.wikipedia.org/wiki/Software_testing#Property_testing)思想，用以发现*逻辑错误*（即*非崩溃功能错误*）。

    对于**特性 2 和 3**，Kea2 让你专注于测试哪些应用功能，无需关心如何到达这些功能。只需让 Fastbot 帮助完成。由此，你的脚本通常简短、健壮且易于维护，且对应的应用功能被更加充分地压力测试！

**Kea2 三大特性能力**

|  | **特性 1** | **特性 2** | **特性 3** |
| --- | --- | --- | ---- |
| **发现崩溃** | :+1: | :+1: | :+1: |
| **发现深层状态下的崩溃** |  | :+1: | :+1: |
| **发现非崩溃功能（逻辑）错误** |  |  | :+1: |



## 设计与路线图
Kea2 目前协同工作：
- 以 [unittest](https://docs.python.org/3/library/unittest.html) 作为测试框架管理脚本；
- 以 [uiautomator2](https://github.com/openatx/uiautomator2) 作为UI测试驱动；
- 以 [Fastbot](https://github.com/bytedance/Fastbot_Android) 作为后端自动化UI测试工具。

未来，Kea2 将扩展支持
- [pytest](https://docs.pytest.org/en/stable/)，另一款流行的 python 测试框架；
- [Appium](https://github.com/appium/appium)、[Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)（用于 HarmonyOS/Open Harmony）；
- 以及任何其他自动化UI测试工具（不限于 Fastbot）


## 安装

运行环境：
- 支持 Windows、MacOS 和 Linux
- python 3.8+，Android 5.0+（需安装 Android SDK）
- **关闭 VPN**（特性 2 和特性 3 需要）

通过 `pip` 安装 Kea2：
```bash
python3 -m pip install kea2-python
```

获取 Kea2 所有选项：
```bash
kea2 -h
```

## 快速测试

Kea2 连接并运行于 Android 设备。建议您快速测试以确保 Kea2 与您的设备兼容。

1. 连接实体 Android 设备或 Android 模拟器（一个设备即可），并通过运行 `adb devices` 确认设备已连接。

2. 运行 `quicktest.py` 测试示例应用 `omninotes`（该应用以 `omninotes.apk` 发布在 Kea2 仓库）。`quicktest.py` 会自动安装并短时间测试该示例应用。

在您首选的工作目录下初始化 Kea2：
```python
kea2 init
```

> 若首次运行 Kea2，此步骤必做。

运行快速测试：
```python
python3 quicktest.py
```

若您看到应用 `omninotes` 成功运行并被测试，恭喜 Kea2 正常工作！  
否则，请帮忙通过 [提交Bug报告](https://github.com/ecnusse/Kea2/issues) 并附上错误信息。谢谢！



## 特性 1（运行基础版 Fastbot：查找稳定性错误）

使用 Fastbot 的全部能力进行压力测试并查找*稳定性问题*（即*崩溃错误*）；

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

理解上述选项请参考[文档](docs/manual_en.md#launching-kea2)

> 用法类似于原始 Fastbot 的[shell 命令](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command)。

查看更多选项：
```bash
kea2 run -h
```

## 特性 2（运行增强版 Fastbot：自定义测试场景\事件序列\黑白控件）

运行 Fastbot 等自动化UI测试工具测试应用时，你可能会发现某些特定UI页面或功能难以达到或覆盖。原因是 Fastbot 缺乏对应用的知识。幸运的是，脚本测试正是这方面的优势。在特性 2 中，Kea2 支持编写小脚本来指导 Fastbot 探索我们想要到达的任意位置。你还可以用这类小脚本在UI测试过程中屏蔽特定控件。

在 Kea2 中，一个脚本由两个元素组成：
- **前置条件（Precondition）**：何时执行该脚本。
- **交互场景**：达到目标页面的交互逻辑（在脚本的测试方法中指定）。

### 简单示例

假设 `Privacy` 是自动化UI测试时难以触达的UI页面。Kea2 能轻松引导 Fastbot 到达该页面。

```python
    @prob(0.5)
    # precondition: 当我们在页面 `Home` 时执行
    @precondition(lambda self: 
        self.d(text="Home").exists
    )
    def test_goToPrivacy(self):
        """
        通过打开 `Drawer`、点击选项 `Settings` 以及点击 `Privacy`，
        指导 Fastbot 到达页面 `Privacy`。
        """
        self.d(description="Drawer").click()
        self.d(text="Settings").click()
        self.d(text="Privacy").click()
```

- 通过装饰器 `@precondition`，我们指定了前置条件 —— 当页面处于 `Home` 时执行该脚本。  
  其中，`Home` 页面是进入 `Privacy` 页面的起点，且 Fastbot 容易达到 `Home` 页面。  
  因此脚本将在检测到唯一控件 `Home` 存在时被激活。  
- 在脚本测试方法 `test_goToPrivacy` 中，我们指定交互逻辑（即打开 `Drawer`，点击 `Settings`，再点击 `Privacy`）以指导 Fastbot 达到 `Privacy` 页面。  
- 通过装饰器 `@prob`，我们指定当处于 `Home` 页面时，有 50% 概率执行该引导操作。这样，Kea2 还能允许 Fastbot 探索其他页面。

完整示例见脚本 `quicktest.py`，可使用如下命令配合 Fastbot 运行此脚本：

```bash
# 启动 Kea2 并加载单个脚本 quicktest.py。
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## 特性 3（运行增强版 Fastbot：加入自动断言）

Kea2 支持运行 Fastbot 时的自动断言，用于发现*逻辑错误*（即*非崩溃错误*）。为此，你可以在脚本中添加断言。自动化测试时，当断言失败，则发现了可能的功能缺陷。

特性 3 中的脚本包含三个元素：

- **前置条件（Precondition）**：何时执行该脚本。
- **交互场景**：脚本测试方法中指定的交互逻辑。
- **断言**：期望的应用行为。

### 示例

在某社交软件中，发送消息是常见功能。消息发送页面当输入框不为空时，`send` 按钮应一直显示。

<div align="center">
    <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
</div>

<div align="center">
    期望行为（上图）与错误行为（下图）。
</div>
    

针对上述应始终满足的性质，我们可编写如下脚本验证功能是否正确：当消息发送页存在 `input_box` 控件时，输入任意非空字符串，断言 `send_button` 应始终存在。

```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exist

        # 示例中还可加更多断言，如：
        #       输入字符串应在消息发送页显示
        assert self.d(text=random_str).exist
```
> 我们使用 [hypothesis](https://github.com/HypothesisWorks/hypothesis) 来生成随机文本。

你可以用特性 2 中类似命令行运行此示例。

## 文档（更多文档）

[更多文档](docs/manual_en.md)，涵盖：
- Kea2 案例教程（以微信为例）；
- Kea2 脚本定义方法，支持的脚本装饰器（如 `@precondition`、`@prob`、`@max_tries`）；
- Kea2 启动方式、命令行选项；
- 查看与理解 Kea2 运行结果（如界面截图、测试覆盖率、脚本执行成功与否）；
- [如何设置黑白控件/区域](docs/blacklisting.md)

## Kea2 使用的开源项目

- [Fastbot](https://github.com/bytedance/Fastbot_Android)
- [uiautomator2](https://github.com/openatx/uiautomator2)
- [hypothesis](https://github.com/HypothesisWorks/hypothesis)

## 相关论文

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

[Zhendong Su](https://people.inf.ethz.ch/suz/)、[Yiheng Xiong](https://xyiheng.github.io/)、[Xiangchen Shen](https://xiangchenshen.github.io/)、[Mengqian Xu](https://mengqianx.github.io/)、[Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp)、[Jingling Sun](https://jinglingsun.github.io/)、[Jue Wang](https://cv.juewang.info/) 等也积极参与并贡献卓著！

Kea2 还获得了包括 Bytedance（Fastbot 团队成员赵璋、苏宇辉）、OPay（刘铁松）、微信（陆浩川、邓岳棠）、华为、小米等多位工业界人士的宝贵见解、建议、反馈和经验分享。致敬！

[^1]: 许多UI自动化测试工具提供“自定义事件序列”能力（如[Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和 [AppCrawler](https://github.com/seveniruby/AppCrawler)），但在实际使用中存在诸多问题，如自定义能力有限、使用不灵活等。此前不少 Fastbot 用户投诉其“自定义事件序列”存在的问题，如[#209](https://github.com/bytedance/Fastbot_Android/issues/209)、[#225](https://github.com/bytedance/Fastbot_Android/issues/225)、[#286](https://github.com/bytedance/Fastbot_Android/issues/286)。

[^2]: 在UI自动化测试过程中支持自动断言是一项极重要能力，但几乎无测试工具提供这功能。我们注意到[AppCrawler](https://ceshiren.com/t/topic/15801/5)开发者曾希望实现断言机制，获得用户热烈响应，许多用户从2021年起不停催更，然而始终未能实现。