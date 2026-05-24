# Release v0.0.271

## Scope

Human-summary field extraction hardening only.

## Changes

- Hardened `scripts/post-release-validation.sh` human lifecycle summary rendering.
- The finalizer now reads the raw lifecycle-status snapshot file for display-only extraction of:
  - runtime code version
  - VERSION file version
  - adopted artifact/source version
  - candidate count
  - warning/blocker codes
- Kept machine JSON contracts unchanged.
- Kept lifecycle-status JSON output unchanged.
- Kept artifact intake, install, upload, adopt, policy-sync, and Git behavior unchanged.

## Validation intent

This release only improves operator readability when the raw lifecycle-status snapshot already contains populated fields but the compact finalizer summary does not.
