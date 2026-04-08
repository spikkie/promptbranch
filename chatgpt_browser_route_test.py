from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx


DEFAULT_BASE_URL = os.getenv("API_BASE_URL", "https://bonnetjes-app.spikkies-it.nl")
DEFAULT_TIMEOUT = float(os.getenv("API_TEST_TIMEOUT", "30"))
DEFAULT_BROWSER_TIMEOUT = float(os.getenv("API_TEST_BROWSER_TIMEOUT", "300"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Initial end-to-end test for the ChatGPT browser automation routes. "
            "Logs in to the backend, runs browser login-check, sends a text prompt, "
            "and optionally sends a file."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Backend base URL. Defaults to API_BASE_URL or production URL.",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("API_TEST_USERNAME"),
        help="Backend username. Defaults to API_TEST_USERNAME.",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("API_TEST_PASSWORD"),
        help="Backend password. Defaults to API_TEST_PASSWORD.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="HTTP timeout in seconds for normal requests.",
    )
    parser.add_argument(
        "--browser-timeout",
        type=float,
        default=DEFAULT_BROWSER_TIMEOUT,
        help="HTTP timeout in seconds for browser-backed requests.",
    )
    parser.add_argument(
        "--keep-open",
        action="store_true",
        help="Pass keep_open=true to the login-check route.",
    )
    parser.add_argument(
        "--prompt",
        default="Reply with exactly: browser-route-ok",
        help="Text prompt for the initial browser ask route check.",
    )
    parser.add_argument(
        "--json-prompt",
        default='Return exactly this JSON object and nothing else: {"status":"ok","source":"browser-route"}',
        help="Prompt for JSON mode verification.",
    )
    parser.add_argument(
        "--file",
        default=os.getenv("API_TEST_RECEIPT_FILE"),
        help="Optional file path to send with the browser ask route.",
    )
    parser.add_argument(
        "--skip-login-check",
        action="store_true",
        help="Skip POST /chatgpt/browser/login-check.",
    )
    parser.add_argument(
        "--skip-json",
        action="store_true",
        help="Skip the JSON-mode ask test.",
    )
    parser.add_argument(
        "--skip-file",
        action="store_true",
        help="Skip the optional file ask test even if --file is present.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save the combined test results as JSON.",
    )
    return parser


def require(value: str | None, flag_name: str) -> str:
    if value:
        return value
    raise SystemExit(f"Missing {flag_name}. Provide it explicitly or set the matching environment variable.")


def print_step(title: str) -> None:
    print(f"\n=== {title} ===", flush=True)


def dump_payload(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str), flush=True)


def login(client: httpx.Client, username: str, password: str) -> dict[str, Any]:
    response = client.post("/login", data={"username": username, "password": password})
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(f"Login failed: {payload}")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    token_type = str(data.get("token_type", "bearer"))
    if not access_token or not refresh_token:
        raise RuntimeError(f"Login succeeded but tokens were missing: {payload}")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": token_type,
    }


def call_login_check(client: httpx.Client, headers: dict[str, str], keep_open: bool) -> dict[str, Any]:
    response = client.post(
        "/chatgpt/browser/login-check",
        headers=headers,
        params={"keep_open": str(bool(keep_open)).lower()},
    )
    response.raise_for_status()
    return response.json()


def call_browser_ask(
    client: httpx.Client,
    headers: dict[str, str],
    *,
    prompt: str,
    expect_json: bool,
    keep_open: bool = False,
    file_path: str | None = None,
) -> dict[str, Any]:
    data = {
        "prompt": prompt,
        "expect_json": str(bool(expect_json)).lower(),
        "keep_open": str(bool(keep_open)).lower(),
    }
    files = None
    if file_path:
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"File does not exist: {path}")
        files = {"file": (path.name, path.read_bytes(), "application/octet-stream")}
    response = client.post("/chatgpt/browser/ask", headers=headers, data=data, files=files)
    response.raise_for_status()
    return response.json()


def assert_success(payload: dict[str, Any], context: str) -> None:
    if payload.get("success") is not True:
        raise RuntimeError(f"{context} failed: {payload}")
    if payload.get("code") != "success":
        raise RuntimeError(f"{context} returned unexpected code: {payload}")


def main() -> int:
    args = build_parser().parse_args()
    username = require(args.username, "--username / API_TEST_USERNAME")
    password = require(args.password, "--password / API_TEST_PASSWORD")

    results: dict[str, Any] = {
        "base_url": args.base_url.rstrip("/"),
        "keep_open": bool(args.keep_open),
        "steps": {},
    }

    normal_timeout = httpx.Timeout(args.timeout)
    browser_timeout = httpx.Timeout(args.browser_timeout)

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=normal_timeout, follow_redirects=True) as client:
        print_step("login")
        token_bundle = login(client, username=username, password=password)
        results["steps"]["login"] = {
            "success": True,
            "token_type": token_bundle["token_type"],
        }
        dump_payload(results["steps"]["login"])

    headers = {"Authorization": f"Bearer {token_bundle['access_token']}"}

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=browser_timeout, follow_redirects=True) as client:
        if not args.skip_login_check:
            print_step("chatgpt/browser/login-check")
            login_check_payload = call_login_check(client, headers=headers, keep_open=args.keep_open)
            results["steps"]["login_check"] = login_check_payload
            dump_payload(login_check_payload)
            assert_success(login_check_payload, "login-check")

        print_step("chatgpt/browser/ask text prompt")
        ask_payload = call_browser_ask(
            client,
            headers=headers,
            prompt=args.prompt,
            expect_json=False,
        )
        results["steps"]["ask_text"] = ask_payload
        dump_payload(ask_payload)
        assert_success(ask_payload, "browser ask text")

        if not args.skip_json:
            print_step("chatgpt/browser/ask json prompt")
            ask_json_payload = call_browser_ask(
                client,
                headers=headers,
                prompt=args.json_prompt,
                expect_json=True,
            )
            results["steps"]["ask_json"] = ask_json_payload
            dump_payload(ask_json_payload)
            assert_success(ask_json_payload, "browser ask json")
            if not isinstance(ask_json_payload.get("answer"), dict):
                raise RuntimeError(
                    "JSON ask was expected to return a JSON object in the answer field. "
                    f"Payload was: {ask_json_payload}"
                )

        if args.file and not args.skip_file:
            print_step("chatgpt/browser/ask with file")
            ask_file_payload = call_browser_ask(
                client,
                headers=headers,
                prompt="Describe the uploaded file briefly. If it looks like a receipt, say so.",
                expect_json=False,
                file_path=args.file,
            )
            results["steps"]["ask_file"] = ask_file_payload
            dump_payload(ask_file_payload)
            assert_success(ask_file_payload, "browser ask file")
        elif args.file:
            results["steps"]["ask_file"] = {
                "skipped": True,
                "reason": "--skip-file was set",
            }
        else:
            results["steps"]["ask_file"] = {
                "skipped": True,
                "reason": "No --file / API_TEST_RECEIPT_FILE was provided",
            }

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        print_step(f"saved results to {output_path}")

    print_step("summary")
    dump_payload(results)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted by user.", file=sys.stderr, flush=True)
        raise SystemExit(130)
