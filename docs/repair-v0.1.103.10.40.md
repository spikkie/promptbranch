# v0.1.103.10.40 — explicit Docker live profile bootstrap, no copied live pool trust

## Scope

`v0.1.103.10.40` continues from accepted/current `v0.1.103.10.38` and keeps the browser strategy all-in-Docker. The host-CDP/session-manager direction remains out of scope.

## Problem

`v0.1.103.10.39` proved that mechanically creating `.pb_profile_local_debug` was not enough. The release-live profile pool slot was refreshed/copied from another browser profile, then Cloudflare challenged the copied profile. The visible Chrome window showed `Just a moment...` and the unsupported `--disable-blink-features=FedCm` warning.

## Repair

- Add `scripts/pb-docker-live-profile-bootstrap.sh` to manually bootstrap the exact live profiles used by `--run-all-tests`:
  - `.pb_profile_local_debug`
  - `.pb_profile_local_debug_pools/release-live/slots/slot-1`
- Release-control validates that both profiles exist, are writable, and pass `pb --profile-dir ... login-check` before live-only steps.
- Missing/invalid live profiles are release-blocking for `--run-all-tests` and report bootstrap commands instead of being skipped.
- Live tests no longer pass `--profile-pool-refresh`; an existing authenticated release-live slot is reused instead of copied/refreshed.
- Normal browser launches no longer add the visible unsupported `--disable-blink-features=FedCm` flag. Docker defaults allow FedCM unless explicitly disabled for diagnostics.

## Out of scope

- No host-CDP/session-manager work.
- No browser architecture redesign.
- No Project Source mutation behavior change.
- No ChatGPT Project deletion.
- No artifact adoption claim.
