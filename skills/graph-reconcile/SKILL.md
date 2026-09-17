---
name: graph-reconcile
description: Reconcile only the dirty scope of the repository graph at coherent change boundaries, then verify and report freshness and coverage without rebuilding the whole graph.
---

# Dirty-scope reconciliation

Use this skill when source has changed and the repository graph needs to catch up before a
review, a checkpoint or a completion claim.

This skill is workflow guidance. It does not grant permissions and it does not replace the
repository test suite or the host completion gate.

## Coherent boundary

Reconcile at a coherent boundary, meaning a point where a logical unit of work has settled:

- after a batch of related edits, not after each individual edit;
- after a formatter, rename or bulk move has finished writing;
- after a Git operation that changed many paths (checkout, merge, rebase, stash apply);
- immediately before you report a task, review or checkpoint as complete.

A coherent boundary is a scope boundary, not a clock boundary. Do not reconcile on a timer,
on every tool call, on every save event, or per keystroke.

## Procedure

1. **Capture the scope.** Record which projects and paths changed. Let the daemon's own
   inventory, watcher hints and byte fingerprints decide what is genuinely dirty; do not
   pre-compute a file list you believe is authoritative.
2. **Request dirty-scope reconciliation.** Call `graph_reconcile` with the solution, the
   bounded project scope, `scope=dirty`, a bounded `wait_timeout_ms`, and a `reason` that
   names this boundary. Reuse the idempotency key for a retry of the same logical request.
3. **Poll boundedly.** Poll `graph_job` for the returned job id within a bounded deadline.
   An existing verified publication that already satisfies the captured barrier may return
   immediately; that is a success, not a no-op to be repeated.
4. **Read the outcome.** Inspect job state, freshness, coverage, verification mode, unresolved
   references and the exact generation vector.
5. **Verify before claiming.** Confirm that the affected scope is covered and that the
   generation you report is the generation you observed. Reconcile plus verify does not
   replace running the repository's real tests.
6. **Report.** State the boundary you used, the scope, the observed freshness and coverage,
   the generation vector, unresolved references and anything still pending.

## Prohibited behaviours

- Per-keystroke or per-save full rebuilds. Requesting a full rebuild after every edit is
  prohibited; it wastes the queue and still races the editor.
- `scope=full` without explicit owner authorisation. Full reindex is deliberate, recorded
  work, not a recovery habit.
- Unbounded polling, unbounded retry or looping until an arbitrary green status appears.
  Maximum forced continuation against unchanged input is two attempts, then report blocked.
- Treating a timeout, a cancellation or a pending job as `fresh`. A timeout means pending or
  blocked; say so.
- Cancelling a shared reconcile job merely because your own client disconnected.
- Continuing to edit the same files during apply verification and then blaming the graph.

## Failure and fallback

- If the daemon is unavailable but a valid checkpoint exists, report snapshot-only mode with
  `freshness=unknown` and continue read-only work under the policy.
- If reconciliation cannot complete inside the deadline, surface the blocked reason, keep the
  dirty state, and stop forcing continuation.
- If a conflict, corruption or incompatible schema is reported, do not ignore the warning and
  do not repair, reinstall or reconfigure the environment without approval.
