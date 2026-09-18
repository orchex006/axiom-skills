# Codex CLI host adapter

Host: `Codex CLI` · Adapter: `axiom-skills/adapters/codex` · Policy owner: `axiom-skills`

Documented integration for this host is `AGENTS.md` discovery, the skills directory, the MCP
configuration and the host's stop-style hooks. This adapter is an instruction template, not an
example configuration and not a claim of installed-host compatibility. The host keeps its own
execution, approval and sandbox controls, and this adapter never widens them.

## 1. Version and capability pin

Before this adapter is written into a repository, probe the host and pin what was observed.

- Run `axiom host detect` and record the installed host version, the documented and tested
  capabilities, the template match and any warning.
- Record the pin in the host matrix (`compatibility/host-matrix.json`) with the exact version,
  operating system, protocol version, adapter version and feature status. A capability that
  was not tested is `not tested`, never `certified`.
- On an unknown or unsupported host version, fall back to a manual preview plus the CLI path.
  Never auto-write an assumed hook configuration or an assumed hook JSON schema, and never
  assume that a documented capability exists on an unverified version.
- Enforcement level MUST be declared explicitly: `instructions_only`, `hook_verified` or
  `ci_verified`. With `instructions_only`, the adapter is text only and claims no hook gate.

## 2. Instruction discovery and explicit policy read

The managed adapter block is delimited in the repository's `AGENTS.md` by
`<!-- axiom-graph:begin -->` and `<!-- axiom-graph:end -->`. Text a human wrote outside those
markers is preserved and never rewritten. Human overrides belong in
`.axiom/agent/POLICY.local.md`, which Axiom never writes.

`AGENTS.md` discovery is a mechanism, not proof that anything was read.

- The agent MUST explicitly read `.axiom/agent/POLICY.md` at the start of a task and record
  the policy path and its digest in the task evidence.
- **A link to the policy is not evidence that the policy was loaded.** A relative Markdown
  link, a mention of the path, or the presence of the managed block MUST NOT be accepted as a
  substitute for the explicit read, and a completion claim that cites only a link is
  incomplete.
- If the installed policy digest does not match the managed ownership hash, report the
  conflict and stop instead of writing or re-reading around it.

## 3. Hook result contract

Adapters map the host's event into a canonical context and map the canonical result back into
the host's official, installed schema. The canonical result carries `action`
(`allow` | `continue` | `block` | `advisory`), `reason`, `job_id`, `snapshot`, `freshness`,
`coverage`, `retry_after_ms` and `hook_attempt`.

- Do not parse conversation transcripts to guess completion, and do not treat a model saying
  "done" as authoritative graph freshness.
- A `fresh` snapshot with `partial` coverage still bounds the conclusion.
- Stop continuation is not task-state completion. A stop-style hook may continue or block a
  stop decision; it does not prove that the task's work, tests or evidence are complete.

## 4. Loop guard

The loop-guard key is `(host, session or turn or task, source fingerprint, target barrier)`.

- Allow at most two forced continuations for one unchanged fingerprint. After that, surface
  the blocked reason with the pending job status and stop forcing continuation.
- Honour the host's own reentrance flag, such as `stop_hook_active`, when the host supplies
  it. A user interrupt or an error stop is never force-continued by default.
- Hook errors write a diagnostic to stderr with the host-correct output shape. They never
  print a banner or arbitrary text into the host's structured output channel.

## 5. Credentials and configuration

The HTTP MCP configuration uses a `url` plus a `bearer_token_env_var` reference, per the
host's documented schema. Never write a real bearer token into the shared repository, a
snapshot, a plan or a log. If the host cannot expand a secure environment reference in the
header that is required, use a stdio adapter that reads an owner-only credential reference
inside the process, or a user-local untracked configuration.

## 6. Disable and uninstall

Disabling or uninstalling this adapter preserves the host's existing configuration: it removes
only unchanged owned content, leaves human text and human-managed MCP servers in place, and
reports anything it could not safely remove instead of guessing.
