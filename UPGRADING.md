# UPGRADING

This file documents the breaking rename that landed in **v0.0.68** and remains the reference for later releases such as **v0.0.69**.

## Summary

`promptbranch` is now the only supported public CLI and Python package surface.
The legacy `chatgpt_*` aliases were removed from the packaged artifact in v0.0.68.

What changed:
- CLI command: `chatgpt` -> `promptbranch`
- Python package: `chatgpt_workflow` -> `promptbranch`
- Internal modules/files: `chatgpt_*` -> `promptbranch_*`
- Internal packages: `chatgpt_automation` / `chatgpt_browser_auth` -> `promptbranch_automation` / `promptbranch_browser_auth`

Migration support that remains:
- config fallback: `~/.config/chatgpt-cli/config.json` is still read if the new config path is absent

## Public command and package replacements

| Old | New |
|---|---|
| `chatgpt` | `promptbranch` |
| `from chatgpt_workflow import ChatGPTServiceClient` | `from promptbranch import ChatGPTServiceClient` |
| `from chatgpt_workflow import ConversationStateStore` | `from promptbranch import ConversationStateStore` |
| `chatgpt completion bash` | `promptbranch completion bash` |
| `chatgpt use <project>` | `promptbranch use <project>` |
| `chatgpt state` | `promptbranch state` |
| `chatgpt prompt` | `promptbranch prompt` |
| `chatgpt state-clear` | `promptbranch state-clear` |

## Top-level module/file replacements

| Old file/module | New file/module |
|---|---|
| `chatgpt_cli.py` | `promptbranch_cli.py` |
| `chatgpt_container_api.py` | `promptbranch_container_api.py` |
| `chatgpt_service_client.py` | `promptbranch_service_client.py` |
| `chatgpt_state.py` | `promptbranch_state.py` |
| `chatgpt_full_integration_test.py` | `promptbranch_full_integration_test.py` |
| `chatgpt_login_test.py` | `promptbranch_login_test.py` |
| `chatgpt_cli_sequence_v5.py` | `promptbranch_cli_sequence_v5.py` |

## Package replacements

| Old package | New package |
|---|---|
| `chatgpt_workflow` | `promptbranch` |
| `chatgpt_automation` | `promptbranch_automation` |
| `chatgpt_browser_auth` | `promptbranch_browser_auth` |

## Config and state path changes

| Purpose | Old path | New path |
|---|---|---|
| CLI config | `~/.config/chatgpt-cli/config.json` | `~/.config/promptbranch/config.json` |
| CLI state | profile-local `.chatgpt_cli_state.json` | profile-local `.promptbranch_state.json` |
| Browser profile dir | visible `profile/` by convention | hidden inherited `.pb_profile/` by default |

The CLI discovers the nearest `.pb_profile` by walking up from the current working directory, and a deeper `.pb_profile` overrides a parent one for that subtree.

## Docker and service naming

| Old | New |
|---|---|
| image `chatgpt-docker-service:*` | image `promptbranch-service:*` |
| app module `chatgpt_container_api:app` | app module `promptbranch_container_api:app` |

## Example updates

| Old | New |
|---|---|
| `examples/chatgpt_service_client_example.py` | `examples/promptbranch_service_client_example.py` |

## Minimal migration steps

### CLI users

```bash
pip uninstall -y chatgpt-claudecode-workflow || true
pipx uninstall chatgpt-claudecode-workflow || true
pipx install ./chatgpt_claudecode_workflow_v0.0.110.zip
promptbranch state
promptbranch prompt
```

### Python callers

Replace imports:

```python
from chatgpt_workflow import ChatGPTServiceClient, ConversationStateStore
```

with:

```python
from promptbranch import ChatGPTServiceClient, ConversationStateStore
```

### Service operators

Update:
- image tags from `chatgpt-docker-service:*` to `promptbranch-service:*`
- app module from `chatgpt_container_api:app` to `promptbranch_container_api:app`
- any scripts that still invoke `chatgpt_*` file names

## Breaking changes to expect

These names are no longer packaged in v0.0.68+:
- `chatgpt` CLI command
- `chatgpt_workflow` package
- `chatgpt_automation` package
- `chatgpt_browser_auth` package
- top-level `chatgpt_*` modules listed above

If you still depend on them, pin to `v0.0.67` temporarily and migrate before adopting `v0.0.68+`.

## v0.0.110

- Added `scripts/promptbranch-aliases.sh` with common Promptbranch aliases such as `pbs` for `promptbranch state`.
- Added `scripts/setup-promptbranch-shell.sh` to install the aliases into Bash or Zsh rc files.
- Added `scripts/promptbranch-statusline.sh` for compact Promptbranch state output in shell prompts or tmux footer/status lines.
- The status helper resolves the nearest inherited `.pb_profile` directory.
