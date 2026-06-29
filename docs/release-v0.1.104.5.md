# Release candidate v0.1.104.5

`v0.1.104.5` is a repair-only candidate for the `v0.1.104 — Sandbox mutation verification and rollback evidence gate` slice.

It preserves the sandbox verification slice and all previous `v0.1.104.x` repairs while adding Project Sources route hydration recovery for the live failure where `?tab=sources` was present but the Sources surface was not hydrated.

The candidate does not advance to `v0.1.105`.
