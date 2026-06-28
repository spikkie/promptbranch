# Repair v0.1.100.1 — text-source add stale-inflight recovery diagnostics/verification repair

Base failed release: `v0.1.100`
Repair version: `v0.1.100.1`
Accepted/current baseline before repair: `chatgpt_claudecode_workflow-2_v0.1.99.1.zip`

## Reason

The `v0.1.100` full release-control run failed in the browser/source-kind matrix at `project_source_add_text` with a committed save request, one stale inflight request, and no verified Project Sources surface proof. The new read-only command execution slice was not the failing component.

## Scope

- Preserve `v0.1.100 — First controlled read-only validation command execution` unchanged.
- Add bounded post-commit Project Sources surface re-open/re-read diagnostics for text-source stale-inflight recovery.
- Accept recovery only with exact text identity/content proof.
- Keep empty/unreadable source surfaces release-blocking.
- Do not advance to `v0.1.101`.

## Validation status

Focused validation was run for project-source recovery tests, loop/CLI/control-surface/version tests, compileall, shell syntax, Artifact Guardian, and artifact verify. Full release-control/adoption is pending operator execution.
