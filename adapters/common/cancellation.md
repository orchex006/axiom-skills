# Cancellation Is Not Completion

Owner: `axiom-skills/adapters/common` · Profile: `cancellation-v1` · Spec baseline: `2.0.0-draft.1`

This document fixes the contract every Axiom completion hook follows when a turn ends for a
reason that is not a completed, reconciled task. It exists because the three paths below can
end a turn at any moment, and none of them is allowed to leave the impression that a
completion gate ran.

## 1. The three cancellation paths

| Path | What the host reports | What the hook does |
|---|---|---|
| User cancel | a user interrupt or cancel reason on the stop or after-turn event | allow, force no continuation |
| Shutdown | the host is exiting; no further turn will run | allow, write the durable record first |
| Error or abort | the host or the agent aborted with an error | allow, never convert the abort into pending work |

A user cancel, a shutdown and an error are **preserved outcomes**, not failures of the task:
each of the three paths preserves durable dirty state without claiming a completion gate ran.
The hook never retries any of them: a cancel is not completion, and forced continuation after
an interrupt would both ignore the human and risk an unbounded loop. The reentrance flag the
host supplies (`stop_hook_active`) is honoured on these paths exactly as it is on a normal
stop, so a requested continuation still cannot recurse.

## 2. Durable dirty state is preserved

When a turn is cancelled, the work that is not yet reconciled must survive what cancelled it.

- The dirty scope is written to the durable local state before the host exits: the bounded
  dirty record goes to the hook state directory (`$AXIOM_HOOK_STATE_DIR`, or
  `<cwd>/.axiom/local/hook-state/` by default) and the pending job status stays with the
  queue, so a cancelled turn leaves durable dirty state rather than an ambiguous empty one.
- Nothing is cleaned, reset, stashed or discarded on cancellation. A shutdown must not be
  used as a reason to drop the only record of unreconciled work, and no source file is
  touched by this path.
- Cancellation never widens authority: no apply, no commit, no push, no config write and no
  credential read happens because a turn was cancelled.
- The durable record is byte-stable and can be read again: a later run resumes from
  `dirty_scope`, re-verifies the graph and then continues normally.

## 3. What is never claimed

- A cancelled, shut down or errored turn never claims that a completion gate ran. The record
  carries `completion_gate: "not_run"` and no adapter may upgrade that to a verified gate.
- Freshness is never upgraded either: the record keeps `freshness: "unverified"`, so a
  cancellation is preserved without claiming a verified graph freshness it does not have.
- Cancellation is not evidence of completion and not evidence of failure of the task; it is
  evidence that the work is still dirty and must be reconciled later.
- Diagnostics still go to stderr only, so the host's structured channel stays a single JSON
  document, and the hook still exits zero.

## 4. The canonical cancellation record

The record below is the shape the hook writes when it preserves a cancelled turn.

```json
{
  "record": "cancellation-v1",
  "outcome": "user_cancel",
  "outcomes": ["user_cancel", "shutdown", "error", "abort"],
  "dirty_state": "preserved",
  "durable": true,
  "durable_location": ".axiom/local/hook-state/",
  "preserved_dirty_scope": true,
  "completion_gate": "not_run",
  "freshness": "unverified",
  "forced_continuation": false,
  "resume_from": "dirty_scope",
  "evidence": "pending"
}
```

- `dirty_state` is `preserved`; it is never `discarded` and never absent.
- `durable` is true, which is what makes the state outlive the process that was cancelled.
- `completion_gate` is `not_run`, and `freshness` is `unverified`. Together they are the
  machine-checkable half of this contract: a fail-open or cancelled path must not masquerade
  as a verified completion gate.
- `forced_continuation` is false, and `resume_from` names the durable dirty scope so the next
  run knows where to start instead of guessing.

## 5. Resume after cancellation

The next run reads the durable record, re-requests the bounded reconcile for the recorded
dirty scope, and only then applies the normal completion rules. A record with
`completion_gate: "not_run"` is never treated as a completed gate, and a record with
`dirty_state: "preserved"` is never treated as a clean tree. If the durable record itself is
missing or unreadable, the hook degrades exactly like every other adapter: it allows the turn
and writes a stderr diagnostic, and it invents neither a gate nor a clean state.