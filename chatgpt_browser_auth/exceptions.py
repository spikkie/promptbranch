class AuthenticationError(RuntimeError):
    """Raised when authentication cannot be completed."""


class ManualLoginRequiredError(AuthenticationError):
    """Raised when a visible browser is required to complete login."""


class ResponseTimeoutError(TimeoutError):
    """Raised when ChatGPT did not produce the expected output in time."""


class BotChallengeError(AuthenticationError):
    """Raised when ChatGPT/Cloudflare challenge blocks the browser before app load."""
