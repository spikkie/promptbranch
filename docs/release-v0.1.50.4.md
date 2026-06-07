# Release v0.1.50.4

Repair release for `v0.1.50.3`.

## Base release

`chatgpt_claudecode_workflow-2_v0.1.50.3.zip`

## Reason

The `v0.1.50.3` source-add persistence repair correctly required post-refresh source verification, but the packaged `docker-compose.chatgpt-service.yml` still declared the stale image tag `promptbranch-service:0.1.50`. Full release-control validation failed the `version_consistency` step because the expected package version was `0.1.50.3` while the Compose service image tag normalized to `0.1.50`.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `tests/test_compose_timeout_policy.py`
- `tests/test_promptbranch_test_suite.py`
- `docs/release-v0.1.50.4.md`

## Validation performed

- `python3 -m compileall -q .`
- `python3 -m pytest -q tests/test_compose_timeout_policy.py tests/test_promptbranch_test_suite.py::test_source_version_consistency_detects_compose_image_tag_drift tests/test_promptbranch_test_suite.py::test_source_version_consistency_accepts_parameterized_compose_default tests/test_promptbranch_test_suite.py::test_source_version_consistency_detects_parameterized_compose_default_drift`
- `promptbranch_test_suite.source_version_consistency(repo_path=.)`
- clean ZIP layout and hygiene checks

## Scope confirmation

No slice or line was advanced. This repair only refreshes stale release-version metadata for the intended `v0.1.50` repair line so the release-control version-consistency gate can evaluate the candidate correctly. It also updates the affected version-consistency regression test to control the runtime package-version observation when using a synthetic temporary repository. It does not change source-add behavior, lifecycle routing, artifact adoption execution, policy sync execution, Git mutation, or project source mutation capability.
