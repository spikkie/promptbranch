# Repair release v0.0.278.15

Base release: v0.0.278.14
Repair version: v0.0.278.15
Reason: Decompose and optimize submit confirmation timing for old, large ChatGPT task DOMs after response fast-return was proven in v0.0.278.14.

Files changed:
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_list_browser_client.py`
- version assertion tests updated for v0.0.278.15
- `docs/repair-v0.0.278.15.md`

Validation performed:
- Python compilation over repository Python files.
- Focused pytest for browser-client submit confirmation behavior and version/health/compose policy checks.

Scope confirmation:
- No slice or line was advanced.
- No source-add, artifact lifecycle, ask/reply protocol, MCP, or release lifecycle scope was advanced.
- This repair changes only submit confirmation timing/accounting and the fast confirmation path for successful dispatches.
