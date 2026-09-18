# Host setup guide (negative fixture: one host missing)

Codex: `AGENTS.md`, `bearer_token_env_var`, `graph_stop.py`, `codex-stop-v1`, `{"decision": "block"}`.

Claude: `CLAUDE.md`, `TaskCompleted`, `claude-stop-v1`, `claude-task-completed-v1`, `mcpServers`, `{"decision": "block"}`.

Gemini: `GEMINI.md`, `httpUrl`, `AfterAgent`, `AfterTool`, `gemini-after-agent-v1`, `{"decision": "retry"}`.

The agent MUST explicitly read `.axiom/agent/POLICY.md`; a link is not evidence.

Managed block: `<!-- axiom-graph:begin -->` and `<!-- axiom-graph:end -->`.

Enforcement levels: `instructions_only`, `hook_verified`, `ci_verified`. Host status is
not certified and each field is version-specific for the installed version.
