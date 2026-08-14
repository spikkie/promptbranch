#!/usr/bin/env bash

usage() {
  cat <<'EOF'
Usage:
  ./install.sh --version VERSION --artifact ZIP \
    --artifact-conversation-url URL [--release-type normal|repair]

Thin bootstrap for the canonical Promptbranch release lifecycle.

This script contains no independent release policy. It verifies the transport
ZIP, extracts the candidate launcher, then delegates the complete lifecycle to
scripts/run-release-lifecycle-proof.py using the exact Promptbranch pipx Python.
EOF
}

version=""
artifact=""
artifact_conversation_url=""
release_type="repair"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --version)
      version="${2:-}"
      shift 2
      ;;
    --artifact)
      artifact="${2:-}"
      shift 2
      ;;
    --artifact-conversation-url)
      artifact_conversation_url="${2:-}"
      shift 2
      ;;
    --release-type)
      release_type="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown option: $1" >&2
      usage >&2
      exit 64
      ;;
  esac
done

if [ -z "$version" ] || [ -z "$artifact" ] || [ -z "$artifact_conversation_url" ]; then
  echo "ERROR: --version, --artifact and --artifact-conversation-url are required" >&2
  usage >&2
  exit 64
fi

case "$release_type" in
  normal|repair) ;;
  *)
    echo "ERROR: --release-type must be normal or repair" >&2
    exit 64
    ;;
esac

PB_PYTHON="${PB_PYTHON:-$HOME/.local/share/pipx/venvs/promptbranch/bin/python}"
if [ "${PB_PYTHON#/}" = "$PB_PYTHON" ] || [ ! -x "$PB_PYTHON" ]; then
  echo "ERROR: PB_PYTHON must be an absolute executable path: $PB_PYTHON" >&2
  exit 64
fi

artifact="$(realpath -e "$artifact" 2>/dev/null)"
if [ -z "$artifact" ] || [ ! -f "$artifact" ]; then
  echo "ERROR: candidate ZIP not found" >&2
  exit 66
fi

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
profile_dir="$repo_root/.pb_profile"

"$PB_PYTHON" - "$artifact" "$version" <<'PYVERIFY'
import sys
import zipfile
from pathlib import Path

zip_path = Path(sys.argv[1]).resolve()
expected_version = sys.argv[2]
with zipfile.ZipFile(zip_path) as archive:
    bad = archive.testzip()
    if bad:
        raise SystemExit(f"ERROR: candidate ZIP CRC failure at {bad}")
    names = set(archive.namelist())
    required = {
        "VERSION",
        "pyproject.toml",
        "promptbranch_cli.py",
        "scripts/run-release-lifecycle-proof.py",
    }
    missing = sorted(required - names)
    if missing:
        raise SystemExit("ERROR: candidate ZIP missing canonical lifecycle entries: " + ", ".join(missing))
    internal_version = archive.read("VERSION").decode("utf-8").strip()
if internal_version != expected_version:
    raise SystemExit(
        f"ERROR: candidate ZIP VERSION mismatch: expected {expected_version}, got {internal_version}"
    )
print(f"Candidate transport ZIP verified: {zip_path}")
PYVERIFY
verify_rc=$?
if [ "$verify_rc" -ne 0 ]; then
  exit "$verify_rc"
fi

bootstrap_dir="$(mktemp -d)"
unzip -q "$artifact" -d "$bootstrap_dir"
unzip_rc=$?
if [ "$unzip_rc" -ne 0 ]; then
  rm -rf "$bootstrap_dir"
  exit "$unzip_rc"
fi

"$PB_PYTHON" \
  "$bootstrap_dir/scripts/run-release-lifecycle-proof.py" \
  --cli "$bootstrap_dir/promptbranch_cli.py" \
  --artifact "$artifact" \
  --version "$version" \
  --release-type "$release_type" \
  --repo-path "$repo_root" \
  --profile-dir "$profile_dir" \
  --profile full \
  --test-timeout 3600 \
  --artifact-conversation-url "$artifact_conversation_url" \
  --json
lifecycle_rc=$?

rm -rf "$bootstrap_dir"
exit "$lifecycle_rc"
