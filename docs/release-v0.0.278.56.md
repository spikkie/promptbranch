# v0.0.278.56 — fast one-shot ask path

## Summary

Restores the default `pb ask` behavior to the simple UI-equivalent path from the v0.0.278.48 line: fill the prompt once, attach requested files, press Enter once, wait for the answer, and print it.

## Scope

- Built from `chatgpt_claudecode_workflow_v0.0.278.48.zip`.
- Preserves existing ask CLI options, including `--prompt-file`, `--file`, repeatable `--attach/--attachment`, `--json`, `--conversation-url`, protocol/parse-reply flags, `--keep-open`, and `--retries`.
- Removes retry/refill/send-button fallback behavior from the default submit path.
- Keeps answer freshness delegated to the normal post-submit answer wait.

## Non-goals

- No trusted refill retry.
- No retry Enter after prepare-only.
- No retry send-button click.
- No submit-backend archaeology in the default path.

## Validation

Focused tests and ZIP hygiene checks were run before packaging.
