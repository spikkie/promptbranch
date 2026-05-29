# v0.0.278.49 — retry-fill timing decomposition diagnostics

Base: `chatgpt_claudecode_workflow_v0.0.278.48.zip`.

Scope: diagnostic-only evidence capture for the trusted-refill retry fill path.

Behavioral constraints:

- Preserve `.48` submit behavior.
- Preserve raw Enter primary dispatch.
- Preserve trusted-refill retry behavior.
- Preserve exact-marker/fresh-answer gates.
- Preserve the `.48` classifier rule: `/backend-api/f/conversation/prepare` is not a final submit confirmation.
- Do not shorten or remove any wait/dwell behavior.

Diagnostics added:

- `fill_timing_decomposition`
- `fill_attempts`
- `fill_evidence.timing_decomposition`
- phase timings for:
  - trusted-paste attempt
  - composer clear
  - focus click
  - Control+A
  - Backspace
  - clipboard permission grant
  - clipboard write
  - Control+V paste
  - post-paste dwell
  - composer verification

Purpose:

Identify which part of `retry_fill_seconds` dominates the successful retry path before any future timing optimization is attempted.
