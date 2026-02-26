from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SessionStatus(str, Enum):
    """Lifecycle status for an integration session.

    Values:
        RUNNING: Session is active and accepts steps.
        ENDED: Session finished normally.
        ABORTED: Session was aborted.
    """
    RUNNING = "running"
    ENDED = "ended"
    ABORTED = "aborted"


@dataclass
class SessionConfig:
    """Configuration for one integration session.

    Attributes:
        device_id: ADB serial for the target device.
        driver_name: Attribute name injected into property tests, e.g. "d".
        max_properties_per_step: Max properties executed per on_engine_step.
        per_step_timeout_sec: Timeout seconds for one on_engine_step call.
    """
    device_id: str
    driver_name: str = "d"
    max_properties_per_step: int = 8
    per_step_timeout_sec: int = 8


@dataclass
class StepResult:
    """Result payload for a single on_engine_step call.

    Attributes:
        session_id: Session identifier.
        step_id: Engine step index.
        precondition_satisfied: Count of satisfied preconditions in this step.
        properties_executed: Number of properties actually executed.
        errors: Number of property execution errors in this step.
        error_properties: Property names that failed in this step.
        stop_reason: Internal loop stop reason, e.g. no_match or timeout.
        event_meta: Optional event metadata from the engine.
    """
    session_id: str
    step_id: int
    precondition_satisfied: int
    properties_executed: int
    errors: int
    stop_reason: str
    error_properties: List[str] = field(default_factory=list)
    event_meta: Optional[Dict[str, Any]] = None


@dataclass
class SessionState:
    """Persisted state of a running session.

    Attributes:
        session_id: Session identifier.
        status: Session lifecycle status.
        config: Session configuration snapshot.
        started_at: ISO-8601 start time.
        updated_at: ISO-8601 last update time.
        total_steps: Total engine steps processed.
        total_properties_executed: Total properties executed.
        total_errors: Total property execution errors.
        reason: End or abort reason if set.
    """
    session_id: str
    status: SessionStatus
    config: SessionConfig
    started_at: str
    updated_at: str
    total_steps: int = 0
    total_properties_executed: int = 0
    total_errors: int = 0
    reason: str = ""


@dataclass
class SessionSummary:
    """Terminal summary returned by end_session.

    Attributes:
        session_id: Session identifier.
        status: Final session status.
        reason: End reason label.
        total_steps: Total engine steps processed.
        total_properties_executed: Total properties executed.
        total_errors: Total property execution errors.
    """
    session_id: str
    status: SessionStatus
    reason: str
    total_steps: int
    total_properties_executed: int
    total_errors: int
