# Host link table (negative fixture: fabricated runtime verification URL)

This fixture presents a URL that is not one of the retrieved, allowlisted host documentation
links, and labels it as runtime verification. A checker must reject it: a claimed runtime verification link
that was never retrieved is not evidence.

| Source | Host | Topic | URL | Retrieval | Cited token |
| --- | --- | --- | --- | --- | --- |
| S99 | Codex | MCP | https://developers.openai.com/codex/mcp-bearer-token-field | runtime verified | `bearer_token_env_var` |
