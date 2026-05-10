# Promptbranch Ask/Reply Contract

When Promptbranch sends a protocol-aware request, the assistant reply must include exactly one machine-readable reply envelope.

Automation uses only the JSON between these markers:

```text
BEGIN_PROMPTBRANCH_REPLY_JSON
{ ...valid JSON matching promptbranch.ask.reply schema_version 1.0... }
END_PROMPTBRANCH_REPLY_JSON
```

Human-readable explanation may appear before or after the envelope, but Promptbranch automation ignores it.

The reply envelope must include:

- `schema`: `promptbranch.ask.reply`
- `schema_version`: `1.0`
- `request_id`
- `status`
- `result_type`
- `summary`
- `baseline`
- `changes`
- `artifacts`
- `validation`
- `next_step`

Artifact entries are candidates only. They must not be treated as accepted baselines until Promptbranch downloads, verifies, migrates, tests, and adopts them through explicit guarded commands.
