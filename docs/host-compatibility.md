# Host Compatibility and Version Probing

Owner: `axiom-skills` · Version: inherits the axiom-skills component version (`0.1.0-draft.1`) · Spec baseline: `2.0.0-draft.1`

Documentation versioning: this document inherits the axiom-skills component version and has no
independent version. There is no separate documentation version to bump — when the component
version moves, this guide moves with it, and it is never published as its own versioned
document.

Audience: an operator or agent that probes one of the supported agent hosts — Codex CLI,
Claude Code, Gemini CLI, Antigravity (AGY) — and records what was actually observed.

Companion: `docs/guides/hosts.md` is the wiring guide; this document is the probing and
compatibility-discipline guide. Both share one rule: a documented capability table is not
certification, and an in-repository unit test is not host certification.

## 1. Unverified until version-probed

Every host example in this document is marked `unverified` until the exact installed host
version was probed and recorded. "Version-probed" is a specific, evidenced act — not an
assumption, not a documentation read, and not a bare host CLI version string:

- the exact installed version was observed on a named operating system;
- the surface (`ide` or `cli`) was resolved, because a host may ship separate surfaces;
- the protocol version and the adapter version were pinned;
- a host runtime test artifact exists and its SHA256 is recorded.

Until all of that holds, the example stays `unverified`, and any capability that was not
exercised on that version is `not tested` — never `certified`. None of the examples in §5 were
promoted, because no licensed host runtime test was performed in this environment and
`adapters/compatibility.json` records `version_probe: "not_run"` for every adapter. A Codex CLI
or Claude Code executable being present on the build host is a locator hit, not a version
probe, and it does not promote an example.

## 2. Independent compatibility dimensions

Installed version, operating system, surface, protocol version, adapter version and
enforcement level are independent compatibility dimensions. Never collapse them into one
"supported" claim: a host can be probed on one operating system and not another, on the `cli`
surface and not the `ide` surface, and at one protocol version and not the next. Record each
dimension on its own line so a reader can see exactly which part is evidenced.

| Dimension | What it pins | Recorded value shape |
| --- | --- | --- |
| installed version | the exact observed host build | `1.2.3` |
| operating system | the tested platform | `windows-11`, `macos-15`, `ubuntu-24.04` |
| surface | which host surface was probed | `cli`, `ide`, or `ide_and_cli` |
| protocol version | the adapter/host wire contract | `1` |
| adapter version | the shipped Axiom adapter | `0.1.0-draft.1` |
| enforcement level | the ceiling the evidence supports | `instructions_only` |

An enforcement level must never exceed the evidence behind it. `instructions_only` is text
only and claims no hook gate; `hook_verified` and `ci_verified` require their own host runtime
artifacts. Until such an artifact exists for a probed version, the ceiling is
`instructions_only`.

## 3. Provider settings never override host permissions

Axiom provider settings and MCP server entries configure where the graph service is reached;
they are not an authority grant. Provider settings never override host permissions, and they
never grant, widen or replace a host's approval, sandbox or execution controls. Host approval
stays authoritative: the host decides whether a tool call, a hook or a command is permitted,
and no Axiom provider setting can turn a host-denied action into an allowed one. When a host
does not permit an action, the correct outcome is the host's refusal — not a configuration
workaround that claims the permission instead.

## 4. Probe recipe

1. Resolve the surface first (IDE or CLI). Antigravity ships both with separate versions,
   configuration paths and hook behaviour; resolve them separately and never assume one
   profile's paths apply to the other.
2. Probe the exact installed version and record it with the operating system and the date,
   alongside the adapter version and the protocol version.
3. Mark every feature you did not exercise `not tested`; a capability that was only read from
   documentation is not `verified`.
4. Set the enforcement level to the ceiling the evidence supports, and no higher.
5. Persist a runtime test artifact with its SHA256 before any feature claims `verified`.
6. Update `adapters/compatibility.json` and this document together, so the record and the guide
   cannot drift.

## 5. Per-host examples (all unverified)

Every example below carries an explicit `Probe status:` line. The status is `unverified` and the
example is a shape only; the probe recipe in §4 is what promotes it.

### Codex CLI

Probe status: `unverified` — no installed Codex CLI version was probed and the compatibility
record keeps `version_probe: "not_run"` for this adapter.

- Adapter: `adapters/codex/instructions.md`; hook `adapters/codex/hooks/graph_stop.py`.
- Surface: `cli`. Enforcement level: `instructions_only`.
- Instruction loading: repository `AGENTS.md`, managed block only [S09].
- MCP: `url` plus `bearer_token_env_var` [S10]; the setting selects an endpoint and grants
  nothing.

### Claude Code

Probe status: `unverified` — no installed Claude Code version was probed and the compatibility
record keeps `version_probe: "not_run"` for this adapter.

- Adapter: `adapters/claude/instructions.md`; hooks `graph_stop.py` and
  `graph_task_completed.py`.
- Surface: `cli`. Enforcement level: `instructions_only`.
- Instruction loading: `CLAUDE.md` scope; existing repository instructions stay authoritative.
- MCP: `mcpServers` [S20]; a configured server does not widen host approval.

### Gemini CLI

Probe status: `unverified` — no installed Gemini CLI version was probed and the compatibility
record keeps `version_probe: "not_run"` for this adapter.

- Adapter: `adapters/gemini/instructions.md`; hook
  `adapters/gemini/hooks/graph_after_agent.py`.
- Surface: `cli`. Enforcement level: `instructions_only`.
- Instruction loading: `GEMINI.md` working-root-upward discovery plus a human-owned global
  context file [S17]; the retry and halt policy is the host's own.
- MCP: `httpUrl` [S18].

### Antigravity (AGY)

Probe status: `unverified` — no installed Antigravity version was probed on either surface and
the compatibility record keeps `version_probe: "not_run"` for this adapter.

- Adapter: `adapters/antigravity/instructions.md`; hook
  `adapters/antigravity/hooks/graph_stop.py`.
- Surface: `ide_and_cli`, unresolved separately. Enforcement level: `instructions_only`.
- Instruction loading: rules location `.agent/rules` [S14] and skills location `.agents/skills`
  [S13]; both are version-specific.
- MCP: `serverUrl` [S15].

## 6. Recording, drift and re-probing

`adapters/compatibility.json` is the owner-repository record; the specification-side matrix is
`axiom-specs/compatibility/host-matrix.json`. This guide and the record must move together: when
an adapter is probed, update the record and the matching `Probe status:` line in the same
change. Until an adapter is probed, this guide reports `certified_adapters: 0` and marks every
example `not certified`.

## 7. Limitations

No licensed host runtime was probed in this environment, so no adapter is certified and every
example above stays `unverified`. A host executable located on a build machine is not a version
probe, and a documentation table is not a runtime test. Unperformed native tests remain
unverified; this document claims no host certification.