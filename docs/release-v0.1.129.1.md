# v0.1.129.1 — release-source version scan isolation corrective

Repair-only successor to `v0.1.129`.

- Preserves the complete `v0.1.129` read-only external-application pilot bootstrap.
- Reuses `promptbranch_source_fingerprint.iter_release_source_files()` for current-version hard-code validation.
- Excludes operator `.pb_profile` runtime history from release-source authority without deleting or rewriting that evidence.
- Keeps fail-closed detection for actual executable/packaging source and `.promptbranch-release.json`.
- Adds a regression proving runtime-history exclusion and canonical-source rejection.
- Adds no application mutation, deployment, acceptance, or scope authority.

Accepted/current remains `v0.1.128.2.7` until the canonical lifecycle reaches `FINAL_VERIFIED`. Next normal after repair acceptance is `v0.1.130`.
