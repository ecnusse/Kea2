import os
import time
import errno
import random
import threading

class LockTimeoutError(Exception):
    pass

class FileLock:
    """Simple cross-platform exclusive lock with per-thread reentrancy.

    Usage:
        with FileLock(path, timeout=10.0, poll_interval=0.1):
            # exclusive section

    Implementation:
    - If `portalocker` is available it will use that for advisory file locking.
    - Otherwise falls back to an atomic mkdir-based lock (create a directory '<path>.lockdir').
    - Reentrancy: a thread that already holds the lock can re-enter without blocking.
    """
    # thread-local storage to track held locks: mapping lock_id -> {'count': int, 'lockfile': file obj or None}
    _local = threading.local()

    def __init__(self, path, timeout=10.0, poll_interval=0.1):
        self.target = os.fspath(path)
        self.timeout = float(timeout)
        self.poll_interval = float(poll_interval)
        self._use_portalocker = False
        self._portalocker = None
        self._lockfile = None
        self._lockdir = None
        try:
            import portalocker  # type: ignore
            self._portalocker = portalocker
            self._use_portalocker = True
        except Exception:
            self._portalocker = None
            self._use_portalocker = False
        # Normalize lock id
        self._lock_id = os.path.abspath(self.target)

    def __enter__(self):
        if not hasattr(FileLock._local, 'held'):
            FileLock._local.held = {}
        held = FileLock._local.held
        # Reentrant: if we already hold this lock in this thread, increment counter and return
        if self._lock_id in held:
            held[self._lock_id]['count'] += 1
            return self

        deadline = time.time() + self.timeout
        if self._use_portalocker:
            lock_path = self.target if os.path.isdir(self.target) else (self.target + '.lockfile')
            parent = os.path.dirname(lock_path) or '.'
            try:
                os.makedirs(parent, exist_ok=True)
            except Exception:
                pass
            # open lock file
            lf = open(lock_path, 'a+b')
            while True:
                try:
                    self._portalocker.lock(lf, self._portalocker.LockFlags.EXCLUSIVE | self._portalocker.LockFlags.NON_BLOCKING)
                    # record in thread-local
                    held[self._lock_id] = {'count': 1, 'lockfile': lf, 'lockdir': None}
                    return self
                except Exception:
                    if time.time() > deadline:
                        try:
                            lf.close()
                        except Exception:
                            pass
                        raise LockTimeoutError(f"Timeout acquiring portalocker on {lock_path}")
                    time.sleep(self.poll_interval + random.random() * 0.01)
        else:
            lockdir = (self.target + '.lockdir') if not str(self.target).endswith('.lockdir') else self.target
            while True:
                try:
                    os.mkdir(lockdir)
                    try:
                        with open(os.path.join(lockdir, 'owner'), 'w') as f:
                            f.write(f"{os.getpid()}\n{time.time()}\n")
                    except Exception:
                        pass
                    held[self._lock_id] = {'count': 1, 'lockfile': None, 'lockdir': lockdir}
                    return self
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise
                    if time.time() > deadline:
                        raise LockTimeoutError(f"Timeout acquiring mkdir lock on {lockdir}")
                    time.sleep(self.poll_interval + random.random() * 0.01)

    def __exit__(self, exc_type, exc, tb):
        held = getattr(FileLock._local, 'held', None)
        if not held or self._lock_id not in held:
            # nothing to release
            return
        entry = held[self._lock_id]
        entry['count'] -= 1
        if entry['count'] > 0:
            return
        # count reached zero: release underlying OS lock
        if entry.get('lockfile'):
            try:
                self._portalocker.unlock(entry['lockfile'])
            except Exception:
                pass
            try:
                entry['lockfile'].close()
            except Exception:
                pass
        else:
            lockdir = entry.get('lockdir')
            if lockdir:
                try:
                    owner = os.path.join(lockdir, 'owner')
                    if os.path.exists(owner):
                        try:
                            os.remove(owner)
                        except Exception:
                            pass
                    os.rmdir(lockdir)
                except Exception:
                    # best-effort cleanup only
                    pass
        try:
            del held[self._lock_id]
        except Exception:
            pass
