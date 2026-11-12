"""Output-directory ownership shared by the CLI and its MCP launcher."""
import json
import os
import secrets
from datetime import datetime
from pathlib import Path


HANDOFF_ENV = "KEA2_OUTPUT_HANDOFF"
MARKER = ".kea2-launch-token"


def new_stamp():
    return datetime.now().strftime("%Y%m%d%H_%M%S%f")


def prepare_handoff(directory, task_id=None):
    directory = Path(directory).resolve()
    token = secrets.token_hex(32)
    with (directory / MARKER).open("x", encoding="utf-8") as stream:
        stream.write(token)
    payload = {"directory": str(directory), "token": token}
    if task_id is not None:
        payload["task_id"] = task_id
    return json.dumps(payload)


def claim_output(directory):
    """Create exclusively, or consume the parent's one-use reservation."""
    directory = Path(directory).resolve()
    handoff = os.environ.pop(HANDOFF_ENV, None)
    if handoff:
        data = json.loads(handoff)
        marker = directory / MARKER
        if (data.get("directory") != str(directory) or
                not marker.is_file() or
                marker.read_text(encoding="utf-8") != data.get("token")):
            raise ValueError("Invalid MCP output-directory reservation")
        marker.unlink()
        return
    directory.mkdir(parents=True, exist_ok=False)


def valid_stamp(value):
    """Accept legacy log stamps while excluding path separators and unsafe characters."""
    return isinstance(value, str) and bool(value) and not any(
        char in value for char in '/\\:*?"<>|\n\r\t\0')
