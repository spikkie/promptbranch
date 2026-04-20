# How to upgrade from old `chatgpt_*` names

## Goal

Move from the old `chatgpt`/`chatgpt_*` naming to `promptbranch`/`promptbranch_*`.

## Main replacements

- CLI command: `chatgpt` -> `promptbranch`
- Python package: `chatgpt_workflow` -> `promptbranch`
- service app: `chatgpt_container_api:app` -> `promptbranch_container_api:app`
- image tag: `chatgpt-docker-service:*` -> `promptbranch-service:*`

## Config and state migration

- config: `~/.config/chatgpt-cli/config.json` -> `~/.config/promptbranch/config.json`
- state: `.chatgpt_cli_state.json` -> `.promptbranch_state.json`

## More detail

Read the full migration note:

- `UPGRADING.md`
