from typing import Any, Dict, Optional

from .errors import EngineIntegrationError
from .models import SessionConfig, SessionState, SessionStatus, SessionSummary, StepResult
from .runtime import EngineRuntime
from .store import FileSessionStore
from .utils import ensure_positive_int, new_session_id, now_iso


class SessionManager:
    def __init__(self, store: Optional[FileSessionStore] = None):
        """Create a manager with a backing store and in-memory runtimes.

        Args:
            store: Optional file-backed store instance.
        """
        self.store = store or FileSessionStore()
        self._runtimes: Dict[str, EngineRuntime] = {}
        self._last_step_by_session: Dict[str, int] = {}

    def start_session(self, config: SessionConfig, discover_spec: Dict[str, Any]) -> str:
        """Initialize session state, persist it, and create runtime.

        Args:
            config: SessionConfig instance.
            discover_spec: Property discovery options.

        Returns:
            session_id: New session identifier.
        """
        ensure_positive_int("max_properties_per_step", config.max_properties_per_step)
        ensure_positive_int("per_step_timeout_sec", config.per_step_timeout_sec)

        session_id = new_session_id()
        now = now_iso()
        state = SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            config=config,
            started_at=now,
            updated_at=now,
        )
        self.store.create_session(state)
        self._runtimes[session_id] = EngineRuntime(session_id=session_id, config=config, discover_spec=discover_spec)
        self._last_step_by_session[session_id] = -1
        return session_id

    def on_engine_step(
        self,
        session_id: str,
        step_id: int,
        ui_xml: Optional[str] = None,
        event_meta: Optional[Dict[str, Any]] = None,
    ) -> StepResult:
        """Execute one engine step and update persisted counters.

        Args:
            session_id: Target session id.
            step_id: Monotonic step index from the engine.
            ui_xml: Optional pre-dumped UI hierarchy XML.
            event_meta: Optional event metadata from the engine.

        Returns:
            result: StepResult for this step.
        """
        state = self.store.load_session(session_id)
        if state.status != SessionStatus.RUNNING:
            raise EngineIntegrationError("SESSION_NOT_RUNNING", f"Session is not running: {session_id}")

        last_step = self._last_step_by_session.get(session_id, -1)
        if step_id <= last_step:
            raise EngineIntegrationError("INVALID_STEP_ORDER", f"step_id must be increasing, got {step_id}")

        runtime = self._runtimes.get(session_id)
        if runtime is None:
            runtime = EngineRuntime(session_id=session_id, config=state.config, discover_spec={})
            self._runtimes[session_id] = runtime

        result = runtime.run_step(step_id=step_id, ui_xml=ui_xml, event_meta=event_meta)
        state.total_steps += 1
        state.total_properties_executed += result.properties_executed
        state.total_errors += result.errors
        self.store.save_session(state)
        self.store.append_step_event(session_id, result)
        self._last_step_by_session[session_id] = step_id
        return result

    def get_session_state(self, session_id: str) -> SessionState:
        """Return the current session state snapshot.

        Args:
            session_id: Target session id.

        Returns:
            state: SessionState instance.
        """
        return self.store.load_session(session_id)

    def end_session(self, session_id: str, reason: str = "time_up") -> SessionSummary:
        """Mark session ended and release runtime resources.

        Args:
            session_id: Target session id.
            reason: End reason label.

        Returns:
            summary: SessionSummary instance.
        """
        state = self.store.finish_session(session_id=session_id, reason=reason)
        self._runtimes.pop(session_id, None)
        self._last_step_by_session.pop(session_id, None)
        return self._to_summary(state)

    def abort_session(self, session_id: str, reason: str) -> bool:
        """Abort a session and release runtime resources.

        Args:
            session_id: Target session id.
            reason: Abort reason label.

        Returns:
            success: True if abort succeeded.
        """
        self.store.abort_session(session_id=session_id, reason=reason)
        self._runtimes.pop(session_id, None)
        self._last_step_by_session.pop(session_id, None)
        return True

    def _to_summary(self, state: SessionState) -> SessionSummary:
        """Convert full state into a lightweight summary.

        Args:
            state: SessionState instance.

        Returns:
            summary: SessionSummary instance.
        """
        return SessionSummary(
            session_id=state.session_id,
            status=state.status,
            reason=state.reason,
            total_steps=state.total_steps,
            total_properties_executed=state.total_properties_executed,
            total_errors=state.total_errors,
        )
