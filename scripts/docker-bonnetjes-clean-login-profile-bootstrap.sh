#!/usr/bin/env bash
set -euo pipefail

# Create/open a fresh host Chrome profile for the Bonnetjes Cloudflare parity
# test. This is the only manual-login phase. After login, close Chrome and run
# docker-browser-parity-cloudflare-check.sh with PROMPTBRANCH_HOST_PROFILE_DIR
# pointing to the printed profile path.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

profile_dir="${PROMPTBRANCH_HOST_PROFILE_DIR:-}"
reuse=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile-dir)
      profile_dir="${2:-}"
      shift 2
      ;;
    --reuse)
      reuse=1
      shift
      ;;
    --help|-h)
      cat <<'HELP'
Usage: docker-bonnetjes-clean-login-profile-bootstrap.sh [--profile-dir PATH] [--reuse]

Creates a fresh empty Chrome profile by default, opens a visible host Chrome
window at https://chatgpt.com/, and prints the exact Docker Cloudflare check
command to run after manual login.

Default profile path:
  ./.pb_profile_bonnetjes_manual_<UTC timestamp>

Use --reuse only when deliberately reopening an existing profile.
HELP
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 64
      ;;
  esac
done

if [[ -z "${profile_dir}" ]]; then
  profile_dir="${repo_root}/.pb_profile_bonnetjes_manual_$(date -u +%Y%m%dT%H%M%SZ)"
elif [[ "${profile_dir}" != /* ]]; then
  profile_dir="${repo_root}/${profile_dir}"
fi

if [[ "${reuse}" == "0" ]]; then
  rm -rf -- "${profile_dir}"
fi
mkdir -p -- "${profile_dir}"
chmod 700 "${profile_dir}" || true

cat <<MSG
== Bonnetjes clean login profile bootstrap ==
profile_dir=${profile_dir}

A visible Chrome window will open. In that window:
  1. Confirm Cloudflare clears.
  2. Log in manually.
  3. Confirm the ChatGPT composer is visible.
  4. Close Chrome completely.

After Chrome is closed, run:

PROMPTBRANCH_DOCKER_BROWSER_PROFILE=bonnetjes-cloudflare-parity \\
PROMPTBRANCH_HOST_PROFILE_DIR="${profile_dir}" \\
PROMPTBRANCH_PROFILE_DIR=/app/profile \\
PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS=300 \\
./scripts/docker-browser-parity-cloudflare-check.sh --max-wait-seconds 300 --poll-seconds 10
MSG

google-chrome \
  --user-data-dir="${profile_dir}" \
  --profile-directory=Default \
  --ozone-platform=x11 \
  --disable-gpu \
  --disable-vulkan \
  --password-store=basic \
  --use-mock-keychain \
  --disable-sync \
  --no-first-run \
  --no-default-browser-check \
  https://chatgpt.com/
