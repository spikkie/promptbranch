# Release candidate v0.1.104.2

Repair-only candidate for `v0.1.104`.

`v0.1.104.2` preserves the sandbox mutation verification and rollback evidence gate from `v0.1.104`, preserves the project-remove frozen scheduler timeout repair from `v0.1.104.1`, and repairs only the Project ensure create/reuse browser timeout path.

The repair adds extended Project ensure service timeout handling and post-timeout exact Project resolve recovery. It also introduces an isolated release-test mode for pre-adoption focused validation. Isolated release tests are not an adoption/current gate and cannot be used with `--adopt-after-validation`.

`v0.1.105` remains deferred: Sandbox correction promotion readiness check.
