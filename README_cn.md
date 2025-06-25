[![PyPI](https://img.shields.io/pypi/v/kea2-python.svg)](https://pypi.python.org/pypi/kea2-python)
[![PyPI Downloads](https://static.pepy.tech/badge/kea2-python)](https://pepy.tech/projects/kea2-python)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)


<div>
    <img src="https://github.com/user-attachments/assets/36ec9f2f-a3d8-482a-9a61-4785f3278991" style="border-radius: 14px; width: 20%; height: 20%;"/> 
</div>

### Github 仓库链接
[https://github.com/ecnusse/Kea2](https://github.com/ecnusse/Kea2)

### [点击此处：查看中文文档](README_cn.md)

## 关于

Kea2 是一个易用的移动应用模糊测试工具。其主要*创新点*在于能够将自动化 UI 测试与脚本（通常由人工编写）融合，从而利用人工智慧增强自动化 UI 测试，有效发现*崩溃错误*及*非崩溃功能性（逻辑）错误*。

Kea2 目前构建于 [Fastbot](https://github.com/bytedance/Fastbot_Android) 之上，*一款工业级自动化 UI 测试工具*，以及 [uiautomator2](https://github.com/openatx/uiautomator2)，*一款易用且稳定的 Android 自动化库*。
当前 Kea2 的目标是针对 [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) 应用。

## 创新点及重要特性

<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>

- **特性1**(查找稳定性问题): 具备 [Fastbot](https://github.com/bytedance/Fastbot_Android) 的完整能力，用于压力测试及发现*稳定性问题*（即*崩溃错误*）；

- **特性2**(自定义测试场景\事件序列\黑白名单\黑白控件[^1]): 自定义 Fastbot 运行时的测试场景（例如测试特定功能、执行指定事件序列、进入特定 UI 页面、达到特定应用状态、黑名单特定 Activity/UI 控件/UI 区域），基于 *python* 语言及 [uiautomator2](https://github.com/openatx/uiautomator2) 提供充分的能力和灵活性；

- **特性3**(支持断言机制[^2]): 支持在运行 Fastbot 时基于从 [Kea](https://github.com/ecnusse/Kea) 继承的[基于性质的测试](https://en.wikipedia.org/wiki/Software_testing#Property_testing)思想，实现自动断言，用于发现*逻辑错误*（即*非崩溃功能性错误*）。

    对于**特性2和特性3**，Kea2 允许你专注于测试哪些应用功能，无需担心如何访问功能点。只需让 Fastbot 帮助，即能使你的脚本通常简短、鲁棒且易维护，且对应的应用功能得到更充分的压力测试！

**Kea2 三大特性的能力汇总**

|  | **特性1** | **特性2** | **特性3** |
| --- | --- | --- | ---- |
| **查找崩溃错误** | :+1: | :+1: | :+1: |
| **查找深层状态下的崩溃** |  | :+1: | :+1: |
| **查找非崩溃功能（逻辑）错误** |  |  | :+1: |



## 设计与发展路线
Kea2 当前使用：
- [unittest](https://docs.python.org/3/library/unittest.html) 作为测试框架管理脚本；
- [uiautomator2](https://github.com/openatx/uiautomator2) 作为 UI 测试驱动；
- [Fastbot](https://github.com/bytedance/Fastbot_Android) 作为后台自动化 UI 测试工具。

未来 Kea2 将扩展支持：
- [pytest](https://docs.pytest.org/en/stable/)，另一款流行 Python 测试框架；
- [Appium](https://github.com/appium/appium)、[Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)（用于 HarmonyOS/Open Harmony）；
- 任何其他自动化 UI 测试工具（不限于 Fastbot）


## 安装

运行环境：
- 支持 Windows、MacOS 和 Linux
- python 3.8+，Android 5.0+（已安装 Android SDK）
- **关闭 VPN**（特性2和3所需）

通过 `pip` 安装 Kea2：
```bash
python3 -m pip install kea2-python
```

运行以下命令查看 Kea2 参数选项：
```bash
kea2 -h
```

## 快速测试

Kea2 可连接并运行于 Android 设备。建议您先做快速测试，确保 Kea2 与您的设备兼容。

1. 连接一台真实 Android 设备或 Android 模拟器（只需一台设备），并确保通过运行 `adb devices` 能看到该设备。

2. 运行 `quicktest.py` 来测试示例应用 `omninotes`（在 Kea2 仓库中以 `omninotes.apk` 形式发布）。脚本 `quicktest.py` 会自动安装并短时测试该示例应用。

在您偏好的工作目录下初始化 Kea2：
```python
kea2 init
```

> 第一次运行 Kea2 时务必执行此步骤。

运行快速测试：
```python
python3 quicktest.py
```

如果您看到应用 `omninotes` 成功运行并被测试，表明 Kea2 工作正常！
否则，请帮助我们[提交问题报告](https://github.com/ecnusse/Kea2/issues)，并附带错误信息。谢谢！



## 特性1（运行基础版 Fastbot：查找稳定性错误）

用 Fastbot 的全部能力对您的应用做压力测试，寻找*稳定性问题*（即*崩溃错误*）；

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

关于命令参数含义，可参阅我们的[手册](docs/manual_en.md#launching-kea2)。

> 使用方式与原 Fastbot 的[shell 命令](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command)类似。

查看更多选项：
```bash
kea2 run -h
```

## 特性2（运行增强版 Fastbot：自定义测试场景\事件序列\黑白控件）

在运行像 Fastbot 这样的 UI 自动化测试工具时，您可能发现某些特定 UI 页面或功能难以触达或覆盖。这是因为 Fastbot 对您的应用不了解。脚本测试则具备此优势。特性2 允许编写小脚本，指导 Fastbot 探索任意页面。您也可用此类脚本屏蔽特定控件。

在 Kea2 中，一个脚本由两个元素组成：
- **前置条件**：何时执行脚本；
- **交互场景**：实现预期访问的交互逻辑（定义在脚本的测试方法中）。

### 简单示例

假设 `Privacy` 是 UI 自动化测试中难以触达的页面，Kea2 可轻松引导 Fastbot 访问该页面。

```python
    @prob(0.5)
    # precondition: 当我们位于页面 `Home`
    @precondition(lambda self: 
        self.d(text="Home").exists
    )
    def test_goToPrivacy(self):
        """
        指导 Fastbot 通过打开 `Drawer`，点击 `Settings`，再点击 `Privacy` 访问页面 `Privacy`。
        """
        self.d(description="Drawer").click()
        self.d(text="Settings").click()
        self.d(text="Privacy").click()
```

- 通过装饰器 `@precondition`，指定前置条件——即当我们处于 `Home` 页面时执行。这里的 `Home` 页面是 `Privacy` 的入口，且 Fastbot 能轻松抵达。因此当检测到唯一控件 `Home` 存在时，脚本才被激活。
- 脚本的测试方法 `test_goToPrivacy` 中定义交互逻辑（打开 `Drawer`，点击 `Settings`，点击 `Privacy`）来引导 Fastbot 抵达 `Privacy` 页面。
- 装饰器 `@prob` 指定触发该行为的概率（例如本示例中为 50%），从而允许 Kea2 同时探索其他页面。

完整示例可见脚本 `quicktest.py`，并通过如下命令用 Fastbot 运行此脚本：

```bash
# 启动 Kea2 并加载单个脚本 quicktest.py。
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## 特性3（运行增强版 Fastbot：加入自动断言）

Kea2 支持在运行 Fastbot 过程中进行自动断言，发现*逻辑错误*（即*非崩溃错误*）。为此，您可在脚本中添加断言。断言失败时即可能发现功能性缺陷。

特性3 中脚本包含三个元素：

- **前置条件**：何时执行脚本；
- **交互场景**：交互逻辑（定义于测试方法）；
- **断言**：期望的应用行为。

### 示例

在社交应用中，发送消息是常见功能。在消息发送页，当输入框非空时，发送按钮应始终出现。

<div align="center">
    <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
</div>

<div align="center">
    期望行为（上图）与异常行为（下图）。
</div>
    

对于上述持续保持的性质，我们可以写如下脚本验证功能正确性：当消息发送页存在 `input_box` 控件时，向输入框录入任意非空字符串，并断言 `send_button` 应始终存在。

```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exist

        # 我们甚至可以做更多断言，比如：
        # 输入的字符串应该出现在消息发送页面
        assert self.d(text=random_str).exist
```
> 我们使用 [hypothesis](https://github.com/HypothesisWorks/hypothesis) 来生成随机文本。

您可用与特性2类似的命令行运行此示例。

## 文档（更多文档）

您可查阅 [用户手册](docs/manual_en.md)，包含：
- Kea2 在微信上的使用示例（中文）；
- 如何定义 Kea2 脚本及使用装饰器（如 `@precondition`、`@prob`、`@max_tries`）；
- 如何运行 Kea2 及命令行选项；
- 如何定位及理解 Kea2 测试结果；
- 如何在模糊测试期间[设置白名单或黑名单](docs/blacklisting.md)针对特定 Activity、UI 控件和 UI 区域。

## Kea2 依赖的开源项目

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

[Zhendong Su](https://people.inf.ethz.ch/suz/), [Yiheng Xiong](https://xyiheng.github.io/), [Xiangchen Shen](https://xiangchenshen.github.io/), [Mengqian Xu](https://mengqianx.github.io/), [Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp), [Jingling Sun](https://jinglingsun.github.io/), [Jue Wang](https://cv.juewang.info/) 也曾积极参与并对该项目做出大量贡献！

此外，Kea2 得到了多位来自业界人士的宝贵见解、建议、反馈及经验分享，包括来自 Bytedance（[Zhao Zhang](https://github.com/zhangzhao4444)、Fastbot 团队的 Yuhui Su）、OPay（Tiesong Liu）、WeChat（Haochuan Lu、Yuetang Deng）、华为、小米等公司的支持。致敬！

[^1]: 许多 UI 自动化测试工具提供“自定义事件序列”功能（如[Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和 [AppCrawler](https://github.com/seveniruby/AppCrawler)），但实际使用中存在诸多问题，如自定义能力受限、使用不灵活等。此前不少 Fastbot 用户抱怨其“自定义事件序列”功能存在问题，见[#209](https://github.com/bytedance/Fastbot_Android/issues/209), [#225](https://github.com/bytedance/Fastbot_Android/issues/225), [#286](https://github.com/bytedance/Fastbot_Android/issues/286)等。

[^2]: 支持自动断言功能在 UI 自动化测试中非常重要，但几乎无测试工具具备此能力。我们注意到[AppCrawler](https://ceshiren.com/t/topic/15801/5)开发者曾希望实现断言机制，得到用户热烈响应，许多用户自2021年起持续催促，但始终未实现。