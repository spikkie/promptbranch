#!/usr/bin/env bash
set -euo pipefail

# Compatibility wrapper. The standard Promptbranch browser Cloudflare/auth
# validation workflow is implemented by scripts/pb-browser-cloudflare-validation.sh.
# This wrapper keeps old operator commands working.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${repo_root}/scripts/pb-browser-cloudflare-validation.sh" "$@"
