import random
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple
from unittest import TestCase, TestSuite

import uiautomator2 as u2
from lxml import etree

from kea2.adbUtils import ADBDevice
from kea2.keaUtils import keaTestLoader
from kea2.typedefs import MAX_TRIES_MARKER, PRECONDITIONS_MARKER, PROB_MARKER
from kea2.u2Driver import U2Driver, U2StaticDevice, _HindenWidgetFilter
from kea2.utils import getFullPropName, getProjectRoot

from .errors import EngineIntegrationError
from .models import SessionConfig, StepResult


class EngineRuntime:
    """
    Runtime for engine-driven step callbacks.

    This is a scaffold that keeps the protocol stable. 
    """

    def __init__(self, session_id: str, config: SessionConfig, discover_spec: Dict[str, Any]):
        """Bind session config and discovery spec for step execution.

        Args:
            session_id: Session identifier.
            config: SessionConfig instance.
            discover_spec: Property discovery options.
        """
        self.session_id = session_id
        self.config = config
        self.discover_spec = discover_spec or {}
        self._loaded = False
        self.all_properties: Dict[str, TestCase] = {}
        self._executed_count: Dict[str, int] = {}
        self._setup_classes = set()
        self._script_driver = None
        self._static_checker = None

    def load_properties(self) -> None:
        """
        Discover and collect property scripts (Feature 2 only).

        Returns:
            None.
        """
        self._set_target_device()
        self._script_driver = U2Driver.getScriptDriver(mode="direct")
        self._static_checker = U2StaticDevice(self._script_driver)
        suite = self._discover_property_suite()
        self._collect_properties(suite)
        self._executed_count = {name: 0 for name in self.all_properties}
        self._loaded = True

    def dump_ui(self) -> str:
        """
        Dump current hierarchy from direct uiautomator2 channel.

        Returns:
            ui_xml: UI hierarchy XML string.
        """
        xml = self._script_driver.dump_hierarchy()
        if not xml:
            raise EngineIntegrationError("EMPTY_UI", "Empty UI hierarchy returned")
        return xml
        
    def get_checkable_properties(self, ui_xml: str) -> Tuple[List[str], int]:
        """
        Evaluate preconditions and filter properties by @prob / @max_tries.

        Args:
            ui_xml: UI hierarchy XML string.

        Returns:
            (checkable property names, precondition satisfied count)
        """
        static_checker = self._get_static_checker(ui_xml)
        precond_satisfied: List[str] = []
        for prop_name, test in self.all_properties.items():
            method = getattr(test, test._testMethodName)
            preconds = getattr(method, PRECONDITIONS_MARKER, tuple())
            valid = True
            setattr(test, self.config.driver_name, static_checker)
            for precond in preconds:
                if not precond(test):
                    valid = False
                    break
        
            if valid:
                precond_satisfied.append(prop_name)

        u_threshold = random.random()
        checkable: List[str] = []
        for prop_name in precond_satisfied:
            test = self.all_properties[prop_name]
            p = getattr(test, PROB_MARKER, 1.0)
            max_tries = getattr(test, MAX_TRIES_MARKER, float("inf"))
            if p < u_threshold:
                continue
            if self._executed_count.get(prop_name, 0) >= max_tries:
                continue
            checkable.append(prop_name)
        return checkable, len(precond_satisfied)

    def execute_one_property(self, prop_name: str, step_id: int) -> int:
        """
        Execute one property and return 1 on error/failure, otherwise 0.

        Args:
            prop_name: Fully qualified property name.
            step_id: Engine step index.

        Returns:
            errors: 1 if error, otherwise 0.
        """
        test = self.all_properties[prop_name]
        self._ensure_setup_class(test)
        setattr(test, self.config.driver_name, self._script_driver)
        self._executed_count[prop_name] = self._executed_count.get(prop_name, 0) + 1
        try:
            # debug() executes setUp/testMethod/tearDown and surfaces exceptions directly.
            test.debug()
            return 0
        except Exception:
            return 1

    def run_step(self, step_id: int, ui_xml: Optional[str] = None, event_meta: Optional[Dict[str, Any]] = None) -> StepResult:
        """Run one engine step and return aggregated execution stats.

        Args:
            step_id: Engine step index.
            ui_xml: Optional pre-dumped UI hierarchy XML.
            event_meta: Optional event metadata from the engine.

        Returns:
            result: StepResult instance.
        """
        if not self._loaded:
            self.load_properties()

        start = perf_counter()
        loop_count = 0
        precondition_satisfied = 0
        properties_executed = 0
        errors = 0
        error_properties: List[str] = []
        stop_reason = "no_match"

        cur_ui = ui_xml
        while True:
            if loop_count >= self.config.max_properties_per_step:
                stop_reason = "property_quantity_limit"
                break
            elapsed = perf_counter() - start
            if elapsed >= self.config.per_step_timeout_sec:
                stop_reason = "timeout"
                break

            if cur_ui is None:
                cur_ui = self.dump_ui()

            checkable, precond_satisfied_count = self.get_checkable_properties(cur_ui)
            precondition_satisfied += precond_satisfied_count
            if not checkable:
                stop_reason = "no_match"
                break

            prop_name = self._pick_property(checkable)
            prop_error = self.execute_one_property(prop_name=prop_name, step_id=step_id)
            errors += prop_error
            if prop_error:
                error_properties.append(prop_name)
            properties_executed += 1
            loop_count += 1
            cur_ui = None

        return StepResult(
            session_id=self.session_id,
            step_id=step_id,
            precondition_satisfied=precondition_satisfied,
            properties_executed=properties_executed,
            errors=errors,
            stop_reason=stop_reason,
            error_properties=error_properties,
            event_meta=event_meta,
        )

    def _set_target_device(self) -> None:
        """Bind runtime device to both U2 and ADB helpers.

        Returns:
            None.
        """
        if not self.config.device_id:
            raise EngineIntegrationError("INVALID_CONFIG", "device_id is required")
        U2Driver.setDevice({"serial": self.config.device_id})
        ADBDevice.setDevice(serial=self.config.device_id)

    def _discover_property_suite(self) -> TestSuite:
        """Discover property tests via unittest discovery.

        Returns:
            suite: unittest.TestSuite containing discovered tests.
        """
        start_dir, pattern, top_level_dir = self._resolve_discover_args()
        return keaTestLoader.discover(
            start_dir=start_dir,
            pattern=pattern,
            top_level_dir=top_level_dir,
        )
        
    def _resolve_discover_args(self) -> Tuple[str, str, Optional[str]]:
        """Resolve discovery arguments from discover_spec.

        Returns:
            start_dir: Absolute start directory.
            pattern: Filename pattern for tests.
            top_level_dir: Optional top-level directory.
        """
        args = list(self.discover_spec.get("propertytest_args") or [])
        if args and args[0] == "discover":
            args = args[1:]

        start_dir = self.discover_spec.get("start_dir")
        pattern = self.discover_spec.get("pattern")
        top_level_dir = self.discover_spec.get("top_level_dir")

        i = 0
        while i < len(args):
            token = args[i]
            if token in ("-s", "--start-directory") and i + 1 < len(args):
                start_dir = args[i + 1]
                i += 2
                continue
            if token in ("-p", "--pattern") and i + 1 < len(args):
                pattern = args[i + 1]
                i += 2
                continue
            if token in ("-t", "--top-level-directory") and i + 1 < len(args):
                top_level_dir = args[i + 1]
                i += 2
                continue
            i += 1

        project_root = getProjectRoot() or Path.cwd()
        start_dir = start_dir or "."
        pattern = pattern or "test*.py"

        start_path = Path(start_dir)
        if not start_path.is_absolute():
            start_path = project_root / start_path
        if not start_path.exists():
            raise EngineIntegrationError("DISCOVER_INVALID", f"start_dir not found: {start_path}")

        top_level_path = None
        if top_level_dir:
            top_level_path = Path(top_level_dir)
            if not top_level_path.is_absolute():
                top_level_path = project_root / top_level_path
            if not top_level_path.exists():
                raise EngineIntegrationError("DISCOVER_INVALID", f"top_level_dir not found: {top_level_path}")

        return str(start_path), str(pattern), str(top_level_path) if top_level_path else None

    def _collect_properties(self, suite: TestSuite) -> None:
        """Collect property test cases from the discovered suite.

        Args:
            suite: TestSuite from discovery.

        Returns:
            None.
        """
        self.all_properties = {}
        for test in self._iter_tests(suite):
            if type(test).__name__ == "_FailedTest":
                raise EngineIntegrationError("DISCOVER_IMPORT_ERROR", f"Import error in discovered tests: {test}")
            if hasattr(test, PRECONDITIONS_MARKER):
                self.all_properties[getFullPropName(test)] = test
        if not self.all_properties:
            raise EngineIntegrationError("NO_PROPERTIES", "No property methods found via discovery")

    def _iter_tests(self, suite: TestSuite):
        """Yield all leaf tests from a nested TestSuite.

        Args:
            suite: TestSuite or nested TestSuite.

        Yields:
            test: unittest.TestCase instances.
        """
        for t in suite:
            if isinstance(t, TestSuite):
                yield from self._iter_tests(t)
            else:
                yield t

    def _ensure_setup_class(self, test: TestCase) -> None:
        """Call setUpClass once per TestCase class.

        Args:
            test: TestCase instance.

        Returns:
            None.
        """
        test_class = test.__class__
        class_id = repr(test_class)
        if class_id in self._setup_classes:
            return
        self._setup_classes.add(class_id)
        setattr(test_class, self.config.driver_name, self._script_driver)
        test_class.setUpClass()

    def _pick_property(self, candidates: List[str]) -> str:
        """Select one property from candidates.

        Args:
            candidates: List of property names.

        Returns:
            prop_name: Selected property name.
        """
        if not candidates:
            raise EngineIntegrationError("NO_CANDIDATE", "No checkable property candidates")
        return random.choice(candidates)

    def _get_static_checker(self, hierarchy: str) -> U2StaticDevice:
        """
        Build static checker from current hierarchy while reusing the same direct
        uiautomator2 connection.

        Args:
            hierarchy: UI hierarchy XML string.

        Returns:
            checker: U2StaticDevice instance with loaded hierarchy.
        """
        if self._static_checker is None:
            self._static_checker = U2StaticDevice(self._script_driver)
        
        self._static_checker.clear_cache()
        self._static_checker.xml = etree.fromstring(hierarchy.encode("utf-8"))
        _HindenWidgetFilter(self._static_checker.xml)
        return self._static_checker
