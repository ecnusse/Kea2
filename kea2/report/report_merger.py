import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from collections import defaultdict

from ..utils import getLogger, catchException

logger = getLogger(__name__)


class TestReportMerger:
    """
    Merge multiple test result directories into a single combined dataset
    Only processes result_*.json and coverage.log files for the simplified template
    """
    
    def __init__(self):
        self.merged_data = {}
        self.result_dirs = []
        self._package_name: Optional[str] = None
    
    @catchException("Error merging reports")
    def merge_reports(self, result_paths: List[Union[str, Path]], output_dir: Optional[Union[str, Path]] = None) -> Optional[Path]:
        """
        Merge multiple test result directories
        
        Args:
            result_paths: List of paths to test result directories (res_* directories)
            output_dir: Output directory for merged data (optional)
            
        Returns:
            Path to the merged data directory, or None if validation fails
        """
        # Convert paths and validate
        self.result_dirs = [Path(p).resolve() for p in result_paths]
        self._package_name = None

        package_name, fatal_error = self._determine_package_name()
        if fatal_error:
            logger.error("Aborting merge because package validation failed.")
            return None
        self._package_name = package_name
        
        # Setup output directory
        timestamp = datetime.now().strftime("%Y%m%d%H_%M%S")
        if output_dir is None:
            output_dir = Path.cwd() / f"merged_report_{timestamp}"
        else:
            output_dir = Path(output_dir).resolve() / f"merged_report_{timestamp}"
        
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Merging {len(self.result_dirs)} test result directories...")

        # Merge different types of data
        merged_property_stats, property_source_mapping = self._merge_property_results(output_dir)
        property_kinds = self._collect_property_kinds()
        source_summaries = self._collect_source_summaries()
        merged_coverage_data = self._merge_coverage_data()
        merged_crash_anr_data = self._merge_crash_dump_data(output_dir)

        # Calculate final statistics
        final_data = self._calculate_final_statistics(
            merged_property_stats,
            merged_coverage_data,
            merged_crash_anr_data,
            property_source_mapping,
            property_kinds,
        )
        
        # Add merge information to final data
        final_data['merge_info'] = {
            'merge_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'source_count': len(self.result_dirs),
            'source_directories': [str(Path(d).name) for d in self.result_dirs],
            'source_summaries': source_summaries,
            'package_name': self._package_name or ""
        }

        # Generate HTML report (now includes merge info)
        report_file = self._generate_html_report(final_data, output_dir)
        
        logger.debug(f"Reports generated successfully in: {output_dir}")
        return report_file

    def _collect_source_summaries(self) -> List[Dict]:
        """
        Collect summary statistics for each source result directory.
        """
        summaries = []

        for result_dir in self.result_dirs:
            summaries.append(self._build_source_summary(result_dir))

        return summaries

    def _build_source_summary(self, result_dir: Path) -> Dict:
        """
        Build summary statistics for a single result directory.
        """
        summary = {
            "dir_name": result_dir.name,
            "property_violations": 0,
            "invariant_violations": 0,
            "total_testing_time": "00:00:00",
            "executed_events": 0,
            "coverage_percent": "0.00%",
            "executed_properties": "0/0",
            "crash_count": 0,
            "anr_count": 0,
        }

        result_files = list(result_dir.glob("result_*.json"))
        if not result_files:
            return summary

        output_dirs = list(result_dir.glob("output_*"))
        output_dir = output_dirs[0] if output_dirs else None

        property_kinds = self._collect_property_kinds_for_dir(result_dir)

        try:
            with open(result_files[0], "r", encoding="utf-8") as f:
                property_stats = json.load(f)
        except Exception as exc:
            logger.warning(f"Failed to read {result_files[0]}: {exc}")
            return summary

        all_properties_count = 0
        executed_properties_count = 0

        for prop_name, stats in property_stats.items():
            fail_count = stats.get("fail", 0)
            error_count = stats.get("error", 0)
            total_executions = stats.get("executed", 0)
            kind = property_kinds.get(prop_name, "unknown")
            if kind not in {"property", "invariant"}:
                kind = "unknown"

            if kind != "invariant":
                all_properties_count += 1
                if total_executions > 0:
                    executed_properties_count += 1
                if fail_count > 0 or error_count > 0:
                    summary["property_violations"] += 1
            elif fail_count > 0 or error_count > 0:
                summary["invariant_violations"] += 1

        summary["executed_properties"] = f"{executed_properties_count}/{all_properties_count}"

        if output_dir:
            steps_log = output_dir / "steps.log"
            if steps_log.exists():
                executed_events, total_time = self._extract_steps_log_summary(steps_log)
                summary["executed_events"] = executed_events
                summary["total_testing_time"] = total_time

            coverage_file = output_dir / "coverage.log"
            if coverage_file.exists():
                coverage_percent = self._extract_coverage_percent(coverage_file)
                summary["coverage_percent"] = f"{coverage_percent:.2f}%"

            crash_dump_file = output_dir / "crash-dump.log"
            if crash_dump_file.exists():
                parsed_events = self._parse_crash_dump_file(crash_dump_file)
                if parsed_events:
                    crash_events, anr_events = parsed_events
                    summary["crash_count"] = len(crash_events)
                    summary["anr_count"] = len(anr_events)

        return summary

    def _collect_property_kinds_for_dir(self, result_dir: Path) -> Dict[str, str]:
        """
        Collect property kind metadata from a single result directory.
        """
        property_kinds: Dict[str, str] = {}

        result_files = list(result_dir.glob("result_*.json"))
        if not result_files:
            return property_kinds

        try:
            with open(result_files[0], "r", encoding="utf-8") as f:
                result_data = json.load(f)

            for prop_name, stats in result_data.items():
                kind = stats.get("kind", "")
                if not prop_name or not isinstance(kind, str) or not kind:
                    continue

                normalized_kind = kind.strip().lower()
                if not normalized_kind:
                    continue

                property_kinds.setdefault(prop_name, normalized_kind)
        except Exception as exc:
            logger.warning(f"Failed to parse {result_files[0]}: {exc}")

        return property_kinds

    def _extract_steps_log_summary(self, steps_log: Path) -> Tuple[int, str]:
        """
        Extract executed events count and total testing time from steps.log.
        """
        executed_events = 0
        first_step_time = None
        last_step_time = None

        with open(steps_log, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    step_data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                step_type = step_data.get("Type", "")
                if step_type in {"Monkey", "Fuzz"}:
                    executed_events += 1

                step_time = step_data.get("Time")
                if step_time:
                    if first_step_time is None:
                        first_step_time = step_time
                    last_step_time = step_time

        total_testing_time = "00:00:00"
        if first_step_time and last_step_time:
            def _get_datetime(raw_datetime: str) -> datetime:
                return datetime.strptime(raw_datetime, r"%Y-%m-%d %H:%M:%S.%f")

            time_delta = _get_datetime(last_step_time) - _get_datetime(first_step_time)
            total_seconds = int(time_delta.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            total_testing_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        return executed_events, total_testing_time

    def _extract_coverage_percent(self, coverage_file: Path) -> float:
        """
        Extract final coverage percent from coverage.log.
        """
        last_coverage = None
        with open(coverage_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_coverage = json.loads(line)
        if last_coverage and "coverage" in last_coverage:
            return round(float(last_coverage.get("coverage", 0)), 2)
        return 0.0

    def _collect_property_kinds(self) -> Dict[str, str]:
        """
        Collect property kind metadata from result_*.json files across result directories.

        Returns:
            Dict[str, str]: Mapping of property name to kind (property/invariant)
        """
        property_kinds: Dict[str, str] = {}

        for result_dir in self.result_dirs:
            result_files = list(result_dir.glob("result_*.json"))
            if not result_files:
                continue

            try:
                with open(result_files[0], "r", encoding="utf-8") as f:
                    result_data = json.load(f)

                for prop_name, stats in result_data.items():
                    kind = stats.get("kind", "")
                    if not prop_name or not isinstance(kind, str) or not kind:
                        continue

                    normalized_kind = kind.strip().lower()
                    if not normalized_kind:
                        continue

                    existing = property_kinds.get(prop_name)
                    if existing and existing != normalized_kind:
                        logger.debug(
                            "Property kind conflict for %s: %s vs %s",
                            prop_name,
                            existing,
                            normalized_kind,
                        )
                        continue

                    property_kinds.setdefault(prop_name, normalized_kind)
            except Exception as exc:
                logger.warning(f"Failed to parse {result_files[0]}: {exc}")
                continue

        return property_kinds

    def _determine_package_name(self) -> Tuple[Optional[str], bool]:
        """
        Ensure all reports belong to the same application and return the shared package name.

        Returns:
            tuple: (package_name, fatal_error)
                package_name: shared package name if determined, otherwise None
                fatal_error: True if validation should stop the merge
        """
        if not self.result_dirs:
            logger.error("No result directories provided for merge.")
            return None, True

        known_package: Optional[str] = None

        for result_dir in self.result_dirs:
            package_name, fatal_error = self._extract_package_name(result_dir)
            if fatal_error:
                return None, True
            if package_name is None:
                continue

            if known_package is None:
                known_package = package_name
            elif package_name != known_package:
                logger.error(
                    f"Cannot merge reports generated for different applications: "
                    f"{result_dir.name} uses package '{package_name}' while others use '{known_package}'."
                )
                return None, True

        if known_package:
            logger.debug(f"Validated application package for merge: {known_package}")
        else:
            logger.warning("No package information found in provided report directories. Proceeding without package validation.")
        return known_package, False

    def _extract_package_name(self, result_dir: Path) -> Tuple[Optional[str], bool]:
        """
        Extract the application package name from a report directory.
        """
        config_path = result_dir / "bug_report_config.json"
        if not config_path.exists():
            logger.warning(f"Skipping package validation for {result_dir}: bug_report_config.json not found.")
            return None, False

        try:
            with open(config_path, "r", encoding="utf-8") as config_file:
                config_data = json.load(config_file)
        except Exception as exc:
            logger.error(f"Failed to load bug_report_config.json from {result_dir}: {exc}")
            return None, True
        package_names = config_data.get("packageNames")
        if isinstance(package_names, str):
            package_name = package_names.strip()
            if not package_name:
                logger.error(f"Package name is empty in bug_report_config.json for {result_dir}")
                return None, True
            return package_name, False

        if isinstance(package_names, list):
            valid_names = [pkg.strip() for pkg in package_names if pkg and pkg.strip()]
            if not valid_names:
                logger.error(f"No valid packageNames found in bug_report_config.json for {result_dir}")
                return None, True
            if len(valid_names) > 1:
                logger.error(f"Multiple packageNames found in {config_path}, only single package is supported.")
                return None, True
            return valid_names[0], False

        logger.error(f"packageNames format is invalid in {config_path}")
        return None, True
    
    def _merge_property_results(self, output_dir: Path = None) -> Tuple[Dict[str, Dict], Dict[str, List[Dict]]]:
        """
        Merge property test results from all directories

        Args:
            output_dir: The output directory where the merged report will be saved (for calculating relative paths)

        Returns:
            Tuple of (merged_property_results, property_source_mapping)
            - merged_property_results: Merged property execution results
            - property_source_mapping: Maps property names to list of source directory info with fail/error
              Each entry contains: {'dir_name': str, 'report_path': str}
        """
        merged_results = defaultdict(lambda: {
            "precond_satisfied": 0,
            "executed": 0,
            "fail": 0,
            "error": 0
        })

        # Track which directories have fail/error for each property
        property_source_mapping = defaultdict(list)

        for result_dir in self.result_dirs:
            result_files = list(result_dir.glob("result_*.json"))
            html_files = list(result_dir.glob("*.html"))
            if not result_files:
                logger.warning(f"No result file found in {result_dir}")
                continue
            if not html_files:
                logger.warning(f"No html file found in {result_dir}")
                continue

            result_file = result_files[0]  # Take the first (should be only one)
            html_file = html_files[0]
            dir_name = result_dir.name  # Get the directory name (e.g., res_2025072011_5048015228)

            # Find the HTML report file in the result directory
            html_report_path = None
            
            # Calculate relative path from output_dir to the HTML file
            try:
                html_report_path = os.path.relpath(html_file.resolve(), output_dir.resolve())
            except ValueError:
                # If on different drives (Windows), use absolute path as fallback
                html_report_path = str(html_file.resolve())

            with open(result_file, 'r', encoding='utf-8') as f:
                test_results = json.load(f)

            # Merge results for each property
            for prop_name, prop_result in test_results.items():
                for key in ["precond_satisfied", "executed", "fail", "error"]:
                    merged_results[prop_name][key] += prop_result.get(key, 0)

                # Track source directories for properties with fail/error
                if prop_result.get('fail', 0) > 0 or prop_result.get('error', 0) > 0:
                    # Check if this directory is already in the mapping
                    existing_dirs = [item['dir_name'] for item in property_source_mapping[prop_name]]
                    if dir_name not in existing_dirs:
                        property_source_mapping[prop_name].append({
                            'dir_name': dir_name,
                            'report_path': html_report_path
                        })

            logger.debug(f"Merged results from: {result_file}")

        return dict(merged_results), dict(property_source_mapping)
    
    def _merge_coverage_data(self) -> Dict:
        """
        Merge coverage data from all directories
        
        Returns:
            Final merged coverage information
        """
        all_activities = set()
        tested_activities = set()
        activity_counts = defaultdict(int)
        total_steps = 0
        
        for result_dir in self.result_dirs:
            # Find coverage log file
            output_dirs = list(result_dir.glob("output_*"))
            if not output_dirs:
                logger.warning(f"No output directory found in {result_dir}")
                continue
                
            coverage_file = output_dirs[0] / "coverage.log"
            if not coverage_file.exists():
                logger.warning(f"No coverage.log found in {output_dirs[0]}")
                continue

            # Read the last line of coverage.log to get final state
            last_coverage = None
            with open(coverage_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        last_coverage = json.loads(line)
            
            if last_coverage:
                # Collect all activities
                all_activities.update(last_coverage.get("totalActivities", []))
                tested_activities.update(last_coverage.get("testedActivities", []))
                
                # Update activity counts (take maximum)
                for activity, count in last_coverage.get("activityCountHistory", {}).items():
                    activity_counts[activity] += count
                
                # Add steps count
                total_steps += last_coverage.get("stepsCount", 0)
            
            logger.debug(f"Merged coverage data from: {coverage_file}")
        
        # Calculate final coverage percentage (rounded to 2 decimal places)
        coverage_percent = round((len(tested_activities) / len(all_activities) * 100), 2) if all_activities else 0.00
        
        return {
            "coverage_percent": coverage_percent,
            "total_activities": list(all_activities),
            "tested_activities": list(tested_activities),
            "total_activities_count": len(all_activities),
            "tested_activities_count": len(tested_activities),
            "activity_count_history": dict(activity_counts),
            "total_steps": total_steps
        }

    def _merge_crash_dump_data(self, output_dir: Path = None) -> Dict:
        """
        Merge crash and ANR data from all directories

        Returns:
            Dict containing merged crash and ANR events
        """
        all_crash_events = []
        all_anr_events = []

        for result_dir in self.result_dirs:
            dir_name = result_dir.name

            # Locate corresponding HTML report for hyperlinking
            html_report_path = None
            html_files = list(result_dir.glob("*.html"))
            if not html_files:
                continue
            html_file = html_files[0]
            try:
                html_report_path = os.path.relpath(html_file.resolve(), output_dir.resolve())
            except ValueError:
                html_report_path = str(html_file.resolve())

            # Find crash dump log file
            output_dirs = list(result_dir.glob("output_*"))
            if not output_dirs:
                continue

            crash_dump_file = output_dirs[0] / "crash-dump.log"
            if not crash_dump_file.exists():
                logger.debug(f"No crash-dump.log found in {output_dirs[0]}")
                continue

            try:
                # Parse crash and ANR events from this file
                crash_events, anr_events = self._parse_crash_dump_file(crash_dump_file)

                for crash in crash_events:
                    crash["source_directory"] = dir_name
                    crash["report_path"] = html_report_path

                for anr in anr_events:
                    anr["source_directory"] = dir_name
                    anr["report_path"] = html_report_path

                all_crash_events.extend(crash_events)
                all_anr_events.extend(anr_events)

                logger.debug(f"Merged {len(crash_events)} crash events and {len(anr_events)} ANR events from: {crash_dump_file}")

            except Exception as e:
                logger.error(f"Error reading crash dump file {crash_dump_file}: {e}")
                continue

        # Deduplicate events based on content and timestamp
        unique_crash_events = self._deduplicate_crash_events(all_crash_events)
        unique_anr_events = self._deduplicate_anr_events(all_anr_events)

        logger.debug(f"Total unique crash events: {len(unique_crash_events)}, ANR events: {len(unique_anr_events)}")

        return {
            "crash_events": unique_crash_events,
            "anr_events": unique_anr_events,
            "total_crash_count": len(unique_crash_events),
            "total_anr_count": len(unique_anr_events)
        }
    
    @catchException("Error parsing crash-dump.log")
    def _parse_crash_dump_file(self, crash_dump_file: Path) -> Tuple[List[Dict], List[Dict]]:
        """
        Parse crash and ANR events from crash-dump.log file

        Args:
            crash_dump_file: Path to crash-dump.log file

        Returns:
            tuple: (crash_events, anr_events) - Lists of crash and ANR event dictionaries
        """
        crash_events = []
        anr_events = []

        with open(crash_dump_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse crash events
        crash_events = self._parse_crash_events(content)
        # Parse ANR events
        anr_events = self._parse_anr_events(content)
        
        return crash_events, anr_events

    def _parse_crash_events(self, content: str) -> List[Dict]:
        """
        Parse crash events from crash-dump.log content

        Args:
            content: Content of crash-dump.log file

        Returns:
            List[Dict]: List of crash event dictionaries
        """
        crash_events = []

        # Pattern to match crash blocks
        crash_pattern = r'(\d{14})\ncrash:\n(.*?)\n// crash end'

        for match in re.finditer(crash_pattern, content, re.DOTALL):
            timestamp_str = match.group(1)
            crash_content = match.group(2)

            # Parse timestamp (format: YYYYMMDDHHMMSS)
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                formatted_time = timestamp_str

            # Extract crash information
            crash_info = self._extract_crash_info(crash_content)

            crash_event = {
                "time": formatted_time,
                "exception_type": crash_info.get("exception_type", "Unknown"),
                "process": crash_info.get("process", "Unknown"),
                "stack_trace": crash_info.get("stack_trace", "")
            }

            crash_events.append(crash_event)

        return crash_events

    def _parse_anr_events(self, content: str) -> List[Dict]:
        """
        Parse ANR events from crash-dump.log content

        Args:
            content: Content of crash-dump.log file

        Returns:
            List[Dict]: List of ANR event dictionaries
        """
        anr_events = []

        # Pattern to match ANR blocks
        anr_pattern = r'(\d{14})\nanr:\n(.*?)\nanr end'

        for match in re.finditer(anr_pattern, content, re.DOTALL):
            timestamp_str = match.group(1)
            anr_content = match.group(2)

            # Parse timestamp (format: YYYYMMDDHHMMSS)
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                formatted_time = timestamp_str

            # Extract ANR information
            anr_info = self._extract_anr_info(anr_content)

            anr_event = {
                "time": formatted_time,
                "reason": anr_info.get("reason", "Unknown"),
                "process": anr_info.get("process", "Unknown"),
                "trace": anr_info.get("trace", "")
            }

            anr_events.append(anr_event)

        return anr_events

    def _extract_crash_info(self, crash_content: str) -> Dict:
        """
        Extract crash information from crash content

        Args:
            crash_content: Content of a single crash block

        Returns:
            Dict: Extracted crash information
        """
        crash_info = {
            "exception_type": "Unknown",
            "process": "Unknown",
            "stack_trace": ""
        }

        lines = crash_content.strip().split('\n')

        for line in lines:
            line = line.strip()

            # Extract PID from CRASH line
            if line.startswith("// CRASH:"):
                # Pattern: // CRASH: process_name (pid xxxx) (dump time: ...)
                pid_match = re.search(r'\(pid\s+(\d+)\)', line)
                if pid_match:
                    crash_info["process"] = pid_match.group(1)

            # Extract exception type from Long Msg line
            elif line.startswith("// Long Msg:"):
                # Pattern: // Long Msg: ExceptionType: message
                exception_match = re.search(r'// Long Msg:\s+([^:]+)', line)
                if exception_match:
                    crash_info["exception_type"] = exception_match.group(1).strip()

        # Extract full stack trace (all lines starting with //)
        stack_lines = []
        for line in lines:
            if line.startswith("//"):
                # Remove the "// " prefix for cleaner display
                clean_line = line[3:] if line.startswith("// ") else line[2:]
                stack_lines.append(clean_line)

        crash_info["stack_trace"] = '\n'.join(stack_lines)

        return crash_info

    def _extract_anr_info(self, anr_content: str) -> Dict:
        """
        Extract ANR information from ANR content

        Args:
            anr_content: Content of a single ANR block

        Returns:
            Dict: Extracted ANR information
        """
        anr_info = {
            "reason": "Unknown",
            "process": "Unknown",
            "trace": ""
        }

        lines = anr_content.strip().split('\n')

        for line in lines:
            line = line.strip()

            # Extract PID from ANR line
            if line.startswith("// ANR:"):
                # Pattern: // ANR: process_name (pid xxxx) (dump time: ...)
                pid_match = re.search(r'\(pid\s+(\d+)\)', line)
                if pid_match:
                    anr_info["process"] = pid_match.group(1)

            # Extract reason from Reason line
            elif line.startswith("Reason:"):
                # Pattern: Reason: Input dispatching timed out (...)
                reason_match = re.search(r'Reason:\s+(.+)', line)
                if reason_match:
                    full_reason = reason_match.group(1).strip()
                    # Simplify the reason by extracting the main part before parentheses
                    simplified_reason = self._simplify_anr_reason(full_reason)
                    anr_info["reason"] = simplified_reason

        # Store the full ANR trace content
        anr_info["trace"] = anr_content

        return anr_info

    def _simplify_anr_reason(self, full_reason: str) -> str:
        """
        Simplify ANR reason by extracting the main part

        Args:
            full_reason: Full ANR reason string

        Returns:
            str: Simplified ANR reason
        """
        # Common ANR reason patterns to simplify
        simplification_patterns = [
            # Input dispatching timed out (details...) -> Input dispatching timed out
            (r'^(Input dispatching timed out)\s*\(.*\).*$', r'\1'),
            # Broadcast of Intent (details...) -> Broadcast timeout
            (r'^Broadcast of Intent.*$', 'Broadcast timeout'),
            # Service timeout -> Service timeout
            (r'^Service.*timeout.*$', 'Service timeout'),
            # ContentProvider timeout -> ContentProvider timeout
            (r'^ContentProvider.*timeout.*$', 'ContentProvider timeout'),
        ]

        # Apply simplification patterns
        for pattern, replacement in simplification_patterns:
            match = re.match(pattern, full_reason, re.IGNORECASE)
            if match:
                if callable(replacement):
                    return replacement(match)
                elif '\\1' in replacement:
                    return re.sub(pattern, replacement, full_reason, flags=re.IGNORECASE)
                else:
                    return replacement

        # If no pattern matches, try to extract the part before the first parenthesis
        paren_match = re.match(r'^([^(]+)', full_reason)
        if paren_match:
            simplified = paren_match.group(1).strip()
            # Remove trailing punctuation
            simplified = re.sub(r'[.,;:]+$', '', simplified)
            return simplified

        # If all else fails, return the original but truncated
        return full_reason[:50] + "..." if len(full_reason) > 50 else full_reason

    def _deduplicate_crash_events(self, crash_events: List[Dict]) -> List[Dict]:
        """
        Deduplicate crash events based on exception type and stack trace

        Args:
            crash_events: List of crash events

        Returns:
            List[Dict]: Deduplicated crash events
        """
        seen_crashes = set()
        unique_crashes = []

        for crash in crash_events:
            # Create a hash key based on exception type and first few lines of stack trace
            exception_type = crash.get("exception_type", "")
            stack_trace = crash.get("stack_trace", "")

            # Use first 3 lines of stack trace for deduplication
            stack_lines = stack_trace.split('\n')[:3]
            crash_key = (
                exception_type,
                '\n'.join(stack_lines),
                crash.get("source_directory", "")
            )

            if crash_key not in seen_crashes:
                seen_crashes.add(crash_key)
                unique_crashes.append(crash)

        return unique_crashes

    def _deduplicate_anr_events(self, anr_events: List[Dict]) -> List[Dict]:
        """
        Deduplicate ANR events based on reason and process

        Args:
            anr_events: List of ANR events

        Returns:
            List[Dict]: Deduplicated ANR events
        """
        seen_anrs = set()
        unique_anrs = []

        for anr in anr_events:
            # Create a hash key based on reason and process
            reason = anr.get("reason", "")
            process = anr.get("process", "")
            anr_key = (reason, process, anr.get("source_directory", ""))

            if anr_key not in seen_anrs:
                seen_anrs.add(anr_key)
                unique_anrs.append(anr)

        return unique_anrs

    def _calculate_final_statistics(
        self,
        property_stats: Dict,
        coverage_data: Dict,
        crash_anr_data: Dict = None,
        property_source_mapping: Dict = None,
        property_kinds: Dict[str, str] = None,
    ) -> Dict:
        """
        Calculate final statistics for template rendering

        Note: Total bugs count only includes property test failures/errors,
        not crashes or ANRs (which are tracked separately)

        Args:
            property_stats: Merged property statistics
            coverage_data: Merged coverage data
            crash_anr_data: Merged crash and ANR data (optional)
            property_source_mapping: Maps property names to source directories with fail/error (optional)

        Returns:
            Complete data for template rendering
        """
        # Calculate bug count from property failures (exclude invariants)
        property_bugs_found = 0
        invariant_violations_count = 0

        # Calculate property counts (exclude invariants from summary counts)
        all_properties_count = 0
        executed_properties_count = 0

        # Initialize crash/ANR data
        crash_events = []
        anr_events = []
        total_crash_count = 0
        total_anr_count = 0

        if crash_anr_data:
            crash_events = crash_anr_data.get('crash_events', [])
            anr_events = crash_anr_data.get('anr_events', [])
            total_crash_count = crash_anr_data.get('total_crash_count', 0)
            total_anr_count = crash_anr_data.get('total_anr_count', 0)

        # Prepare enhanced property statistics with derived metrics
        processed_property_stats = {}
        property_stats_summary = {
            "total_properties": 0,
            "total_precond_satisfied": 0,
            "total_executed": 0,
            "total_passes": 0,
            "total_fails": 0,
            "total_errors": 0,
            "total_not_executed": 0,
        }

        property_kind_summary = {
            "all": 0,
            "property": 0,
            "invariant": 0,
            "unknown": 0,
        }
        property_source_kind_summary = {
            "all": 0,
            "property": 0,
            "invariant": 0,
            "unknown": 0,
        }

        for prop_name, stats in property_stats.items():
            precond_satisfied = stats.get("precond_satisfied", 0)
            total_executions = stats.get("executed", 0)
            fail_count = stats.get("fail", 0)
            error_count = stats.get("error", 0)

            pass_count = max(total_executions - fail_count - error_count, 0)
            not_executed_count = max(precond_satisfied - total_executions, 0)
            kind = (property_kinds or {}).get(prop_name, "unknown")
            if kind not in {"property", "invariant"}:
                kind = "unknown"

            processed_property_stats[prop_name] = {
                **stats,
                "executed_total": total_executions,
                "pass_count": pass_count,
                "not_executed": not_executed_count,
                "kind": kind,
            }

            if kind != "invariant":
                all_properties_count += 1
                if total_executions > 0:
                    executed_properties_count += 1
                if fail_count > 0 or error_count > 0:
                    property_bugs_found += 1
            elif fail_count > 0 or error_count > 0:
                invariant_violations_count += 1

            property_stats_summary["total_properties"] += 1
            property_stats_summary["total_precond_satisfied"] += precond_satisfied
            property_stats_summary["total_executed"] += total_executions
            property_stats_summary["total_passes"] += pass_count
            property_stats_summary["total_fails"] += fail_count
            property_stats_summary["total_errors"] += error_count
            property_stats_summary["total_not_executed"] += not_executed_count

            property_kind_summary["all"] += 1
            property_kind_summary[kind] += 1

        if property_source_mapping:
            for prop_name in property_source_mapping.keys():
                kind = (property_kinds or {}).get(prop_name, "unknown")
                if kind not in {"property", "invariant"}:
                    kind = "unknown"
                property_source_kind_summary["all"] += 1
                property_source_kind_summary[kind] += 1

        # Calculate total bugs found (only property bugs, not including crashes/ANRs)
        total_bugs_found = property_bugs_found

        # Prepare final data
        final_data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'bugs_found': total_bugs_found,
            'invariant_violations_count': invariant_violations_count,
            'property_bugs_found': property_bugs_found,
            'all_properties_count': all_properties_count,
            'executed_properties_count': executed_properties_count,
            'property_stats': processed_property_stats,
            'property_stats_summary': property_stats_summary,
            'property_kind_summary': property_kind_summary,
            'property_source_kind_summary': property_source_kind_summary,
            'property_source_mapping': property_source_mapping or {},
            'crash_events': crash_events,
            'anr_events': anr_events,
            'total_crash_count': total_crash_count,
            'total_anr_count': total_anr_count,
            **coverage_data  # Include all coverage data
        }

        return final_data
    
    def get_merge_summary(self) -> Dict:
        """
        Get summary of the merge operation
        
        Returns:
            Dictionary containing merge summary information
        """
        if not self.result_dirs:
            return {}
        
        summary = {
            "merged_directories": len(self.result_dirs),
            "source_paths": [str(p) for p in self.result_dirs],
            "merge_timestamp": datetime.now().isoformat()
        }
        if self._package_name:
            summary["package_name"] = self._package_name
        return summary

    @catchException("Error generating HTML report")
    def _generate_html_report(self, data: Dict, output_dir: Path) -> Path:
        """
        Generate HTML report using the merged template

        Args:
            data: Final merged data
            output_dir: Output directory

        Returns:
            Path to the generated HTML report
        """
        from jinja2 import Environment, FileSystemLoader, PackageLoader, select_autoescape

        # Set up Jinja2 environment
        try:
            jinja_env = Environment(
                loader=PackageLoader("kea2.report", "templates"),
                autoescape=select_autoescape(['html', 'xml'])
            )
        except (ImportError, ValueError):
            # Fallback to file system loader
            current_dir = Path(__file__).parent
            templates_dir = current_dir / "templates"

            jinja_env = Environment(
                loader=FileSystemLoader(templates_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )

        # Render template
        template = jinja_env.get_template("merged_bug_report_template.html")
        html_content = template.render(**data)

        # Save HTML report
        report_file = output_dir / "merged_report.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.debug(f"HTML report generated: {report_file}")
        return report_file
