import argparse
import json
import time
from pathlib import Path


def write_normal_files(output_dir: Path, stamp: str):
    result_file = output_dir / f"result_{stamp}.json"
    prop_exec_file = output_dir / f"property_exec_info_{stamp}.json"

    result_data = {
        "test.prop.one": {"executed": 2, "fail": 0, "error": 0},
        "test.prop.two": {"executed": 1, "fail": 1, "error": 0},
    }
    result_file.write_text(json.dumps(result_data, indent=2), encoding="utf-8")
    prop_exec_file.write_text(
        json.dumps(
            {
                "startStepsCount": 1,
                "propName": "test.prop.one",
                "kind": "property",
                "state": "pass",
                "tb": "",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def write_crash_file(output_dir: Path, stamp: str):
    result_file = output_dir / f"result_{stamp}.json"
    partial_data = {
        "test.prop.one": {"executed": 1, "fail": 0, "error": 1},
    }
    result_file.write_text(json.dumps(partial_data, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-stamp", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--scenario", required=True, choices=["normal", "long", "fail", "crash"])
    parser.add_argument("--running-minutes", required=False, type=int, default=10)
    args = parser.parse_args()

    stamp = args.log_stamp
    parent = Path(args.output_dir).expanduser().resolve()
    output_dir = parent / f"res_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.scenario == "normal":
        time.sleep(2)
        write_normal_files(output_dir, stamp)
        raise SystemExit(0)
    if args.scenario == "long":
        time.sleep(300)
        raise SystemExit(0)
    if args.scenario == "fail":
        raise SystemExit(1)
    if args.scenario == "crash":
        time.sleep(1)
        write_crash_file(output_dir, stamp)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
