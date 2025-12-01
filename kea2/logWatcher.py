import re
import os
import threading
import time

from typing import IO
from .utils import getLogger


logger = getLogger(__name__)

PATTERN_EXCEPTION = re.compile(r"\[Fastbot\].+Internal\serror\n([\s\S]*)")
PATTERN_STATISTIC = re.compile(r".+Monkey\sis\sover!\n([\s\S]+)")


def thread_excepthook(args):
    print(args.exc_value, flush=True)
    os._exit(1)


class LogWatcher:

    def watcher(self, poll_interval=3):
        self.last_pos = 0

        with open(self.log_file, "r", encoding="utf-8") as fp:
            while not self.end_flag:
                self.read_log(fp)
                time.sleep(poll_interval)
            
            time.sleep(0.2)
            self.read_log(fp)
        
    def read_log(self, f: IO):
        f.seek(self.last_pos)
        buffer = f.read()
        self.last_pos = f.tell()

        self.parse_log(buffer)

    def parse_log(self, content):
        exception_match = PATTERN_EXCEPTION.search(content)
        if exception_match:
            exception_body = exception_match.group(1).strip()
            if exception_body:
                raise RuntimeError(
                    "[Error] Fatal Execption while running fastbot:\n" + 
                    exception_body + 
                    f"\nSee {self.log_file} for details."
                )
        
        statistic_match = PATTERN_STATISTIC.search(content)
        if statistic_match and not self.statistic_printed:
            statistic_body = statistic_match.group(1).strip()
            if statistic_body:
                self.statistic_printed = True
                print(
                    "[INFO] Fastbot exit:\n" + 
                    statistic_body
                , flush=True)

    def __init__(self, log_file):
        logger.info(f"Watching log: {log_file}")
        self.log_file = log_file
        self.end_flag = False
        self.statistic_printed = False

        threading.excepthook = thread_excepthook
        self.t = threading.Thread(target=self.watcher, daemon=True)
        self.t.start()
    
    def close(self):
        logger.info("Close: LogWatcher")
        self.end_flag = True
        if self.t:
            self.t.join()
        
        if not self.statistic_printed:
            self._parse_whole_log()
    
    def _parse_whole_log(self):
        logger.warning(
            "LogWatcher closed without reading the statistics, parsing the whole log now."
        )
        with open(self.log_file, "r", encoding="utf-8") as fp:
            content = fp.read()
            self.parse_log(content)


if __name__ == "__main__":
    # LogWatcher()
    pass