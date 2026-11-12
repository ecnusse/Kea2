"""Task identity, lifecycle and explicit registration of existing experiments.

Uses only the standard library; importing this module never requires MCP or a device.
"""
import json
import os
import re
import sqlite3
import tempfile
import uuid
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path

from . import task_store
from .run_identity import HANDOFF_ENV, claim_output, valid_stamp
from .utils import getLogger

logger = getLogger(__name__)
SESSION = ContextVar("kea2_registration", default=None)
MANIFEST = "kea2_task.json"


def now():
    return datetime.now().astimezone().isoformat()


def valid_id(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9_.-]+", value)) and value not in (".", "..")


def write_manifest(record):
    root = Path(record["output_dir"])
    payload = {key: record.get(key) for key in (
        "task_id", "stamp", "origin", "parent_task_id", "task_kind", "status",
        "created_at", "started_at", "finished_at", "exit_code", "packages", "device_serial")}
    payload.update(version=1, result_file="result_{}.json".format(record["stamp"]))
    filename = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(root),
                                         prefix=".kea2-task-", delete=False) as stream:
            filename = stream.name
            json.dump(payload, stream, ensure_ascii=False, indent=2)
        os.replace(filename, str(root / MANIFEST))
    except OSError as exc:
        logger.warning("Cannot save task metadata: %s", exc)
    finally:
        if filename and Path(filename).exists():
            try:
                Path(filename).unlink()
            except OSError:
                pass


def prepare_run(options, automatic_stamp):
    """Register opportunistically without changing CLI paths or stamp semantics."""
    session = SESSION.get()
    if session is None:
        return False
    stamp = options.log_stamp
    root = Path(options.output_dir).resolve()
    handoff = os.environ.get(HANDOFF_ENV)
    if handoff:
        claim_output(root)
    else:
        root.mkdir(parents=True, exist_ok=True)
    identity = stamp if valid_id(stamp) else uuid.uuid4().hex
    if handoff:
        identity = json.loads(handoff).get("task_id", identity)
        if not valid_id(identity):
            raise ValueError("Invalid MCP task identity")
    record = dict(task_id=identity, stamp=stamp, output_dir=str(root),
                  status="running", created_at=now(), started_at=now(), pid=os.getpid(),
                  device_serial=options.serial, packages=options.packageNames,
                  origin="mcp" if handoff else session.get("origin", "cli"),
                  parent_task_id=session.get("parent_task_id"),
                  task_kind="hybrid" if options.unittest_args else "experiment",
                  result_file=str(root / ("result_" + stamp + ".json")),
                  log_file=str(root / ("fastbot_" + stamp + ".log")))
    registered = False
    try:
        task_store.init_db()
        if handoff:
            previous = task_store.get_task(identity)
            if (not previous or previous["stamp"] != stamp or
                    Path(previous["output_dir"]).resolve() != root or
                    previous["status"] not in ("queued", "running")):
                raise ValueError("MCP task identity does not match the reserved output directory")
            record["created_at"] = previous["created_at"]
            record["log_file"] = previous.get("log_file") or record["log_file"]
            task_store.update_task_status(identity, "running", started_at=record["started_at"],
                                         pid=os.getpid(), task_kind=record["task_kind"])
            registered = True
        else:
            for _ in range(100):
                try:
                    task_store.create_task(**record)
                    registered = True
                    break
                except sqlite3.IntegrityError:
                    # Keep filenames and paths unchanged; only the registry ID changes.
                    record["task_id"] = uuid.uuid4().hex
    except (sqlite3.Error, OSError) as exc:
        logger.warning("Task registration unavailable; continuing testing: %s", exc)
    session["record"] = record
    session["registered"] = registered
    write_manifest(record)
    logger.debug("Task ID: %s; registered: %s; result directory: %s",
                 record["task_id"], registered, root)
    return True


def finish_session(session, exit_code, cancelled=False):
    record = session.get("record")
    if not record:
        return
    if session.get("registered"):
        try:
            saved = task_store.get_task(record["task_id"])
            if saved and saved["status"] in ("finished", "failed", "cancelled") and saved.get("finished_at"):
                write_manifest(saved)
                return
        except (sqlite3.Error, OSError):
            pass
    status = "cancelled" if cancelled else ("finished" if exit_code == 0 else "failed")
    record.update(status=status, exit_code=exit_code, finished_at=now())
    if session.get("registered"):
        try:
            task_store.update_task_status(record["task_id"], status, exit_code=exit_code,
                                         finished_at=record["finished_at"])
            saved = task_store.get_task(record["task_id"])
            record.update(status=saved["status"], exit_code=saved["exit_code"],
                          finished_at=saved["finished_at"])
        except (sqlite3.Error, OSError) as exc:
            logger.warning("Cannot finalize task registration: %s", exc)
    write_manifest(record)


def _read_json(path):
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Metadata exceeds 1 MiB: " + str(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Metadata must be a JSON object: " + str(path))
    return data


def _candidates(root):
    """Inspect only the selected directory and its immediate res_* children."""
    found = []
    for directory in [root] + sorted(p for p in root.glob("res_*") if p.is_dir() and not p.is_symlink()):
        stamps = {p.name[len("result_"):-5] for p in directory.glob("result_*.json") if p.is_file()}
        stamps.update(p.name[len("property_exec_info_"):-5]
                      for p in directory.glob("property_exec_info_*.json") if p.is_file())
        for p in directory.glob("output_*"):
            if p.is_dir() and any((p / name).is_file() for name in
                                 ("steps.log", "coverage.log", "widget_coverage.log", "crash-dump.log")):
                stamps.add(p.name[len("output_"):])
        metadata = _read_json(directory / MANIFEST) if (directory / MANIFEST).exists() else None
        if metadata:
            if metadata.get("version") != 1 or not valid_stamp(metadata.get("stamp")) or not valid_id(metadata.get("task_id")):
                raise ValueError("Invalid task manifest: " + str(directory / MANIFEST))
            if metadata.get("task_kind") != "hybrid" and metadata["stamp"] not in stamps:
                raise ValueError("Task manifest has no matching result sources: " + str(directory))
            if metadata.get("task_kind") == "hybrid":
                continue
        for stamp in sorted(stamps):
            if not valid_stamp(stamp):
                raise ValueError("Unsupported stamp: " + stamp)
            found.append({"result_dir": str(directory.resolve()), "stamp": stamp,
                          "metadata": metadata if metadata and metadata["stamp"] == stamp else None})
    return found


def register_result(result_dir, stamp=None, task_id=None):
    """Explicit, read-only inspection of historical files; only the DB is mutated."""
    try:
        root = Path(result_dir).expanduser().resolve()
        if not root.is_dir():
            raise ValueError("Result directory does not exist")
        if ((stamp is not None and not valid_stamp(stamp)) or
                (task_id is not None and not valid_id(task_id))):
            raise ValueError("Invalid stamp or task_id")
        candidates = _candidates(root)
        selected = [c for c in candidates if stamp is None or c["stamp"] == stamp]
        if not selected:
            return {"status": "unsupported", "message": "No matching supported experiment sources; HTML alone is insufficient"}
        if len(selected) > 1:
            return {"status": "selection_required", "candidates": [
                {k: c[k] for k in ("result_dir", "stamp")} for c in selected],
                "message": "Specify the exact result_dir and stamp; no task was registered"}
        chosen = selected[0]
        root, stamp = Path(chosen["result_dir"]), chosen["stamp"]
        metadata = chosen["metadata"] or {}
        identity = task_id or metadata.get("task_id") or (stamp if valid_id(stamp) else uuid.uuid4().hex)
        # Parse through the same read-only result layer used by MCP, including its safety checks.
        from .results import ResultSnapshot
        snapshot = ResultSnapshot({"task_id": identity, "stamp": stamp, "output_dir": str(root), "status": "unknown"})
        report = snapshot.report()
        if not any(value in ("available", "partial") for key, value in report["availability"].items()
                   if key not in ("run_options", "report_configuration")):
            return {"status": "invalid", "message": "No readable experiment sources", "availability": report["availability"]}
        notes = ["Historical completion status and exit code are not verified; stored as unknown."]
        if metadata:
            notes.append("Manifest identity recovered; claimed lifecycle metadata retained as unverified metadata.")
        task_store.init_db()
        conn = task_store._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for row in conn.execute("SELECT task_id, stamp, output_dir FROM tasks WHERE stamp = ?", (stamp,)):
                if row["output_dir"] and Path(row["output_dir"]).resolve() == root:
                    return {"status": "already_registered", "task_id": row["task_id"], "stamp": stamp,
                            "output_dir": str(root)}
            if conn.execute("SELECT 1 FROM tasks WHERE task_id = ?", (identity,)).fetchone():
                return {"status": "identity_conflict", "task_id": identity,
                        "message": "ID is registered at another location; specify an explicit task_id alias"}
            conn.execute("INSERT INTO tasks (task_id, stamp, status, output_dir, result_file, log_file, "
                         "origin, task_kind, extra_json) VALUES (?, ?, 'unknown', ?, ?, ?, 'imported', 'experiment', ?)",
                         (identity, stamp, str(root), str(root / ("result_" + stamp + ".json")),
                          str(root / ("fastbot_" + stamp + ".log")),
                          json.dumps({"registration": {"registered_at": now(), "unverified_manifest": metadata}})))
            conn.commit()
        finally:
            conn.close()
        return {"status": "registered", "task_id": identity, "stamp": stamp, "output_dir": str(root),
                "availability": report.get("availability"), "warnings": report.get("warnings"), "notes": notes}
    except (OSError, ValueError, sqlite3.Error) as exc:
        return {"status": "invalid", "message": str(exc)}
