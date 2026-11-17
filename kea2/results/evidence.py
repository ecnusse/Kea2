"""Read-only event reconstruction and evidence retrieval."""

import hashlib
import io
import json
from datetime import datetime
from pathlib import Path, PureWindowsPath

from .errors import ResultError
from .models import SCHEMA_VERSION, ArtifactResponse, validated

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_TEXT_BYTES = 64 * 1024 * 1024


def step_number(value):
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdigit():
        try:
            return int(value)
        except ValueError:
            pass
    return None


def _invalid_constant(value):
    raise ValueError("Non-finite JSON constant: " + value)


def link(relation, candidates, reason):
    candidates = list(dict.fromkeys(candidates))
    return {
        "relation": relation,
        "status": "resolved" if len(candidates) == 1 else "ambiguous" if candidates else "unavailable",
        "target_id": candidates[0] if len(candidates) == 1 else None,
        "candidates": candidates if len(candidates) > 1 else [],
        "reason": reason,
    }


class EvidenceMixin:
    def _safe_artifact_path(self, relative):
        # Logs are untrusted. Reject POSIX/Windows absolute paths, ADS, traversal
        # and links resolving outside this experiment even on another OS.
        relative = relative.replace("\\", "/")
        if (PureWindowsPath(relative).drive or relative.startswith("/")
                or ":" in relative or ".." in relative.split("/")):
            raise ResultError("UNSAFE_ARTIFACT", "Artifact path is outside the experiment")
        resolved = (self.root / relative).resolve()
        if self.root not in resolved.parents:
            raise ResultError("UNSAFE_ARTIFACT", "Artifact path resolves outside the experiment")
        return resolved

    def _register_artifact(self, relative, kind="log"):
        relative = relative.replace("\\", "/")
        identifier = "artifact:" + hashlib.sha256(relative.encode()).hexdigest()[:24]
        if identifier in self._artifact_index:
            return self._artifact_index[identifier]
        state, size, stamp = "missing", None, None
        suffix = Path(relative).suffix.lower()
        mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".webp": "image/webp"}.get(suffix) if kind == "screenshot" else "text/plain"
        try:
            path = self._safe_artifact_path(relative)
            stat = path.stat()
            if not path.is_file():
                state = "invalid"
            else:
                size, stamp = stat.st_size, (stat.st_size, stat.st_mtime_ns)
                maximum = MAX_IMAGE_BYTES if kind == "screenshot" else MAX_TEXT_BYTES
                state = "available" if size <= maximum else "too_large"
        except FileNotFoundError:
            pass
        except ResultError:
            state = "invalid"
        except OSError:
            state = "unreadable"
        record = {"id": identifier, "kind": kind, "relative_path": relative,
                  "mime_type": mime, "size_bytes": size, "availability": state}
        self._artifact_index[identifier] = record
        self._artifact_stamps[identifier] = stamp
        self.records["artifacts"].append(record)
        # Listing and retrieval share the same metadata snapshot.
        self.digest.update(json.dumps([record, stamp], sort_keys=True).encode())
        return record

    def _screenshot_link(self, reference):
        if not reference or not isinstance(reference, str):
            return link("screenshot", [], "No explicit screenshot reference")
        # Validate the reference itself before prefixing a result-relative folder.
        try:
            self._safe_artifact_path(reference)
        except ResultError:
            return link("screenshot", [], "Unsafe screenshot reference rejected")
        relative = "output_{}/screenshots/{}".format(self.task["stamp"], reference)
        artifact = self._register_artifact(relative, "screenshot")
        candidates = [artifact["id"]] if artifact["availability"] == "available" else []
        return link("screenshot", candidates, "Explicit log reference; file " + artifact["availability"])

    def _load_evidence(self):
        self._artifact_index, self._artifact_stamps = {}, {}
        self._execution_keys = {}
        self._step_info = {}
        self.observation = None
        for relative in self.paths.values():
            self._register_artifact(relative)
        for prefix in ("kea2", "fastbot"):
            self._register_artifact("{}_{}.log".format(prefix, self.task["stamp"]))

        active = []
        kinds = {c["name"]: c["kind"] for c in self.records["checks"]}
        for line_no, raw in self._json_lines("steps"):
            number = step_number(raw.get("MonkeyStepsCount"))
            kind = raw.get("Type")
            if number is None or not isinstance(kind, str):
                self._invalid("steps", line_no)
                continue
            info = raw.get("Info")
            if isinstance(info, str) and info.strip().startswith(("{", "[")):
                try:
                    info = json.loads(info, parse_constant=_invalid_constant)
                except (ValueError, RecursionError):
                    self._invalid("steps", line_no)
                    # Preserve the event, but never reconstruct an execution
                    # from an invalid marker.
            details = info if isinstance(info, dict) else {}
            action = details.get("method", details.get("act"))
            if info == "kill_apps":
                action = "kill_apps"
            record = {
                "id": "step:{}".format(line_no), "monkey_step": number,
                "time_raw": raw.get("Time") if isinstance(raw.get("Time"), str) else None,
                "type": kind, "activity": raw.get("Activity") if isinstance(raw.get("Activity"), str) else None,
                "action": action if isinstance(action, str) else None,
                "parameters": details.get("params", details.get("pos")),
                "source": self._source("steps", line=line_no), "raw": raw,
                "evidence": [self._screenshot_link(raw.get("Screenshot"))],
            }
            self.records["steps"].append(record)
            self._step_info[record["id"]] = details
            if kind != "ScriptInfo":
                continue
            name, state = details.get("propName"), details.get("state")
            if not isinstance(name, str) or not name or state not in ("start", "pass", "fail", "error"):
                self._invalid("steps", line_no)
                continue
            check_kind = details.get("kind", kinds.get(name, "unknown"))
            if check_kind not in ("property", "invariant"):
                check_kind = "unknown"
            explicit_start = step_number(details.get("startStepsCount"))
            if state == "start":
                execution = self._new_execution(record, name, check_kind, "incomplete", record["id"], None,
                                                explicit_start if explicit_start is not None else number)
                active.append((execution, self.warning_count))
                continue
            candidates = [(e, warnings) for e, warnings in active
                          if e["check_name"] == name and e["kind"] == check_kind
                          and (explicit_start is None or self._execution_keys[e["id"]][2] == explicit_start)]
            if len(candidates) == 1 and candidates[0][1] == self.warning_count:
                execution = candidates[0][0]
                execution["state"], execution["end_step_id"] = state, record["id"]
                execution["evidence"].append(link("step", [record["id"]], "Explicit terminal marker"))
                active.remove(candidates[0])
            else:
                # Invariants often have only terminal markers. Do not invent a
                # preceding execution interval when a start marker is absent.
                self._new_execution(record, name, check_kind, state, None, record["id"],
                                    explicit_start if explicit_start is not None else number)
                if candidates:
                    self._warn("steps", "AMBIGUOUS_EXECUTION_BOUNDARY", line_no)
                    active = [(e, w) for e, w in active if (e, w) not in candidates]

        self._observe_run()
        self._link_findings()

    def _new_execution(self, step, name, kind, state, start, end, start_count):
        record = {"id": "segment:" + step["id"], "check_name": name, "kind": kind,
                  "state": state, "start_step_id": start, "end_step_id": end,
                  "source": step["source"],
                  "evidence": [link("step", [step["id"]], "Explicit ScriptInfo marker")]}
        self.records["executions"].append(record)
        self._execution_keys[record["id"]] = (name, kind, start_count)
        return record

    def _observe_run(self):
        if self.availability["steps"] not in ("available", "partial"):
            return
        steps = self.records["steps"]
        times = [s["time_raw"] for s in steps if s["time_raw"]]
        duration = None
        if times:
            try:
                duration = (datetime.fromisoformat(times[-1]) - datetime.fromisoformat(times[0])).total_seconds()
                if duration < 0:
                    raise ValueError("Reversed time")
            except (ValueError, TypeError, OverflowError):
                duration = None
                self._warn("steps", "INVALID_TIME_RANGE")
        self.observation = {
            "first_event_time_raw": times[0] if times else None,
            "last_event_time_raw": times[-1] if times else None,
            "log_duration_seconds": duration,
            "max_monkey_step": max((s["monkey_step"] for s in steps), default=None),
            "log_record_count": len(steps), "source": self._source("steps"),
        }

    def _link_findings(self):
        occurrences = {}
        for finding in self.records["findings"]:
            if "check_name" in finding:
                key = (finding["check_name"], finding["type"], finding["monkey_step"], finding["state"])
                occurrences[key] = occurrences.get(key, 0) + 1
        steps_by_id = {s["id"]: s for s in self.records["steps"]}
        for finding in self.records["findings"]:
            if "check_name" in finding:
                key = (finding["check_name"], finding["type"], finding["monkey_step"], finding["state"])
                candidates = [e for e in self.records["executions"]
                              if self._execution_keys[e["id"]] == key[:3] and e["state"] == key[3]]
                ids = [e["id"] for e in candidates]
                reason = "Exact check name, kind, start counter and outcome"
                if len(ids) == 1 and occurrences[key] > 1:
                    ids = []
                    reason = "Repeated occurrences cannot be uniquely paired with this execution"
                association = link("execution", ids, reason)
                finding["evidence"] = [association]
                if association["status"] == "resolved":
                    end = candidates[0]["end_step_id"]
                    if end:
                        finding["evidence"].append(link("step", [end], "Matched execution terminal marker"))
                        finding["evidence"].extend(steps_by_id[end]["evidence"])
            else:
                candidates = [s["id"] for s in self.records["steps"]
                              if finding["monkey_step"] is not None and s["monkey_step"] == finding["monkey_step"]]
                finding["evidence"] = [
                    link("step", candidates, "Matching Monkey counter only; does not establish causality"),
                    self._screenshot_link(finding.get("screenshot_reference")),
                ]

    def finding_context(self, finding, before, after):
        if any(type(v) is not int or not 0 <= v <= 20 for v in (before, after)):
            raise ResultError("INVALID_RANGE", "context_before/context_after must be 0..20")
        evidence = finding["evidence"]
        ids = {e["target_id"] for e in evidence if e["status"] == "resolved"}
        executions = [e for e in self.records["executions"] if e["id"] in ids]
        artifact_ids = set(ids)
        for execution in executions:
            for step in self.records["steps"]:
                if step["id"] in (execution["start_step_id"], execution["end_step_id"]):
                    artifact_ids.update(e["target_id"] for e in step["evidence"] if e["status"] == "resolved")
        positions = [i for i, step in enumerate(self.records["steps"]) if step["id"] in ids]
        context = []
        if len(positions) == 1:
            anchor = positions[0]
            context = self.records["steps"][max(0, anchor - before):anchor + after + 1]
            for step in context:
                artifact_ids.update(e["target_id"] for e in step["evidence"] if e["status"] == "resolved")
        return {"context_steps": context, "related_executions": executions,
                "related_artifacts": [a for a in self.records["artifacts"] if a["id"] in artifact_ids]}

    def artifact(self, artifact_id, snapshot_id, offset=0, limit=8000):
        if snapshot_id != self.snapshot_id:
            raise ResultError("STALE_SNAPSHOT", "Sources or artifacts changed; query again")
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 32000:
            raise ResultError("INVALID_RANGE", "offset >= 0 and limit 1..32000 required")
        record = self._artifact_index.get(artifact_id)
        if record is None:
            raise ResultError("ARTIFACT_NOT_FOUND", "Unknown artifact ID")
        if record["availability"] != "available":
            raise ResultError("ARTIFACT_UNAVAILABLE", "Artifact is " + record["availability"])
        path = self._safe_artifact_path(record["relative_path"])
        is_image = record["kind"] == "screenshot"
        maximum = MAX_IMAGE_BYTES if is_image else MAX_TEXT_BYTES
        with path.open("rb") as stream:
            before = path.stat()
            if (before.st_size, before.st_mtime_ns) != self._artifact_stamps[artifact_id]:
                raise ResultError("STALE_SNAPSHOT", "Artifact changed before reading")
            raw = stream.read(maximum + 1)
            after = path.stat()
        if len(raw) > maximum:
            raise ResultError("ARTIFACT_TOO_LARGE", "Artifact exceeds read size limit")
        if (after.st_size, after.st_mtime_ns) != self._artifact_stamps[artifact_id]:
            raise ResultError("STALE_SNAPSHOT", "Artifact changed during reading")
        response = {"schema_version": SCHEMA_VERSION, "task_id": self.task["task_id"],
                    "snapshot_id": self.snapshot_id, "artifact": dict(record),
                    "content_type": "image" if is_image else "text",
                    "sha256": hashlib.sha256(raw).hexdigest(), "text": None,
                    "offset": None, "next_offset": None, "total_characters": None}
        if is_image:
            if offset:
                raise ResultError("INVALID_RANGE", "Images do not support text offsets")
            from PIL import Image
            try:
                with Image.open(io.BytesIO(raw)) as image:
                    mime = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}.get(image.format)
                    if mime is None:
                        raise ValueError("Unsupported image format")
                    image.verify()
            except (OSError, ValueError, Image.DecompressionBombError) as exc:
                raise ResultError("INVALID_IMAGE", "Cannot decode screenshot") from exc
            response["artifact"]["mime_type"] = mime
            return validated(ArtifactResponse, response), raw
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ResultError("INVALID_TEXT_ENCODING", "Artifact is not valid UTF-8; refusing silent replacement") from exc
        if offset > len(text):
            raise ResultError("INVALID_RANGE", "offset exceeds text length")
        end = offset + limit
        response.update(text=text[offset:end], offset=offset, total_characters=len(text),
                        next_offset=end if end < len(text) else None)
        return validated(ArtifactResponse, response), None
