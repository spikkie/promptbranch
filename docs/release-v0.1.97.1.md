# Release v0.1.97.1 — Text-source add post-commit reconciliation repair

Repair-only candidate for the failed `v0.1.97` run. The normal slice remains `v0.1.97 — Read-only loop evidence gate`; this release changes only the text-source post-commit reconciliation path used by Project Source validation.

## Operator command

```bash
zip=~/Downloads/chatgpt_claudecode_workflow-2_v0.1.97.1.zip
ver=v0.1.97.1
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
