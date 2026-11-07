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
        columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
        for name in ("origin", "parent_task_id", "task_kind"):
            if name not in columns:
                try:
                    conn.execute("ALTER TABLE tasks ADD COLUMN " + name + " TEXT")
                except sqlite3.OperationalError:
                    if name not in {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}:
                        raise
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
    reserve_output: bool = False,
    origin: Optional[str] = None,
    parent_task_id: Optional[str] = None,
    task_kind: Optional[str] = None,
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
                created_at, started_at, finished_at, exit_code, extra_json,
                origin, parent_task_id, task_kind
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                origin, parent_task_id, task_kind,
            ),
        )
        if reserve_output:
            # The unique INSERT and exclusive mkdir must both succeed before commit.
            Path(output_dir).mkdir(parents=True, exist_ok=False)
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
        "origin", "parent_task_id", "task_kind",
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
            f"UPDATE tasks SET {', '.join(set_parts)} WHERE task_id = ?"
            + (" AND status NOT IN ('finished','failed','cancelled','cancelling')" if status in ("queued", "running")
               else " AND status NOT IN ('cancelled','cancelling')" if status not in ("cancelled", "cancelling") else ""),
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


def list_tasks_page(status: Optional[str] = None, limit: int = 20,
                    offset: int = 0, origin: Optional[str] = None,
                    parent_task_id: Optional[str] = None) -> Dict[str, Any]:
    """Read one bounded page of task metadata, without opening result files."""
    if status is not None and status not in _ALLOWED_STATUS:
        raise ValueError("INVALID_STATUS")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("INVALID_LIMIT")
    if type(offset) is not int or offset < 0:
        raise ValueError("INVALID_OFFSET")
    if origin is not None and origin not in ("cli", "mcp", "imported"):
        raise ValueError("INVALID_ORIGIN")
    init_db()
    conn = _connect()
    try:
        # Count and page must describe the same database state within this call.
        conn.execute("BEGIN")
        selectors = [(key, value) for key, value in
                     (("status", status), ("origin", origin), ("parent_task_id", parent_task_id))
                     if value is not None]
        where = " WHERE " + " AND ".join(key + " = ?" for key, _ in selectors) if selectors else ""
        params = [value for _, value in selectors]
        total = conn.execute("SELECT COUNT(*) FROM tasks" + where, params).fetchone()[0]
        rows = conn.execute(
            "SELECT task_id, status, device_serial, packages, output_dir, "
            "created_at, started_at, finished_at, exit_code, stamp, origin, parent_task_id, task_kind FROM tasks" + where +
            " ORDER BY created_at DESC, task_id DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        tasks = [_row_to_dict(row) for row in rows]
        return {"tasks": tasks, "total": total, "limit": limit, "offset": offset,
                "next_offset": offset + len(tasks) if offset + len(tasks) < total else None}
    finally:
        conn.close()


async def create_task_locked(**kwargs: Any) -> None:
    async with _WRITE_LOCK:
        create_task(**kwargs)


async def update_task_status_locked(task_id: str, status: str, **fields: Any) -> None:
    async with _WRITE_LOCK:
        update_task_status(task_id, status, **fields)
