class AuthenticationError(RuntimeError):
    """Raised when authentication cannot be completed."""


class ManualLoginRequiredError(AuthenticationError):
    """Raised when a visible browser is required to complete login."""


class ResponseTimeoutError(TimeoutError):
    """Raised when ChatGPT did not produce the expected output in time."""


class BotChallengeError(AuthenticationError):
    """Raised when ChatGPT/Cloudflare challenge blocks the browser before app load."""


class UnsupportedOperationError(RuntimeError):
    """Raised when the current ChatGPT UI does not expose the requested action."""



class BrowserContextUnavailableError(RuntimeError):
    """Raised when the browser persistent context cannot be launched or recovered."""


class BrowserProfileBusyError(TimeoutError):
    """Raised when the shared browser profile is already owned by another operation."""

    def __init__(
        self,
        message: str,
        *,
        operation_name: str | None = None,
        active_operation: str | None = None,
        waited_seconds: float | None = None,
        retry_after_seconds: float | None = None,
        profile_dir: str | None = None,
    ) -> None:
        super().__init__(message)
        self.operation_name = operation_name
        self.active_operation = active_operation
        self.waited_seconds = waited_seconds
        self.retry_after_seconds = retry_after_seconds
        self.profile_dir = profile_dir

    def to_payload(self) -> dict:
        return {
            "ok": False,
            "status": "browser_profile_busy",
            "error": str(self),
            "error_type": type(self).__name__,
            "operation": self.operation_name,
            "active_operation": self.active_operation,
            "waited_seconds": self.waited_seconds,
            "retry_after_seconds": self.retry_after_seconds,
            "profile_dir": self.profile_dir,
            "timeout_layer": "browser_profile_lock",
            "recovery_hint": "A browser-backed operation is already using the shared profile. Retry after the active operation finishes, or use async job/status support when available.",
        }
