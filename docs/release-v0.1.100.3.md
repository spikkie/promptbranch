# Release candidate v0.1.100.3

`v0.1.100.3` is a repair-only candidate for ZIP hygiene after `v0.1.100.2` packaged generated `debug_artifacts/` entries.

## Validation command

```bash
zip=~/Downloads/chatgpt_claudecode_workflow-2_v0.1.100.3.zip
ver=v0.1.100.3

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

Do not call this release accepted/current until release-control passes and `pb artifact current --json` proves runtime/source/artifact/registry alignment.
