# Promptbranch Artifact Naming

Status: active from v0.1.73

## Canonical artifact filename

All future Promptbranch-managed release ZIPs use one filename grammar:

```text
<repo_id>_<version>.zip
```

Where:

```text
repo_id = the portable Promptbranch repo id
version = v-prefixed dot-separated numeric version
```

The version token must contain at least three numeric components and exactly one leading `v`.

Accepted examples:

```text
chatgpt_claudecode_workflow-2_v0.1.73.zip
architecture-process_v0.29.0.zip
ib_forex_trading_v0.248.3.1.zip
candlecast-src_v0.19.5.94.1.zip
```

Rejected examples:

```text
architecture-process_0.29.0.zip
ib_forex_trading.0.248.3.1.zip
candlecast-src_0.19.5.94.1.zip
chatgpt_claudecode_workflow-2_0.1.73.zip
```

## Internal version normalization

A repository may still expose a bare internal version in `VERSION` or package metadata:

```text
0.248.3.1
```

Promptbranch normalizes this to the filename token:

```text
v0.248.3.1
```

The filename remains canonical and must include the leading `v`.

## Adoption rule

`pb artifact adopt` enforces canonical artifact filenames for mutating adoption. Non-canonical filenames fail closed and report the expected canonical filename when it can be inferred.

Canonical local-only adoption example:

```bash
pb artifact adopt architecture-process_v0.29.0.zip \
  --repo architecture-process \
  --local-path ~/git/architecture-process/architecture-process_v0.29.0.zip \
  --local-only \
  --json
```

Canonical Project Source adoption example:

```bash
pb artifact adopt architecture-process_v0.29.0.zip \
  --repo architecture-process \
  --local-path ~/git/architecture-process/architecture-process_v0.29.0.zip \
  --from-project-source \
  --json
```

## Historical artifacts

Historical release ZIPs are not rewritten automatically. Operators should copy legacy filenames to canonical filenames before adoption into a project-scoped registry.

Example:

```bash
cp ib_forex_trading.0.248.3.1.zip ib_forex_trading_v0.248.3.1.zip
```

The copied ZIP contents are unchanged; only the transport filename is canonicalized.
