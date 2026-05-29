# Release v0.0.278.47

Diagnostic-only release built from v0.0.278.46.

## Purpose

Decompose the known-good full trusted-refill retry path before making any further speed changes.

The preceding failed speed candidates showed that a fast/slim refill can verify visible composer text while still producing prepare-only/no-commit behavior. This release keeps the v0.0.278.42/v0.0.278.46 submit behavior unchanged and adds evidence to determine which part of the slower full refill path is required.

## Behavior

No intended behavior changes:

- raw Enter remains primary submit dispatch
- prepare-only fast-fail remains enabled
- trusted-refill + Enter remains the retry path
- fast latest-turn answer promotion remains unchanged
- exact current sentinel / marker gates remain unchanged

## Added diagnostics

The retry full refill evidence now includes:

- `diagnostic_fill_path`
- `phase_timings`
- `phase_order`
- `attempt_phase_timings`
- `verification_attempts`
- `fill_event_probe_install`
- `fill_event_probe_events`
- decomposed clear / clipboard / paste / dwell / verification timings

The goal is to separate:

- focus/click time
- Control+A / Backspace clear time
- clipboard permission time
- clipboard write time
- Control+V dispatch time
- post-paste dwell time
- React/composer verification time
- passive paste/beforeinput/input/key/focus events

## Validation

Focused validation performed from clean extracted ZIP:

- `python3 -m compileall -q .`
- focused pytest suite covering browser client, CLI, container API, service client, parser, and compose timeout policy

