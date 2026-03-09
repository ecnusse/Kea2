# Documentation
English | [简体中文](/docs/manual_cn.md)

## Directory

### 1. Kea2's high-level idea
- [Kea2's high-level idea](#kea2s-high-level-idea)
### 2. How to write Kea2's scripts?
- [Kea2's Scripts](#kea2s-script-tutorials)
- [Kea2's Script APIs](#kea2s-scripts-apis) (Test class structure, decorators)
### 3. How to launch Kea2?
- [Kea2's Command Line Interface](#1-launch-kea2-by-shell-commands) (args for `kea2 run`, sub-commands, and retrun code)
- [Launch in python code (Unittest Main)](#2-launch-kea2-by-unittestmain)
### 4. How to read and manage Kea2's reports?
-  [Read Kea2's test reports](#meaning-of-property-violations) (meaning of property violations)
-  [Generate Kea2's test reports](#manually-generate-kea2-report)
-  [Generate merged test report](#merge-multiple-test-reports-for-multiple-test-sessions)
### 5. Configuration File
- [Fastbot configuration files](#fastbot-configuration-files)
- [Blacklisting/Whitelisting](#blacklisting-specific-ui-widgetsregions-黑白名单控件界面特定区域)
- [Update user configuration files](#update-of-user-configuration-files)
### 6. Advanced Features
- [Advanced Feature 1: Stateful Testing](#advanced-feature-1-stateful-testing-带状态的测试)
- [Advanced Feature 2: Invariant Checks](#advanced-feature-2-ivariant-checks-不变式检查)
- [Advanced Feature 3: Reusing regression tests](#advanced-feature-3-reusing-regression-tests-兼容已有脚本通过前置脚本步骤到达特定层次)

### 7. Experimental Feature
- [Experimental Feature1: FBM Merge](#experimental-feature1-fbm-merge)

### 8. FAQs and Tips
- [FAQs](#faqs)
- [Interacting with Third-party Packages](#interacting-with-third-party-packages)
- [Tricks to enhance Kea2 performance](#tricks-to-enhance-kea2-performance)





# Kea2's high-level idea

- :star: [Blog: 别再苦哈哈写测试脚本了，生成它们吧！](https://mp.weixin.qq.com/s/R2kLCkXpDjpa8wCX4Eidtg)
- :star: [Kea2 分享交流会 (2025.09, bilibili 录播)](https://www.bilibili.com/video/BV1CZYNz9Ei5/)
- [Q&A for Kea2 and PBT (对Kea2和PBT技术的常见问题和回答)](https://sy8pzmhmun.feishu.cn/wiki/SLGwwqgzIiEuC3kwmV8cSZY0nTg?from=from_copylink) 
- [Kea2 101 (Kea2 从0到1 的入门教程与最佳实践，建议新手阅读)](https://sy8pzmhmun.feishu.cn/wiki/EwaWwPCitiUJoBkIgALcHtglnDK?from=from_copylink)


# Kea2's script tutorials
We provide two tutorials to show you how to write Kea2's scripts and illustrate some sample usage of Kea2's scripts.

1. [A guide of making use of Kea2's Feature 2 and 3 to test your app. (Take WeChat for example)](Scenario_Examples_zh.md).
2. [A guide of writing Kea2's scripts to stress test a particular feature of your app. (Take lark for example)](https://sy8pzmhmun.feishu.cn/wiki/Clqbwxx7ciul5DkEyq8c6edxnTc).

# Kea2's scripts APIs

Basically, you can write Kea2's scripts by following two steps:

### 1. Create a test class that extends `unittest.TestCase`

```python
import unittest 

class MyFirstTest(unittest.TestCase):
    ...
```

> Kea2 uses [unittest](https://docs.python.org/3/library/unittest.html) to manage scripts. Test classes should extend `unittest.TestCase`.

You can optionally define `setUpClass` to do one-time setup for the class (e.g., prepare shared resources). It can also be used to [apply global setup for the u2 driver](https://github.com/openatx/uiautomator2?tab=readme-ov-file#global-settings). If defined, it is called once before any test methods run.

### 2. Write scripts by defining test methods

You can decorate a test method with `@precondition`. It takes a boolean-returning function as an argument. When it returns `True`, the precondition is satisfied and the method becomes eligible to run. Kea2 then executes it based on the probability defined by `@prob`.

If a test method is not decorated with `@precondition`, it will not be activated during automated UI testing and will be treated as a normal `unittest` test method.
To always execute a method during exploration, specify `@precondition(lambda self: True)`. (You may need [invariant checking](#advanced-feature-2-ivariant-checks-不变式检查) if you want to check some properties at every step.) If `@prob` is not provided, the default probability is 1 (always execute when the precondition is satisfied).

Here is a recommended template:

```python
import unittest
from uiautomator2 import Device  # Import u2 for typing
from kea2 import precondition

class MyFirstTest(unittest.TestCase):
    d: Device  # Type hint for uiautomator2's Device

    @prob(0.7)
    @precondition(lambda self: ...)
    def test_func1(self):
        self.d(...)  # Use self.d to interact with the device
        ...
```

> Kea2 uses [uiautomator2](https://github.com/openatx/uiautomator2) to manipulate Android devices. Refer to [uiautomator2's docs](https://github.com/openatx/uiautomator2?tab=readme-ov-file#quick-start) for more details. 

You can read [Kea - Write your first property](https://kea-docs.readthedocs.io/en/latest/part-keaUserManuel/first_property.html) for more details.

## Decorators 

### `@precondition`

```python
@precondition(lambda self: ...)
def test_func1(self):
    ...
```

The decorator `@precondition` takes a function which returns boolean as an arugment. When the function returns `True`, the precondition is satisified and function `test_func1` will be activated, and Kea2 will run `test_func1` based on certain probability value defined by the decorator `@prob`.
The default probability value is 1 if `@prob` is not specified. In this case, function `test_func1` will be always executed when its precondition is satisfied.

### `@prob`

```python
@prob(0.7)
@precondition(lambda self: ...)
def test_func1(self):
    ...
```

The decorator `@prob` takes a float number as an argument. The number represents the probability of executing function `test_func1` when its precondition (specified by `@precondition`) is satisfied. The probability value should be between 0 and 1. 
The default probability value is 1 if `@prob` is not specified. In this case, function `test_func1` will be always executed when its precondition is satisfied.

When the preconditions of multiple functions are satisfied. Kea2 will randomly select one of these functions to execute based on their probability values. 
Specifically, Kea2 will generate a random value `p` between 0 and 1, and `p` will be used to decide which function to be selected based on the probability values of
these functions.

For example, if three functions `test_func1`, `test_func2` and `test_func3` whose preconditions are satisified, and
their probability values are `0.2`, `0.4`, and `0.6`, respectively. 
- Case 1: If `p` is randomly assigned as `0.3`, `test_func1` will lose the chance of being selected because its probability value `0.2` is smaller than `p`. Kea2 will *randomly* select one function from `test_func2` and `test_func3` to be executed.
- Case 2: If `p` is randomly assigned as `0.1`, Kea2 will *randomly* select one function from `test_func1`, `test_func2` and `test_func3` to be executed.
- Case 3: If `p` is randomly assigned as `0.7`, Kea2 will ignore all these three functions `test_func1`, `test_func2` and `test_func3`.


### `@max_tries`

```python
@max_tries(1)
@precondition(lambda self: ...)
def test_func1(self):
    ...
```

The decorator `@max_tries` takes an integer as an argument. The number represents the maximum number of times function `test_func1` will be executed when the precondition is satisfied. The default value is `inf` (infinite).


# Launch Kea2

We offer two ways to launch Kea2.

## 1. Launch Kea2 by shell commands

You can launch Kea2 by shell commands `kea2 run`.

`kea2 run` is consisted of two parts: the first part is the options for Kea2, and the second part is the sub-command and its arguments.

### 1.1 `kea2 run` Options

| arg                        | meaning                                                                                                                                                                                                                                                               | default | 
|----------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------| --- |
| -s                         | The serial of your device, which can be found by `adb devices`                                                                                                                                                                                                        | |
| -t                         | The transport id of your device, which can be found by `adb devices -l`                                                                                                                                                                                               | |
| -p                         | Specify the target app package name(s) to test (e.g., com.example.app). *Supports multiple packages: `-p pkg1 pkg2 pkg3`*                                                                                                                                             | 
| -o                         | The ouput directory for logs and results                                                                                                                                                                                                                              | `output` |
| --running-minutes          | The time (in minutes) to run Kea2                                                                                                                                                                                                                                     | `10` |
| --max-step                 | The maxium number of monkey events to send                                                                                                                                                                                                                            | `inf` (infinite) |
| --throttle                 | The delay time (in milliseconds) between two monkey events                                                                                                                                                                                                            | `200` |
| --driver-name              | The name of driver used in the kea2's scripts. If `--driver-name d` is specified, you should use `d` to interact with a device, e..g, `self.d(..).click()`.                                                                                                           | `d` |
| --log-stamp                | the stamp for log file and result file. (e.g., if `--log-stamp 123` is specified, the log files will be named as `fastbot_123.log` and `result_123.json`.)                                                                                                            | current time stamp |
| --profile-period           | The period (in the numbers of monkey events) to profile coverage and collect UI screenshots. Specifically, the UI screenshots are stored on the SDcard of the mobile device, and thus you need to set an appropriate value according to the available device storage. | `25` |
| --take-screenshots         | Take the UI screenshot at every Monkey event. The screenshots will be automatically pulled from the mobile device to your host machine periodically (the period is specified by `--profile-period`).                                                                  |  |
| --pre-failure-screenshots  | Dump n screenshots before failure. 0 means take screenshots for every step. This option is only valid when `--take-screenshots` is set.                                                                                                                               | `0` |
| --post-failure-screenshots | Dump n screenshots after failure. Should be smaller than `--pre-failure-screenshots`. This option is only valid when `--take-screenshots` is set.                                                                                                                     | `0` |
| --restart-app-period       | The period (in the numbers of monkey events) to restart the app under test.                                                                                                                                                                                           | `0` (never restart) |
| --fastbot-agent            | Fastbot agent strategy. Available options: `double-sarsa`, `sarsa`. | `double-sarsa` |
| --device-output-root       | The root of device output dir. Kea2 will temporarily save the screenshots and result log into `"<device-output-root>/output_*********/"`. Make sure the root dir can be access.                                                                                       | `/sdcard` |
| --act-whitelist-file       | Activity WhiteList File. You can pass a custom path, or omit the value to use `/sdcard/.kea2/awl.strings`.                                                                                                                                                            | |
| --act-blacklist-file       | Activity BlackList File. You can pass a custom path, or omit the value to use `/sdcard/.kea2/abl.strings`.                                                                                                                                                            | |
| --merge-fbm                | Enable FBM merge at startup. Pulls FBM(s) from the device and merges with local PC FBM data. The FBM file path on the local PC is in `configs/merge_fbm`.                                                                                                             | |

### 1.2 Sub-commands and their arguments
Kea2 supports 3 sub-commands: `propertytest`, `unittest`, and `--` (extra arguments).

#### **1.2.1 `propertytest` sub-command and test discovery (property based testing)**

Kea2 is compatible with `unittest` framework. You can manage your test cases in unittest style and discover them with [unittest discovery options](https://docs.python.org/3/library/unittest.html#test-discovery). You can launch Kea2 with `kea run` with driver options and sub-command `propertytest`.

The shell command:
```
# <unittest discovery cmds> are the unittest discovery commands, e.g., `discover -p quicktest.py`
kea2 run <Kea2 cmds> propertytest <unittest discovery cmds> 
```
Sample shell commands:

```bash
# Launch Kea2 and load one single script quicktest.py.
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10  propertytest discover -p quicktest.py

# Launch Kea2 and load multiple scripts from the directory mytests/omni_notes
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10  propertytest discover -s mytests/omni_notes -p test*.py
```

#### **1.2.2 (Expirimental Feature) `unitest` sub-command (hybrid test)**

> This feature is still under development. We are looking forward to your feedback! Contact us if you're interested in this feature.

`unittest` sub-command is used for feature 4 (Hybrid Testing). You can launch Kea2 with `kea run` with driver options and sub-command `unittest`. Same as `propertytest`, you can use [unittest discovery options](https://docs.python.org/3/library/unittest.html#test-discovery) to load your test cases.


#### **1.2.3 `--` sub-command (extra arguments)**

If you need to pass extra arguments to the underlying Fastbot, append `--` after the regular arguments, then list the extra arguments. For example, to set the touch event percentage to 30%, run:

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10  -- --pct-touch 30 unittest discover -p quicktest.py
```
### Return Code
`kea2 run` (and `python -m kea2.cli run`) exits with:

| code | meaning |
| --- | --- |
| `0` | Success. Test run completed without test failures. |
| `1` | Property violation detected. |
| `2` | Crash or ANR detected. |
| `3` | Both property violation and Crash or ANR detected. |
| `4` | Unexpected runtime error. |

Notes:
- `KeyboardInterrupt` (Ctrl-C) is treated as a normal stop. It is not classified as an unexpected runtime error.

## 2. Launch Kea2 by `unittest.main`

Like unittest, we can launch Kea2 through the method `unittest.main`.

Here is an example (named as `mytest.py`). You can see that the options are directly defined in the script.

```python
import unittest

from kea2 import KeaTestRunner, Options, keaTestLoader

class MyTest(unittest.TestCase):
    ...
    # <your test methods here>

if __name__ == "__main__":
    KeaTestRunner.setOptions(
        Options(
            driverName="d",
            packageNames=[PACKAGE_NAME],
            # serial="emulator-5554",   # specify the serial
            maxStep=100,
            # running_mins=10,  # specify the maximal running time in minutes, default value is 10m
            # throttle=200,   # specify the throttle in milliseconds, default value is 200ms
        )
    )
    # Declare the KeaTestRunner
    unittest.main(testRunner=KeaTestRunner, testLoader=keaTestLoader)
```

We can directly run the script `mytest.py` to launch Kea2, e.g.,
```bash
python3 mytest.py
```


# Read and Manage Kea2 test reports

**[:page_facing_up: View the sample test report](https://ecnusse.github.io/Kea2_sample_report/)** - *Courtesy of Opay.*

**[:page_facing_up: View the sample merged test report](https://ecnusse.github.io/kea2_sample_test_report/)**

## Read Kea2's test reports
### Meaning of Property Violations

Field | Description | Meaning
--- | --- | --- |
precond_satisfied | During exploration, how many times has the test method's precondition been satisfied? | Does we reach the state during exploration? 
executed | During UI testing, how many times the test method has been executed? | Has the test method ever been executed?
fail | How many times did the test method fail the assertions during UI testing? | When failed, the test method found a likely functional bug. 
error | How many times does the test method abort during UI tsting due to some unexpected errors (e.g. some UI widgets used in the test method cannot be found) | When some error happens, the script needs to be updated/fixed because the script leads to some unexpected errors.

### Meaning of Widget Coverage

Widget coverage counts the distinct widgets triggered during exploration (events generated by the fuzzing engine). A widget is identified by the tuple `<activity, class, resourceId, content-desc>`.

### Improve testing by analyzing the report

Use coverage trends (activity and widget coverage) to understand exploration progress and refine scripts for better results.

**1. Set a time budget.** Coverage typically saturates after a while, so longer runs do not always yield better results. Identify the saturation point from the report and set the budget accordingly. Multiple short runs can be more effective than one long run.

**2. Design kea2 scripts.** Use `--take-screenshots` to capture each step, then review the report to find where exploration gets stuck. For example, if it stalls at a login page, add a login script to help it move past that state and reach deeper screens. After adding the appropriate scripts, you can use the `--pre-failure-screenshots` and `--post-failure-screenshots` options to avoid generating too many screenshots to enhance performance.

## Manage Kea2's test reports
### Manually generate Kea2 report

The `kea2 report` command generates an HTML test report from existing test results. This command analyzes test data and creates a comprehensive visual report showing test execution statistics, coverage information, property violations, and crash details.

| arg | meaning | required |
| --- | --- | --- |
| -s, --sync | Sync data from device before generating the report |
| -p, --path *[PATHS]* | Path to the directory containing test results (res_* directory) | :white_check_mark: |

**Usage Examples:**

```bash
# Generate report from a test result directory
kea2 report -p res_20240101_120000

# Sync device data before generating the report
kea2 report -s -p res_20240101_120000

# Generate multiple reports
kea2 report -p ./output/res_20240101_120000 /Users/username/kea2_tests/res_20240102_130001
```

### Merge multiple test reports (for multiple test sessions)

The `kea2 merge` command allows you to merge multiple test report directories and generate a combined report. This is useful when you have run multiple test sessions and want to consolidate the results into a single comprehensive report.

| arg | meaning | required |
| --- | --- | --- |
| -p, --paths | Paths to test report directories (res_* directories) to merge. At least 2 paths are required. | :white_check_mark: |
| -o, --output | Output directory for merged report |  |

**Usage Examples:**

```bash
# Merge two test report directories
kea2 merge -p res_20240101_120000 res_20240102_130000

# Merge multiple test report directories with custom output
kea2 merge -p res_20240101_120000 res_20240102_130000 res_20240103_140000 -o my_merged_report
```


# Configuration Files (Fastbot, blacklist/whitelist)

## Fastbot configuration files

After executing `Kea2 init`, some configuration files will be generated in the `configs` directory. 
These configuration files belong to `Fastbot`, and their specific introductions are provided in [Introduction to configuration files](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E4%B8%93%E5%AE%B6%E7%B3%BB%E7%BB%9F).

## Blacklisting specific UI widgets/regions (黑白名单/控件/界面特定区域)

Blacklisting is defined by two dimensions: scope (widget-level vs tree-level) and rule type (global vs conditional).

#### 1. Scope (what to block)
**Widget-level** — block a single widget.  
**Tree-level** — block a widget and its entire subtree (a UI region).

#### 2. Rule Type (when to block)
**Global** — applied on every page/screen.  
**Conditional** — applied only on pages that satisfy `@precondition`.

### APIs for Blacklisting/Whitelisting UI widgets/regions

| Scope \ Rule Type | Global (always) | Conditional (`@precondition`) |
|-|-|-|
| Widget-level | `global_block_widgets` | `@precondition → block_*` |
| Tree-level | `global_block_tree` | `@precondition → block_tree_*` |

**See Example in:** [:blue_book: widget.block.py](../kea2/assets/fastbot_configs/widget.block.py)

#### :white_check_mark: Supported Selectors for Blacklisting

Commonly used attributes are listed below. For detailed usage, please refer to the [uiautomator2 documentation](https://github.com/openatx/uiautomator2/):


<details>
  <summary>Basic Selectors</summary>

- **Text-related attributes**  
  `text`, `textContains`, `textStartsWith`

- **Class-related attributes**  
  `className`

- **Description-related attributes**  
  `description`, `descriptionContains`, `descriptionStartsWith`

- **State-related attributes**  
  `checkable`, `checked`, `clickable`, `longClickable`, `scrollable`, `enabled`, `focusable`, `focused`, `selected`

- **Package name related attributes**  
  `packageName`

- **Resource ID related attributes**  
  `resourceId`

- **Index related attributes**  
  `index`
</details>

<details>
  <summary>Children and Siblings Selector</summary>

- **Locate child or grandchild elements**  

  ```python
  d(className="android.widget.ListView").child(text="Wi-Fi")
  ```

- **Locate sibling elements**  

  ```python
  d(text="Settings").sibling(className="android.widget.ImageView")
  ```
</details>

<details>
  <summary>Basic XPath Expressions</summary>

**Basic**  
```python
d.xpath('//*[@text="Private FM"]')
```

**Starting with @**  
```python
d.xpath('@personal-fm') # Equivalent to d.xpath('//*[@resource-id="personal-fm"]').exists
```

**Child element positioning**  
```python
d.xpath('@android:id/list').child('/android.widget.TextView')
```
</details>



#### :no_entry_sign: Unsupported Selectors for Blacklisting

 Please avoid using the following methods as they are **not supported** for blacklist configuration:

<details>
  <summary>Positional relations based queries</summary>

```python
d(A).left(B)    # Select B to the left of A
d(A).right(B)   # Select B to the right of A
d(A).up(B)      # Select B above A
d(A).down(B)    # Select B below A
```
</details>

<details>
  <summary>Child querying selectors</summary>

`child_by_text`, `child_by_description`, `child_by_instance`.
```python
d(className="android.widget.ListView", resourceId="android:id/list") \
  .child_by_text("Bluetooth", className="android.widget.LinearLayout")

d(className="android.widget.ListView", resourceId="android:id/list") \
  .child_by_text(
    "Bluetooth",
    allow_scroll_search=True,  # default False
    className="android.widget.LinearLayout"
  )
```
</details>

<details>
  <summary>instance</summary>

```python
d(className="android.widget.Button", instance=2)
```
</details>

<details>
  <summary>Regular expression-based queries</summary>

`textMatches`, `classNameMatches`, `descriptionMatches`, `packageNameMatches`, `resourceIdMatches`
</details>

<details>
  <summary>Chained XPath selectors</summary>

Chained XPath selectors with parent-child relationships:
```python
d.xpath('//android.widget.Button').xpath('//*[@text="Private FM"]')
```

```python
d.xpath('//*[@text="Private FM"]').parent() # Position to the parent element
d.xpath('//*[@text="Private FM"]').parent("@android:list") # Position to the parent element that meets the condition
```

Xpath selectors with logical operators:
```python
(d.xpath("NFC") & d.xpath("@android:id/item"))
```

```python
(d.xpath("NFC") | d.xpath("App") | d.xpath("Content"))
```
</details>


### Blacklisting/Whitelisting activities

We inherit Fastbot's blacklisting and whitelisting mechanism for activities. To use this feature, you need to:

1. specify the activities to be blacklisted or whitelisted in `configs/awl.strings`.
2. Add the corresponding parameter (`--act-blacklist-file`, `--act-whitelist-file`) when running kea2.

> The `configs/awl.strings` file is generated by `Kea2 init`. [View the sample configuration file](/kea2/assets/fastbot_configs/abl.strings)

### Parameters for activity blacklisting and whitelisting

| arg | meaning | default |
| --- | --- | --- |
| `--act-blacklist-file [path]` | Activate activity blacklisting. If `path` is omitted, use `/sdcard/.kea2/abl.strings`. | |
| `--act-whitelist-file [path]` | Activate activity whitelisting. If `path` is omitted, use `/sdcard/.kea2/awl.strings`. | |

Sample Usage:
```
kea2 run -p it.feio.android.omninotes.alpha --act-blacklist-file propertytest discover -p quicktest.py

# custom blacklist file path
kea2 run -p it.feio.android.omninotes.alpha --act-blacklist-file /sdcard/custom_abl.strings propertytest discover -p quicktest.py
```

### Mechanism of activity blacklisting and whitelisting
- Whitelist and blacklist **cannot be set at the same time**. Choose one mode: if a whitelist is set, all activities outside it are treated as blacklisted.
- Fastbot monitors activity launches. When a blacklisted activity is about to start, it is blocked, so the UI may appear unresponsive during that transition.


## Update of User Configuration Files
When updating Kea2, the user's local configuration sometimes needs to be updated. (The latest kea2 version may not be compatible with the old configuration files.)

When runtime error detected, Kea2 will check whether the local configuration files are compatible with the current Kea2 version. If not, a warning message will be printed in the console. Update the local configuration files according to the following instructions.

1. Backup your local configuration files (in case of any unexpected issues during the update process).
2. delete all the configuration files under "/configs" in the project's root directory.
3. run `kea2 init` to generate the latest configuration files.
4. Merge your old configurations into the new configuration files according to your needs.

# Advanced Features
## Advanced Feature 1: Stateful Testing (带状态的测试)

Stateful testing is an advanced approach in property-based testing. The idea is to model the app's internal data state and share it across multiple properties to guide exploration and uncover more complex defects.

Kea2 provides a shared `state` object for stateful testing. It is a singleton `dict` that stores internal data and modeled states across properties. You can update `state` in properties, then read it in later properties to control exploration.

Example: in CRUD-related features, you can record the current data items and use them in later properties. A typical scenario that needs stateful testing is "searching items" (you must know which items exist before searching).

```python
from kea2 import state

state["item_names"] = []  # store data items

class MyStatefulTest(unittest.TestCase):
    @precondition(...)
    def test_add_item(self):
        # add a data item
        new_item_name = __get_random_item_name()
        self.d(resourceId="add_button").click()
        self.d(resourceId="item_name_input").set_text(new_item_name)
        self.d(resourceId="save_button").click()
        # update items in state
        state["item_names"].append(new_item_name)

    # search with items stored in state
    @precondition(lambda self: len(state["item_names"]) > 0 and ...)
    def search_item(self):
        search_name = random.choice(state["item_names"])
        self.d(resourceId="search_box").set_text(search_name)
        self.d.press("enter")
        assert self.d(text=search_name).exists
```

> If you want to learn more about stateful testing, see the [Hypothesis Stateful Testing documentation](https://hypothesis.readthedocs.io/en/latest/stateful.html)

## Advanced Feature 2: Ivariant Checks (不变式检查)

Invariant checks (`@invariant`) define properties that should always hold. A normal property contains a precondition P, an interaction scenario I, and an assertion Q. An invariant is a special property where P is always true, I is empty, and Q is checked in every state.

Kea2 checks all invariants every time the app enters a new state (i.e., after each property execution or monkey event).

We illustrate the difference between normal properties and invariants with the following figure:

**For normal properties:** 

`total steps` > `precondition satified times` > `property check times` > `fails` + `errors`

**For invariants:**

`total steps` = `invariant checks times` > `fails` + `errors`

```python
from kea2 import invariant

@invariant
def invariant_non_negative_word_count(self):
    if self.d(resourceId="word_count").exists:
        # Get the unlearned word count
        word_count_text = self.d(resourceId="word_count").get_text()
        word_count = int(word_count_text)
        assert word_count >= 0, f"Word count is negative: {word_count}"
```

`@invariant` marks an invariant check. All invariants are executed after every property execution or monkey event (on each iteration). Invariants are suitable for always-true conditions, such as layout issues on a single page or state consistency derived from [Stateful testing](#stateful-testing). Keep invariants fast and side-effect free.


## Advanced Feature 3: Reusing regression tests (兼容已有脚本：通过前置脚本步骤到达特定层次)

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
from kea2 import Kea2Tester, Options

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

# Experimental Feature

## Experimental Feature1: FBM Merge

### Overview
FBM Merge (Model Aggregation) supports distributed testing environments (multi-device parallel testing). At the end of each round, Fastbot models are aggregated to accelerate training and enable model sharing.

### How to Enable
Simply add the `--merge-fbm` parameter when running kea2:
```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10 --merge-fbm propertytest discover -p quicktest.py
```

### Purpose
- Designed for distributed kea2 runs (one PC with multiple mobile devices).
- Aggregates FBM data from multiple devices to compensate for insufficient activity coverage on a single device.
- The merged FBM file is automatically maintained on the PC.
- The merging process automatically slims down the FBM file, greatly reducing file size and improving performance.

### Implementation Details
1. **Automatic Pull and Merge:**
   - At the start of kea2 run, a copy of the FBM file is pulled from the mobile device as the "starting point" for this round.
   - After the run, both the newly generated FBM file and the starting point file are pulled back to the PC.
   - The PC calculates the delta between the two files, obtains the new FBM data for this round, and merges it into the core FBM file on the PC.
   - The merging process uses file locks to prevent concurrent read/write conflicts.
2. **File Permissions:**
   - On Linux/MacOS, merged files have 644 permissions.
   - On Windows, Administrators have full control, Everyone has read-only, and permission inheritance is disabled (to simulate 644 permissions).
3. **File Slimming:**
   - Duplicate entries are removed at both the data structure and index levels to achieve file slimming.
     - **Data Structure Deduplication:** For the same action, regardless of how many times it appears across devices or test runs, only one action record is kept, and accumulate the trigger counts of the same activity that belongs to this action, avoiding redundant entries.
     - **Index Deduplication:** When saving the FBM file, deduplication was performed on the indexes. For example, the same string `MainActivity` only creates an index once, thereby reducing the space occupied by the FBM file.
   - On average, file size can be reduced by 90%. For example, a 6MB FBM file can be slimmed down to just 226KB, with entry count reduced from 87,933 to 6,025.
   - Example: Two entries like "MainActivity 15" and "MainActivity 10" are merged into one entry "MainActivity 25".

### Usage Notes
- Users only need to add the `--merge-fbm` parameter when running kea2 run; the PC-side FBM file will be maintained automatically.
- **Note:** The PC-side FBM file is not automatically pushed to the device. If you want it to take effect on the device, you need to manually push it to the `/sdcard` directory.
- The merged FBM file is located in the `configs/merge_fbm/` directory.

#### Example: Push to Device
```bash
adb -s <devicename> push $root_dir/configs/merge_fbm/fastbot_<package_name>.fbm /sdcard
```

### Typical Use Cases
1. **First-time Testing on a New Device:** Push the merged FBM file to benefit from models accumulated on older devices.
2. **Large-scale Device Testing:** After each test, push the merged file from the PC to all devices to improve coverage consistency across devices.

### Console Output Example

The following image shows a sample console output after a successful FBM Merge:

![FBM Merge Console Example](images/fbm_merge_example.png)


# Other Tips and FAQs

## FAQs
### Kea2 always goes back to home or exits a page, why?
You may be using gesture navigation. Fastbot’s scroll events can be recognized as a “back” gesture, causing the current page to exit. We recommend switching to 3-button navigation to avoid this issue.

See [Kea2 issue #99](https://github.com/ecnusse/Kea2/issues/99) for more details.

## Interacting with Third-party Packages
Kea2 blocks third-party packages (e.g., ad packages) during exploration by default. If you want to interact with them, add `--allow-any-starts` in [extra arguments](#---sub-command-extra-arguments) when launching Kea2.

For example:
```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10  --driver -- --allow-any-starts propertytest discover -p quicktest.py
```

## Tricks to enhance Kea2 performance

Currently, we have an algorithm in `@precondition` decorator and `widgets.block.py` to enhence the performance of the tool. The algorithm only support basic selector (No parent-child relationship) in uiautomator2. If you have many properties with complex preconditions and observed performance issue, you're recommanded to specify it in xpath.

| | **Recommand** | **Not recommand** |
| -- | -- | -- |
| **Selector** | `d(text="1").exist` | `d(text="1").child(text="2").exist` |

If you need to specify `parent-child` relation ship in `@precondition`, specify it in xpath.

for example: 

```python
# Do not use: 
# @precondition(lambda self: 
#      self.d(className="android.widget.ListView").child(text="Bluetooth")
# ):
# ...

# Use
@precondition(lambda self: 
    self.d.xpath('//android.widget.ListView/*[@text="Bluetooth"]')
):
...
```

## Debug Mode (`kea2 -d ...`)

You can enable debug mode by adding the `-d` option when using Kea2. In debug mode, Kea2 will print more detailed logs to help diagnose issues.

| arg | meaning | default |
| --- | --- | --- |
| -d | Enable debug mode | |

> ```bash
> # add -d to enable debug mode
> kea2 -d run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10  unittest discover -p quicktest.py
> ```
