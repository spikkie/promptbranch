# Release v0.0.278.37

Regression-control release built from `chatgpt_claudecode_workflow_v0.0.278.36.zip`.

## Purpose

Preserve submit evidence when the service-level internal deadline fires and explicitly distinguish backend-confirmed-but-DOM-not-visible submits from true submit failures.

## Changes

- Record latest in-flight ask progress inside `promptbranch_browser_auth.client`.
- Preserve `submit_evidence`, `conversation_url`, and `ask_phase_timings` in `/v1/ask` when the internal service deadline guard triggers.
- After submit confirmation, run a post-submit DOM user-turn visibility probe.
- Add submit evidence fields for backend-only visibility classification:
  - `post_submit_user_turn_visibility_checked`
  - `post_submit_user_turn_visible`
  - `post_submit_user_turn_visibility_status`
  - `backend_confirmed_user_turn_id`
  - `backend_confirmed_user_turn_index`
  - `submit_backend_confirmed_but_user_turn_not_visible`
  - `submit_visibility_classification`
- Return `submit_confirmed_backend_only_ui_not_hydrated` when backend conversation detail confirms the submitted user turn but the DOM transcript does not show it.

## Validation

- `python3 -m py_compile promptbranch_browser_auth/client.py promptbranch_container_api.py`
- Focused endpoint regression for internal-deadline submit-evidence preservation.
- Focused container API partial-timeout regression.

## Acceptance note

This release is diagnostic/control-plane hardening only. It should not be adopted unless live stale-guard diagnostics return either fresh sentinel success or a structured failure that preserves submit evidence.
