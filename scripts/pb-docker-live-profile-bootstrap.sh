#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

seed_profile_dir="${PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_SEED_DIR:-${repo_root}/.pb_profile_local_debug}"
pool_name="${PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_POOL:-release-live}"
slot_index="${PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_POOL_SLOT_INDEX:-1}"
slot_profile_dir="${PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_SLOT_DIR:-}"
url="${PROMPTBRANCH_BROWSER_BOOTSTRAP_URL:-}"
fresh=0
seed_only=0
slot_only=0

usage() {
  cat <<'HELP'
Usage: pb-docker-live-profile-bootstrap.sh [options]

Bootstrap the exact Docker-visible live profiles used by canonical Promptbranch
full/live validation. This avoids trusting copied browser profiles.

Default profiles:
  seed: ./.pb_profile_local_debug
  slot: ./.pb_profile_local_debug_pools/release-live/slots/slot-1

Options:
  --fresh             Delete/recreate selected profiles before opening Docker Chrome.
  --reuse             Reuse selected profiles. Default.
  --url URL           URL to open. Defaults to the standard Docker bootstrap default.
  --seed-only         Bootstrap only .pb_profile_local_debug.
  --slot-only         Bootstrap only release-live slot-1.
  --seed-profile-dir PATH
  --slot-profile-dir PATH
  --pool NAME         Pool name. Default: release-live.
  --slot-index N      Slot index. Default: 1.
  --help              Show this help.

Manual steps in each Docker Chrome window:
  1. Wait until Cloudflare clears.
  2. Log in if needed.
  3. Open/confirm the Promptbranch project or conversation URL.
  4. Confirm the composer is visible for the live slot profile.
  5. Close Chrome completely.
HELP
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fresh|--fresh-profile) fresh=1; shift ;;
    --reuse|--reuse-profile) fresh=0; shift ;;
    --url) url="${2:-}"; shift 2 ;;
    --seed-only) seed_only=1; shift ;;
    --slot-only) slot_only=1; shift ;;
    --seed-profile-dir) seed_profile_dir="${2:-}"; shift 2 ;;
    --slot-profile-dir) slot_profile_dir="${2:-}"; shift 2 ;;
    --pool) pool_name="${2:-}"; shift 2 ;;
    --slot-index) slot_index="${2:-}"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 64 ;;
  esac
done

resolve_path() {
  local value="$1"
  if [[ "${value}" == /* ]]; then
    printf '%s\n' "${value}"
  else
    printf '%s\n' "${repo_root}/${value}"
  fi
}

seed_profile_dir="$(resolve_path "${seed_profile_dir}")"
if [[ -z "${slot_profile_dir}" ]]; then
  slot_profile_dir="$(python3 - "${seed_profile_dir}" "${pool_name}" "${slot_index}" <<'PY'
from __future__ import annotations
from pathlib import Path
import re
import sys
seed = Path(sys.argv[1])
pool = sys.argv[2]
slot = int(sys.argv[3])
safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", pool or "default").strip("._-") or "default"
print(seed.parent / f"{seed.name}_pools" / safe / "slots" / f"slot-{slot}")
PY
)"
else
  slot_profile_dir="$(resolve_path "${slot_profile_dir}")"
fi

bootstrap_args=()
if [[ ${fresh} -eq 1 ]]; then
  bootstrap_args+=(--fresh)
fi
if [[ -n "${url}" ]]; then
  bootstrap_args+=(--url "${url}")
fi

cat <<MSG
== Promptbranch Docker live profile bootstrap ==
seed_profile_dir=${seed_profile_dir}
pool_name=${pool_name}
slot_index=${slot_index}
slot_profile_dir=${slot_profile_dir}
fresh=${fresh}
url=${url:-<bootstrap-default>}

This opens Docker-launched Chrome for the shared profile used by canonical Promptbranch live validation.
No profile copying is performed.
MSG

if [[ ${slot_only} -eq 0 ]]; then
  echo "== Bootstrap live seed profile =="
  ./scripts/pb-docker-browser-profile-bootstrap.sh --profile-dir "${seed_profile_dir}" "${bootstrap_args[@]}"
fi

if [[ ${seed_only} -eq 0 ]]; then
  echo "== Bootstrap release-live pool slot profile =="
  ./scripts/pb-docker-browser-profile-bootstrap.sh --profile-dir "${slot_profile_dir}" "${bootstrap_args[@]}"
fi

cat <<MSG
== Done ==
Next validation command:
  PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_SEED_DIR="${seed_profile_dir}" \\
  PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_SLOT_DIR="${slot_profile_dir}" \\
  $PB_PYTHON <bootstrap-dir>/scripts/run-release-lifecycle-proof.py --cli <bootstrap-dir>/promptbranch_cli.py --artifact <candidate.zip> --version <version> --release-type <normal|repair> --repo-path . --profile-dir .pb_profile --profile full --test-timeout 3600 --artifact-conversation-url <candidate-conversation-url> --json
MSG
