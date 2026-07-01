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

prepare_profile_dir_for_host_chrome() {
  local dir="$1"
  local parent
  parent="$(dirname "${dir}")"
  mkdir -p -- "${parent}"

  if [[ -e "${dir}" && ! -d "${dir}" ]]; then
    echo "ERROR: browser profile path exists but is not a directory: ${dir}" >&2
    exit 66
  fi

  if [[ "${fresh}" == "1" ]]; then
    if ! rm -rf -- "${dir}"; then
      cat >&2 <<MSG
ERROR: cannot remove browser profile for --fresh: ${dir}
The directory is probably owned by another user. Repair ownership first, for example:
  sudo chown -R $(id -u):$(id -g) "${dir}"
Then rerun this command.
MSG
      exit 21
    fi
  fi

  if [[ -d "${dir}" && ! -w "${dir}" ]]; then
    if rmdir -- "${dir}" 2>/dev/null; then
      echo "Repaired empty non-writable browser profile placeholder: ${dir}"
    else
      cat >&2 <<MSG
ERROR: browser profile directory is not writable: ${dir}
Chrome must be able to create SingletonLock in this directory.

Likely cause: Docker created the bind-mount target as root before host Chrome bootstrap.
Repair it on the host, for example:
  sudo chown -R $(id -u):$(id -g) "${dir}"

If you do not need this profile state, you may also remove/recreate it with owner permissions.
MSG
      exit 21
    fi
  fi

  mkdir -p -- "${dir}"
  if [[ ! -w "${dir}" ]]; then
    cat >&2 <<MSG
ERROR: browser profile directory is still not writable after preparation: ${dir}
Repair ownership first, for example:
  sudo chown -R $(id -u):$(id -g) "${dir}"
MSG
    exit 21
  fi
  chmod 700 "${dir}" || true
  rm -f \
    "${dir}/SingletonLock" \
    "${dir}/SingletonCookie" \
    "${dir}/SingletonSocket" \
    2>/dev/null || true
}

prepare_profile_dir_for_host_chrome "${profile_dir}"

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
