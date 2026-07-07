# v0.1.103.10.69 — add install.sh strict all-all release gate

## Scope

Add a repo-root `install.sh` helper that runs the strict full release gate for a new ZIP release:

1. Install the exact candidate ZIP.
2. Run default product validation.
3. Run explicit external ChatGPT live validation.
4. Require live validation to pass.
5. Adopt only if the combined validation verdict is `GO`.
6. Emit `pb artifact current --all --json` evidence after adoption.

## Command

```bash
./install.sh v0.1.103.10.69
```

Optional explicit ZIP path:

```bash
./install.sh v0.1.103.10.69 "$HOME/Downloads/chatgpt_claudecode_workflow-2_v0.1.103.10.69.zip"
```

## Out of scope

- No release-control behavior change.
- No external-live classification change.
- No Cloudflare workaround.
- No host-CDP/session-manager.
- No copied-profile trust.
- No ChatGPT Project deletion.
