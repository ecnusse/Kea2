"""Compatibility alias for the shared task store."""
import sys
from kea2 import task_store as _shared
sys.modules[__name__] = _shared
