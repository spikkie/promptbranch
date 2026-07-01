#!/usr/bin/env bash
set -euo pipefail

# Bootstrap the standard Promptbranch browser profile with a visible host Chrome
# login. By default this writes login/session state to:
#   .pb_profile/browser/default
# Docker mounts that same profile to /app/profile.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

standard_profile_dir="${repo_root}/.pb_profile/browser/default"
profile_dir="${PROMPTBRANCH_HOST_PROFILE_DIR:-${standard_profile_dir}}"
fresh=0

usage() {
  cat <<'HELP'
Usage: pb-browser-profile-bootstrap.sh [--profile-dir PATH] [--fresh] [--reuse]

Opens a visible host Chrome window using the standard Promptbranch browser
profile. Log in manually, confirm the ChatGPT composer is visible, then close
Chrome completely. The same profile is later bind-mounted into Docker as
/app/profile.

Default profile path:
  ./.pb_profile/browser/default

Options:
  --profile-dir PATH  Use a different browser profile directory.
  --fresh             Delete and recreate the selected profile before opening Chrome.
  --reuse             Compatibility alias; this is the default behavior.

After Chrome is closed, run:

PROMPTBRANCH_DOCKER_BROWSER_PROFILE=standard-browser \
PROMPTBRANCH_HOST_PROFILE_DIR="<profile_dir>" \
PROMPTBRANCH_PROFILE_DIR=/app/profile \
PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS=300 \
./scripts/docker-browser-parity-cloudflare-check.sh --max-wait-seconds 300 --poll-seconds 10
HELP
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile-dir)
      profile_dir="${2:-}"
      shift 2
      ;;
    --fresh|--fresh-profile)
      fresh=1
      shift
      ;;
    --reuse|--reuse-profile)
      fresh=0
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 64
      ;;
  esac
done

if [[ -z "${profile_dir}" ]]; then
  profile_dir="${standard_profile_dir}"
elif [[ "${profile_dir}" != /* ]]; then
  profile_dir="${repo_root}/${profile_dir}"
fi

if [[ "${fresh}" == "1" ]]; then
  rm -rf -- "${profile_dir}"
fi
mkdir -p -- "${profile_dir}"
chmod 700 "${profile_dir}" || true
rm -f \
  "${profile_dir}/SingletonLock" \
  "${profile_dir}/SingletonCookie" \
  "${profile_dir}/SingletonSocket" \
  2>/dev/null || true

cat <<MSG
== Promptbranch standard browser profile bootstrap ==
profile_dir=${profile_dir}
fresh=${fresh}

A visible Chrome window will open. In that window:
  1. Confirm Cloudflare clears.
  2. Log in manually if needed.
  3. Confirm the ChatGPT composer is visible.
  4. Close Chrome completely.

After Chrome is closed, run:

PROMPTBRANCH_DOCKER_BROWSER_PROFILE=standard-browser \\
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
