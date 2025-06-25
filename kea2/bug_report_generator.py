import json
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, TypedDict
from collections import deque
import concurrent.futures
import queue
import threading

import cv2
from jinja2 import Environment, FileSystemLoader, select_autoescape, PackageLoader
from kea2.utils import getLogger, timer

logger = getLogger(__name__)


class StepData(TypedDict):
    Type: str
    MonkeyStepsCount: int
    Time: str
    Info: Dict
    Screenshot: str

@dataclass
class DataPath:
    steps_log: Path
    result_json: Path
    coverage_log: Path
    screenshots_dir: Path

@dataclass
class ScreenshotTask:
    """Screenshot marking task data structure"""
    screenshot_path: Path
    action_type: str
    position: list
    task_id: str

@dataclass
class ImageData:
    """Image data structure"""
    task_id: str
    image: object  # cv2 image
    action_type: str
    position: list
    screenshot_path: Path


class BugReportGenerator:
    """
    Generate HTML format bug reports
    """

    def __init__(self, result_dir=None):
        """
        Initialize the bug report generator

        Args:
            result_dir: Directory path containing test results (optional)
        """
        if result_dir is not None:
            self._setup_paths(result_dir)
        
        # Create thread pool with maximum worker threads for general tasks
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        
        # Create separate thread pools for screenshot processing pipeline
        self.screenshot_readers = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.screenshot_processors = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self.screenshot_writers = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        
        # Pipeline queues for screenshot processing
        self.read_queue = queue.Queue(maxsize=10)
        self.process_queue = queue.Queue(maxsize=10)
        self.write_queue = queue.Queue(maxsize=10)
        
        # Pipeline control flags
        self._pipeline_shutdown = False
        self._pipeline_threads = []

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
        self.log_timestamp = self.result_dir.name.split("_", 1)[1]

        self.data_path: DataPath = DataPath(
            steps_log=self.result_dir / f"output_{self.log_timestamp}" / "steps.log",
            result_json=self.result_dir / f"result_{self.log_timestamp}.json",
            coverage_log=self.result_dir / f"output_{self.log_timestamp}" / "coverage.log",
            screenshots_dir=self.result_dir / f"output_{self.log_timestamp}" / "screenshots"
        )

        self.screenshots = deque()
        self.take_screenshots = self._detect_screenshots_setting()

    def __del__(self):
        """Clean up thread pool resources"""
        self._shutdown_screenshot_pipeline()
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)

    def _shutdown_screenshot_pipeline(self):
        """Gracefully shutdown screenshot processing pipeline"""
        try:
            # Set shutdown flag
            self._pipeline_shutdown = True
            
            # Wait for all pipeline threads to complete
            for thread in self._pipeline_threads:
                if thread.is_alive():
                    thread.join(timeout=2)
            
            # Clear queues to avoid thread blocking
            self._clear_queues()
            
            # Shutdown thread pools
            if hasattr(self, 'screenshot_readers'):
                self.screenshot_readers.shutdown(wait=False)
            if hasattr(self, 'screenshot_processors'):
                self.screenshot_processors.shutdown(wait=False)
            if hasattr(self, 'screenshot_writers'):
                self.screenshot_writers.shutdown(wait=False)
                
        except Exception as e:
            logger.error(f"Error shutting down screenshot pipeline: {e}")

    def _clear_queues(self):
        """Clear all queues"""
        queues = [self.read_queue, self.process_queue, self.write_queue]
        for q in queues:
            try:
                while not q.empty():
                    q.get_nowait()
            except queue.Empty:
                pass

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
                raise ValueError("No result directory specified. Please provide result_dir_path or initialize with a directory.")
            
            logger.debug("Starting bug report generation")

            # Collect test data
            test_data = self._collect_test_data()

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
            raise

    def _collect_test_data(self):
        """
        Collect test data, including results, coverage, etc.
        """
        data = {
            "timestamp": self.log_timestamp,
            "bugs_found": 0,
            "executed_events": 0,
            "total_testing_time": 0,
            "coverage": 0,
            "total_activities": [],
            "tested_activities": [],
            "property_violations": [],
            "property_stats": [],
            "screenshot_info": {},
            "coverage_trend": []
        }

        # Use thread pool to read multiple files in parallel
        future_tasks = {}
        
        # Submit file reading tasks
        if self.data_path.steps_log.exists():
            future_tasks['steps'] = self.executor.submit(self._process_steps_log_parallel)
        
        if self.data_path.result_json.exists():
            future_tasks['result'] = self.executor.submit(self._read_result_json)
            
        if self.data_path.coverage_log.exists():
            future_tasks['coverage'] = self.executor.submit(self._get_cov_trend_parallel)

        # Wait for all tasks to complete and collect results
        results = {}
        for task_name, future in future_tasks.items():
            try:
                results[task_name] = future.result()
            except Exception as e:
                logger.error(f"Error in {task_name} task: {e}")
                results[task_name] = None

        # Process step log results
        if 'steps' in results and results['steps']:
            steps_data = results['steps']
            data.update(steps_data)

        # Process result file
        if 'result' in results and results['result']:
            result_data = results['result']
            data["bugs_found"] = sum(1 for test_result in result_data.values() 
                                   if test_result.get("fail", 0) > 0 or test_result.get("error", 0) > 0)
            data["property_stats"] = result_data

        # Process coverage data
        if 'coverage' in results and results['coverage']:
            cov_trend, last_coverage = results['coverage']
            if cov_trend:
                data["coverage_trend"] = cov_trend
            if last_coverage:
                data["coverage"] = last_coverage.get("coverage", 0)
                data["total_activities"] = last_coverage.get("totalActivities", [])
                data["tested_activities"] = last_coverage.get("testedActivities", [])

        return data

    def _process_steps_log_parallel(self):
        """Process step log file in parallel"""
        try:
            steps_data = {
                "executed_events": 0,
                "total_testing_time": 0,
                "property_violations": [],
                "screenshot_info": {}
            }
            
            steps_log_path = self.data_path.steps_log
            property_violations = {}
            relative_path = f"output_{self.log_timestamp}/screenshots"
            
            # Batch read file content
            with open(steps_log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Use thread pool to parse JSON data in parallel
            parse_futures = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as json_executor:
                for i, line in enumerate(lines):
                    if line.strip():
                        future = json_executor.submit(self._parse_step_data_safe, line, i)
                        parse_futures.append(future)
                
                # Collect parsing results
                parsed_steps = []
                for future in concurrent.futures.as_completed(parse_futures):
                    result = future.result()
                    if result:
                        parsed_steps.append(result)
                
                # Sort by step index
                parsed_steps.sort(key=lambda x: x[1])  # Sort by index

            # Start screenshot processing pipeline
            screenshot_pipeline_future = None
            screenshot_tasks = []
            if self.take_screenshots:
                screenshot_pipeline_future = self.executor.submit(self._start_screenshot_pipeline)

            # Process parsed step data
            current_property = None
            current_test = {}
            monkey_events_count = 0
            step_index = 0

            for step_data, original_index in parsed_steps:
                if step_data:
                    step_index += 1
                    step_type = step_data.get("Type", "")
                    screenshot = step_data.get("Screenshot", "")
                    info = step_data.get("Info", {})

                    if step_type == "Monkey":
                        monkey_events_count += 1

                    # Collect screenshot marking tasks (using new parallel pipeline)
                    if self.take_screenshots and screenshot and step_type == "Monkey":
                        task = self._create_screenshot_task(info, screenshot)
                        if task:
                            screenshot_tasks.append(task)

                    # Add screenshot information
                    if screenshot and screenshot not in steps_data["screenshot_info"]:
                        self._add_screenshot_info(screenshot, step_type, info, step_index, relative_path, steps_data)

                    # Process script information
                    if step_type == "ScriptInfo":
                        try:
                            property_name = info.get("propName", "")
                            state = info.get("state", "")
                            current_property, current_test = self._process_script_info(
                                property_name, state, step_index, screenshot,
                                current_property, current_test, property_violations
                            )
                        except Exception as e:
                            logger.error(f"Error processing ScriptInfo step {step_index}: {e}")

                    # Record timing information
                    if step_index == 1:
                        first_step_time = step_data["Time"]
                    last_step_time = step_data["Time"]

            # Process all screenshot tasks
            if screenshot_tasks:
                self._process_screenshot_tasks_pipeline(screenshot_tasks)

            # Wait for screenshot processing pipeline to complete
            if screenshot_pipeline_future:
                try:
                    screenshot_pipeline_future.result(timeout=30)  # 30 seconds timeout
                    
                    # Wait for all pipeline threads to complete
                    for thread in self._pipeline_threads:
                        if thread.is_alive():
                            thread.join(timeout=5)
                            
                except concurrent.futures.TimeoutError:
                    logger.warning("Screenshot pipeline processing timeout")
                finally:
                    # Ensure pipeline is properly closed
                    self._shutdown_screenshot_pipeline()

            steps_data["executed_events"] = monkey_events_count

            # Calculate test time
            if step_index > 0:
                try:
                    steps_data["total_testing_time"] = int((
                        datetime.datetime.strptime(last_step_time, "%Y-%m-%d %H:%M:%S.%f") -
                        datetime.datetime.strptime(first_step_time, "%Y-%m-%d %H:%M:%S.%f")
                    ).total_seconds())
                except Exception as e:
                    logger.error(f"Error calculating test time: {e}")

            # Generate property violations list
            self._generate_property_violations_list(property_violations, steps_data)
            
            return steps_data
            
        except Exception as e:
            logger.error(f"Error processing steps log: {e}")
            return None

    def _parse_step_data_safe(self, line, index):
        """Safe step data parsing, returns (step_data, index) tuple"""
        try:
            if line.strip():
                step_data = self._parse_step_data(line)
                return (step_data, index)
        except Exception as e:
            logger.error(f"Error parsing step data at line {index}: {e}")
        return (None, index)

    def _read_result_json(self):
        """Read result JSON file"""
        try:
            with open(self.data_path.result_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading result JSON: {e}")
            return None

    def _get_cov_trend_parallel(self):
        """Process coverage trend data in parallel"""
        try:
            cov_trend = []
            last_coverage = None
            
            with open(self.data_path.coverage_log, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Use thread pool to parse coverage data in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as cov_executor:
                parse_futures = []
                for i, line in enumerate(lines):
                    if line.strip():
                        future = cov_executor.submit(self._parse_coverage_line, line, i)
                        parse_futures.append(future)
                
                # Collect parsing results
                coverage_data_list = []
                for future in concurrent.futures.as_completed(parse_futures):
                    result = future.result()
                    if result:
                        coverage_data_list.append(result)
                
                # Sort by index
                coverage_data_list.sort(key=lambda x: x[1])
                
                # Extract coverage trend data
                for coverage_data, _ in coverage_data_list:
                    if coverage_data:
                        cov_trend.append({
                            "steps": coverage_data.get("stepsCount", 0),
                            "coverage": coverage_data.get("coverage", 0),
                            "tested_activities_count": coverage_data.get("testedActivitiesCount", 0)
                        })
                        last_coverage = coverage_data
            
            return cov_trend, last_coverage
            
        except Exception as e:
            logger.error(f"Error processing coverage trend: {e}")
            return [], None

    def _parse_coverage_line(self, line, index):
        """Safe parsing of coverage data line"""
        try:
            if line.strip():
                coverage_data = json.loads(line)
                return (coverage_data, index)
        except Exception as e:
            logger.error(f"Error parsing coverage data at line {index}: {e}")
        return (None, index)

    def _parse_step_data(self, raw_step_info: str) -> StepData:
        step_data = json.loads(raw_step_info)
        step_data["Info"] = json.loads(step_data.get("Info"))
        return step_data

    def _create_screenshot_task(self, info, screenshot: str) -> ScreenshotTask:
        """Create screenshot marking task"""
        try:
            act = info.get("act")
            pos = info.get("pos")
            if act in ["CLICK", "LONG_CLICK"] or act.startswith("SCROLL"):
                screenshot_path = self.data_path.screenshots_dir / screenshot
                if screenshot_path.exists():
                    return ScreenshotTask(
                        screenshot_path=screenshot_path,
                        action_type=act,
                        position=pos,
                        task_id=f"{screenshot}_{act}"
                    )
        except Exception as e:
            logger.error(f"Error creating screenshot task: {e}")
        return None

    def _start_screenshot_pipeline(self):
        """Start screenshot processing pipeline"""
        # Reset shutdown flag
        self._pipeline_shutdown = False
        self._pipeline_threads = []
        
        # Start reader thread
        reader_thread = threading.Thread(target=self._screenshot_reader_worker, daemon=True)
        reader_thread.start()
        self._pipeline_threads.append(reader_thread)
        
        # Start processor thread
        processor_thread = threading.Thread(target=self._screenshot_processor_worker, daemon=True)
        processor_thread.start()
        self._pipeline_threads.append(processor_thread)
        
        # Start writer thread
        writer_thread = threading.Thread(target=self._screenshot_writer_worker, daemon=True)
        writer_thread.start()
        self._pipeline_threads.append(writer_thread)
        
        return True

    def _process_screenshot_tasks_pipeline(self, tasks: list[ScreenshotTask]):
        """Add screenshot tasks to processing pipeline"""
        for task in tasks:
            if self._pipeline_shutdown:
                break
            try:
                self.read_queue.put(task, timeout=5)
            except queue.Full:
                logger.warning(f"Read queue full, skipping task {task.task_id}")
        
        # Send termination signal
        if not self._pipeline_shutdown:
            try:
                self.read_queue.put(None, timeout=2)
            except queue.Full:
                logger.warning("Could not send termination signal to read queue")

    def _screenshot_reader_worker(self):
        """Screenshot reading worker thread"""
        try:
            while not self._pipeline_shutdown:
                try:
                    task = self.read_queue.get(timeout=2)
                    if task is None:  # Termination signal
                        self.process_queue.put(None, timeout=2)
                        break
                    
                    # Check if thread pool is still available
                    if self._pipeline_shutdown or self.screenshot_readers._shutdown:
                        break
                    
                    # Parallel image reading
                    future = self.screenshot_readers.submit(self._read_image_parallel, task)
                    image_data = future.result(timeout=10)
                    
                    if image_data and not self._pipeline_shutdown:
                        try:
                            self.process_queue.put(image_data, timeout=2)
                        except queue.Full:
                            logger.warning("Process queue full, dropping image data")
                        
                except queue.Empty:
                    continue  # Continue waiting for tasks
                except Exception as e:
                    if not self._pipeline_shutdown:
                        logger.error(f"Error in screenshot reader worker: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Fatal error in screenshot reader worker: {e}")
        finally:
            # Ensure termination signal is sent
            try:
                if not self._pipeline_shutdown:
                    self.process_queue.put(None, timeout=1)
            except:
                pass

    def _screenshot_processor_worker(self):
        """Screenshot processing worker thread"""
        try:
            while not self._pipeline_shutdown:
                try:
                    image_data = self.process_queue.get(timeout=2)
                    if image_data is None:  # Termination signal
                        self.write_queue.put(None, timeout=2)
                        break
                    
                    # Check if thread pool is still available
                    if self._pipeline_shutdown or self.screenshot_processors._shutdown:
                        break
                    
                    # Parallel image processing
                    future = self.screenshot_processors.submit(self._process_image_parallel, image_data)
                    processed_data = future.result(timeout=10)
                    
                    if processed_data and not self._pipeline_shutdown:
                        try:
                            self.write_queue.put(processed_data, timeout=2)
                        except queue.Full:
                            logger.warning("Write queue full, dropping processed data")
                        
                except queue.Empty:
                    continue  # Continue waiting for tasks
                except Exception as e:
                    if not self._pipeline_shutdown:
                        logger.error(f"Error in screenshot processor worker: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Fatal error in screenshot processor worker: {e}")
        finally:
            # Ensure termination signal is sent
            try:
                if not self._pipeline_shutdown:
                    self.write_queue.put(None, timeout=1)
            except:
                pass

    def _screenshot_writer_worker(self):
        """Screenshot writing worker thread"""
        try:
            while not self._pipeline_shutdown:
                try:
                    processed_data = self.write_queue.get(timeout=2)
                    if processed_data is None:  # Termination signal
                        break
                    
                    # Check if thread pool is still available
                    if self._pipeline_shutdown or self.screenshot_writers._shutdown:
                        break
                    
                    # Parallel image writing
                    future = self.screenshot_writers.submit(self._write_image_parallel, processed_data)
                    future.result(timeout=10)
                        
                except queue.Empty:
                    continue  # Continue waiting for tasks
                except Exception as e:
                    if not self._pipeline_shutdown:
                        logger.error(f"Error in screenshot writer worker: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Fatal error in screenshot writer worker: {e}")

    def _read_image_parallel(self, task: ScreenshotTask) -> ImageData:
        """Parallel image reading"""
        try:
            img = cv2.imread(str(task.screenshot_path))
            if img is None:
                logger.warning(f"Could not read image: {task.screenshot_path}")
                return None
            
            return ImageData(
                task_id=task.task_id,
                image=img,
                action_type=task.action_type,
                position=task.position,
                screenshot_path=task.screenshot_path
            )
        except Exception as e:
            logger.error(f"Error reading image {task.screenshot_path}: {e}")
            return None

    def _process_image_parallel(self, image_data: ImageData) -> ImageData:
        """Parallel image processing (marking operation)"""
        try:
            img = image_data.image
            position = image_data.position
            action_type = image_data.action_type
            
            # Validate position format
            if not isinstance(position, (list, tuple)) or len(position) != 4:
                logger.warning(f"Invalid position format: {position}")
                return None

            x1, y1, x2, y2 = int(position[0]), int(position[1]), int(position[2]), int(position[3])

            # Choose color based on action type: CLICK uses red, LONG_CLICK uses blue
            if action_type == "CLICK":
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 5)
            elif action_type == "LONG_CLICK":
                cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 5)
            elif action_type.startswith("SCROLL"):
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 5)

            return image_data
            
        except Exception as e:
            logger.error(f"Error processing image {image_data.task_id}: {e}")
            return None

    def _write_image_parallel(self, image_data: ImageData) -> bool:
        """Parallel image writing"""
        try:
            cv2.imwrite(str(image_data.screenshot_path), image_data.image)
            return True
        except Exception as e:
            logger.error(f"Error writing image {image_data.screenshot_path}: {e}")
            return False

    def _detect_screenshots_setting(self):
        """
            Detect if screenshots were enabled during test run.
            Returns True if screenshots were taken, False otherwise.
        """
        return self.data_path.screenshots_dir.exists()

    def _generate_html_report(self, data):
        """
        Generate HTML format bug report
        """
        try:
            # Format timestamp for display
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Ensure coverage_trend has data
            if not data["coverage_trend"]:
                logger.warning("No coverage trend data")
                data["coverage_trend"] = [{"steps": 0, "coverage": 0, "tested_activities_count": 0}]

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
                'total_activities_count': len(data["total_activities"]),
                'tested_activities_count': len(data["tested_activities"]),
                'tested_activities': data["tested_activities"],  # Pass list of tested Activities
                'total_activities': data["total_activities"],  # Pass list of all Activities
                'items_per_page': 10,  # Items to display per page
                'screenshots': self.screenshots,
                'property_violations': data["property_violations"],
                'property_stats': data["property_stats"],
                'coverage_data': coverage_trend_json,
                'take_screenshots': self.take_screenshots  # Pass screenshot setting to template
            }

            # Check if template exists, if not create it
            template_path = Path(__file__).parent / "templates" / "bug_report_template.html"
            if not template_path.exists():
                logger.warning("Template file does not exist, creating default template...")

            # Use Jinja2 to render template
            template = self.jinja_env.get_template("bug_report_template.html")
            html_content = template.render(**template_data)

            return html_content

        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            raise

    def _add_screenshot_info(self, screenshot: str, step_type: str, info: Dict, step_index: int, relative_path: str, steps_data: Dict):
        """
        Add screenshot information to data structure
        
        Args:
            screenshot: Screenshot filename
            step_type: Type of step (Monkey, Script, ScriptInfo)
            info: Step information dictionary
            step_index: Current step index
            relative_path: Relative path to screenshots directory
            steps_data: Steps data dictionary to update
        """
        try:
            caption = ""

            if step_type == "Monkey":
                # Extract 'act' attribute for Monkey type and convert to lowercase
                caption = f"{info.get('act', 'N/A').lower()}"
            elif step_type == "Script":
                # Extract 'method' attribute for Script type
                caption = f"{info.get('method', 'N/A')}"
            elif step_type == "ScriptInfo":
                # Extract 'propName' and 'state' attributes for ScriptInfo type
                prop_name = info.get('propName', '')
                state = info.get('state', 'N/A')
                caption = f"{prop_name} {state}" if prop_name else f"{state}"

            steps_data["screenshot_info"][screenshot] = {
                "type": step_type,
                "caption": caption,
                "step_index": step_index
            }
            
            screenshot_caption = steps_data["screenshot_info"][screenshot].get('caption', '')
            self.screenshots.append({
                'id': step_index,
                'path': f"{relative_path}/{screenshot}",
                'caption': f"{step_index}. {screenshot_caption}"
            })
            
        except Exception as e:
            logger.error(f"Error parsing screenshot info: {e}")
            steps_data["screenshot_info"][screenshot] = {
                "type": step_type,
                "caption": step_type,
                "step_index": step_index
            }
            
            screenshot_caption = steps_data["screenshot_info"][screenshot].get('caption', '')
            self.screenshots.append({
                'id': step_index,
                'path': f"{relative_path}/{screenshot}",
                'caption': f"{step_index}. {screenshot_caption}"
            })

    def _process_script_info(self, property_name: str, state: str, step_index: int, screenshot: str, 
                           current_property: str, current_test: Dict, property_violations: Dict) -> tuple:
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
                        "precondition_page": start_step,
                        "interaction_pages": [start_step, end_step],
                        "postcondition_page": end_step
                    })
                    index += 1


if __name__ == "__main__":
    print("开始生成bug报告...")

    try:
        b = BugReportGenerator()
        report_path = b.generate_report("P:/Python/Kea2/output/res_2025062520_1336605919")
        print(f"✓ bug报告生成成功: {report_path}")
    except Exception as e:
        print(f"✗ 生成失败: {e}")
        print("请检查目录路径是否正确")
