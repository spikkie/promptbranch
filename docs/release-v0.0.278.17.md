# Release v0.0.278.17 — warm-task stale-answer guard

## Base release

v0.0.278.16

## Release type

Normal release.

This release canonicalizes the warm-task stale-answer guard into a supported normal version because the local release workflow does not support the fourth-field repair version for this line.

## Reason

v0.0.278.16 introduced warm-task hydration reuse, but the warm path could return a stale latest assistant answer when the current page already contained an old parseable JSON response. The response extractor needed a post-submit freshness guard before returning latest-turn JSON.

## Files changed

- promptbranch_browser_auth/client.py
- tests/test_project_list_browser_client.py
- VERSION
- pyproject.toml
- promptbranch_version.py
- docker-compose.chatgpt-service.yml
- tests/test_chatgpt_container_api.py
- tests/test_promptbranch_container_api.py
- tests/test_compose_timeout_policy.py
- tests/test_cli_parser.py
- tests/test_promptbranch_cli.py
- docs/release-v0.0.278.17.md

## Validation performed

- Python bytecode compilation for packaged Python files.
- Focused pytest coverage for browser-client response freshness, warm hydration reuse, submit confirmation fast path, JSON fast return, version output, and container/compose version checks.
- ZIP verification for root layout, VERSION, nested ZIP absence, and hygiene exclusions.

## Scope confirmation

No new feature line was opened. The release preserves the intended v0.0.278.16 warm hydration behavior while fixing the stale-answer correctness defect in a workflow-supported normal version.
