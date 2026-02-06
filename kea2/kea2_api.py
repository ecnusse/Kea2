from typing import Optional, List, Callable, Any, Union, Dict
from pathlib import Path
import unittest
import os
import inspect
from .keaUtils import KeaTestRunner, Options
from .u2Driver import U2Driver
from .utils import getLogger, TimeStamp, setCustomProjectRoot
from .adbUtils import ADBDevice

logger = getLogger(__name__)


class Kea2Tester:
    """
    Kea2 property tester
    
    This class allows users to directly launch Kea2 property tests in existing test scripts.
    
    Environment Variables:
        KEA2_HYBRID_MODE: Controls whether to enable Kea2 testing
            - "kea2": Enable Kea2 testing, trigger a breakpoint after testing is completed
            - Other values or not set: Skip Kea2 testing, continue executing the original script
            
    """
    
    def __init__(self):
        self.options: Optional[Options] = None
        self.properties: List[unittest.TestCase] = []
        self._caller_info: Optional[Dict[str, str]] = None
    
    def run_kea2_testing(self, option: Options, configs_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        Launch kea2 property test
        
        Args:
            option: Kea2 and Fastbot configuration options
            configs_path: Your configs directory (absolute or relative path)
        
        Returns:
            dict: Test result dictionary containing the following keys:
                - executed (bool): Whether Kea2 testing was executed
                - skipped (bool): Whether Kea2 testing was skipped (KEA2_HYBRID_MODE != kea2)
                - caller_info (Dict|None): Caller information (file, class, method name)
                - output_dir (Path|None): Test output directory
                - bug_report (Path|None): Bug report HTML file path
                - result_json (Path|None): Test result JSON file path
                - log_file (Path|None): Fastbot log file path
        
        """

        self._caller_info = self._get_caller_info()
        
        logger.info("Starting Kea2 property testing...")
        logger.info(f"Kea2 test launch location:")
        if self._caller_info:
            logger.info(f"   File: {self._caller_info['file']}")
            logger.info(f"   Class: {self._caller_info['class']}")
            logger.info(f"   Method: {self._caller_info['method']}")

        self.options = option
        if self.options is None:
            raise ValueError("Please set up the option config first.")

        from kea2.utils import getProjectRoot
        previous_root = getProjectRoot()
        if configs_path is not None:
            configs_dir = Path(configs_path).expanduser() 
            if not configs_dir.exists() or not configs_dir.is_dir():
                raise FileNotFoundError(f"Configs directory not found in the specified path: {configs_dir}")
            else:
                setCustomProjectRoot(configs_path)
        
        KeaTestRunner.setOptions(self.options)
        argv = ["python3 -m unittest"] + self.options.propertytest_args
        
        logger.info("Starting Kea2 property test...")
        runner = KeaTestRunner()
        unittest.main(module=None, argv=argv, testRunner=runner, exit=False)
        logger.info("Kea2 property test completed.")

        if configs_path is not None:
            setCustomProjectRoot(previous_root)
        
        result = self._build_test_result()
        
        return result
    
    def _build_test_result(self) -> Dict[str, Any]:
        """
        build test result dict
        
        Returns:
            dict: Dictionary containing output directory and paths to various report files
        """
        if self.options is None:
            return {
                'executed': False,
                'skipped': False,
                'caller_info': self._caller_info,
                'output_dir': None,
                'bug_report': None,
                'result_json': None,
                'log_file': None
            }
        
        output_dir = self.options.output_dir
        
        from .utils import StampManager
        
        bug_report_path = output_dir / "bug_report.html"
        stamp_manager = StampManager()
        stamp = stamp_manager.stamp or self.options.log_stamp
        result_name = stamp_manager.result_file.name if stamp_manager.result_file else f"result_{stamp}.json"
        log_name = stamp_manager.log_file.name if stamp_manager.log_file else f"fastbot_{stamp}.log"
        result_json_path = output_dir / result_name
        log_file_path = output_dir / log_name
        
        return {
            'executed': True,
            'skipped': False,
            'caller_info': self._caller_info,
            'output_dir': output_dir,
            'bug_report': bug_report_path if bug_report_path.exists() else None,
            'result_json': result_json_path if result_json_path.exists() else None,
            'log_file': log_file_path if log_file_path.exists() else None
        }
    
    def _get_caller_info(self) -> Dict[str, str]:
        """
        Get caller information (file, class, method name)
        
        Returns:
            dict: Dictionary containing file, class, method
        """
        try:
            frame = inspect.currentframe()
            caller_frame = frame.f_back.f_back
            
            while caller_frame:
                frame_info = inspect.getframeinfo(caller_frame)
                if 'kea2_api.py' not in frame_info.filename:
                    # find caller
                    file_path = frame_info.filename
                    method_name = frame_info.function
                    
                    # get class name
                    class_name = None
                    if 'self' in caller_frame.f_locals:
                        class_name = caller_frame.f_locals['self'].__class__.__name__
                    
                    return {
                        'file': file_path,
                        'class': class_name or 'N/A',
                        'method': method_name
                    }
                caller_frame = caller_frame.f_back
            
            return {
                'file': 'Unknown',
                'class': 'N/A',
                'method': 'Unknown'
            }
        except Exception as e:
            logger.warning(f"Failed to get caller info: {e}")
            return {
                'file': 'Unknown',
                'class': 'N/A',
                'method': 'Unknown'
            }
