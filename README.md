

[![PyPI](https://img.shields.io/pypi/v/kea2-python.svg)](https://pypi.python.org/pypi/kea2-python)
[![PyPI Downloads](https://static.pepy.tech/badge/kea2-python)](https://pepy.tech/projects/kea2-python)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ecnusse/Kea2)

<div>
    <img src="https://github.com/user-attachments/assets/8d9f8750-1e10-411b-a49f-7d8367bbe9fe" style="border-radius: 14px; width: 20%; height: 20%;"/> 
</div>


Please contact Xixian Liang at [xixian@stu.ecnu.edu.cn](xixian@stu.ecnu.edu.cn) with your Wechat ID / QR code to be invited to the WeChat discussion group. Of course, we are also ready on GitHub to answer your questions/feedback.

####  Github repo [https://github.com/ecnusse/Kea2](https://github.com/ecnusse/Kea2)
####  Gitee mirror [https://gitee.com/XixianLiang/Kea2](https://gitee.com/XixianLiang/Kea2)




### [点击此处：查看中文文档](README_cn.md) 

## About 

<div align="center">
    <img src="docs/images/kea2_logo.png" alt="kea_logo" style="border-radius: 14px; width: 20%; height: 20%;"/>
</div>
<div align="center">
    <a href="https://en.wikipedia.org/wiki/Kea">Kea2's logo: A large parrot skilled in finding "bugs"</a>
</div>
</br>

Kea2 is an easy-to-use tool for fuzzing mobile apps. Its key *novelty* is able to fuse automated UI testing with scripts (usually written by human), thus empowering automated UI testing with human intelligence for effectively finding *crashing bugs* as well as *non-crashing functional (logic) bugs*. 

Kea2 is currently built on top of [Fastbot](https://github.com/ecnusse/Fastbot_Android) 3.0 (a modified/enhanced version of the original [FastBot](https://github.com/bytedance/Fastbot_Android) 2.0), *an industrial-strength automated UI testing tool from ByteDance*, and [uiautomator2](https://github.com/openatx/uiautomator2), *an easy-to-use and stable Android automation library*. 
Kea2 currently targets [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) apps. 

## Novelty & Important features

<div align="center">
    <div style="max-width:80%; max-height:80%">
    <img src="docs/images/intro.png" style="border-radius: 14px; width: 80%; height: 80%;"/> 
    </div>
</div>

- **Feature 1**(查找稳定性问题): coming with the full capability of [Fastbot](https://github.com/bytedance/Fastbot_Android) for stress testing and finding *stability problems* (i.e., *crashing bugs*); 

- **Feature 2**(自定义测试场景\事件序列\黑白名单\黑白控件[^1]): customizing testing scenarios when running Fastbot (e.g., testing specific app functionalities, executing specific event traces, entering specifc UI pages, reaching specific app states, blacklisting specific activities/UI widgets/UI regions) with the full capability and flexibility powered by *python* language and [uiautomator2](https://github.com/openatx/uiautomator2);

- **Feature 3**(支持断言机制[^2]): supporting auto-assertions when running Fastbot, based on the idea of [property-based testing](https://en.wikipedia.org/wiki/Software_testing#Property_testing) inheritted from [Kea](https://github.com/ecnusse/Kea), for finding *logic bugs* (i.e., *non-crashing functional bugs*).

    For **Feature 2 and 3**, Kea2 allows you to focus on what app functionalities to be tested. You do not need to worry about how to reach these app functionalities. Just let Fastbot help. As a result, your scripts are usually short, robust and easy to maintain, and the corresponding app functionalities are much more stress-tested!

**The ability of the three features in Kea2**

|                                                  | **Feature 1** | **Feature 2** | **Feature 3** |
| ------------------------------------------------ | ------------- | ------------- | ------------- |
| **Finding crashes**                              | :+1:          | :+1:          | :+1:          |
| **Finding crashes in deep states**               |               | :+1:          | :+1:          |
| **Finding non-crashing functional (logic) bugs** |               |               | :+1:          |

## Kea2's Users

Kea2 (and its idea) has been used/integrated by

- [OPay Business](https://play.google.com/store/apps/details?id=team.opay.pay.merchant.service) --- a financial & payment app (2 millions of active users daily). OPay uses Kea2 for regression testing on POS machines and mobile devices.

- [WeChat's iExplorer]() --- WeChat's in-house testing platform (coming with an interactive UI-based tool to ease writing scripts)

- [WeChat Payment's UAT]() --- WeChat Payment's in-house testing platform (fully automated property-based testing by synthesizing properties from the system specifications)

- [DevEco Testing](https://developer.huawei.com/consumer/cn/deveco-testing/) --- Huawei's Official Testing Platform for HarmonyOS (Kea2 is built upon Hypium)

- [ByteDance's Fastbot](https://github.com/bytedance/Fastbot_Android)

Please let us know and willing to hear your feedback/questions if you are also using Kea2.

## Design & Roadmap
Kea2 currently works with:
- [unittest](https://docs.python.org/3/library/unittest.html) as the testing framework to manage the scripts;
- [uiautomator2](https://github.com/openatx/uiautomator2) as the UI test driver; 
- [Fastbot](https://github.com/bytedance/Fastbot_Android) as the backend automated UI testing tool. 

In the future, Kea2 will be extended to support
- [pytest](https://docs.pytest.org/en/stable/), another popular python testing framework;
- [Appium](https://github.com/appium/appium), [Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines) (for HarmonyOS/Open Harmony);
- any other automated UI testing tools (not limited to Fastbot)


## Installation

Running environment:
- support Windows, MacOS and Linux
- python 3.8+, Android 5.0~16.0 (Android SDK installed)
- **VPN closed** (Features 2 and 3 required)

Install Kea2 by `pip`:
```bash
python3 -m pip install kea2-python
```

Find Kea2's options by running 
```bash
kea2 -h
```

Upgrade Kea2 to its latest version if you already installed Kea2 before:
```bash
python3 -m pip install -U kea2-python
```
> If you're using mirror sites like Tsinghua or USTC, you may fail to upgrade. Because these sites may not have the latest version yet. In this case, you can try to install Kea2 by specifying the latest version manually, or use `pypi.org` directly by `pip install kea2-python -i https://pypi.org/simple`.

Upgrade Kea2 to the specifc latest version (e.g., 1.0.0) if you already installed Kea2 before:
```bash
python3 -m pip install -U kea2-python==1.0.0
```

Initialize Kea2 under your preferred working directory:
```python
kea2 init
```

> This initialization step is always needed if it is your first time to run Kea2. If you have upgraded Kea2, you are also recommended to rerun this step to ensure any potential new configurations of Kea2 would take effect.


## Quick Test

Kea2 connects to and runs on Android devices. We recommend you to do a quick test to ensure that Kea2 is compatible with your devices.

1. Connect to a real Android device or an Android emulator and make sure you can see the connected device by running `adb devices`. 

2. Run `quicktest.py` to test a sample app `omninotes` (released as `omninotes.apk` in Kea2's repository). The script `quicktest.py` will automatically install and test this sample app for a short time.

Run the quick test:
```bash
python3 quicktest.py
```

> This quick test would automatically download `omninotes.apk`. If the download fails, please copy `omninotes.apk` from Kea2's repository (top-level) to your working directory and execute the quick test command again.

If you can see the app `omninotes` is successfully running and tested, Kea2 works!
Otherwise, please help [file a bug report](https://github.com/ecnusse/Kea2/issues) with the error message to us. Thank you!



## Feature 1(运行基础版Fastbot：查找稳定性错误)

Test your app with the full capability of Fastbot for stress testing and finding *stability problems* (i.e., *crashing bugs*); 

```bash
kea2 run -p it.feio.android.omninotes.alpha --running-minutes 10 --throttle 200
```

To understand the meanings of the options, you can see our [user manual](docs/manual_en.md#launching-kea2).

> The usage is similar to the the original Fastbot's [shell commands](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command). 

See more options by 
```bash
kea2 run -h
```

## Feature 2(运行增强版Fastbot：自定义测试场景\事件序列\黑白控件)

When running any automated UI testing tools like Fastbot to test your apps, you may find that some specifc UI pages or functionalities are difficult to reach or cover. The reason is that Fastbot lacks knowledge of your apps. Fortunately, this is the strength of script testing. In Feature 2, Kea2 can support writing small scripts to guide Fastbot to explore wherever we want. You can also use such small scripts to block specific widgets during UI testing.

In Kea2, a script is composed of two elements:
-  **Precondition:** When to execute the script.
- **Interaction scenario:** The interaction logic (specified in the script's test method) to reach where we want.

### Simple Example

Assuming `Privacy` is a hard-to-reach UI page during automated UI testing. Kea2 can easily guide Fastbot to reach this page.

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

- By the decorator `@precondition`, we specify the precondition --- when we are at the `Home` page. 
In this case, the `Home` page is the entry page of the `Privacy` page and the `Home` page can be easily reached by Fastbot. Thus, the script will be activated when we are at `Home` page by checking whether a unique widget `Home` exists. 
- In script's test method `test_goToPrivacy`, we specify the interaction logic (i.e., opening `Drawer`, clicking the option `Setting` and clicking `Privacy`) to guide Fastbot to reach the `Privacy` page.
- By the decorator `@prob`, we specify the probability (50% in this example) to do the guidance when we are at the `Home` page. As a result, Kea2 still allows Fastbot to explore other pages.

You can find the full example in script `quicktest.py`, and run this script with Fastbot by the command `kea2 run`:

```bash
# Launch Kea2 and load one single script quicktest.py.
kea2 run -p it.feio.android.omninotes.alpha --running-minutes 10 --throttle 200 --driver-name d propertytest discover -p quicktest.py
```

## Feature 3(运行增强版Fastbot：加入自动断言)

Kea2 supports auto-assertions when running Fastbot for finding *logic bugs* (i.e., *non-crashing bugs*). To achieve this, you can add assertions in the scripts. When an assertion fails during automated UI testing, we find a likely functional bug. 

In Feature 3, a script is composed of three elements:

- **Precondition:** When to execute the script.
- **Interaction scenario:** The interaction logic (specified in the script's test method).
- **Assertion:** The expected app behaviour.

### Example

In a social media app, message sending is a common feature. On the message sending page, the `send` button should always appears when the input box is not empty (i.e., has some message).

<div align="center">
    <img src="docs/images/socialAppBug.png" style="border-radius: 14px; width:30%; height:40%;"/>
</div>

<div align="center">
    The expected behavior (the upper figure) and the buggy behavior (the lower figure).
</div>
​    

For the preceding always-holding property, we can write the following script to validate the functional correctness: when there is an `input_box` widget on the message sending page, we can type any non-empty string text into the input box and assert `send_button` should always exists.


```python
    @precondition(
        lambda self: self.d(description="input_box").exists
    )
    def test_input_box(self):

        # genenerate a random non-empty string (this is also property-based testing
        #                                       by feeding random text inputs!)
        from hypothesis.strategies import text, ascii_letters
        random_str = text(alphabet=ascii_letters).example()

        # input this non-empty string into the input box 
        self.d(description="input_box").set_text(random_str)

        # check whether the send button exists
        assert self.d(description="send_button").exist

        # we can even do more assertions, e.g.,
        #       the input string should successfully appear on the message sending page
        assert self.d(text=random_str).exist
```
>  We use [hypothesis](https://github.com/HypothesisWorks/hypothesis) to generate random texts.

You can run this example by using the similar command line in Feature 2.

## Feature 4(兼容已有脚本：通过前置脚本步骤到达特定层次)

Kea2 supports reusing existing Ui test Scripts. We are inspired by the idea that: *The existing Ui test scripts usually cover important app functionalities and can reach deep app states. Thus, they can be used as good "guiding scripts" to drive Fastbot to explore important and deep app states.*

For example, you may already have some existing Ui test scripts "login and add a friend", This feature allows you to use the existing script, set some breakpoints (i.e., interruptable points) in the script, and launch Fastbot to explore the app after every breakpoint. By using this feature, you can do the login first and then launch Fastbot to explore the app after login. Which helps Fastbot to explore deep app states. (fastbot can't do login by itself easily).

### Example

Here are four example scripts in hybridetest_examples, each corresponding to different forms of user scripts, showing you how to launch kea2 in the existing code.

Specifically:  

* [u2_unittest_example.py](hybridtest_examples\u2_unittest_example.py) is a u2 script organized with unittest.
* [u2_pytest_example.py](hybridtest_examples\u2_pytest_example.py) is a u2 script organized with pytest.
* [appium_unittest_example.py](hybridtest_examples\appium_unittest_example.py) is an appium script organized with unittest.
* [appium_pytest_example.py](hybridtest_examples\appium_pytest_example.py) is an appium script organized with pytest.

Some notes:

1. You can control whether to execute the kea2-related code you have written by modifying the condition of 'if'. This allows you to easily enable or disable kea2 operations in the same script. Here we use environment variable as an example.
2. Since kea2 is driven by u2, if an appium-written script wants to launch kea2, it is necessary to first close the appium session. Remember to configure the parameter `"noReset": True` in `desired_caps` to avoid resetting the application when closing the session.
3. You need to insert the following code template into your existing test cases: Here, you can add your own hook logic in the commented sections, including starting or stopping the appium session, cleaning up instances, etc. This depends on how you want to design the setup and teardown. Apart from that, you only need to configure the `option` parameter and `configs_path` parameter(where your directory `configs` located, btw, `configs`'s location dependon where you executed `kea2 init`), then pass it to the `run_kea2_testing` function.

```python
from kea2 import Kea2Tester, Options, U2Driver

if os.environ.get('KEA2_HYBRID_MODE', '').lower() == 'true': 
    '''
    Note: The if condition here can be modified as needed according to the actual 
    situation of the project, the form of environment variables is just an example.    
    '''

    # close your driver session etc. here
    # ...
    
    tester = Kea2Tester()
    result = self.tester.run_kea2_testing(
        Options(
            driverName="d",
            packageNames=[PACKAGE_NAME],
            propertytest_args=["discover", "-p", "Omninotes_Sample.py"],
            serial=DEVICE_SERIAL,
            running_mins=2,
            maxStep=20
        ),
        configs_path = None  # Default, if your configs folder is located in the root directory, miss this.           
    )
    
    # restart your driver session or clean instance here
    # ...
    
    return  # this make your following steps of this testcase not work
```



## Test Reports（测试报告）

Kea2 automatically generates a HTML test report after each testing session. You can find the report in `output/` under your working directory.

You can also manually generate the test report by `kea2 report` (see `kea2 report -h` for details).

You can also merge the test report from multiple testing sessions by `kea2 merge` (see `kea2 merge -h` for details).
The merged test report is quite useful if you would test your apps for multiple sessions.

You can find a sample [test report](https://ecnusse.github.io/Kea2_sample_report/) from Opay (Thank you!). You can find more details on the test report in [this documentation](docs/test_report_introduction.md).

## Documentations（更多文档）


### :blue_book: [User Manual](docs/manual_en.md) (Important!)
You can find the [user manual](docs/manual_en.md), which includes:
- Examples of using Kea2 on WeChat (in Chinese);
- How to define Kea2's scripts and use the decorators (e.g., `@precondition`、`@prob`、`@max_tries`);
- How to run Kea2 and Kea2's command line options
- How to find and understand Kea2's testing results
- How to [whitelist or blacklist](docs/blacklisting.md) specific activities, UI widgets and UI regions during fuzzing

### Other resources about Kea2 (in Chinese)
- [Q&A for Kea2 and PBT (对Kea2和PBT技术的常见问题和回答)](https://sy8pzmhmun.feishu.cn/wiki/SLGwwqgzIiEuC3kwmV8cSZY0nTg?from=from_copylink) 
- [Kea2 101 (Kea2 从0到1 的入门教程与最佳实践，建议新手阅读)](https://sy8pzmhmun.feishu.cn/wiki/EwaWwPCitiUJoBkIgALcHtglnDK?from=from_copylink)
- [Kea2 分享交流会 (2025.09, bilibili 录播)](https://www.bilibili.com/video/BV1CZYNz9Ei5/)
- [Kea2 工具快速介绍 (2025.11, bilibili 录播)](https://www.bilibili.com/video/BV1WAyUBDEMw/)

Some blogs on Kea/Kea2 (in Chinese):
- [别再苦哈哈写测试脚本了，生成它们吧！(一)](https://mp.weixin.qq.com/s/R2kLCkXpDjpa8wCX4Eidtg)
- [别再苦哈哈写测试脚本了，生成它们吧！(二)](https://mp.weixin.qq.com/s/s4WkdstNcKupu9OP8jeOXw)
- [别再苦哈哈写测试脚本了，生成它们吧！(三)](https://mp.weixin.qq.com/s/BjXyo-xJRmPB_sCc4pmh8g)
- [2025 Let’s GoSSIP 软件安全暑期学校预告第一弹——Kea2](https://mp.weixin.qq.com/s/8_0_GNNin8E5BqTbJU33wg)
- [功能性质驱动的测试技术：下一代GUI自动化测试技术](https://appw8oh6ysg4044.xet.citv.cn/p/course/video/v_6882fa14e4b0694ca0ec0a1b) --- 视频回放&PPT@MTSC 2025

工业界对Kea2的理解和评价（点击箭头查看详情）：

<details>
  <summary>Kea2的性质是什么含义？Kea2意义和价值是什么？</summary>

    kea2 其实是一个工具，它是python+u2+fastbot的集合体。 它本身更像是一台装好了发动机和轮子的汽车底盘。
    
    性质是苏老师他们团队提出的一个概念， 转换到测试领域的实际工作中，性质对应的是最小单位的功能（原子级功能），性质的依赖条件很少或没有，它可以自身运行。一个典型的性质就是登录，它仅仅具有输入用户名，输入密码，提交。再举个例子，给视频点个赞，也就是简单的两三步。就是一个性质。
    
    性质与kea2结合的意义是在于解决过去使用appium过重的问题。用appium去测试一个性质通常要写很多行的代码，引导界面到达性质的位置。但使用kea2，就只需要编写性质，如何到其所在的位置是交给fastbot和它的学习算法来搞定的。 
    
    kea2另个重大的价值是，它解决了上述思想所需要的技术支撑，比appium更轻量的UI编写方式，fastbot编写性质的能力不足，以及无法编写逻辑和断言。整体上是保留了fastbot以往的优秀品质，完善了其不足和短板。
    
    简而言之，需要做传统的编排型的功能测试，仍然使用appium，使用kea2也行，但你感觉不到它的价值。本身有需要做混沌测试，模糊测试，兼容性测试。那么强烈，强烈推荐kea2。kea2更偏探索性测试而非编排型。
</details>

<details>
  <summary>kea2组成是什么？kea2的核心作用？kea2做了什么？</summary>

kea2 组成：

    fastbot  --  fuzz测试引擎，负责跑路。
    u2 -- 负责进行业务空间的操作。与使用selenium，appium，没什么区别。
    python --  u2的操作，逻辑的编写，定制化的实现。

kea2的核心作用：

    提供了条件触发器。 在FB跑路的时候，会不停遍历条件触发器，一旦触发，挂起FB，开始执行触发器指定的 ui test 及 assert。执行完毕，继续切回FB跑路。

kea2做了什么：

    替换了FB的条件触发功能。
    替换了FB的黑名单，黑控件功能。
    替换了FB剪枝功能。
    增加了多元化的元素空间操作能力。
    增加了fuzz测试中的 逻辑设定。
    增加了断言能力。
    增加了元素操作能力。
</details>


## Open-source projects used by Kea2

- [Fastbot](https://github.com/bytedance/Fastbot_Android)
- [uiautomator2](https://github.com/openatx/uiautomator2)
- [hypothesis](https://github.com/HypothesisWorks/hypothesis)

## Relevant papers of Kea2

> General and Practical Property-based Testing for Android Apps. ASE 2024. [pdf](https://dl.acm.org/doi/10.1145/3691620.3694986)

> An Empirical Study of Functional Bugs in Android Apps. ISSTA 2023. [pdf](https://dl.acm.org/doi/10.1145/3597926.3598138)

> Fastbot2: Reusable Automated Model-based GUI Testing for Android Enhanced by Reinforcement Learning. ASE 2022. [pdf](https://dl.acm.org/doi/10.1145/3551349.3559505)

> Guided, Stochastic Model-Based GUI Testing of Android Apps. ESEC/FSE 2017.  [pdf](https://dl.acm.org/doi/10.1145/3106237.3106298)

## Maintainers/Contributors

Kea2 has been actively developed and maintained by the people in [ecnusse](https://github.com/ecnusse):

- [Xixian Liang](https://xixianliang.github.io/resume/) ([@XixianLiang][])
- [Bo Ma](https://github.com/majuzi123) ([@majuzi123][])
- [Cheng Peng](https://github.com/Drifterpc) ([@Drifterpc][])
- [Ting Su](https://tingsu.github.io/) ([@tingsu][])

[@XixianLiang]: https://github.com/XixianLiang
[@majuzi123]: https://github.com/majuzi123
[@Drifterpc]: https://github.com/Drifterpc
[@tingsu]: https://github.com/tingsu

[Zhendong Su](https://people.inf.ethz.ch/suz/), [Yiheng Xiong](https://xyiheng.github.io/), [Xiangchen Shen](https://xiangchenshen.github.io/), [Mengqian Xu](https://mengqianx.github.io/), [Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp), [Jingling Sun](https://jinglingsun.github.io/), [Jue Wang](https://cv.juewang.info/), [Geguang Pu]() have also been actively participated in this project and contributed a lot!

Kea2 has also received many valuable insights, advices, feedbacks and lessons shared by several industrial people from Bytedance ([Zhao Zhang](https://github.com/zhangzhao4444), Yuhui Su from the Fastbot team), OPay (Tiesong Liu), WeChat (Haochuan Lu, Yuetang Deng), Huawei, Xiaomi and etc. Kudos!

### Become a Contributor!

Kea2 is an open-source project and we are calling for more contributors to join us!

See [Developer guide](DEVELOP.md) for more details.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ecnusse/Kea2&type=Date)](https://www.star-history.com/#ecnusse/Kea2&Date)

[^1]: 不少UI自动化测试工具提供了“自定义事件序列”能力（如[Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) 和[AppCrawler](https://github.com/seveniruby/AppCrawler)），但在实际使用中存在不少问题，如自定义能力有限、使用不灵活等。此前不少Fastbot用户抱怨过其“自定义事件序列”在使用中的问题，如[#209](https://github.com/bytedance/Fastbot_Android/issues/209), [#225](https://github.com/bytedance/Fastbot_Android/issues/225), [#286](https://github.com/bytedance/Fastbot_Android/issues/286)等。

[^2]: 在UI自动化测试过程中支持自动断言是一个很重要的能力，但几乎没有测试工具提供这样的能力。我们注意到[AppCrawler](https://ceshiren.com/t/topic/15801/5)的开发者曾经希望提供一种断言机制，得到了用户的热切响应，不少用户从21年就开始催更，但始终未能实现。 
