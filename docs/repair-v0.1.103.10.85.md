# v0.1.103.10.85 — diagnostic legacy 10.75 vs current Project Source transactions

## Scope

- Keep `pbsa <file>` unchanged.
- Create two disposable projects and two unique disposable filenames.
- Run the verbatim v0.1.103.10.75 add/overwrite transaction in one project.
- Run the current transaction in the other project.
- Record requested filename, Library-assigned filename, processed file ID, libfile metadata object ID, Project Source identity, upload responses, remove response, and second-upload result.
- Emit a deterministic conclusion: both work, legacy only, current only, or both fail.

## Safety

No release artifact upload, adoption, existing Project Source mutation, platform-gitops file, host CDP/session manager, copied-profile trust, Cloudflare bypass, or rate-limit bypass. Disposable projects are retained because Project deletion remains frozen.

## Command

Install the diagnostic candidate and run the A/B probe without Project Source upload or adoption:

```bash
./install.sh v0.1.103.10.85 "$HOME/Downloads/chatgpt_claudecode_workflow-2_v0.1.103.10.85.zip" --diagnostic-project-source-ab
```

After the candidate service is already running, the probe can be repeated directly with a fresh pair of disposable names:

```bash
./scripts/pb-project-source-ab-diagnostic.sh
```

## Legacy transaction provenance

The diagnostic legacy method is AST-identical to `_add_project_source_operation` from the packaged `v0.1.103.10.75` artifact after normalizing only the method name.

```text
normalized AST SHA256: 10d673452f450c94beb6e79881d0ba3f7f5e1c9194340e5a82fa9bb78938ba45
```
