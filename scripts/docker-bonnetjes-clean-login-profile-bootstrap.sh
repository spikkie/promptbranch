#!/usr/bin/env bash
set -euo pipefail

# Compatibility wrapper. The standard Promptbranch browser profile bootstrap is
# implemented by scripts/pb-browser-profile-bootstrap.sh. This wrapper keeps old
# operator commands working while the default profile path is now neutral:
#   .pb_profile/browser/default

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${repo_root}/scripts/pb-browser-profile-bootstrap.sh" "$@"
