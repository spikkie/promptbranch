# Patchright upgrade notes

- Pinned `patchright==1.58.2` in `requirements.txt`.
- `setup-env.sh` now installs Patchright-managed Chrome via `patchright install chrome`.
- `Dockerfile` now installs Chrome through Patchright and only Chromium deps via Playwright.

Recommended runtime for Patchright:
- `channel="chrome"`
- `headless=False` for first-session establishment
- reuse the same persistent profile for later runs
