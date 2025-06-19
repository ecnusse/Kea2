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

Kea2 是一个易用的 Python 库，用于支持、自定义及提升移动应用的自动化 UI 测试。Kea2 的创新点在于能够融合由人类编写的脚本与自动化 UI 测试工具，从而实现许多有趣且强大的功能。

Kea2 目前构建于 [Fastbot](https://github.com/bytedance/Fastbot_Android) 和 [uiautomator2](https://github.com/openatx/uiautomator2) 之上，目标为 [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) 应用。

## 重要功能
- **功能 1**(查找稳定性问题)：具备 [Fastbot](https://github.com/bytedance/Fastbot_Android) 的全部能力，进行压力测试并发现*稳定性问题*(即*崩溃错误*);
  
- **功能 2**(自定义测试场景\事件序列\黑白名单\黑白控件[^1])：在运行 Fastbot 时自定义测试场景（例如测试具体的应用功能、执行特定的事件序列、进入特定的 UI 页面、达到特定的应用状态、将特定的 activity/UI 控件/UI 区域列入黑名单）——利用 *python* 语言和 [uiautomator2](https://github.com/openatx/uiautomator2) 完全的能力与灵活性实现；

- **功能 3**(支持断言机制[^2])：支持在运行 Fastbot 时自动断言，基于从 [Kea](https://github.com/ecnusse/Kea) 继承的[基于性质的测试](https://en.wikipedia.org/wiki/Software_testing#Property_testing)理念，用于发现*逻辑错误*(即*非崩溃错误*)

**Kea2 三大功能的能力对比**
|  | **功能 1** | **功能 2** | **功能 3** |
| --- | --- | --- | ---- |
| **发现崩溃** | :+1: | :+1: | :+1: |
| **深层状态下发现崩溃** |  | :+1: | :+1: |
| **发现非崩溃功能性（逻辑）错误** |  |  | :+1: |

<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>

## 设计与计划

Kea2 作为 Python 库发布，目前集成：
- 以 [unittest](https://docs.python.org/3/library/unittest.html) 作为测试框架；
- 使用 [uiautomator2](https://github.com/openatx/uiautomator2) 作为 UI 测试驱动；
- 以 [Fastbot](https://github.com/bytedance/Fastbot_Android) 作为后端自动化 UI 测试工具。

未来计划扩展支持：
- [pytest](https://docs.pytest.org/en/stable/)
- [Appium](https://github.com/appium/appium)，[Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)（针对 HarmonyOS/Open Harmony）
- 其他自动化 UI 测试工具（不限于 Fastbot）

## 安装

运行环境要求：
- 支持 Windows、MacOS 和 Linux
- python 3.8+，Android 5.0+（需安装 Android SDK）
- **关闭 VPN**（功能 2 和 3 需要）

通过 `pip` 安装 Kea2：
```bash
python3 -m pip install kea2-python
```

查看 Kea2 的选项运行命令：
```bash
kea2 -h
```

## 快速测试

Kea2 连接并运行于 Android 设备。建议您做一次快速测试，以确保 Kea2 与您的设备兼容。

1. 连接一台真实 Android 设备或 Android 模拟器（一个设备即可），确保运行 `adb devices` 能看到设备。

2. 运行 `quicktest.py` 测试示例应用 `omninotes`（在 Kea2 仓库中已发布 `omninotes.apk`）。脚本 `quicktest.py` 会自动安装并短时间测试此示例应用。

在您喜欢的工作目录下初始化 Kea2：
```python
kea2 init
```

> 如果是第一次运行 Kea2，这一步总是必须的。

执行快速测试：
```python
python3 quicktest.py
```

如果看到应用 `omninotes` 成功运行并被测试，即表示 Kea2 已生效！
否则，请帮助我们[提交错误报告](https://github.com/ecnusse/Kea2/issues)，并附上错误信息。感谢！

## 功能 1（运行基础版 Fastbot：查找稳定性错误）

使用 Fastbot 的全部能力对您的应用进行压力测试，查找*稳定性问题*（即*崩溃错误*）；

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

理解上述选项含义请查看[文档](docs/manual_en.md#launching-kea2)

> 用法类似于原 Fastbot 的[shell 命令](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command)。

查看更多选项：
```bash
kea2 run -h
```

## 功能 2（运行增强版 Fastbot：自定义测试场景\事件序列\黑白控件）

在运行 Fastbot 等自动 UI 测试工具测试您的应用时，您可能会发现某些特定 UI 页面或功能难以到达或覆盖，原因在于 Fastbot 缺少应用知识。幸运的是，这正是脚本测试的优势。功能 2 中，Kea2 支持编写小脚本指导 Fastbot 探索我们想去的地方，您也可以用小脚本在 UI 测试中屏蔽特定控件。

在 Kea2 中，一个脚本由两个元素组成：
- **前置条件（Precondition）**：什么时候执行该脚本；
- **交互场景**：交互逻辑（由脚本的测试方法指定）以达到目标位置。

### 简单示例

假设 `Privacy` 是自动 UI 测试中难以到达的页面，Kea2 可以轻松引导 Fastbot 到达该页面。

```python
    @prob(0.5)
    # precondition: 当我们处于页面 `Home`
    @precondition(lambda self: 
        self.d(text="Home").exists
    )
    def test_goToPrivacy(self):
        """
        引导 Fastbot 到达页面 `Privacy`，通过打开 `Drawer`，
        点击选项 `Settings`，再点击 `Privacy`。
        """
        self.d(description="Drawer").click()
        self.d(text="Settings").click()
        self.d(text="Privacy").click()
```

- 通过装饰器 `@precondition`，我们指定前置条件——当我们处于 `Home` 页面。此处 `Home` 页面是进入 `Privacy` 页的入口，且 Fastbot 容易达到该页面。脚本在检测到存在唯一控件 `Home` 时激活。
- 测试方法 `test_goToPrivacy` 中指定交互逻辑（打开 `Drawer`，点击选项 `Settings`，再点击 `Privacy`）以引导 Fastbot 到达 `Privacy` 页面。
- 装饰器 `@prob` 指定在处于 `Home` 页面时以 50% 的概率执行该指导操作。这样 Kea2 保持了 Fastbot 探索其他页面的能力。

您可以在脚本 `quicktest.py` 中找到完整示例，并用 `kea2 run` 命令配合 Fastbot 运行：

```bash
# 启动 Kea2 并加载单脚本 quicktest.py。
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## 功能 3（运行增强版 Fastbot：加入自动断言）

Kea2 支持在运行 Fastbot 时实现自动断言，用于发现*逻辑错误*(即*非崩溃错误*)。为此，您可以在脚本中添加断言。当自动化 UI 测试过程中断言失败时，我们就发现了可能的功能性缺陷。

功能 3 中，一个脚本由三个元素构成：

- **前置条件**：什么时候执行脚本；
- **交互场景**：交互逻辑（由脚本测试方法指定）；
- **断言**：期望的应用行为。

### 示例

在社交媒体应用中，发送消息是常用功能。在发送消息页面，当输入框不为空时，`send` 按钮应始终显示。

<div align="center" >
    <div >
        <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
    </div>
    <p>期望行为（上图）与错误行为（下图）。</p>
</div>

针对上述恒定性质，我们可以写如下脚本来验证功能正确性：当消息页面存在 `input_box` 控件，输入任意非空字符串后，断言 `send_button` 始终存在。

```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exist

        # 我们甚至可以做更多断言，例如：
        #       发送页面应显示输入的字符串
        assert self.d(text=random_str).exist
```
> 我们使用了 [hypothesis](https://github.com/HypothesisWorks/hypothesis) 来生成随机文本。

您可以用功能 2 中类似的命令行运行此示例。

## 文档（更多文档）

[更多文档](docs/manual_en.md)，包括：
- Kea2 案例教程（基于微信介绍）；
- Kea2 脚本定义方法，支持的脚本装饰器（如 `@precondition`、`@prob`、`@max_tries`）；
- Kea2 启动方式、命令行选项；
- 查看/理解 Kea2 运行结果（如界面截图、测试覆盖率、脚本执行成功与否）；
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

[Zhendong Su](https://people.inf.ethz.ch/suz/), [Yiheng Xiong](https://xyiheng.github.io/), [Xiangchen Shen](https://xiangchenshen.github.io/), [Mengqian Xu](https://mengqianx.github.io/), [Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp), [Jingling Sun](https://jinglingsun.github.io/), [Jue Wang](https://cv.juewang.info/) 也积极参与了该项目并贡献良多！

Kea2 也获得了来自字节跳动([Zhao Zhang](https://github.com/zhangzhao4444)、Fastbot 团队的 Yuhui Su)、OPay（Tiesong Liu）、微信（Haochuan Lu, Yuetang Deng）、华为、小米等多位业界人士的宝贵见解、建议、反馈和经验分享，感谢支持！

[^1]: 许多 UI 自动化测试工具支持“自定义事件序列”能力（如 [Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和 [AppCrawler](https://github.com/seveniruby/AppCrawler)），但在实际使用中存在许多问题，例如自定义能力有限、使用不灵活等。此前不少 Fastbot 用户投诉其“自定义事件序列”的使用问题，如[#209](https://github.com/bytedance/Fastbot_Android/issues/209), [#225](https://github.com/bytedance/Fastbot_Android/issues/225), [#286](https://github.com/bytedance/Fastbot_Android/issues/286)等。

[^2]: 在 UI 自动化测试过程中支持自动断言是一项非常重要的能力，但几乎没有测试工具提供该功能。我们注意到 [AppCrawler](https://ceshiren.com/t/topic/15801/5) 的开发者曾试图引入断言机制，受到用户热切期待，许多用户自 2021 年起持续催促更新，但终未实现。