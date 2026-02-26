import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any

from .errors import EngineIntegrationError


def now_iso() -> str:
    """Return current UTC time in ISO-8601 format.

    Returns:
        timestamp: ISO-8601 timestamp string.
    """
    return datetime.now(timezone.utc).isoformat()


def new_session_id() -> str:
    """Generate a stable session id based on timestamp.

    Returns:
        session_id: New session identifier, e.g. sess_YYYYMMDDHH_xxxxxxxxxx.
    """
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d%H")
    suffix = f"{int(now.timestamp() * 1000) % 10_000_000_000:010d}"
    return f"sess_{stamp}_{suffix}"


def ensure_positive_int(name: str, value: int) -> None:
    """Validate a positive integer config field.

    Args:
        name: Field name for error reporting.
        value: Value to validate.

    Returns:
        None.
    """
    if not isinstance(value, int) or value <= 0:
        raise EngineIntegrationError("INVALID_CONFIG", f"{name} must be a positive integer")


def dataclass_to_json(data: Any) -> str:
    """Serialize a dataclass instance to JSON.

    Args:
        data: Dataclass instance.

    Returns:
        json_text: JSON string.
    """
    if not is_dataclass(data):
        raise TypeError("Expected dataclass instance")
    return json.dumps(asdict(data), ensure_ascii=False, indent=2)
