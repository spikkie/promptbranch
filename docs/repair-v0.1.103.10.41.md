# v0.1.103.10.41 — preserve Docker live profile pool across release ZIP import

`v0.1.103.10.41` is a repair-only continuation of the all-in-Docker live profile line.

## Problem

`v0.1.103.10.40` correctly required explicitly bootstrapped live Docker profiles, but the release ZIP import plan preserved `.pb_profile_local_debug/` and removed `.pb_profile_local_debug_pools/`. That deleted the authenticated `release-live/slots/slot-1` profile before `--run-all-tests` reached live preflight.

## Repair

Release ZIP import now preserves local Docker live profile pool state:

```text
.pb_profile_local_debug_pools/
```

The pool remains protected local state:

- it is preserved across install/import;
- it is excluded from rsync imports;
- it is rejected if accidentally packaged inside a release ZIP;
- it remains ignored/generated local browser state, not source code.

## Scope boundaries

- Keep all-in-Docker only.
- Do not revive host-CDP/session-manager.
- Do not copy `.pb_profile/browser/default` into live profiles.
- Keep run-all live preflight strict.
- No browser/session architecture change.
