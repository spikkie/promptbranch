# Release v0.0.276.13

Repair release for candidate-test observability and timeout control.

## Changes

- `pb artifact candidate-test` now uses a bounded internal timeout default of 540 seconds.
- The delegated release-control command is exposed in preflight output.
- Candidate-test subprocesses run in their own process group so timeout cleanup can terminate child pytest processes.
- Candidate-test stdout/stderr are written to durable log files under `.pb_profile/artifact_candidate_test_logs/`.
- Timeout and runner failures emit structured JSON records instead of relying on external shell timeout behavior.

## Non-goals

- No adoption behavior changed.
- No Project Source mutation added.
- No release baseline advancement.
