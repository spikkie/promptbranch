# Repair v0.1.104.4 — Project Sources direct-route visibility repair

## Base and scope

- Accepted/current baseline before the repair line: `chatgpt_claudecode_workflow-2_v0.1.103.zip`.
- Failed normal candidate: `chatgpt_claudecode_workflow-2_v0.1.104.zip`.
- Failed repair candidates preserved: `v0.1.104.1`, `v0.1.104.2`, `v0.1.104.3`.
- Repair candidate: `chatgpt_claudecode_workflow-2_v0.1.104.4.zip`.
- Normal slice preserved: `v0.1.104 — Sandbox mutation verification and rollback evidence gate`.
- Scope advancement: none. `v0.1.105` remains deferred.

## Failure being repaired

Full release-control for `v0.1.104.3` failed during pre-validation Project Source ZIP add with:

```text
504 error for POST http://localhost:8000/v1/project-sources: Project Sources tab did not become visible
```

The service was already healthy and running `0.1.104.3`, but the browser source-add operation navigated to the Project home route and required a visible `Sources` tab before using the source surface. In the failed run the tab did not become visible, so the operation failed before file source persistence verification could begin.

## Repair

- Open Project Source add/remove/capability operations directly on the `?tab=sources` route.
- Add a Project Sources surface probe that accepts an already-rendered sources surface without requiring the tab control itself.
- If the tab control is absent, retry by navigating directly to the `?tab=sources` route and verify the surface with read-only evidence.
- Keep release blocking if neither the tab nor a verified sources surface becomes visible.
- Preserve all sandbox mutation verification behavior from `v0.1.104` and prior repairs.

## Validation

Focused validation covered:

- direct sources-route surface acceptance without a visible tab;
- direct-route retry when the tab is missing;
- source-add operation opening `?tab=sources` before probing;
- control-surface validation;
- version-surface validation;
- Artifact Guardian and artifact verify.
