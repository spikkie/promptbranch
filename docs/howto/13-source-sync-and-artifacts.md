# How to sync a repo snapshot and manage artifacts

## Goal

Use Promptbranch as a local control plane for source snapshots and release ZIPs.

## Package the current repo without uploading

```bash
promptbranch src sync . --no-upload --json
```

This creates a ZIP under `.pb_profile/artifacts/`, records it in `.pb_profile/promptbranch_artifacts.json`, and avoids changing the ChatGPT project.

## Package and upload as a project source

```bash
promptbranch ws use "My Project"
promptbranch src sync . --json
```

The upload path uses the existing transactional source-add flow. If you only want a local artifact, keep `--no-upload`.

## Show the current artifact state

```bash
promptbranch artifact current
promptbranch artifact current --json
```

## List registered artifacts

```bash
promptbranch artifact list
promptbranch artifact list --json
```

## Create a release ZIP

```bash
promptbranch artifact release . --json
```

Release ZIPs use the repo `VERSION` file when it contains a version-like value. The ZIP opens directly to repo contents; it must not contain a wrapper folder.

## Verify a ZIP

```bash
promptbranch artifact verify .pb_profile/artifacts/chatgpt_claudecode_workflow_v0.0.130.zip --json
```

Without a path, `artifact verify` checks the latest registered artifact.
