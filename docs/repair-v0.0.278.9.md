# Repair v0.0.278.9 — Submit timing reconciliation

## Base release

`v0.0.278.8`

## Repair version

`v0.0.278.9`

## Reason

Live validation of `v0.0.278.8` showed that the send-button path worked and avoided the earlier Enter fallback path, but submit timing was still not mathematically reconcilable with service-log timestamps. In particular, `submit_total_seconds` could include a long wall-clock delay that was not represented in any smaller timing field.

The most likely missing segment was the post-dispatch composer snapshot taken after clicking Send or pressing Enter and before submit confirmation polling. This repair exposes that segment explicitly and includes it in submit accounting.

## Files changed

- `promptbranch_browser_auth/client.py`
  - added post-dispatch snapshot timing fields;
  - included post-dispatch snapshot time in `submit_wait_seconds`;
  - added monotonic timestamp fields for submit start, dispatch start/completion, confirmation start, and confirmation completion;
  - added `submit_accounted_seconds` and `submit_unaccounted_seconds` so live logs can be reconciled against JSON timings;
  - propagated the new fields into `ask_phase_timings`.
- `tests/test_project_list_browser_client.py`
  - extended the focused submit test to assert the new reconciliation fields.
- version metadata files:
  - `VERSION`
  - `pyproject.toml`
  - `promptbranch_version.py`
  - `promptbranch.egg-info/PKG-INFO`
  - `docker-compose.chatgpt-service.yml`
- version expectation tests updated from `v0.0.278.8` to `v0.0.278.9`.

## Validation performed

- `python3 -m py_compile promptbranch_browser_auth/client.py`
- focused submit reconciliation test:
  - `pytest -q tests/test_project_list_browser_client.py::test_submit_prompt_button_path_skips_slow_user_turn_dom_wait_after_running_confirmation`

Additional packaging verification was performed before producing the ZIP:

- ZIP opens successfully;
- ZIP root contains repository contents directly;
- `VERSION` is `v0.0.278.9`;
- no wrapper folder;
- no cache/temp/local-state files;
- no nested ZIPs.

## Slice / line status

This is a repair release only. No slice was advanced. No line was opened. No planned scope was changed.
