"""Read-only widget inventory and HTML-compatible execution trend collection."""

import bisect
import re


class CoverageMixin:
    def _load_widgets(self):
        text = self._read("widget_inventory")
        if text is None:
            return
        markers = ("|class:", "|resourceId:", "|content-desc:")
        pattern = r"activity:(.*?)\|class:(.*?)\|resourceId:(.*?)\|content-desc:(.*)\|"
        seen = set()
        for line, raw in enumerate(text.splitlines(), 1):
            if not raw.strip():
                continue
            match = re.fullmatch(pattern, raw)
            status = "parsed"
            if match is None:
                status = "invalid"
            elif any(raw.count(marker) != 1 for marker in markers):
                status = "ambiguous"
            if status != "parsed":
                self.availability["widget_inventory"] = "partial"
                self._warn("widget_inventory", "WIDGET_" + status.upper(), line)
            values = match.groups() if status == "parsed" else (None,) * 4
            self.records["widgets"].append(dict(
                id="widget:{}".format(line), activity=values[0], class_name=values[1],
                resource_id=values[2], content_description=values[3], raw=raw,
                parse_status=status, source=self._source("widget_inventory", line=line)))
            if raw in seen:
                self._warn("widget_inventory", "DUPLICATE_WIDGET_RECORD", line)
            seen.add(raw)
        if (self.availability["widget_inventory"] == "available"
                and self.widget_count is not None and len(seen) != self.widget_count):
            self._warn("widget_inventory", "WIDGET_COUNTS_DISAGREE")

    def _load_property_trend(self):
        if self.availability["steps"] not in ("available", "partial"):
            return
        kinds = {c["name"]: c["kind"] for c in self.records["checks"]}
        executed, counts = set(), {}
        last_step = None
        for step in self.records["steps"]:
            if step["type"] != "ScriptInfo":
                continue
            info = self._step_info[step["id"]]
            name, state = info.get("propName"), info.get("state")
            kind = info.get("kind")
            kind = kind.strip().lower() if isinstance(kind, str) else ""
            if not kind and isinstance(name, str):
                kind = kinds.get(name, "unknown")
            number = step["monkey_step"]
            if not isinstance(name, str) or not name or state != "start" or kind == "invariant" or number is None:
                continue
            if last_step is not None and number < last_step:
                self._warn("steps", "PROPERTY_TREND_COUNTER_DECREASED", step["source"]["line"])
            last_step = number
            executed.add(name)
            counts[number] = len(executed)
        points = [t["monkey_step"] for t in self.records["trends"]
                  if t["metric"] == "activity_coverage_percent"]
        ordered = sorted(counts)
        for number in points or ordered:
            index = bisect.bisect_right(ordered, number) - 1
            self.records["property_execution_trend"].append({
                "monkey_step": number,
                "executed_property_count": counts[ordered[index]] if index >= 0 else 0,
                "source": self._source("steps"),
            })
