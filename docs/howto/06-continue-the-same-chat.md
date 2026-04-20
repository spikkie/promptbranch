# How to continue the same chat

## Goal

Ask one question, keep the returned `conversation_url`, and use it for follow-up messages in the same conversation.

## First ask

```bash
promptbranch --project-url https://chatgpt.com/g/.../project   ask --json "Reply with JSON only"
```

Capture the returned `conversation_url`.

## Second ask in the same chat

```bash
promptbranch --project-url https://chatgpt.com/g/.../project   ask --json   --conversation-url https://chatgpt.com/g/.../c/...   "Continue the same conversation"
```

## Why this matters

Without `--conversation-url`, a project ask can open a fresh chat instead of continuing the prior one.

## Smoke-test proof

The supported reference workflow is exercised by:

```bash
python ./promptbranch_cli_sequence_v5.py
```
