from dataclasses import asdict
from enum import Enum
import json
from typing import Deque, Dict
from unittest import TestCase, TextTestResult
from collections import deque

from .state import INVARIANT_MARKER
from .typedefs import PBTTestResult, PropertyExecutionInfo, PropStatistic
from .utils import StampManager, getLogger, getFullPropName


logger = getLogger(__name__)


class CheckKind(Enum):
    PROPERTY = "property"
    INVARIANT = "invariant"


def get_check_kind(test: TestCase) -> CheckKind:
    if hasattr(test, INVARIANT_MARKER):
        return CheckKind.INVARIANT
    return CheckKind.PROPERTY


class KeaJsonResult(TextTestResult):

    # +------------------------------+
    # | Setup utils                  |
    # +------------------------------+
    res: PBTTestResult = dict()
    lastPropertyInfo: PropertyExecutionInfo
    lastInvariantInfo: PropertyExecutionInfo
    executionInfoBuffer: Deque["PropertyExecutionInfo"] = deque()
    currentStepsCount: int

    @classmethod
    def setProperties(cls, allProperties: Dict):
        for testCase in allProperties.values():
            cls.res[getFullPropName(testCase)] = PropStatistic(kind=CheckKind.PROPERTY.value)
    
    @classmethod
    def setInvariants(cls, allInvariants: Dict):
        for testCase in allInvariants.values():
            cls.res[getFullPropName(testCase)] = PropStatistic(kind=CheckKind.INVARIANT.value)
    
    @property
    def result_file(self):
        return StampManager().result_file
    
    @property
    def property_exection_result_file(self):
        return StampManager().prop_exec_file
        

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.showAll = True
        self.currentStepsCount = 0
        self.lastInvariantInfo = None
    
    def startTest(self, test):
        if get_check_kind(test) is CheckKind.INVARIANT:
            self.lastInvariantInfo = PropertyExecutionInfo(
                propName=getFullPropName(test),
                kind=CheckKind.INVARIANT.value,
                state="start",
                tb="",
                startStepsCount=self.currentStepsCount
            )
        super(TextTestResult, self).startTest(test)
        if self.showAll:
            self.stream.write(" - ")
            self.stream.write(str(test))
            self.stream.write(" ... ")
            self.stream.flush()
            self._newline = False

    def setCurrentStepsCount(self, stepsCount: int):
        self.currentStepsCount = stepsCount

    # +------------------------------+
    # | Property-specific execution  |
    # +------------------------------+
    def addExcutedProperty(self, test: TestCase, stepsCount: int):
        self.res[getFullPropName(test)].executed += 1

        self.lastPropertyInfo = PropertyExecutionInfo(
            propName=getFullPropName(test),
            kind=CheckKind.PROPERTY.value,
            state="start",
            tb="",
            startStepsCount=stepsCount
        )

    def addPropertyPrecondSatisfied(self, test: TestCase):
        self.res[getFullPropName(test)].precond_satisfied += 1

    def updateExecutionInfo(self, test):
        # if the test is a property, and it is still in "start" state, set it to "pass"
        # then record the last executed property info
        if get_check_kind(test) is CheckKind.PROPERTY:
            if self.lastPropertyInfo.state == "start":
                self.lastPropertyInfo.state = "pass"
            self.executionInfoBuffer.append(self.lastPropertyInfo)
        # if the test is an invariant, and the last invariant failed or errored, record it
        # (only record failed/errored invariants)
        if get_check_kind(test) is CheckKind.INVARIANT:
            if self.lastInvariantInfo.state in {"fail", "error"}:
                self.executionInfoBuffer.append(self.lastInvariantInfo)

    def getExcutedProperty(self, test: TestCase):
        return self.res[getFullPropName(test)].executed

    # +------------------------------+
    # | Shared result updates        |
    # +------------------------------+
    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.res[getFullPropName(test)].fail += 1
        self._record_exception(test, err, "fail")

    def addError(self, test, err):
        super().addError(test, err)
        self.res[getFullPropName(test)].error += 1
        self._record_exception(test, err, "error")

    # +------------------------------+
    # | Result utils                 |
    # +------------------------------+
    def printError(self, test):
        self._print_property_error(test)
        self._print_invariant_error(test)

    def logSummary(self):
        property_fails = sum(_.fail for _ in self.res.values() if _.kind == "property")
        property_errors = sum(_.error for _ in self.res.values() if _.kind == "property")
        invariant_fails = sum(_.fail for _ in self.res.values() if _.kind == "invariant")
        invariant_errors = sum(_.error for _ in self.res.values() if _.kind == "invariant")
        logger.info(f"[Property Execution Summary] Errors:{property_errors}, Fails:{property_fails}")
        if invariant_fails > 0 or invariant_errors > 0:
            logger.info(f"[Invariant Execution Summary] Errors:{invariant_errors}, Fails:{invariant_fails}")
    
    def flushResult(self):
        json_res = dict()
        for propName, propStatitic in self.res.items():
            json_res[propName] = asdict(propStatitic)
        with open(self.result_file, "w", encoding="utf-8") as fp:
            json.dump(json_res, fp, indent=4)

        with open(self.property_exection_result_file, "a", encoding="utf-8") as fp:
            while self.executionInfoBuffer:
                execInfo = self.executionInfoBuffer.popleft()
                fp.write(f"{json.dumps(asdict(execInfo))}\n")

    # +------------------------------+
    # | Property/invariant helpers   |
    # +------------------------------+
    def _record_exception(self, test, err, state):
        if get_check_kind(test) is CheckKind.PROPERTY:
            self.lastPropertyInfo.state = state
            self.lastPropertyInfo.tb = self._exc_info_to_string(err, test)
            return
        if get_check_kind(test) is CheckKind.INVARIANT:
            self.lastInvariantInfo = PropertyExecutionInfo(
                propName=getFullPropName(test),
                kind=CheckKind.INVARIANT.value,
                state=state,
                tb=self._exc_info_to_string(err, test),
                startStepsCount=self.currentStepsCount,
            )

    def _print_property_error(self, test):
        if get_check_kind(test) is not CheckKind.PROPERTY:
            return
        if self.lastPropertyInfo.state not in ["fail", "error"]:
            return
        flavour = self.lastPropertyInfo.state.upper()
        self.stream.writeln("")
        self.stream.writeln(self.separator1)
        self.stream.writeln("%s: %s" % (flavour, self.getDescription(test)))
        self.stream.writeln(self.separator2)
        self.stream.writeln("%s" % self.lastPropertyInfo.tb)
        self.stream.writeln(self.separator1)
        self.stream.flush()

    def _print_invariant_error(self, test):
        if get_check_kind(test) is not CheckKind.INVARIANT:
            return
        if not self.lastInvariantInfo or self.lastInvariantInfo.state not in {"fail", "error"}:
            return
        self.stream.writeln("")
        self.stream.writeln(self.separator1)
        self.stream.writeln("%s: %s" % (self.lastInvariantInfo.state.upper(), self.lastInvariantInfo.tb))
        self.stream.writeln(self.separator1)
        self.stream.flush()


class KeaTextTestResult(TextTestResult):

    # +------------------------------+
    # | Setup and output formatting  |
    # +------------------------------+
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.showAll = True
    
    def getDescription(self: "KeaJsonResult", test: "TestCase"):
        doc_first_line = test.shortDescription()
        if get_check_kind(test) is CheckKind.INVARIANT:
            return getFullPropName(test)
        if self.descriptions and doc_first_line:
            doc_first_line = "# " + doc_first_line
            return '\n'.join((str(test), doc_first_line))
        else:
            return str(test)
    
    def startTest(self: "KeaJsonResult", test):
        if get_check_kind(test) is CheckKind.INVARIANT:
            self.stream.writeln(f"[INFO] Invariant: {getFullPropName(test)}")
            self.stream.flush()
            self._newline = True
        else:
            self.stream.write("[INFO] Start executing property: ")
            self.stream.writeln(self.getDescription(test))
            self.stream.flush()
            self._newline = True
    
    # +------------------------------+
    # | Shared status updates        |
    # +------------------------------+
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
