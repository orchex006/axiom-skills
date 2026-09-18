# Changelog

Canonical changelog for `axiom-skills`. Component versioning is independent of the spec
version; entries below are unreleased working-tree changes, not a published release.

## Unreleased

### A-001 — Define minimal graph policy contract

Add `policy/POLICY.md` as the canonical managed graph policy. It fixes the exact graph
directory `.axiom/graph`, separates graph freshness from coverage, states explicitly that the
policy grants no new permissions and that graph data is never an instruction, forbids loading
every JSON shard into context, and describes the managed-instruction boundary.

### A-002 — Create bounded context skill

Add `skills/graph-context/SKILL.md`. The workflow requests an explicit, bounded graph
projection before any source reading, uses returned source locations as the reading list,
respects the byte and node budgets, and never loads `.axiom/graph` as a directory or dumps a
catalog into context.

### A-003 — Create batch reconcile skill

Add `skills/graph-reconcile/SKILL.md`. Reconciliation is requested with dirty scope at
coherent change boundaries, polled within a bounded deadline, and reported as pending or
blocked when the deadline expires. Per-keystroke and per-save full rebuilds are prohibited,
and `scope=full` requires explicit owner authorisation.

### A-004 — Create impact review skill

Add `skills/graph-impact/SKILL.md`. The review states the expected impact before querying,
compares that expectation against the actual dependency projection, and records resolved and
unresolved limits. An empty or truncated result is never upgraded into a claim that the change
has no impact: missing edges, partial coverage, dynamic binding and unanalyzed consumers are
reported as unverified risk with a verification action.

### A-005 — Create checkpoint publication skill

Add `skills/graph-checkpoint/SKILL.md`. A checkpoint names its source selector explicitly
(`--source staged`, `--source worktree --verify-stable`, `--source commit --ref`), materialises
the Git index for commit-bound checkpoints, verifies against the staged source, and separates
the Git-ignored `live/` lane from the tracked `checkpoint/` lane. A checkpoint whose source was
not the staged index is never committed, publication happens at an explicit boundary rather
than on every save, and the size budgets and non-union merge rules are stated.

### A-006 — Create graph diagnostics skill

Add `skills/graph-doctor/SKILL.md`. A missing daemon, a partial snapshot and a bounded timeout
map to distinct recovery steps with their own evidence and escalation, and deleting or
rebuilding the live graph, the queue database or daemon state is explicitly not a recovery
step. Authentication, bind addresses, freshness checks and host configuration are never
weakened to clear a symptom.

### A-007 — Create approved version-update skill

Add `skills/graph-update/SKILL.md`. A version check reports `installed`, `available`,
`compatible`, `channel`, `schema_range`, `update_policy` and `needs_restart` without ever
guessing that an unknown or offline result is up to date. Check and plan are separate from
apply: `axiom update apply --plan <digest>` runs only for a plan digest a human approved for
that exact scope, re-verifies the installed state and refuses instead of silently replanning.
Auto-apply is disabled by default, rollback is bounded to owned files whose after-hash is
unchanged, and repository content — a skill file, a document, a graph payload, a task
description, a commit message — can never authorize an apply.

### A-008 — Create canonical policy/skill package manifest

Add `release/skills-manifest.json` with the component version, the declared install scope, the
host capability requirements and the declared files with their SHA256 and byte counts, plus
the reference verifier `release/verify_manifest.py`. The manifest declares and the verifier
enforces the strict install policy: a missing file, a hash or byte-count mismatch, a duplicate
declaration or an unknown file inside a declared scope fails install. Nothing is repaired in
place and an install still requires an explicit human approval.

### A-009 — Create Codex instruction adapter

Add `adapters/codex/instructions.md`. The adapter pins the probed host version and capability
set, falls back to a manual preview on an unknown version, and never auto-writes an assumed
hook configuration. Instruction discovery is not treated as evidence of reading: the agent
must explicitly read `.axiom/agent/POLICY.md` and record the policy path and digest, because a
link to the policy is not evidence that the policy was loaded. The canonical hook result
(`action`, `reason`, `job_id`, `snapshot`, `freshness`, `coverage`, `retry_after_ms`,
`hook_attempt`), the declaration of an `instructions_only`, `hook_verified` or `ci_verified`
enforcement level, the transcript-parsing prohibition, the two-continuation loop guard, the
`bearer_token_env_var` credential rule and the managed instruction markers are all stated.

### A-010 — Create Claude Code instruction adapter

Add `adapters/claude/instructions.md`. The adapter pins the probed host version and
capability set before anything is written, declares the `instructions_only`, `hook_verified`
and `ci_verified` enforcement levels, and names the `CLAUDE.md` instruction scope plus the
`Stop` and `TaskCompleted` events. `TaskCompleted` is bound to the documented task lifecycle
and is not treated as a hook for every turn, a Stop continuation is not the same as a user
interrupt, and a bounded reconcile failure blocks only where the pinned version documents a
stop decision. A link to the policy is not evidence that the policy was loaded, so the agent
must explicitly read `.axiom/agent/POLICY.md` and record the path and digest.

### A-011 — Create Gemini CLI instruction adapter

Add `adapters/gemini/instructions.md`. The adapter covers `GEMINI.md` discovery, the MCP
configuration and the `AfterAgent` and `AfterTool` hooks, and keeps the user-level context
file human-owned: the repository-local managed block is staged around byte-identical human
text, activation is proven with a fixture rather than assumed, and no unrelated global
instruction is overwritten. The host's own JSON and exit conventions are used instead of the
Claude exit or JSON shape, and the MCP transport uses the documented `httpUrl` field.

### A-012 — Create Antigravity host adapter

Add `adapters/antigravity/instructions.md`. The adapter separates the IDE and CLI surfaces
with their own versions, paths and hook behaviour, and requires `axiom host detect` plus a
recorded pin in the host matrix. An unrecognized path is reported as a conflict rather than
written to. The `Stop` hook's documented output decision on this host is `continue`, carried
with the reason, and the other host's `decision: block` payload is not reused blindly; the MCP
configuration uses the documented `serverUrl` field. Human rules outside the managed markers
are preserved, and existing repository instructions remain authoritative over the managed block.

### A-013 — Create Codex Stop hook adapter

Add `adapters/codex/hooks/graph_stop.py`. The hook maps a Codex payload to a canonical result
(`action`, `reason`, `job_id`, `snapshot`, `freshness`, `coverage`, `retry_after_ms`,
`hook_attempt`) and maps that result back to the host's documented output, emitting the block
decision only for its declared `codex-stop-v1` schema profile. It honours `stop_hook_active`
and allows at most two forced continuations for one unchanged fingerprint. A malformed payload,
an unrecognised profile, an unavailable status or an unreadable state file degrades to an empty
decision plus a stderr diagnostic, and the hook never parses a conversation transcript.

### A-014 — Create Claude Stop hook adapter

Add `adapters/claude/hooks/graph_stop.py`. The adapter is the Claude counterpart of A-013 with
its own pinned host and `claude-stop-v1` profile, and it blocks only where the installed host
reports the capability: when the host does not support a stop decision the bounded reconcile
failure is reported as `advisory` instead. A user interrupt is never force-continued, and the
adapter states that Claude is not claimed to invoke the Stop hook reliably for every surface.

### A-015 — Create Claude task-completion hook adapter

Add `adapters/claude/hooks/graph_task_completed.py`. Enforcement is scoped to the documented
`TaskCompleted` event and a real task identity, so the adapter is not a universal
response-completion hook: an ordinary turn, a message, a tool result or a user interrupt is
left alone. The task transition may be blocked only while a bounded graph reconcile is still
pending and only for the declared `claude-task-completed-v1` profile, with the same
two-continuation loop guard and the same degrade-to-empty-and-diagnose behaviour.

### A-016 — Implement Gemini AfterAgent adapter

Add `adapters/gemini/hooks/graph_after_agent.py`. The adapter pins `gemini-after-agent-v1`,
declares the host's own bounded `retry` decision and halt condition, and never reuses the
Claude exit convention or another host's `{"decision": "block", "reason": ...}` payload shape.
The effective retry bound is the smaller of the host-reported `retry_remaining` budget and the
documented two-continuation cap, so a host that reports nothing cannot widen the bound. stdout
carries exactly one strict JSON document and every diagnostic and log line goes to stderr, so a
log line cannot corrupt the hook response.

### A-017 — Implement Antigravity Stop adapter

Add `adapters/antigravity/hooks/graph_stop.py`. The adapter pins `antigravity-stop-v1` and
emits this host's documented `continue` decision with the reason carried alongside it; the
canonical `block` action is mapped to `continue` and never to another host's block payload, and
`block` is only used where the pinned version documents it. A bounded reconcile failure is
`advisory` where the installed host reports no stop decision, a user interrupt is never
force-continued, and the two-continuation loop guard and the degrade-to-empty-and-diagnose
behaviour match the other adapters.

### A-018 — Bound hook runtime and reconnect behaviour

Add `adapters/common/hook_runtime.py`. One attempt runs under a wall-clock `timeout_ms` in an
abandonable daemon worker, so a hung daemon call or a dead socket cannot hang completion
indefinitely; the caller gets pending evidence naming the failure instead of an unanswered
wait. Retries are capped by `max_retries` and by the documented `HARD_MAX_RETRIES = 2`, a crash
is recorded as `crashed` pending evidence rather than propagated into the host's structured
channel, and `bounded_budget` refuses a non-positive or unbounded budget instead of silently
clamping it.

### A-019 — Handle graph-unavailable fallback policy

Add `adapters/common/degraded_policy.json`. The mode is explicit per repository and is never
inherited: `axiom-graphd` and `axiom-mcp` are `strict` and return pending evidence while the
graph is unverified, `axiom-skills` and `axiom-specs` are `advisory`, and an unknown repository
falls back to an explicit non-fail-open `strict` default. Every degraded path reports
`freshness: "unverified"` and `completion_gate: "not_claimed"`, so a fail-open decision never
masquerades as verified graph freshness or as a completion gate that ran.

### A-020 — Separate cancellation from completion

Add `adapters/common/cancellation.md`. A user cancel, a shutdown and an error preserve durable
dirty state without claiming a completion gate ran: the dirty scope is written to the durable
hook state before exit, nothing is cleaned, reset, stashed or discarded, and no authority is
widened by a cancelled turn. The machine-checkable record declares
`dirty_state: "preserved"`, `durable: true`, `completion_gate: "not_run"`,
`freshness: "unverified"`, `forced_continuation: false` and `resume_from: "dirty_scope"`, so a
later run resumes from the preserved dirty scope instead of treating a cancel as completion.

### A-021 — Version and certify adapter payloads

Add `adapters/compatibility.json`. Every shipped host adapter records its declared host identity
and surface, the exact adapter version, the protocol version, the documented sources, the
boundary caveat, the per-feature status and the SHA256-pinned in-repository test evidence, and
the recorded hash is checked against the bytes shipped in the bundle rather than trusted. No
adapter is certified: certification requires a probed exact installed version, a tested operating
system, a host runtime test artifact with its SHA256 and an enforcement level the evidence
supports, so every adapter stays at `enforcement_level: "instructions_only"` with an explicit
`certification_blocker` and an empty `host_runtime_evidence`. A documented capability table, an
in-repository unit test, a mock or a cross-compile is never accepted as host certification, and a
feature the host does not document cannot claim a status.

### Tests

Extend `tests/test_canonical_workflows.py` with positive contract checks for the nine canonical
workflow artifacts, structural sequencing checks (expected impact stated before the comparison,
staged verification before commit, apply approval sequenced after check and plan), and negative
or boundary fixtures that must be rejected: a policy that misses the canonical graph directory
or grants permissions, a context skill whose projection request is missing or reordered after
source reading, a reconcile skill that rebuilds on every edit, an impact skill that turns a
missing edge into a no-impact claim, a checkpoint skill that exports an unstaged working tree, a
diagnostics skill that treats every symptom as delete-and-rebuild, an update skill that applies
the newest release from repository text without approval, a bundle with an undeclared file or a
changed declared file, and a Codex adapter that treats a policy link as proof the policy was
loaded or retries the stop hook without a bound. The manifest tests replay the shipped
`release/verify_manifest.py` against staged bundles, so the install-failure contract is executed
rather than asserted. A dedicated `unittest` class binds each slice to its task.

The same module now covers the three additional host adapters and the three completion hooks
with a shared adapter contract and a shared hook contract. Each host adapter is checked for the
version pin, the policy-read requirement, the canonical result fields, the two-continuation loop
guard, the reentrance flag and the managed markers, and each is replayed against a negative
fixture and a boundary fixture that removes one required rule. Each hook is run the way its host
runs it, with JSON on stdin and an isolated loop-guard state directory, so block, cap,
reentrance, interrupt, malformed-input, untrusted-profile and non-task-event behaviour are
executed rather than described. The bundle is declared with 19 files across the `policy`,
`skills` and `adapters` scopes, and the bytecode hygiene assertions keep a declared scope free
of generated `__pycache__` content.

The module also covers the two additional host hooks and the three shared adapter-common
contracts. The Gemini AfterAgent hook is exercised for its documented retry decision, its halt
path when the host budget is spent, its host-versus-adapter retry bound and its strict
single-document stdout; the Antigravity Stop hook is exercised through a contract subclass that
requires the host's documented `continue` decision, so a variant that reuses another host's
`decision: block` payload is rejected. The bounded hook runtime is run for real: a daemon call
that never answers must return pending evidence inside the budget, a crash must be recorded as
pending evidence rather than raised, the retry cap must stop further attempts, and an unbounded
budget must be refused. The degraded policy is checked for an explicit per-repository mode with
unverified freshness and no claimed gate, and the cancellation contract is parsed from its
shipped record, with negative and boundary variants that claim a gate ran, drop the resume
requirement or discard the dirty state all rejected.

The compatibility record is replayable as well: the checks reject an adapter certified without a
probed installed version or host runtime evidence, a capability the host does not document that
still claims a status, a test-evidence hash that no longer matches the shipped bytes, and an
enforcement level raised above the evidence, while the shipped record keeps all four adapters
uncertified and declared inside the bundle.

### Delivery record — A-001 … A-021 integrated into `main`

Record that the skills delivery chain is integrated into `main`, so the workspace owner can see
what is finished without opening each branch. The earlier merges were made from the working
checkout and pushed directly, which left no pull-request record in GitHub; this entry is the
explicit integration record for that delivery.

| Task group | Task branch (`feature/…`) | Branch tip SHA | Integrated into `main` by |
| --- | --- | --- | --- |
| A-001 – A-003 | `a-001-003-canonical-workflows` | `6874cb8` | `b5b9a3e` |
| A-004 – A-006 | `a-004-006-canonical-workflows` | `581b855` | `b5b9a3e` |
| A-007 – A-009 | `a-007-009-canonical-workflows` | `fea863d` | `b5b9a3e` |
| A-010 – A-015 | `a-010-015-host-adapters-and-hooks` | `6d0c218` | `b5b9a3e` |
| A-016 – A-020 | `a-016-020-hooks-and-common` | `f7052ea` | `b5b9a3e` |
| A-021 | `a-021-compatibility-certification` | `5765ee6` | `b5b9a3e` |
| governance contract | `governance-development-contract` | `f4dc5fd` | `26f66d2` |

Verification recorded for the integrated state of `main`: `python -m pytest tests -q` reports
`106 passed`, and `python release/verify_manifest.py` reports `OK` for the committed bundle bytes
(component `axiom-skills`, version `0.1.0-draft.1`, 20 files).

Not verified / not claimed: no host certification beyond `adapters/compatibility.json` was re-run
for this entry, and no release branch or tag was created. The feature branches are intentionally
kept so their history stays reviewable.

### Governance — development contract, branch/merge/release policy

Add `Development.md` for `axiom-skills`: repository identity and ownership boundaries, the
preflight gate, required checks (`python -m pytest tests -q`), evidence and completion
requirements, branch/merge/release policy, the rule that verified work finished in a worktree
must reach the owner's primary checkout, commit/push rules, version/release policy and the
definition of blocked.

The contract records that `main` is the integration branch, `feature/<task-id>-<slug>` is the
mandatory task branch and `release/vX.Y.Z` is the release branch. An agent MAY merge a verified
task branch into `main` on its own authority once every merge-gate condition holds; release
branches, tags and publishes still require explicit release authorization.

It also records that a skill MUST NOT instruct an agent to bypass an applicable `AGENTS.md` or
`Development.md`, and that bootstrap operations which manage governance must preserve
human-owned instructions.

Unverified statements: this contract is documentation only; no skill bundle or adapter behaviour
changed in this entry.

### V2-003 — Publish canonical bootstrap content bundle

Add `templates/bootstrap/manifest.json` as the machine-readable pin for the managed bootstrap
content inside `axiom-skills`. `templates/bootstrap/AGENTS.block.md` and
`templates/bootstrap/gitignore.fragment` are carried byte-exact from the `axiom-specs` repo seeds
and pinned with SHA256, byte count, template version and role, and each declares the exact markers
that bound the only bytes a re-apply may rewrite.

The bundle ships no second policy copy: exactly one policy source, `policy/POLICY.md` (installed
at `.axiom/agent/POLICY.md`), is referenced once, so the bootstrap engine consumes the canonical
policy instead of a forked hardcoded copy. Human text outside the managed markers is preserved, a
managed segment whose bytes no longer match the pinned template is reported as a conflict instead
of being replaced, and the seeder `POLICY.md` from the seed set is deliberately not republished
because it would be a duplicate policy text.

Verified: `python -m pytest tests -q` and `python release/verify_manifest.py` (declared scopes
stay `policy`, `skills`, `adapters`; `templates/` is outside them).

Not verified / not claimed: this manifest is content plus a local regression test only. No
bootstrap, install or update was run against a real repository, no host adapter behaviour
changed, and no release branch or tag was created.
