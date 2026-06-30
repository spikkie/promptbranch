#!/usr/bin/env bash
set -euo pipefail

# Safe exporter for Docker browser parity auth-readiness challenge artifacts.
# It never copies /app/debug_artifacts wholesale. It stages only matching
# auth_readiness_auth_challenge_detected_* files inside the container under
# /tmp/pb-challenge-artifacts, enforces count/byte caps, then docker-cp's that
# bounded staging directory to a host destination.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
default_dest="/tmp/promptbranch-docker-browser-parity-challenge-artifacts/${ts}"
dest="${PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_DEST:-${1:-${default_dest}}}"
max_files="${PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_MAX_FILES:-30}"
max_bytes="${PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_MAX_BYTES:-52428800}"
container_name="${PROMPTBRANCH_DOCKER_CONTAINER_NAME:-chatgpt_claudecode_workflow-chatgpt-service-1}"

case "${max_files}" in
  ''|*[!0-9]*) echo "ERROR: PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_MAX_FILES must be an integer" >&2; exit 64 ;;
esac
case "${max_bytes}" in
  ''|*[!0-9]*) echo "ERROR: PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_MAX_BYTES must be an integer" >&2; exit 64 ;;
esac
if (( max_files < 1 || max_files > 500 )); then
  echo "ERROR: max file count out of range: ${max_files}" >&2
  exit 64
fi
if (( max_bytes < 1 || max_bytes > 1073741824 )); then
  echo "ERROR: max total bytes out of range: ${max_bytes}" >&2
  exit 64
fi

CID="$(docker ps --filter "name=${container_name}" -q | head -1)"
if [[ -z "${CID}" ]]; then
  echo "ERROR: no running container matched name=${container_name}" >&2
  exit 69
fi

# Resolve destination before creating it. Refuse destinations inside the repo
# debug tree because /app/debug_artifacts may be the same host bind mount; this
# prevents recursive debug_artifacts-in-debug_artifacts explosions.
dest_parent="$(dirname "${dest}")"
mkdir -p "${dest_parent}"
dest_real="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${dest}")"
repo_real="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${repo_root}")"
debug_real="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${repo_root}/debug_artifacts")"

case "${dest_real}" in
  "${debug_real}"|"${debug_real}"/*)
    cat >&2 <<MSG
ERROR: refusing destination inside repo debug_artifacts: ${dest_real}
Use an external destination such as /tmp/promptbranch-docker-browser-parity-challenge-artifacts/${ts}.
This guard prevents recursive docker cp growth when /app/debug_artifacts is bind-mounted from the repo.
MSG
    exit 78
    ;;
esac

printf '== docker browser parity safe challenge artifact export ==\n'
printf 'container=%s\n' "${CID}"
printf 'stage=/tmp/pb-challenge-artifacts\n'
printf 'dest=%s\n' "${dest_real}"
printf 'max_files=%s\n' "${max_files}"
printf 'max_bytes=%s\n' "${max_bytes}"

# Stage bounded artifacts in /tmp inside the container. Never docker cp the
# whole /app/debug_artifacts tree. Create the stage directory first so even
# no-matching-artifact cases remain docker-cp safe.
docker exec "${CID}" sh -lc 'rm -rf /tmp/pb-challenge-artifacts && mkdir -p /tmp/pb-challenge-artifacts'
docker exec "${CID}" python3 - "${max_files}" "${max_bytes}" <<'PY'
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
        print(json.dumps(manifest, indent=2, sort_keys=True))
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
print(json.dumps(manifest, indent=2, sort_keys=True))
PY

rm -rf -- "${dest_real}"
mkdir -p "${dest_real}"
docker cp "${CID}:/tmp/pb-challenge-artifacts/." "${dest_real}/"

python3 - "${dest_real}" <<'PY'
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
PY
