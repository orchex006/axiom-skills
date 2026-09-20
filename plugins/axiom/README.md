# Axiom agent plugin

This package contains byte-identical copies of the canonical `axiom-skills/skills/` and `policy/POLICY.md` content. The repository copies are authoritative; `python release/build_plugin_bundle.py --check` verifies the packaged copies. The four manifests expose the same skills to Codex, Claude Code, Gemini CLI, and Antigravity. No manifest starts an MCP server, installs a binary, changes host permissions, or claims host certification.

Installation and marketplace commands are in `marketplace-plugins/README.md` at the repository root. Install the runtime separately before using graph operations. Keep release status and native host verification distinct from the presence of these manifests.
