#!/usr/bin/env bash
set -euo pipefail

# Safe exporter for Docker browser parity auth-readiness challenge artifacts.
# It never copies /app/debug_artifacts wholesale. It stages only matching
# auth_readiness_auth_challenge_detected_* files inside the container under
# /tmp/pb-challenge-artifacts, enforces count/byte caps, then docker-cp's that
# bounded staging directory to a host destination. If no challenge artifacts
# exist, it returns ok=true/status=no_matching_artifacts and does not docker cp.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
default_dest="/tmp/promptbranch-docker-browser-parity-challenge-artifacts/${ts}"
dest="${PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_DEST:-${1:-${default_dest}}}"
max_files="${PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_MAX_FILES:-30}"
max_bytes="${PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_MAX_BYTES:-52428800}"
container_name="${PROMPTBRANCH_DOCKER_CONTAINER_NAME:-chatgpt_claudecode_workflow-chatgpt-service-1}"

json_error() {
  local status="$1"
  local message="$2"
  python3 - "$status" "$message" <<'PY_JSON_ERROR'
from __future__ import annotations
import json, sys
print(json.dumps({"ok": False, "status": sys.argv[1], "error": sys.argv[2]}, indent=2, sort_keys=True))
PY_JSON_ERROR
}

case "${max_files}" in
  ''|*[!0-9]*) json_error invalid_max_files "PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_MAX_FILES must be an integer"; exit 64 ;;
esac
case "${max_bytes}" in
  ''|*[!0-9]*) json_error invalid_max_bytes "PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_MAX_BYTES must be an integer"; exit 64 ;;
esac
if (( max_files < 1 || max_files > 500 )); then
  json_error invalid_max_files "max file count out of range: ${max_files}"
  exit 64
fi
if (( max_bytes < 1 || max_bytes > 1073741824 )); then
  json_error invalid_max_bytes "max total bytes out of range: ${max_bytes}"
  exit 64
fi

CID="$(docker ps --filter "name=${container_name}" -q | head -1)"
if [[ -z "${CID}" ]]; then
  json_error no_running_container "no running container matched name=${container_name}"
  exit 69
fi

dest_parent="$(dirname "${dest}")"
mkdir -p "${dest_parent}"
dest_real="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${dest}")"
debug_real="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${repo_root}/debug_artifacts")"

case "${dest_real}" in
  "${debug_real}"|"${debug_real}"/*)
    json_error refusing_destination_inside_repo_debug_artifacts "refusing destination inside repo debug_artifacts: ${dest_real}; use /tmp/promptbranch-docker-browser-parity-challenge-artifacts/${ts}"
    exit 78
    ;;
esac

docker exec "${CID}" sh -lc 'rm -rf /tmp/pb-challenge-artifacts && mkdir -p /tmp/pb-challenge-artifacts'
docker exec "${CID}" python3 - "${max_files}" "${max_bytes}" <<'PY_STAGE'
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

max_files = int(sys.argv[1])
max_bytes = int(sys.argv[2])
source = Path('/app/debug_artifacts')
stage = Path('/tmp/pb-challenge-artifacts')
pattern = 'auth_readiness_auth_challenge_detected_*'

if stage.exists():
    shutil.rmtree(stage)
stage.mkdir(parents=True, exist_ok=True)

files: list[Path] = []
if source.exists():
    candidates = [p for p in source.glob(pattern) if p.is_file() and not p.is_symlink()]
    candidates.sort(key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
    files = candidates[:max_files]

if not files:
    manifest = {
        'ok': True,
        'status': 'no_matching_artifacts',
        'source_dir': str(source),
        'stage_dir': str(stage),
        'pattern': pattern,
        'max_files': max_files,
        'max_bytes': max_bytes,
        'file_count': 0,
        'total_bytes': 0,
        'entries': [],
    }
    (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    raise SystemExit(0)

total_bytes = 0
entries = []
for path in files:
    size = path.stat().st_size
    if total_bytes + size > max_bytes:
        manifest = {
            'ok': False,
            'status': 'artifact_export_size_limit_exceeded',
            'source_dir': str(source),
            'stage_dir': str(stage),
            'pattern': pattern,
            'max_files': max_files,
            'max_bytes': max_bytes,
            'bytes_before_file': total_bytes,
            'rejected_file': path.name,
            'rejected_file_size': size,
        }
        (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        raise SystemExit(0)
    shutil.copy2(path, stage / path.name)
    total_bytes += size
    entries.append({'name': path.name, 'bytes': size})

manifest = {
    'ok': True,
    'status': 'artifact_export_staged',
    'source_dir': str(source),
    'stage_dir': str(stage),
    'pattern': pattern,
    'max_files': max_files,
    'max_bytes': max_bytes,
    'file_count': len(entries),
    'total_bytes': total_bytes,
    'entries': entries,
}
(stage / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
PY_STAGE

manifest_json="$(docker exec "${CID}" cat /tmp/pb-challenge-artifacts/manifest.json 2>/dev/null || true)"
if [[ -z "${manifest_json}" ]]; then
  json_error missing_staged_manifest "missing /tmp/pb-challenge-artifacts/manifest.json after staging"
  exit 2
fi
stage_status="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read()).get("status",""))' <<<"${manifest_json}")"
if [[ "${stage_status}" == "no_matching_artifacts" ]]; then
  MANIFEST_JSON="${manifest_json}" python3 - "${dest_real}" <<'PY_NO_MATCH'
from __future__ import annotations
import json, os, sys
payload = json.loads(os.environ['MANIFEST_JSON'])
payload['host_destination'] = sys.argv[1]
print(json.dumps(payload, indent=2, sort_keys=True))
PY_NO_MATCH
  exit 0
fi

rm -rf -- "${dest_real}"
mkdir -p "${dest_real}"
docker cp "${CID}:/tmp/pb-challenge-artifacts/." "${dest_real}/"

python3 - "${dest_real}" <<'PY_FINAL'
from __future__ import annotations

import json
import sys
from pathlib import Path

dest = Path(sys.argv[1])
manifest_path = dest / 'manifest.json'
manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'ok': False, 'status': 'missing_manifest'}
manifest['host_destination'] = str(dest)
print(json.dumps(manifest, indent=2, sort_keys=True))
raise SystemExit(0 if manifest.get('ok') else 2)
PY_FINAL
