# Release v0.0.241.2

Repair release for `v0.0.241.1`.

## Base release

`chatgpt_claudecode_workflow_v0.0.241.1.zip`

## Reason

`chatgpt_claudecode_workflow_release_control.sh --version v0.0.241.1` recreated the Docker service successfully, and Docker reported the container healthy, but release-control failed during service version verification because the inline Python health probe contained an invalid string literal:

```text
SyntaxError: unterminated string literal
```

The failure was in the release-control verification helper, not in Docker startup.

## Files changed

- `chatgpt_claudecode_workflow_release_control.sh`
- `docker-compose.chatgpt-service.yml`
- version metadata/tests/docs

## Changes

- Fixed the inline Python health probe newline writes by using escaped `\n` literals.
- Added test coverage that extracts the health-probe heredoc and compiles it with Python.
- Added `pull_policy: build` to the Compose service to avoid the noisy remote pull attempt for local `promptbranch-service:<version>` images.

## Validation performed

- `bash -n chatgpt_claudecode_workflow_release_control.sh`
- Python compile checks
- focused shell-script and version tests
- ZIP CRC and hygiene checks

## Scope confirmation

No slice, line, or feature scope was advanced. This is a repair-only release for service verification and Docker Compose local-build behavior.
