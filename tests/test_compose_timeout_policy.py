from pathlib import Path

from promptbranch_version import PACKAGE_VERSION


def test_chatgpt_service_compose_uses_current_image_tag_and_long_response_timeout() -> None:
    text = Path("docker-compose.chatgpt-service.yml").read_text(encoding="utf-8")

    assert "promptbranch-service:${PROMPTBRANCH_SERVICE_IMAGE_TAG:-local}" in text
    assert "0.1.50.5" not in text
    assert PACKAGE_VERSION not in text
    assert "CHATGPT_RESPONSE_TIMEOUT_MS: ${CHATGPT_RESPONSE_TIMEOUT_MS:-1200000}" in text

