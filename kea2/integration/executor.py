import io
import random
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple
from unittest import TestCase, TestSuite

from lxml import etree

from kea2.adbUtils import ADBDevice
from kea2.keaUtils import KeaTestRunner, Options, keaTestLoader
from kea2.u2Driver import U2Driver, U2StaticDevice, _HindenWidgetFilter
from kea2.utils import getFullPropName, getProjectRoot

from .errors import EngineIntegrationError
from .contracts import ExecuteResult, Kea2Summary


class _PrecondCounter:
    """Adapter for KeaTestRunner.getCheckableProperties."""

    def __init__(self, executed_count: Dict[str, int]):
        self._executed_count = executed_count
        self.precondition_satisfied = 0

    def addPropertyPrecondSatisfied(self, test: TestCase) -> None:
        self.precondition_satisfied += 1

    def getExcutedProperty(self, test: TestCase) -> int:
        return self._executed_count.get(getFullPropName(test), 0)


class _ReusableKeaRunner(KeaTestRunner):
    """
    Thin KeaTestRunner wrapper that only reuses:
    - validateAndCollectProperties (property loader)
    - getCheckableProperties (precondition/prob/max_tries filter)
    """

    def __init__(self, driver_name: str):
        super().__init__(stream=io.StringIO(), descriptions=False, verbosity=0)
        self.options = SimpleNamespace(driverName=driver_name)

    def load_properties_from_suite(self, suite: TestSuite) -> Dict[str, TestCase]:
        self.validateAndCollectProperties(suite)
        return dict(self.allProperties)

    def get_checkable_properties(
        self,
        ui_xml: str,
        executed_count: Dict[str, int],
        static_checker: U2StaticDevice,
    ) -> Tuple[List[str], int]:
        counter = _PrecondCounter(executed_count=executed_count)
        checkable = self.getCheckableProperties(
            xml_raw=ui_xml,
            result=counter,
            staticCheckerDriver=static_checker,
        )
        return list(checkable), counter.precondition_satisfied


class PropertyEngine:
    """In-memory runtime for third-party engine callbacks."""

    def __init__(self, config: Options):
        self.config = config
        self._loaded = False
        self._all_properties: Dict[str, TestCase] = {}
        self._executed_count: Dict[str, int] = {}
        self._setup_classes = set()
        self._script_driver = None
        self._static_checker = None
        self._runner = _ReusableKeaRunner(driver_name=config.driverName)
        self._summary = Kea2Summary()

    def initialize(self) -> None:
        self._set_target_device()
        self._script_driver = U2Driver.getScriptDriver(mode="direct")
        self._static_checker = U2StaticDevice(self._script_driver)
        suite = self._discover_property_suite()
        self._all_properties = self._runner.load_properties_from_suite(suite)
        if not self._all_properties:
            raise EngineIntegrationError("NO_PROPERTIES", "No property methods found via discovery")
        self._executed_count = {name: 0 for name in self._all_properties}
        self._summary.loaded_properties = list(self._all_properties.keys())
        self._loaded = True

    def stop(self) -> None:
        self._loaded = False

    def execute_property(self, ui_xml: Optional[str] = None) -> ExecuteResult:
        if not self._loaded:
            raise EngineIntegrationError("NOT_INITIALIZED", "Kea2 runtime is not initialized")
        precondition_satisfied = 0
        properties_executed = 0
        errors = 0
        error_properties: List[str] = []

        try:
            cur_ui = ui_xml or self.dump_ui()
            static_checker = self._get_static_checker(cur_ui)
            checkable, precondition_satisfied = self._runner.get_checkable_properties(
                ui_xml=cur_ui,
                executed_count=self._executed_count,
                static_checker=static_checker,
            )

            if checkable:
                prop_name = random.choice(checkable)
                prop_error = self._execute_one_property(prop_name)
                errors += prop_error
                if prop_error:
                    error_properties.append(prop_name)
                properties_executed = 1
        except Exception:
            # Step-level isolation: never crash the whole engine loop on one step failure.
            errors = 1
            if not error_properties:
                error_properties.append("__engine__")

        step_result = ExecuteResult(
            precondition_satisfied=precondition_satisfied,
            properties_executed=properties_executed,
            errors=errors,
            error_properties=error_properties,
        )
        self._summary.total_precondition_satisfied += precondition_satisfied
        self._summary.total_properties_executed += properties_executed
        self._summary.total_errors += errors
        return step_result

    def get_result(self) -> Kea2Summary:
        return self._summary

    def dump_ui(self) -> str:
        xml = self._script_driver.dump_hierarchy()
        if not xml:
            raise EngineIntegrationError("EMPTY_UI", "Empty UI hierarchy returned")
        return xml

    def _execute_one_property(self, prop_name: str) -> int:
        test = self._all_properties[prop_name]
        self._ensure_setup_class(test)
        setattr(test, self.config.driverName, self._script_driver)
        self._executed_count[prop_name] = self._executed_count.get(prop_name, 0) + 1
        try:
            test.debug()
            return 0
        except Exception:
            return 1

    def _set_target_device(self) -> None:
        if not self.config.serial:
            raise EngineIntegrationError("INVALID_CONFIG", "serial (device id) is required")
        U2Driver.setDevice({"serial": self.config.serial})
        ADBDevice.setDevice(serial=self.config.serial)

    def _discover_property_suite(self) -> TestSuite:
        start_dir, pattern, top_level_dir = self._resolve_discover_args()
        return keaTestLoader.discover(
            start_dir=start_dir,
            pattern=pattern,
            top_level_dir=top_level_dir,
        )

    def _resolve_discover_args(self) -> Tuple[str, str, Optional[str]]:
        args = list(self.config.propertytest_args or [])
        if args and args[0] == "discover":
            args = args[1:]

        start_dir = "."
        pattern = "test*.py"
        top_level_dir: Optional[str] = None

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

    def _ensure_setup_class(self, test: TestCase) -> None:
        test_class = test.__class__
        class_id = repr(test_class)
        if class_id in self._setup_classes:
            return
        self._setup_classes.add(class_id)
        setattr(test_class, self.config.driverName, self._script_driver)
        test_class.setUpClass()

    def _get_static_checker(self, hierarchy: str) -> U2StaticDevice:
        if self._static_checker is None:
            self._static_checker = U2StaticDevice(self._script_driver)
        self._static_checker.clear_cache()
        self._static_checker.xml = etree.fromstring(hierarchy.encode("utf-8"))
        _HindenWidgetFilter(self._static_checker.xml)
        return self._static_checker
