# v0.1.128.2.7

Repair scope: deterministic offline wheel-build authority.

- Baseline remains accepted/current `v0.1.128.2.6.1.1.1` until the canonical lifecycle proves otherwise.
- Supersedes the long `.2.6.1.1.*` candidate chain as the sole active repair candidate; historical failed artifacts remain evidence only.
- Keeps the change-only-`VERSION` invariant.
- Adds one canonical wheel builder using the PEP 517 backend declared by `pyproject.toml`.
- Explicitly preflights backend/build requirements and emits `build_backend_unavailable` when they cannot be satisfied.
- Builds without package-index access and without PEP 517 environment creation.
- Forbids raw `pip wheel` subprocesses in release-validation tests.
- Acceptance, adoption, Git publication, Project Source publication, and production promotion are not claimed by this construction document.
