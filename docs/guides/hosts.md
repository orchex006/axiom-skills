# Host Setup Guides

Owner: `axiom-skills` · Adapter guide version: 1 · Spec baseline: `2.0.0-draft.1`

Audience: an operator or agent that wires the Axiom graph workflow into a supported agent
host: Codex CLI, Claude Code, Gemini CLI or Antigravity (AGY).

Everything in this guide is **version-specific**. Instruction-file discovery, MCP
configuration field names and hook events or output schemas are taken from the host
documentation retrieved on 2026-09-18 (links in [§3](#3-certification-links)) and are bound
to a host's installed version. The adapters under `adapters/` are instruction templates, not
example configurations and not a claim of installed-host compatibility.
`adapters/compatibility.json` declares all four adapters `certified: false` with
`enforcement_level: instructions_only` because no licensed host runtime was available to
probe. A documented capability table is not certification, and an in-repository unit test is
not host certification.

## 1. Before you configure a host

1. Probe the host and pin what was actually observed: `axiom host detect --json` reports the
   installed host version, the documented and tested capabilities, the template match and any
   warning. It is the documented CLI surface for host detection
   (`repo-seeds/axiom-graphd/docs/21-INSTALLATION.md` §F in the spec package).
2. Record the pin in the host matrix `compatibility/host-matrix.json`: the exact installed
   version, the operating system, the surface (`ide` or `cli`), the protocol version, the
   adapter version and each feature status. A capability that was not tested is `not tested`,
   never `certified`.
3. Declare the enforcement level explicitly: `instructions_only`, `hook_verified` or
   `ci_verified`. With `instructions_only` the adapter is text only and claims no hook gate.
   An enforcement level must never exceed the evidence behind it.
4. Read `policy/POLICY.md` and the owner spec (`axiom-specs/specs/v2/A-axiom-skills.md`)
   before editing a host.

On an unknown or unsupported host version, fall back to a manual preview plus the CLI path.
Never auto-write an assumed hook configuration or an assumed hook JSON schema, and never
assume that a documented capability exists on an unverified version.

## 2. What is shared and what is host-specific

Shared by every host:

- the canonical internal hook result: `action` (`allow` | `continue` | `block` | `advisory`),
  `reason`, `job_id`, `snapshot`, `freshness`, `coverage`, `retry_after_ms`, `hook_attempt`;
- the explicit policy read and its recorded digest ([§4](#4-instruction-loading));
- the loop guard, the cancellation contract and the degraded policy
  ([§6](#6-hooks-loop-guard-cancellation-and-degraded-policy));
- the rule that a stop-style continuation is not task-state completion, and that a `fresh`
  snapshot with `partial` coverage still bounds the conclusion.

Host-specific, and therefore never copied between hosts:

- the MCP configuration field names ([§5](#5-mcp-configuration-and-credentials));
- the instruction file and its discovery scope ([§4](#4-instruction-loading));
- the hook event names and the host output decision schema
  ([§6](#6-hooks-loop-guard-cancellation-and-degraded-policy)).

## 3. Certification links

The table below is the documentation evidence this guide is grounded in. Each row was
retrieved with an HTTPS `GET` (`urllib`, `User-Agent
axiom-skills-docs-link-check/1.0`, `Accept-Encoding: gzip`, gzip decoded before matching) on
2026-09-18. All eleven URLs returned `HTTP 200` and the cited token was present in the
decoded body. The raw retrieval log and its SHA256 are preserved at
`evidence/artifacts/D-008/links.md`.

| Source | Host | Topic | URL | Retrieval | Cited token |
| --- | --- | --- | --- | --- | --- |
| S09 | Codex | instructions | https://developers.openai.com/codex/guides/agents-md | HTTP 200 (final: learn.chatgpt.com/docs/agent-configuration/agents-md) | `AGENTS.md` |
| S10 | Codex | MCP | https://developers.openai.com/codex/mcp | HTTP 200 (final: learn.chatgpt.com/docs/extend/mcp) | `bearer_token_env_var`, `mcp_servers` |
| S11 | Codex | hooks | https://developers.openai.com/codex/hooks | HTTP 200 (final: learn.chatgpt.com/docs/hooks) | `Stop` |
| S12 | Claude | hooks | https://code.claude.com/docs/en/hooks | HTTP 200 | `Stop`, `TaskCompleted` |
| S20 | Claude | MCP | https://code.claude.com/docs/en/mcp | HTTP 200 | `mcpServers` |
| S13 | Antigravity | skills | https://antigravity.google/docs/skills/ | HTTP 200 | `.agents/skills` |
| S14 | Antigravity | rules | https://antigravity.google/docs/rules-workflows/ | HTTP 200 | `.agent/rules` |
| S15 | Antigravity | MCP | https://antigravity.google/docs/mcp/ | HTTP 200 | `serverUrl` |
| S16 | Antigravity | hooks | https://antigravity.google/docs/hooks/ | HTTP 200 | `Stop`, `PostToolUse` |
| S17 | Gemini | hooks | https://geminicli.com/docs/hooks/ | HTTP 200 | `AfterAgent`, `AfterTool` |
| S18 | Gemini | MCP | https://geminicli.com/docs/tools/mcp-server/ | HTTP 200 | `httpUrl` |

These are host documentation references, not host certification. The source registry
`axiom-specs/research/SOURCES.md` defines S01–S28; the rows above are its S09–S20 host
entries. Because no licensed host runtime was probed, `adapters/compatibility.json` records
`certified_adapters: 0` and `host_runtime_tests_run: 0`, and every adapter carries an explicit
certification blocker. Certification of a host requires a probed exact installed version, a
tested operating system, a protocol version, a host runtime test artifact and its SHA256, and
an enforcement level the evidence supports. Until those exist, read this guide as documented
and in-repository tested behaviour only, and mark host status `not tested`.

## 4. Instruction loading

Each host reads a different instruction file and discovers it differently. The Axiom-owned
content is a **managed block** delimited by `<!-- axiom-graph:begin -->` and
`<!-- axiom-graph:end -->`. Human text outside those markers is preserved and never
rewritten; existing repository instructions remain authoritative over the managed block.
Human overrides belong in `.axiom/agent/POLICY.local.md`, which Axiom never writes.

| Host | Instruction file | Discovery scope | Managed block markers | Policy read |
| --- | --- | --- | --- | --- |
| Codex | `AGENTS.md` | repository `AGENTS.md` discovery [S09] | `<!-- axiom-graph:begin -->` … `<!-- axiom-graph:end -->` | explicit |
| Claude | `CLAUDE.md` | repository and nested `CLAUDE.md` scope [S12] | `<!-- axiom-graph:begin -->` … `<!-- axiom-graph:end -->` | explicit |
| Gemini | `GEMINI.md` | working root upward, plus a user-level global context file [S17] | `<!-- axiom-graph:begin -->` … `<!-- axiom-graph:end -->` | explicit |
| Antigravity | rules and skills locations | installed rules path and skill location; IDE and CLI resolved separately [S13][S14] | `<!-- axiom-graph:begin -->` … `<!-- axiom-graph:end -->` | explicit |

Discovery is a mechanism, not proof that anything was read. The agent MUST explicitly read
`.axiom/agent/POLICY.md` at the start of a task and record the policy path and its digest in
the task evidence. **A link to the policy is not evidence that the policy was loaded**: a
relative Markdown link, an `@import` edge, a mention of the path, a skill listing entry or
the mere presence of the managed block must not be accepted as a substitute for the explicit
read. If the installed policy digest does not match the managed ownership hash, report the
conflict and stop instead of writing or re-reading around it.

Gemini has two scopes that are not interchangeable: the repository-local Axiom block is
staged into the working root with human text left byte-identical, while the user-level global
context file stays human-owned and untracked by Axiom. Antigravity's active rules and skill
locations follow the documented installed version; when a configured rules path or skill
location is not one the pinned version documents, stop and report a conflict rather than
writing to a guessed location.

## 5. MCP configuration and credentials

The MCP configuration schema is host-native, so each host gets a different rendered shape
from the same graph endpoint. Do not copy one host's JSON into another.

| Host | HTTP transport field(s) | Source | Note |
| --- | --- | --- | --- |
| Codex | `url` plus `bearer_token_env_var` | S10 | environment reference in the header; `mcp_servers` config map |
| Claude | transport `type` plus `url` | S20 | native MCP schema (`mcpServers`) |
| Gemini | `httpUrl` | S18 | HTTP streaming; stdio/SSE form also documented |
| Antigravity | `serverUrl` | S15 | per-surface configuration; do not substitute Gemini's `httpUrl` |

Live MCP writes must preserve existing host configuration and use an environment or credential
reference; a token must never be written into a tracked project config. Never write a real
bearer token into the shared repository, a snapshot, a plan or a log. If the host cannot
expand a secure environment reference in the required header, use a stdio adapter that reads
an owner-only credential reference inside the process, or a user-local untracked
configuration.

## 6. Hooks, loop guard, cancellation and degraded policy

Each adapter maps the host event into the canonical context and maps the canonical result
back into the host's official, installed output schema. The shipped schema profiles and the
documented host decision are:

| Host | Event | Adapter | Schema profile | Host output decision |
| --- | --- | --- | --- | --- |
| Codex | `Stop` | `adapters/codex/hooks/graph_stop.py` | `codex-stop-v1` | `{"decision": "block", "reason": "..."}` |
| Claude | `Stop` | `adapters/claude/hooks/graph_stop.py` | `claude-stop-v1` | `{"decision": "block", "reason": "..."}` |
| Claude | `TaskCompleted` | `adapters/claude/hooks/graph_task_completed.py` | `claude-task-completed-v1` | `{"decision": "block", "reason": "..."}` |
| Gemini | `AfterAgent` (and `AfterTool`) | `adapters/gemini/hooks/graph_after_agent.py` | `gemini-after-agent-v1` | `{"decision": "retry", "retry_after_ms": "..."}` |
| Antigravity | `Stop` | `adapters/antigravity/hooks/graph_stop.py` | `antigravity-stop-v1` | `{"decision": "continue", "reason": "..."}` |
| Antigravity | `PostToolUse` | cheap change hint only [S16] | — | no decision; never a full project parse |

Event scope matters. Claude's `TaskCompleted` applies to the host's task update and
agent-team task lifecycle; it does not fire for every turn and is not every turn. A `Stop`
decision is not a user interrupt: an abort, a cancel or a host error is not a `Stop` event and
is never force-continued. Gemini's `AfterAgent` retry and halt policy is the host's own and is
not the Claude exit or JSON shape, so a Claude hook payload or exit convention must not be
reused blindly. Antigravity's documented `Stop` output decision is `continue`; the other
host's `decision: block` payload is not reused blindly, and `block` is emitted only where the
pinned version documents it. A stop-style continuation is not task-state completion: it never
proves that the task's work, tests or evidence are complete.

Loop guard. The loop-guard key is `(host, session or turn or task, source fingerprint, target
barrier)`. Allow at most two forced continuations for one unchanged fingerprint; after that,
surface the blocked reason with the pending job status and stop forcing continuation. Honour
the host's own reentrance flag, such as `stop_hook_active`, when the host supplies it. A user
interrupt or an error stop is never force-continued by default. Hook errors write a diagnostic
to stderr with the host-correct output shape and never print a banner or arbitrary text into
the host's structured output channel.

Cancellation is not completion. When a turn ends by user cancel, shutdown or error/abort, the
adapter preserves durable dirty state and writes the `cancellation-v1` record with
`dirty_state: preserved`, `completion_gate: not_run`, `freshness: unverified` and
`forced_continuation: false`; it never claims a completion gate ran. Durable state goes to
`$AXIOM_HOOK_STATE_DIR`, or `<cwd>/.axiom/local/hook-state/` by default. The shared runtime
`adapters/common/hook_runtime.py` bounds every call with a timeout and a retry cap and
records pending evidence rather than raising, so an unavailable graph never becomes a hard
stop the host cannot express.

Degraded policy. `adapters/common/degraded_policy.json` is applied per repository: the
`axiom-skills` repository runs `advisory` with `fail_open: true`, while `axiom-graphd` and
`axiom-mcp` run `strict`, and an unknown repository defaults to `strict`. A fail-open or
cancelled path never claims fresh freshness or a completion gate.

## 7. Disable and uninstall

Disabling or uninstalling an adapter preserves the host's existing configuration: it removes
only unchanged Axiom-owned content, leaves human text, human overrides, human-managed MCP
servers and global context files in place, and reports anything it could not safely remove
instead of guessing. Antigravity removes owned content on both the IDE and CLI surfaces
without touching human rules or human-managed MCP servers. No source file is touched by a
cancellation or uninstall path.

## 8. Per-host quick reference

### Codex CLI

- Adapter: `adapters/codex/instructions.md`; hook `adapters/codex/hooks/graph_stop.py`.
- Instruction loading: repository `AGENTS.md`, managed block only [S09].
- Hook: `Stop` → `{"decision": "block", "reason": "..."}` (`codex-stop-v1`) [S11].
- MCP: `url` plus `bearer_token_env_var` [S10].
- Status: documented and in-repository tested, not certified.

### Claude Code

- Adapter: `adapters/claude/instructions.md`; hooks `graph_stop.py` and
  `graph_task_completed.py`.
- Instruction loading: `CLAUDE.md` scope; existing repository instructions stay
  authoritative.
- Hooks: `Stop` → `{"decision": "block", "reason": "..."}` (`claude-stop-v1`) and
  `TaskCompleted` → `{"decision": "block", "reason": "..."}`
  (`claude-task-completed-v1`); `TaskCompleted` is not every turn [S12].
- MCP: native `type` plus `url`; `mcpServers` [S20].
- Status: documented and in-repository tested, not certified.

### Gemini CLI

- Adapter: `adapters/gemini/instructions.md`; hook
  `adapters/gemini/hooks/graph_after_agent.py`.
- Instruction loading: `GEMINI.md` working-root-upward discovery plus a human-owned global
  context file [S17].
- Hooks: `AfterAgent` (and `AfterTool`) → `{"decision": "retry", "reason": "..."}` with
  `retry_after_ms` when the host reports it (`gemini-after-agent-v1`); retry and halt policy is
  the host's own, not the Claude shape.
- MCP: `httpUrl` [S18].
- Status: documented and in-repository tested, not certified.

### Antigravity (AGY)

- Adapter: `adapters/antigravity/instructions.md`; hook
  `adapters/antigravity/hooks/graph_stop.py`.
- Versioning: IDE and CLI are separate surfaces with separate versions, configuration paths
  and hook behaviour; resolve them separately and never assume one profile's paths apply to
  the other.
- Instruction loading: rules location `.agent/rules` [S14] and skills location
  `.agents/skills` [S13]; both are version-specific.
- Hooks: `Stop` → `{"decision": "continue", "reason": "..."}` (`antigravity-stop-v1`)
  [S16]; `PostToolUse` carries a cheap change hint only.
- MCP: `serverUrl` [S15].
- Status: documented and in-repository tested, not certified.
