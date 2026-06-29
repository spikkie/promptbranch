# Repair v0.1.104.5 — Project Sources route hydration recovery repair

## Base

- Accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.103.zip`.
- Failed normal candidate: `chatgpt_claudecode_workflow-2_v0.1.104.zip`.
- Failed repair candidates: `v0.1.104.1`, `v0.1.104.2`, `v0.1.104.3`, `v0.1.104.4`.
- Repair candidate: `chatgpt_claudecode_workflow-2_v0.1.104.5.zip`.

## Reason

`v0.1.104.4` still failed Project Source ZIP add before release validation. The browser reached `?tab=sources`, but no Project Sources card, empty state, add/upload affordance, or verified Sources surface rendered. A bare Sources URL is therefore insufficient evidence.

## Repair

- Strip transient Cloudflare challenge query parameters while constructing the Project Sources route.
- Add richer Project Sources surface probe diagnostics, including visible text preview and likely challenge state.
- Add bounded route recovery: Project home -> Sources, Sources reload, Project home -> Sources final.
- Accept recovery only when concrete Sources surface evidence is visible.
- Preserve fail-closed behavior when the surface remains absent.

## Scope control

No normal-slice scope advances. `v0.1.105` remains deferred. No Project Source mutation semantics, artifact adoption behavior, deployment, Kubernetes mutation, patch/diff artifact generation, or ChatGPT Project deletion behavior is changed.
