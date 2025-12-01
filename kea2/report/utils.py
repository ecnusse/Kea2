from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

@contextmanager
def thread_pool(max_workers=128, wait=True, name_prefix="worker"):
    executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=name_prefix)
    try:
        yield executor
    finally:
        executor.shutdown(wait=wait)