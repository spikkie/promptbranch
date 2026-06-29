# Release v0.1.104.7

`v0.1.104.7` is a repair-only rollback candidate for the `v0.1.104` line.

## Repair slice

```text
v0.1.104.7 — rollback to v0.1.104.1 source line
```

## Preserved normal slice

```text
v0.1.104 — Sandbox mutation verification and rollback evidence gate
```

## Scope

This release intentionally returns to the `v0.1.104.1` source line and drops the `v0.1.104.2` through `v0.1.104.6` Project ensure, isolated release-test, Project Sources direct-route, route-hydration, and challenge/interstitial experiments.

It preserves:

- sandbox mutation verification behavior from `v0.1.104`
- sandbox-only mutation behavior from `v0.1.103`
- project-remove frozen scheduler timeout repair from `v0.1.104.1`
- no ChatGPT Project deletion
- no Project Source mutation behavior change
- no artifact adoption behavior change
- no normal scope advancement

## Validation status

Focused validation is required before handoff. Full release-control/adoption remains required before this candidate may be called accepted/current.
