# v0.1.103.10.64 — release-live-continuous trusted conversation direct path

## Problem

The attached session log showed `release-live-continuous` opened the trusted project conversation URL and reached a healthy state:

- `logged_in=True`
- `composer_visible=True`
- `challenge_detected=False`

Then it navigated away to `https://chatgpt.com/` for `project-ensure-home` discovery and the page/context closed with `TargetClosedError`.

## Repair

When `--warmup-conversation-url` is a project-scoped conversation URL (`/g/.../c/...`), `release-live-continuous` now:

- derives the project home URL from the conversation URL;
- records a synthetic trusted project result;
- skips root project discovery;
- does not create/discover/delete projects;
- sends the bootstrap prompt to the trusted conversation URL;
- sends the first ask in the resulting same conversation/session.

## Scope boundaries

- No Cloudflare workaround.
- No host-CDP/session-manager.
- No copied-profile trust.
- No private backend-api operational dependency.
- No ChatGPT Project deletion.
- No claim that external live validation passes.
