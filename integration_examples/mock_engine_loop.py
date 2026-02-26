import argparse
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import uiautomator2 as u2
from lxml import etree

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kea2.integration import end_session, get_session_state, on_engine_step, start_session

_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mock an engine traversal loop: perform real UI actions and call Kea2 on_engine_step."
    )
    parser.add_argument(
        "--device-id",
        default="emulator-5554"
    )
    parser.add_argument(
        "--app-package",
        default="it.feio.android.omninotes.alpha"
    )
    parser.add_argument(
        "--foreground-wait-sec",
        type=float,
        default=0.8
    )
    parser.add_argument(
        "--property-file",
        default=str(Path(__file__).parent / "quicktest3.py")
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=30
    )
    parser.add_argument(
        "--interval-sec",
        type=float,
        default=0.2
    )
    parser.add_argument(
        "--max-properties-per-step",
        type=int,
        default=2
    )
    parser.add_argument(
        "--per-step-timeout-sec",
        type=int,
        default=10
    )
    parser.add_argument(
        "--dump-retries",
        type=int,
        default=3
    )
    parser.add_argument(
        "--reconnect-retries",
        type=int,
        default=1
    )
    parser.add_argument(
        "--action-retries",
        type=int,
        default=1
    )
    return parser


def parse_bounds(raw: str) -> Optional[Tuple[int, int, int, int]]:
    m = _BOUNDS_RE.match(raw or "")
    if not m:
        return None
    x1, y1, x2, y2 = [int(m.group(i)) for i in range(1, 5)]
    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2, y2


def collect_clickable_centers(ui_xml: str) -> List[Dict[str, object]]:
    try:
        root = etree.fromstring(ui_xml.encode("utf-8"))
    except Exception:
        return []
    nodes = root.xpath(".//node[@enabled='true' and @clickable='true' and @bounds]")
    centers: List[Dict[str, object]] = []
    for node in nodes:
        bounds = parse_bounds(node.get("bounds"))
        if not bounds:
            continue
        x1, y1, x2, y2 = bounds
        # Skip tiny widgets to reduce noise.
        if (x2 - x1) * (y2 - y1) < 64:
            continue
        target = (
            node.get("resource-id")
            or node.get("text")
            or node.get("content-desc")
            or ""
        )
        centers.append(
            {
                "x": (x1 + x2) // 2,
                "y": (y1 + y2) // 2,
                "target": target,
            }
        )
    return centers


def do_swipe(d: u2.Device, rnd: random.Random) -> Dict[str, object]:
    try:
        w, h = d.window_size()
    except Exception:
        w, h = 1080, 1920
    horizontal = rnd.random() < 0.5
    if horizontal:
        y = int(h * rnd.uniform(0.30, 0.70))
        if rnd.random() < 0.5:
            sx, ex = int(w * 0.85), int(w * 0.15)
            direction = "left"
        else:
            sx, ex = int(w * 0.15), int(w * 0.85)
            direction = "right"
        sy = ey = y
    else:
        x = int(w * rnd.uniform(0.30, 0.70))
        if rnd.random() < 0.5:
            sy, ey = int(h * 0.80), int(h * 0.20)
            direction = "up"
        else:
            sy, ey = int(h * 0.20), int(h * 0.80)
            direction = "down"
        sx = ex = x
    return {
        "type": "swipe",
        "direction": direction,
        "from": [sx, sy],
        "to": [ex, ey],
    }


def connect_device(device_id: str) -> u2.Device:
    d = u2.connect(device_id)
    d.settings["wait_timeout"] = 2.5
    return d


def _run_with_reconnect(
    d: u2.Device,
    device_id: str,
    op: Callable[[u2.Device], object],
    retries: int,
    reconnect_retries: int,
) -> Tuple[Optional[object], u2.Device, Optional[str]]:
    last_error: Optional[str] = None
    reconnect_left = reconnect_retries
    attempts_left = max(1, retries)
    while attempts_left > 0:
        try:
            return op(d), d, None
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            attempts_left -= 1
            if attempts_left > 0:
                time.sleep(0.2)
                continue
            if reconnect_left <= 0:
                break
            reconnect_left -= 1
            d = connect_device(device_id)
            attempts_left = max(1, retries)
    return None, d, last_error


def safe_dump_hierarchy(
    d: u2.Device,
    device_id: str,
    dump_retries: int,
    reconnect_retries: int,
) -> Tuple[Optional[str], u2.Device, Optional[str]]:
    return _run_with_reconnect(
        d=d,
        device_id=device_id,
        op=lambda dev: dev.dump_hierarchy(),
        retries=dump_retries,
        reconnect_retries=reconnect_retries,
    )


def _current_package(d: u2.Device) -> str:
    try:
        current = d.app_current()
    except Exception:
        return ""
    if not isinstance(current, dict):
        return ""
    package = current.get("package")
    return package.strip() if isinstance(package, str) else ""


def ensure_foreground_app(
    d: u2.Device,
    device_id: str,
    app_package: str,
    action_retries: int,
    reconnect_retries: int,
    wait_sec: float,
) -> Tuple[u2.Device, Optional[str]]:
    if not app_package:
        return d, None
    current_pkg = _current_package(d)
    if current_pkg == app_package:
        return d, None

    def _start(dev: u2.Device) -> bool:
        try:
            dev.app_start(app_package, stop=False)
        except TypeError:
            dev.app_start(app_package)
        return True

    _, d, start_error = _run_with_reconnect(
        d=d,
        device_id=device_id,
        op=_start,
        retries=action_retries,
        reconnect_retries=reconnect_retries,
    )
    time.sleep(wait_sec)
    current_pkg = _current_package(d)
    if current_pkg != app_package:
        msg = start_error or f"foreground_not_reached: current={current_pkg or '<unknown>'}"
        return d, msg
    return d, None


def _fallback_action(
    d: u2.Device,
    rnd: random.Random,
    device_id: str,
    action_retries: int,
    reconnect_retries: int,
    dump_error: Optional[str],
) -> Tuple[Dict[str, object], u2.Device]:
    # Prefer back/swipe when UI snapshot cannot be parsed or fetched.
    if rnd.random() < 0.5:
        _, d, action_error = _run_with_reconnect(
            d=d,
            device_id=device_id,
            op=lambda dev: dev.press("back"),
            retries=action_retries,
            reconnect_retries=reconnect_retries,
        )
        meta = {
            "action_type": "back",
            "target": "",
            "coords": None,
            "degraded": True,
            "dump_error": dump_error,
            "action_error": action_error,
        }
        return meta, d

    swipe_meta = do_swipe(d, rnd)
    _, d, action_error = _run_with_reconnect(
        d=d,
        device_id=device_id,
        op=lambda dev: dev.swipe(
            swipe_meta["from"][0],
            swipe_meta["from"][1],
            swipe_meta["to"][0],
            swipe_meta["to"][1],
            duration=0.15,
        ),
        retries=action_retries,
        reconnect_retries=reconnect_retries,
    )
    return {
        "action_type": "swipe",
        "target": "",
        "coords": {"from": swipe_meta["from"], "to": swipe_meta["to"]},
        "degraded": True,
        "dump_error": dump_error,
        "action_error": action_error,
    }, d


def do_one_engine_action(
    d: u2.Device,
    rnd: random.Random,
    device_id: str,
    dump_retries: int,
    reconnect_retries: int,
    action_retries: int,
) -> Tuple[Dict[str, object], u2.Device]:
    ui_xml, d, dump_error = safe_dump_hierarchy(
        d=d,
        device_id=device_id,
        dump_retries=dump_retries,
        reconnect_retries=reconnect_retries,
    )
    if not ui_xml:
        return _fallback_action(
            d=d,
            rnd=rnd,
            device_id=device_id,
            action_retries=action_retries,
            reconnect_retries=reconnect_retries,
            dump_error=dump_error,
        )

    clickable_centers = collect_clickable_centers(ui_xml)
    action_roll = rnd.random()

    # 80% click, 18% swipe, 2% back.
    if clickable_centers and action_roll < 0.80:
        picked = rnd.choice(clickable_centers)
        x = int(picked["x"])
        y = int(picked["y"])
        target = str(picked.get("target") or "")
        _, d, action_error = _run_with_reconnect(
            d=d,
            device_id=device_id,
            op=lambda dev: dev.click(x, y),
            retries=action_retries,
            reconnect_retries=reconnect_retries,
        )
        return {
            "action_type": "click",
            "target": target,
            "coords": [x, y],
            "degraded": False,
            "dump_error": dump_error,
            "action_error": action_error,
        }, d
    if action_roll < 0.98:
        swipe_meta = do_swipe(d, rnd)
        _, d, action_error = _run_with_reconnect(
            d=d,
            device_id=device_id,
            op=lambda dev: dev.swipe(
                swipe_meta["from"][0],
                swipe_meta["from"][1],
                swipe_meta["to"][0],
                swipe_meta["to"][1],
                duration=0.15,
            ),
            retries=action_retries,
            reconnect_retries=reconnect_retries,
        )
        swipe_meta["degraded"] = False
        swipe_meta["dump_error"] = dump_error
        swipe_meta["action_error"] = action_error
        return {
            "action_type": "swipe",
            "target": "",
            "coords": {"from": swipe_meta["from"], "to": swipe_meta["to"]},
            "degraded": swipe_meta["degraded"],
            "dump_error": swipe_meta["dump_error"],
            "action_error": swipe_meta["action_error"],
        }, d

    _, d, action_error = _run_with_reconnect(
        d=d,
        device_id=device_id,
        op=lambda dev: dev.press("back"),
        retries=action_retries,
        reconnect_retries=reconnect_retries,
    )
    return {
        "action_type": "back",
        "target": "",
        "coords": None,
        "degraded": False,
        "dump_error": dump_error,
        "action_error": action_error,
    }, d


def main() -> None:
    args = build_parser().parse_args()

    prop_path = Path(args.property_file).resolve()
    if not prop_path.exists():
        raise SystemExit(f"Property file not found: {prop_path}")

    discover_spec = {
        "propertytest_args": [
            "discover",
            "-s",
            str(prop_path.parent),
            "-p",
            prop_path.name,
        ]
    }
    config = {
        "device_id": args.device_id,
        "driver_name": "d",
        "max_properties_per_step": args.max_properties_per_step,
        "per_step_timeout_sec": args.per_step_timeout_sec,
    }

    rnd = random.Random()
    d = connect_device(args.device_id)

    session_id = start_session(config=config, discover_spec=discover_spec)
    print(f"[mock-engine] session_id={session_id}")

    end_reason = "max_steps_reached"
    try:
        for step_id in range(1, args.max_steps + 1):
            d, fg_error = ensure_foreground_app(
                d=d,
                device_id=args.device_id,
                app_package=args.app_package,
                action_retries=args.action_retries,
                reconnect_retries=args.reconnect_retries,
                wait_sec=args.foreground_wait_sec,
            )
            action_meta, d = do_one_engine_action(
                d=d,
                rnd=rnd,
                device_id=args.device_id,
                dump_retries=args.dump_retries,
                reconnect_retries=args.reconnect_retries,
                action_retries=args.action_retries,
            )
            step_result = on_engine_step(
                session_id=session_id,
                step_id=step_id,
                event_meta={
                    "action_type": action_meta.get("action_type", ""),
                    "target": action_meta.get("target", ""),
                    "coords": action_meta.get("coords"),
                },
            )
            print(
                    f"[mock-engine] step={step_id} action={action_meta['action_type']} "
                    f"satisfied={step_result['precondition_satisfied']} "
                    f"props={step_result['properties_executed']} "
                    f"errors={step_result['errors']} "
                    f"stop={step_result['stop_reason']} "
                    f"degraded={action_meta.get('degraded', False)}"
                )

            if args.interval_sec > 0:
                time.sleep(args.interval_sec)

        state = get_session_state(session_id=session_id)
        print("[mock-engine] session_state:")
        print(json.dumps(state, ensure_ascii=False, indent=2))
    finally:
        summary = end_session(session_id=session_id, reason=end_reason)
        print("[mock-engine] session_summary:")
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
