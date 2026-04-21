from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence


@dataclass(slots=True)
class ChatGPTBrowserConfig:
    project_url: str
    profile_dir: str
    email: Optional[str] = None
    password: Optional[str] = None
    headless: bool = False
    browser_channel: Optional[str] = None
    no_viewport: Optional[bool] = None
    challenge_wait_timeout_ms: int = 20_000
    use_patchright: bool = True
    navigation_timeout_ms: int = 45_000
    response_timeout_ms: int = 600_000
    manual_login_timeout_ms: int = 600_000
    slow_mo_ms: int = 0
    viewport_width: int = 1440
    viewport_height: int = 1080
    debug: bool = False
    debug_artifact_dir: str = "debug_artifacts"
    save_trace: bool = True
    save_html: bool = True
    save_screenshot: bool = True
    disable_fedcm: bool = True
    filter_no_sandbox: bool = True
    extra_browser_args: Sequence[str] = field(default_factory=tuple)
    min_context_spacing_seconds: float = 8.0
    conversation_history_rate_limit_cooldown_seconds: float = 180.0
    rate_limit_modal_wait_timeout_ms: int = 180_000
    rate_limit_modal_poll_interval_ms: int = 1_000
    clear_singleton_locks: bool = False

    def __post_init__(self) -> None:
        self.profile_dir = str(Path(self.profile_dir).expanduser().resolve())
        self.debug_artifact_dir = str(Path(self.debug_artifact_dir).expanduser().resolve())
        if self.navigation_timeout_ms <= 0:
            raise ValueError("navigation_timeout_ms must be positive")
        if self.response_timeout_ms <= 0:
            raise ValueError("response_timeout_ms must be positive")
        if self.manual_login_timeout_ms <= 0:
            raise ValueError("manual_login_timeout_ms must be positive")
        if self.challenge_wait_timeout_ms <= 0:
            raise ValueError("challenge_wait_timeout_ms must be positive")
        if self.min_context_spacing_seconds < 0:
            raise ValueError("min_context_spacing_seconds must be non-negative")
        if self.conversation_history_rate_limit_cooldown_seconds < 0:
            raise ValueError("conversation_history_rate_limit_cooldown_seconds must be non-negative")
        if self.rate_limit_modal_wait_timeout_ms <= 0:
            raise ValueError("rate_limit_modal_wait_timeout_ms must be positive")
        if self.rate_limit_modal_poll_interval_ms <= 0:
            raise ValueError("rate_limit_modal_poll_interval_ms must be positive")

    @property
    def is_headed(self) -> bool:
        return not self.headless
