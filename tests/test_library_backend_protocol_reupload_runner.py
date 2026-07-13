from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pb-library-backend-protocol-reupload-diagnostic.py"
LAUNCHER = ROOT / "scripts" / "pb-library-backend-protocol-reupload-diagnostic.sh"


def test_runner_help_works_from_external_cwd(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert "backend protocol discovery" in completed.stdout


def test_launcher_uses_standard_token_and_endpoint(tmp_path: Path) -> None:
    observed = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            observed["path"] = self.path
            observed["authorization"] = self.headers.get("Authorization", "")
            length = int(self.headers.get("Content-Length", "0") or "0")
            observed["payload"] = json.loads(self.rfile.read(length) or b"{}")
            body = json.dumps(
                {
                    "ok": True,
                    "status": "diagnostic_completed",
                    "conclusion": "backend_inventory_not_discovered",
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        home = tmp_path / "home"
        cfg = home / ".config" / "promptbranch"
        cfg.mkdir(parents=True)
        (cfg / "config.json").write_text(
            json.dumps(
                {
                    "service_base_url": f"http://127.0.0.1:{server.server_port}",
                    "service_token": "secret",
                }
            )
        )
        env = os.environ.copy()
        env["HOME"] = str(home)
        for key in (
            "PYTHONPATH",
            "CHATGPT_CLI_CONFIG",
            "CHATGPT_SERVICE_BASE_URL",
            "CHATGPT_API_BASE_URL",
            "CHATGPT_SERVICE_TOKEN",
            "CHATGPT_API_TOKEN",
        ):
            env.pop(key, None)
        completed = subprocess.run(
            [str(LAUNCHER), "--timeout-seconds", "10"],
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert completed.returncode == 0, completed.stderr
    assert observed["path"] == "/v1/diagnostics/library-backend-protocol-reupload"
    assert observed["authorization"] == "Bearer secret"
    assert observed["payload"]["allow_project_source_mutation"] is True
    assert observed["payload"]["project_name_prefix"] == "itest-pb-library-backend"
