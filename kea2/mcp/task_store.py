import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


DB_PATH = Path.home() / ".kea2" / "tasks.db"
_WRITE_LOCK = asyncio.Lock()
_ALLOWED_STATUS = {
    "queued",
    "running",
    "cancelling",
    "cancelled",
    "finished",
    "failed",
    "unknown",
}


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                stamp TEXT,
                pid INTEGER,
                status TEXT NOT NULL CHECK (
                    status IN ('queued','running','cancelling','cancelled','finished','failed','unknown')
                ),
                device_serial TEXT,
                packages TEXT,
                output_dir TEXT,
                log_file TEXT,
                result_file TEXT,
                created_at TEXT,
                started_at TEXT,
                finished_at TEXT,
                exit_code INTEGER,
                extra_json TEXT
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_stamp ON tasks(stamp);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_device_serial ON tasks(device_serial);")
        conn.commit()
    finally:
        conn.close()


def _serialize_field(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def create_task(
    task_id: str,
    stamp: str,
    status: str = "queued",
    pid: Optional[int] = None,
    device_serial: Optional[str] = None,
    packages: Optional[Any] = None,
    output_dir: Optional[str] = None,
    log_file: Optional[str] = None,
    result_file: Optional[str] = None,
    created_at: Optional[str] = None,
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
    exit_code: Optional[int] = None,
    extra_json: Optional[Any] = None,
) -> None:
    if status not in _ALLOWED_STATUS:
        raise ValueError(f"invalid status: {status}")
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO tasks (
                task_id, stamp, pid, status, device_serial, packages,
                output_dir, log_file, result_file,
                created_at, started_at, finished_at, exit_code, extra_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                stamp,
                pid,
                status,
                device_serial,
                _serialize_field(packages),
                output_dir,
                log_file,
                result_file,
                created_at,
                started_at,
                finished_at,
                exit_code,
                _serialize_field(extra_json),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_task_status(task_id: str, status: str, **fields: Any) -> None:
    if status not in _ALLOWED_STATUS:
        raise ValueError(f"invalid status: {status}")
    update_fields: Dict[str, Any] = dict(fields)
    update_fields["status"] = status
    if not update_fields:
        return

    allowed_columns = {
        "stamp",
        "pid",
        "status",
        "device_serial",
        "packages",
        "output_dir",
        "log_file",
        "result_file",
        "created_at",
        "started_at",
        "finished_at",
        "exit_code",
        "extra_json",
    }
    invalid = [k for k in update_fields if k not in allowed_columns]
    if invalid:
        raise ValueError(f"invalid fields: {invalid}")

    set_parts = []
    values: List[Any] = []
    for key, value in update_fields.items():
        set_parts.append(f"{key} = ?")
        values.append(_serialize_field(value))
    values.append(task_id)

    conn = _connect()
    try:
        conn.execute(
            f"UPDATE tasks SET {', '.join(set_parts)} WHERE task_id = ?",
            values,
        )
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    result = dict(row)
    for key in ("packages", "extra_json"):
        val = result.get(key)
        if isinstance(val, str):
            try:
                result[key] = json.loads(val)
            except Exception:
                pass
    return result


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        return _row_to_dict(row)
    finally:
        conn.close()


def list_tasks(status: Optional[str] = None) -> List[Dict[str, Any]]:
    if status is not None and status not in _ALLOWED_STATUS:
        raise ValueError(f"invalid status: {status}")
    conn = _connect()
    try:
        if status is None:
            rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


async def create_task_locked(**kwargs: Any) -> None:
    async with _WRITE_LOCK:
        create_task(**kwargs)


async def update_task_status_locked(task_id: str, status: str, **fields: Any) -> None:
    async with _WRITE_LOCK:
        update_task_status(task_id, status, **fields)
