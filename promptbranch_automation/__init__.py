from .automation import ChatGPTAutomation, ask_chatgpt
from promptbranch_browser_auth.exceptions import (
    AuthenticationError,
    ManualLoginRequiredError,
    ResponseTimeoutError,
)

__all__ = [
    "AuthenticationError",
    "ChatGPTAutomation",
    "ManualLoginRequiredError",
    "ResponseTimeoutError",
    "ask_chatgpt",
]

from .service import ChatGPTAutomationService, ChatGPTAutomationSettings
