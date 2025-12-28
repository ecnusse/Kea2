
# Documentation

[中文文档](manual_cn.md)

## Kea2's tutorials 

1. [A guide of making use of Kea2's Feature 2 and 3 to test your app. (Take WeChat for example)](Scenario_Examples_zh.md).
2. [A guide of writing Kea2's scripts to stress test a particular feature of your app. (Take lark for example)](https://sy8pzmhmun.feishu.cn/wiki/Clqbwxx7ciul5DkEyq8c6edxnTc).

## Kea2's scripts

Kea2 uses [Unittest](https://docs.python.org/3/library/unittest.html) to manage scripts. All the Kea2's scripts can be found in unittest's rules (i.e., the test methods should start with `test_`, the test classes should extend `unittest.TestCase`).

Kea2 uses [Uiautomator2](https://github.com/openatx/uiautomator2) to manipulate android devices. Refer to [Uiautomator2's docs](https://github.com/openatx/uiautomator2?tab=readme-ov-file#quick-start) for more details. 

Basically, you can write Kea2's scripts by following two steps:

1. Create a test class which extends `unittest.TestCase`. 

```python
import unittest 

class MyFirstTest(unittest.TestCase):
    ...
```

2. Write your own script by defining test methods

By default, only the test method starts with `test_` will be found by unittest. You can decorate the function with `@precondition`. The decorator `@precondition` takes a function which returns boolean as an arugment. When the function returns `True`, the precondition is satisified and the script will be activated, and Kea2 will run the script based on certain probability defined by the decorator `@prob`.

Note that if a test method is not decorated with `@precondition`.
This test method will never be activated during automated UI testing, and will be treated as a normal `unittset` test method.
Thus, you need to explicitly specify `@precondition(lambda self: True)` when the test method should be always executed. When a test method is not decorated with `@prob`, the default probability is 1 (always execute when precondition satisfied). 

Here's an recommended way to write your Kea2's scripts. (You can use it as a template.)

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

You can read [Kea - Write your fisrt property](https://kea-docs.readthedocs.io/en/latest/part-keaUserManuel/first_property.html) for more details.

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


## Launch Kea2

We offer two ways to launch Kea2.

### 1. Launch Kea2 by shell commands

You can launch Kea2 by shell commands `kea2 run`.

`kea2 run` is consisted of two parts: the first part is the options for Kea2, and the second part is the sub-command and its arguments.

### 1.1 `kea2 run` Options

| arg | meaning | default | 
| --- | --- | --- |
| -s | The serial of your device, which can be found by `adb devices` | |
| -t | The transport id of your device, which can be found by `adb devices -l` | |
| -p | Specify the target app package name(s) to test (e.g., com.example.app). *Supports multiple packages: `-p pkg1 pkg2 pkg3`* | 
| -o | The ouput directory for logs and results | `output` |
| --agent |  {native, u2}. By default, `u2` is used and supports all the three important features of Kea2. If you hope to run the orignal Fastbot, please use `native`.| `u2` |
| --running-minutes | The time (in minutes) to run Kea2 | `10` |
| --max-step | The maxium number of monkey events to send (only available in `--agent u2`) | `inf` (infinite) |
| --throttle | The delay time (in milliseconds) between two monkey events | `200` |
| --driver-name | The name of driver used in the kea2's scripts. If `--driver-name d` is specified, you should use `d` to interact with a device, e..g, `self.d(..).click()`. |
| --log-stamp | the stamp for log file and result file. (e.g., if `--log-stamp 123` is specified, the log files will be named as `fastbot_123.log` and `result_123.json`.) | current time stamp |
| --profile-period | The period (in the numbers of monkey events) to profile coverage and collect UI screenshots. Specifically, the UI screenshots are stored on the SDcard of the mobile device, and thus you need to set an appropriate value according to the available device storage. | `25` |
| --take-screenshots | Take the UI screenshot at every Monkey event. The screenshots will be automatically pulled from the mobile device to your host machine periodically (the period is specified by `--profile-period`). |  |
| --pre-failure-screenshots | Dump n screenshots before failure. 0 means take screenshots for every step. This option is only valid when `--take-screenshots` is set. | `0` |
| --post-failure-screenshots | Dump n screenshots after failure. Should be smaller than `--pre-failure-screenshots`. This option is only valid when `--take-screenshots` is set. | `0` |
| --restart-app-period | The period (in the numbers of monkey events) to restart the app under test. | `0` (never restart) |
| --device-output-root | The root of device output dir. Kea2 will temporarily save the screenshots and result log into `"<device-output-root>/output_*********/"`. Make sure the root dir can be access. | `/sdcard` |
| --act-whitelist-file | Activity WhiteList File. Only the activities listed in the file can be explored during testing. | |
| --act-blacklist-file | Activity BlackList File. The activities listed in the file will be avoided during testing. | |

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
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10 --throttle 200 --driver-name d propertytest discover -p quicktest.py

# Launch Kea2 and load multiple scripts from the directory mytests/omni_notes
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10 --throttle 200 --driver-name d propertytest discover -s mytests/omni_notes -p test*.py
```

#### **1.2.2 (Expirimental Feature) `unitest` sub-command (hybrid test)**

> This feature is still under development. We are looking forward to your feedback! Contact us if you're interested in this feature.

`unittest` sub-command is used for feature 4 (Hybrid Testing). You can launch Kea2 with `kea run` with driver options and sub-command `unittest`. Same as `propertytest`, you can use [unittest discovery options](https://docs.python.org/3/library/unittest.html#test-discovery) to load your test cases.


#### **1.2.3 `--` sub-command (extra arguments)**

If you need to pass extra arguments to the underlying Fastbot, append `--` after the regular arguments, then list the extra arguments. For example, to set the touch event percentage to 30%, run:

```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10 --throttle 200 --driver-name d -- --pct-touch 30 unittest discover -p quicktest.py
```

### 2. Launch Kea2 by `unittest.main`

Like unittest, we can launch Kea2 through the method `unittest.main`.

Here is an example (named as `mytest.py`). You can see that the options are directly defined in the script.

```python
import unittest

from kea2 import KeaTestRunner, Options
from kea2.u2Driver import U2Driver

class MyTest(unittest.TestCase):
    ...
    # <your test methods here>

if __name__ == "__main__":
    KeaTestRunner.setOptions(
        Options(
            driverName="d",
            Driver=U2Driver,
            packageNames=[PACKAGE_NAME],
            # serial="emulator-5554",   # specify the serial
            maxStep=100,
            # running_mins=10,  # specify the maximal running time in minutes, default value is 10m
            # throttle=200,   # specify the throttle in milliseconds, default value is 200ms
            # agent='native'  # 'native' for running the vanilla Fastbot
        )
    )
    # Declare the KeaTestRunner
    unittest.main(testRunner=KeaTestRunner)
```

We can directly run the script `mytest.py` to launch Kea2, e.g.,
```bash
python3 mytest.py
```

Here's all the available options in `Options`.

```python
    # the driver_name in script (if self.d, then d.) 
    driverName: str = None
    # the driver (only U2Driver available now)
    Driver: AbstractDriver = None
    # list of package names. Specify the apps under test
    packageNames: List[str] = None
    # target device
    serial: str = None
    # target device with transport_id
    transport_id: str = None
    # test agent. "native" for stage 1 and "u2" for stage 1~3
    agent: Literal["u2", "native"] = "u2"
    # max step in exploration (availble in stage 2~3)
    maxStep: Union[str, float] = float("inf")
    # time(mins) for exploration
    running_mins: int = 10
    # time(ms) to wait when exploring the app
    throttle: int = 200
    # the output_dir for saving logs and results
    output_dir: str = "output"
    # the stamp for log file and result file, default: current time stamp
    log_stamp: str = None
    # the profiling period to get the coverage result.
    profile_period: int = 25
    # take screenshots for every step
    take_screenshots: bool = False
    # Screenshots before failure (Dump n screenshots before failure. 0 means take screenshots for every step)
    pre_failure_screenshots: int = 0
    # Screenshots after failure (Dump n screenshots before failure. Should be smaller than pre_failure_screenshots)
    post_failure_screenshots: int = 0
    # The root of output dir on device
    device_output_root: str = "/sdcard"
    # the debug mode
    debug: bool = False
    # Activity WhiteList File
    act_whitelist_file: str = None
    # Activity BlackList File
    act_blacklist_file: str = None
    # propertytest sub-commands args (eg. discover -s xxx -p xxx)
    propertytest_args: str = None
    # unittest sub-commands args (Feat 4)
    unittest_args: List[str] = None
    # Extra args (directly passed to fastbot)
    extra_args: List[str] = None
```


## Manage Kea2 reports

### Generate kea2 report (`kea2 report`)

The `kea2 report` command generates an HTML test report from existing test results. This command analyzes test data and creates a comprehensive visual report showing test execution statistics, coverage information, property violations, and crash details.

| arg | meaning | required | default |
| --- | --- | --- | --- |
| -p, --path | Path to the directory containing test results (res_* directory) | Yes | |

**Usage Examples:**

```bash
# Generate report from a test result directory
kea2 report -p res_20240101_120000

# Generate multiple reports
kea2 report -p ./output/res_20240101_120000 /Users/username/kea2_tests/res_20240102_130001
```

**What the report includes:**
- **Test Summary**: Total bugs found, execution time, coverage percentage
- **Property Test Results**: Execution statistics for each test property (preconditions satisfied, executed, failed, errors)
- **Code Coverage**: Activity coverage trends and detailed coverage information
- **Property Violations**: Detailed information about failed test properties with error traces
- **Crash Events**: Application crashes detected during testing
- **ANR Events**: Application Not Responding events
- **Screenshots**: UI screenshots captured during testing (if enabled)
- **Activity Traversal**: History of activities visited during testing

**Output:**
The report command generates:
- An HTML report file (`bug_report.html`) in the specified test result directory
- Interactive charts and visualizations for coverage and execution trends
- Detailed error information with stack traces for debugging

**Input Directory Structure:**
The command expects a test result directory with the following structure:
```
res_<timestamp>/
├── bug_report_config.json           # Report configuration (Includes test infos)
├── result_<timestamp>.json          # Property test results
├── output_<timestamp>/
│   ├── steps.log                    # Test execution steps
│   ├── coverage.log                 # Coverage data
│   ├── crash-dump.log               # Crash and ANR events
│   └── screenshots/                 # UI screenshots (if enabled)
└── property_exec_info_<timestamp>.json  # Property execution details
```

### Merge multiple test reports (`kea2 merge`)

The `kea2 merge` command allows you to merge multiple test report directories and generate a combined report. This is useful when you have run multiple test sessions and want to consolidate the results into a single comprehensive report.

| arg | meaning | required | default |
| --- | --- | --- | --- |
| -p, --paths | Paths to test report directories (res_* directories) to merge. At least 2 paths are required. | Yes | |
| -o, --output | Output directory for merged report | No | `merged_report_<timestamp>` |

**Usage Examples:**

```bash
# Merge two test report directories
kea2 merge -p res_20240101_120000 res_20240102_130000

# Merge multiple test report directories with custom output
kea2 merge -p res_20240101_120000 res_20240102_130000 res_20240103_140000 -o my_merged_report

# Enable debug mode while merging
kea2 -d merge -p res_20240101_120000 res_20240102_130000
```

**What gets merged:**
- Property test execution statistics (preconditions satisfied, executed, failed, errors)
- Code coverage data (activities covered, coverage percentage)
- Crash and ANR events
- Test execution steps and timing information

**Output:**
The merge command generates:
- A merged report directory containing consolidated data
- An HTML report (`merged_report.html`) with visual summaries
- Merge metadata including source directories and timestamp

## Debug Mode (`kea2 -d ...`)

You can enable debug mode by adding the `-d` option when using Kea2. In debug mode, Kea2 will print more detailed logs to help diagnose issues.

| arg | meaning | default |
| --- | --- | --- |
| -d | Enable debug mode | |

> ```bash
> # add -d to enable debug mode
> kea2 -d run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10 --throttle 200 --driver-name d unittest discover -p quicktest.py
> ```

## Examining the running statistics of scripts

If you want to examine whether your scripts have been executed or how many times they have been executed during testing. Open the file `result.json` after the testing is finished.

Here's an example.

```json
{
    "test_goToPrivacy": {
        "precond_satisfied": 8,
        "executed": 2,
        "fail": 0,
        "error": 1
    },
    ...
}
```

**How to read `result.json`**

Field | Description | Meaning
--- | --- | --- |
precond_satisfied | During exploration, how many times has the test method's precondition been satisfied? | Does we reach the state during exploration? 
executed | During UI testing, how many times the test method has been executed? | Has the test method ever been executed?
fail | How many times did the test method fail the assertions during UI testing? | When failed, the test method found a likely functional bug. 
error | How many times does the test method abort during UI tsting due to some unexpected errors (e.g. some UI widgets used in the test method cannot be found) | When some error happens, the script needs to be updated/fixed because the script leads to some unexpected errors.

## Configuration File

After executing `Kea2 init`, some configuration files will be generated in the `configs` directory. 
These configuration files belong to `Fastbot`, and their specific introductions are provided in [Introduction to configuration files](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E4%B8%93%E5%AE%B6%E7%B3%BB%E7%BB%9F).

## Update of User Configuration Files
When updating Kea2, the user's local configuration sometimes needs to be updated. (The latest kea2 version may not be compatible with the old configuration files.)

When runtime error detected, Kea2 will check whether the local configuration files are compatible with the current Kea2 version. If not, a warning message will be printed in the console. Update the local configuration files according to the following instructions.

1. Backup your local configuration files (in case of any unexpected issues during the update process).
2. delete all the configuration files under "/configs" in the project's root directory.
3. run `kea2 init` to generate the latest configuration files.
4. Merge your old configurations into the new configuration files according to your needs.

## App's Crash Bugs
Kea2 dumps the triggered crash bugs in the `fastbot_*.log` generated in the output directory specified by `-o`. You can search the keyword `FATAL EXCEPTION` in `fastbot_*.log` to find the concrete information of crash bugs.

These crash bugs are also recorded on your device. [See the Fastbot manual for details](https://github.com/bytedance/Fastbot_Android/blob/main/handbook-cn.md#%E7%BB%93%E6%9E%9C%E8%AF%B4%E6%98%8E).

## Interacting with Thrid-party Packages
Kea2 will block the third-party packages (e.g., ad packages) during exploration by default. If you want to interact with these packages, please add `--allow-any-starts` in [extra arguments](#---sub-command-extra-arguments) when launching Kea2.

For example:
```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10 --throttle 200 --driver -- --allow-any-starts propertytest discover -p quicktest.py
```

## Tips to Enhance Kea2 performance

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
