import os
import logging
import traceback
import time

from pathlib import Path
from functools import wraps
from typing import Callable, Dict, Optional, Union
from unittest import TestCase


def singleton(cls):
    _instance = {}

    def inner():
        if cls not in _instance:
            _instance[cls] = cls()
        return _instance[cls]
    return inner


class LoggingLevel:
    level = logging.INFO
    _instance: Optional["LoggingLevel"] = None  # 单例缓存

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def set_level(cls, level: int):
        cls.level = level


class DynamicLevelFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= LoggingLevel.level


def getLogger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    def enable_pretty_logging():
        if not logger.handlers:
            # Configure handler
            handler = logging.StreamHandler()
            handler.flush = lambda: handler.stream.flush()
            handler.setFormatter(logging.Formatter('[%(levelname)1s][%(asctime)s %(module)s:%(lineno)d pid:%(process)d] %(message)s'))
            handler.setLevel(logging.NOTSET)
            handler.addFilter(DynamicLevelFilter())
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
            logger.propagate = False

    enable_pretty_logging()
    return logger


logger = getLogger(__name__)




@singleton
class TimeStamp:
    time_stamp = None

    def getTimeStamp(cls):
        if cls.time_stamp is None:
            import datetime
            cls.time_stamp = datetime.datetime.now().strftime('%Y%m%d%H_%M%S%f')
        return cls.time_stamp
    
    def getCurrentTimeStamp(cls):
        import datetime
        return datetime.datetime.now().strftime('%Y%m%d%H_%M%S%f')


@singleton
class StampManager:
    stamp: Optional[str] = None
    output_dir: Optional[Path] = None

    def set_stamp(self, stamp: str):
        self.stamp = stamp

    def set_output_dir(self, output_dir: Path):
        self.output_dir = Path(output_dir)

    @property
    def log_file_name(self) -> Optional[str]:
        if not self.stamp:
            return None
        return f"fastbot_{self.stamp}.log"

    @property
    def result_file_name(self) -> Optional[str]:
        if not self.stamp:
            return None
        return f"result_{self.stamp}.json"

    @property
    def prop_exec_file_name(self) -> Optional[str]:
        if not self.stamp:
            return None
        return f"property_exec_info_{self.stamp}.json"

    @property
    def log_file(self) -> Optional[Path]:
        if not self.output_dir or not self.log_file_name:
            return None
        return Path(self.output_dir) / self.log_file_name

    @property
    def result_file(self) -> Optional[Path]:
        if not self.output_dir or not self.result_file_name:
            return None
        return Path(self.output_dir) / self.result_file_name

    @property
    def prop_exec_file(self) -> Optional[Path]:
        if not self.output_dir or not self.prop_exec_file_name:
            return None
        return Path(self.output_dir) / self.prop_exec_file_name

from uiautomator2 import Device
d = Device


_CUSTOM_PROJECT_ROOT: Optional[Path] = None


def setCustomProjectRoot(configs_path: Optional[Union[str, Path]]):
    """
    Set a custom project root directory (containing the configs directory). Passing None can restore the default behavior.
    """
    global _CUSTOM_PROJECT_ROOT

    if configs_path is None:
        _CUSTOM_PROJECT_ROOT = None
        return

    candidate = Path(configs_path).expanduser()
    if candidate.name == "configs":
        candidate = candidate.parent

    candidate = candidate.resolve()
    _CUSTOM_PROJECT_ROOT = candidate


def getProjectRoot():
    if _CUSTOM_PROJECT_ROOT:
        return _CUSTOM_PROJECT_ROOT

    root = Path(Path.cwd().anchor)
    cur_dir = Path.absolute(Path(os.curdir))
    while not os.path.isdir(cur_dir / "configs"):
        if cur_dir == root:
            return None
        cur_dir = cur_dir.parent
    return cur_dir


def timer(log_info: str=None):
    """ ### Decorator to measure the execution time of a function.

    This decorator can be used to wrap functions where you want to log the time taken for execution
    
    ### Usage:
        - @timer("Function execution took %cost_time seconds.")
        - @timer()  # If no log_info is provided, it will print the function name and execution time.
    
    `%cost_time` will be replaced with the actual time taken for execution.
    """
    def accept(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            if log_info:
                logger.info(log_info.replace(r"%cost_time", f"{end_time - start_time:.4f}"))
            else:
                logger.info(f"Function '{func.__name__}' executed in {(end_time - start_time):.4f} seconds.")
            return result
        return wrapper
    return accept


def catchException(log_info: str):
    """ ### Decorator to catch exceptions and print log info.

    This decorator can be used to wrap functions that may raise exceptions,
    allowing you to log a message when the exception is raised.

    ### Usage:
        - @catchException("An error occurred in the function ****.")
    """
    def accept(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.info(log_info)
                tb = traceback.format_exception(type(e), e, e.__traceback__.tb_next)
                print(''.join(tb), end='', flush=True)
        return wrapper
    return accept


def loadFuncsFromFile(file_path: str) -> Dict[str, Callable]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} not found.")

    def __get_module():
        import importlib.util
        module_name = Path(file_path).stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    mod = __get_module()

    import inspect
    funcs = dict()
    for func_name, func in inspect.getmembers(mod, inspect.isfunction):
        funcs[func_name] = func

    return funcs


def getClassName(clazz):
    return f'%s.%s' % (clazz.__module__, clazz.__qualname__)

def getFullPropName(testCase: TestCase):
    return f"%s.%s" % (getClassName(testCase.__class__), testCase._testMethodName)
