# v0.1.103.10.54 — fast release-control run-all replay harness

Adds a fast release-control run-all replay harness for orchestration/control-flow scenarios before long live Docker/ChatGPT validation runs. The harness includes the `live_bootstrap_429_guardrail_with_persisted_cooldown` scenario from v0.1.103.10.53 and asserts that ask_live, visual_artifact_roundtrip, and release_live are not launched while import_smoke and artifact_guard remain represented.
