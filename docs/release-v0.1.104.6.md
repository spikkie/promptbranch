# Release candidate v0.1.104.6

## Slice

Repair-only continuation of:

```text
v0.1.104 — Sandbox mutation verification and rollback evidence gate
```

## Repair title

```text
Project Sources challenge/interstitial readiness repair
```

## Summary

This repair improves Project Source ZIP-add readiness handling when the browser reaches a ChatGPT/Cloudflare challenge/interstitial instead of the real Project Sources surface.

The repair detects challenge/interstitial text, waits for bounded settlement, and returns explicit structured failure evidence if the interstitial persists. It does not attempt to bypass Cloudflare or automate unsafe challenge handling.

## Not accepted/current until

`v0.1.104.6` is only accepted/current after full release-control passes and `pb artifact current --json` proves runtime/source/artifact/registry alignment.
