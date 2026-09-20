# axiom-skills

Reusable Agent Skills, host adapters and the managed-item policy for the Axiom
Graph Ecosystem. Specification baseline: `2.0.0-draft.1`, component version
`0.1.0-draft.1` (channel `draft`, `released: false`).

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
  axiom-cli-install       tier-aware install/update/doctor/uninstall through the distributed entrypoint
adapters/                 per-host adapters (see the host table below)
  common/hook_runtime.py  shared bounded runtime: wall-clock budget, retry cap, pending evidence
  common/degraded_policy.json   per-repository strict/advisory mode
  common/cancellation.md  the cancellation-v1 record
  compatibility.json      per-adapter, per-feature status and in-repository test evidence
templates/bootstrap/      managed AGENTS block, gitignore fragment, bootstrap manifest
release/skills-manifest.json   hash-pinned bundle declaration, fail-closed install policy
release/verify_manifest.py     reference verifier for that manifest
docs/                     host compatibility, host wiring and agent workflow guides
tests/                    five test modules
```

## Host adapters

All four supported hosts are usable, and each one expresses the canonical
completion gate in its **own** documented decision vocabulary. There is no
"unsupported host" among them: what differs is the event name and the output
shape, never whether the gate exists. Choosing Codex CLI, Claude Code, Gemini CLI
or Antigravity (AGY) is therefore a matter of which host you already run.

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

`axiom-skills` claims no host certification. `adapters/compatibility.json` records
`version_probe: "not_run"`, `certified: false` and
`enforcement_level: "instructions_only"` for all four adapters, because no
licensed host runtime was available to probe. A documented capability table is not
certification and an in-repository unit test is not host certification. Before
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

`spec.lock.json` pins the immutable `axiom-specs` revision this bundle was
reviewed against, plus a SHA256 digest for each contract it consumes. It is an
**unapproved draft pin**: no released specification revision exists, so the pin is
not owner approval and carries no release coverage.

Validate the pin offline against a checkout of the pinned content:

```bash
python tools/spec-lock-check.py --lock spec.lock.json --spec-root <axiom-specs-checkout>
```

Default mode must accept (`immutable revision and pinned digests verified`).
`--release` deliberately still rejects with
`release-coverage-missing:conformance/fixture-index.json`, because release
coverage is only meaningful against a released revision.

## Install and release status

`release/skills-manifest.json` declares the bundle installed by explicit human
approval only: `requires_explicit_human_approval: true` and a fail-closed policy
where a missing file, a hash mismatch, a byte-count mismatch, an unknown file or a
duplicate declaration each `fail`. The bundle is `released: false` on channel
`draft`; there is no released artifact, no tag and no certification.

## Platform support status

Windows x64, Linux x64, macOS arm64 and macOS x64 are required native targets. No
target is certified and this repository ships no native install/run/uninstall
evidence. Host adapter behaviour is version-specific and is never inferred from
compilation or from a passing in-repository test.

## Documentation

[docs/README.md](docs/README.md) indexes the guides in this repository. Shared
normative contracts stay canonical in `axiom-specs` and are resolved through the
pinned revision, never as a local editable copy.
