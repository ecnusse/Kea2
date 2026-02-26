from dataclasses import asdict
from typing import Any, Dict, Optional

from .models import SessionConfig
from .session import SessionManager

_manager = SessionManager()


def start_session(config: Dict[str, Any], discover_spec: Optional[Dict[str, Any]] = None) -> str:
    """Create a new integration session and return session_id.

    Args:
        config: SessionConfig-compatible dict for device and runtime settings.
        discover_spec: Optional discovery spec for property discovery arguments.

    Returns:
        session_id: New session identifier.
    """
    cfg = SessionConfig(**config)
    return _manager.start_session(config=cfg, discover_spec=discover_spec or {})


def on_engine_step(
    session_id: str,
    step_id: int,
    ui_xml: Optional[str] = None,
    event_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Handle one engine step and return a serializable result.

    Args:
        session_id: Target session id.
        step_id: Monotonic step index from the engine.
        ui_xml: Optional pre-dumped UI hierarchy XML.
        event_meta: Optional event metadata from the engine.

    Returns:
        result: JSON-ready dict of StepResult.
    """
    result = _manager.on_engine_step(
        session_id=session_id,
        step_id=step_id,
        ui_xml=ui_xml,
        event_meta=event_meta,
    )
    return asdict(result)


def get_session_state(session_id: str) -> Dict[str, Any]:
    """Fetch current session state as a JSON-ready dict.

    Args:
        session_id: Target session id.

    Returns:
        state: JSON-ready dict of SessionState.
    """
    state = _manager.get_session_state(session_id)
    payload = asdict(state)
    payload["status"] = state.status.value
    return payload


def end_session(session_id: str, reason: str = "time_up") -> Dict[str, Any]:
    """Finish a session and return a summary payload.

    Args:
        session_id: Target session id.
        reason: End reason label.

    Returns:
        summary: JSON-ready dict of SessionSummary.
    """
    summary = _manager.end_session(session_id=session_id, reason=reason)
    payload = asdict(summary)
    payload["status"] = summary.status.value
    return payload


def abort_session(session_id: str, reason: str) -> bool:
    """Abort a session and release its runtime resources.

    Args:
        session_id: Target session id.
        reason: Abort reason label.

    Returns:
        success: True if abort succeeded.
    """
    return _manager.abort_session(session_id=session_id, reason=reason)
