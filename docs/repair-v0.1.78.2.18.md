# Repair v0.1.78.2.18 — prompt-file smoke diagnostics and strict button causality

## Baseline and release

- Accepted baseline remains: `v0.1.78.2.16` until adoption evidence says otherwise
- Superseded candidate: `v0.1.78.2.17`
- Repair release: `v0.1.78.2.18`
- Continuity: includes the `v0.1.78.2.17` prompt-file submit-policy repair plus the `v0.1.78.2.18` harness/causality hardening
- Scope: narrow Promptbranch repair for `pb ask --prompt-file` validation evidence and prompt-file submit causality

## Reason

After installing `v0.1.78.2.17`, the focused live smoke exited immediately after:

```text
pb ask "Use the prompt file." --prompt-file /tmp/... --json
cleanup
```

The script had `set -euo pipefail` and redirected `pb ask` output to a temporary JSON file. If `pb ask` exited non-zero, shell execution stopped before the Python validator ran, and the EXIT trap deleted both the prompt file and JSON output. That made the remaining live failure unobservable.

The same repair also tightens submit causality: prompt-file asks may fall back to keyboard Enter only when button dispatch is unavailable or fails before dispatch. Once a visible/enabled send button has been clicked, a prepare-token-only state remains a hard failure and Promptbranch must not press keyboard Enter afterward as a comparison/fallback, because that creates ambiguous submit causality.

## Files changed

- `scripts/smoke-pb-ask-prompt-file.sh`
  - Captures the `pb ask` exit code instead of exiting early under `set -e`.
  - Preserves the JSON diagnostic file on failure.
  - Emits `pb_ask_exit_code`, `output_json`, and the parsed payload or raw invalid JSON preview.
  - Deletes the JSON only after a successful smoke.
- `promptbranch_browser_auth/client.py`
  - Skips post-dispatch keyboard Enter variant comparison for prompt-file button-first asks.
  - Records `skipped_prompt_file_button_first_policy` in submit evidence when button dispatch reached prepare-only/no-commit.
- `tests/test_project_list_browser_client.py`
  - Adds coverage proving prompt-file button-dispatch prepare-only does not press keyboard Enter afterward.
- `tests/test_promptbranch_shell_scripts.py`
  - Updates smoke-script contract expectations for retained diagnostic JSON and exit-code reporting.
- Version/control-surface files updated for `v0.1.78.2.18`.

## Validation performed

- Python compile check for touched runtime modules.
- Focused pytest for prompt-file CLI/API/service/browser/smoke behavior.
- Bash syntax validation for the prompt-file smoke script.
- ZIP integrity and hygiene validation.

## Validation not performed here

- Live ChatGPT `pb ask --prompt-file` smoke was not run in this environment.
- Full release-control was not run here.
- Artifact adoption/current verification was not run here.

## Scope confirmation

No normal slice advanced. This repair changes only prompt-file smoke diagnostics and prompt-file submit causality behavior. It does not change CV generator code, Project Source add/remove/overwrite behavior, ChatGPT Project deletion behavior, artifact registry behavior, Docker provenance policy, or release-control adoption semantics.
