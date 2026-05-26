# Repair v0.0.276.18

Base release: `v0.0.276.17`
Repair version: `v0.0.276.18`
Release type: repair

## Reason

Fix the protocol ask/release timeout mismatch where the local service client could time out before the browser service finished waiting for ChatGPT to complete an answer. The observed failure mode is `service_read_timeout` while the ChatGPT UI can still be generating and eventually produce a valid protocol answer.

## Files changed

- `promptbranch_cli.py`
  - Added a browser-response timeout floor for protocol ask/release service-client reads.
  - Kept protocol service read timeout above the browser-service assistant response wait budget plus fresh-turn and safety buffer.
- `docker-compose.chatgpt-service.yml`
  - Updated the service image tag to `promptbranch-service:0.0.276.18`.
  - Added default `CHATGPT_RESPONSE_TIMEOUT_MS=1200000` so the browser service can wait up to 20 minutes for slow artifact-producing answers.
- `tests/test_promptbranch_cli.py`
  - Added regression coverage for the protocol service-client timeout floor.
  - Repaired stale/corrupted protocol reply parsing and lifecycle fixture invocations so the focused suite can validate this repair.
- `tests/test_compose_timeout_policy.py`
  - Added regression coverage for Compose image tag and response-timeout policy.
- Version metadata and current-version expectations updated to `v0.0.276.18`.

## Validation performed

- `python -m py_compile promptbranch_cli.py promptbranch_browser_auth/client.py promptbranch_container_api.py promptbranch_service_client.py`
- Focused pytest suite covering protocol timeout behavior and service metadata.
- ZIP hygiene verification: root-level repository contents, no wrapper folder, no nested ZIPs, no cache files, and version metadata checked.

## Scope control

No slice or line was advanced. This repair only fixes timeout durability and release metadata consistency for the intended v0.0.276 repair line.
