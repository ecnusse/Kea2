from pathlib import Path
import json
from typing import Deque, Set, List, TYPE_CHECKING
from ..utils import catchException

if TYPE_CHECKING:
    from ..keaUtils import Options


try:
    from ..utils import getLogger
except ImportError:
    def getLogger(name):
        import logging
        return logging.getLogger(name)

logger = getLogger(__name__)

class WidgetCoverage:
    AUTO_RESOURCE_ID = "<AUTO>"
    _profile_period: int
    _options: "Options"
    _all_activities: Set[str] = None
    
    def __init__(self, output_dir, options:"Options"=None, profile_period:int=None):
        self.output_dir = Path(output_dir)
        self.steps_log = self.output_dir / "steps.log"
        self.coverage_log = self.output_dir / "widget_coverage.log"
        self._options = options
        self._profile_period = profile_period
    
    @property
    def profile_period(self):
        if not self._profile_period:
            self._profile_period = self.options.profile_period
        return self._profile_period
    
    @property
    def options(self):
        if self._options is None:
            from ..keaUtils import Options
            with open(self.output_dir / "options.json", "r", encoding="utf-8") as f:
                options_data = json.load(f)
            if options_data:
                self._options = Options.from_dict(options_data)
        return self._options
    
    @property
    def all_activities(self) -> Set[str]:
        if self._all_activities is None:
            with open(self.output_dir / "coverage.log") as f:
                line = f.readline()
                data = json.loads(line)
                self._all_activities = set(data["totalActivities"])
        return self._all_activities
                

    def generate_coverage_report(self):
        logger.info(
            f"Generating widget coverage report (profile_period={self.profile_period})..."
        )

        if not self.steps_log.exists():
            raise FileNotFoundError(f"Steps log file not found: {self.steps_log}")

        triggered_widgets, coverage_records = self._analyze_steps(self.profile_period)
        logger.info(f"Total unique widgets triggered: {len(triggered_widgets)}")
        self.__dump_triggered_widgets(triggered_widgets)
        self.__dump_coverage_log(coverage_records)

    def __dump_triggered_widgets(self, triggered_widgets: Set[str]):
        output_file = self.output_dir / "widget_coverage_report.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.writelines(f"{w}\n" for w in triggered_widgets)

    def __dump_coverage_log(self, records: List[dict]):
        with open(self.coverage_log, "w", encoding="utf-8") as f:
            f.writelines(f"{w}\n" for w in records)

    def _analyze_steps(self, profile_period: int):
        triggered_widgets: Set[str] = set()
        coverage_records: List[dict] = []

        last_recorded_step = -1
        final_steps_count = None  # track the last steps count seen

        def __record_coverage(steps_count: int):
            coverage_records.append(
                json.dumps({
                    "stepsCount": steps_count,
                    "coverage": len(triggered_widgets),
                })
            )
        
        with open(self.steps_log, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if data.get("Type") == "Monkey":
                    widget_repr = self.__get_widget_repr(data)
                    if widget_repr:
                        triggered_widgets.add(widget_repr)
                steps_count = int(data.get("MonkeyStepsCount", 0))
                final_steps_count = steps_count

                if steps_count % profile_period == 0:
                    __record_coverage(steps_count)
                    last_recorded_step = steps_count

            # Record the last step; avoid duplicate if it's already recorded at a period boundary.
            if (
                final_steps_count
                and final_steps_count != last_recorded_step
            ):
                __record_coverage(final_steps_count)

        return triggered_widgets, coverage_records
    
    def is_activity_in_target_packages(self, activity: str) -> bool:
        if self.all_activities:
            return activity in self.all_activities
        # Fallback
        # Check if activity matches any of the specified package names
        # filter out irrelevant widgets (not in the target packages)
        for pkg in self.options.packageNames:
            if pkg in activity:
                return True
            pkg_name_from_activity = ".".join(_ for _ in activity.split(".") if "activity" not in _.lower())
            if pkg_name_from_activity in pkg:
                return True
        return False

    @catchException("Error getting widget representation")
    def __get_widget_repr(self, data):
        activity: str = data.get("Activity", "")
        if not activity:
            return ""
         
        if not self.is_activity_in_target_packages(activity):
            return ""

        info_str = data.get("Info", "")
        if not info_str:
            return ""
        
        act_info = json.loads(info_str)

        if act_info.get("act") == "BACK":
            return (
                f"activity:{activity}"
                f"|class:KEY_BACK"
                f"|resourceId:KEY_BACK"
                f"|content-desc:KEY_BACK|"
            )

        widget_str = act_info.get("widget", "")
        if not widget_str or widget_str == "":
            return ""

        act_widget = json.loads(widget_str)

        className = act_widget.get("class", "")
        resource_id = act_widget.get("resource-id", "")
        description = act_widget.get("content-desc", "")

        if not any((className, resource_id, description)):
            return ""

        normalized_res_id = self.__normalize_resource_id(resource_id)

        widget_repr = (
            f"activity:{activity}"
            f"|class:{className}"
            f"|resourceId:{normalized_res_id}"
            f"|content-desc:{description}|"
        )
        return widget_repr

    def __normalize_resource_id(self, resource_id: str) -> str:
        if not resource_id:
            return ""

        if ":" in resource_id or "/" in resource_id:
            return resource_id

        return self.AUTO_RESOURCE_ID
