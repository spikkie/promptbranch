# Release candidate v0.1.104.4

`v0.1.104.4` is a repair-only candidate for the `v0.1.104 — Sandbox mutation verification and rollback evidence gate` slice.

It preserves:

- `v0.1.104` sandbox mutation verification and rollback evidence gate;
- `v0.1.104.1` project-remove frozen scheduler timeout repair;
- `v0.1.104.2` Project ensure create/reuse timeout repair;
- `v0.1.104.3` removal of isolated release-test mode.

It repairs the live Project Source ZIP add failure where the service returned a 504 because the Project Sources tab did not become visible. Source add/remove/capability flows now navigate directly to the Project Sources route and accept a verified sources surface even if the tab control itself is not visible.

`v0.1.105 — Sandbox correction promotion readiness check` remains deferred until this repair is accepted/current.
