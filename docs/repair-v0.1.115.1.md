# v0.1.115.1 — Release-live profile ownership handoff repair

`v0.1.115` is immutable and repair-required. Its strict host run proved all non-live and primary transport gates, but the first continuous external-live operation failed because cross-process browser-profile contention bypassed the advertised bounded wait queue.

The repair makes the file lock obey the configured queue deadline, adds owner diagnostics, and adds an explicit two-layer release barrier between live preflight and continuous live execution. The normal PBAI-001 scope is unchanged.
