import random
import warnings
import types
import traceback
import json
import os
import functools

from copy import deepcopy
from pathlib import Path
from time import perf_counter, sleep
from typing import Callable, Any, Deque, Dict, List, Literal, NewType, Tuple, Union
from contextvars import ContextVar
from unittest import TextTestRunner, TestLoader, TestSuite, TestCase
from unittest import registerResult, TextTestResult, SkipTest
from unittest import main as unittest_main
from dataclasses import dataclass, asdict, fields, is_dataclass
from datetime import datetime
from fnmatch import fnmatchcase
import uiautomator2 as u2


from .typedefs import PRECONDITIONS_MARKER, PROB_MARKER, MAX_TRIES_MARKER, INTERRUPTABLE_MARKER
from .typedefs import PropertyStore
from .report.bug_report_generator import BugReportGenerator
from .resultSyncer import ResultSyncer
from .logWatcher import LogWatcher
from .utils import TimeStamp, StampManager, catchException, getProjectRoot, getLogger, loadFuncsFromFile, timer, getClassName, getFullPropName
from .u2Driver import StaticU2UiObject, StaticXpathObject, U2Driver, U2StaticDevice
from .fastbotManager import FastbotManager
from .adbUtils import ADBDevice
from .state import invariant, INVARIANT_MARKER
from .result import KeaJsonResult, KeaTextTestResult
from .fbm_plugin import merge_fbm

logger = getLogger(__name__)
hybrid_mode = ContextVar("hybrid_mode", default=False)


class KeaRuntimeError(RuntimeError):
    """Raised when Kea test run fails due to runtime errors."""




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
    driverName: str = "d"
    # list of package names. Specify the apps under test
    packageNames: List[str] = None
    # target device
    serial: str = None
    # target device with transport_id
    transport_id: str = None
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
    device_output_root: str = "/sdcard/.kea2"
    # the debug mode
    debug: bool = False
    # Activity WhiteList File
    act_whitelist_file: str = None
    # Activity BlackList File
    act_blacklist_file: str = None
    # Fastbot Agent
    fastbot_agent: Literal["double-sarsa", "sarsa"] = "double-sarsa"
    # propertytest sub-commands args (eg. discover -s xxx -p xxx)
    propertytest_args: List[str] = None
    # period (N steps) to restart the app under test
    restart_app_period: int = None
    # unittest sub-commands args (Feat 4)
    unittest_args: List[str] = None
    # Extra args (directly passed to fastbot)
    extra_args: List[str] = None
    # Whether to pull device FBM(s) at start, merge with PC FBM and push merged back to device
    merge_fbm: bool = False

    def __setattr__(self, name, value):
        if value is None:
            return
        super().__setattr__(name, value)

    def __post_init__(self):
        import logging
        logging.basicConfig(level=logging.DEBUG if self.debug else logging.INFO)

        self._set_driver()

        self.log_stamp = self.log_stamp if self.log_stamp else TimeStamp().getTimeStamp()
        self._sanitize_stamp(self.log_stamp)

        self.output_dir = Path(self.output_dir).absolute() / f"res_{self.log_stamp}"
        StampManager().set_stamp(self.log_stamp)
        StampManager().set_output_dir(self.output_dir)

        self._sanitize_args()

        _check_package_installation(self.packageNames)
        _save_bug_report_configs(self)
        _save_options_configs(self)

    def to_dict(self):
        from copy import deepcopy
        obj = deepcopy(self)
        for f in fields(obj):
            v = getattr(obj, f.name)
            if isinstance(v, Path):
                setattr(obj, f.name, str(v))
        return asdict(obj)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Options":
        data = dict(data)
        path_fields = {
            "output_dir",
            "device_output_root",
            "act_whitelist_file",
            "act_blacklist_file",
        }
        obj = cls.__new__(cls)
        for f in fields(cls):
            if f.name in data:
                value = data[f.name]
                if f.name in path_fields and value is not None:
                    value = Path(value)
                setattr(obj, f.name, value)
        return obj

    def set_stamp(self, stamp: str = None):
        """for hybrid test run. set a new stamp for the Options instance to save logs and results.
        """
        if stamp:
            self.log_stamp = stamp
            StampManager().set_stamp(stamp)

    def _sanitize_stamp(self, stamp: str):
        illegal_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\n', '\r', '\t', '\0']
        for char in illegal_chars:
            if char in stamp:
                raise ValueError(
                    f"char: `{char}` is illegal in --log-stamp. current stamp: {stamp}"
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

    def _set_driver(self):
        target_device = dict()
        if self.serial:
            target_device["serial"] = self.serial
        if self.transport_id:
            target_device["transport_id"] = self.transport_id
        U2Driver.setDevice(target_device)
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
        "log_stamp": options.log_stamp,
        "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(output_dir / "bug_report_config.json", "w", encoding="utf-8") as fp:
        json.dump(configs, fp, indent=4)

def _save_options_configs(self: "Options"):
    output_dir = Path(self.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    configs = self.to_dict()
    with open(output_dir / "options.json", "w", encoding="utf-8") as fp:
        json.dump(configs, fp, indent=4)


class KeaOptionSetter:
    options: Options = None

    @classmethod
    def setOptions(cls, options: Options):
        if not isinstance(options.packageNames, list) and len(options.packageNames) > 0:
            raise ValueError("packageNames should be given in a list.")
        cls.options = options


class KeaTestSuite(TestSuite):
    def addTest(self, test):
        if isinstance(test, TestCase):
            # inject the preconds, prob, max_tries, interruptable info into the test case
            func = getattr(test, test._testMethodName)
            for attr in {PRECONDITIONS_MARKER, INVARIANT_MARKER, PROB_MARKER, MAX_TRIES_MARKER, INTERRUPTABLE_MARKER}:
                if hasattr(func, attr):
                    val = getattr(func, attr)
                    setattr(test, attr, val)
        return super().addTest(test)


class KeaTestLoader(TestLoader):
    testMethodPrefix = ""
    suiteClass = KeaTestSuite

    def loadTestsFromTestCase(self, testCaseClass):
        # remove the setUp and tearDown functions in PBT
        def setUp(self): ...
        def tearDown(self): ...
        testCaseClass.setUp = types.MethodType(setUp, testCaseClass)
        testCaseClass.tearDown = types.MethodType(tearDown, testCaseClass)
        return super().loadTestsFromTestCase(testCaseClass)

    def getTestCaseNames(self, testCaseClass):
        """Return a sorted sequence of method names found within testCaseClass
        """
        def shouldIncludeMethod(attrname: str):
            if not attrname.startswith(self.testMethodPrefix):
                return False
            testFunc = getattr(testCaseClass, attrname)
            if not callable(testFunc):
                return False
            # exclude the test methods that are not properties
            if not hasattr(testFunc, PRECONDITIONS_MARKER) ^ hasattr(testFunc, INVARIANT_MARKER):
                return False
            fullName = f'%s.%s' % (getClassName(testCaseClass), attrname)
            self.__log_loading_info(testFunc, fullName)
            return self.testNamePatterns is None or \
                any(fnmatchcase(fullName, pattern) for pattern in self.testNamePatterns)
        testFnNames = list(filter(shouldIncludeMethod, dir(testCaseClass)))
        if self.sortTestMethodsUsing:
            testFnNames.sort(key=functools.cmp_to_key(self.sortTestMethodsUsing))
        return testFnNames

    def __log_loading_info(self, testFunc: Callable, fullName: str):
        if hasattr(testFunc, PRECONDITIONS_MARKER):
            print(f"[INFO] Load property: {fullName}", flush=True)
        if hasattr(testFunc, INVARIANT_MARKER):
            print(f"[INFO] Load invariant: {fullName}", flush=True)


keaTestLoader = KeaTestLoader()


class SetUpClassExtension:
    # setting up setUpClass
    _setup = set()

    def setUpClass(self: "KeaTestRunner", test: TestCase):
        testClass = test.__class__
        if not repr(testClass) in self._setup:
            self._setup.add(repr(testClass))
            script_driver = U2Driver.getScriptDriver(mode="proxy")
            setattr(testClass, self.options.driverName, script_driver)
            try:
                testClass.setUpClass()
            except Exception:
                logger.error(f"Error when executing {getClassName(testClass)}.setUpClass")
                import traceback
                traceback.print_exc()


class KeaTestRunner(TextTestRunner, KeaOptionSetter, SetUpClassExtension):

    resultclass: KeaJsonResult
    allProperties: PropertyStore
    allInvariants: PropertyStore
    _block_funcs: Dict[Literal["widgets", "trees"], List[Callable]] = None

    def _setOuputDir(self):
        output_dir = self.options.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp_manager = StampManager()
        if not stamp_manager.stamp:
            stamp_manager.set_stamp(self.options.log_stamp or TimeStamp().getTimeStamp())
        stamp_manager.set_output_dir(output_dir)
        logger.info(f"Log file: {stamp_manager.log_file}")
        logger.info(f"Result file: {stamp_manager.result_file}")
        logger.info(f"Property execution info file: {stamp_manager.prop_exec_file}")

    @merge_fbm
    @catchException("Unexpected Error in KeaTestRunner.run")
    def run(self, test):
        self.validateAndCollectProperties(test)

        if len(self.allProperties) == 0:
            logger.warning("No property has been found.")

        self._setOuputDir()

        # Setup JsonResult
        KeaJsonResult.setProperties(self.allProperties)
        KeaJsonResult.setInvariants(self.allInvariants)
        self.resultclass = KeaJsonResult
        result: KeaJsonResult = self._makeResult()
        registerResult(result)

        result.failfast = self.failfast
        result.buffer = self.buffer
        result.tb_locals = self.tb_locals

        with warnings.catch_warnings():
            stamp_manager = StampManager()
            fb = FastbotManager(self.options, stamp_manager.log_file)
            fb.start()

            log_watcher = LogWatcher(stamp_manager.log_file)
            
            # initialize the result.json file
            result.flushResult()
            # setUp for the u2 driver
            self.scriptDriver = U2Driver.getScriptDriver(mode="proxy")

            for test in {**self.allProperties, **self.allInvariants}.values():
                self.setUpClass(test)

            fb.check_alive()
            fb.init(options=self.options, stamp=stamp_manager.stamp)

            resultSyncer = ResultSyncer(fb.device_output_dir, self.options)
            resultSyncer.run()
            start_time = perf_counter()
            fb_is_running = True
            self.stepsCount = 0

            # Kea2 main testing loop
            try:
                while self.stepsCount < self.options.maxStep:
                    logger.info(f"[Property based testing] [New Iteration] Elapsed: {perf_counter()-start_time:.1f}s")
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
                        # determine whether to stepMonkey (normal step) or dumpHierarchy (after executing a property)
                        # stepMonkey will change the ui state and return the new ui hierarchy
                        # dumpHierarchy will just return the current ui hierarchy
                        # this is to avoid losing the ui state after executing a property
                        xml_raw: str = ""
                        if fb.executed_prop:
                            fb.executed_prop = False
                            xml_raw = fb.dumpHierarchy()
                        else:
                            self.stepsCount += 1
                            logger.info(f"Sending monkeyEvent {self._monkey_event_count}")
                            xml_raw = fb.stepMonkey(self._monkeyStepInfo)
                    # If the connection is refused, fastbot might have stpped running
                    except u2.HTTPError:
                        logger.info("Connection refused by remote.")
                        # If fastbot has exited normally, end the testing process
                        if fb.get_return_code() == 0:
                            logger.info("Exploration times up (--running-minutes).")
                            fb_is_running = False
                            break
                        else:
                            import traceback
                            traceback.print_exc()
                            raise RuntimeError("Fastbot Aborted.")

                    if not xml_raw:
                        logger.warning("Empty ui hierarchy returned. Skip this step.")
                        continue

                    result.setCurrentStepsCount(self.stepsCount)

                    # check all invariants
                    staticCheckerDriver = U2Driver.getStaticChecker(hierarchy=xml_raw)
                    if self.allInvariants:
                        print(f"[INFO] Checking {len(self.allInvariants)} invariants...", flush=True)
                    for _, test in self.allInvariants.items():
                        setattr(test, self.options.driverName, staticCheckerDriver)
                        try:
                            test(result)
                        finally:
                            result.printError(test)
                            result.updateExecutionInfo(test)
                            if result.lastInvariantInfo.state in {"fail", "error"}:
                                fb.logScript(result.lastInvariantInfo)

                    # Trigger the result syncer to get the coverage result periodically (Set by profile_period)
                    if self.options.profile_period and self.stepsCount % self.options.profile_period == 0:
                        resultSyncer.sync_event.set()

                    # get the checkable properties
                    checkableProperties = self.getCheckableProperties(xml_raw, result, staticCheckerDriver)

                    if not checkableProperties:
                        continue

                    self.scriptDriver = U2Driver.getScriptDriver(mode="proxy")

                    # randomly select a property to execute
                    propertyName = random.choice(checkableProperties)
                    test = self.allProperties[propertyName]
                    result.addExcutedProperty(test, self.stepsCount)
                    fb.logScript(result.lastPropertyInfo)
                    # Dependency Injection. driver when doing scripts
                    setattr(test, self.options.driverName, self.scriptDriver)
                    try:
                        test(result)
                    finally:
                        result.printError(test)
                    result.updateExecutionInfo(test)
                    fb.logScript(result.lastPropertyInfo)
                    fb.executed_prop = True
                    result.flushResult()
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt received. Stopping the testing process.")
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise KeaRuntimeError("Kea test run interrupted by exception.") from e
            finally:
                if fb_is_running:
                    fb.stopMonkey()
                result.flushResult()
                resultSyncer.close()

                fb.join()
                print(f"Finish sending monkey events.", flush=True)
                log_watcher.close()
                result.has_crash_or_anr = log_watcher.has_crash_or_anr

                result.logSummary()
                self._generate_bug_report()

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

    def getCheckableProperties(self, xml_raw: str, result: KeaJsonResult, staticCheckerDriver: U2StaticDevice) -> List:
        # Get the precondition satisfied properties
        precondSatisfiedProperties = list()
        for propName, test in self.allProperties.items():
            valid = True
            property = getattr(test, test._testMethodName)
            # check if all preconds passed
            for precond in property.preconds:
                # Dependency injection. Static driver checker for precond
                setattr(test, self.options.driverName, staticCheckerDriver)
                # excecute the precondition
                try:
                    if not precond(test):
                        valid = False
                        break
                except u2.UiObjectNotFoundError as e:
                    valid = False
                    break
                except Exception as e:
                    logger.error(f"Error when checking precond: {propName}")
                    traceback.print_exc()
                    valid = False
                    break
            # if all the precond passed. make it the candidate prop.
            if valid:
                result.addPropertyPrecondSatisfied(test)
                precondSatisfiedProperties.append(propName)

        # get the checkable properties
        checkableProperties = []
        u = random.random()    # sample the execution probability threshold u ~ U(0, 1)
        for propName in precondSatisfiedProperties:
            test = self.allProperties[propName]
            p = getattr(test, PROB_MARKER, 1)
            max_tries = getattr(test, MAX_TRIES_MARKER, float("inf"))
            # filter the properties according to the given u
            if p < u:
                print(f"{propName} will not execute due to probability (@prob). Skip.", flush=True)
                continue
            # filter the property reached max_tries
            if result.getExcutedProperty(test) >= max_tries:
                print(f"{propName} has reached its max_tries {max_tries} (@max_tries). Skip.", flush=True)
                continue
            checkableProperties.append(propName)

        # log the checkable properties information
        if len(checkableProperties) > 0:
            print(f"[INFO] {len(checkableProperties)} Checkable properties:", flush=True)
            print("\n".join([f'                - {_}' for _ in checkableProperties]), flush=True)
        else:
            print(f"[INFO] {len(checkableProperties)} Checkable property.", flush=True)

        return checkableProperties

    def validateAndCollectProperties(self, test: TestSuite):
        """ validate and collect all the properties to prepare for PBT
        :Why validate here?:
            Because some properties may not be importable due to ImportError (e.g., missing dependencies
            or syntax errors). We need to validate them before PBT to avoid runtime errors.
        """
        self.allProperties = dict()
        self.allInvariants = dict()

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
            if hasattr(t, PRECONDITIONS_MARKER):
                self.allProperties[getFullPropName(t)] = t
            if hasattr(t, INVARIANT_MARKER):
                self.allInvariants[getFullPropName(t)] = t
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
            script_driver = U2Driver.getScriptDriver()
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
        U2Driver.tearDown()
    
    def __del__(self):
        """tearDown method. Cleanup the env.
        """
        try:
            self.tearDown()
        except Exception:
            # Ignore exceptions in __del__ to avoid "Exception ignored" warnings
            pass

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
                        unittest_main(module=None, argv=argv, testRunner=KeaTestRunner, testLoader=keaTestLoader, exit=False)
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
            if hasattr(self, 'options') and self.options:
                U2Driver.tearDown()
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
