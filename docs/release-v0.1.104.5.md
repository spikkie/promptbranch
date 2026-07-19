# Release v0.1.104.5

`v0.1.104.5` is a repair candidate that makes offline release-validation pytest execution hermetic. Every subprocess receives explicit temporary HOME, XDG, Promptbranch profile, project state/config, and cache authority. A child-process preflight verifies the paths before the test node begins and fails closed if repository `.pb_profile` remains reachable.

The `v0.1.104.4` visual completion/envelope repair, all 13 sandbox gates, current-turn readiness, one-reload recovery, fresh direct policy, independent localhost policy, and ten-step release manifest are unchanged.

This candidate is not accepted/current until strict host validation passes 10/10 and evidence-bound adoption emits `release_adopted_and_verified`.
