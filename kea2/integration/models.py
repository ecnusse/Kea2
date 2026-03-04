from dataclasses import dataclass, field
from typing import List


@dataclass
class ExecuteResult:
    """Single execute_property call result."""
    precondition_satisfied: int
    properties_executed: int
    errors: int
    error_properties: List[str] = field(default_factory=list)


@dataclass
class Kea2Summary:
    """In-memory accumulated integration summary."""
    loaded_properties: List[str] = field(default_factory=list)
    total_precondition_satisfied: int = 0
    total_properties_executed: int = 0
    total_errors: int = 0
