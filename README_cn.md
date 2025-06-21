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

Kea2 是一个易用的移动应用模糊测试工具。它的核心*创新点*在于能够融合自动化 UI 测试与脚本（通常由人工编写），从而赋能自动化 UI 测试以人类智能，有效发现*崩溃错误*以及*非崩溃功能（逻辑）错误*。

Kea2 目前构建于 [Fastbot](https://github.com/bytedance/Fastbot_Android) 之上，*一个工业级自动化 UI 测试工具*，以及 [uiautomator2](https://github.com/openatx/uiautomator2)，*一个易用且稳定的 Android 自动化库*。  
Kea2 当前目标为 [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) 应用。

## 重要特性

<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>

- **特性 1**（查找稳定性问题）：集成 [Fastbot](https://github.com/bytedance/Fastbot_Android) 全能力用于压力测试及查找*稳定性问题*（即*崩溃错误*）；

- **特性 2**（自定义测试场景\事件序列\黑白名单\黑白控件[^1]）：运行 Fastbot 时可自定义测试场景（如测试特定应用功能、执行特定事件轨迹、进入特定 UI 页面、达到特定应用状态、黑名单指定特定活动/UI 控件/UI 区域）的能力，利用*python*语言及 [uiautomator2](https://github.com/openatx/uiautomator2) 的完整能力和灵活性；

- **特性 3**（支持断言机制[^2]）：运行 Fastbot 时支持自动断言，基于继承于 [Kea](https://github.com/ecnusse/Kea) 的[基于性质的测试](https://en.wikipedia.org/wiki/Software_testing#Property_testing)理念，用于查找*逻辑错误*（即*非崩溃功能错误*）。

对于**特性 2 和 3**，Kea2 允许你关注测试哪些应用功能，无需担心如何抵达这些功能点，交由 Fastbot 处理。结果是你的脚本往往简短、稳健且便于维护，同时相关功能点的压力测试更为充分！

**Kea2 三大特性的能力对比**

|  | **特性 1** | **特性 2** | **特性 3** |
| --- | --- | --- | ---- |
| **发现崩溃** | :+1: | :+1: | :+1: |
| **在深度状态发现崩溃** |  | :+1: | :+1: |
| **发现非崩溃功能（逻辑）错误** |  |  | :+1: |



## 设计与规划
作为 Python 库发布的 Kea2，目前配套使用：
- [unittest](https://docs.python.org/3/library/unittest.html) 作为测试框架；
- [uiautomator2](https://github.com/openatx/uiautomator2) 作为 UI 测试驱动；
- [Fastbot](https://github.com/bytedance/Fastbot_Android) 作为后端自动化 UI 测试工具。

未来，Kea2 将扩展支持
- [pytest](https://docs.pytest.org/en/stable/)
- [Appium](https://github.com/appium/appium), [Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)（针对 HarmonyOS/Open Harmony）
- 其他自动化 UI 测试工具（不限于 Fastbot）


## 安装

运行环境：
- 支持 Windows、MacOS 和 Linux
- python 3.8+，Android 5.0+（需安装 Android SDK）
- **关闭 VPN**（特性 2 和 3 需要）

通过 `pip` 安装 Kea2：
```bash
python3 -m pip install kea2-python
```

通过运行以下命令查看 Kea2 的选项
```bash
kea2 -h
```

## 快速测试

Kea2 连接并运行于 Android 设备。建议您进行快速测试以确认 Kea2 是否兼容您的设备。

1. 连接一台真实 Android 设备或一个 Android 模拟器（只需要一台设备），通过运行 `adb devices` 确认设备已连接。

2. 运行 `quicktest.py` 来测试示例应用 `omninotes`（该应用以 `omninotes.apk` 形式包含于 Kea2 仓库）。脚本 `quicktest.py` 会自动安装并短时间测试该示例应用。

在期望的工作目录中初始化 Kea2：
```python
kea2 init
```

> 若首次运行 Kea2，此步骤必需。

运行快速测试：
```python
python3 quicktest.py
```

若看到应用 `omninotes` 成功运行并测试，则表明 Kea2 正常工作！  
否则，请帮忙通过 [提交 bug 报告](https://github.com/ecnusse/Kea2/issues) 并附上错误信息联系我们，谢谢！



## 特性 1（运行基础版 Fastbot：查找稳定性错误）

利用 Fastbot 全能力测试您的应用，进行压力测试并发现*稳定性问题*（即*崩溃错误*）；

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

理解上述选项请查看[文档](docs/manual_en.md#launching-kea2)

> 用法与原始 Fastbot 的[shell 命令](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command)相似。

查看更多选项：
```bash
kea2 run -h
```

## 特性 2（运行增强版 Fastbot：自定义测试场景\事件序列\黑白控件）

运行任何自动化 UI 测试工具（如 Fastbot）测试应用时，有时会发现某些特定 UI 页面或功能难以到达或覆盖，原因在于 Fastbot 缺乏对应用的知识。幸运的是，脚本测试在这方面具有优势。  
在特性 2 中，Kea2 支持编写小脚本，引导 Fastbot 探索任意目标位置，也可以用来在 UI 测试中屏蔽特定控件。

在 Kea2 中，一个脚本由两部分组成：
- **前置条件（Precondition）：** 脚本执行的时机。
- **交互场景（Interaction scenario）：** 脚本测试方法指定的交互逻辑，达到预期目标。

### 简单示例

假设 `Privacy` 是自动化 UI 测试中难以到达的页面，Kea2 可以轻松引导 Fastbot 到达该页面。

```python
    @prob(0.5)
    # precondition: 当我们处于 `Home` 页面时
    @precondition(lambda self: 
        self.d(text="Home").exists
    )
    def test_goToPrivacy(self):
        """
        通过打开 `Drawer`，点击 `Settings` 选项，再点击 `Privacy` 引导 Fastbot 到达 `Privacy` 页面。
        """
        self.d(description="Drawer").click()
        self.d(text="Settings").click()
        self.d(text="Privacy").click()
```

- 通过装饰器 `@precondition`，我们指定前置条件——当处于 `Home` 页面时激活脚本。此处 `Home` 页面是 `Privacy` 页面入口，且 Fastbot 容易到达，所以脚本通过检查是否存在唯一控件 `Home` 来判断是否激活。  
- 在脚本测试方法 `test_goToPrivacy` 中，指定具体交互逻辑（打开 Drawer，点击 Settings，再点击 Privacy）以引导 Fastbot 到达 `Privacy` 页面。  
- 通过装饰器 `@prob`，我们指定在满足前置条件时执行脚本的概率（本例为 50%），使 Kea2 仍允许 Fastbot 探索其他页面。

完整示例可见脚本 `quicktest.py`，用以下命令调用 Fastbot 运行该脚本：

```bash
# 启动 Kea2 并加载单个脚本 quicktest.py。
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## 特性 3（运行增强版 Fastbot：加入自动断言）

Kea2 支持在运行 Fastbot 时自动断言，用于发现*逻辑错误*（即*非崩溃错误*）。为此，您可在脚本中添加断言。测试执行中断言失败即视为发现潜在的功能性错误。

在特性 3 中，一个脚本由三部分组成：

- **前置条件（Precondition）：** 脚本执行的时机。
- **交互场景（Interaction scenario）：** 脚本测试方法指定的交互逻辑。
- **断言（Assertion）：** 预期的应用行为。

### 示例

在社交媒体应用中，消息发送是常见功能。发送消息页面中，当输入框非空时，`send` 按钮应始终出现。

<div align="center">
    <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
</div>

<div align="center">
    期望行为（上图）与错误行为（下图）。
</div>
    

针对上述始终成立的性质，我们可以写如下脚本验证功能正确性：当消息发送页面存在 `input_box` 控件时，输入任意非空字符串，并断言 `send_button` 始终存在。

```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exist

        # 我们甚至可以做更多断言，例如
        #       输入的字符串应该显示在消息发送页面
        assert self.d(text=random_str).exist
```
> 我们使用 [hypothesis](https://github.com/HypothesisWorks/hypothesis) 来生成随机文本。

可使用特性 2 中类似的命令行运行该示例。

## 文档（更多文档）

[更多文档](docs/manual_en.md)，包括：
- 基于微信介绍的 Kea2 案例教程、
- Kea2 脚本定义方式、支持的脚本装饰器（如 `@precondition`、`@prob`、`@max_tries`）、
- Kea2 启动方式、命令行选项
- 查看/理解 Kea2 运行结果（如界面截图、测试覆盖率、脚本执行成功与否）。
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

Kea2 由 [ecnusse](https://github.com/ecnusse) 团队积极开发与维护：

- [Xixian Liang](https://xixianliang.github.io/resume/) ([@XixianLiang][])
- Bo Ma ([@majuzi123][])
- Chen Peng ([@Drifterpc][])
- [Ting Su](https://tingsu.github.io/) ([@tingsu][])

[@XixianLiang]: https://github.com/XixianLiang
[@majuzi123]: https://github.com/majuzi123
[@Drifterpc]: https://github.com/Drifterpc
[@tingsu]: https://github.com/tingsu

[Zhendong Su](https://people.inf.ethz.ch/suz/)、[Yiheng Xiong](https://xyiheng.github.io/)、[Xiangchen Shen](https://xiangchenshen.github.io/)、[Mengqian Xu](https://mengqianx.github.io/)、[Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp)、[Jingling Sun](https://jinglingsun.github.io/)、[Jue Wang](https://cv.juewang.info/) 等人也积极参与了本项目并做出了大量贡献！

Kea2 也收到了来自字节跳动（Fastbot 团队的 [Zhao Zhang](https://github.com/zhangzhao4444)、Su Ting）、OPay（Tiesong Liu）、微信（Haochuan Lu、Yuetang Deng）、华为、小米等多家工业界人士的宝贵见解、建议、反馈和经验分享，致敬！

[^1]: 不少 UI 自动化测试工具提供了“自定义事件序列”能力（如 [Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和 [AppCrawler](https://github.com/seveniruby/AppCrawler)），但在实际使用中存在不少问题，如自定义能力有限、使用不灵活等。此前不少 Fastbot 用户抱怨过其“自定义事件序列”在使用中的问题，如[#209](https://github.com/bytedance/Fastbot_Android/issues/209), [#225](https://github.com/bytedance/Fastbot_Android/issues/225), [#286](https://github.com/bytedance/Fastbot_Android/issues/286)等。

[^2]: 在 UI 自动化测试过程中支持自动断言是一个很重要的能力，但几乎没有测试工具提供这样的能力。我们注意到 [AppCrawler](https://ceshiren.com/t/topic/15801/5) 的开发者曾经希望提供一种断言机制，得到了用户的热切响应，不少用户从21年就开始催更，但始终未能实现。