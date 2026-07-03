#!/usr/bin/env bash
set -euo pipefail

# Diagnostic-only helper. It starts or reuses the Docker service with the
# Promptbranch Docker browser launch envelope and records runtime/passive
# auth-readiness evidence. It does not add Project Sources, click the ChatGPT
# login button, wait for hidden manual login, or adopt artifacts.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

keep_open=0
no_recreate="${PROMPTBRANCH_DOCKER_BROWSER_NO_RECREATE:-0}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep-open)
      keep_open=1
      shift
      ;;
    --no-recreate)
      no_recreate=1
      shift
      ;;
    --help|-h)
      cat <<'HELP'
Usage: docker-browser-parity-auth-readiness.sh [--keep-open] [--no-recreate]

Diagnostic-only helper. --keep-open asks the service to hold the browser
context for PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS. --no-recreate
uses the already-running service and fails if it is not healthy.
HELP
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 64
      ;;
  esac
done

mkdir -p debug_artifacts/docker-browser-parity

ts="$(date -u +%Y%m%dT%H%M%SZ)"
out_dir="debug_artifacts/docker-browser-parity/${ts}"
mkdir -p "${out_dir}"

export PROMPTBRANCH_DOCKER_BROWSER_PROFILE="${PROMPTBRANCH_DOCKER_BROWSER_PROFILE:-docker-browser-parity}"
export PROMPTBRANCH_PROFILE_DIR="${PROMPTBRANCH_PROFILE_DIR:-/app/profile}"
export CHATGPT_USE_PATCHRIGHT="${CHATGPT_USE_PATCHRIGHT:-1}"
export CHATGPT_BROWSER_CHANNEL="${CHATGPT_BROWSER_CHANNEL:-chrome}"
export CHATGPT_HEADLESS="${CHATGPT_HEADLESS:-0}"
export CHATGPT_DISABLE_FEDCM="${CHATGPT_DISABLE_FEDCM:-0}"
export CHATGPT_FILTER_NO_SANDBOX="${CHATGPT_FILTER_NO_SANDBOX:-0}"
export CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS="${CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS:-1}"
export CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS="${CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS:-20000}"
export PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS="${PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS:-300}"

printf '== docker browser parity env ==\n' | tee "${out_dir}/run.log"
printf 'keep_open=%s\nno_recreate=%s\n' "${keep_open}" "${no_recreate}" | tee -a "${out_dir}/run.log"
env | sort | grep -E '^(PROMPTBRANCH_DOCKER_BROWSER_PROFILE|PROMPTBRANCH_PROFILE_DIR|PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS|CHATGPT_USE_PATCHRIGHT|CHATGPT_BROWSER_CHANNEL|CHATGPT_HEADLESS|CHATGPT_DISABLE_FEDCM|CHATGPT_FILTER_NO_SANDBOX|CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS|CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS)=' | tee -a "${out_dir}/run.log"

mkdir -p .pb_profile .pb_profile_docker debug_artifacts

if [[ "${no_recreate}" =~ ^(1|true|yes|on)$ ]]; then
  if curl -fsS http://localhost:8000/healthz > "${out_dir}/healthz.preexisting.json"; then
    echo 'Using existing healthy Docker service (--no-recreate).' | tee -a "${out_dir}/run.log"
  else
    echo 'ERROR: --no-recreate requested but existing service is not healthy' | tee -a "${out_dir}/run.log"
    exit 1
  fi
else
  docker compose -f docker-compose.chatgpt-service.yml up -d --build | tee -a "${out_dir}/run.log"
fi

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

if [[ "${keep_open}" == "1" ]]; then
  auth_body='{"keep_open": true}'
else
  auth_body='{"keep_open": false}'
fi

auth_http_code="$(curl -sS -o "${out_dir}/auth-readiness.json" -w '%{http_code}' \
  -X POST http://localhost:8000/v1/auth-readiness \
  "${auth_header[@]}" \
  -H 'Content-Type: application/json' \
  -d "${auth_body}" || true)"
printf '%s\n' "${auth_http_code}" > "${out_dir}/auth-readiness.http_code"

if [[ "${keep_open}" == "1" ]]; then
  session_http_code="$(curl -sS -o "${out_dir}/auth-readiness-session-status.json" -w '%{http_code}' \
    "${auth_header[@]}" \
    http://localhost:8000/v1/auth-readiness/session/status || true)"
  printf '%s\n' "${session_http_code}" > "${out_dir}/auth-readiness-session-status.http_code"
fi

docker compose -f docker-compose.chatgpt-service.yml logs --tail=400 chatgpt-service > "${out_dir}/docker-service.log" || true

python3 - <<PY
import json
from pathlib import Path
out = Path(${out_dir@Q})
summary = {"ok": True, "action": "docker_browser_parity_auth_readiness", "output_dir": str(out)}
for name in ["healthz", "docker-browser-runtime", "auth-readiness", "auth-readiness-session-status"]:
    path = out / f"{name}.json"
    http_code_path = out / f"{name}.http_code"
    http_code = http_code_path.read_text().strip() if http_code_path.exists() else ""
    if not path.exists():
        continue
    try:
        payload = json.loads(path.read_text())
        if http_code:
            payload.setdefault("http_code", http_code)
        summary[name.replace('-', '_')] = payload
    except Exception as exc:
        summary[name.replace('-', '_')] = {"ok": False, "error": str(exc), "path": str(path), "http_code": http_code}

auth = summary.get("auth_readiness", {})
runtime = summary.get("docker_browser_runtime", {})
summary["keep_open_requested"] = bool(${keep_open})
summary["no_recreate_requested"] = str(${no_recreate@Q}).lower() in {"1", "true", "yes", "on"}
summary["ok"] = bool(runtime.get("ok") and auth.get("ok"))
summary["status"] = auth.get("status") or ("diagnostic_failed" if not summary["ok"] else "auth_preflight_ready")
summary["release_blocking"] = bool(auth.get("release_blocking", not summary["ok"]))
(out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(json.dumps(summary, indent=2, sort_keys=True))
raise SystemExit(0 if summary["ok"] else 2)
PY
