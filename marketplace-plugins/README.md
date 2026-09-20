# Axiom plugin distribution

The repository hosts one `plugins/axiom` package containing the same Axiom skills for four agent hosts. Install from a reviewed revision; installing a plugin does not install `axiom-graphd` or `axiom-mcp` and does not certify a host version.

| Host | Discovery file | Local installation |
| --- | --- | --- |
| Codex | `.agents/plugins/marketplace.json` | `codex plugin marketplace add <repository-path>` then `codex plugin add axiom@axiom-skills` |
| Claude Code | `.claude-plugin/marketplace.json` | `claude plugin marketplace add <repository-path>` then `claude plugin install axiom@axiom-skills` |
| Gemini CLI | `plugins/axiom/gemini-extension.json` | `gemini extensions install <repository-path>/plugins/axiom` |
| Antigravity CLI | `plugins/axiom/plugin.json` | `agy plugin install <repository-path>/plugins/axiom` |

Codex marketplace registration is an explicit user action; this repository does not change a user's personal marketplace. Gemini and Antigravity use the local package path because their documented installation surface does not consume the Codex or Claude marketplace catalogs. On Windows, replace `<repository-path>` with the absolute path to this checkout. After installation, inspect the host's plugin list and a skill before using the runtime. Record the exact host version and OS before claiming host compatibility.
