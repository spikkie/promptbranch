# How to troubleshoot common failures

## Symptom: login check fails

Check:

- credentials are present
- the browser profile is valid
- the service can open the ChatGPT site without extra challenges

Try headed mode and keep the browser open.

## Symptom: asks start a new chat instead of continuing

Use `--conversation-url` from the first successful `ask --json` response.

## Symptom: source removal does not match the expected name

The UI can persist a display label that differs from the original input name. Use the authoritative value returned by source-add flows or inspect the exact persisted label.

## Symptom: service works locally but Docker mode fails

Check:

- `CHATGPT_PASSWORD_SECRET_FILE`
- mounted profile directory
- service token and base URL
- compose logs

## Symptom: browser automation becomes unstable

Common causes:

- DOM selector drift
- Cloudflare/browser challenges
- expired login session
- rate limiting

## Debugging tools

- `promptbranch state --json`
- `promptbranch prompt`
- `http://localhost:8000/docs`
- compose logs
- `python ./promptbranch_cli_sequence_v5.py`
