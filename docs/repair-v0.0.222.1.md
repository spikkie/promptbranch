# Repair release v0.0.222.1

## Base release

`chatgpt_claudecode_workflow_v0.0.222.zip`

## Repair version

`chatgpt_claudecode_workflow_v0.0.222.1.zip`

## Reason

Add a repeatable post-release validation helper so the operator can run the standard after-release checks with one command and one versioned log directory. This repairs an operational gap in the v0.0.222 release workflow; it does not advance the Artifact Intake MVP scope.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_cli.py`
- `docker-compose.chatgpt-service.yml`
- `README.md`
- `scripts/post-release-validation.sh`
- `tests/test_promptbranch_shell_scripts.py`
- version expectation tests for CLI/container/MCP surfaces
- `docs/repair-v0.0.222.1.md`

## Validation performed

- `bash -n scripts/post-release-validation.sh`
- `python3 -m py_compile` on core Python modules
- focused pytest for shell script, version, MCP, artifact, and container surfaces
- extracted ZIP verification
- ZIP CRC/testzip check
- ZIP hygiene check for cache/log/debug/generated artifacts

## Scope confirmation

No slice or line was advanced. The repair adds validation tooling only.

No changes were made to:

- ask/reply protocol schema
- reply parsing semantics
- artifact download
- candidate migration
- artifact adoption
- Project Source mutation
- source sync behavior
- MCP write/process policy
- rate-limit pacing behavior
