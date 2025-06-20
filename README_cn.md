[![PyPI](https://img.shields.io/pypi/v/kea2-python.svg)](https://pypi.python.org/pypi/kea2-python)
[![PyPI Downloads](https://static.pepy.tech/badge/kea2-python)](https://pepy.tech/projects/kea2-python)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)


<div>
    <img src="https://github.com/user-attachments/assets/aa5839fc-4542-46f6-918b-c9f891356c84" style="border-radius: 14px; width: 20%; height: 20%;"/> 
</div>

### Github仓库链接
[https://github.com/ecnusse/Kea2](https://github.com/ecnusse/Kea2)

### [点击此处：查看中文文档](README_cn.md)

## 关于

Kea2 是一个易用的 Python 库，用于支持、自定义和提升移动应用的自动化 UI 测试。Kea2 的创新点在于能够融合脚本（通常由人工编写）与自动化 UI 测试工具，从而实现许多有趣且强大的功能。

Kea2 目前构建于 [Fastbot](https://github.com/bytedance/Fastbot_Android) 和 [uiautomator2](https://github.com/openatx/uiautomator2) 之上，针对 [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) 应用。

## 主要特点
- **特点 1**(查找稳定性问题)：具备 [Fastbot](https://github.com/bytedance/Fastbot_Android) 的全部能力，用于压力测试及查找*稳定性问题*（即*崩溃类错误*）；

- **特点 2**(自定义测试场景\事件序列\黑白名单\黑白控件[^1])：允许在运行 Fastbot 时自定义测试场景（例如测试特定应用功能、执行指定事件序列、进入指定 UI 页面、达到特定应用状态、屏蔽特定活动/UI 控件/UI 区域），依托 *python* 语言和 [uiautomator2](https://github.com/openatx/uiautomator2) 提供强大灵活的自定义能力；

- **特点 3**(支持断言机制[^2])：基于继承自 [Kea](https://github.com/ecnusse/Kea) 的[基于性质的测试](https://en.wikipedia.org/wiki/Software_testing#Property_testing)思想，支持在运行 Fastbot 时自动断言，从而发现*逻辑错误*（即*非崩溃类错误*）。

**Kea2 三大特点能力比较**

|  | **特点 1** | **特点 2** | **特点 3** |
| --- | --- | --- | ---- |
| **发现崩溃错误** | :+1: | :+1: | :+1: |
| **发现深层状态下崩溃** |  | :+1: | :+1: |
| **发现非崩溃功能性（逻辑）错误** |  |  | :+1: |


<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>



## 设计与路线图
Kea2 作为 Python 库发布，目前与以下工具协作工作：
- 使用 [unittest](https://docs.python.org/3/library/unittest.html) 作为测试框架；
- 使用 [uiautomator2](https://github.com/openatx/uiautomator2) 作为 UI 测试驱动；
- 使用 [Fastbot](https://github.com/bytedance/Fastbot_Android) 作为后台自动化 UI 测试工具。

未来，Kea2 将扩展支持
- [pytest](https://docs.pytest.org/en/stable/)
- [Appium](https://github.com/appium/appium)、[Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)（适用于 HarmonyOS/Open Harmony）
- 其他自动化 UI 测试工具（不限于 Fastbot）


## 安装

运行环境：
- 支持 Windows、MacOS 和 Linux
- python 3.8+，Android 5.0+（需安装 Android SDK）
- **关闭 VPN**（特点 2 和 3 需要）

通过 `pip` 安装 Kea2：
```bash
python3 -m pip install kea2-python
```

运行以下命令查看 Kea2 的选项：
```bash
kea2 -h
```

## 快速测试

Kea2 需要连接并运行在 Android 设备上。建议您先做一个快速测试以确保 Kea2 与您的设备兼容。

1. 连接一台真实 Android 设备或 Android 模拟器（一个设备即可），并确保通过 `adb devices` 能看到连接设备。

2. 运行 `quicktest.py` 测试一个示例应用 `omninotes`（此应用以 `omninotes.apk` 形式发布在 Kea2 仓库中）。`quicktest.py` 脚本会自动安装并短时间测试此示例应用。

在您期望的工作目录中初始化 Kea2：
```python
kea2 init
```

> 如果是第一次运行 Kea2，此步骤必须执行。

运行快速测试：
```python
python3 quicktest.py
```

如果您看到应用 `omninotes` 成功启动并被测试，则说明 Kea2 工作正常！
否则，请帮忙[提交 bug 报告](https://github.com/ecnusse/Kea2/issues)并附上错误信息。谢谢！


## 特点1(运行基础版Fastbot：查找稳定性错误)

使用 Fastbot 的全部能力测试您的应用，进行压力测试并查找*稳定性问题*（即*崩溃类错误*）;


```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

理解上述选项含义请查看[文档](docs/manual_en.md#launching-kea2)

> 用法类似于原生 Fastbot 的[shell 命令](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command)。

更多选项请使用
```bash
kea2 run -h
```

## 特点2(运行增强版Fastbot：自定义测试场景\事件序列\黑白控件)

当使用类似 Fastbot 的自动化 UI 测试工具测试应用时，您可能会发现某些特定 UI 页面或功能难以达到或覆盖。原因是 Fastbot 缺乏对您应用的知识。幸运的是，脚本测试擅长弥补这一点。在特点 2 中，Kea2 支持编写小脚本来指导 Fastbot 探索我们希望其到达的界面。同时，还可以用此类小脚本屏蔽测试过程中的指定控件。

在 Kea2 中，一条脚本由两部分构成：
- **前置条件：** 何时执行该脚本。
- **交互场景：** 脚本的测试方法中指定的交互逻辑，用以达到期望位置。

### 简单示例

假设 `Privacy` 是在自动化 UI 测试中较难达到的页面。Kea2 可以轻松引导 Fastbot 到达该页面。

```python
    @prob(0.5)
    # 前置条件：当页面位于 `Home`
    @precondition(lambda self: 
        self.d(text="Home").exists
    )
    def test_goToPrivacy(self):
        """
        通过打开 `Drawer`，点击选项 `Settings` 并点击 `Privacy`，引导 Fastbot 到达 `Privacy` 页面。
        """
        self.d(description="Drawer").click()
        self.d(text="Settings").click()
        self.d(text="Privacy").click()
```

- 通过装饰器 `@precondition` 说明前置条件——当我们在 `Home` 页面时。
此处，`Home` 页面是 `Privacy` 页面的入口，且 Fastbot 容易到达 `Home` 页面。脚本通过检查唯一控件 `Home` 是否存在来激活。
- 脚本的测试方法 `test_goToPrivacy` 中指定交互逻辑（即打开 `Drawer`，点击 `Settings`，再点击 `Privacy`），引导 Fastbot 到达 `Privacy` 页面。
- 通过装饰器 `@prob` 指定出发概率（本例为 50%），从而在处于 `Home` 页面时，有该概率执行上述指导动作，保证 Fastbot 仍能探索其他页面。

完整示例可见脚本 `quicktest.py`，可用以下命令运行此脚本及 Fastbot：

```bash
# 启动 Kea2 并只加载单条脚本 quicktest.py
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## 特点3(运行增强版Fastbot：加入自动断言)

当运行 Fastbot 时，Kea2 支持自动断言功能，以发现*逻辑错误*（即*非崩溃错误*）。您可以在脚本中添加断言，当自动化 UI 测试过程中断言失败，即可能发现函数缺陷。

在特点 3 中，一条脚本包含三个部分：

- **前置条件：** 何时执行该脚本。
- **交互场景：** 脚本测试方法中的交互逻辑。
- **断言：** 期望的应用行为。

### 示例

在社交媒体应用中，发送消息是常见功能。在发送页面，当输入框非空时，`send` 按钮应始终出现。

<div align="center" >
    <div>
        <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
    </div>
    <p>期望行为（上图）和有缺陷行为（下图）。<p/>
</div>

针对上述始终成立的性质，我们可以写如下脚本进行功能正确性验证：当消息发送页面有 `input_box` 控件时，向其输入任意非空字符串，并断言 `send_button` 始终存在。

```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exist

        # 我们还可以做更多断言，例如：
        #  输入的字符串应当显示在消息发送页面
        assert self.d(text=random_str).exist
```
>  我们使用 [hypothesis](https://github.com/HypothesisWorks/hypothesis) 来生成随机文本。

您可以用特点 2 中类似命令运行此示例。

## 文档（更多文档）

[更多文档](docs/manual_en.md)，包括：
- Kea2 案例教程（基于微信介绍）
- Kea2 脚本定义方法，支持的脚本装饰器（如`@precondition`、`@prob`、`@max_tries`）
- Kea2 启动方式、命令行选项
- 查看/理解 Kea2 运行结果（如界面截图、测试覆盖率、脚本是否成功执行）
- [如何黑白控件/区域](docs/blacklisting.md)

## Kea2 采用的开源项目

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

项目也得到 [Zhendong Su](https://people.inf.ethz.ch/suz/)、[Yiheng Xiong](https://xyiheng.github.io/)、[Xiangchen Shen](https://xiangchenshen.github.io/)、[Mengqian Xu](https://mengqianx.github.io/)、[Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp)、[Jingling Sun](https://jinglingsun.github.io/)、[Jue Wang](https://cv.juewang.info/) 等多位科学家的积极参与和贡献！

此外，来自字节跳动（如 Fastbot 团队的 [Zhao Zhang](https://github.com/zhangzhao4444)、Yuhui Su）、OPay（Tiesong Liu）、微信（Haochuan Lu、Yuetang Deng）、华为、小米等多家工业界人员给予了许多宝贵的见解、建议、反馈和经验分享，特此致谢！

[^1]: 许多 UI 自动化测试工具提供“自定义事件序列”能力（如[Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97)和[AppCrawler](https://github.com/seveniruby/AppCrawler)），但实际使用中存在不少问题，如自定义能力有限、使用不灵活等。许多 Fastbot 用户对此提出过抱怨，如[#209](https://github.com/bytedance/Fastbot_Android/issues/209)、[#225](https://github.com/bytedance/Fastbot_Android/issues/225)、[#286](https://github.com/bytedance/Fastbot_Android/issues/286)等。

[^2]: UI 自动化测试过程中的自动断言能力非常重要，但几乎没有测试工具提供。注意到[AppCrawler](https://ceshiren.com/t/topic/15801/5)的开发者曾尝试实现断言机制，用户反响热烈，从 2021 年起不断催促，但最终未能实现。