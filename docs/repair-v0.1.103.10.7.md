# v0.1.103.10.7 — generated-cache-free release transport repair

`v0.1.103.10.7` repairs the release transport ZIP produced for the standard browser auth-only validation slice.

The previous candidate was rejected by release import planning because `.pytest_cache/` entries were present inside the ZIP. This repair keeps runtime behavior unchanged and repackages the candidate without generated cache entries.

Out of scope:

- Project Source mutation
- Cloudflare browser envelope changes
- Patchright/CDP session-manager changes
- Artifact adoption claims
- Git commit or push
