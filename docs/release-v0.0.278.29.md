# Release v0.0.278.29

Base: `chatgpt_claudecode_workflow_v0.0.278.28.zip`

Scope: diagnostic-only continuation of the ChatGPT submit causality line.

Changes:

- Classify `prepare_only_then_idle_without_commit` when `/backend-api/f/conversation/prepare` returns conduit tokens, all tokens remain unconsumed, stream status is complete/idle, and no backend user-message commit is proven.
- Preserve the previous `stream_started_without_user_message_commit` branch for real post-prepare `IS_STREAMING` evidence.
- Add `prepare_token_set_not_consumed` and complete/idle stream-status evidence fields.
- Tighten post-prepare UI-error detection by removing broad `text=error`, `text=failed`, and `[class*=error]` matches and requiring strict non-empty alert/toast/error text.
- Add diagnostic keyboard-submit variant comparison after button-click prepare-only failures. The comparison re-fills the prompt and presses `Enter`, recording whether keyboard submit reaches the same prepare-only/idle state or a different finalization path. It does not weaken stale-answer guards.

Validation:

- `python3 -m py_compile` over repository Python files.
- Focused pytest for submit causality and release/version/container checks.

Adoption rule:

Do not adopt this release unless the live stale-guard run returns the fresh sentinel. This release remains fail-closed by design.
