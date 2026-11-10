"""Versioned result contract, independent of parsing, HTML and MCP.

Dataclasses are the single source of truth for Python values, strict validation
and JSON Schema. No optional MCP or third-party dependency is required.
"""

import copy
import math
from dataclasses import MISSING, dataclass, field, fields, is_dataclass
from functools import lru_cache
from typing import Any, Dict, List, Literal, Optional, Union, get_args, get_origin, get_type_hints

SCHEMA_VERSION = "1.5"
Availability = Literal["available", "missing", "partial", "invalid", "unreadable", "too_large"]
CheckKind = Literal["property", "invariant", "unknown"]


def count(description):
    return field(metadata={"minimum": 0, "description": description})


class ContractError(ValueError):
    """A value does not satisfy the published output contract."""


@dataclass
class SourceReference:
    artifact: str
    line: Optional[int] = field(default=None, metadata={"minimum": 1, "omit_none": True})
    key: Optional[str] = field(default=None, metadata={"omit_none": True})


@dataclass
class EvidenceLink:
    relation: Literal["step", "screenshot", "execution", "artifact"]
    status: Literal["resolved", "unavailable", "ambiguous"]
    target_id: Optional[str]
    candidates: List[str]
    reason: Optional[str]


@dataclass
class CheckRecord:
    name: str
    kind: CheckKind
    precond_satisfied: Optional[int] = count("Recorded precondition satisfaction count.")
    executed: Optional[int] = count("Recorded execution count, not distinct checks.")
    fail: int = count("Assertion failure occurrences.")
    error: int = count("Execution error occurrences; not confirmed application defects.")
    pass_count: Optional[int] = count("Derived max(executed - fail - error, 0); not invariant success history.")
    pass_count_basis: Literal["derived_max_executed_minus_fail_minus_error", "not_applicable"]
    source: SourceReference
    raw: Dict[str, Any]


@dataclass
class CheckFinding:
    id: str
    type: CheckKind
    state: Literal["fail", "error"]
    check_name: str
    monkey_step: int = count("Monkey step counter; multiple events can share it.")
    description: str
    source: SourceReference
    trace_characters: int = count("Full trace length in Unicode characters.")
    evidence: List[EvidenceLink] = field(default_factory=list)


@dataclass
class AppFinding:
    id: str
    type: Literal["crash", "anr"]
    time_raw: str
    monkey_step: Optional[int] = count("Recorded Monkey step, or null when unknown.")
    process_name: Optional[str]
    pid: Optional[int] = count("Process ID, separate from process name.")
    description: str
    screenshot_reference: Optional[str]
    source: SourceReference
    trace_characters: int = count("Full trace length in Unicode characters.")
    evidence: List[EvidenceLink] = field(default_factory=list)


FindingRecord = Union[CheckFinding, AppFinding]


@dataclass
class ActivityRecord:
    name: str
    covered: bool
    in_inventory: bool
    visit_count: Optional[int] = count("Null means no traversal count was recorded.")
    source: SourceReference


@dataclass
class ActivityTrend:
    metric: Literal["activity_coverage_percent"]
    monkey_step: int = count("Monkey step counter, not elapsed time.")
    value: float = field(metadata={"minimum": 0, "maximum": 100, "description": "Percent, 0..100."})
    raw: Dict[str, Any]
    source: SourceReference


@dataclass
class WidgetTrend:
    metric: Literal["unique_triggered_widget_count"]
    monkey_step: int = count("Monkey step counter, not elapsed time.")
    value: int = count("Unique triggered widgets; not a percentage.")
    raw: Dict[str, Any]
    source: SourceReference


TrendRecord = Union[ActivityTrend, WidgetTrend]


@dataclass
class WarningRecord:
    source: str
    code: str
    line: Optional[int] = field(default=None, metadata={"minimum": 1, "omit_none": True})


@dataclass
class FindingFlags:
    property_violation: Optional[bool]
    crash_or_anr: Optional[bool]


@dataclass
class ExecutionMetadata:
    status: Literal["queued", "running", "cancelling", "cancelled", "completed", "execution_error", "unknown"]
    exit_code: Optional[int]
    finding_flags: FindingFlags
    created_at: Optional[str]
    started_at: Optional[str]
    finished_at: Optional[str]
    packages: Optional[List[str]]
    device_serial: Optional[str]
    requested_parameters: Optional[Dict[str, Any]]


@dataclass
class CheckCounts:
    count: int = count("Distinct checks of this kind.")
    executed_check_count: Optional[int] = field(metadata={"minimum": 0})
    violated_check_count: int = field(metadata={"minimum": 0, "description": "Distinct checks with fail/error; not unique root causes."})
    execution_count: Optional[int] = field(metadata={"minimum": 0})
    fail_occurrences: int = field(metadata={"minimum": 0})
    error_occurrences: int = field(metadata={"minimum": 0})


@dataclass
class CheckSummary:
    property: CheckCounts
    invariant: CheckCounts
    unknown: CheckCounts


@dataclass
class Summary:
    checks: Optional[CheckSummary]
    activity_coverage_percent: Optional[float] = field(metadata={"minimum": 0, "maximum": 100})
    unique_triggered_widget_count: Optional[int] = count("Null means unknown, not zero.")
    observed_crash_occurrences: Optional[int] = count("Valid parsed occurrences, not unique bugs. An absent optional log is zero for a completed run with exit code 0 or 1; otherwise unavailable sources are null.")
    observed_anr_occurrences: Optional[int] = count("Valid parsed occurrences, not unique bugs. An absent optional log is zero for a completed run with exit code 0 or 1; otherwise unavailable sources are null.")


@dataclass
class SourceAvailability:
    checks: Availability
    property_executions: Availability
    activity_coverage: Availability
    run_options: Availability
    report_configuration: Availability
    widget_inventory: Availability
    widget_coverage: Availability
    crashes: Availability
    steps: Availability


@dataclass
class SectionCount:
    record_count: int = count("Number of parsed records currently queryable.")


@dataclass
class Sections:
    checks: SectionCount
    findings: SectionCount
    activities: SectionCount
    trends: SectionCount
    steps: SectionCount
    executions: SectionCount
    artifacts: SectionCount
    configuration: SectionCount
    widgets: SectionCount
    property_execution_trend: SectionCount


@dataclass
class Provenance:
    parser_version: str
    sources: Dict[str, str]


@dataclass
class Envelope:
    schema_version: Literal["1.5"]
    task_id: str
    snapshot_id: str
    availability: SourceAvailability
    warnings: List[WarningRecord]
    warning_count: int = count("All warnings, including omitted examples.")
    warnings_truncated: bool


@dataclass
class ReportResponse(Envelope):
    execution: ExecutionMetadata
    data_completeness: Literal["available_sources", "partial"]
    is_live: bool
    summary: Summary
    sections: Sections
    limitations: List[str]
    provenance: Provenance
    observation: Optional["RunObservation"]


@dataclass
class Page(Envelope):
    total: int = count("Filtered record count before pagination.")
    next_cursor: Optional[str]


@dataclass
class CheckPage(Page):
    section: Literal["checks"]
    items: List[CheckRecord]


@dataclass
class FindingPage(Page):
    section: Literal["findings"]
    items: List[FindingRecord]


@dataclass
class ActivityPage(Page):
    section: Literal["activities"]
    items: List[ActivityRecord]


@dataclass
class TrendPage(Page):
    section: Literal["trends"]
    items: List[TrendRecord]


@dataclass
class FindingResponse(Envelope):
    finding: FindingRecord
    trace: str
    offset: int = count("Unicode character offset in full trace.")
    total_characters: int = count("Full trace length.")
    next_offset: Optional[int] = count("Next Unicode character offset, or null at end.")
    context_steps: List["StepRecord"] = field(default_factory=list)
    related_executions: List["ExecutionRecord"] = field(default_factory=list)
    related_artifacts: List["ArtifactRecord"] = field(default_factory=list)


@dataclass
class ErrorDetail:
    code: str
    message: str


@dataclass
class ErrorResponse:
    error: ErrorDetail


# These records define the next collection stages. Null collections in
# ExperimentData mean not implemented/unavailable, never "observed zero".
@dataclass
class StepRecord:
    id: str
    monkey_step: Optional[int] = count("Monkey counter; id identifies the individual event.")
    time_raw: Optional[str]
    type: str
    activity: Optional[str]
    action: Optional[str]
    parameters: Any
    source: SourceReference
    evidence: List[EvidenceLink]
    raw: Dict[str, Any]


@dataclass
class ArtifactRecord:
    id: str
    kind: Literal["screenshot", "log", "trace", "other"]
    relative_path: str
    mime_type: Optional[str]
    size_bytes: Optional[int] = count("Bytes, or null if unavailable.")
    availability: Availability


@dataclass
class ExecutionRecord:
    id: str
    check_name: str
    kind: CheckKind
    state: Literal["start", "pass", "fail", "error", "incomplete", "unknown"]
    start_step_id: Optional[str]
    end_step_id: Optional[str]
    evidence: List[EvidenceLink]
    source: SourceReference


@dataclass
class StepPage(Page):
    section: Literal["steps"]
    items: List[StepRecord]


@dataclass
class ExecutionPage(Page):
    section: Literal["executions"]
    items: List[ExecutionRecord]


@dataclass
class ArtifactPage(Page):
    section: Literal["artifacts"]
    items: List[ArtifactRecord]


@dataclass
class WidgetPage(Page):
    section: Literal["widgets"]
    items: List["WidgetRecord"]


@dataclass
class PropertyExecutionPage(Page):
    section: Literal["property_execution_trend"]
    items: List["PropertyExecutionPoint"]


@dataclass
class ConfigurationRecord:
    document: Literal["run_options", "report_configuration"]
    key: str
    value: Any
    encoding: Literal["json", "tagged_nonfinite"]
    source: SourceReference


@dataclass
class ConfigurationPage(Page):
    section: Literal["configuration"]
    items: List[ConfigurationRecord]


QueryResponse = Union[CheckPage, FindingPage, ActivityPage, TrendPage, StepPage, ExecutionPage, ArtifactPage, WidgetPage, PropertyExecutionPage, ConfigurationPage]


@dataclass
class ArtifactResponse:
    schema_version: Literal["1.5"]
    task_id: str
    snapshot_id: str
    artifact: ArtifactRecord
    content_type: Literal["image", "text"]
    sha256: str
    text: Optional[str]
    offset: Optional[int] = count("Unicode character offset; null for images.")
    next_offset: Optional[int] = count("Next text offset, or null at end/for images.")
    total_characters: Optional[int] = count("Full decoded text length; null for images.")


@dataclass
class WidgetRecord:
    id: str
    activity: Optional[str]
    class_name: Optional[str]
    resource_id: Optional[str]
    content_description: Optional[str]
    source: SourceReference
    raw: str
    parse_status: Literal["parsed", "ambiguous", "invalid"]


@dataclass
class Diagnostic:
    code: str
    observation: str
    rule: str
    evidence: List[EvidenceLink]
    limitations: List[str]


@dataclass
class TraceRecord:
    finding_id: str
    text: str
    source: SourceReference


@dataclass
class RunObservation:
    first_event_time_raw: Optional[str]
    last_event_time_raw: Optional[str]
    log_duration_seconds: Optional[float] = field(metadata={"minimum": 0})
    max_monkey_step: Optional[int] = count("Maximum recorded Monkey counter, not total log records.")
    log_record_count: Optional[int] = count("Observed event records, including script actions.")
    source: SourceReference


@dataclass
class PropertyExecutionPoint:
    monkey_step: int = count("Monkey step counter.")
    executed_property_count: int = count("Distinct properties started up to this point, not execution attempts.")
    source: SourceReference


@dataclass
class FindingGroup:
    id: str
    occurrence_ids: List[str]
    algorithm_version: str
    grouping_basis: str


@dataclass
class ExperimentData:
    report: ReportResponse
    checks: List[CheckRecord]
    findings: List[FindingRecord]
    activities: List[ActivityRecord]
    trends: List[TrendRecord]
    traces: List[TraceRecord]
    observation: Optional[RunObservation] = None
    steps: Optional[List[StepRecord]] = None
    artifacts: Optional[List[ArtifactRecord]] = None
    executions: Optional[List[ExecutionRecord]] = None
    configuration: Optional[List[ConfigurationRecord]] = None
    widgets: Optional[List[WidgetRecord]] = None
    diagnostics: Optional[List[Diagnostic]] = None
    property_execution_trend: Optional[List[PropertyExecutionPoint]] = None
    finding_groups: Optional[List[FindingGroup]] = None


@lru_cache(maxsize=None)
def _hints(model):
    return get_type_hints(model)


def decode(model, value, path="$"):
    """Build typed values without coercion; reject unknown normalized fields."""
    origin, args = get_origin(model), get_args(model)
    if model is Any:
        _json_value(value, path)
        return copy.deepcopy(value)
    if origin is Union:
        for alternative in args:
            try:
                return decode(alternative, value, path)
            except ContractError:
                pass
        raise ContractError(path + ": no matching union variant")
    if origin is Literal:
        if not any(type(value) is type(v) and value == v for v in args):
            raise ContractError(path + ": invalid enum value")
        return value
    if is_dataclass(model):
        if is_dataclass(value):
            value = to_dict(value)
        if not isinstance(value, dict):
            raise ContractError(path + ": expected object")
        declared = {f.name: f for f in fields(model)}
        if set(value) - set(declared):
            raise ContractError(path + ": unknown fields " + str(sorted(set(value) - set(declared))))
        hints, converted = _hints(model), {}
        for name, f in declared.items():
            if name not in value:
                if f.default is not MISSING or f.default_factory is not MISSING:
                    continue
                raise ContractError(path + "." + name + ": required field missing")
            item = decode(hints[name], value[name], path + "." + name)
            for bound, compare in (("minimum", lambda a, b: a < b), ("maximum", lambda a, b: a > b)):
                if item is not None and bound in f.metadata and compare(item, f.metadata[bound]):
                    raise ContractError(path + "." + name + ": violates " + bound)
            converted[name] = item
        result = model(**converted)
        _invariants(result, path)
        return result
    if origin is list:
        if not isinstance(value, list):
            raise ContractError(path + ": expected array")
        return [decode(args[0], item, "{}[{}]".format(path, i)) for i, item in enumerate(value)]
    if origin is dict:
        if not isinstance(value, dict):
            raise ContractError(path + ": expected object")
        return {decode(args[0], k, path): decode(args[1], v, path + "." + str(k)) for k, v in value.items()}
    valid = ((model is type(None) and value is None) or
             (model is float and type(value) in (int, float) and math.isfinite(value)) or
             (model in (str, int, bool) and type(value) is model))
    if not valid:
        raise ContractError(path + ": wrong value type")
    return value


def _json_value(value, path):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if isinstance(value, list):
        for item in value:
            _json_value(item, path)
        return
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        for item in value.values():
            _json_value(item, path)
        return
    raise ContractError(path + ": not a finite JSON value")


def _invariants(value, path):
    if isinstance(value, ArtifactResponse):
        if value.content_type == "image":
            if any(v is not None for v in (value.text, value.offset, value.next_offset, value.total_characters)):
                raise ContractError(path + ": image response cannot have text pagination")
        else:
            if value.text is None or value.offset is None or value.total_characters is None:
                raise ContractError(path + ": text response requires text pagination")
            end = value.offset + len(value.text)
            if end > value.total_characters or value.next_offset != (end if end < value.total_characters else None):
                raise ContractError(path + ": inconsistent artifact pagination")
    if isinstance(value, CheckRecord):
        if value.kind == "invariant":
            if any(v is not None for v in (value.precond_satisfied, value.executed, value.pass_count)) or value.pass_count_basis != "not_applicable":
                raise ContractError(path + ": invariant execution/pass statistics are not applicable")
        elif any(v is None for v in (value.precond_satisfied, value.executed, value.pass_count)) or value.pass_count_basis != "derived_max_executed_minus_fail_minus_error":
            raise ContractError(path + ": property statistics require counts and derivation")
        elif value.pass_count != max(value.executed - value.fail - value.error, 0):
            raise ContractError(path + ": pass_count does not match its derivation")
    if isinstance(value, CheckCounts):
        if max(value.executed_check_count or 0, value.violated_check_count) > value.count:
            raise ContractError(path + ": distinct check counts exceed inventory")
    if isinstance(value, EvidenceLink):
        if ((value.status == "resolved" and (not value.target_id or value.candidates))
                or (value.status != "resolved" and value.target_id is not None)
                or (value.status == "ambiguous" and len(value.candidates) < 2)
                or (value.status == "unavailable" and value.candidates)):
            raise ContractError(path + ": inconsistent evidence association")
    if isinstance(value, Envelope):
        if value.warning_count < len(value.warnings) or value.warnings_truncated != (value.warning_count > len(value.warnings)):
            raise ContractError(path + ": inconsistent warning count")
    if isinstance(value, FindingResponse):
        end = value.offset + len(value.trace)
        if (value.total_characters != value.finding.trace_characters or end > value.total_characters
                or value.next_offset != (end if end < value.total_characters else None)):
            raise ContractError(path + ": inconsistent trace pagination")
    if isinstance(value, Page) and len(value.items) > value.total:
        raise ContractError(path + ": page exceeds total record count")
    if isinstance(value, ReportResponse):
        optional_crashes_absent = (value.availability.crashes == "missing"
                                   and value.execution.status == "completed"
                                   and value.execution.finding_flags.crash_or_anr is False)
        complete = all(v == "available" or (k == "crashes" and optional_crashes_absent)
                       for k, v in to_dict(value.availability).items())
        if value.data_completeness != ("available_sources" if complete else "partial"):
            raise ContractError(path + ": inconsistent source completeness")
        if value.is_live != (value.execution.status in ("queued", "running", "cancelling")):
            raise ContractError(path + ": inconsistent live status")
    if isinstance(value, ExperimentData):
        for section in ("checks", "findings", "activities", "trends", "steps", "executions", "artifacts", "widgets", "property_execution_trend", "configuration"):
            if getattr(value.report.sections, section).record_count != len(getattr(value, section) or []):
                raise ContractError(path + ": section count does not match records")
        targets = {"step": value.steps, "screenshot": value.artifacts,
                   "artifact": value.artifacts, "execution": value.executions}
        for collection in (value.findings, value.steps, value.artifacts, value.executions, value.widgets, value.finding_groups):
            if collection is not None and len({r.id for r in collection}) != len(collection):
                raise ContractError(path + ": duplicate record IDs")
        findings = {f.id: f for f in value.findings}
        if len(value.traces) != len(findings) or {t.finding_id for t in value.traces} != set(findings):
            raise ContractError(path + ": every finding must have exactly one trace")
        for trace in value.traces:
            if len(trace.text) != findings[trace.finding_id].trace_characters:
                raise ContractError(path + ": full trace length disagrees with finding")
        for group in value.finding_groups or []:
            if (not group.occurrence_ids or len(set(group.occurrence_ids)) != len(group.occurrence_ids)
                    or not set(group.occurrence_ids) <= set(findings)):
                raise ContractError(path + ": invalid grouped occurrence references")
        records = list(value.findings) + (value.steps or []) + (value.executions or []) + (value.diagnostics or [])
        for record in records:
            for link in record.evidence:
                if link.status != "resolved":
                    continue
                candidates = targets[link.relation]
                target = next((r for r in candidates or [] if r.id == link.target_id), None)
                if target is None or (link.relation == "screenshot" and target.kind != "screenshot"):
                    raise ContractError(path + ": resolved evidence target does not exist")
        step_ids = {r.id for r in value.steps or []}
        for execution in value.executions or []:
            for step_id in (execution.start_step_id, execution.end_step_id):
                if step_id is not None and step_id not in step_ids:
                    raise ContractError(path + ": execution references an unknown step")


def to_dict(value):
    """Serialize models, preserving null except explicitly optional source keys."""
    if is_dataclass(value):
        return {f.name: to_dict(getattr(value, f.name)) for f in fields(value)
                if not (f.metadata.get("omit_none") and getattr(value, f.name) is None)}
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    return value


def validated(model, value):
    return to_dict(decode(model, value))


ROOT_MODELS = {
    "experiment": ExperimentData, "report": ReportResponse,
    "query": QueryResponse, "finding": FindingResponse, "error": ErrorResponse,
    "artifact": ArtifactResponse,
}


def json_schema(document="experiment"):
    """Generate portable Draft 7 JSON Schema from the exact runtime models."""
    if document not in ROOT_MODELS:
        raise ValueError("Unknown result schema document")
    definitions = {}

    def schema(model):
        origin, args = get_origin(model), get_args(model)
        if model is Any:
            return {}
        if origin is Union:
            return {"anyOf": [schema(t) for t in args]}
        if origin is Literal:
            return {"enum": list(args)}
        if is_dataclass(model):
            name = model.__name__
            if name not in definitions:
                definitions[name] = {}
                props, required, hints = {}, [], _hints(model)
                for f in fields(model):
                    props[f.name] = schema(hints[f.name])
                    props[f.name].update({k: v for k, v in f.metadata.items() if k != "omit_none"})
                    if f.default is MISSING and f.default_factory is MISSING:
                        required.append(f.name)
                definitions[name] = {"type": "object", "properties": props,
                                     "required": required, "additionalProperties": False}
            return {"$ref": "#/definitions/" + name}
        if origin is list:
            return {"type": "array", "items": schema(args[0])}
        if origin is dict:
            return {"type": "object", "additionalProperties": schema(args[1])}
        return {"type": {str: "string", int: "integer", float: "number",
                         bool: "boolean", type(None): "null"}[model]}

    root = schema(ROOT_MODELS[document])
    return {"$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Kea2 {} {}".format(document, SCHEMA_VERSION),
            **root, "definitions": definitions}
