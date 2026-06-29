# Release candidate v0.1.104.3

Repair-only candidate for `v0.1.104`.

`v0.1.104.3` preserves the sandbox mutation verification and rollback evidence gate from `v0.1.104`, preserves the project-remove frozen scheduler timeout repair from `v0.1.104.1`, and preserves the Project ensure create/reuse browser timeout repair from `v0.1.104.2`.

This repair removes the `--run-isolated-release-tests` / `--run-slice-tests` release-control mode introduced in the failed `v0.1.104.2` candidate. The release line returns to the simpler policy: focused local checks may be run during artifact creation, but accepted/current status requires the full release-control/adoption gate.

`v0.1.105` remains deferred: Sandbox correction promotion readiness check.
