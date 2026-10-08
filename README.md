# axiom-skills

## Current GitHub delivery policy

Skills use one portable bundle across OS targets. GitHub Actions verifies tests, payload hashes and plugin parity; GitHub Releases supplies the checked archive with source revision, version and SHA-256 checksum. No certification, code signing or attestation is required. Host runtime results document capabilities and never gate skill downloads. Existing host permissions, updater integrity and approval checks remain unchanged.


Reusable Agent Skills, host adapters and the managed-item policy for the Axiom
Graph Ecosystem. Specification baseline: `2.0.0-draft.1`, component version
`0.1.1` (portable bundle; installed-host runtime results remain unverified).

**Owner scope:** the eight Agent Skills (the six graph workflow skills plus the
ecosystem installation skill and the distributed-CLI provisioning skill), the
per-host adapters that wire the graph completion gate into a host, the shared
bounded hook runtime, the managed-item policy, and the bootstrap templates that
`axiom-graphd` applies.

It does **not** own the graph runtime (`axiom-graphd`), the query gateway
(`axiom-mcp`) or the ecosystem contracts (`axiom-specs`). The canonical template
bytes are produced here while the bootstrap manifest contract and its application
are owned by `axiom-graphd`; public commands, schema/layout versions and shared
guard semantics change in `axiom-specs` first.

## Repository layout

```text
policy/POLICY.md          managed-item policy, least privilege, degraded operation
skills/                   eight Agent Skills, one SKILL.md each
  graph-context           read the graph for the task at hand
  graph-impact            bound the change surface before editing
  graph-reconcile         request and follow a bounded reconcile
  graph-checkpoint        record a checkpoint with its evidence
  graph-doctor            diagnose the graph service and its prerequisites
  graph-update            check and delegate one approved update plan
  graph-install           provision the ecosystem in the contract order and report honestly
  axiom-cli-install       tier-aware install/update/doctor/uninstall through the distributed entrypoint (axm, the short name of axiom-cli)
adapters/                 per-host adapters (see the host table below)
  common/hook_runtime.py  shared bounded runtime: wall-clock budget, retry cap, pending evidence
  common/degraded_policy.json   per-repository strict/advisory mode
  common/cancellation.md  the cancellation-v1 record
  compatibility.json      per-adapter, per-feature status and in-repository test evidence
templates/bootstrap/      managed AGENTS block, gitignore fragment, bootstrap manifest
release/skills-manifest.json   hash-pinned bundle declaration, fail-closed install policy
release/verify_manifest.py     reference verifier for that manifest
release/build_plugin_bundle.py byte-for-byte check/copy of canonical skills into the plugin
plugins/axiom/            one portable plugin package for four hosts
.agents/plugins/          Codex marketplace catalog
.claude-plugin/           Claude Code marketplace catalog
marketplace-plugins/      cross-host package index and installation guide
docs/                     host compatibility, host wiring and agent workflow guides
tests/                    unit and package validation tests
```

## Plugin distribution

`plugins/axiom` packages the eight canonical skills and policy for Codex, Claude Code,
Gemini CLI and Antigravity. The Codex and Claude marketplaces point to the same
package; Gemini and Antigravity install it by local path. See
[marketplace-plugins/README.md](marketplace-plugins/README.md) for entrypoints.
The plugin does not start an MCP server or install the Axiom runtime. Run
`python release/build_plugin_bundle.py` to check that packaged skills and policy
match the canonical source before publishing or updating the bundle.

## Host adapters

All four host adapters have in-repository implementations, and each one expresses
the canonical completion gate in its **own** documented decision vocabulary.
Installed-host runtime tests remain unverified; the event name and output
shape differ by host. Choose Codex CLI, Claude Code, Gemini CLI or Antigravity
(AGY) only after checking the installed version and its recorded capabilities.

| Host | Adapter | Completion gate | Host decision output |
| --- | --- | --- | --- |
| Codex CLI | `adapters/codex/instructions.md` | `Stop` | `{"decision": "block", "reason": ...}` (`adapters/codex/hooks/graph_stop.py`) |
| Claude Code | `adapters/claude/instructions.md` | `Stop` and `TaskCompleted` | `{"decision": "block", "reason": ...}` (`graph_stop.py`, `graph_task_completed.py`) |
| Gemini CLI | `adapters/gemini/instructions.md` | `AfterAgent` (and `AfterTool`) | `{"decision": "retry", "reason": ..., "retry_after_ms": ...}` (`graph_after_agent.py`) |
| Antigravity (AGY) | `adapters/antigravity/instructions.md` | `Stop` | `{"decision": "continue", "reason": ...}` (`graph_stop.py`) |

Every adapter shares the same canonical result (`action`, `reason`, `job_id`,
`snapshot`, `freshness`, `coverage`, `retry_after_ms`, `hook_attempt`), the same
loop-guard key `(host, session or turn or task, source fingerprint, target
barrier)`, and the same cap of two forced continuations per unchanged
fingerprint. A user interrupt, a shutdown or a host error is never force-continued.
One host's decision payload is never copied into another host's schema, because
`block`, `retry` and `continue` are the hosts' own shapes and are not
interchangeable.

Where a host genuinely has no equivalent event, the adapter records the feature as
`not_documented` in `adapters/compatibility.json` instead of inventing a hook the
host cannot deliver. Two examples: Gemini CLI documents no task-completion event,
and Antigravity does not document an `AfterAgent` event, so neither adapter claims
one. That is a faithful record of the host's surface, not a missing Axiom
capability - in both cases the host's documented completion gate is implemented.

Antigravity ships an IDE surface and a CLI surface with separate versions,
configuration paths and hook behaviour. Resolve them separately; never assume one
surface's paths apply to the other.

### Version probing

`axiom-skills` claims no host runtime verification. `adapters/compatibility.json` records
`version_probe: "not_run"`, `runtime_verified: false` and
`enforcement_level: "instructions_only"` for all four adapters, because no
licensed host runtime was available to probe. A documented capability table is not
runtime verification and an in-repository unit test is not host runtime verification. Before
wiring an adapter into a repository, probe the exact installed version and record
it in `compatibility/host-matrix.json`; see
[docs/host-compatibility.md](docs/host-compatibility.md) and
[docs/guides/hosts.md](docs/guides/hosts.md).

## Build and verify

```bash
python -m pytest tests -q
python release/verify_manifest.py
```

`python -m pytest tests -q` is this repository's required check. Run
`python release/verify_manifest.py` as well whenever the manifest or an adapter
changes: `release/skills-manifest.json` hash-pins every file under `policy/`,
`skills/` and `adapters/`, so any content change there must regenerate the
manifest in the same commit. Both checks are run against the final bytes and the
real command and exit code are recorded; a check that did not run is recorded as
unverified.

## Specification pin

`spec.lock.json` pins the immutable K-604 `axiom-specs` draft revision this bundle
was reviewed against, plus a SHA256 digest for each contract it consumes. The
pin passes coverage validation; this does not publish the specification or
verify a product release.

Validate the pin offline against the exact immutable K-604 revision. The
validator is canonical in `axiom-specs` (`tools/spec-lock-check.py`) and is not
shipped in this bundle. From an archive of pinned revision
`51fc8f92a56db0471205f368b6bfeefe434b165d`, point `--lock` at this
repository's `spec.lock.json`:

```bash
python tools/spec-lock-check.py --lock ../axiom-skills/spec.lock.json --spec-root . --release --json
```

Use `--release --json` to check the pin's required coverage. The `--release`
flag here validates pin coverage only; the revision remains a draft feature
revision pending independent review and main integration.

## Install and release status

`release/skills-manifest.json` declares the bundle installed by explicit human
approval only: `requires_explicit_human_approval: true` and a fail-closed policy
where a missing file, a hash mismatch, a byte-count mismatch, an unknown file or a
duplicate declaration each `fail`. The current manifest describes an unpublished `experimental` candidate. Historical K-101 release records remain unchanged. The complete 44-file owner payload can be supplied to the
distribution converter with `release/skills-manifest.json` at its root. The
converter builds the engine-format `skills/bundle.json` from these exact owner
bytes; a minimal fixture is insufficient.

For a local consumer candidate, run `python3 release/verify_manifest.py`, then
`python3 release/build_engine_source.py --out <new-empty-path>`. The output has
`skills-manifest.json` and all 44 declared payload paths at its root. Supply
that root to the distribution's owner-manifest conversion path. The builder
refuses an existing output path, missing or changed bytes, and undeclared files.

## Platform support status

There is one portable skills bundle, without an OS/architecture release matrix. Historical K-101/K-201/K-301/K-401 task lanes record consumer handoffs, not separate skill variants or prerequisites for portable release. Invoked runtime and installer artifacts retain their declared target support. Host
adapter behaviour is version-specific and is never inferred from a passing
in-repository test.

## Documentation

[docs/README.md](docs/README.md) indexes the guides in this repository. Shared
normative contracts stay canonical in `axiom-specs` and are resolved through the
pinned revision, never as a local editable copy.

## Public CI specification boundary

The specification repository is private. Public skills CI validates the immutable owner pin metadata, bundle bytes, portable packaging and available owner tests without fetching private specification content. Exact contract-byte verification is recorded by the authorized specification handoff. Tests requiring a separate specification checkout report skipped on public CI; they are not relabelled passed. No cross-repository token or private source publication is required.

## K-608 canonical bootstrap content

The portable owner payload includes the exact block, gitignore fragment and template manifest under templates/bootstrap. Graphd consumes these owner-pinned bytes instead of hardcoding another policy source. The policy remains a single file at policy/POLICY.md. No template bytes, human governance or OS-specific skill copies are changed.
