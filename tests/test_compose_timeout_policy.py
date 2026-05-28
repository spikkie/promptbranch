from pathlib import Path


def test_chatgpt_service_compose_uses_current_image_tag_and_long_response_timeout() -> None:
    text = Path("docker-compose.chatgpt-service.yml").read_text(encoding="utf-8")

    assert "image: promptbranch-service:0.0.278.12" in text
    assert "CHATGPT_RESPONSE_TIMEOUT_MS: ${CHATGPT_RESPONSE_TIMEOUT_MS:-1200000}" in text

