from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import httpx
import pytest


DEFAULT_TIMEOUT = float(os.getenv("API_TEST_TIMEOUT", "30"))
DEFAULT_UPLOAD_TIMEOUT = float(os.getenv("API_TEST_UPLOAD_TIMEOUT", "660"))
DEFAULT_BASE_URL = os.getenv("API_BASE_URL", "https://example.invalid")


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


@pytest.fixture(scope="session")
def base_url() -> str:
    return DEFAULT_BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def timeout() -> float:
    return DEFAULT_TIMEOUT


@pytest.fixture(scope="session")
def client(base_url: str, timeout: float) -> httpx.Client:
    with httpx.Client(base_url=base_url, timeout=timeout, follow_redirects=True) as c:
        yield c


@pytest.fixture(scope="session")
def username() -> str:
    value = os.getenv("API_TEST_USERNAME")
    if not value:
        pytest.skip("API_TEST_USERNAME is not set; skipping authenticated production smoke tests.")
    return value


@pytest.fixture(scope="session")
def password() -> str:
    value = os.getenv("API_TEST_PASSWORD")
    if not value:
        pytest.skip("API_TEST_PASSWORD is not set; skipping authenticated production smoke tests.")
    return value


@pytest.fixture(scope="session")
def write_tests_enabled() -> bool:
    return _truthy(os.getenv("API_ENABLE_WRITE_TESTS"))


@pytest.fixture(scope="session")
def receipt_file() -> Path:
    value = os.getenv("API_TEST_RECEIPT_FILE")
    if not value:
        pytest.skip("API_TEST_RECEIPT_FILE is not set; skipping upload tests.")
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        pytest.skip(f"API_TEST_RECEIPT_FILE does not exist: {path}")
    return path


@pytest.fixture(scope="session")
def login_payload(username: str, password: str) -> Dict[str, str]:
    return {"username": username, "password": password}


def extract_token_bundle(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise AssertionError(f"Expected dict payload, got {type(payload)!r}")

    candidates = [payload]
    data = payload.get("data")
    if isinstance(data, dict):
        candidates.append(data)

    for candidate in candidates:
        access_token = candidate.get("access_token")
        refresh_token = candidate.get("refresh_token")
        token_type = candidate.get("token_type")
        if access_token and refresh_token and token_type:
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": token_type,
            }

    raise AssertionError(
        "Could not find access_token / refresh_token / token_type in response payload. "
        f"Payload was: {payload}"
    )


@pytest.fixture(scope="session")
def token_bundle(client: httpx.Client, login_payload: Dict[str, str]) -> Dict[str, Any]:
    response = client.post("/login", data=login_payload)
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload.get("success") is True, payload
    assert payload.get("code") == "success", payload
    return extract_token_bundle(payload)


@pytest.fixture(scope="session")
def auth_headers(token_bundle: Dict[str, Any]) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token_bundle['access_token']}"}


@pytest.fixture(scope="session")
def upload_timeout() -> float:
    return DEFAULT_UPLOAD_TIMEOUT
