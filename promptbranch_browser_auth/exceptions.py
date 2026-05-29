class AuthenticationError(RuntimeError):
    """Raised when authentication cannot be completed."""


class ManualLoginRequiredError(AuthenticationError):
    """Raised when a visible browser is required to complete login."""




class AuthChallengeRequiredError(AuthenticationError):
    """Raised when login reaches a provider challenge that automation must not bypass."""

    def __init__(
        self,
        message: str,
        *,
        challenge_type: str = "unknown",
        page_url: str | None = None,
        page_title: str | None = None,
        text_preview: str | None = None,
        artifact_paths: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.challenge_type = challenge_type
        self.page_url = page_url
        self.page_title = page_title
        self.text_preview = text_preview
        self.artifact_paths = artifact_paths or {}

    def to_payload(self) -> dict:
        return {
            "ok": False,
            "status": "auth_challenge_required",
            "error": str(self),
            "error_type": type(self).__name__,
            "timeout_layer": "authentication",
            "challenge_type": self.challenge_type,
            "manual_action_required": True,
            "page_url": self.page_url,
            "page_title": self.page_title,
            "text_preview": self.text_preview,
            "artifact_paths": self.artifact_paths,
        }


class ResponseTimeoutError(TimeoutError):
    """Raised when ChatGPT did not produce the expected output in time."""


class BotChallengeError(AuthenticationError):
    """Raised when ChatGPT/Cloudflare challenge blocks the browser before app load."""


class UnsupportedOperationError(RuntimeError):
    """Raised when the current ChatGPT UI does not expose the requested action."""



class BrowserContextUnavailableError(RuntimeError):
    """Raised when the browser persistent context cannot be launched or recovered."""

    def __init__(self, message: str, *, payload: dict | None = None) -> None:
        super().__init__(message)
        self.payload = payload or {}

    def to_payload(self) -> dict:
        payload = dict(self.payload)
        payload.setdefault("ok", False)
        payload.setdefault("status", "browser_launch_failed")
        payload.setdefault("error", str(self))
        payload.setdefault("error_type", type(self).__name__)
        payload.setdefault("timeout_layer", "browser_launch")
        return payload


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
