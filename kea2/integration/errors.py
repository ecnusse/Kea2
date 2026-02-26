from dataclasses import dataclass


@dataclass
class EngineErrorDetail:
    """Structured error payload for integration failures.

    Attributes:
        code: Stable error code string.
        message: Human-readable error message.
    """
    code: str
    message: str


class EngineIntegrationError(RuntimeError):
    def __init__(self, code: str, message: str):
        """Create an integration error with a stable code and message.

        Args:
            code: Stable error code string.
            message: Human-readable error message.
        """
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self):
        """Serialize error fields for JSON responses.

        Returns:
            payload: Dict with code and message.
        """
        return {"code": self.code, "message": self.message}
