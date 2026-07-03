# v0.1.103.10.37 — source-add auth bootstrap accepts project-page readiness

## Problem

`v0.1.103.10.36` fixed successful auth-readiness evidence export, but full release-control adoption failed before Project Source add. The pre-source-add auth bootstrap targeted the Promptbranch project home URL and produced a valid logged-in project page:

- `logged_in=true`
- `challenge_detected=false`
- `cloudflare_cleared=true`
- `project_page_visible=true`
- `composer_visible=false`

The strict browser validation still required `composer_visible=true`, which is too strong for a Project Source preflight on `/project`.

## Repair

Release-control now sets `PROMPTBRANCH_BROWSER_VALIDATION_ALLOW_PROJECT_PAGE_READY=1` only for the `pre_source_add` auth bootstrap phase.

`pb-browser-cloudflare-validation.sh` remains strict by default. It only accepts a missing composer when all of these are true:

- explicit `PROMPTBRANCH_BROWSER_VALIDATION_ALLOW_PROJECT_PAGE_READY=1`
- target URL path ends with `/project`
- `project_page_visible=true`
- `logged_in=true`
- `challenge_detected=false`

## Scope boundaries

- Keep `v0.1.103.10.36` evidence-export normalization.
- Keep `v0.1.103.10.35` held-session clear strategy.
- Keep composer readiness required for ask/live/conversation validation.
- Preserve Project Source add and full direct/full localhost validation as release-blocking.
- No browser/session architecture changes.
- No ChatGPT Project deletion.
