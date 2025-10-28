import json
import re
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, TypedDict, List, Deque, NewType, Union, Optional
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFont
from jinja2 import Environment, FileSystemLoader, select_autoescape, PackageLoader
from kea2.utils import getLogger, catchException

logger = getLogger(__name__)


class StepData(TypedDict):
    # The type of the action (Monkey / Script / Script Info)
    Type: str
    # The steps of monkey event when the action happened
    # ps: since we insert script actions into monkey actions. Total actions count >= Monkey actions count
    MonkeyStepsCount: int
    # The time stamp of the action
    Time: str
    # The execution info of the action
    Info: Dict
    # The screenshot of the action
    Screenshot: str


class CovData(TypedDict):
    stepsCount: int
    coverage: float
    totalActivitiesCount: int
    testedActivitiesCount: int
    totalActivities: List[str]
    testedActivities: List[str]
    activityCountHistory: Dict[str, int]


class ReportData(TypedDict):
    timestamp: str
    bugs_found: int
    executed_events: int
    total_testing_time: float
    coverage: float
    total_activities_count: int
    tested_activities_count: int
    total_activities: List
    tested_activities: List
    all_properties_count: int
    executed_properties_count: int
    property_violations: List[Dict]
    property_stats: List
    property_error_details: Dict[str, List[Dict]]  # Support multiple errors per property
    screenshot_info: Dict
    coverage_trend: List
    property_execution_trend: List  # Track executed properties count over steps
    activity_count_history: Dict[str, int]  # Activity traversal count from final coverage data
    crash_events: List[Dict]  # Crash events from crash-dump.log
    anr_events: List[Dict]  # ANR events from crash-dump.log


class PropertyExecResult(TypedDict):
    precond_satisfied: int
    executed: int
    fail: int
    error: int


@dataclass
class PropertyExecInfo:
    """Class representing property execution information from property_exec_info file"""
    prop_name: str
    state: str  # start, pass, fail, error
    traceback: str
    start_steps_count: int
    occurrence_count: int = 1
    short_description: str = ""
    start_steps_count_list: List[int] = None
    
    def __post_init__(self):
        if self.start_steps_count_list is None:
            self.start_steps_count_list = [self.start_steps_count]
        if not self.short_description and self.traceback:
            self.short_description = self._extract_error_summary(self.traceback)
    
    def _extract_error_summary(self, traceback: str) -> str:
        """Extract a short error summary from the full traceback"""
        try:
            lines = traceback.strip().split('\n')
            for line in reversed(lines):
                line = line.strip()
                if line and not line.startswith('  '):
                    return line
            return "Unknown error"
        except Exception:
            return "Error parsing traceback"
    
    def get_error_hash(self) -> int:
        """Generate hash key for error deduplication"""
        return hash((self.state, self.traceback))
    
    def is_error_state(self) -> bool:
        """Check if this is an error or fail state"""
        return self.state in ["fail", "error"]
    
    def add_occurrence(self, start_steps_count: int):
        """Add another occurrence of the same error"""
        self.occurrence_count += 1
        self.start_steps_count_list.append(start_steps_count)


PropertyName = NewType("PropertyName", str)
TestResult = NewType("TestResult", Dict[PropertyName, PropertyExecResult])


@dataclass
class DataPath:
    output_dir: Path
    steps_log: Path
    result_json: Path
    coverage_log: Path
    screenshots_dir: Path
    property_exec_info: Path
    crash_dump_log: Path


class BugReportGenerator:
    """
    Generate HTML format bug reports
    """

    _cov_trend: Deque[CovData] = None
    _test_result: TestResult = None
    _take_screenshots: bool = None
    _data_path: DataPath = None

    @property
    def cov_trend(self):
        if self._cov_trend is not None:
            return self._cov_trend

        # Parse coverage data
        if not self.data_path.coverage_log.exists():
            logger.error(f"{self.data_path.coverage_log} not exists")

        cov_trend = list()

        with open(self.data_path.coverage_log, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                coverage_data = json.loads(line)
                cov_trend.append(coverage_data)
        self._cov_trend = cov_trend
        return self._cov_trend

    @property
    def take_screenshots(self) -> bool:
        """Whether the `--take-screenshots` enabled. Should we report the screenshots?

        Returns:
            bool: Whether the `--take-screenshots` enabled.
        """
        if self._take_screenshots is None:
            self._take_screenshots = self.data_path.screenshots_dir.exists()
        return self._take_screenshots

    @property
    def test_result(self) -> TestResult:
        if self._test_result is not None:
            return self._test_result

        if not self.data_path.result_json.exists():
            logger.error(f"{self.data_path.result_json} not found")
        with open(self.data_path.result_json, "r", encoding="utf-8") as f:
            self._test_result: TestResult = json.load(f)

        return self._test_result

    def __init__(self, result_dir=None):
        """
        Initialize the bug report generator

        Args:
            result_dir: Directory path containing test results
        """
        if result_dir is not None:
            self._setup_paths(result_dir)

        self.executor = ThreadPoolExecutor(max_workers=128)

        # Set up Jinja2 environment
        # First try to load templates from the package
        try:
            self.jinja_env = Environment(
                loader=PackageLoader("kea2", "templates"),
                autoescape=select_autoescape(['html', 'xml'])
            )
        except (ImportError, ValueError):
            # If unable to load from package, load from current directory's templates folder
            current_dir = Path(__file__).parent
            templates_dir = current_dir / "templates"

            # Ensure template directory exists
            if not templates_dir.exists():
                templates_dir.mkdir(parents=True, exist_ok=True)

            self.jinja_env = Environment(
                loader=FileSystemLoader(templates_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )

    def _setup_paths(self, result_dir):
        """
        Setup paths for a given result directory

        Args:
            result_dir: Directory path containing test results
        """
        self.result_dir = Path(result_dir)
        
        if (self.result_dir / "bug_report_config.json").exists():
            with open(self.result_dir / "bug_report_config.json", "r", encoding="utf-8") as fp:
                config = json.load(fp)
                self.log_stamp = config.get("log_stamp", "")
                
        if self.log_stamp:
            output_dir = self.result_dir / f"output_{self.log_stamp}"
            property_exec_info_file = self.result_dir / f"property_exec_info_{self.log_stamp}.json"
            result_file = self.result_dir / f"result_{self.log_stamp}.json"
        else:
            output_dirs = [_ for _ in self.result_dir.glob("output_*") if _.is_dir()]
            property_exec_info_files = [_ for _ in self.result_dir.glob("property_exec_info_*.json") if _.is_file()]
            result_files = [_ for _ in self.result_dir.glob("result_*.json") if _.is_file()]
            if all([output_dirs, property_exec_info_files, result_files]):
                output_dir = output_dirs[0]
                property_exec_info_file = property_exec_info_files[0]
                result_file = result_files[0]
        
        if not all([output_dir, property_exec_info_file, result_file]):
            raise RuntimeError("Cannot determine output directory or execution info files from result directory.")

        self.data_path: DataPath = DataPath(
            output_dir=output_dir,
            steps_log=output_dir / "steps.log",
            coverage_log=output_dir / "coverage.log",
            screenshots_dir=output_dir / "screenshots",
            crash_dump_log=output_dir / "crash-dump.log",
            property_exec_info=property_exec_info_file,
            result_json=result_file,
        )

        self.screenshots = deque()

    def generate_report(self, result_dir_path=None):
        """
        Generate bug report and save to result directory

        Args:
            result_dir_path: Directory path containing test results (optional)
                           If not provided, uses the path from initialization
        """
        try:
            # Setup paths if result_dir_path is provided
            if result_dir_path is not None:
                self._setup_paths(result_dir_path)

            # Check if paths are properly set up
            if not hasattr(self, 'result_dir') or self.result_dir is None:
                raise ValueError(
                    "No result directory specified. Please provide result_dir_path or initialize with a directory.")

            logger.debug("Starting bug report generation")

            # Collect test data
            test_data: ReportData = self._collect_test_data()

            # Generate HTML report
            html_content = self._generate_html_report(test_data)

            # Save report
            report_path = self.result_dir / "bug_report.html"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.debug(f"Bug report saved to: {report_path}")
            return str(report_path)

        except Exception as e:
            logger.error(f"Error generating bug report: {e}")
        finally:
            self.executor.shutdown()

    def _collect_test_data(self) -> ReportData:
        """
        Collect test data, including results, coverage, etc.
        """
        data: ReportData = {
            "timestamp": self.log_stamp,
            "bugs_found": 0,
            "executed_events": 0,
            "total_testing_time": 0,
            "coverage": 0,
            "total_activities": [],
            "tested_activities": [],
            "all_properties_count": 0,
            "executed_properties_count": 0,
            "property_violations": [],
            "property_stats": [],
            "property_error_details": {},
            "screenshot_info": {},
            "coverage_trend": [],
            "property_execution_trend": [],
            "activity_count_history": {},
            "crash_events": [],
            "anr_events": []
        }

        # Parse steps.log file to get test step numbers and screenshot mappings
        property_violations = {}  # Store multiple violation records for each property
        executed_properties_by_step = {}  # Track executed properties at each step: {step_count: set()}
        executed_properties = set()  # Track unique executed properties

        if not self.data_path.steps_log.exists():
            logger.error(f"{self.data_path.steps_log} not exists")
            return

        current_property = None
        current_test = {}
        step_index = 0
        monkey_events_count = 0  # Track monkey events separately

        with open(self.data_path.steps_log, "r", encoding="utf-8") as f:
            # Track current test state

            for step_index, line in enumerate(f, start=1):
                step_data = self._parse_step_data(line)

                if not step_data:
                    continue

                step_type = step_data.get("Type", "")
                screenshot = step_data.get("Screenshot", "")
                info = step_data.get("Info", {})

                # Count Monkey events separately
                if step_type == "Monkey":
                    monkey_events_count += 1

                # If screenshots are enabled, mark the screenshot
                if self.take_screenshots and step_data["Screenshot"]:
                    self.executor.submit(self._mark_screenshot, step_data)

                # Collect detailed information for each screenshot
                if screenshot and screenshot not in data["screenshot_info"]:
                    self._add_screenshot_info(step_data, step_index, data)

                # Process ScriptInfo for property violations and execution tracking
                if step_type == "ScriptInfo":
                    try:
                        property_name = info.get("propName", "")
                        state = info.get("state", "")
                        
                        # Track executed properties (properties that have been started)
                        if property_name and state == "start":
                            executed_properties.add(property_name)
                            # Record the monkey steps count for this property execution
                            executed_properties_by_step[monkey_events_count] = executed_properties.copy()
                        
                        current_property, current_test = self._process_script_info(
                            property_name, state, step_index, screenshot,
                            current_property, current_test, property_violations
                        )
                    except Exception as e:
                        logger.error(f"Error processing ScriptInfo step {step_index}: {e}")

                # Store first and last step for time calculation
                if step_index == 1:
                    first_step_time = step_data["Time"]
                last_step_time = step_data["Time"]

            # Set the monkey events count correctly
            data["executed_events"] = monkey_events_count

            # Calculate test time
            if first_step_time and last_step_time:
                def _get_datetime(raw_datetime) -> datetime:
                    return datetime.strptime(raw_datetime, r"%Y-%m-%d %H:%M:%S.%f")

                test_time = _get_datetime(last_step_time) - _get_datetime(first_step_time)

                total_seconds = int(test_time.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                data["total_testing_time"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Enrich property statistics with derived metrics and calculate bug count
        enriched_property_stats = {}
        for property_name, test_result in self.test_result.items():
            # Check if failed or error
            if test_result.get("fail", 0) > 0 or test_result.get("error", 0) > 0:
                data["bugs_found"] += 1

            executed_count = test_result.get("executed", 0)
            fail_count = test_result.get("fail", 0)
            error_count = test_result.get("error", 0)
            pass_count = max(executed_count - fail_count - error_count, 0)

            enriched_property_stats[property_name] = {
                **test_result,
                "pass_count": pass_count
            }

        # Store the enriched result data for direct use in HTML template
        data["property_stats"] = enriched_property_stats

        # Calculate properties statistics
        data["all_properties_count"] = len(self.test_result)
        data["executed_properties_count"] = sum(1 for result in self.test_result.values() if result.get("executed", 0) > 0)

        # Calculate detailed property statistics for table headers
        property_stats_summary = self._calculate_property_stats_summary(enriched_property_stats)
        data["property_stats_summary"] = property_stats_summary

        # Process coverage data
        data["coverage_trend"] = self.cov_trend

        if self.cov_trend:
            final_trend = self.cov_trend[-1]
            data["coverage"] = final_trend["coverage"]
            data["total_activities"] = final_trend["totalActivities"]
            data["tested_activities"] = final_trend["testedActivities"]
            data["total_activities_count"] = final_trend["totalActivitiesCount"]
            data["tested_activities_count"] = final_trend["testedActivitiesCount"]
            data["activity_count_history"] = final_trend["activityCountHistory"]

        # Generate property execution trend aligned with coverage trend
        data["property_execution_trend"] = self._generate_property_execution_trend(executed_properties_by_step)

        # Generate Property Violations list
        self._generate_property_violations_list(property_violations, data)

        # Load error details for properties with fail/error state
        data["property_error_details"] = self._load_property_error_details()

        # Load crash and ANR events from crash-dump.log
        crash_events, anr_events = self._load_crash_dump_data()

        # Add screenshot ID information to crash and ANR events
        self._add_screenshot_ids_to_events(crash_events)
        self._add_screenshot_ids_to_events(anr_events)

        data["crash_events"] = crash_events
        data["anr_events"] = anr_events

        return data

    def _parse_step_data(self, raw_step_info: str) -> StepData:
        step_data: StepData = json.loads(raw_step_info)
        step_data["Info"] = json.loads(step_data["Info"])
        return step_data

    @catchException("Error when marking screenshot")
    def _mark_screenshot(self, step_data: StepData):
        step_type = step_data["Type"]
        screenshot_name = step_data["Screenshot"]
        if not screenshot_name:
            return

        if step_type == "Monkey":
            act = step_data["Info"].get("act")
            pos = step_data["Info"].get("pos")
            if act in ["CLICK", "LONG_CLICK"] or act.startswith("SCROLL"):
                self._mark_screenshot_interaction(step_type, screenshot_name, act, pos)

        elif step_type == "Script":
            act = step_data["Info"].get("method")
            pos = step_data["Info"].get("params")
            if act in ["click", "setText", "swipe"]:
                self._mark_screenshot_interaction(step_type, screenshot_name, act, pos)


    def _mark_screenshot_interaction(self, step_type: str, screenshot_name: str, action_type: str, position: Union[List, Tuple]) -> bool:
        """
        Mark interaction on screenshot with colored rectangle

        Args:
            step_type (str): Type of the step (Monkey or Script)
            screenshot_name (str): Name of the screenshot file
            action_type (str): Type of action (CLICK/LONG_CLICK/SCROLL for Monkey, click/setText/swipe for Script)
            position: Position coordinates or parameters (format varies by action type)

        Returns:
            bool: True if marking was successful, False otherwise
        """
        screenshot_path: Path = self.data_path.screenshots_dir / screenshot_name
        if not screenshot_path.exists():
            logger.debug(f"Screenshot file {screenshot_path} not exists.")
            return False

        try:
            img = Image.open(screenshot_path).convert("RGB")
        except OSError as e:
            logger.debug(f"Error opening image {screenshot_path}: {e}")
            return False
        draw = ImageDraw.Draw(img)
        line_width = 5

        if step_type == "Monkey":
            if len(position) < 4:
                logger.warning(f"Monkey action requires 4 coordinates, got {len(position)}. Skip drawing.")
                return False

            x1, y1, x2, y2 = map(int, position[:4])

            if action_type == "CLICK":
                for i in range(line_width):
                    draw.rectangle([x1 - i, y1 - i, x2 + i, y2 + i], outline=(255, 0, 0))
            elif action_type == "LONG_CLICK":
                for i in range(line_width):
                    draw.rectangle([x1 - i, y1 - i, x2 + i, y2 + i], outline=(0, 0, 255))
            elif action_type.startswith("SCROLL"):
                for i in range(line_width):
                    draw.rectangle([x1 - i, y1 - i, x2 + i, y2 + i], outline=(0, 255, 0))

        elif step_type == "Script":
            if action_type == "click":

                if len(position) < 2:
                    logger.warning(f"Script click action requires 2 coordinates, got {len(position)}. Skip drawing.")
                    return False
                
                x, y = map(float, position[:2])
                x1, y1, x2, y2 = x - 50, y - 50, x + 50, y + 50

                for i in range(line_width):
                    draw.rectangle([x1 - i, y1 - i, x2 + i, y2 + i], outline=(255, 0, 0))
                    
            elif action_type == "swipe":

                if len(position) < 4:
                    logger.warning(f"Script swipe action requires 4 coordinates, got {len(position)}. Skip drawing.")
                    return False
                
                x1, y1, x2, y2 = map(float, position[:4])
                
                # mark start and end positions with rectangles
                start_x1, start_y1, start_x2, start_y2 = x1 - 50, y1 - 50, x1 + 50, y1 + 50
                for i in range(line_width):
                    draw.rectangle([start_x1 - i, start_y1 - i, start_x2 + i, start_y2 + i], outline=(255, 0, 0))

                end_x1, end_y1, end_x2, end_y2 = x2 - 50, y2 - 50, x2 + 50, y2 + 50
                for i in range(line_width):
                    draw.rectangle([end_x1 - i, end_y1 - i, end_x2 + i, end_y2 + i], outline=(255, 0, 0))
                
                # draw line between start and end positions
                draw.line([(x1, y1), (x2, y2)], fill=(255, 0, 0), width=line_width)
                
                # add text labels for start and end positions
                font = ImageFont.truetype("arial.ttf", 80)
                    
                # draw "start" at start position
                draw.text((x1 - 20, y1 - 70), "start", fill=(255, 0, 0), font=font)
                    
                # draw "end" at end position
                draw.text((x2 - 15, y2 - 70), "end", fill=(255, 0, 0), font=font)

        img.save(screenshot_path)
        return True

    @catchException("Error rendering template")
    def _generate_html_report(self, data: ReportData):
        """
        Generate HTML format bug report
        """
        # Format timestamp for display
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Ensure coverage_trend has data
        if not data.get("coverage_trend"):
            logger.warning("No coverage trend data")
            # Use the same field names as in coverage.log file
            data["coverage_trend"] = [{"stepsCount": 0, "coverage": 0, "testedActivitiesCount": 0}]

        # Convert coverage_trend to JSON string, ensuring all data points are included
        coverage_trend_json = json.dumps(data["coverage_trend"])
        logger.debug(f"Number of coverage trend data points: {len(data['coverage_trend'])}")

        # Prepare template data
        template_data = {
            'timestamp': timestamp,
            'bugs_found': data["bugs_found"],
            'total_testing_time': data["total_testing_time"],
            'executed_events': data["executed_events"],
            'coverage_percent': round(data["coverage"], 2),
            'total_activities_count': data["total_activities_count"],
            'tested_activities_count': data["tested_activities_count"],
            'tested_activities': data["tested_activities"],
            'total_activities': data["total_activities"],
            'all_properties_count': data["all_properties_count"],
            'executed_properties_count': data["executed_properties_count"],
            'items_per_page': 10,  # Items to display per page
            'screenshots': self.screenshots,
            'property_violations': data["property_violations"],
            'property_stats': data["property_stats"],
            'property_error_details': data["property_error_details"],
            'coverage_data': coverage_trend_json,
            'take_screenshots': self.take_screenshots,  # Pass screenshot setting to template
            'property_execution_trend': data["property_execution_trend"],
            'property_execution_data': json.dumps(data["property_execution_trend"]),
            'activity_count_history': data["activity_count_history"],
            'crash_events': data["crash_events"],
            'anr_events': data["anr_events"],
            'triggered_crash_count': len(data["crash_events"]),
            'triggered_anr_count': len(data["anr_events"]),
            'property_stats_summary': data["property_stats_summary"]
        }

        # Check if template exists, if not create it
        template_path = Path(__file__).parent / "templates" / "bug_report_template.html"
        if not template_path.exists():
            logger.warning("Template file does not exist, creating default template...")

        # Use Jinja2 to render template
        template = self.jinja_env.get_template("bug_report_template.html")
        html_content = template.render(**template_data)

        return html_content

    def _add_screenshot_info(self, step_data: StepData, step_index: int, data: Dict):
        """
        Add screenshot information to data structure

        Args:
            step_data: data for the current step
            step_index: Current step index
            data: Data dictionary to update
        """
        caption = ""

        if step_data["Type"] == "Monkey":
            # Extract 'act' attribute for Monkey type and add MonkeyStepsCount
            monkey_steps_count = step_data.get('MonkeyStepsCount', 'N/A')
            action = step_data['Info'].get('act', 'N/A')
            caption = f"Monkey Step {monkey_steps_count}: {action}"
        elif step_data["Type"] == "Script":
            # Extract 'method' attribute for Script type
            caption = f"{step_data['Info'].get('method', 'N/A')}"
        elif step_data["Type"] == "ScriptInfo":
            # Extract 'propName' and 'state' attributes for ScriptInfo type
            prop_name = step_data["Info"].get('propName', '')
            state = step_data["Info"].get('state', 'N/A')
            caption = f"{prop_name}: {state}" if prop_name else f"{state}"

        screenshot_name = step_data["Screenshot"]

        # Check if the screenshot file actually exists
        screenshot_file_path = self.data_path.screenshots_dir / screenshot_name
        if not screenshot_file_path.exists():
            # Skip adding this screenshot if the file doesn't exist
            return

        # Use relative path string instead of Path object
        abs_screenshots_path = self.data_path.output_dir / "screenshots" / screenshot_name
        relative_screenshot_path = str(abs_screenshots_path.relative_to(self.result_dir))

        data["screenshot_info"][screenshot_name] = {
            "type": step_data["Type"],
            "caption": caption,
            "step_index": step_index
        }

        self.screenshots.append({
            'id': step_index,
            'path': relative_screenshot_path,  # Now using string path
            'caption': f"{step_index}. {caption}"
        })

    def _process_script_info(self, property_name: str, state: str, step_index: int, screenshot: str,
                             current_property: str, current_test: Dict, property_violations: Dict) -> Tuple:
        """
        Process ScriptInfo step for property violations tracking

        Args:
            property_name: Property name from ScriptInfo
            state: State from ScriptInfo (start, pass, fail, error)
            step_index: Current step index
            screenshot: Screenshot filename
            current_property: Currently tracked property
            current_test: Current test data
            property_violations: Dictionary to store violations

        Returns:
            tuple: (updated_current_property, updated_current_test)
        """
        if property_name and state:
            if state == "start":
                # Record new test start
                current_property = property_name
                current_test = {
                    "start": step_index,
                    "end": None,
                    "screenshot_start": screenshot
                }

            elif state in ["pass", "fail", "error"]:
                if current_property == property_name:
                    # Update test end information
                    current_test["end"] = step_index
                    current_test["screenshot_end"] = screenshot

                    if state == "fail" or state == "error":
                        # Record failed/error test
                        if property_name not in property_violations:
                            property_violations[property_name] = []

                        property_violations[property_name].append({
                            "start": current_test["start"],
                            "end": current_test["end"],
                            "screenshot_start": current_test["screenshot_start"],
                            "screenshot_end": screenshot
                        })

                    # Reset current test
                    current_property = None
                    current_test = {}

        return current_property, current_test

    def _generate_property_violations_list(self, property_violations: Dict, data: Dict):
        """
        Generate property violations list from collected violation data

        Args:
            property_violations: Dictionary containing property violations
            data: Data dictionary to update with property violations list
        """
        if property_violations:
            index = 1
            for property_name, violations in property_violations.items():
                for violation in violations:
                    start_step = violation["start"]
                    end_step = violation["end"]
                    data["property_violations"].append({
                        "index": index,
                        "property_name": property_name,
                        "interaction_pages": [start_step, end_step]
                    })
                    index += 1

    def _load_property_error_details(self) -> Dict[str, List[Dict]]:
        """
        Load property execution error details from property_exec_info file
        
        Returns:
            Dict[str, List[Dict]]: Mapping of property names to their error tracebacks with context
        """
        if not self.data_path.property_exec_info.exists():
            logger.warning(f"Property exec info file {self.data_path.property_exec_info} not found")
            return {}
            
        try:
            property_exec_infos = self._parse_property_exec_infos()
            return self._group_errors_by_property(property_exec_infos)
            
        except Exception as e:
            logger.error(f"Error reading property exec info file: {e}")
            return {}

    def _parse_property_exec_infos(self) -> List[PropertyExecInfo]:
        """Parse property execution info from file"""
        exec_infos = []
        
        with open(self.data_path.property_exec_info, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    exec_info_data = json.loads(line)
                    prop_name = exec_info_data.get("propName", "")
                    state = exec_info_data.get("state", "")
                    tb = exec_info_data.get("tb", "")
                    start_steps_count = exec_info_data.get("startStepsCount", 0)
                    
                    exec_info = PropertyExecInfo(
                        prop_name=prop_name,
                        state=state,
                        traceback=tb,
                        start_steps_count=start_steps_count
                    )
                    
                    if exec_info.is_error_state() and prop_name and tb:
                        exec_infos.append(exec_info)
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse property exec info line {line_number}: {line[:100]}... Error: {e}")
                    continue
                    
        return exec_infos

    def _group_errors_by_property(self, exec_infos: List[PropertyExecInfo]) -> Dict[str, List[Dict]]:
        """Group errors by property name and deduplicate"""
        error_details = {}
        
        for exec_info in exec_infos:
            prop_name = exec_info.prop_name
            
            if prop_name not in error_details:
                error_details[prop_name] = {}
            
            error_hash = exec_info.get_error_hash()
            
            if error_hash in error_details[prop_name]:
                # Error already exists, add occurrence
                error_details[prop_name][error_hash].add_occurrence(exec_info.start_steps_count)
            else:
                # New error, create entry
                error_details[prop_name][error_hash] = exec_info
        
        # Convert to template-compatible format
        result = {}
        for prop_name, hash_dict in error_details.items():
            result[prop_name] = []
            for exec_info in hash_dict.values():
                result[prop_name].append({
                    "state": exec_info.state,
                    "traceback": exec_info.traceback,
                    "occurrence_count": exec_info.occurrence_count,
                    "short_description": exec_info.short_description,
                    "startStepsCountList": exec_info.start_steps_count_list
                })
            
            # Sort by earliest startStepsCount, then by occurrence count (descending)
            result[prop_name].sort(key=lambda x: (min(x["startStepsCountList"]), -x["occurrence_count"]))
        
        return result

    def _generate_property_execution_trend(self, executed_properties_by_step: Dict[int, set]) -> List[Dict]:
        """
        Generate property execution trend aligned with coverage trend
        
        Args:
            executed_properties_by_step: Dictionary containing executed properties at each step
            
        Returns:
            List[Dict]: Property execution trend data aligned with coverage trend
        """
        property_execution_trend = []
        
        # Get step points from coverage trend to ensure alignment
        coverage_step_points = []
        if self.cov_trend:
            coverage_step_points = [cov_data["stepsCount"] for cov_data in self.cov_trend]
        
        # If no coverage data, use property execution data points
        if not coverage_step_points and executed_properties_by_step:
            coverage_step_points = sorted(executed_properties_by_step.keys())
        
        # Generate property execution data for each coverage step point
        for step_count in coverage_step_points:
            # Find the latest executed properties count up to this step
            executed_count = 0
            latest_step = 0
            
            for exec_step in executed_properties_by_step.keys():
                if exec_step <= step_count and exec_step >= latest_step:
                    latest_step = exec_step
                    executed_count = len(executed_properties_by_step[exec_step])
            
            property_execution_trend.append({
                "stepsCount": step_count,
                "executedPropertiesCount": executed_count
            })
        
        return property_execution_trend

    def _calculate_property_stats_summary(self, test_result: TestResult) -> Dict[str, int]:
        """
        Calculate summary statistics for property checking table headers

        Args:
            test_result: Test result data containing property statistics

        Returns:
            Dict: Summary statistics for each column
        """
        stats_summary = {
            "total_properties": 0,
            "total_precond_satisfied": 0,
            "total_executed": 0,
            "total_passes": 0,
            "total_fails": 0,
            "total_errors": 0,
            "properties_with_errors": 0
        }

        for property_name, result in test_result.items():
            executed_count = result.get("executed", result.get("executed_total", 0))
            fail_count = result.get("fail", 0)
            error_count = result.get("error", 0)
            pass_count = result.get("pass_count",
                                    max(executed_count - fail_count - error_count, 0))

            stats_summary["total_properties"] += 1
            stats_summary["total_precond_satisfied"] += result.get("precond_satisfied", 0)
            stats_summary["total_executed"] += executed_count
            stats_summary["total_passes"] += pass_count
            stats_summary["total_fails"] += fail_count
            stats_summary["total_errors"] += error_count

            # Count properties that have errors or fails
            if fail_count > 0 or error_count > 0:
                stats_summary["properties_with_errors"] += 1

        return stats_summary

    def _load_crash_dump_data(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Load crash and ANR events from crash-dump.log file

        Returns:
            tuple: (crash_events, anr_events) - Lists of crash and ANR event dictionaries
        """
        crash_events = []
        anr_events = []

        if not self.data_path.crash_dump_log.exists():
            logger.info(f"No crash was found in this run.")
            return crash_events, anr_events

        try:
            with open(self.data_path.crash_dump_log, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse crash events with screenshot mapping
            crash_events = self._parse_crash_events_with_screenshots(content)

            # Parse ANR events with screenshot mapping
            anr_events = self._parse_anr_events_with_screenshots(content)

            logger.debug(f"Found {len(crash_events)} crash events and {len(anr_events)} ANR events")

            return crash_events, anr_events

        except Exception as e:
            logger.error(f"Error reading crash dump file: {e}")
            return crash_events, anr_events

    def _parse_crash_events_with_screenshots(self, content: str) -> List[Dict]:
        """
        Parse crash events from crash-dump.log content with screenshot mapping

        Args:
            content: Content of crash-dump.log file

        Returns:
            List[Dict]: List of crash event dictionaries with screenshot information
        """
        crash_events = []

        # Pattern to match crash blocks with optional screenshot information
        # Look for StepsCount and CrashScreen before the timestamp
        crash_pattern = r'(?:StepsCount:\s*(\d+)\s*\nCrashScreen:\s*([^\n]+)\s*\n)?(\d{14})\ncrash:\n(.*?)\n// crash end'

        for match in re.finditer(crash_pattern, content, re.DOTALL):
            steps_count = match.group(1)
            crash_screen = match.group(2)
            timestamp_str = match.group(3)
            crash_content = match.group(4)

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
                "stack_trace": crash_info.get("stack_trace", ""),
                "steps_count": steps_count,
                "crash_screen": crash_screen.strip() if crash_screen else None
            }

            crash_events.append(crash_event)

        return crash_events

    def _parse_anr_events_with_screenshots(self, content: str) -> List[Dict]:
        """
        Parse ANR events from crash-dump.log content with screenshot mapping

        Args:
            content: Content of crash-dump.log file

        Returns:
            List[Dict]: List of ANR event dictionaries with screenshot information
        """
        anr_events = []

        # Pattern to match ANR blocks with optional screenshot information
        anr_pattern = r'(?:StepsCount:\s*(\d+)\s*\nCrashScreen:\s*([^\n]+)\s*\n)?(\d{14})\nanr:\n(.*?)\nanr end'

        for match in re.finditer(anr_pattern, content, re.DOTALL):
            steps_count = match.group(1)
            crash_screen = match.group(2)
            timestamp_str = match.group(3)
            anr_content = match.group(4)

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
                "trace": anr_info.get("trace", ""),
                "steps_count": steps_count,
                "crash_screen": crash_screen.strip() if crash_screen else None
            }

            anr_events.append(anr_event)

        return anr_events

    def _find_screenshot_id_by_filename(self, screenshot_filename: str) -> str:
        """
        Find screenshot ID by filename in the screenshots list

        Args:
            screenshot_filename: Name of the screenshot file

        Returns:
            str: Screenshot ID if found, empty string otherwise
        """
        if not screenshot_filename:
            return ""

        for screenshot in self.screenshots:
            # Extract filename from path
            screenshot_path = screenshot.get('path', '')
            if screenshot_path.endswith(screenshot_filename):
                return str(screenshot.get('id', ''))

        return ""

    def _add_screenshot_ids_to_events(self, events: List[Dict]):
        """
        Add screenshot ID information to crash/ANR events

        Args:
            events: List of crash or ANR event dictionaries
        """
        for event in events:
            crash_screen = event.get('crash_screen')
            if crash_screen:
                screenshot_id = self._find_screenshot_id_by_filename(crash_screen)
                event['screenshot_id'] = screenshot_id
            else:
                event['screenshot_id'] = ""

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


if __name__ == "__main__":
    print("Generating bug report")
    # OUTPUT_PATH = "<Your output path>"
    OUTPUT_PATH = "/Users/drifter327/Code/Kea2/output/res_2025090122_1216279438"

    report_generator = BugReportGenerator()
    report_path = report_generator.generate_report(OUTPUT_PATH)
    print(f"bug report generated: {report_path}")
