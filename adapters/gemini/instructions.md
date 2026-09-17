# Gemini CLI host adapter

Host: `Gemini CLI` · Adapter: `axiom-skills/adapters/gemini` · Policy owner: `axiom-skills`

Documented integration for this host is the `GEMINI.md` context scope, the MCP
configuration, and the `AfterAgent` and `AfterTool` hooks. This adapter is an instruction
template, not an example configuration and not a claim of installed-host compatibility. The
host keeps its own execution, permission and tool-approval controls, and this adapter never
widens them.

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

## 2. Discovery, activation and global instruction safety

`GEMINI.md` discovery walks from the working root upward, and the host also reads a
user-level context file outside the repository. Discovery is a mechanism, not proof that
anything was read, and the two scopes are not interchangeable.

- Activation is proven with a fixture: the repository-local, Axiom-owned block delimited by
  `<!-- axiom-graph:begin -->` and `<!-- axiom-graph:end -->` is staged into the working
  root, the human text is left byte-identical, so no unrelated global instruction is overwritten.
  The global context file stays human-owned and untracked by Axiom, and the adapter only ever
  writes the repository-local block.
- Existing repository instructions remain authoritative over the managed block.
- The agent MUST explicitly read `.axiom/agent/POLICY.md` at the start of a task and record
  the policy path and its digest in the task evidence.
- **A link to the policy is not evidence that the policy was loaded.** A mention of the path
  or the presence of the managed block MUST NOT be accepted as a substitute for the explicit
  read.

## 3. Hook events and their real scope

- `AfterAgent` runs after an agent turn and `AfterTool` after a tool call. Their retry and
  halt policy is the host's own and is not the Claude exit or JSON shape, so a Claude hook
  payload or exit convention MUST NOT be reused blindly here.
- A graph that is unavailable degrades to `advisory`; the adapter never converts an
  unresolved job into a hard stop the host cannot express.

Adapters map the host's event into a canonical context and map the canonical result back into
the host's official, installed schema. The canonical result carries `action`
(`allow` | `continue` | `block` | `advisory`), `reason`, `job_id`, `snapshot`, `freshness`,
`coverage`, `retry_after_ms` and `hook_attempt`.

- Do not parse conversation transcripts to guess completion, and do not treat a model saying
  "done" as authoritative graph freshness.
- A `fresh` snapshot with `partial` coverage still bounds the conclusion.
- Stop-style continuation is not task-state completion, and an agent turn ending is not
  evidence that the task's work, tests or evidence are complete.

## 4. Loop guard

The loop-guard key is `(host, session or turn or task, source fingerprint, target barrier)`.

- Allow at most two forced continuations for one unchanged fingerprint. After that, surface
  the blocked reason with the pending job status and stop forcing continuation.
- Honour the host's own reentrance flag, such as `stop_hook_active`, when the host supplies
  it, so an `AfterAgent` retry cannot recurse without bound.
- A user interrupt or a host error is never force-continued by default.
- Hook errors write a diagnostic to stderr with the host-correct output shape. They never
  print a banner or arbitrary text into the host's structured output channel.

## 5. Credentials and configuration

The HTTP streaming MCP configuration uses the host's documented `httpUrl` field, and the stdio
form is preferred when the host cannot expand a secure environment reference in a required
header. Never write a real bearer token into the shared repository, a snapshot, a plan or a
log; use a stdio adapter that reads an owner-only credential reference inside the process, or
a user-local untracked configuration.

## 6. Disable and uninstall

Disabling or uninstalling this adapter preserves the host's existing configuration: it removes
only unchanged owned content, leaves human text and human-managed MCP servers and global
context files in place, and reports anything it could not safely remove instead of guessing.
