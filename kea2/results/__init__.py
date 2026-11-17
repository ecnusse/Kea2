"""Read-only, structured views of existing Kea2 test results."""

from .service import ResultError, ResultSnapshot

__all__ = ["ResultError", "ResultSnapshot"]
