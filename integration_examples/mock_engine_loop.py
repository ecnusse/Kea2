import argparse
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import uiautomator2 as u2
from lxml import etree

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kea2.integration import Kea2PropertyEngine
from kea2.keaUtils import Options

_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple mock traversal engine for kea2/integration")
    parser.add_argument("--device-id", default="emulator-5554")
    parser.add_argument("--app-package", default="it.feio.android.omninotes.alpha")
    parser.add_argument("--property-file", default=str(Path(__file__).parent / "quicktest3.py"))
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--interval-sec", type=float, default=0.2)
    parser.add_argument("--swipe-prob", type=float, default=0.2, help="Probability of swipe action")
    parser.add_argument("--back-prob", type=float, default=0.05, help="Probability of back action")
    return parser


def _parse_bounds(raw: str) -> Optional[Tuple[int, int, int, int]]:
    m = _BOUNDS_RE.match(raw or "")
    if not m:
        return None
    x1, y1, x2, y2 = [int(m.group(i)) for i in range(1, 5)]
    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2, y2


def _pick_clickable(xml: str, rnd: random.Random) -> Optional[Tuple[int, int, str]]:
    try:
        root = etree.fromstring(xml.encode("utf-8"))
    except Exception:
        return None
    nodes = root.xpath(".//node[@enabled='true' and @clickable='true' and @bounds]")
    candidates = []
    for node in nodes:
        bounds = _parse_bounds(node.get("bounds"))
        if not bounds:
            continue
        x1, y1, x2, y2 = bounds
        if (x2 - x1) * (y2 - y1) < 64:
            continue
        target = node.get("resource-id") or node.get("text") or node.get("content-desc") or ""
        candidates.append(((x1 + x2) // 2, (y1 + y2) // 2, target))
    return rnd.choice(candidates) if candidates else None


def _do_swipe(d: u2.Device) -> Dict[str, object]:
    try:
        w, h = d.window_size()
    except Exception:
        w, h = 1080, 1920
    sx, sy = int(w * 0.5), int(h * 0.8)
    ex, ey = int(w * 0.5), int(h * 0.2)
    d.swipe(sx, sy, ex, ey, duration=0.15)
    return {"action_type": "swipe", "target": "", "coords": {"from": [sx, sy], "to": [ex, ey]}}


def _do_action(d: u2.Device, ui_xml: str, rnd: random.Random, swipe_prob: float, back_prob: float) -> Dict[str, object]:
    roll = rnd.random()
    if roll < back_prob:
        d.press("back")
        return {"action_type": "back", "target": "", "coords": None}
    if roll < back_prob + swipe_prob:
        return _do_swipe(d)

    picked = _pick_clickable(ui_xml, rnd)
    if picked is None:
        return _do_swipe(d)
    x, y, target = picked
    d.click(x, y)
    return {"action_type": "click", "target": target, "coords": [x, y]}


def _ensure_foreground(d: u2.Device, app_package: str) -> None:
    if not app_package:
        return
    try:
        current = d.app_current()
        current_pkg = current.get("package") if isinstance(current, dict) else ""
    except Exception:
        current_pkg = ""
    if current_pkg == app_package:
        return
    try:
        d.app_start(app_package, stop=False)
    except TypeError:
        d.app_start(app_package)


def main() -> None:
    args = build_parser().parse_args()
    prop_path = Path(args.property_file).resolve()
    if not prop_path.exists():
        raise SystemExit(f"Property file not found: {prop_path}")

    kea = Kea2PropertyEngine()
    kea.init_kea2(
        Options(
            serial="emulator-5554",
            packageNames=["it.feio.android.omninotes.alpha"],
            driverName="d",
            propertytest_args=["discover", "-s", "integration_examples", "-p", "quicktest3.py"],
        )
    )
    print("[mock-engine] kea2 initialized")

    d = u2.connect(args.device_id)
    d.settings["wait_timeout"] = 2.5
    rnd = random.Random()

    try:
        for step_id in range(1, args.max_steps + 1):
            try:
                _ensure_foreground(d, args.app_package)
                ui_before = d.dump_hierarchy()
                action_meta = _do_action(d, ui_before, rnd, args.swipe_prob, args.back_prob)
                ui_after = d.dump_hierarchy()
                step_result = kea.execute_property(ui_xml=ui_after)
                print(
                    f"[mock-engine] step={step_id} action={action_meta['action_type']} "
                    f"satisfied={step_result['precondition_satisfied']} "
                    f"props={step_result['properties_executed']} "
                    f"errors={step_result['errors']}"
                )
            except Exception as exc:
                print(f"[mock-engine] step={step_id} skipped: {type(exc).__name__}: {exc}")

            if args.interval_sec > 0:
                time.sleep(args.interval_sec)

        print("[mock-engine] result:")
        print(json.dumps(kea.get_result(), ensure_ascii=False, indent=2))
    finally:
        kea.stop_kea2()


if __name__ == "__main__":
    main()
