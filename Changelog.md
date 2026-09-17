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
