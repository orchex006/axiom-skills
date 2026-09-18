# Host link table (negative fixture: fabricated certification URL)

This fixture presents a URL that is not one of the retrieved, allowlisted host documentation
links, and labels it as certification. A checker must reject it: a claimed certification link
that was never retrieved is not evidence.

| Source | Host | Topic | URL | Retrieval | Cited token |
| --- | --- | --- | --- | --- | --- |
| S99 | Codex | MCP | https://developers.openai.com/codex/mcp-bearer-token-field | certified | `bearer_token_env_var` |
