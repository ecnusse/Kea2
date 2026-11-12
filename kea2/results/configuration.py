"""Read saved configuration without constructing Options or contacting devices."""

import json
import math


def _encode(value):
    """Encode legacy Python JSON nonfinite values without losing their meaning."""
    if isinstance(value, float) and not math.isfinite(value):
        token = "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
        return {"$nonfinite": token}, True
    if isinstance(value, (dict, list)):
        pairs = value.items() if isinstance(value, dict) else enumerate(value)
        result, changed = {}, False
        for key, item in pairs:
            result[key], nested = _encode(item)
            changed = changed or nested
        return (result if isinstance(value, dict) else list(result.values())), changed
    return value, False


class ConfigurationMixin:
    def _load_configuration(self):
        documents = {}
        for source in ("run_options", "report_configuration"):
            text = self._read(source)
            if text is None:
                continue

            def unique_object(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("Duplicate configuration key")
                    result[key] = value
                return result

            try:
                raw = json.loads(text, object_pairs_hook=unique_object)
                if not isinstance(raw, dict):
                    raise ValueError("Configuration must be an object")
                records = []
                for key, value in raw.items():
                    encoded, changed = _encode(value)
                    records.append({"document": source, "key": key, "value": encoded,
                                    "encoding": "tagged_nonfinite" if changed else "json",
                                    "source": self._source(source, key=key)})
                    if changed:
                        self._warn(source, "NONFINITE_CONFIGURATION_VALUE")
            except (ValueError, RecursionError):
                self.availability[source] = "invalid"
                self._warn(source, "INVALID_CONFIGURATION")
                continue
            documents[source] = raw
            self.records["configuration"].extend(records)
            if "log_stamp" in raw and raw["log_stamp"] != self.task["stamp"]:
                self._warn(source, "CONFIGURATION_STAMP_MISMATCH")
        if len(documents) == 2:
            options, report = documents["run_options"], documents["report_configuration"]
            # Preserve both values; never silently select a winner.
            for key in sorted(options.keys() & report.keys()):
                if type(options[key]) is not type(report[key]) or options[key] != report[key]:
                    self._warn("report_configuration", "CONFIGURATION_DISAGREEMENT:" + key)
