"""Offline result queries. This module never renders reports or contacts devices.

Schema 1.4 adds saved run options and report configuration.
It deliberately does not infer missing data, screenshot associations or causes.
"""

import hashlib
import json
import math
import re
from pathlib import Path
from typing import List

from .models import (
    SCHEMA_VERSION, ActivityRecord, CheckRecord, ExperimentData, FindingRecord,
    FindingResponse, QueryResponse, ReportResponse, TrendRecord, decode, validated,
    StepRecord, ExecutionRecord, ArtifactRecord, WidgetRecord, PropertyExecutionPoint, ConfigurationRecord,
)
from .errors import ResultError
from .evidence import EvidenceMixin
from .coverage import CoverageMixin
from .configuration import ConfigurationMixin

MAX_SOURCE_BYTES = 64 * 1024 * 1024
SECTIONS = ("checks", "findings", "activities", "trends", "steps", "executions", "artifacts", "widgets", "property_execution_trend", "configuration")
CRASH_BLOCK = re.compile(
    r"(?:StepsCount:\s*(\d+)\s*\nCrashScreen:[ \t]*([^\n]*)\n)?"
    r"(\d{14})\r?\n(crash|anr):\r?\n(.*?)\r?\n(?:// crash end|anr end)",
    re.DOTALL,
)


def _count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def _strings(value):
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def _reject_constant(value):
    raise ValueError("Non-finite JSON number: " + value)


def _execution(task):
    code = task.get("exit_code")
    status = task.get("status")
    if status == "cancelled":
        state = "cancelled"
    elif code in (0, 1, 2, 3):
        state = "completed"
    elif code is not None or status == "failed":
        state = "execution_error"
    elif status in ("queued", "running", "cancelling"):
        state = status
    elif status == "finished":
        state = "completed"
    else:
        state = "unknown"
    return {
        "status": state, "exit_code": code,
        "finding_flags": {
            "property_violation": bool(code & 1) if code in (0, 1, 2, 3) else None,
            "crash_or_anr": bool(code & 2) if code in (0, 1, 2, 3) else None,
        },
        "created_at": task.get("created_at"), "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
        "packages": task.get("packages"), "device_serial": task.get("device_serial"),
        "requested_parameters": task.get("extra_json"),
    }


class ResultSnapshot(EvidenceMixin, CoverageMixin, ConfigurationMixin):
    """One bounded read of known sources, with content-bound pagination.

    Queries currently rebuild the snapshot. Cursors reject changed data rather
    than silently paginating a different run state. Large files are explicitly
    unavailable, never silently truncated.
    """

    def __init__(self, task):
        self.task = task
        self.warnings = []
        self.warning_count = 0
        self.availability = {}
        self.records = {section: [] for section in SECTIONS}
        self.traces = {}
        self.digest = hashlib.sha256()
        self.digest.update(json.dumps(task, sort_keys=True, default=str).encode("utf-8"))
        output_dir, stamp = task.get("output_dir"), task.get("stamp")
        if not output_dir or not stamp:
            raise ResultError("RESULT_LOCATION_UNAVAILABLE", "Task has no output directory or stamp")
        from ..run_identity import valid_stamp
        if not valid_stamp(stamp):
            raise ResultError("INVALID_STAMP", "Task stamp is not a safe filename component")
        self.root = Path(output_dir).resolve()
        nested = "output_{}/".format(stamp)
        self.paths = {
            "run_options": "options.json",
            "report_configuration": "bug_report_config.json",
            "checks": "result_{}.json".format(stamp),
            "property_executions": "property_exec_info_{}.json".format(stamp),
            "activity_coverage": nested + "coverage.log",
            "widget_coverage": nested + "widget_coverage.log",
            "widget_inventory": nested + "widget_coverage_report.txt",
            "crashes": nested + "crash-dump.log",
            "steps": nested + "steps.log",
        }
        self._load_configuration()
        self._load_checks()
        self._load_executions()
        self._load_coverage()
        self._load_crashes()
        self._load_evidence()
        self._load_widgets()
        self._load_property_trend()
        record_models = {"checks": CheckRecord, "findings": FindingRecord,
                         "activities": ActivityRecord, "trends": TrendRecord,
                         "steps": StepRecord, "executions": ExecutionRecord, "artifacts": ArtifactRecord, "widgets": WidgetRecord,
                         "property_execution_trend": PropertyExecutionPoint, "configuration": ConfigurationRecord}
        for section, model in record_models.items():
            self.records[section] = validated(List[model], self.records[section])
        if (self.availability["checks"] == "available"
                and self.availability["property_executions"] == "available"):
            observed = {}
            for finding in self.records["findings"]:
                if "check_name" in finding:
                    key = (finding["check_name"], finding["state"])
                    observed[key] = observed.get(key, 0) + 1
            expected = {(c["name"], state): c[state] for c in self.records["checks"]
                        for state in ("fail", "error") if c[state]}
            if observed != expected:
                self._warn("property_executions", "OUTCOME_COUNTS_DISAGREE")
        self.snapshot_id = self.digest.hexdigest()

    def _warn(self, source, code, line=None):
        self.warning_count += 1
        if len(self.warnings) >= 50:
            return
        warning = {"source": source, "code": code}
        if line is not None:
            warning["line"] = line
        self.warnings.append(warning)

    def _read(self, source):
        relative = self.paths[source]
        self.digest.update(source.encode("utf-8"))
        path = (self.root / relative).resolve()
        if self.root not in path.parents:
            self.availability[source] = "invalid"
            self._warn(source, "PATH_OUTSIDE_RESULT_DIRECTORY")
            self.digest.update(b"unsafe")
            return None
        try:
            with path.open("rb") as stream:
                before = path.stat()
                if before.st_size > MAX_SOURCE_BYTES:
                    self.availability[source] = "too_large"
                    self._warn(source, "SOURCE_SIZE_LIMIT")
                    self.digest.update(str((before.st_size, before.st_mtime_ns)).encode())
                    return None
                raw = stream.read(MAX_SOURCE_BYTES + 1)
                after = path.stat()
        except FileNotFoundError:
            self.availability[source] = "missing"
            self.digest.update(b"missing")
            return None
        except OSError:
            self.availability[source] = "unreadable"
            self._warn(source, "SOURCE_UNREADABLE")
            self.digest.update(b"unreadable")
            return None
        self.digest.update(raw)
        if len(raw) > MAX_SOURCE_BYTES:
            self.availability[source] = "too_large"
            self._warn(source, "SOURCE_SIZE_LIMIT")
            return None
        self.availability[source] = "available"
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            self.availability[source] = "partial"
            self._warn(source, "SOURCE_CHANGED_DURING_READ")
        try:
            return raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            self.availability[source] = "partial"
            self._warn(source, "INVALID_UTF8")
            return raw.decode("utf-8-sig", errors="replace")

    def _invalid(self, source, line=None):
        self.availability[source] = "partial"
        self._warn(source, "INVALID_RECORD", line)

    def _json_lines(self, source):
        text = self._read(source)
        if text is None:
            return
        for line, raw in enumerate(text.splitlines(), 1):
            if not raw.strip():
                continue
            try:
                item = json.loads(raw, parse_constant=_reject_constant)
            except (ValueError, RecursionError):
                self._invalid(source, line)
                continue
            if not isinstance(item, dict):
                self._invalid(source, line)
                continue
            yield line, item

    def _source(self, name, **location):
        return {"artifact": self.paths[name], **location}

    def _load_checks(self):
        text = self._read("checks")
        if text is None:
            return
        try:
            data = json.loads(text, parse_constant=_reject_constant)
            if not isinstance(data, dict):
                raise ValueError("Expected object")
        except (ValueError, RecursionError):
            self.availability["checks"] = "invalid"
            self._warn("checks", "INVALID_JSON")
            return
        for name, stats in data.items():
            if (not isinstance(stats, dict) or
                    any(not _count(stats.get(k, 0))
                        for k in (("fail", "error") if stats.get("kind") == "invariant"
                                  else ("executed", "precond_satisfied", "fail", "error")))):
                self._invalid("checks")
                continue
            kind = stats.get("kind", "unknown")
            if kind not in ("property", "invariant"):
                kind = "unknown"
            executed, fail, error = (stats.get(k, 0) for k in ("executed", "fail", "error"))
            if kind != "invariant" and fail + error > executed:
                self._warn("checks", "FAILURES_EXCEED_EXECUTED")
            self.records["checks"].append({
                "name": name, "kind": kind,
                "precond_satisfied": None if kind == "invariant" else stats.get("precond_satisfied", 0),
                "executed": None if kind == "invariant" else executed, "fail": fail, "error": error,
                "pass_count": None if kind == "invariant" else max(executed - fail - error, 0),
                "pass_count_basis": "not_applicable" if kind == "invariant" else "derived_max_executed_minus_fail_minus_error",
                "source": self._source("checks", key=name), "raw": stats,
            })

    def _add_finding(self, finding, trace):
        self.traces[finding["id"]] = trace
        finding["trace_characters"] = len(trace)
        self.records["findings"].append(finding)

    def _load_executions(self):
        kinds = {c["name"]: c["kind"] for c in self.records["checks"]}
        for line, item in self._json_lines("property_executions"):
            if item.get("state") not in ("start", "pass", "fail", "error"):
                self._invalid("property_executions", line)
                continue
            if item["state"] not in ("fail", "error"):
                continue
            if (not isinstance(item.get("propName"), str) or not item["propName"]
                    or not isinstance(item.get("tb", ""), str)
                    or not _count(item.get("startStepsCount"))):
                self._invalid("property_executions", line)
                continue
            kind = item.get("kind", kinds.get(item["propName"], "unknown"))
            if kind not in ("property", "invariant"):
                kind = "unknown"
            trace = item.get("tb", "")
            self._add_finding({
                "id": "execution:{}".format(line), "type": kind,
                "state": item["state"], "check_name": item["propName"],
                "monkey_step": item["startStepsCount"],
                "description": trace.strip().splitlines()[-1][:500] if trace.strip() else "",
                "source": self._source("property_executions", line=line),
            }, trace)

    def _load_coverage(self):
        final = None
        final_line = None
        for line, item in self._json_lines("activity_coverage"):
            if (not _count(item.get("stepsCount")) or not _number(item.get("coverage"))
                    or not 0 <= item["coverage"] <= 100
                    or not all(_strings(item.get(k)) for k in ("totalActivities", "testedActivities"))
                    or not isinstance(item.get("activityCountHistory", {}), dict)
                    or not all(_count(v) for v in item.get("activityCountHistory", {}).values())
                    or not all(_count(item.get(k)) for k in ("totalActivitiesCount", "testedActivitiesCount"))):
                self._invalid("activity_coverage", line)
                continue
            final = item
            final_line = line
            self.records["trends"].append({
                "metric": "activity_coverage_percent", "monkey_step": item["stepsCount"],
                "value": item["coverage"], "raw": item,
                "source": self._source("activity_coverage", line=line),
            })
        self.final_coverage = final
        if final:
            total, tested = set(final["totalActivities"]), set(final["testedActivities"])
            if (not tested <= total or len(total) != final["totalActivitiesCount"]
                    or len(tested) != final["testedActivitiesCount"]):
                self._warn("activity_coverage", "COVERAGE_COUNTS_DISAGREE")
            for name in sorted(total | tested):
                self.records["activities"].append({
                    "name": name, "covered": name in tested, "in_inventory": name in total,
                    "visit_count": final.get("activityCountHistory", {}).get(name),
                    "source": self._source("activity_coverage", line=final_line),
                })
        self.widget_count = None
        for line, item in self._json_lines("widget_coverage"):
            if not _count(item.get("stepsCount")) or not _count(item.get("coverage")):
                self._invalid("widget_coverage", line)
                continue
            self.widget_count = item["coverage"]
            self.records["trends"].append({
                "metric": "unique_triggered_widget_count", "monkey_step": item["stepsCount"],
                "value": item["coverage"], "raw": item,
                "source": self._source("widget_coverage", line=line),
            })

    def _load_crashes(self):
        text = self._read("crashes")
        if text is None:
            return
        matches = list(CRASH_BLOCK.finditer(text))
        remainder = CRASH_BLOCK.sub("", text)
        if remainder.strip():
            self._invalid("crashes")
        for match in matches:
            step, screen, timestamp, kind, trace = match.groups()
            line = text.count("\n", 0, match.start()) + 1
            process = re.search(r"// (?:CRASH|ANR):\s*(.*?)\s+\(pid\s+(\d+)\)", trace)
            description = re.search(r"(?:^|\n)(?:// Long Msg:|Reason:)\s*([^\r\n]+)", trace)
            self._add_finding({
                "id": "{}:{}".format(kind, line), "type": kind,
                "time_raw": timestamp, "monkey_step": int(step) if step else None,
                "process_name": process.group(1) if process else None,
                "pid": int(process.group(2)) if process else None,
                "description": description.group(1)[:500] if description else "",
                "screenshot_reference": screen.strip() if screen else None,
                "source": self._source("crashes", line=line),
            }, trace)

    def report(self):
        checks = self.records["checks"]
        counts = None
        if self.availability["checks"] in ("available", "partial"):
            counts = {}
            for kind in ("property", "invariant", "unknown"):
                subset = [c for c in checks if c["kind"] == kind]
                counts[kind] = {
                    "count": len(subset),
                    "executed_check_count": None if kind == "invariant" else sum(c["executed"] > 0 for c in subset),
                    "violated_check_count": sum(c["fail"] + c["error"] > 0 for c in subset),
                    "execution_count": None if kind == "invariant" else sum(c["executed"] for c in subset),
                    "fail_occurrences": sum(c["fail"] for c in subset),
                    "error_occurrences": sum(c["error"] for c in subset),
                }
        execution = _execution(self.task)
        available = all(v == "available" or (k == "crashes" and self._absent_crash_log_is_empty())
                        for k, v in self.availability.items())
        return validated(ReportResponse, {
            "schema_version": SCHEMA_VERSION, "task_id": self.task["task_id"],
            "snapshot_id": self.snapshot_id, "execution": execution,
            "data_completeness": "available_sources" if available else "partial",
            "is_live": execution["status"] in ("queued", "running", "cancelling"),
            "summary": {
                "checks": counts,
                "activity_coverage_percent": self.final_coverage["coverage"] if self.final_coverage else None,
                "unique_triggered_widget_count": self.widget_count,
                "observed_crash_occurrences": self._event_count("crash"),
                "observed_anr_occurrences": self._event_count("anr"),
            },
            "availability": dict(self.availability),
            "sections": {k: {"record_count": len(v)} for k, v in self.records.items()},
            "warnings": list(self.warnings),
            "warning_count": self.warning_count,
            "warnings_truncated": self.warning_count > len(self.warnings),
            "limitations": [
                "Counts describe readable records. An absent optional crash log counts as zero for a completed run with exit code 0 or 1; other missing sources remain unknown.",
                "Source files are read independently; this is not an atomic writer snapshot.",
                "Execution metadata reflects the task store, not a fresh process liveness probe.",
                "Grouping, diagnostics and cross-run analysis are not implemented yet.",
                "Screenshot inventory covers explicit log references, not unreferenced files.",
            ],
            "provenance": {"parser_version": SCHEMA_VERSION, "sources": dict(self.paths)},
            "observation": self.observation,
        })

    def to_model(self) -> ExperimentData:
        """Build the complete canonical model; uncollected sections remain null."""
        traces = [{"finding_id": f["id"], "text": self.traces[f["id"]], "source": f["source"]}
                  for f in self.records["findings"]]
        data = {"report": self.report(), **self.records, "traces": traces, "observation": self.observation}
        if self.availability["steps"] not in ("available", "partial"):
            data.update(steps=None, executions=None, property_execution_trend=None)
        if self.availability["widget_inventory"] not in ("available", "partial"):
            data["widgets"] = None
        if not any(self.availability[k] in ("available", "partial")
                   for k in ("run_options", "report_configuration")):
            data["configuration"] = None
        return decode(ExperimentData, data)

    def _absent_crash_log_is_empty(self):
        """A successful detector outcome permits the optional crash log to be absent.

        Keep physical availability truthful. Unknown/imported or interrupted runs
        must not acquire a negative verdict merely because their log is absent.
        """
        execution = _execution(self.task)
        return (self.availability["crashes"] == "missing"
                and execution["status"] == "completed"
                and execution["finding_flags"]["crash_or_anr"] is False)

    def _event_count(self, kind):
        if self._absent_crash_log_is_empty():
            return 0
        if self.availability["crashes"] not in ("available", "partial"):
            return None
        if self.availability["crashes"] == "partial" and not any(
                f["type"] in ("crash", "anr") for f in self.records["findings"]):
            return None
        return sum(f["type"] == kind for f in self.records["findings"])

    def query(self, section, filters=None, cursor=None, limit=50):
        if section not in SECTIONS:
            raise ResultError("INVALID_SECTION", "Supported sections: " + ", ".join(SECTIONS))
        if not _count(limit) or not 1 <= limit <= 100:
            raise ResultError("INVALID_LIMIT", "limit must be between 1 and 100")
        filters = {} if filters is None else filters
        allowed = {
            "configuration": {"document": str, "key": str},
            "checks": {"name": str, "kind": str, "has_findings": bool},
            "findings": {"type": str, "check_name": str, "state": str},
            "activities": {"name": str, "covered": bool},
            "trends": {"metric": str},
            "steps": {"type": str, "start_step": int, "end_step": int, "execution_id": str},
            "executions": {"check_name": str, "kind": str, "state": str, "id": str},
            "artifacts": {"kind": str, "availability": str, "id": str},
            "widgets": {"activity": str, "class_name": str, "resource_id": str, "content_description": str, "parse_status": str},
            "property_execution_trend": {"start_step": int, "end_step": int},
        }[section]
        if not isinstance(filters, dict) or any(
            key not in allowed or type(value) is not allowed[key]
            or (key in ("start_step", "end_step") and value < 0)
            for key, value in filters.items()
        ):
            raise ResultError("INVALID_FILTER", "Unsupported filter or filter value type")
        binding = hashlib.sha256(json.dumps(
            [section, filters], sort_keys=True).encode()).hexdigest()[:16]
        prefix = self.snapshot_id + ":" + binding
        offset = 0
        if cursor is not None:
            try:
                snapshot, query, raw_offset = cursor.split(":")
                offset = int(raw_offset)
            except (ValueError, AttributeError):
                raise ResultError("INVALID_CURSOR", "Malformed cursor")
            if snapshot != self.snapshot_id:
                raise ResultError("STALE_SNAPSHOT", "Sources or task state changed; restart pagination")
            if query != binding or offset < 0:
                raise ResultError("INVALID_CURSOR", "Cursor belongs to another query")
        rows = self.records[section]
        for key, value in filters.items():
            if key in ("start_step", "end_step"):
                rows = [r for r in rows if r["monkey_step"] is not None and
                        (r["monkey_step"] >= value if key == "start_step" else r["monkey_step"] <= value)]
            elif key == "execution_id":
                execution = next((e for e in self.records["executions"] if e["id"] == value), None)
                if execution is None:
                    raise ResultError("EXECUTION_NOT_FOUND", "Unknown execution ID")
                boundaries = {s["id"]: s["source"]["line"] for s in self.records["steps"]}
                start, end = execution["start_step_id"], execution["end_step_id"]
                if start is None or end is None:
                    rows = [r for r in rows if r["id"] in (start, end)]
                else:
                    rows = [r for r in rows if boundaries[start] <= r["source"]["line"] <= boundaries[end]]
            elif key == "has_findings":
                rows = [r for r in rows if (r["fail"] + r["error"] > 0) == value]
            elif key == "name":
                rows = [r for r in rows if value in r["name"]]
            else:
                rows = [r for r in rows if r.get(key) == value]
        if offset > len(rows):
            raise ResultError("INVALID_CURSOR", "Cursor offset exceeds result count")
        end = offset + limit
        return validated(QueryResponse, {
            "schema_version": SCHEMA_VERSION, "task_id": self.task["task_id"],
            "snapshot_id": self.snapshot_id, "section": section,
            "items": rows[offset:end], "total": len(rows),
            "next_cursor": prefix + ":" + str(end) if end < len(rows) else None,
            "availability": dict(self.availability), "warnings": list(self.warnings),
            "warning_count": self.warning_count,
            "warnings_truncated": self.warning_count > len(self.warnings),
        })

    def finding(self, finding_id, snapshot_id, offset=0, limit=8000, context_before=0, context_after=0):
        if snapshot_id != self.snapshot_id:
            raise ResultError("STALE_SNAPSHOT", "Sources or task state changed; query findings again")
        if not _count(offset) or not _count(limit) or not 1 <= limit <= 32000:
            raise ResultError("INVALID_RANGE", "offset >= 0 and 1 <= limit <= 32000 required")
        item = next((f for f in self.records["findings"] if f["id"] == finding_id), None)
        if item is None:
            raise ResultError("FINDING_NOT_FOUND", "Finding does not exist in this snapshot")
        trace = self.traces[finding_id]
        if offset > len(trace):
            raise ResultError("INVALID_RANGE", "offset exceeds trace length")
        end = offset + limit
        return validated(FindingResponse, {
            "schema_version": SCHEMA_VERSION, "task_id": self.task["task_id"],
            "snapshot_id": self.snapshot_id, "finding": item,
            "trace": trace[offset:end], "offset": offset, "total_characters": len(trace),
            "next_offset": end if end < len(trace) else None,
            "availability": dict(self.availability), "warnings": list(self.warnings),
            "warning_count": self.warning_count,
            "warnings_truncated": self.warning_count > len(self.warnings),
            **self.finding_context(item, context_before, context_after),
        })
