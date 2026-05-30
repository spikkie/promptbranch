# Release v0.0.278.67 — release-control test transport selection

## Summary

This release makes release-control test execution transport-explicit.

It implements the next step from `docs/testing/PROMPTBRANCH_TESTING_STRATEGY.md`: release-control can run the existing `pb test full` / `pb test report` gate through direct local execution, the localhost Docker service API path, or both.

## Scope

Added to `chatgpt_claudecode_workflow_release_control.sh`:

```bash
--test-transport direct|localhost|both
--localhost-base-url URL
```

Default behavior remains compatible:

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.278.67 \
  --run-tests
```

still uses the direct test path and the historical log names.

## Transport modes

### direct

Runs the existing local test path:

```bash
pb test full --json
pb test report <log> --json
```

### localhost

Runs the full test profile with the service adapter selected:

```bash
CHATGPT_SERVICE_BASE_URL=http://127.0.0.1:8000 \
pb test full --json
pb test report <localhost-log> --json
```

### both

Runs direct first, then localhost. The workflow is considered successful only when both test/report pairs pass.

## Logs

Explicit transport mode creates transport-specific logs:

```text
.pb_profile/release_logs/<version>/
  pb_test.full.direct.<version>.log
  pb_test.full.direct.<version>.report.json
  pb_test.full.localhost.<version>.log
  pb_test.full.localhost.<version>.report.json
```

The default direct mode without `--test-transport` preserves the historical paths:

```text
pb_test.full.<version>.log
pb_test.full.<version>.report.json
```

## Recommended verification

First run localhost only:

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.278.67 \
  --run-tests \
  --test-transport localhost \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12 \
  2>&1 | tee release_control.v0.0.278.67.localhost.log
```

If localhost is green, run both:

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.0.278.67 \
  --run-tests \
  --test-transport both \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12 \
  2>&1 | tee release_control.v0.0.278.67.both.log
```

## Not included

This release does not add new live ask test profiles yet:

```text
pb test ask-live --json
pb test login-bootstrap-live --json
pb test artifact-download-live --json
```

Those remain planned follow-up slices.
