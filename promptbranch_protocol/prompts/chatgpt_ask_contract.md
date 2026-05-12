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

## Locked MVP-F decisions

- In protocol mode, the reply envelope is required; prose without the envelope is invalid.
- Plain/manual `pb ask` may still use prose-only answers, but automation must ignore prose outside the envelope.
- If multiple answers or multiple envelopes are present, Promptbranch must fail closed and require an explicit `answer_id`.
- Artifact download is direct-URL-only for MVP. If no concrete `download.url` exists, report the candidate but do not download.
- Artifact URLs are temporary. Include `answer_id` and `url_seen_at` when available so the host can re-resolve later.
- Repair releases must be explicit with `release_type=repair`, `base_release`, `target_version`, and `repair_reason`.
- MVP artifacts are ZIP-first. Non-ZIP outputs are diagnostics only until a separate baseline path is designed.
