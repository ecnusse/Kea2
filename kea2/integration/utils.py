from .errors import EngineIntegrationError


def ensure_positive_int(name: str, value: int) -> None:
    if not isinstance(value, int) or value <= 0:
        raise EngineIntegrationError("INVALID_CONFIG", f"{name} must be a positive integer")
