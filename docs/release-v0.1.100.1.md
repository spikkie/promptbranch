# Release candidate v0.1.100.1

`v0.1.100.1` is a repair-only candidate for text-source add stale-inflight recovery diagnostics/verification.

It does not advance the normal MVP slice. `v0.1.100` remains the active normal slice and `v0.1.101` remains deferred until the repair is accepted/current.

## Candidate behavior

- Re-opens/re-reads Project Sources during text-source post-commit recovery.
- Records recovery diagnostics when the source surface remains empty or unreadable.
- Requires exact text identity/content proof to mark recovery successful.
- Preserves the single allowlisted read-only validation command execution from `v0.1.100`.

## Promotion command

```bash
zip=~/Downloads/chatgpt_claudecode_workflow-2_v0.1.100.1.zip
ver=v0.1.100.1

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
