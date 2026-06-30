#!/usr/bin/env bash
set -euo pipefail

# Diagnostic-only helper. It enables the explicit Docker parity Project Source mutation
# gate, verifies passive auth-readiness first, then uploads exactly one caller-supplied
# source file. It is intentionally separate from release-control/adoption.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

source_path="${1:-}"
if [[ -z "${source_path}" ]]; then
  echo "usage: $0 <source-file>" >&2
  echo "example: $0 ./chatgpt_claudecode_workflow-2_v0.1.103.4.zip" >&2
  exit 64
fi
if [[ ! -f "${source_path}" ]]; then
  echo "ERROR: source file not found: ${source_path}" >&2
  exit 66
fi

mkdir -p debug_artifacts/docker-browser-parity

ts="$(date -u +%Y%m%dT%H%M%SZ)"
out_dir="debug_artifacts/docker-browser-parity/${ts}-project-source"
mkdir -p "${out_dir}"

export PROMPTBRANCH_DOCKER_BROWSER_PROFILE="${PROMPTBRANCH_DOCKER_BROWSER_PROFILE:-docker-browser-parity}"
export PROMPTBRANCH_PROFILE_DIR="${PROMPTBRANCH_PROFILE_DIR:-/app/profile}"
export PROMPTBRANCH_ALLOW_PROJECT_SOURCE_MUTATION="${PROMPTBRANCH_ALLOW_PROJECT_SOURCE_MUTATION:-1}"
export CHATGPT_USE_PATCHRIGHT="${CHATGPT_USE_PATCHRIGHT:-1}"
export CHATGPT_BROWSER_CHANNEL="${CHATGPT_BROWSER_CHANNEL:-chrome}"
export CHATGPT_HEADLESS="${CHATGPT_HEADLESS:-0}"
export CHATGPT_DISABLE_FEDCM="${CHATGPT_DISABLE_FEDCM:-1}"
export CHATGPT_FILTER_NO_SANDBOX="${CHATGPT_FILTER_NO_SANDBOX:-0}"
export CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS="${CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS:-1}"
export CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS="${CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS:-20000}"

printf '== docker browser parity guarded project source env ==\n' | tee "${out_dir}/run.log"
env | sort | grep -E '^(PROMPTBRANCH_DOCKER_BROWSER_PROFILE|PROMPTBRANCH_PROFILE_DIR|PROMPTBRANCH_ALLOW_PROJECT_SOURCE_MUTATION|CHATGPT_USE_PATCHRIGHT|CHATGPT_BROWSER_CHANNEL|CHATGPT_HEADLESS|CHATGPT_DISABLE_FEDCM|CHATGPT_FILTER_NO_SANDBOX|CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS|CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS)=' | tee -a "${out_dir}/run.log"

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

python3 - <<PY
import json
from pathlib import Path
out = Path(${out_dir@Q})
auth = json.loads((out / "auth-readiness.json").read_text())
required = {
    "logged_in": auth.get("logged_in") is True,
    "challenge_clear": auth.get("challenge_detected") is False,
    "composer_visible": auth.get("composer_visible") is True,
    "release_not_blocking": auth.get("release_blocking") is False,
}
(out / "preflight-required.json").write_text(json.dumps(required, indent=2, sort_keys=True) + "\n")
if not all(required.values()):
    raise SystemExit("auth readiness preflight failed: " + json.dumps(required, sort_keys=True))
PY

source_abs="$(realpath "${source_path}")"
source_name="$(basename "${source_path}")"
source_http_code="$(curl -sS -o "${out_dir}/project-source-add.json" -w '%{http_code}' \
  -X POST http://localhost:8000/v1/project-sources \
  "${auth_header[@]}" \
  -F type=file \
  -F overwrite_existing=true \
  -F keep_open=false \
  -F "name=${source_name}" \
  -F "file=@${source_abs};filename=${source_name}" || true)"
printf '%s\n' "${source_http_code}" > "${out_dir}/project-source-add.http_code"

docker compose -f docker-compose.chatgpt-service.yml logs --tail=500 chatgpt-service > "${out_dir}/docker-service.log" || true

python3 - <<PY
import json
from pathlib import Path
out = Path(${out_dir@Q})
summary = {"ok": True, "action": "docker_browser_parity_guarded_project_source", "output_dir": str(out)}
for name in ["healthz", "docker-browser-runtime", "auth-readiness", "project-source-add"]:
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
source = summary.get("project_source_add", {})
runtime = summary.get("docker_browser_runtime", {})
summary["ok"] = bool(runtime.get("ok") and auth.get("ok") and source.get("ok"))
summary["status"] = source.get("status") or ("project_source_mutation_test_passed" if summary["ok"] else "project_source_mutation_test_failed")
summary["release_blocking"] = bool(auth.get("release_blocking", not summary["ok"])) or not summary["ok"]
(out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(json.dumps(summary, indent=2, sort_keys=True))
raise SystemExit(0 if summary["ok"] else 2)
PY
