# Release candidate v0.1.100.2

`v0.1.100.2` is a repair-only candidate for browser scheduler source-lifecycle timeout repair.

## Baseline

Accepted/current baseline before this repair: `chatgpt_claudecode_workflow-2_v0.1.99.1.zip`.

Failed candidate line repaired: `v0.1.100` with previous failed repair `v0.1.100.1`.

## Scope

- Preserve `v0.1.100` first controlled read-only validation command execution.
- Preserve `v0.1.100.1` text-source stale-inflight recovery diagnostics.
- Repair only the same-profile source-remove scheduler test timeout by replacing unbounded active-operation polling with bounded explicit fixture synchronization.

## Out of scope

No read-only command result diagnosis, correction planning, file mutation, deployment, Kubernetes mutation, Project Source behavior change, artifact adoption behavior change, or ChatGPT Project deletion.

## Promotion command

```bash
zip=~/Downloads/chatgpt_claudecode_workflow-2_v0.1.100.2.zip
ver=v0.1.100.2

timeout --foreground 10800 ./chatgpt_claudecode_workflow_release_control.sh \
  --install-from-zip "$zip" \
  --version "$ver" \
  --run-all-tests \
  --strict-source-kind-matrix \
  --adopt-after-validation \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12 \
  2>&1 | tee ~/tmp/release_control.$ver.run_all_tests.adopt.log
```
