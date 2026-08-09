# v0.1.126.1.1.1 — Project Source text-add readiness and bounded recovery repair

## Authority

- Built from the exact immutable `v0.1.126.1.1` release artifact (`6ef6aa2afc7afb064ff8ae9ef3fb027760ef2c0e2e6d6d6e1a33819f8d59b484`).
- Accepted/current baseline remains `v0.1.125.3.4.2` until this repair reaches `FINAL_VERIFIED`.
- Release mode: repair; no scope advance.

## Live failure repaired

The `v0.1.126.1.1` operator-host run proved Docker runtime preparation and the shared source fingerprint, then failed in `browser.project_source_add_text`. The current ChatGPT Project Source UI advertised `Text input`, but the Add/Save button remained disabled. The browser selector surface still allowed a generic `input[type=text]` as the text value editor, which can resolve the title field instead of the text body. The service returned HTTP 504, and the full integration harness re-raised the exception before the already-existing zero-request reconciliation/retry logic could run.

## Repair

- Text source value selection now targets only body editors (`textarea`, contenteditable, or non-input textbox roles); the generic title-input fallback is removed from body selection.
- Save readiness gets two bounded stabilization attempts: re-fill exact body/title values, dispatch input/change/blur events, perform a no-net-change keyboard edit for text bodies, re-resolve the save button, and verify enabled state.
- Disabled-save failures carry structured readiness evidence including value lengths/matches, title state, button disabled attributes, save-request summary, and visible dialog preview.
- `ResponseTimeoutError` can carry structured payloads through the container HTTP boundary.
- Deferred integration steps preserve structured exception payloads instead of re-raising immediately.
- With zero observed save requests, the harness first lists authoritative Project Sources. A correlated late-visible source is accepted, an empty surface permits one controlled retry, and unrelated/ambiguous state remains release-blocking.

## Acceptance

Construction validation does not accept this release. First run a focused live `project_source_add_text` proof. Only after that focused proof is green should the canonical full release lifecycle be retried. Final acceptance still requires `FINAL_VERIFIED`, independent all-state verification with no failed invariants, exact Git push/Project Source publication evidence, and production-image convergence on port 8000.
