# Antigravity host adapter

Host: `Antigravity (AGY)` · Adapter: `axiom-skills/adapters/antigravity` · Policy owner: `axiom-skills`

Documented integration for this host is the rules and skills locations, the MCP
configuration, and the `Stop` and `PostToolUse` hooks. This adapter is an instruction
template, not an example configuration and not a claim of installed-host compatibility. The
host keeps its own execution, permission and tool-approval controls, and this adapter never
widens them.

## 1. Version and capability pin

Antigravity ships as an IDE surface and a CLI surface, and the two have separate versions,
configuration paths and hook behaviour. Resolve them separately and never assume one
profile's paths apply to the other.

- Run `axiom host detect` and record the installed host version, the documented and tested
  capabilities, the template match and any warning.
- Record the pin in the host matrix (`compatibility/host-matrix.json`) with the exact version,
  operating system, surface (`ide` or `cli`), protocol version, adapter version and feature
  status. A capability that was not tested is `not tested`, never `certified`, and a
  capability confirmed on one surface is not a claim about the other.
- Active rules and skill locations follow the documented installed version. When a configured
  rules path or skill location is not one the pinned version documents, the adapter stops rather
  than writing to a guessed location: an unrecognized path is reported as a conflict.
- On an unknown or unsupported host version, fall back to a manual preview plus the CLI path.
  Never auto-write an assumed hook configuration or an assumed hook JSON schema.
- Enforcement level MUST be declared explicitly: `instructions_only`, `hook_verified` or
  `ci_verified`. With `instructions_only`, the adapter is text only and claims no hook gate.

## 2. Rules, skills and policy activation

The managed adapter block is delimited by `<!-- axiom-graph:begin -->` and
`<!-- axiom-graph:end -->`. Human rules outside those markers are preserved and never
rewritten, and existing repository instructions remain authoritative over the managed block.
Human overrides belong in `.axiom/agent/POLICY.local.md`, which Axiom never writes.

- The agent MUST explicitly read `.axiom/agent/POLICY.md` at the start of a task and record
  the policy path and its digest in the task evidence.
- **A link to the policy is not evidence that the policy was loaded.** A mention of the path,
  a skill listing entry or the presence of the managed block MUST NOT be accepted as a
  substitute for the explicit read.
- If the installed policy digest does not match the managed ownership hash, report the
  conflict and stop instead of writing or re-reading around it.

## 3. Hook events and their real scope

- The `Stop` hook's documented output decision on this host is `continue`, with the reason
  carried alongside it. The host's `decision: block` payload shape from another host is not
  reused blindly here: `block` is only emitted where the pinned version documents it, and
  otherwise the adapter reports `advisory`.
- `PostToolUse` carries a cheap change hint only. It never triggers a full project parse and
  never dumps graph context.
- Stop-style continuation is not task-state completion.

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
  it, so a requested continuation cannot recurse without bound.
- A user interrupt or a host error is never force-continued by default.
- Hook errors write a diagnostic to stderr with the host-correct output shape. They never
  print a banner or arbitrary text into the host's structured output channel.

## 5. Credentials and configuration

The MCP configuration uses the host's documented `serverUrl` field. Never write a real bearer
token into the shared repository, a snapshot, a plan or a log. If the host cannot expand a
secure environment reference in a required header, use a stdio adapter that reads an
owner-only credential reference inside the process, or a user-local untracked configuration.

## 6. Disable and uninstall

Disabling or uninstalling this adapter preserves the host's existing configuration on both
surfaces: it removes only unchanged owned content, leaves human rules and human-managed MCP
servers in place, and reports anything it could not safely remove instead of guessing.
