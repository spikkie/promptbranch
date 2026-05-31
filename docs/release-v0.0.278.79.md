# Release v0.0.278.79

Repair release over v0.0.278.78.

Scope: version-source consistency repair only.

Changes:
- Updated repository VERSION to v0.0.278.79.
- Updated `pyproject.toml` package version to 0.0.278.79.
- Updated `promptbranch_version.py` package/runtime version to 0.0.278.79.
- Updated `docker-compose.chatgpt-service.yml` image tag to 0.0.278.79.
- Removed stale `promptbranch.egg-info/` from the packaged source and excluded generated egg-info metadata from future ZIPs.
- Hardened version-consistency checks to include the source `promptbranch_version.py` value and Docker Compose service image tag.

Validation performed:
- `python3 -m compileall -q .`
- `pytest -q tests/test_cli_parser.py tests/test_chatgpt_container_api.py tests/test_promptbranch_container_api.py tests/test_compose_timeout_policy.py tests/test_promptbranch_test_suite.py -q`

No visual-artifact-roundtrip scope was changed.
No artifact-intake relaxation was added.
No release baseline was adopted.
