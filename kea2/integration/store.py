import json
from dataclasses import asdict
from pathlib import Path

from kea2.fs_lock import FileLock

from .errors import EngineIntegrationError
from .models import SessionConfig, SessionState, SessionStatus, StepResult
from .utils import now_iso


class FileSessionStore:
    def __init__(self, root: str = "output/sessions"):
        """Create a file-backed store for session state and events.

        Args:
            root: Root directory for session files.
        """
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(str(self.root / ".sessions.lock"))

    def _session_path(self, session_id: str) -> Path:
        """Return the JSON path for a session state file.

        Args:
            session_id: Session identifier.

        Returns:
            path: Path to the session JSON file.
        """
        return self.root / f"{session_id}.json"

    def _event_path(self, session_id: str) -> Path:
        """Return the JSONL path for session step events.

        Args:
            session_id: Session identifier.

        Returns:
            path: Path to the session events JSONL file.
        """
        return self.root / f"{session_id}.events.jsonl"

    def create_session(self, state: SessionState) -> None:
        """Persist a new session, failing if it already exists.

        Args:
            state: SessionState instance.

        Returns:
            None.
        """
        with self._lock:
            p = self._session_path(state.session_id)
            if p.exists():
                raise EngineIntegrationError("SESSION_EXISTS", f"Session already exists: {state.session_id}")
            self._write_session_unlocked(state)

    def load_session(self, session_id: str) -> SessionState:
        """Load a session state from disk.

        Args:
            session_id: Session identifier.

        Returns:
            state: SessionState instance.
        """
        with self._lock:
            p = self._session_path(session_id)
            if not p.exists():
                raise EngineIntegrationError("SESSION_NOT_FOUND", f"Session not found: {session_id}")
            raw = json.loads(p.read_text(encoding="utf-8"))
        return self._parse_state(raw)

    def save_session(self, state: SessionState) -> None:
        """Update a session state and write it to disk.

        Args:
            state: SessionState instance.

        Returns:
            None.
        """
        state.updated_at = now_iso()
        with self._lock:
            self._write_session_unlocked(state)

    def append_step_event(self, session_id: str, step_result: StepResult) -> None:
        """Append a StepResult line to the session event log.

        Args:
            session_id: Session identifier.
            step_result: StepResult instance.

        Returns:
            None.
        """
        line = json.dumps(asdict(step_result), ensure_ascii=False)
        with self._lock:
            with self._event_path(session_id).open("a", encoding="utf-8") as fp:
                fp.write(f"{line}\n")

    def finish_session(self, session_id: str, reason: str) -> SessionState:
        """Mark a session ended with a reason.

        Args:
            session_id: Session identifier.
            reason: End reason label.

        Returns:
            state: Updated SessionState instance.
        """
        state = self.load_session(session_id)
        state.status = SessionStatus.ENDED
        state.reason = reason
        self.save_session(state)
        return state

    def abort_session(self, session_id: str, reason: str) -> SessionState:
        """Mark a session aborted with a reason.

        Args:
            session_id: Session identifier.
            reason: Abort reason label.

        Returns:
            state: Updated SessionState instance.
        """
        state = self.load_session(session_id)
        state.status = SessionStatus.ABORTED
        state.reason = reason
        self.save_session(state)
        return state

    def _write_session_unlocked(self, state: SessionState) -> None:
        """Write session state to disk without locking.

        Args:
            state: SessionState instance.

        Returns:
            None.
        """
        payload = asdict(state)
        payload["status"] = state.status.value
        self._session_path(state.session_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _parse_state(self, raw: dict) -> SessionState:
        """Parse raw JSON into a SessionState instance.

        Args:
            raw: Raw JSON dict from disk.

        Returns:
            state: SessionState instance.
        """
        cfg_raw = dict(raw.get("config", {}))
        config = SessionConfig(**cfg_raw)
        return SessionState(
            session_id=raw["session_id"],
            status=SessionStatus(raw["status"]),
            config=config,
            started_at=raw["started_at"],
            updated_at=raw["updated_at"],
            total_steps=raw.get("total_steps", 0),
            total_properties_executed=raw.get("total_properties_executed", 0),
            total_errors=raw.get("total_errors", 0),
            reason=raw.get("reason", ""),
        )
