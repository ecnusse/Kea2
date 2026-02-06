from dataclasses import dataclass
import re

from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from ..utils import catchException, getLogger

from typing import TYPE_CHECKING, Dict, List, Tuple, Union
if TYPE_CHECKING:
    from .bug_report_generator import BugReportGenerator, StepData


CRASH_PATTERN = r'(?:StepsCount:\s*(\d+)\s*\nCrashScreen:\s*([^\n]*)\s*\n)?(\d{14})\ncrash:\n(.*?)\n// crash end'
ANR_PATTERN = r'(?:StepsCount:\s*(\d+)\s*\nCrashScreen:\s*([^\n]+)\s*\n)?(\d{14})\nanr:\n(.*?)\nanr end'


@dataclass
class DataPath:
    output_dir: Path
    steps_log: Path
    result_json: Path
    coverage_log: Path
    screenshots_dir: Path
    property_exec_info: Path
    crash_dump_log: Path


logger = getLogger(__name__)


class CrashAnrMixin:
    def _iter_crash_info(self: "BugReportGenerator", content: str, pattern: str):
        """
        Iterate over crash info blocks in crash-dump.log content

        Args:
            content: Content of crash-dump.log file

        Yields:
            Tuple[str, str, str, str]: steps_count, crash_screen, timestamp_str, crash_content
        """
        for match in re.finditer(pattern, content, re.DOTALL):
            steps_count = match.group(1)
            crash_screen = match.group(2)
            timestamp_str = match.group(3)
            crash_content = match.group(4)
            
            if timestamp_str:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                
            if not crash_screen and steps_count:
                _crash_screens = list(self.data_path.screenshots_dir.glob(f'screenshot-{steps_count}-*.png'))
                if _crash_screens:
                    crash_screen = str(_crash_screens[0].name)
            
            yield steps_count, crash_screen, timestamp_str, crash_content

    def _parse_crash_events_with_screenshots(self: "BugReportGenerator", content: str) -> List[Dict]:
        """
        Parse crash events from crash-dump.log content with screenshot mapping

        Args:
            content: Content of crash-dump.log file

        Returns:
            List[Dict]: List of crash event dictionaries with screenshot information
        """
        crash_events = []
        for steps_count, crash_screen, timestamp_str, crash_content in self._iter_crash_info(content, CRASH_PATTERN):
            crash_info = self._extract_crash_info(crash_content)
            crash_event = {
                "time": timestamp_str,
                "exception_type": crash_info.get("exception_type", "Unknown"),
                "process": crash_info.get("process", "Unknown"),
                "stack_trace": crash_info.get("stack_trace", ""),
                "steps_count": steps_count,
                "crash_screen": crash_screen.strip() if crash_screen else None
            }
            crash_events.append(crash_event)
        return crash_events

    def _parse_anr_events_with_screenshots(self: "BugReportGenerator", content: str) -> List[Dict]:
        """
        Parse ANR events from crash-dump.log content with screenshot mapping

        Args:
            content: Content of crash-dump.log file

        Returns:
            List[Dict]: List of ANR event dictionaries with screenshot information
        """
        anr_events = []

        for steps_count, crash_screen, timestamp_str, anr_content in self._iter_crash_info(content, ANR_PATTERN):
            # Extract ANR information
            anr_info = self._extract_anr_info(anr_content)
            anr_event = {
                "time": timestamp_str,
                "reason": anr_info.get("reason", "Unknown"),
                "process": anr_info.get("process", "Unknown"),
                "trace": anr_info.get("trace", ""),
                "steps_count": steps_count,
                "crash_screen": crash_screen.strip() if crash_screen else None
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

class PathParserMixin:

    _data_path: DataPath = None
    
    @property
    def data_path(self: "BugReportGenerator"):
        if not self._data_path:
            self._setup_paths()
        return self._data_path
    
    def _setup_paths(self: "BugReportGenerator"):
        """
        Setup paths for a given result directory

        Args:
            result_dir: Directory path containing test results
        """ 
        if self.config:
            self.log_stamp = self.config.get("log_stamp", "")
                
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

        self._data_path: DataPath = DataPath(
            output_dir=output_dir,
            steps_log=output_dir / "steps.log",
            coverage_log=output_dir / "coverage.log",
            screenshots_dir=output_dir / "screenshots",
            crash_dump_log=output_dir / "crash-dump.log",
            property_exec_info=property_exec_info_file,
            result_json=result_file,
        )


class ScreenshotsMixin:

    _take_screenshots: bool = None
    _all_screenshot_names = set()
    
    @property
    def take_screenshots(self: "BugReportGenerator") -> bool:
        """Whether the `--take-screenshots` enabled. Should we report the screenshots?

        Returns:
            bool: Whether the `--take-screenshots` enabled.
        """
        if self._take_screenshots is None:
            self._take_screenshots = self.data_path.screenshots_dir.exists()
        return self._take_screenshots

    @catchException("Error when marking screenshot")
    def _mark_screenshot(self: "BugReportGenerator", step_data: "StepData"):
        step_type = step_data["Type"]
        screenshot_name = step_data["Screenshot"]
        if not screenshot_name:
            return
        info = step_data.get("Info")
        if not isinstance(info, dict):
            return

        if step_type == "Monkey":
            act = info.get("act")
            pos = info.get("pos")
            if act in ["CLICK", "LONG_CLICK"] or act.startswith("SCROLL"):
                self._mark_screenshot_interaction(step_type, screenshot_name, act, pos)

        elif step_type == "Script":
            act = info.get("method")
            pos = info.get("params")
            if act in ["click", "setText", "swipe"]:
                self._mark_screenshot_interaction(step_type, screenshot_name, act, pos)

    def _mark_screenshot_interaction(
            self: "BugReportGenerator",
            step_type: str, screenshot_name: str, action_type: str, position: Union[List, Tuple]
        ) -> bool:
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
    
    def _add_screenshot_info(
        self: "BugReportGenerator",
        step_data: "StepData",
        step_id: str,
        data: Dict,
        force_append: bool = False,
    ):
        """
        Add screenshot information to data structure

        Args:
            step_data: data for the current step
            step_index: Current step index
            data: Data dictionary to update
        """
        screenshot_name = step_data["Screenshot"]
        if screenshot_name in self._all_screenshot_names:
            return
        self._all_screenshot_names.add(screenshot_name)

        caption = ""
        info = step_data.get("Info")

        if step_data["Type"] == "Monkey":
            # Extract 'act' attribute for Monkey type and add MonkeyStepsCount
            if isinstance(info, dict):
                action = info.get('act', 'N/A')
            else:
                action = str(info) if info else 'N/A'
            caption = f"Monkey Step: {action}"
        elif step_data["Type"] == "Script":
            # Extract 'method' attribute for Script type
            if isinstance(info, dict):
                caption = f"{info.get('method', 'N/A')}"
            else:
                caption = str(info) if info else "N/A"
        elif step_data["Type"] == "ScriptInfo":
            # Extract 'propName' and 'state' attributes for ScriptInfo type
            if isinstance(info, dict):
                prop_name = info.get('propName', '')
                state = info.get('state', 'N/A')
            else:
                prop_name = ''
                state = str(info) if info else 'N/A'
            caption = f"{prop_name}: {state}" if prop_name else f"{state}"
        elif step_data["Type"] == "Fuzz":
            caption = f"Monkey Step: Fuzz"


        # Check if the screenshot file actually exists
        screenshot_file_path = self.data_path.screenshots_dir / screenshot_name
        if not screenshot_file_path.exists():
            # Skip adding this screenshot if the file doesn't exist
            return

        if hasattr(self, "_screenshot_id_by_filename"):
            self._screenshot_id_by_filename[screenshot_name] = str(step_id)

        # Use relative path string instead of Path object
        abs_screenshots_path = self.data_path.output_dir / "screenshots" / screenshot_name
        relative_screenshot_path = str(abs_screenshots_path.relative_to(self.result_dir))

        if screenshot_name not in data["screenshot_info"]:
            data["screenshot_info"][screenshot_name] = {
                "type": step_data["Type"],
                "caption": caption,
                "step_index": step_id
            }
        elif not force_append:
            return

        self.screenshots.append({
            'id': step_id,
            'path': relative_screenshot_path,  # Now using string path
            'caption': f"{step_id}. {caption}"
        })
