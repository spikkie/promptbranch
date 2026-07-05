# v0.1.103.10.56 — wire release-live-continuous into real CLI test dispatch

## Scope

This repair keeps the continuous release-live browser-session design from v0.1.103.10.55 and fixes the CLI dispatch gap exposed by the real release-control run.

## Bug

`pb test release-live-continuous` was present in parser/help and release-control invoked it, but `cmd_test()` did not dispatch the command. The command therefore failed with:

```text
RuntimeError: Unknown test command: release-live-continuous
```

## Fix

`cmd_test()` now dispatches `release-live-continuous` to `cmd_test_release_live_continuous()`.

## Regression coverage

The focused CLI tests now cover:

- parser support for `pb test release-live-continuous`
- real `cmd_test()` dispatch to `cmd_test_release_live_continuous()` with a fake backend

## Out of scope

- no host-CDP/session-manager
- no copied profile trust
- no private backend-api operational dependency
- no adoption/current claim
