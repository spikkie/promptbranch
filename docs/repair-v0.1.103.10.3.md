# v0.1.103.10.3 — Auth-only hygiene compile path repair

## Scope

This repair keeps the Bonnetjes Cloudflare parity mode and the `--auth-only-validation` release-control behavior unchanged.

It fixes the auth-only hygiene compile check that incorrectly referenced a missing root-level `promptbranch_service.py` file.

## Changes

- Removed the missing `promptbranch_service.py` target from the auth-only `py_compile` check.
- Replaced it with existing package/runtime modules used by the current CLI and service client path.
- Kept Project Source mutation out of scope.
- Kept `PROMPTBRANCH_ALLOW_PROJECT_SOURCE_MUTATION` unset.

## Expected validation

Run:

```bash
ver=v0.1.103.10.3
zip="$HOME/Downloads/chatgpt_claudecode_workflow-2_${ver}.zip"

timeout --foreground 10800 ./chatgpt_claudecode_workflow_release_control.sh \
  --install-from-zip "$zip" \
  --version "$ver" \
  --auth-only-validation \
  --skip-tests \
  --adopt-after-validation \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12 \
  2>&1 | tee ~/tmp/release_control.$ver.auth_only.adopt.log
```

Pass criteria:

- ZIP install succeeds.
- Installed package version matches `0.1.103.10.3`.
- Auth-only hygiene checks pass.
- Docker Bonnetjes validation passes.
- Local-only artifact adoption records `v0.1.103.10.3` as current.
- No Project Source mutation is attempted.
