# v0.1.103.10.87 — make the A/B diagnostic use normal Promptbranch service authentication

The diagnostic runner now resolves `service_base_url` and `service_token` with the same precedence as the normal Promptbranch CLI: explicit flags, standard environment variables, `~/.config/promptbranch/config.json`, then the legacy `~/.config/chatgpt-cli/config.json` fallback. The token is never printed. The legacy 10.75 and current Project Source transaction implementations are unchanged.
