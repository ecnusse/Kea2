import random
import warnings
import types
import traceback
import json
import os

from collections import deque
from copy import deepcopy
from pathlib import Path
from time import perf_counter, sleep
from typing import Callable, Any, Deque, Dict, List, Literal, NewType, Tuple, Union
from contextvars import ContextVar
from unittest import TextTestRunner, registerResult, TestSuite, TestCase, TextTestResult, defaultTestLoader, SkipTest
from unittest import main as unittest_main
from dataclasses import dataclass, asdict
from datetime import datetime

import uiautomator2 as u2

from .absDriver import AbstractDriver
from .report.bug_report_generator import BugReportGenerator
from .resultSyncer import ResultSyncer
from .logWatcher import LogWatcher
from .utils import TimeStamp, catchException, getProjectRoot, getLogger, loadFuncsFromFile, timer
from .u2Driver import StaticU2UiObject, StaticXpathObject, U2Driver
from .fastbotManager import FastbotManager
from .adbUtils import ADBDevice
from .mixin import BetterConsoleLogExtensionMixin


hybrid_mode = ContextVar("hybrid_mode", default=False)


PRECONDITIONS_MARKER = "preconds"
PROB_MARKER = "prob"
MAX_TRIES_MARKER = "max_tries"
INTERRUPTABLE_MARKER = "interruptable"

logger = getLogger(__name__)


# Class Typing
PropName = NewType("PropName", str)
PropertyStore = NewType("PropertyStore", Dict[PropName, TestCase])


STAMP: str
LOGFILE: str
RESFILE: str
PROP_EXEC_RESFILE: str


def precondition(precond: Callable[[Any], bool]) -> Callable:
    """the decorator @precondition

    @precondition specifies when the property could be executed.
    A property could have multiple preconditions, each of which is specified by @precondition.
    """
    def accept(f):
        preconds = getattr(f, PRECONDITIONS_MARKER, tuple())
        setattr(f, PRECONDITIONS_MARKER, preconds + (precond,))
        return f

    return accept


def prob(p: float):
    """the decorator @prob

    @prob specify the propbability of execution when a property is satisfied.
    """
    p = float(p)
    if not 0 < p <= 1.0:
        raise ValueError("The propbability should between 0 and 1")

    def accept(f):
        setattr(f, PROB_MARKER, p)
        return f

    return accept


def max_tries(n: int):
    """the decorator @max_tries

    @max_tries specify the maximum tries of executing a property.
    """
    n = int(n)
    if not n > 0:
        raise ValueError("The maxium tries should be a positive integer.")

    def accept(f):
        setattr(f, MAX_TRIES_MARKER, n)
        return f

    return accept


def interruptable(strategy='default'):
    """the decorator @interruptable

    @interruptable specify the propbability of **fuzzing** when calling every line of code in a property.
    """

    def decorator(func):
        setattr(func, INTERRUPTABLE_MARKER, True)
        setattr(func, 'strategy', strategy)
        return func
    return decorator


@dataclass
class Options:
    """
    Kea and Fastbot configurations
    """
    # the driver_name in script (if self.d, then d.) 
    driverName: str = None
    # the driver (only U2Driver available now)
    Driver: AbstractDriver = U2Driver
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
    propertytest_args: List[str] = None
    # period (N steps) to restart the app under test
    restart_app_period: int = None
    # unittest sub-commands args (Feat 4)
    unittest_args: List[str] = None
    # Extra args (directly passed to fastbot)
    extra_args: List[str] = None
    # Whether to pull device FBM and merge into PC after test finishes
    upload_fbm: bool = False
    # Whether to pull device FBM(s) at start, merge with PC FBM and push merged back to device
    download_fbm: bool = False

    def __setattr__(self, name, value):
        if value is None:
            return
        super().__setattr__(name, value)
    
    def __post_init__(self):
        import logging
        logging.basicConfig(level=logging.DEBUG if self.debug else logging.INFO)

        if self.Driver:
            self._set_driver()

        global STAMP
        STAMP = self.log_stamp if self.log_stamp else TimeStamp().getTimeStamp()

        self._sanitize_stamp()

        self.output_dir = Path(self.output_dir).absolute() / f"res_{STAMP}"
        self.set_stamp()

        self._sanitize_args()

        _check_package_installation(self.packageNames)
        _save_bug_report_configs(self)
        
    def set_stamp(self, stamp: str = None):
        global STAMP, LOGFILE, RESFILE, PROP_EXEC_RESFILE
        if stamp:
            STAMP = stamp

        LOGFILE = f"fastbot_{STAMP}.log"
        RESFILE = f"result_{STAMP}.json"
        PROP_EXEC_RESFILE = f"property_exec_info_{STAMP}.json"

    def _sanitize_stamp(self):
        global STAMP
        illegal_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\n', '\r', '\t', '\0']
        for char in illegal_chars:
            if char in STAMP:
                raise ValueError(
                    f"char: `{char}` is illegal in --log-stamp. current stamp: {STAMP}"
                )
    
    def _sanitize_args(self):
        if not self.take_screenshots and self.pre_failure_screenshots > 0:
            raise ValueError("--pre-failure-screenshots should be 0 when --take-screenshots is not set.")
        
        if self.pre_failure_screenshots < self.post_failure_screenshots:
            raise ValueError("--post-failure-screenshots should be smaller than --pre-failure-screenshots.") 

        self.profile_period = int(self.profile_period)
        if self.profile_period < 1:
            raise ValueError("--profile-period should be greater than 0")

        self.throttle = int(self.throttle)
        if self.throttle < 0:
            raise ValueError("--throttle should be greater than or equal to 0")

        if self.agent == 'u2' and self.driverName == None:
            raise ValueError("--driver-name should be specified when customizing script in --agent u2")

    def _set_driver(self):
        target_device = dict()
        if self.serial:
            target_device["serial"] = self.serial
        if self.transport_id:
            target_device["transport_id"] = self.transport_id
        self.Driver.setDevice(target_device)
        ADBDevice.setDevice(self.serial, self.transport_id)
    
    def getKeaTestOptions(self, hybrid_test_count: int) -> "Options":
        """ Get the KeaTestOptions for hybrid test run when switching from unittest to kea2 test.
        hybrid_test_count: the count of hybrid test runs
        """
        if not self.unittest_args:
            raise RuntimeError("unittest_args is None. Cannot get KeaTestOptions from it")
        
        opts = deepcopy(self)
        
        time_stamp = TimeStamp().getTimeStamp()
        hybrid_test_stamp = f"{time_stamp}_hybrid_{hybrid_test_count}"
        
        opts.output_dir = self.output_dir / f"res_{hybrid_test_stamp}"
        
        opts.set_stamp(hybrid_test_stamp)
        opts.unittest_args = []
        return opts


def _check_package_installation(packageNames):
    installed_packages = set(ADBDevice().list_packages())

    for package in packageNames:
        if package not in installed_packages:
            logger.error(f"package {package} not installed. Abort.")
            raise ValueError(f"{package} not installed")


def _save_bug_report_configs(options: Options):
    output_dir = options.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    configs = {
        "driverName": options.driverName,
        "packageNames": options.packageNames,
        "take_screenshots": options.take_screenshots,
        "pre_failure_screenshots": options.pre_failure_screenshots,
        "post_failure_screenshots": options.post_failure_screenshots,
        "device_output_root": options.device_output_root,
        "log_stamp": options.log_stamp if options.log_stamp else STAMP,
        "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(output_dir / "bug_report_config.json", "w", encoding="utf-8") as fp:
        json.dump(configs, fp, indent=4)


@dataclass
class PropStatistic:
    precond_satisfied: int = 0
    executed: int = 0
    fail: int = 0
    error: int = 0
    

PBTTestResult = NewType("PBTTestResult", Dict[PropName, PropStatistic])


PropertyExecutionInfoStore = NewType("PropertyExecutionInfoStore", Deque["PropertyExecutionInfo"])
@dataclass
class PropertyExecutionInfo:
    startStepsCount: int
    propName: PropName
    state: Literal["start", "pass", "fail", "error"]
    tb: str


def getFullPropName(testCase: TestCase):
    return ".".join([
        testCase.__module__,
        testCase.__class__.__name__,
        testCase._testMethodName
    ])


class JsonResult(BetterConsoleLogExtensionMixin, TextTestResult):
    
    res: PBTTestResult
    lastExecutedInfo: PropertyExecutionInfo
    executionInfoStore: PropertyExecutionInfoStore = deque()

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.showAll = True

    @classmethod
    def setProperties(cls, allProperties: Dict):
        cls.res = dict()
        for testCase in allProperties.values():
            cls.res[getFullPropName(testCase)] = PropStatistic()

    def flushResult(self):
        global RESFILE, PROP_EXEC_RESFILE
        json_res = dict()
        for propName, propStatitic in self.res.items():
            json_res[propName] = asdict(propStatitic)
        with open(RESFILE, "w", encoding="utf-8") as fp:
            json.dump(json_res, fp, indent=4)

        while self.executionInfoStore:
            execInfo = self.executionInfoStore.popleft()
            with open(PROP_EXEC_RESFILE, "a", encoding="utf-8") as fp:
                fp.write(f"{json.dumps(asdict(execInfo))}\n")

    def addExcuted(self, test: TestCase, stepsCount: int):
        self.res[getFullPropName(test)].executed += 1

        self.lastExecutedInfo = PropertyExecutionInfo(
            propName=getFullPropName(test),
            state="start",
            tb="",
            startStepsCount=stepsCount
        )

    def addPrecondSatisfied(self, test: TestCase):
        self.res[getFullPropName(test)].precond_satisfied += 1

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.res[getFullPropName(test)].fail += 1
        self.lastExecutedInfo.state = "fail"
        self.lastExecutedInfo.tb = self._exc_info_to_string(err, test)

    def addError(self, test, err):
        super().addError(test, err)
        self.res[getFullPropName(test)].error += 1
        self.lastExecutedInfo.state = "error"
        self.lastExecutedInfo.tb = self._exc_info_to_string(err, test)

    def updateExectedInfo(self):
        if self.lastExecutedInfo.state == "start":
            self.lastExecutedInfo.state = "pass"

        self.executionInfoStore.append(self.lastExecutedInfo)

    def getExcuted(self, test: TestCase):
        return self.res[getFullPropName(test)].executed
    
    def printError(self, test):
        if self.lastExecutedInfo.state in ["fail", "error"]:
            flavour = self.lastExecutedInfo.state.upper()
            self.stream.writeln("")
            self.stream.writeln(self.separator1)
            self.stream.writeln("%s: %s" % (flavour, self.getDescription(test)))
            self.stream.writeln(self.separator2)
            self.stream.writeln("%s" % self.lastExecutedInfo.tb)
            self.stream.writeln(self.separator1)
            self.stream.flush()

    def logSummary(self):
        fails = sum(_.fail for _ in self.res.values())
        errors = sum(_.error for _ in self.res.values())

        logger.info(f"[Property Exectution Summary] Errors:{errors}, Fails:{fails}")


class KeaOptionSetter:
    options: Options = None

    @classmethod
    def setOptions(cls, options: Options):
        if not isinstance(options.packageNames, list) and len(options.packageNames) > 0:
            raise ValueError("packageNames should be given in a list.")
        if options.Driver is not None and options.agent == "native":
            logger.warning("[Warning] Can not use any Driver when runing native mode.")
            options.Driver = None
        cls.options = options
    

class KeaTestRunner(TextTestRunner, KeaOptionSetter):

    resultclass: JsonResult
    allProperties: PropertyStore
    _block_funcs: Dict[Literal["widgets", "trees"], List[Callable]] = None

    def _setOuputDir(self):
        output_dir = self.options.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        global LOGFILE, RESFILE, PROP_EXEC_RESFILE
        LOGFILE = output_dir / Path(LOGFILE)
        RESFILE = output_dir / Path(RESFILE)
        PROP_EXEC_RESFILE = output_dir / Path(PROP_EXEC_RESFILE)
        logger.info(f"Log file: {LOGFILE}")
        logger.info(f"Result file: {RESFILE}")
        logger.info(f"Property execution info file: {PROP_EXEC_RESFILE}")

    def run(self, test):


        # take device-side snapshots once at the beginning of the run
        try:
            self._copy_fbm()
        except Exception as e:
            logger.debug(f"Initial device snapshot failed: {e}")

        self.allProperties = dict()
        self.collectAllProperties(test)

        if len(self.allProperties) == 0:
            logger.warning("[Warning] No property has been found.")

        self._setOuputDir()

        JsonResult.setProperties(self.allProperties)
        self.resultclass = JsonResult

        result: JsonResult = self._makeResult()
        registerResult(result)
        result.failfast = self.failfast
        result.buffer = self.buffer
        result.tb_locals = self.tb_locals

        with warnings.catch_warnings():
            if self.warnings:
                # if self.warnings is set, use it to filter all the warnings
                warnings.simplefilter(self.warnings)
                # if the filter is 'default' or 'always', special-case the
                # warnings from the deprecated unittest methods to show them
                # no more than once per module, because they can be fairly
                # noisy.  The -Wd and -Wa flags can be used to bypass this
                # only when self.warnings is None.
                if self.warnings in ["default", "always"]:
                    warnings.filterwarnings(
                        "module",
                        category=DeprecationWarning,
                        message=r"Please use assert\w+ instead.",
                    )

            fb = FastbotManager(self.options, LOGFILE)
            fb.start()

            log_watcher = LogWatcher(LOGFILE)
            
            if self.options.agent == "u2":
                # initialize the result.json file
                result.flushResult()
                # setUp for the u2 driver
                self.scriptDriver = U2Driver.getScriptDriver(mode="proxy")
                fb.check_alive()
                
                fb.init(options=self.options, stamp=STAMP)

                resultSyncer = ResultSyncer(fb.device_output_dir, self.options)
                resultSyncer.run()
                start_time = perf_counter()
                fb_is_running = True
                self.stepsCount = 0

                while self.stepsCount < self.options.maxStep:
                    if self.shouldStop(start_time):
                        logger.info("Exploration time up (--running-minutes).")
                        break

                    if self.options.restart_app_period and self.stepsCount and self.stepsCount % self.options.restart_app_period == 0:
                        self.stepsCount += 1
                        logger.info(f"Sending monkeyEvent {self._monkey_event_count}")
                        logger.info("Kill all test apps to restart the app under test.")
                        for app in self.options.packageNames:
                            logger.info(f"Stopping app: {app}")
                            self.scriptDriver.app_stop(app)
                        sleep(3)
                        fb.sendInfo("kill_apps")
                        continue

                    try:
                        if fb.executed_prop:
                            fb.executed_prop = False
                            xml_raw = fb.dumpHierarchy()
                        else:
                            self.stepsCount += 1
                            logger.info(f"Sending monkeyEvent {self._monkey_event_count}")
                            xml_raw = fb.stepMonkey(self._monkeyStepInfo)
                        propsSatisfiedPrecond = self.getValidProperties(xml_raw, result)
                    except u2.HTTPError:
                        logger.info("Connection refused by remote.")
                        if fb.get_return_code() == 0:
                            logger.info("Exploration times up (--running-minutes).")
                            fb_is_running = False
                            break
                        raise RuntimeError("Fastbot Aborted.")

                    if self.options.profile_period and self.stepsCount % self.options.profile_period == 0:
                        resultSyncer.sync_event.set()

                    # Go to the next round if no precond satisfied
                    if len(propsSatisfiedPrecond) == 0:
                        continue

                    # get the random probability p
                    p = random.random()
                    propsNameFilteredByP = []
                    # filter the properties according to the given p
                    for propName, test in propsSatisfiedPrecond.items():
                        result.addPrecondSatisfied(test)
                        if getattr(test, PROB_MARKER, 1) >= p:
                            propsNameFilteredByP.append(propName)

                    if len(propsNameFilteredByP) == 0:
                        print("Not executed any property due to probability.", flush=True)
                        continue

                    execPropName = random.choice(propsNameFilteredByP)
                    test = propsSatisfiedPrecond[execPropName]
                    # Dependency Injection. driver when doing scripts
                    self.scriptDriver = U2Driver.getScriptDriver(mode="proxy")
                    
                    setattr(test, self.options.driverName, self.scriptDriver)

                    result.addExcuted(test, self.stepsCount)
                    fb.logScript(result.lastExecutedInfo)
                    try:
                        test(result)
                    finally:
                        result.printError(test)

                    result.updateExectedInfo()
                    fb.logScript(result.lastExecutedInfo)
                    fb.executed_prop = True
                    result.flushResult()

                if fb_is_running:
                    fb.stopMonkey()
                result.flushResult()
                resultSyncer.close()
                
            fb.join()
            print(f"Finish sending monkey events.", flush=True)
            log_watcher.close()

        # After run: compute per-device deltas and merge into PC core
        try:
            self._finalize_and_merge_deltas()
        except Exception as e:
            logger.debug(f"Finalize delta merge failed: {e}")

        result.logSummary()

        if self.options.agent == "u2":
            self._generate_bug_report()

        # self._upload_fbm()

        self.tearDown()
        return result
    
    def shouldStop(self, start_time):
        if self.options.running_mins is None:
            return False
        return (perf_counter() - start_time) >= self.options.running_mins * 60

    @property
    def _monkeyStepInfo(self):
        r = self._get_block_widgets()
        r["steps_count"] = self.stepsCount
        return r

    @property
    def _monkey_event_count(self):
        return f"({self.stepsCount} / {self.options.maxStep})" if self.options.maxStep != float("inf") else f"({self.stepsCount})"

    def _get_block_widgets(self):
        block_dict = self._getBlockedWidgets()
        block_widgets: List[str] = block_dict['widgets']
        block_trees: List[str] = block_dict['trees']
        logger.debug(f"Blocking widgets: {block_widgets}")
        logger.debug(f"Blocking trees: {block_trees}")
        return {
            "block_widgets": block_widgets,
            "block_trees": block_trees
        }

    def getValidProperties(self, xml_raw: str, result: JsonResult) -> PropertyStore:

        staticCheckerDriver = U2Driver.getStaticChecker(hierarchy=xml_raw)

        validProps: PropertyStore = dict()
        for propName, test in self.allProperties.items():
            valid = True
            prop = getattr(test, propName)
            p = getattr(prop, PROB_MARKER, 1)
            setattr(test, PROB_MARKER, p)
            # check if all preconds passed
            for precond in prop.preconds:
                # Dependency injection. Static driver checker for precond
                setattr(test, self.options.driverName, staticCheckerDriver)
                # excecute the precond
                try:
                    if not precond(test):
                        valid = False
                        break
                except u2.UiObjectNotFoundError as e:
                    valid = False
                    break
                except Exception as e:
                    logger.error(f"Error when checking precond: {getFullPropName(test)}")
                    traceback.print_exc()
                    valid = False
                    break
            # if all the precond passed. make it the candidate prop.
            if valid:
                if result.getExcuted(test) >= getattr(prop, MAX_TRIES_MARKER, float("inf")):
                    print(f"{getFullPropName(test)} has reached its max_tries. Skip.", flush=True)
                    continue
                validProps[propName] = test

        staticCheckerDriver.clear_cache()

        print(f"{len(validProps)} precond satisfied.", flush=True)
        if len(validProps) > 0:
            print("[INFO] Valid properties:",flush=True)
            print("\n".join([f'                - {getFullPropName(p)}' for p in validProps.values()]), flush=True)
        return validProps

    def collectAllProperties(self, test: TestSuite):
        """collect all the properties to prepare for PBT
        """

        def remove_setUp(testCase: TestCase):
            """remove the setup function in PBT
            """
            def setUp(self): ...
            testCase.setUp = types.MethodType(setUp, testCase)

        def remove_tearDown(testCase: TestCase):
            """remove the tearDown function in PBT
            """
            def tearDown(self): ...
            testCase.tearDown = types.MethodType(tearDown, testCase)

        def iter_tests(suite):
            for test in suite:
                if isinstance(test, TestSuite):
                    yield from iter_tests(test)
                else:
                    yield test

        # Traverse the TestCase to get all properties
        _result = TextTestResult(self.stream, self.descriptions, self.verbosity)
        for t in iter_tests(test):
            # Find all the _FailedTest (Caused by ImportError) and directly run it to report errors
            if type(t).__name__ == "_FailedTest":
                t(_result)
                continue
            testMethodName = t._testMethodName
            # get the test method name and check if it's a property
            testMethod = getattr(t, testMethodName)
            if hasattr(testMethod, PRECONDITIONS_MARKER):
                # remove the hook func in its TestCase
                remove_setUp(t)
                remove_tearDown(t)
                # save it into allProperties for PBT
                self.allProperties[testMethodName] = t
                print(f"[INFO] Load property: {getFullPropName(t)}", flush=True)
        # Print errors caused by ImportError
        _result.printErrors()

    @property
    def _blockWidgetFuncs(self):
        """
        load and process blocking functions from widget.block.py configuration file.

        Returns:
            dict: A dictionary containing two lists:
                - 'widgets': List of functions that block individual widgets
                - 'trees': List of functions that block widget trees
        """
        if self._block_funcs is None:
            self._block_funcs = {"widgets": list(), "trees": list()}
            root_dir = getProjectRoot()
            if root_dir is None or not os.path.exists(
                    file_block_widgets := root_dir / "configs" / "widget.block.py"
            ):
                print(f"[WARNING] widget.block.py not find", flush=True)

            def __get_block_widgets_module():
                import importlib.util
                module_name = "block_widgets"
                spec = importlib.util.spec_from_file_location(module_name, file_block_widgets)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod

            mod = __get_block_widgets_module()

            import inspect
            for func_name, func in inspect.getmembers(mod, inspect.isfunction):
                if func_name == "global_block_widgets":
                    self._block_funcs["widgets"].append(func)
                    setattr(func, PRECONDITIONS_MARKER, (lambda d: True,))
                    continue
                if func_name == "global_block_tree":
                    self._block_funcs["trees"].append(func)
                    setattr(func, PRECONDITIONS_MARKER, (lambda d: True,))
                    continue
                if func_name.startswith("block_") and not func_name.startswith("block_tree_"):
                    if getattr(func, PRECONDITIONS_MARKER, None) is None:
                        logger.warning(f"No precondition in block widget function: {func_name}. Default globally active.")
                        setattr(func, PRECONDITIONS_MARKER, (lambda d: True,))
                    self._block_funcs["widgets"].append(func)
                    continue
                if func_name.startswith("block_tree_"):
                    if getattr(func, PRECONDITIONS_MARKER, None) is None:
                        logger.warning(f"No precondition in block tree function: {func_name}. Default globally active.")
                        setattr(func, PRECONDITIONS_MARKER, (lambda d: True,))
                    self._block_funcs["trees"].append(func)

        return self._block_funcs


    def _getBlockedWidgets(self):
        """
           Executes all blocking functions to get lists of widgets and trees to be blocked during testing.

           Returns:
               dict: A dictionary containing:
                   - 'widgets': List of XPath strings for individual widgets to block
                   - 'trees': List of XPath strings for widget trees to block
           """
        def _get_xpath_widgets(func):
            blocked_set = set()
            script_driver = self.options.Driver.getScriptDriver()
            preconds = getattr(func, PRECONDITIONS_MARKER, [])

            def preconds_pass(preconds):
                try:
                    return all(precond(script_driver) for precond in preconds)
                except u2.UiObjectNotFoundError as e:
                    return False
                except Exception as e:
                    logger.error(f"Error processing precond. Check if precond: {e}")
                    traceback.print_exc()
                    return False

            if preconds_pass(preconds):
                try:
                    _widgets = func(U2Driver.getStaticChecker())
                    _widgets = _widgets if isinstance(_widgets, list) else [_widgets]
                    for w in _widgets:
                        if isinstance(w, (StaticU2UiObject, StaticXpathObject)):
                            xpath = w.selector_to_xpath(w.selector)
                            if xpath != '//error':
                                blocked_set.add(xpath)
                        else:
                            logger.error(f"block widget defined in {func.__name__} Not supported.")
                except Exception as e:
                    logger.error(f"Error processing blocked widgets in: {func}")
                    logger.error(e)
                    traceback.print_exc()
            return blocked_set

        result = {
            "widgets": set(),
            "trees": set()
        }

        for func in self._blockWidgetFuncs["widgets"]:
            widgets = _get_xpath_widgets(func)
            result["widgets"].update(widgets)

        for func in self._blockWidgetFuncs["trees"]:
            trees = _get_xpath_widgets(func)
            result["trees"].update(trees)

        result["widgets"] = list(result["widgets"] - result["trees"])
        result["trees"] = list(result["trees"])

        return result

    @timer(r"Generating bug report cost %cost_time seconds.")
    @catchException("Error when generating bug report")
    def _generate_bug_report(self):
        logger.info("Generating bug report")
        BugReportGenerator(self.options.output_dir).generate_report()

    def tearDown(self):
        """tearDown method. Cleanup the env.
        """
        if self.options.Driver:
            self.options.Driver.tearDown()
    
    def __del__(self):
        """tearDown method. Cleanup the env.
        """
        try:
            self.tearDown()
        except Exception:
            # Ignore exceptions in __del__ to avoid "Exception ignored" warnings
            pass


    def _finalize_and_merge_deltas(self):
        """Pull device fbms, compute deltas (snapshot->current) and merge deltas into PC core fbm.

        This function iterates over configured packages and uses pull_and_merge_to_pc which
        already implements snapshot-aware delta merging when a snapshot is present on device.
        """
        try:
            from kea2.fbm_parser import FBMMerger
        except Exception as e:
            logger.debug(f"FBM merger unavailable for finalize: {e}")
            return

        merger = FBMMerger()
        pkgs = getattr(self.options, 'packageNames', []) or []
        for pkg in pkgs:
            try:
                logger.info(f"Finalizing FBM delta for package: {pkg}")
                ok = merger.pull_and_merge_to_pc(pkg, device=self.options.serial,
                                                 transport_id=self.options.transport_id)
                if ok:
                    logger.info(f"Delta merge completed for package: {pkg}")
                else:
                    logger.debug(f"Delta merge reported failure for package: {pkg}")
            except Exception as e:
                logger.debug(f"Error finalizing delta for {pkg}: {e}")


    def _copy_fbm(self):
        """If options.download_fbm is True, create an on-device snapshot for each package by copying
        `/sdcard/fastbot_{pkg}.fbm` -> `/sdcard/fastbot_{pkg}.snapshot.fbm` using `adb shell cp`.

        Behavior:
        - Only runs if options.download_fbm is True.
        - Tries `adb shell cp` up to `max_retries` times with backoff. Does NOT perform pull/push.
        - Logs per-package success/failure and does not raise to avoid blocking startup.
        """
        # if not getattr(self.options, 'download_fbm', False):
        #     return

        try:
            from kea2.adbUtils import adb_shell
        except Exception:
            try:
                from adbUtils import adb_shell  # type: ignore
            except Exception as e:
                print(f"ADB utilities not available for creating device snapshot: {e}", flush=True)
                return

        import time
        import random

        pkgs = getattr(self.options, 'packageNames', []) or []
        for pkg in pkgs:
            src = f"/sdcard/fastbot_{pkg}.fbm"
            dst = f"/sdcard/fastbot_{pkg}.snapshot.fbm"

            # First check if the source FBM exists on device. If not, skip this package.
            try:
                # use a single-string shell command so adb runs: adb -s <dev> shell "test -f <src> && echo OK || echo NO"
                check_src = adb_shell([f'test -f "{src}" && echo OK || echo NO'], device=self.options.serial, transport_id=self.options.transport_id)
                if not (isinstance(check_src, str) and "OK" in check_src):
                    print(f"Source FBM not found on device for package {pkg}: {src}. Skipping snapshot creation.", flush=True)
                    continue
            except Exception as e:
                print(f"Failed to verify source FBM existence for {pkg}: {e}. Skipping.", flush=True)
                continue

            max_retries = 3
            success = False
            for attempt in range(1, max_retries + 1):
                try:
                    print(f"Attempt {attempt}: creating device snapshot: cp {src} {dst}", flush=True)
                    adb_shell(["cp", src, dst], device=self.options.serial, transport_id=self.options.transport_id)

                    # verify snapshot exists on device using a single-command form
                    try:
                        # verify snapshot exists on device using a single-string command (matches: adb shell "test -f ... && echo OK || echo NO")
                        verify = adb_shell([f'test -f "{dst}" && echo OK || echo NO'], device=self.options.serial, transport_id=self.options.transport_id)
                        if isinstance(verify, str) and "OK" in verify:
                            print(f"Snapshot created on device for package {pkg}: {dst}", flush=True)
                            success = True
                            break
                        else:
                            print(f"Snapshot verify failed on attempt {attempt} for {pkg}: {verify}", flush=True)
                    except Exception as ve:
                        print(f"Verification command failed after cp attempt {attempt} for {pkg}: {ve}", flush=True)
                except Exception as e:
                    print(f"adb shell cp attempt {attempt} failed for {pkg}: {e}", flush=True)

                # backoff before next attempt
                sleep_time = min(5.0, 0.5 * (2 ** (attempt - 1))) + random.uniform(0, 0.1)
                time.sleep(sleep_time)

            if not success:
                print(f"Giving up creating snapshot on device for {pkg} after {max_retries} attempts", flush=True)




class KeaTextTestResult(BetterConsoleLogExtensionMixin, TextTestResult):

    @property
    def wasFail(self):
        return self._wasFail

    def addError(self, test, err):
        self._wasFail = True
        return super().addError(test, err)

    def addFailure(self, test, err):
        self._wasFail = True
        return super().addFailure(test, err)

    def addSuccess(self, test):
        self._wasFail = False
        return super().addSuccess(test)

    def addSkip(self, test, reason):
        self._wasFail = False
        return super().addSkip(test, reason)

    def addExpectedFailure(self, test, err):
        self._wasFail = False
        return super().addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test):
        self._wasFail = False
        return super().addUnexpectedSuccess(test)


class HybridTestRunner(TextTestRunner, KeaOptionSetter):

    allTestCases: Dict[str, Tuple[TestCase, bool]]
    _common_teardown_func = None
    resultclass = KeaTextTestResult

    def __init__(self, stream = None, descriptions = True, verbosity = 1, failfast = False, buffer = False, resultclass = None, warnings = None, *, tb_locals = False):
        super().__init__(stream, descriptions, verbosity, failfast, buffer, resultclass, warnings, tb_locals=tb_locals)
        hybrid_mode.set(True)
        self.hybrid_report_dirs = []

    def run(self, test):

        self.allTestCases = dict()
        self.collectAllTestCases(test)
        if len(self.allTestCases) == 0:
            logger.warning("[Warning] No test case has been found.")

        result: KeaTextTestResult = self._makeResult()
        registerResult(result)
        result.failfast = self.failfast
        result.buffer = self.buffer
        result.tb_locals = self.tb_locals
        with warnings.catch_warnings():
            if self.warnings:
                # if self.warnings is set, use it to filter all the warnings
                warnings.simplefilter(self.warnings)
                # if the filter is 'default' or 'always', special-case the
                # warnings from the deprecated unittest methods to show them
                # no more than once per module, because they can be fairly
                # noisy.  The -Wd and -Wa flags can be used to bypass this
                # only when self.warnings is None.
                if self.warnings in ["default", "always"]:
                    warnings.filterwarnings(
                        "module",
                        category=DeprecationWarning,
                        message=r"Please use assert\w+ instead.",
                    )

            hybrid_test_count = 0
            for testCaseName, test in self.allTestCases.items():
                test, isInterruptable = test, getattr(test, "isInterruptable", False)

                # Dependency Injection. driver when doing scripts
                self.scriptDriver = U2Driver.getScriptDriver(mode="direct")
                setattr(test, self.options.driverName, self.scriptDriver)
                logger.info("Executing unittest testCase %s." % testCaseName)

                try:
                    test._common_setUp()
                    ret: KeaTextTestResult = test(result)
                    if ret.wasFail:
                        logger.error(f"Fail when running test.")
                    if isInterruptable and not ret.wasFail:
                        logger.info(f"Launch fastbot after interruptable script.")
                        hybrid_test_count += 1
                        hybrid_test_options = self.options.getKeaTestOptions(hybrid_test_count)

                        # Track the sub-report directory for later merging
                        self.hybrid_report_dirs.append(hybrid_test_options.output_dir)

                        argv = ["python3 -m unittest"] + hybrid_test_options.propertytest_args
                        KeaTestRunner.setOptions(hybrid_test_options)
                        unittest_main(module=None, argv=argv, testRunner=KeaTestRunner, exit=False)

                finally:
                    test._common_tearDown()
                    result.printErrors()

            # Auto-merge all hybrid test reports after all tests complete
            if len(self.hybrid_report_dirs) > 0:
                self._merge_hybrid_reports()

        return result

    def _merge_hybrid_reports(self):
        """
        Merge all hybrid test reports into a single merged report
        """
        try:
            from kea2.report.report_merger import TestReportMerger

            if len(self.hybrid_report_dirs) < 2:
                logger.info("Only one hybrid test report generated, skipping merge.")
                return

            main_output_dir = self.options.output_dir

            merger = TestReportMerger()
            merged_dir = merger.merge_reports(
                result_paths=self.hybrid_report_dirs,
                output_dir=main_output_dir
            )

            merge_summary = merger.get_merge_summary()
        except Exception as e:
            logger.error(f"Error merging hybrid test reports: {e}")

    def collectAllTestCases(self, test: TestSuite):
        """collect all the properties to prepare for PBT
        """

        def iter_tests(suite):
            for test in suite:
                if isinstance(test, TestSuite):
                    yield from iter_tests(test)
                else:
                    yield test

        funcs = loadFuncsFromFile(getProjectRoot() / "configs" / "teardown.py")
        setUp = funcs.get("setUp", None)
        tearDown = funcs.get("tearDown", None)
        if setUp is None:
            raise ValueError("setUp function not found in teardown.py.")
        if tearDown is None:
            raise ValueError("tearDown function not found in teardown.py.")

        # Traverse the TestCase to get all properties
        for t in iter_tests(test):

            def dummy(self): ...
            # remove the hook func in its TestCase
            t.setUp = types.MethodType(dummy, t)
            t.tearDown = types.MethodType(dummy, t)
            t._common_setUp = types.MethodType(setUp, t)
            t._common_tearDown = types.MethodType(tearDown, t)

            # check if it's interruptable (reflection)
            testMethodName = t._testMethodName
            testMethod = getattr(t, testMethodName)
            isInterruptable = hasattr(testMethod, INTERRUPTABLE_MARKER)

            # save it into allTestCases, if interruptable, mark as true
            setattr(t, "isInterruptable", isInterruptable)
            self.allTestCases[testMethodName] = t
            logger.info(f"Load TestCase: {getFullPropName(t)} , interruptable: {t.isInterruptable}")

    def __del__(self):
        """tearDown method. Cleanup the env.
        """
        try:
            if hasattr(self, 'options') and self.options and self.options.Driver:
                self.options.Driver.tearDown()
        except Exception:
            # Ignore exceptions in __del__ to avoid "Exception ignored" warnings
            pass


def kea2_breakpoint():
    """kea2 entrance. Call this function in TestCase.
    Kea2 will automatically switch to Kea2 Test in kea2_breakpoint in HybridTest mode.
    The normal launch in unittest will not be affected.
    """
    if hybrid_mode.get():
        raise SkipTest("Skip the test after the breakpoint and run kea2 in hybrid mode.")

