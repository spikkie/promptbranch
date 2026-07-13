from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "pb-project-source-ab-diagnostic.py"
LAUNCHER = REPO_ROOT / "scripts" / "pb-project-source-ab-diagnostic.sh"


def test_python_diagnostic_help_imports_repo_module_from_external_cwd(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Project Source legacy-vs-current A/B diagnostic" in completed.stdout


def test_shell_launcher_help_imports_repo_module_from_external_cwd(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [str(LAUNCHER), "--help"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Project Source legacy-vs-current A/B diagnostic" in completed.stdout

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def test_shell_launcher_loads_standard_promptbranch_config_token(tmp_path: Path) -> None:
    observed: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            observed["path"] = self.path
            observed["authorization"] = self.headers.get("Authorization", "")
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length:
                self.rfile.read(length)
            if observed["authorization"] != "Bearer configured-secret":
                payload = {"detail": "Missing bearer token"}
                body = json.dumps(payload).encode("utf-8")
                self.send_response(401)
            else:
                payload = {"ok": True, "status": "diagnostic_completed", "conclusion": "both_transactions_work"}
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        home = tmp_path / "home"
        config_dir = home / ".config" / "promptbranch"
        config_dir.mkdir(parents=True)
        (config_dir / "config.json").write_text(
            json.dumps(
                {
                    "service_base_url": f"http://127.0.0.1:{server.server_port}",
                    "service_token": "configured-secret",
                }
            ),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["HOME"] = str(home)
        for name in (
            "PYTHONPATH",
            "CHATGPT_CLI_CONFIG",
            "CHATGPT_SERVICE_BASE_URL",
            "CHATGPT_API_BASE_URL",
            "CHATGPT_SERVICE_TOKEN",
            "CHATGPT_API_TOKEN",
        ):
            env.pop(name, None)
        completed = subprocess.run(
            [str(LAUNCHER), "--timeout-seconds", "10"],
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert completed.returncode == 0, completed.stderr
    assert observed["path"] == "/v1/diagnostics/project-source-ab"
    assert observed["authorization"] == "Bearer configured-secret"
    payload = json.loads(completed.stdout)
    assert payload["status"] == "diagnostic_completed"
