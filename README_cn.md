[![PyPI](https://img.shields.io/pypi/v/kea2-python.svg)](https://pypi.python.org/pypi/kea2-python)
[![PyPI Downloads](https://static.pepy.tech/badge/kea2-python)](https://pepy.tech/projects/kea2-python)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)


<div>
    <img src="https://github.com/user-attachments/assets/aa5839fc-4542-46f6-918b-c9f891356c84" style="border-radius: 14px; width: 20%; height: 20%;"/> 
</div>
## 关于

Kea2是一个易于使用的Python库，用于支持、定制和改进移动应用的自动化UI测试。Kea2的创新之处在于能够将人工编写的脚本与自动化UI测试工具相融合，从而实现许多有趣且强大的功能。

Kea2目前基于[Fastbot](https://github.com/bytedance/Fastbot_Android)和[uiautomator2](https://github.com/openatx/uiautomator2)构建，并针对[Android](https://en.wikipedia.org/wiki/Android_(operating_system))应用。

## 重要特性
- **特性1**(查找稳定性问题): 具备[Fastbot](https://github.com/bytedance/Fastbot_Android)的全部压力测试能力，可发现*稳定性问题*（即*崩溃性错误*）；  

- **特性2**(自定义测试场景\事件序列\黑白名单\黑白控件[^1]): 运行Fastbot时可自定义测试场景（例如：测试特定应用功能、执行特定事件序列、进入特定UI页面、到达特定应用状态、屏蔽特定活动/UI控件/UI区域），借助*python*语言和[uiautomator2](https://github.com/openatx/uiautomator2)实现完整能力与灵活性；  

- **特性3**(支持断言机制[^2]): 运行Fastbot时支持自动断言，基于继承自[Kea](https://github.com/ecnusse/Kea)的[基于性质的测试](https://en.wikipedia.org/wiki/Software_testing#Property_testing)理念，用于发现*逻辑性错误*（即*非崩溃性错误*）  

**Kea2三大特性能力对比**  
|  | **特性1** | **特性2** | **特性3** |  
| --- | --- | --- | ---- |  
| **发现崩溃问题** | :+1: | :+1: | :+1: |  
| **发现深层状态崩溃** |  | :+1: | :+1: |  
| **发现非崩溃性功能（逻辑）错误** |  |  | :+1: |  


<div align="center">  
    <div style="max-width:80%; max-height:80%">  
    <img src="docs/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/>   
    </div>  
</div>  
## 设计与路线图  
Kea2作为Python库发布，当前支持：  
- 测试框架：[unittest](https://docs.python.org/3/library/unittest.html)；  
- UI测试驱动：[uiautomator2](https://github.com/openatx/uiautomator2)；  
- 后端自动化UI测试工具：[Fastbot](https://github.com/bytedance/Fastbot_Android)。  

未来计划扩展支持：  
- [pytest](https://docs.pytest.org/en/stable/)  
- [Appium](https://github.com/appium/appium)、[Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines)（适配HarmonyOS/Open Harmony）  
- 其他自动化UI测试工具（不限于Fastbot）

## 安装

运行环境：
- 支持 Windows、MacOS 和 Linux
- python 3.8+，Android 5.0+（需安装 Android SDK）
- **关闭 VPN**（功能2和3需要）

通过 `pip` 安装 Kea2：
```bash
python3 -m pip install kea2-python
```

查看 Kea2 的选项：
```bash
kea2 -h
```

## 快速测试

Kea2 需连接并在 Android 设备上运行。建议先进行快速测试以确保 Kea2 与您的设备兼容。

1. 连接一台真实 Android 设备或模拟器（只需一台），并通过运行 `adb devices` 确认设备已连接。

2. 运行 `quicktest.py` 测试示例应用 `omninotes`（该应用以 `omninotes.apk` 形式发布在 Kea2 的代码库中）。脚本 `quicktest.py` 会自动安装并短时间测试该应用。

在您的工作目录下初始化 Kea2：
```python
kea2 init
```

> 首次运行 Kea2 时必须执行此步骤。

运行快速测试：
```python
python3 quicktest.py
```

若能看到应用 `omninotes` 成功运行并完成测试，说明 Kea2 工作正常！
否则，请协助[提交错误报告](https://github.com/ecnusse/Kea2/issues)并提供错误信息。感谢！

## Feature 1(运行基础版Fastbot：查找稳定性错误)

使用Fastbot的全部功能对您的应用进行压力测试，以发现*稳定性问题*（即*崩溃错误*）；


```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent native --running-minutes 10 --throttle 200
```

理解上述选项含义请查看[文档](docs/manual_en.md#launching-kea2)

> 用法与原始Fastbot的[shell命令](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command)类似。

查看更多选项：
```bash
kea2 run -h
```
## Feature 2(运行增强版Fastbot：自定义测试场景\事件序列\黑白控件)

当运行Fastbot等自动化UI测试工具测试您的应用时，您可能会发现某些特定的UI页面或功能难以到达或覆盖。原因是Fastbot缺乏对您应用的了解。幸运的是，这正是脚本测试的优势所在。在Feature 2中，Kea2支持编写小型脚本来引导Fastbot探索我们想要测试的任何地方。您还可以使用此类小脚本在UI测试期间屏蔽特定控件。

在Kea2中，脚本由两个要素组成：
-  **前置条件（Precondition）：** 何时执行脚本。
- **交互场景（Interaction scenario）：** 到达目标所需的交互逻辑（在脚本的测试方法中指定）。

### 简单示例

假设在自动化UI测试中，`Privacy`是一个难以到达的UI页面。Kea2可以轻松引导Fastbot到达该页面。

```python
    @prob(0.5)
    # precondition: when we are at the page `Home`
    @precondition(lambda self: 
        self.d(text="Home").exists
    )
    def test_goToPrivacy(self):
        """
        Guide Fastbot to the page `Privacy` by opening `Drawer`, 
        clicking the option `Setting` and clicking `Privacy`.
        """
        self.d(description="Drawer").click()
        self.d(text="Settings").click()
        self.d(text="Privacy").click()
```

- 通过装饰器`@precondition`，我们指定了前置条件——当处于`Home`页面时。  
  在此情况下，`Home`页面是`Privacy`页面的入口页面，且Fastbot可以轻松到达`Home`页面。因此，脚本会在处于`Home`页面时（通过检查是否存在唯一控件`Home`）被激活。  
- 在脚本的测试方法`test_goToPrivacy`中，我们指定了交互逻辑（即打开`Drawer`、点击选项`Setting`并点击`Privacy`）以引导Fastbot到达`Privacy`页面。  
- 通过装饰器`@prob`，我们指定了在处于`Home`页面时执行引导的概率（本例中为50%）。因此，Kea2仍允许Fastbot探索其他页面。  

完整示例可在脚本`quicktest.py`中找到，并通过以下命令与Fastbot一起运行该脚本：  

```bash
# 启动Kea2并加载单个脚本quicktest.py。
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --agent u2 --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
```

## Feature 3(运行增强版Fastbot：加入自动断言)

Kea2支持在运行Fastbot时加入自动断言功能，用于发现*逻辑错误*（即*非崩溃性错误*）。为此，您可以在脚本中添加断言语句。当自动化UI测试过程中断言失败时，就意味着可能发现了功能性问题。

Feature 3中的脚本包含三个核心要素：

- **前置条件:** 脚本执行的触发条件
- **交互场景:** 交互逻辑（通过脚本的测试方法定义）
- **断言:** 预期的应用行为表现

### 示例

以社交应用为例，消息发送是常见功能。在消息发送页面，当输入框非空（即包含消息内容）时，`send`按钮应当始终可见。

<div align="center" >
    <div >
        <img src="docs/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
    </div>
    <p>预期行为（上图）与异常行为（下图）对比<p/>
</div>

针对上述始终成立的性质，我们可以编写以下脚本来验证功能正确性：当消息发送页面存在`input_box`控件时，向输入框键入任意非空字符串文本后，断言`send_button`必须存在。

```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()
        self.d(description="input_box").set_text(random_str)
        assert self.d(description="send_button").exist

        # 还可扩展更多断言，例如：
        #       输入字符串应在消息发送页面显示
        assert self.d(text=random_str).exist
```
>  我们使用[hypothesis](https://github.com/HypothesisWorks/hypothesis)生成随机文本。

运行此示例的命令行与Feature 2类似。

## 文档（更多文档）

[更多文档](docs/manual_en.md)，包括了：
- Kea2的案例教程（基于微信介绍）、
- Kea2脚本的定义方法，支持的脚本装饰器(如`@precondition`、`@prob`、`@max_tries`)、
- Kea2的启动方式、命令行选项
- 查看/理解Kea2的运行结果（如界面截图、测试覆盖率、脚本执行成功与否）。
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

Kea2由[ecnusse](https://github.com/ecnusse)成员积极开发和维护：

- [Xixian Liang](https://xixianliang.github.io/resume/) ([@XixianLiang][])
- Bo Ma ([@majuzi123][])
- Chen Peng ([@Drifterpc][])
- [Ting Su](https://tingsu.github.io/) ([@tingsu][])

[@XixianLiang]: https://github.com/XixianLiang
[@majuzi123]: https://github.com/majuzi123
[@Drifterpc]: https://github.com/Drifterpc
[@tingsu]: https://github.com/tingsu

[Zhendong Su](https://people.inf.ethz.ch/suz/), [Yiheng Xiong](https://xyiheng.github.io/), [Xiangchen Shen](https://xiangchenshen.github.io/), [Mengqian Xu](https://mengqianx.github.io/), [Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp), [Jingling Sun](https://jinglingsun.github.io/), [Jue Wang](https://cv.juewang.info/) 也积极参与了本项目并作出重要贡献！

Kea2还获得了来自字节跳动（Fastbot团队的[Zhao Zhang](https://github.com/zhangzhao4444)、Yuhui Su）、OPay（Tiesong Liu）、微信（Haochuan Lu、Yuetang Deng）、华为、小米等业界人士的宝贵见解、建议和反馈。特此致谢！

[^1]: 不少UI自动化测试工具提供了“自定义事件序列”能力（如[Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和[AppCrawler](https://github.com/seveniruby/AppCrawler)），但在实际使用中存在不少问题，如自定义能力有限、使用不灵活等。此前不少Fastbot用户抱怨过其“自定义事件序列”在使用中的问题，如[#209](https://github.com/bytedance/Fastbot_Android/issues/209), [#225](https://github.com/bytedance/Fastbot_Android/issues/225), [#286](https://github.com/bytedance/Fastbot_Android/issues/286)等。

[^2]: 在UI自动化测试过程中支持自动断言是一个很重要的能力，但几乎没有测试工具提供这样的能力。我们注意到[AppCrawler](https://ceshiren.com/t/topic/15801/5)的开发者曾经希望提供一种断言机制，得到了用户的热切响应，不少用户从21年就开始催更，但始终未能实现。