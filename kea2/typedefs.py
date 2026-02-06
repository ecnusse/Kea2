# Class Typing
from dataclasses import dataclass
from typing import Deque, Dict, Literal, NewType
from unittest import TestCase

PRECONDITIONS_MARKER = "preconds"
PROB_MARKER = "prob"
MAX_TRIES_MARKER = "max_tries"
INTERRUPTABLE_MARKER = "interruptable"

@dataclass
class PropStatistic:
    kind: Literal["property", "invariant"] = "unknown"
    precond_satisfied: int = 0
    executed: int = 0
    fail: int = 0
    error: int = 0


@dataclass
class PropertyExecutionInfo:
    startStepsCount: int
    propName: "PropName"
    kind: Literal["property", "invariant"]
    state: Literal["start", "pass", "fail", "error"]
    tb: str


PropName = NewType("PropName", str)
PropertyStore = NewType("PropertyStore", Dict[PropName, TestCase])

PBTTestResult = NewType("PBTTestResult", Dict[PropName, PropStatistic])
