# v0.1.103.10.39 — run-all live tests auto-seed from Docker standard browser profile

`v0.1.103.10.38` was accepted/current with full release validation, but live-only run-all tests were skipped because `.pb_profile_local_debug` was missing.

This repair makes `--run-all-tests` execute those live-only tests by creating `.pb_profile_local_debug` from the Docker standard browser profile `.pb_profile/browser/default` when the seed profile is missing. Volatile Chrome lock/debug artifacts are excluded from the copy.

If both `.pb_profile_local_debug` and `.pb_profile/browser/default` are missing, the live phase is release-blocking. This is intentional: `--run-all-tests` should not silently skip live-only tests.

Out of scope:

- host-CDP/session-manager architecture
- Project Source mutation behavior changes
- ChatGPT Project deletion
- full direct/full localhost validation behavior changes
