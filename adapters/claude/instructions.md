# Claude Code host adapter

Host: `Claude Code` · Adapter: `axiom-skills/adapters/claude` · Policy owner: `axiom-skills`

Documented integration for this host is the `CLAUDE.md` instruction scope, the MCP
configuration, and the `Stop` and `TaskCompleted` hooks. This adapter is an instruction
template, not an example configuration and not a claim of installed-host compatibility.
The host keeps its own execution, permission and subagent controls, and this adapter never
widens them and never replaces a human-owned instruction file.

## 1. Version and capability pin

Before this adapter is written into a repository, probe the host and pin what was observed.

- Run `axiom host detect` and record the installed host version, the documented and tested
  capabilities, the template match and any warning.
- Record the pin in the host matrix (`compatibility/host-matrix.json`) with the exact version,
  operating system, protocol version, adapter version and feature status. A capability that
  was not tested is `not tested`, never `certified`.
- On an unknown or unsupported host version, fall back to a manual preview plus the CLI path.
  Never auto-write an assumed hook configuration or an assumed hook JSON schema.
- Enforcement level MUST be declared explicitly: `instructions_only`, `hook_verified` or
  `ci_verified`. With `instructions_only`, the adapter is text only and claims no hook gate.

## 2. CLAUDE scope, imports and policy activation

The managed adapter block is delimited in the repository's `CLAUDE.md` by
`<!-- axiom-graph:begin -->` and `<!-- axiom-graph:end -->`. Text a human wrote outside
those markers is preserved and never rewritten, and **existing repository instructions
remain authoritative**: a managed block refines the host's own instruction file, it never
overrides `AGENTS.md`, a nested `CLAUDE.md` or a human override. Human overrides belong in
`.axiom/agent/POLICY.local.md`, which Axiom never writes.

A file import is resolved by the host, so an imported file is not proof that a reader
followed it. Policy activation is separated from policy discovery:

- The agent MUST explicitly read `.axiom/agent/POLICY.md` at the start of a task and record
  the policy path and its digest in the task evidence.
- **A link to the policy is not evidence that the policy was loaded.** A relative Markdown
  link, an `@import` edge, a mention of the path, or the presence of the managed block MUST
  NOT be accepted as a substitute for the explicit read.
- Never rewrite the host's user-level or global instruction files while activating project
  policy; only the repository-local managed block is owned by Axiom.
- If the installed policy digest does not match the managed ownership hash, report the
  conflict and stop instead of writing or re-reading around it.

## 3. Hook events and their real scope

`Stop` and `TaskCompleted` are different events with different reach.

- `TaskCompleted` applies to the host's task update and agent-team task lifecycle. It does
  **not** fire for every turn and is not every turn.
- `Stop` is a stop decision, not the same as a user interrupt. An abort, a cancel or a host
  error is not a `Stop` event and is never force-continued.
- `Stop` continuation is not task-state completion. A stop-style hook may continue or block a
  stop decision; it does not prove that the task's work, tests or evidence are complete.

Adapters map the host's event into a canonical context and map the canonical result back into
the host's official, installed schema. The canonical result carries `action`
(`allow` | `continue` | `block` | `advisory`), `reason`, `job_id`, `snapshot`, `freshness`,
`coverage`, `retry_after_ms` and `hook_attempt`.

- Do not parse conversation transcripts to guess completion, and do not treat a model saying
  "done" as authoritative graph freshness.
- A `fresh` snapshot with `partial` coverage still bounds the conclusion.

## 4. Loop guard

The loop-guard key is `(host, session or turn or task, source fingerprint, target barrier)`.

- Allow at most two forced continuations for one unchanged fingerprint. After that, surface
  the blocked reason with the pending job status and stop forcing continuation.
- Honour the host's own reentrance flag, such as `stop_hook_active`, when the host supplies
  it, so a continuation the adapter already requested cannot recurse without bound.
- A bounded reconcile failure blocks only where the installed host actually supports a stop
  decision; where it does not, the adapter reports `advisory` and allows the stop instead of
  claiming a gate it cannot enforce.
- Hook errors write a diagnostic to stderr with the host-correct output shape. They never
  print a banner or arbitrary text into the host's structured output channel.

## 5. Credentials and configuration

The MCP configuration uses the host's native schema, a transport `type` plus a `url`, per the
host's documented shape. Never write a real bearer token into the shared repository, a
snapshot, a plan or a log. If the host cannot expand a secure environment reference in the
header that is required, use a stdio adapter that reads an owner-only credential reference
inside the process, or a user-local untracked configuration.

## 6. Disable and uninstall

Disabling or uninstalling this adapter preserves the host's existing configuration: it removes
only unchanged owned content, leaves human text, human overrides and human-managed MCP servers
in place, and reports anything it could not safely remove instead of guessing.
