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

### Tests

Extend `tests/test_canonical_workflows.py` with positive contract checks for the six canonical
workflow artifacts, structural sequencing checks (expected impact stated before the comparison,
staged verification before commit), and negative or boundary fixtures that must be rejected: a
policy that misses the canonical graph directory or grants permissions, a context skill whose
projection request is missing or reordered after source reading, a reconcile skill that
rebuilds on every edit, an impact skill that turns a missing edge into a no-impact claim, a
checkpoint skill that exports an unstaged working tree, and a diagnostics skill that treats
every symptom as delete-and-rebuild. A dedicated `unittest` class binds each slice to its task.
