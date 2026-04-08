import pytest


pytestmark = pytest.mark.skip(
    reason=(
        "2FA tests are intentionally disabled for production verification. "
        "They mutate user state and should only be reintroduced as dedicated opt-in integration tests."
    )
)
