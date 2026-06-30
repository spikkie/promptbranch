#!/usr/bin/env bash
set -euo pipefail

# Diagnostic-only helper. It starts the Docker service with the Promptbranch Docker browser
# launch envelope and records runtime/passive auth-readiness evidence. It does not add
# Project Sources, click the ChatGPT login button, wait for hidden manual login, or adopt artifacts.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

mkdir -p debug_artifacts/docker-browser-parity

ts="$(date -u +%Y%m%dT%H%M%SZ)"
out_dir="debug_artifacts/docker-browser-parity/${ts}"
mkdir -p "${out_dir}"

export PROMPTBRANCH_DOCKER_BROWSER_PROFILE="${PROMPTBRANCH_DOCKER_BROWSER_PROFILE:-docker-browser-parity}"
export PROMPTBRANCH_PROFILE_DIR="${PROMPTBRANCH_PROFILE_DIR:-/app/profile}"
export CHATGPT_USE_PATCHRIGHT="${CHATGPT_USE_PATCHRIGHT:-1}"
export CHATGPT_BROWSER_CHANNEL="${CHATGPT_BROWSER_CHANNEL:-chrome}"
export CHATGPT_HEADLESS="${CHATGPT_HEADLESS:-0}"
export CHATGPT_DISABLE_FEDCM="${CHATGPT_DISABLE_FEDCM:-1}"
export CHATGPT_FILTER_NO_SANDBOX="${CHATGPT_FILTER_NO_SANDBOX:-0}"
export CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS="${CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS:-1}"
export CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS="${CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS:-20000}"

printf '== docker browser parity env ==\n' | tee "${out_dir}/run.log"
env | sort | grep -E '^(PROMPTBRANCH_DOCKER_BROWSER_PROFILE|PROMPTBRANCH_PROFILE_DIR|CHATGPT_USE_PATCHRIGHT|CHATGPT_BROWSER_CHANNEL|CHATGPT_HEADLESS|CHATGPT_DISABLE_FEDCM|CHATGPT_FILTER_NO_SANDBOX|CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS|CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS)=' | tee -a "${out_dir}/run.log"

mkdir -p .pb_profile .pb_profile_docker debug_artifacts

docker compose -f docker-compose.chatgpt-service.yml up -d --build | tee -a "${out_dir}/run.log"

for _ in $(seq 1 60); do
  if curl -fsS http://localhost:8000/healthz > "${out_dir}/healthz.json"; then
    break
  fi
  sleep 2
done

if [[ ! -s "${out_dir}/healthz.json" ]]; then
  echo 'ERROR: service healthz did not become ready' | tee -a "${out_dir}/run.log"
  docker compose -f docker-compose.chatgpt-service.yml logs --tail=240 chatgpt-service > "${out_dir}/docker-service.log" || true
  exit 1
fi

TOKEN="${CHATGPT_SERVICE_TOKEN:-}"
if [[ -z "${TOKEN}" && -f .env ]]; then
  TOKEN="$(grep '^CHATGPT_SERVICE_TOKEN=' .env | tail -1 | cut -d= -f2- || true)"
fi

auth_header=()
if [[ -n "${TOKEN}" ]]; then
  auth_header=(-H "Authorization: Bearer ${TOKEN}")
fi

runtime_http_code="$(curl -sS -o "${out_dir}/docker-browser-runtime.json" -w '%{http_code}' \
  "${auth_header[@]}" \
  http://localhost:8000/v1/docker/browser-runtime || true)"
printf '%s\n' "${runtime_http_code}" > "${out_dir}/docker-browser-runtime.http_code"

auth_http_code="$(curl -sS -o "${out_dir}/auth-readiness.json" -w '%{http_code}' \
  -X POST http://localhost:8000/v1/auth-readiness \
  "${auth_header[@]}" \
  -H 'Content-Type: application/json' \
  -d '{"keep_open": false}' || true)"
printf '%s\n' "${auth_http_code}" > "${out_dir}/auth-readiness.http_code"

docker compose -f docker-compose.chatgpt-service.yml logs --tail=400 chatgpt-service > "${out_dir}/docker-service.log" || true

python3 - <<PY
import json
from pathlib import Path
out = Path(${out_dir@Q})
summary = {"ok": True, "action": "docker_browser_parity_auth_readiness", "output_dir": str(out)}
for name in ["healthz", "docker-browser-runtime", "auth-readiness"]:
    path = out / f"{name}.json"
    http_code_path = out / f"{name}.http_code"
    http_code = http_code_path.read_text().strip() if http_code_path.exists() else ""
    try:
        payload = json.loads(path.read_text())
        if http_code:
            payload.setdefault("http_code", http_code)
        summary[name.replace('-', '_')] = payload
    except Exception as exc:
        summary[name.replace('-', '_')] = {"ok": False, "error": str(exc), "path": str(path), "http_code": http_code}

auth = summary.get("auth_readiness", {})
runtime = summary.get("docker_browser_runtime", {})
summary["ok"] = bool(runtime.get("ok") and auth.get("ok"))
summary["status"] = auth.get("status") or ("diagnostic_failed" if not summary["ok"] else "auth_preflight_ready")
summary["release_blocking"] = bool(auth.get("release_blocking", not summary["ok"]))
(out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(json.dumps(summary, indent=2, sort_keys=True))
raise SystemExit(0 if summary["ok"] else 2)
PY
