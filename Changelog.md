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

### Tests

Add `tests/test_canonical_workflows.py` with positive checks for the three artifacts plus
negative fixtures that must be rejected: a policy that misses the canonical graph directory
or grants permissions, a context skill whose projection request is missing or reordered after
source reading, and a reconcile skill that rebuilds on every edit.
