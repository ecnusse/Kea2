"""Render MCP trend records without reading or modifying the HTML report."""
import hashlib
import io
import os
import tempfile
import threading

from .errors import ResultError

_RENDER_LOCK = threading.Lock()
CHART_VERSION = "4"
METRICS = {
    "activity_coverage_percent": ("Activity coverage", "Coverage (%)", "activity_coverage"),
    "unique_triggered_widget_count": ("Widget coverage", "Unique triggered widgets", "widget_coverage"),
    "property_execution_trend": ("Property execution", "Distinct properties started", "steps"),
}


def render_trend(snapshot, metric, snapshot_id):
    if metric not in METRICS:
        raise ResultError("INVALID_METRIC", "Supported metrics: " + ", ".join(METRICS))
    if snapshot_id != snapshot.snapshot_id:
        raise ResultError("STALE_SNAPSHOT", "Sources changed; refresh the report before requesting a chart")
    title, ylabel, source = METRICS[metric]
    html = (snapshot.root / "bug_report.html").resolve()
    html_path = str(html) if snapshot.root in html.parents and html.is_file() else None
    metadata = {
        "task_id": snapshot.task["task_id"], "snapshot_id": snapshot.snapshot_id,
        "metric": metric, "status": "unavailable", "mime_type": "image/png",
        "chart_version": CHART_VERSION,
        "image_path": None, "html_report_path": html_path,
        "source_availability": snapshot.availability[source],
        "sample_count": 0, "rendered_sample_count": 0, "downsampled": False,
        "x_label": "Monkey step", "y_label": ylabel,
        "is_live": snapshot.report()["is_live"],
    }
    if metric == "property_execution_trend":
        checks = snapshot.records["checks"]
        if snapshot.availability["checks"] == "available" and not any(
                c["kind"] != "invariant" for c in checks):
            metadata.update(status="not_applicable", reason="No properties in the recorded inventory")
            return metadata, None
        # Match the existing structured property trend and HTML counting convention.
        points = [(r["monkey_step"], r["executed_property_count"])
                  for r in snapshot.records[metric]]
        metadata["related_source_availability"] = {
            key: snapshot.availability[key] for key in ("checks", "activity_coverage")}
    else:
        points = [(r["monkey_step"], r["value"]) for r in snapshot.records["trends"]
                  if r["metric"] == metric]
    activity = metric == "activity_coverage_percent"
    if activity:
        points = [(r["monkey_step"], r["value"], r["raw"]["testedActivitiesCount"])
                  for r in snapshot.records["trends"] if r["metric"] == metric]
        metadata["y_label"] = "Activity Coverage (%)"
        metadata["secondary_y_label"] = "Tested Activities"
    if not points:
        metadata["reason"] = "No readable trend samples"
        return metadata, None
    metadata["sample_count"] = len(points)
    metadata["rendered_sample_count"] = len(points)
    # Preserve sample order and counter resets rather than silently sorting or smoothing.
    segments = [[]]
    for point in points:
        if segments[-1] and point[0] < segments[-1][-1][0]:
            segments.append([])
        segments[-1].append(point)
    metadata["counter_reset_count"] = len(segments) - 1
    # A visual origin is not a recorded sample. Preserve any actual step-zero
    # observation, and do not connect counter resets to invented baselines.
    metadata["origin_added"] = points[0][0] > 0
    if metadata["origin_added"]:
        segments[0].insert(0, (0, 0, 0) if activity else (0, 0))
    try:
        with _RENDER_LOCK:
            # MCP clients may pass a minimal environment. Matplotlib's Windows
            # font discovery requires WINDIR even when the OS itself does not.
            if os.name == "nt" and not os.environ.get("WINDIR"):
                import ctypes
                directory = ctypes.create_unicode_buffer(32768)
                length = ctypes.windll.kernel32.GetWindowsDirectoryW(directory, len(directory))
                if not 0 < length < len(directory):
                    raise ResultError("CHART_RENDER_ERROR", "Cannot locate the Windows font directory")
                os.environ["WINDIR"] = directory.value
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            from matplotlib.ticker import MaxNLocator
            fig = Figure(figsize=(10, 2.5), dpi=140, layout="constrained")
            canvas = FigureCanvasAgg(fig)
            ax = fig.subplots()
            secondary = ax.twinx() if activity else None
            color = "#3498db" if activity else (
                "#ff9800" if metric == "unique_triggered_widget_count" else "#f44336")
            label = "Activity Coverage (%)" if activity else ylabel
            if activity:
                ax.set_zorder(secondary.get_zorder() + 1)
                ax.patch.set_visible(False)
            for index, segment in enumerate(segments):
                xs = [p[0] for p in segment]
                ys = [p[1] for p in segment]
                ax.plot(xs, ys, color=color, linewidth=2,
                        label=label if index == 0 else None,
                        marker="o" if len(points) <= 80 or len(segment) == 1 else None,
                        markersize=4)
                if activity:
                    tested = [p[2] for p in segment]
                    secondary.plot(xs, tested, color="#2ecc71", linewidth=2,
                                   label="Tested Activities" if index == 0 else None,
                                   marker="o" if len(points) <= 80 or len(segment) == 1 else None,
                                   markersize=6)
                    secondary.fill_between(xs, tested, color="#2ecc71", alpha=0.10)
                ax.fill_between(xs, ys, color=color, alpha=0.10)
            ax.set_xlabel("Steps Count")
            ax.set_ylabel(metadata["y_label"])
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            ax.grid(True, alpha=0.2)
            ax.spines[["top", "right"]].set_visible(False)
            # Scale to observed values, not the theoretical coverage ceiling.
            # Keep a small headroom and a usable axis for an all-zero series.
            upper = max(p[1] for p in points) * 1.05 or 1
            if metric == "activity_coverage_percent":
                upper = min(100, upper)
            else:
                upper = max(1, upper)
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            ax.set_ylim(0, upper)
            if activity:
                secondary.set_ylim(0, max(1, max(p[2] for p in points) * 1.05))
                secondary.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=4))
                secondary.set_ylabel("Tested Activities", rotation=270, labelpad=18)
            for axis in (ax, secondary) if activity else (ax,):
                axis.tick_params(labelsize=8, colors="#666666", length=0)
                for spine in axis.spines.values():
                    spine.set_color("#dddddd")
                axis.spines["top"].set_visible(False)
            handles, labels = ax.get_legend_handles_labels()
            if activity:
                other_handles, other_labels = secondary.get_legend_handles_labels()
                handles += other_handles
                labels += other_labels
            fig.legend(handles, labels, loc="outside upper center",
                       ncol=2 if activity else 1, frameon=False, fontsize=9)
            ax.margins(x=0.01)
            ax.set_xlim(left=0)
            notes = "{} recorded samples".format(len(points))
            if metadata["source_availability"] != "available":
                notes += " | Partial source"
            if metadata["is_live"]:
                notes += " | Provisional"
            if len(segments) > 1:
                notes += " | Counter resets: {} (segments disconnected)".format(len(segments) - 1)
            fig.supxlabel(notes, fontsize=9, color="#475569")
            buffer = io.BytesIO()
            canvas.print_png(buffer)
            content = buffer.getvalue()
            fig.clear()
    except ImportError:
        raise ResultError("CHART_DEPENDENCY_MISSING", "Install kea2-python[mcp] to enable trend charts")
    metadata.update(status="available", sha256=hashlib.sha256(content).hexdigest(), size_bytes=len(content))
    # Export only generated files. Each snapshot has its own filenames, preserving old links.
    # Failure to export (e.g. read-only historical results) must not suppress the inline image.
    temporary = None
    try:
        directory = (snapshot.root / "mcp_charts").resolve()
        if snapshot.root not in directory.parents:
            raise OSError("Chart directory is outside the experiment")
        directory.mkdir(exist_ok=True)
        target = directory / (metric + "_v" + CHART_VERSION + "_" + snapshot.snapshot_id + ".png")
        with tempfile.NamedTemporaryFile(dir=str(directory), suffix=".tmp", delete=False) as stream:
            temporary = stream.name
            stream.write(content)
        os.replace(temporary, str(target))
        temporary = None
        metadata["image_path"] = str(target)
    except OSError:
        metadata["export_warning"] = "Image returned inline, but no local image could be saved"
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass
    return metadata, content
