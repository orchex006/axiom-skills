# Codex instruction link (boundary fixture: redirected final URL)

Source URL `https://developers.openai.com/codex/guides/agents-md` returned HTTP 200. The final
URL after the redirect (learn.chatgpt.com/docs/agent-configuration/agents-md) is recorded as
plain text, not as a second link, so the only URL present is an allowlisted one. A checker
must accept this: a redirect to a host-owned final URL is not a fabricated certification link.

| Source | Host | Topic | URL | Retrieval | Cited token |
| --- | --- | --- | --- | --- | --- |
| S09 | Codex | instructions | https://developers.openai.com/codex/guides/agents-md | HTTP 200 (final: learn.chatgpt.com/docs/agent-configuration/agents-md) | `AGENTS.md` |
