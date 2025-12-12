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
    
    for report_dir in report_dirs:
        report_dir = Path(report_dir).resolve()

        if not report_dir.exists():
            logger.error(f"Report directory does not exist: {str(report_dir)}, Skipped.")
            continue
        
        logger.debug(f"Generating test report from directory: {report_dir}")
        BugReportGenerator(report_dir).generate_report()


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


def cmd_mergefbm(args):
    """Merge all FBM files in the specified folder and its subfolders using sum mode"""
    from .fbm_parser import FBMMerger
    import glob
    import shutil
    
    try:
        # Validate input path
        input_path = Path(args.path).resolve()
        if not input_path.exists():
            logger.error(f"Input directory does not exist: {input_path}")
            return
        if not input_path.is_dir():
            logger.error(f"Input path is not a directory: {input_path}")
            return

        # Find all FBM files in the directory and its subdirectories
        fbm_files = glob.glob(str(input_path / "**" / "*.fbm"), recursive=True)
        
        if not fbm_files:
            logger.error(f"No FBM files found in {input_path} or its subdirectories")
            return
        
        logger.debug(f"Found {len(fbm_files)} FBM files to merge:")
        for fbm_file in fbm_files:
            logger.debug(f"  - {fbm_file}")
        
        # Set default output file if not provided
        if not args.output:
            output_file = input_path / "merged.fbm"
        else:
            output_file = Path(args.output).resolve()
        
        # Initialize merger
        merger = FBMMerger()
        
        # Handle different cases
        if len(fbm_files) == 1:
            # Only one file, just copy it to output
            shutil.copyfile(fbm_files[0], output_file)
            logger.info(f"Only one FBM file found, copied to {output_file}")
        else:
            # Merge files iteratively: start with the first file and merge with each subsequent file
            # Create a temporary file for the intermediate merged result
            temp_output = input_path / f".tmp_merged.fbm"
            
            # Start with the first file as the initial merged result
            shutil.copyfile(fbm_files[0], temp_output)
            
            # Iterate through the remaining files and merge them one by one
            for i in range(1, len(fbm_files)):
                current_file = fbm_files[i]
                next_temp = input_path / f".tmp_merged_{i}.fbm"
                
                logger.debug(f"Merging {temp_output} and {current_file} into {next_temp}")
                success = merger.merge(str(temp_output), str(current_file), str(next_temp), merge_mode='sum')
                
                if not success:
                    logger.error(f"Failed to merge {temp_output} and {current_file}")
                    # Clean up temporary files
                    for f in [temp_output, next_temp]:
                        if f.exists() and f.name.startswith(".tmp_"):
                            f.unlink()
                    return
                
                # Remove the previous temporary file and update to the new one
                temp_output.unlink()
                temp_output = next_temp
            
            # Move the final merged file to the output location
            if temp_output != output_file:
                temp_output.replace(output_file)
        
        print(f"✅ All FBM files merged successfully!", flush=True)
        print(f"📊 Merged FBM file: {output_file}", flush=True)
        print(f"📈 Merged {len(fbm_files)} FBM files", flush=True)
        
    except Exception as e:
        logger.error(f"Error during FBM merge operation: {e}")
        import traceback
        logger.debug(traceback.format_exc())


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
    ),
    dict(
        action=cmd_mergefbm,
        command="mergefbm",
        help="merge all FBM files in the specified folder and its subfolders using sum mode",
        flags=[
            dict(
                name=["path"],
                args=["-p", "--path"],
                type=str,
                required=True,
                help="Path to the folder containing FBM files to merge"
            ),
            dict(
                name=["output"],
                args=["-o", "--output"],
                type=str,
                required=False,
                help="Output file path for merged FBM file (optional, default: merged.fbm in the input folder)"
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
