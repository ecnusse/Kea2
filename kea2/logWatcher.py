import re
import os
import threading
import time

from typing import IO
from .utils import getLogger


logger = getLogger(__name__)

PATTERN_EXCEPTION = re.compile(r"\[Fastbot\].+Internal\serror\n(?P<exception_body>[\s\S]*)")
PATTERN_STATISTIC = re.compile(r".+Monkey\sis\sover!\n([\s\S]+)")
PATTERN_ANR = re.compile(
    r"(?:\[Fastbot\]\*\*\* ERROR \*\*\* NOT RESPONDING: (?P<pkg>[\w.]+) \(pid \d+\)\n)?"
    r"\[Fastbot\]\*\*\* ERROR \*\*\* ANR in (?P<anr_pkg>[\w.]+) \((?P<activity>[^)]+)\)"
)
# [Fastbot]*** ERROR *** // CRASH: com.example.crash (pid 31624) (elapsed nanos: 81531020643808)
PATTERN_CRASH = re.compile(r"\[Fastbot\]\*\*\* ERROR \*\*\* // CRASH: (?P<crash_pkg>[\w.]+) \(pid \d+\) .*")
PATTERN_CRASH_AND_ANR = re.compile(r"App appears\s+(?P<crash>\d+)\s+crash,\s+(?P<anr>\d+)\s+anr")


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
        if not buffer:
            return

        # Keep a short tail so cross-chunk markers are still detectable.
        tail_buffer = getattr(self, "_tail_buffer", "")
        tail_size = getattr(self, "_tail_size", 4096)
        parse_buffer = tail_buffer + buffer
        self.parse_log(parse_buffer)
        self._tail_size = tail_size
        self._tail_buffer = parse_buffer[-tail_size:]

    def parse_log(self, content):
        if not content or "[Fastbot]" not in content:
            return

        if "Internal error" in content:
            exception_match = PATTERN_EXCEPTION.search(content)
            if exception_match:
                exception_body = exception_match.group("exception_body").strip()
                if exception_body:
                    raise RuntimeError(
                        "[Error] Fatal Execption while running fastbot:\n" +
                        exception_body +
                        f"\nSee {self.log_file} for details."
                    )

        if "[Fastbot]*** ERROR *** ANR" in content:
            anr_match = PATTERN_ANR.search(content)
            if anr_match:
                package = anr_match.group("anr_pkg") or anr_match.group("pkg") or "unknown"
                activity = anr_match.group("activity") or "unknown"
                print(
                    "[INFO] ANR detected while running fastbot:\n"
                    f"package: {package}, activity: {activity}",
                    flush=True
                )

        if "[Fastbot]*** ERROR *** // CRASH:" in content:
            crash_match = PATTERN_CRASH.search(content)
            if crash_match:
                crash_pkg = crash_match.group("crash_pkg") or "unknown"
                print(
                    "[INFO] Crash detected while running fastbot:\n"
                    f"package: {crash_pkg}",
                    flush=True
                )
        
        if (not getattr(self, "statistic_printed", False)) and "Monkey is over!" in content:
            statistic_match = PATTERN_STATISTIC.search(content)
            if statistic_match:
                statistic_body = statistic_match.group(1).strip()
                if statistic_body:
                    self.statistic_printed = True
                    print(
                        "[INFO] Fastbot exit:\n" +
                        statistic_body,
                        flush=True
                    )
            crash_anr_match = PATTERN_CRASH_AND_ANR.search(content)
            if crash_anr_match:
                crash_count = int(crash_anr_match.group("crash"))
                anr_count = int(crash_anr_match.group("anr"))
                if crash_count > 0 or anr_count > 0:
                    self.has_crash_or_anr = True

    def __init__(self, log_file):
        logger.info(f"Watching log: {log_file}")
        self.log_file = log_file
        self.end_flag = False
        self.statistic_printed = False
        self.has_crash_or_anr = False
        self.crash_count = 0
        self.anr_count = 0
        self._tail_size = 4096
        self._tail_buffer = ""

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
    pass
