# coding: utf-8
# cli.py

from __future__ import absolute_import, print_function
from datetime import datetime
import sys
from .utils import getProjectRoot, getLogger
from .kea_launcher import run
from .version_manager import check_config_compatibility, get_cur_version
import argparse

import os
from pathlib import Path


logger = getLogger(__name__)


def cmd_version(args):
    print(get_cur_version(), flush=True)


def cmd_init(args):
    cwd = Path(os.getcwd())
    configs_dir = cwd / "configs"
    if os.path.isdir(configs_dir):
        logger.warning("Kea2 project already initialized")
        return

    import shutil
    def copy_configs():
        src = Path(__file__).parent / "assets" / "fastbot_configs"
        dst = configs_dir
        shutil.copytree(src, dst)

    def copy_samples():
        src = Path(__file__).parent / "assets" / "quicktest.py"
        dst = cwd / "quicktest.py"
        shutil.copyfile(src, dst)
    
    def save_version():
        import json
        version_file = configs_dir / "version.json"
        with open(version_file, "w") as fp:
            json.dump({"version": get_cur_version(), "init date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, fp, indent=4)

    copy_configs()
    copy_samples()
    save_version()
    logger.info("Kea2 project initialized.")


def cmd_load_configs(args):
    pass


def cmd_report(args):
    from .report.bug_report_generator import BugReportGenerator
    report_dirs = args.path
    
    sync_data = args.sync
     
    for report_dir in report_dirs:
        report_dir = Path(report_dir).resolve()

        if not report_dir.exists():
            logger.error(f"Report directory does not exist: {str(report_dir)}, Skipped.")
            continue
        
        logger.debug(f"Generating test report from directory: {report_dir}")
        BugReportGenerator(report_dir, sync_data).generate_report()


def cmd_merge(args):
    """Merge multiple test report directories and generate a combined report"""
    from .report.report_merger import TestReportMerger

    try:
        # Validate input paths
        if not args.paths or len(args.paths) < 2:
            logger.error("At least 2 test report paths are required for merging. Use -p to specify paths.")
            return

        # Validate that all paths exist
        for path in args.paths:
            path_obj = Path(path)
            if not path_obj.exists():
                raise FileNotFoundError(f"{path_obj}")
            if not path_obj.is_dir():
                raise NotADirectoryError(f"{path_obj}")

        logger.debug(f"Merging {len(args.paths)} test report directories...")

        # Initialize merger
        merger = TestReportMerger()

        # Merge test reports
        merged_report = merger.merge_reports(args.paths, args.output)

        if merged_report is not None:
            print(f"✅ Test reports merged successfully!", flush=True)
            print(f"📊 Merged report: {merged_report}", flush=True)
            # Get merge summary
            merge_summary = merger.get_merge_summary()
            print(f"📈 Merged {merge_summary.get('merged_directories', 0)} directories", flush=True)

    except Exception as e:
        logger.error(f"Error during merge operation: {e}")      


def cmd_run(args):
    base_dir = getProjectRoot()
    if base_dir is None:
        logger.error("kea2 project not initialized. Use `kea2 init`.")
        return

    check_config_compatibility()

    run(args)


_commands = [
    dict(action=cmd_version, command="version", help="show version"),
    dict(
        action=cmd_init,
        command="init",
        help="init the Kea2 project in current directory",
    ),
    dict(
        action=cmd_report,
        command="report",
        help="generate test report from existing test results",
        flags=[
            dict(
                name=["report_dir"],
                args=["-p", "--path"],
                type=str,
                nargs="+",
                required=True,
                help="Root directory path of the test results to generate report from"
            ),
            dict(
                name=["sync_data"],
                args=["-s", "--sync"],
                action="store_true",
                help="Sync data from device before generating report"
            )
        ]
    ),
    dict(
        action=cmd_merge,
        command="merge",
        help="merge multiple test report directories and generate a combined report",
        flags=[
            dict(
                name=["paths"],
                args=["-p", "--paths"],
                type=str,
                nargs='+',
                required=True,
                help="Paths to test report directories (res_* directories) to merge"
            ),
            dict(
                name=["output"],
                args=["-o", "--output"],
                type=str,
                required=False,
                help="Output directory for merged report (optional)"
            )
        ]
    )
]


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-d", "--debug", action="store_true",
                        help="show detail log")

    subparser = parser.add_subparsers(dest='subparser')

    actions = {}
    for c in _commands:
        cmd_name = c['command']
        actions[cmd_name] = c['action']
        sp = subparser.add_parser(
            cmd_name,
            help=c.get('help'),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        for f in c.get('flags', []):
            args = f.get('args')
            if not args:
                args = ['-'*min(2, len(n)) + n for n in f['name']]
            kwargs = f.copy()
            kwargs.pop('name', None)
            kwargs.pop('args', None)
            sp.add_argument(*args, **kwargs)

    from .kea_launcher import _set_runner_parser
    _set_runner_parser(subparser)
    actions["run"] = cmd_run
    if sys.argv[1:] == ["run"]:
        sys.argv.append("-h")
    args = parser.parse_args()

    import logging
    from .utils import LoggingLevel
    LoggingLevel.set_level(logging.INFO)
    if args.debug:
        LoggingLevel.set_level(logging.DEBUG)
        logger.debug("args: %s", args)

    if args.subparser:
        actions[args.subparser](args)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
