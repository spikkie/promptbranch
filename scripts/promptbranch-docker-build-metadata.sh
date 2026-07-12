#!/usr/bin/env bash
promptbranch_export_docker_build_metadata() {
  local repo_root="${1:?repo root required}"
  local version="${PROMPTBRANCH_VERSION:-}"
  if [[ -z "${version}" ]]; then
    version="$(tr -d '\r\n[:space:]' < "${repo_root}/VERSION")"
  fi
  version="${version#v}"
  local fingerprint="${PROMPTBRANCH_SOURCE_FINGERPRINT:-}"
  if [[ -z "${fingerprint}" || "${fingerprint}" == "unknown" ]]; then
    fingerprint="$(python3 - "${repo_root}" <<'PY_META'
from pathlib import Path
import hashlib, sys
root=Path(sys.argv[1])
d=hashlib.sha256()
for rel in ('VERSION','promptbranch_version.py','pyproject.toml'):
    p=root/rel
    d.update(rel.encode()); d.update(b'\0'); d.update(p.read_bytes()); d.update(b'\0')
print(d.hexdigest())
PY_META
)"
  fi
  local artifact_sha="${PROMPTBRANCH_ARTIFACT_SHA256:-}"
  if [[ -z "${artifact_sha}" || "${artifact_sha}" == "unknown" ]]; then
    local candidate="${repo_root}/$(basename "${repo_root}")_v${version}.zip"
    if [[ -f "${candidate}" ]]; then
      artifact_sha="$(sha256sum "${candidate}" | awk '{print $1}')"
    else
      artifact_sha="unknown"
    fi
  fi
  export PROMPTBRANCH_VERSION="${version}"
  export PROMPTBRANCH_SERVICE_IMAGE_TAG="${PROMPTBRANCH_SERVICE_IMAGE_TAG:-${version}}"
  export PROMPTBRANCH_SERVICE_IMAGE="${PROMPTBRANCH_SERVICE_IMAGE:-promptbranch-service:${PROMPTBRANCH_SERVICE_IMAGE_TAG}}"
  export PROMPTBRANCH_ARTIFACT_SHA256="${artifact_sha}"
  export PROMPTBRANCH_SOURCE_FINGERPRINT="${fingerprint}"
}
