# Release v0.0.278.20

## Base

Built from `chatgpt_claudecode_workflow_v0.0.278.19.zip`.

## Reason

`v0.0.278.19` correctly rejected stale visible JSON using request markers, but it could still enter the response-wait path after URL-only submit confirmation. In warm old tasks this caused long fail-closed waits when the prompt was not causally proven to have been accepted.

## Changes

- Require submit causality before response extraction.
- Do not accept same-conversation URL as sufficient submit confirmation by default.
- Accept only running-state evidence (`stop_button` / `composer_running`) or prompt-specific user-turn echo (`user_turn_echo`) before entering response wait.
- Return `submit_causality_not_confirmed` instead of waiting for a response when causality is not proven.
- Preserve warm-task hydration reuse and request-bound JSON stale-answer guard.

## New evidence fields

- `submit_causal_confirmation_required`
- `submit_causal_confirmation_verified`
- `submit_causal_confirmation_reason`
- `submit_url_only_confirmation_rejected`
- `submit_user_turn_echo_found`
- `submit_user_turn_echo_seconds`
- `response_wait_skipped`
- `response_wait_skipped_reason`

## Validation

- Python compilation.
- Focused pytest coverage for stale-answer rejection, URL-only submit rejection, user-turn echo confirmation, and existing fast-return behavior.

## Slice / line advancement

No slice or line was advanced. This is a normal compatibility release because the local workflow does not support fourth-field repair versions.
