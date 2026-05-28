# Repair release v0.0.278.14

Base release: v0.0.278.13
Repair version: v0.0.278.14
Reason: Fast-return successful latest-turn parseable JSON responses and avoid expensive success-path completion/debug probes unless explicit deep diagnostics are enabled.

Files changed:
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_list_browser_client.py`
- version assertion updates under `tests/`
- `docs/repair-v0.0.278.14.md`

Behavioral scope:
- Preserves v0.0.278.13 response wait decomposition.
- Preserves v0.0.278.12 post-submit snapshot skip.
- Preserves v0.0.278.11 capped DOM diagnostics.
- Adds latest-turn JSON fast return for successful `expect_json=True` responses.
- Skips global completion-signal probing and success-path debug artifact save when latest-turn JSON is already parseable and deep debug is not explicitly enabled.
- Keeps completion-signal probing and diagnostics for fallback/deep-debug paths.

Validation performed:
- `python3 -m py_compile` over repository Python files.
- Focused pytest:
  - `tests/test_project_list_browser_client.py`
  - `tests/test_chatgpt_container_api.py`
  - `tests/test_promptbranch_container_api.py`
  - `tests/test_compose_timeout_policy.py`
  - `tests/test_cli_parser.py::test_parser_accepts_version_subcommand`
  - `tests/test_promptbranch_cli.py::test_main_version_subcommand_outputs_release`

Slice/line confirmation:
- No slice or line was advanced.
- No release lifecycle, source-add, hydration, or submit-confirmation scope was changed.
