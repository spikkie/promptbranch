# Failure classification

Classify before retrying:

- **invalid input / contract failure** — deterministic input/schema/precondition failure;
- **authority mismatch** — requested action lacks the required control-plane authority;
- **route/identity mismatch** — browser/project/conversation is not the requested target;
- **rate limit / cooldown** — explicit service/browser rate-limit evidence;
- **timeout** — operation exceeded a defined deadline; timeout alone does not prove submission failed or succeeded;
- **validation failure** — operation completed but required invariant/evidence is false;
- **retryable operational failure** — canonical state can be resumed without changing immutable artifact identity;
- **product defect** — reproducible canonical-path behavior violates the deterministic contract.

Do not collapse these into a generic retry loop.
