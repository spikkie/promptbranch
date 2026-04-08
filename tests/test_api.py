from __future__ import annotations

from pathlib import Path

import httpx
import pytest


REQUIRED_PUBLIC_PATHS = {
    "/": {"get"},
    "/login": {"post"},
    "/token/refresh": {"post"},
    "/protected": {"get"},
    "/receipts": {"get"},
    "/receipt/upload": {"post"},
}


@pytest.mark.production_safe
def test_root_returns_service_message(client: httpx.Client) -> None:
    response = client.get("/")
    assert response.status_code == 200, response.text

    payload = response.json()
    assert isinstance(payload, dict), payload
    assert "message" in payload, payload
    assert "Receipt backend is up" in payload["message"], payload


@pytest.mark.production_safe
def test_openapi_exposes_expected_routes(client: httpx.Client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text

    payload = response.json()
    assert "paths" in payload, payload

    paths = payload["paths"]
    for route, methods in REQUIRED_PUBLIC_PATHS.items():
        assert route in paths, f"Missing route in openapi.json: {route}"
        available = {method.lower() for method in paths[route].keys()}
        missing = methods - available
        assert not missing, f"Route {route} missing methods: {sorted(missing)}"


@pytest.mark.production_safe
def test_login_returns_bearer_tokens(token_bundle: dict) -> None:
    assert token_bundle["access_token"], token_bundle
    assert token_bundle["refresh_token"], token_bundle
    assert str(token_bundle["token_type"]).lower() == "bearer", token_bundle


@pytest.mark.production_safe
def test_protected_route_accepts_bearer_token(
    client: httpx.Client, auth_headers: dict, username: str
) -> None:
    response = client.get("/protected", headers=auth_headers)
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload.get("success") is True, payload
    assert payload.get("code") == "success", payload
    assert username in payload.get("message", ""), payload


@pytest.mark.production_safe
def test_receipts_endpoint_is_reachable_with_auth(
    client: httpx.Client, auth_headers: dict
) -> None:
    response = client.get("/receipts", headers=auth_headers)
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload.get("success") is True, payload
    assert payload.get("code") == "success", payload


@pytest.mark.production_safe
def test_users_endpoint_is_reachable_with_auth(
    client: httpx.Client, auth_headers: dict
) -> None:
    response = client.get("/users", headers=auth_headers)
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload.get("success") is True, payload
    assert payload.get("code") == "success", payload


@pytest.mark.production_safe
def test_refresh_endpoint_is_reachable_with_refresh_token(
    client: httpx.Client, token_bundle: dict
) -> None:
    response = client.post(
        "/token/refresh", json={"refresh_token": token_bundle["refresh_token"]}
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload.get("success") is True, payload
    assert payload.get("code") == "success", payload


@pytest.mark.write_api
def test_receipt_upload_is_available_when_explicitly_enabled(
    client: httpx.Client,
    auth_headers: dict,
    receipt_file: Path,
    write_tests_enabled: bool,
    upload_timeout: float,
) -> None:
    if not write_tests_enabled:
        pytest.skip("Write tests are disabled. Set API_ENABLE_WRITE_TESTS=1 to enable upload testing.")

    with receipt_file.open("rb") as fh:
        files = {"file": (receipt_file.name, fh, "application/octet-stream")}
        response = client.post("/receipt/upload", files=files, headers=auth_headers, timeout=upload_timeout)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("success") in {True, False}, payload
    assert payload.get("code") in {"success", "duplicate"}, payload
