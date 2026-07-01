# v0.1.103.10.18 — pb test api coverage runner

## Scope

Add a full rerunnable API coverage script and expose it through `pb test api`.

## Safety

- Browser-owning API calls are run sequentially.
- Destructive endpoints are skipped or guard-tested by default.
- Project Source mutation requires explicit `--allow-source-add --source-file`.
- ChatGPT Project deletion remains frozen.

## Commands

```bash
pb test api --json
pb test api --allow-source-add --source-file chatgpt_claudecode_workflow-2_v0.1.103.10.18.zip --json
```
