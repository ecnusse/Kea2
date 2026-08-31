<div align="center">

[![PyPI](https://img.shields.io/pypi/v/kea2-python.svg)](https://pypi.python.org/pypi/kea2-python)
[![PyPI Downloads](https://static.pepy.tech/badge/kea2-python)](https://pepy.tech/projects/kea2-python)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ecnusse/Kea2)

[<img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white" />](https://github.com/ecnusse/Kea2)
[<img src="https://img.shields.io/badge/Gitee-333333?style=for-the-badge&logo=gitee&logoColor=white" />](https://gitee.com/XixianLiang/Kea2) 

**English | [简体中文](/README_cn.md)**

</br>

<img src="docs/images/kea2_logo.png" alt="kea_logo" style="border-radius: 14px; width: 20%; height: 20%;"/>

<a href="https://en.wikipedia.org/wiki/Kea">Kea2's logo: A large parrot skilled in finding "bugs"</a>

</div>
</br>

### [:blue_book: User Manual](/docs/manual_en.md) | [:blue_book: 用户手册](/docs/manual_cn.md)

## About 

Kea2 is an easy-to-use tool for fuzzing mobile apps. Its key *novelty* is able to fuse automated UI testing with scripts (usually written by human), thus empowering automated UI testing with human intelligence for effectively finding *crashing bugs* as well as *non-crashing functional (logic) bugs*. 

Kea2 is currently built on top of [Fastbot 3.0](https://github.com/ecnusse/Fastbot_Android) (a modified/enhanced version of the original [FastBot 2.0](https://github.com/bytedance/Fastbot_Android)), *an industrial-strength automated UI testing tool from ByteDance*, and [uiautomator2](https://github.com/openatx/uiautomator2), *an easy-to-use and stable Android automation library*. 
Kea2 currently targets [Android](https://en.wikipedia.org/wiki/Android_(operating_system)) apps. 


https://github.com/user-attachments/assets/6120d8f5-5a9d-4ead-b27e-840c8757e28e




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

<div align="center">
<table>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/f4eefbe3-1a4c-4a6e-acca-b97d35e34487" alt="Huawei" width="180"></td>
    <td><img src="https://github.com/user-attachments/assets/c8da7eb1-c7bd-4fc8-ac7c-ee241168566c" alt="WeChat Pay" width="180"></td>
    <td><img src="https://github.com/user-attachments/assets/741f7796-c3d7-47c1-b79a-933c0a241613" alt="ByteDance" width="180"></td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/cef587b2-0142-40ed-91f0-baf087d0a03a" alt="WeChat" width="180"></td>
    <td><img src="https://github.com/user-attachments/assets/8334d717-c9d2-4fda-ad9b-611fa37935b4" alt="OPay" width="180"></td>
    <td><img src="https://github.com/user-attachments/assets/b93a09b0-2cb6-4ae9-8239-cf7efe5f8499" alt="Xiaomi" width="180"></td>
  </tr>
</table>
</div>

- [DevEco Studio](https://developer.huawei.com/consumer/cn/deveco-studio/) --- Huawei's IDE for HarmonyOS, leveraging Kea2 to power its internal quality assessment tool, AppAnalyzer.

- [WeChat Payment's UAT]() --- WeChat Payment's in-house testing platform (fully automated property-based testing by synthesizing properties from the system specifications)

- [ByteDance's Fastbot](https://github.com/bytedance/Fastbot_Android)

- [WeChat's iExplorer]() --- WeChat's in-house testing platform (coming with an interactive UI-based tool to ease writing scripts)

- [OPay Business](https://play.google.com/store/apps/details?id=team.opay.pay.merchant.service) --- a financial & payment app (20 millions of active users daily). OPay uses Kea2 for regression testing on POS machines and mobile devices.

- [Xiaomi]() --- Integrate Kea2 with pytest to turn it into a standalone plugin within Xiaomi's internal toolchain, and use it in conjunction with their automated exploration testing tool.

[**👉 Click here to see how users are using Kea2**](docs/user_cases_en.md)

Please let us know and willing to hear your feedback/questions if you are also using Kea2.

## Design & Roadmap

**Kea2 currently works with 3 open-sourced projects:**
- [unittest](https://docs.python.org/3/library/unittest.html) as the testing framework to manage the scripts;
- [uiautomator2](https://github.com/openatx/uiautomator2) as the UI test driver; 
- [Fastbot](https://github.com/bytedance/Fastbot_Android) as the backend automated UI testing tool.

Several key features of Kea2 are inspired by **[Hypothesis](https://github.com/HypothesisWorks/hypothesis)**, the property-based testing framework for Python.

**In the future, Kea2 will be extended to support:**
- [pytest](https://docs.pytest.org/en/stable/), another popular python testing framework;
- [Appium](https://github.com/appium/appium), [Hypium](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/hypium-python-guidelines) (for HarmonyOS/Open Harmony);
- any other automated UI testing tools (not limited to Fastbot)


## Installation

Running environment:
- support Windows, MacOS and Linux
- python 3.8+, Android 5.0~16.0 (Android SDK installed)
- **Disable localhost proxy** (some VPNs affect u2). Set it to bypass `localhost` or turn off the VPN if needed. (Required for Features 2 and 3.)

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



## Feature 1 (Find crashes with the full capability of Fastbot and get kea2 test reports)

Test your app with the full capability of Fastbot for stress testing and finding *stability problems* (i.e., *crashing bugs*); 
Meanwhile, you can get test reports generated by Kea2 to understand app behaviors and discovered bugs during testing.

```bash
kea2 run -p it.feio.android.omninotes.alpha --running-minutes 10
```

To understand the meanings of the options, you can see our [user manual](/docs/manual_en.md#launch-kea2).

> The usage is similar to the the original Fastbot's [shell commands](https://github.com/bytedance/Fastbot_Android?tab=readme-ov-file#run-fastbot-with-shell-command).

See more options by 
```bash
kea2 run -h
```

## Feature 2 (Run Enhanced Fastbot: Customize Testing Scenarios/Event Sequences/Widget Whitelists and Blacklists)

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
kea2 run -p it.feio.android.omninotes.alpha --running-minutes 10 propertytest discover -p quicktest.py
```

## Feature 3 (Run Enhanced Fastbot: Add Assertions)

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





## Test Reports

Kea2 automatically generates a HTML test report after each testing session. You can find the report in `output/` under your working directory.
<div align="center">
    <img style="border-radius: 14px; width: 70%; height: 70%;" src="https://github.com/user-attachments/assets/83a30d44-1884-4098-8062-9bab62bfdb19" />
</div>

#### Sample test reports
- [Single test report](https://ecnusse.github.io/Kea2_sample_report/) - Courtesy of Opay.
- [Merged test report (multiple runs)](https://ecnusse.github.io/kea2_sample_test_report/) - Summary for multiple runs.

> You can find more details on the test report in [this documentation](docs/test_report_introduction.md).


## :blue_book: User Manual (用户手册)

Please see the [user manual](/docs/manual_en.md) for more details on how to use Kea2.

请查看[用户手册](/docs/manual_cn.md)以获取更多Kea2的详细文档。


## :mega: News & Media
- [Kea2: Practical Property-based Testing for Mobile Apps](https://dl.acm.org/doi/10.1145/3803437.3806416) has been accepted at FSE 2026.
-  [Property-driven Testing Technology: Next-generation GUI Automated Testing](https://appw8oh6ysg4044.xet.citv.cn/p/course/video/v_6882fa14e4b0694ca0ec0a1b) - Video replay and slides @ MTSC 2025
- [Let's GoSSIP 2025 Software Security Summer School: Kea2 (Preview #1)](https://mp.weixin.qq.com/s/8_0_GNNin8E5BqTbJU33wg)

Industry perspectives on Kea2 (click to expand, courtesy of Opay):

<details>
  <summary>What does a “property” mean in Kea2? What is Kea2's value?</summary>

    Kea2 is essentially a toolkit that combines Python, uiautomator2, and Fastbot. It is like a vehicle chassis with an engine and wheels already assembled.
    
    The concept of “property” was introduced by Prof. Su's team. In practical testing work, a property corresponds to a minimal, atomic app function with little or no dependency on other flows, so it can run independently. Typical examples include login (enter username, enter password, submit) or liking a video with just a few steps.
    
    The value of combining properties with Kea2 is that it addresses the “heavy scripting” issue in Appium-style tests. With Appium, testing one property often requires many lines of navigation code. With Kea2, you mainly define the property itself, and Fastbot plus its learning strategy handles how to reach the target state.
    
    Another major value is technical enablement: Kea2 provides lighter UI scripting than Appium, while compensating for Fastbot's original limitations in property logic and assertions. It preserves Fastbot's strengths and fills key capability gaps.
    
    In short, for strictly orchestrated functional test cases, Appium is still a fine choice. But if your goal is exploratory testing, fuzz/stress testing, or compatibility testing, Kea2 is strongly recommended.
</details>

<details>
  <summary>What is Kea2 made of? What is its core role? What has it changed?</summary>

Kea2 is composed of:

    Fastbot -- the fuzzing engine that drives large-scale exploration.
    u2 -- executes business-level UI actions, similar in spirit to Selenium/Appium interactions.
    Python -- used to write UI actions, logic, and custom behaviors.

Kea2's core role:

    It provides condition triggers. While Fastbot is exploring, Kea2 continuously evaluates trigger conditions. When a condition is met, Fastbot is paused, the specified UI test/assertions are executed, and then control returns to Fastbot.

What Kea2 has changed:

    Replaced Fastbot's original condition-trigger mechanism.
    Replaced Fastbot's activity/widget blacklist mechanism.
    Replaced Fastbot's pruning mechanism.
    Added richer element-space operation capabilities.
    Added logic modeling in fuzz testing workflows.
    Added assertion support.
    Expanded UI element interaction capabilities.
</details>


## Relevant papers of Kea2

- [Kea2: Practical Property-based Testing for Mobile Apps](https://dl.acm.org/doi/10.1145/3803437.3806416). FSE 2026.
- [General and Practical Property-based Testing for Android Apps](https://dl.acm.org/doi/10.1145/3691620.3694986). ASE 2024.
- [Model-guided Property-based Testing of WeChat Pay at Billion-user Scale](). ASE 2026.
- [PropGen: Automated Property Generation for Property-Based Testing of Mobile Apps](). ASE 2026.
- [An Empirical Study of Functional Bugs in Android Apps](https://dl.acm.org/doi/10.1145/3597926.3598138). ISSTA 2023.
- [Fastbot2: Reusable Automated Model-based GUI Testing for Android Enhanced by Reinforcement Learning](https://dl.acm.org/doi/10.1145/3551349.3559505). ASE 2022.
- [Guided, Stochastic Model-Based GUI Testing of Android Apps](https://dl.acm.org/doi/10.1145/3106237.3106298). ESEC/FSE 2017.

## Reference This

```bibtex
@inproceedings{10.1145/3803437.3806416,
  author = {Liang, Xixian and Peng, Cheng and Ma, Bo and Shen, Xiangchen and Xiong, Yiheng and Su, Ting},
  title = {Kea2: Practical Property-based Testing for Mobile Apps},
  year = {2026},
  isbn = {9798400726361},
  publisher = {Association for Computing Machinery},
  address = {New York, NY, USA},
  url = {https://doi.org/10.1145/3803437.3806416},
  doi = {10.1145/3803437.3806416},
  abstract = {Validating functional correctness of mobile apps is challenging for manual testing and automated UI testing (limited to simple crashing bugs). Property-based testing is promising to tackle this challenge given functional properties. To this end, we introduce Kea2, a practical property-based testing tool for apps: (1) specifying properties in Python with enough flexibility and expressiveness; and (2) reusing existing GUI fuzzing techniques to support effective property checking. Indeed, Kea2 can find functional (logic) bugs in real-world apps. Kea2 has been open-sourced at https://github.com/ecnusse/Kea2 (a demo video: https://youtu.be/HS4rTCcaSPE), and received positive feedback for its usability and features.},
  booktitle = {Proceedings of the 34th ACM International Conference on the Foundations of Software Engineering},
  pages = {182--186},
  numpages = {5},
  location = {Concordia University, Montreal, QC, Canada},
  series = {FSE Companion '26}
}

@inproceedings{10.1145/3691620.3694986,
  author = {Xiong, Yiheng and Su, Ting and Wang, Jue and Sun, Jingling and Pu, Geguang and Su, Zhendong},
  title = {General and Practical Property-based Testing for Android Apps},
  year = {2024},
  isbn = {9798400712487},
  publisher = {Association for Computing Machinery},
  address = {New York, NY, USA},
  url = {https://doi.org/10.1145/3691620.3694986},
  doi = {10.1145/3691620.3694986},
  abstract = {Finding non-crashing functional bugs for Android apps is challenging for both manual testing and automated GUI testing techniques. This paper introduces and designs a general and practical testing technique based on the idea of property-based testing for finding such bugs. Specifically, our technique incorporates (1) a property description language (PDL) to allow specifying desired app properties, and (2) two exploration strategies as the input generators for effectively validating the properties. We implemented our technique as a tool named Kea and evaluated it on 124 historical bugs from eight real-world, popular Android apps. Our evaluation shows that our PDL can specify all the app properties violated by these historical bugs, demonstrating its generability for finding functional bugs. Kea successfully found 66 (68.0\%) and 92 (94.8\%) of the 97 historical bugs in scope under the two exploration strategies, demonstrating its practicability. Moreover, Kea found 25 new functional bugs on the latest versions of these eight apps, given the specified properties. To date, all these bugs have been confirmed, and 21 have been fixed. In comparison, prior state-of-the-art techniques found only 13 (13.4\%) historical bugs and 1 new bug. We have made all the artifacts publicly available at https://github.com/ecnusse/Kea.},
  booktitle = {Proceedings of the 39th IEEE/ACM International Conference on Automated Software Engineering},
  pages = {53--64},
  numpages = {12},
  keywords = {property-based testing, Android app testing, non-crashing functional bugs},
  location = {Sacramento, CA, USA},
  series = {ASE '24}
}
```


## Contact us

Please contact Xixian Liang at [xixian@stu.ecnu.edu.cn](xixian@stu.ecnu.edu.cn) with your Wechat ID / QR code to be invited to the WeChat discussion group. You can also contact Bo Ma([boma@stu.ecnu.edu.cn](boma@stu.ecnu.edu.cn)), Cheng Peng([pengcheng@stu.ecnu.edu.cn](pengcheng@stu.ecnu.edu.cn)), Yuyang Huang([huangyuyang@stu.ecnu.edu.cn](huangyuyang@stu.ecnu.edu.cn)).

Of course, we are also ready on GitHub to answer your questions/feedback.

**From an enterprise or university?** If your organization is using or evaluating Kea2, you are welcome to fill in a short form by clicking the link or scanning the QR code below, so that we can support you better.

Form link: <https://sy8pzmhmun.feishu.cn/share/base/form/shrcn5An36fzPzPEZsZ7mzSCE4b>

<div align="center">
    <img src="https://github.com/user-attachments/assets/ed2b16d7-6a7c-4814-8325-1a855e872f22" alt="Kea2 signup form QR code" style="border-radius: 14px; width: 20%; height: 20%;"/>
</div>

### Maintainers/Contributors

Kea2 has been actively developed and maintained by the people in [ecnusse](https://github.com/ecnusse):

- [Xixian Liang](https://xixianliang.github.io/resume/) ([@XixianLiang][])
- [Bo Ma](https://github.com/majuzi123) ([@majuzi123][])
- [Cheng Peng](https://github.com/Drifterpc) ([@Drifterpc][])
- [Yuyang Huang](https://github.com/YuYoungG) ([@YuYoungG][])
- [Ting Su](https://tingsu.github.io/) ([@tingsu][])

[@XixianLiang]: https://github.com/XixianLiang
[@majuzi123]: https://github.com/majuzi123
[@Drifterpc]: https://github.com/Drifterpc
[@YuYoungG]: https://github.com/YuYoungG
[@tingsu]: https://github.com/tingsu

[Zhendong Su](https://people.inf.ethz.ch/suz/), [Yiheng Xiong](https://xyiheng.github.io/), [Xiangchen Shen](https://xiangchenshen.github.io/), [Mengqian Xu](https://mengqianx.github.io/), [Haiying Sun](https://faculty.ecnu.edu.cn/_s43/shy/main.psp), [Jingling Sun](https://jinglingsun.github.io/), [Jue Wang](https://cv.juewang.info/), [Geguang Pu]() have also been actively participated in this project and contributed a lot!

Kea2 has also received many valuable insights, advices, feedbacks and lessons shared by several industrial people from Bytedance ([Zhao Zhang](https://github.com/zhangzhao4444), Yuhui Su from the Fastbot team), OPay (Tiesong Liu), WeChat (Haochuan Lu, Yuetang Deng), Huawei, Xiaomi and etc. Kudos!

### Become a Contributor!

Kea2 is an open-source project and we are calling for more contributors to join us!

See [Developer guide](DEVELOP.md) for more details.

## Star History

<a href="https://www.star-history.com/?repos=ecnusse%2FKea2&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=ecnusse/Kea2&type=date&theme=dark&legend=top-left&sealed_token=xTcIgy9M4-i1Mr8zkwwExXKPfdDt_DgnpqzwY0RmpjKOULbHx7gXFOS1TTK2hBEvOCP4eVjjyu2ALDTuY9_d8DJPNcJGOv9q76oThj3i4WGYlbmg_aWRYhhDTScCnclZ0rwnz6XxeRaUE9dr_VBXz-GUctDCChip2TlhLfqNuMordyyLufyORBbeC7T9" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=ecnusse/Kea2&type=date&legend=top-left&sealed_token=xTcIgy9M4-i1Mr8zkwwExXKPfdDt_DgnpqzwY0RmpjKOULbHx7gXFOS1TTK2hBEvOCP4eVjjyu2ALDTuY9_d8DJPNcJGOv9q76oThj3i4WGYlbmg_aWRYhhDTScCnclZ0rwnz6XxeRaUE9dr_VBXz-GUctDCChip2TlhLfqNuMordyyLufyORBbeC7T9" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=ecnusse/Kea2&type=date&legend=top-left&sealed_token=xTcIgy9M4-i1Mr8zkwwExXKPfdDt_DgnpqzwY0RmpjKOULbHx7gXFOS1TTK2hBEvOCP4eVjjyu2ALDTuY9_d8DJPNcJGOv9q76oThj3i4WGYlbmg_aWRYhhDTScCnclZ0rwnz6XxeRaUE9dr_VBXz-GUctDCChip2TlhLfqNuMordyyLufyORBbeC7T9" />
 </picture>
</a>

[^1]: Many UI automated testing tools provide “custom event sequence” features (such as [Fastbot](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BA%8B%E4%BB%B6%E5%BA%8F%E5%88%97) and [AppCrawler](https://github.com/seveniruby/AppCrawler)), but these features often have practical limitations, such as restricted flexibility and difficult maintenance. Many Fastbot users have reported issues with its custom event sequence capability, e.g., [#209](https://github.com/bytedance/Fastbot_Android/issues/209), [#225](https://github.com/bytedance/Fastbot_Android/issues/225), and [#286](https://github.com/bytedance/Fastbot_Android/issues/286).

[^2]: Supporting automatic assertions during UI automated testing is an important capability, but very few tools provide it. We noticed that the developers of [AppCrawler](https://ceshiren.com/t/topic/15801/5) once planned to introduce an assertion mechanism; the idea received strong user interest, and users kept asking for updates since 2021, but it has not been delivered.
