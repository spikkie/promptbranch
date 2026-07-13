# v0.1.103.10.86 — make the diagnostic runner import repository modules reliably

This diagnostic-only repair preserves the v0.1.103.10.85 A/B transaction implementation and changes only its launcher/import bootstrap.

`pb-project-source-ab-diagnostic.py` now adds the repository root to `sys.path` before importing `promptbranch_service_client`. The shell launcher also exports the repository root through `PYTHONPATH`, so the diagnostic works from the repository root, another working directory, and the `install.sh --diagnostic-project-source-ab` path.

No Project Source transaction logic, release upload, test adoption, Cloudflare handling, or browser trust policy changes.
