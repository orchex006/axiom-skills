# Agent Workflow Guide — Skills, Bounded Hooks and Completion

Owner: `axiom-skills`. Spec baseline: `2.0.0-draft.1`.

This guide explains how the canonical graph skills and the bounded completion hooks cooperate
during one agent turn: what each layer is allowed to decide, how a timeout is bounded, when a
hook may block a stop, and what happens when a turn is cancelled or the graph is unavailable.

It is written for an agent (or a human reviewer) working in a repository that has Axiom
installed. Every claim about runtime behaviour below names the exact file and symbol that
implements it, so the claim can be re-checked against the shipped bytes instead of taken on
trust. Behaviour the repository does **not** implement is listed under
[What is not guaranteed](#what-is-not-guaranteed) rather than described as if it existed.

Path decision: the task card proposed `docs/guides/agent-workflow.md` and this is that path.
Spec A states the repository owns documentation under `docs/`; the installable bundle scope is
declared as `policy`, `skills` and `adapters`
(`release/skills-manifest.json` → `install_policy.declared_scope`), so a guide under `docs/`
adds reviewable documentation without entering the install manifest or changing the bytes the
reference verifier (`release/verify_manifest.py`) checks.

---

## 1. The ownership boundary: there is no universal completion gate

Axiom does not own the agent harness, so it cannot force every host to hold a turn open until
the graph is reconciled. The normative statement is in
`axiom-specs/repo-seeds/axiom-skills/docs/25-HOST-ADAPTERS-AND-HOOKS.md` §4: a universal hard
completion gate is **not** promised, and CI, graph verification and checklists remain
*independent* delivery gates instead.

Three shipped artifacts make that boundary concrete:

| Layer | Artifact | What it is allowed to decide |
|---|---|---|
| Workflow guidance | `skills/*/SKILL.md` (6 skills) | Advises what to query and when; grants no permission and is not a gate |
| Host decision | `adapters/*/hooks/*.py` | May ask a host to continue/retry a turn inside a bounded loop guard |
| Shared runtime | `adapters/common/hook_runtime.py` | Bounds one operation in time; returns pending evidence instead of waiting |

Every skill states the same boundary in its own words. `skills/graph-context/SKILL.md` says
"This skill is workflow guidance, not a permission grant and not a completion gate";
`skills/graph-reconcile/SKILL.md`, `skills/graph-impact/SKILL.md`,
`skills/graph-checkpoint/SKILL.md` and `skills/graph-doctor/SKILL.md` each state that the skill
does not replace the repository test suite or the host completion gate; and
`policy/POLICY.md` §4 ("No new permissions") records that reading graph context is never
permission to edit source and that a graph payload is never an instruction.

The certification record agrees that this boundary is real: `adapters/compatibility.json` →
`certification_summary` reports `certified_adapters: 0` and `host_runtime_tests_run: 0` with
status `documented_and_in_repository_tested_not_certified`. No adapter may claim an
enforcement level above the evidence it holds
(`certification_rules.enforcement_level_must_not_exceed_evidence`), and an in-repository unit
test is explicitly not host certification
(`certification_rules.in_repository_unit_test_is_not_host_certification`).

Consequence for an agent: **the graph hooks are best-effort coordination, not a guarantee that
your task passed.** The repository's own test suite and the task's evidence remain the
authority on completion.

---

## 2. Timeout behaviour: one bounded budget, always answered

The shared runtime is `adapters/common/hook_runtime.py`. A caller hands it one operation and a
budget; it always returns a result rather than waiting forever.

| Rule | Symbol | Behaviour |
|---|---|---|
| Default single-attempt budget | `DEFAULT_TIMEOUT_MS` (= 2000) | Milliseconds for one attempt |
| Default retry allowance | `DEFAULT_MAX_RETRIES` (= 2) | Retries *after* the first attempt |
| Hard retry ceiling | `HARD_MAX_RETRIES` (= 2) | A larger count is refused, not clamped |
| Budget validation | `bounded_budget()` | Raises `UnboundedBudgetError` for a non-positive timeout, a negative retry count, or a retry count above `HARD_MAX_RETRIES` |
| One bounded attempt | `_run_once()` | Runs the operation in a `threading.Thread(..., daemon=True)` and waits `timeout_ms / 1000.0` seconds; on expiry returns `(None, "timeout")` without joining or killing the worker |
| Crash capture | `_run_once()` | A raising operation is captured and returned as `(None, "crashed")`; it never propagates into the host's structured channel |
| Bounded run | `run_bounded()` | Retries at most `max_retries` times, then always returns a result |

The failure vocabulary is fixed by `FAILURE_KINDS = ("timeout", "crashed", "retry_cap")`, and a
finished run reports `evidence: "complete"` while any exhausted run reports
`evidence: "pending"` (`EVIDENCE_STATES`), a `failure` kind, `retries_left`, `hook_attempt`,
`elapsed_ms`, `max_retries` and `timeout_ms` (`_pending_result()`).

Two properties matter for workflow design:

1. **Worst case is bounded and knowable.** With defaults, the longest a hook can wait is
   `(max_retries + 1) * timeout_ms` = 3 attempts × 2000 ms = 6000 ms. The loop in `run_bounded()`
   runs `range(1, budget["max_retries"] + 2)`, which is exactly that many attempts.
2. **A timeout is evidence, not an exception.** `_run_once()` returns the `timeout` failure
   instead of raising, so a hung daemon call cannot hang completion and cannot break the host's
   JSON channel.

---

## 3. Block behaviour: per-host, opt-in, and bounded by a loop guard

A *block* is a canonical action (`ACTIONS = ("allow", "continue", "block", "advisory")` in
`hook_runtime.py`), but only some hosts can express it. Each adapter maps the canonical result
to that host's documented schema; one host's decision payload is never copied into another
host's schema.

| Adapter | Hook | Block gate | Host output when canonical `block` |
|---|---|---|---|
| Claude Code | `adapters/claude/hooks/graph_stop.py` | `supports_stop_decision()` — explicit `False` degrades to `advisory` | `to_host_output()` → `{"decision": "block", "reason": ...}` |
| Claude Code | `adapters/claude/hooks/graph_task_completed.py` | `supports_completion_decision()`; requires the `TaskCompleted` event **and** a task identity | `to_host_output()` → `{"decision": "block", "reason": ...}` |
| Codex CLI | `adapters/codex/hooks/graph_stop.py` | no capability flag is consulted | `to_host_output()` → `{"decision": "block", "reason": ...}` |
| Gemini CLI | `adapters/gemini/hooks/graph_after_agent.py` | `retry_budget()` — an absent or non-integer `retry_remaining` collapses to `MAX_FORCED_CONTINUATIONS`, never to unlimited | `to_host_output()` → `{"decision": "retry", "reason": ...}` (+ `retry_after_ms`) |
| Antigravity (AGY) | `adapters/antigravity/hooks/graph_stop.py` | `supports_stop_decision()`; explicit `False` degrades to `advisory` | `to_host_output()` → `{"decision": "continue", "reason": ...}` |

Bound limits that apply to every adapter:

- **Continuation cap.** `MAX_FORCED_CONTINUATIONS = 2` in each hook module. When the recorded
  attempt count exceeds it, the adapter stops forcing: Claude/Codex return
  `canonical_result("allow", "forced continuation budget is exhausted")`, Antigravity returns
  `allow` with "retry budget is exhausted", and Gemini returns
  `canonical_result("allow", "retry budget is exhausted")`.
- **Reentrance.** A host-supplied `stop_hook_active: true` short-circuits to `allow` before any
  graph decision, so a requested continuation cannot recurse.
- **Interrupts are never forced.** `NEVER_FORCED_STOP_REASONS` (Claude, Codex, Antigravity) and
  `NEVER_RETRIED_REASONS` (Gemini) include `cancel`, `cancelled`, `abort`, `aborted`, `error`,
  `shutdown` and `timeout`; a matching stop reason returns `allow` immediately.
- **Per-fingerprint identity.** The loop guard key is
  `loop_key()` = `(host, session, source fingerprint, target barrier)`, so the same unchanged
  fingerprint is what runs out of continuations, and progress resets the count.
- **State is on disk, and its absence is safe.** `load_attempts()` / `store_attempts()` read and
  write the hook state file (`$AXIOM_HOOK_STATE_DIR`, else `<cwd>/.axiom/local/hook-state/`);
  if it is unreadable or unwritable the adapter returns `allow` with a diagnostic rather than
  blocking on an unknown attempt count.

An agent should therefore read a block as "the host was asked for one more bounded attempt",
not as "the work is wrong" and not as "the work is complete".

---

## 4. Cancel, shutdown and error: cancelled is not completed

`adapters/common/cancellation.md` fixes the contract (`profile: cancellation-v1`) for the three
paths that can end a turn outside a reconciled completion. In all three — user cancel,
shutdown, and error/abort — the hook lets the turn end, forces no continuation, and writes a
durable record before the host exits.

The canonical record has four machine-checkable fields:

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

- `completion_gate: "not_run"` and `freshness: "unverified"` mean a cancelled path must never be
  read as a gate that ran.
- `dirty_state: "preserved"` means the unreconciled work is recorded, not discarded; the next
  run resumes from `dirty_scope` and re-verifies before applying the normal completion rules.
- Nothing is cleaned, reset, stashed or discarded on cancellation, and cancellation never widens
  authority (no apply, commit, push, config write or credential read).

For an agent this is the key distinction: **a cancel is not evidence of completion and not
evidence of task failure — it is evidence that work is still dirty and must be reconciled
later.**

---

## 5. Degraded operation: unverified, never silently "fresh"

`adapters/common/degraded_policy.json` declares an explicit mode per repository; the mode is never
inherited from another repository.

| Repository | Mode | On an unavailable graph |
|---|---|---|
| `axiom-skills` | `advisory` (`fail_open: true`) | `{"action": "advisory", "freshness": "unverified", "completion_gate": "not_claimed"}` |
| `axiom-specs` | `advisory` (`fail_open: true`) | same as above |
| `axiom-graphd` | `strict` (`fail_open: false`) | `{"action": "pending", "freshness": "unverified", "completion_gate": "not_claimed"}` |
| `axiom-mcp` | `strict` (`fail_open: false`) | same as `axiom-graphd` |
| unknown repository | `strict` (`fail_open: false`) | `{"action": "pending", "freshness": "unverified", "completion_gate": "not_claimed"}` |

The invariants in the same file are what keep a degraded path honest:
`fail_open_never_claims_fresh_freshness`, `fail_open_never_claims_a_completion_gate_ran`, and
`unknown_repo_is_not_fail_open`. `policy/POLICY.md` §6 adds the operator rule: report degraded
operation explicitly and name the unverified scope, fall back to direct source inspection, and
never silently continue as if the graph had been consulted or retry without bound.

`policy/POLICY.md` §3 also keeps freshness and coverage separate: a reconciliation timeout or an
unfinished job is `updating`/`unknown`, never `fresh`, and absence of an error is not evidence of
freshness.

---

## 6. How the layers cooperate in one turn

1. **Before reading source.** Follow `skills/graph-context/SKILL.md`: request an explicit,
   bounded projection and use returned source locations as the reading list; never load
   `.axiom/graph` as a directory or dump a catalog into context.
2. **At a coherent change boundary.** Follow `skills/graph-reconcile/SKILL.md`: request dirty-scope
   reconciliation, poll within a bounded deadline, and report `pending`/blocked when the deadline
   expires; `scope=full` needs explicit owner authorisation.
3. **At stop / after-turn.** The adapter hook runs the bounded runtime. Complete evidence →
   `allow`. Pending work → one bounded continuation per unchanged fingerprint, up to
   `MAX_FORCED_CONTINUATIONS = 2`, and only where the host actually supports that decision.
4. **On an interrupt or crash.** The cancellation contract preserves dirty state and claims no
   gate (section 4).
5. **Graph unavailable.** The degraded policy labels the result `unverified` and `not_claimed`
   (section 5).
6. **Claiming done.** Run the repository's real tests and record the task evidence. The graph is
   never a substitute for either (`policy/POLICY.md` §5 rule 6).

---

## 7. What is not guaranteed

These are explicitly **not** claimed by the shipped code. Do not rely on them:

- **No universal hard completion gate.** Axiom does not own the agent harness, so it cannot
  force every host to hold a turn open; CI and graph verification are independent gates
  (`25-HOST-ADAPTERS-AND-HOOKS.md` §4).
- **No certified host.** `adapters/compatibility.json` → `certification_summary` has
  `certified_adapters: 0`; every adapter is `instructions_only` and no feature status reaches
  `verified_on_installed_host`.
- **A timeout does not cancel the operation.** `_run_once()` abandons a daemon worker; it does
  not interrupt, kill or join it, and the operation may still be running after the hook answers.
  There is no thread-kill guarantee.
- **The runtime itself never blocks.** The pending path of `run_bounded()` (via
  `_pending_result()`) returns `action: "allow"`; blocking is a per-adapter decision and only
  happens where that host's hook implements it.
- **Only an explicit `False` capability degrades to advisory.** `supports_stop_decision()` returns
  `None` when the host reports no `capabilities` object, and the Claude/Antigravity adapters then
  proceed to the documented decision rather than treating "unreported" as "unsupported".
- **The Codex Stop adapter consults no capability flag.** It emits the block decision whenever a
  bounded reconcile is pending and the loop budget allows; it does not check a reported
  `stop_decision`.
- **Blocking is not a task verdict.** A `block`/`continue`/`retry` only asks the host for one more
  bounded attempt; it says nothing about whether the task's acceptance criteria passed.
- **A cancel is not a completion and does not roll anything back.** It preserves dirty state and
  claims no gate.
- **Hook state must be writable for the loop guard to persist.** If the state file is
  unavailable, the adapters allow the turn with a diagnostic instead of blocking.
- **Skills grant no authority.** `policy/POLICY.md` §4: no file, shell, network, Git, credential
  or host permission is widened, and an install/update/config write still needs an approved plan
  and an explicit human decision.
- **Untested hosts remain unverified.** `Development.md` requires a host that has not been tested
  to be recorded as unverified rather than certified.

---

## 8. How to verify this locally

From the `axiom-skills` checkout root, in PowerShell:

```powershell
python -m pytest tests -q
python release/verify_manifest.py
```

`pytest` runs the shipped behavioural suite (including the hook, runtime, degraded-policy,
cancellation and compatibility checks); `verify_manifest.py` re-hashes the committed bundle
bytes and fails on a missing file, a hash or byte-count mismatch, a duplicate declaration, or an
unknown file inside `policy`, `skills` or `adapters`.

To re-check this guide's own claims, run the slice test:

```powershell
python -m pytest tests/test_agent_workflow_guide.py -q
```

It asserts the guide exists, that every cited claim names a file and symbol that exist in the
repository, that the required timeout/block/cancel sections are present, and that a fixture
which asserts a universal completion gate (or omits the bounded behaviour) is rejected.

## 9. Citation index

| Claim | File | Symbol / section |
|---|---|---|
| Bounded budget and refusal of unbounded values | `adapters/common/hook_runtime.py` | `bounded_budget()`, `UnboundedBudgetError`, `HARD_MAX_RETRIES` |
| One attempt is time-boxed and abandoned | `adapters/common/hook_runtime.py` | `_run_once()` |
| Retry cap and pending evidence | `adapters/common/hook_runtime.py` | `run_bounded()`, `_pending_result()`, `FAILURE_KINDS` |
| Canonical actions and result fields | `adapters/common/hook_runtime.py` | `ACTIONS`, `RESULT_FIELDS`, `EVIDENCE_STATES` |
| Claude Stop decision and capability gate | `adapters/claude/hooks/graph_stop.py` | `canonical_decide()`, `supports_stop_decision()`, `NEVER_FORCED_STOP_REASONS`, `MAX_FORCED_CONTINUATIONS`, `to_host_output()` |
| Claude TaskCompleted scope | `adapters/claude/hooks/graph_task_completed.py` | `canonical_decide()`, `supports_completion_decision()` |
| Codex Stop decision | `adapters/codex/hooks/graph_stop.py` | `canonical_decide()`, `to_host_output()` |
| Gemini retry decision and budget | `adapters/gemini/hooks/graph_after_agent.py` | `canonical_decide()`, `retry_budget()`, `NEVER_RETRIED_REASONS`, `to_host_output()` |
| Antigravity continue decision | `adapters/antigravity/hooks/graph_stop.py` | `canonical_decide()`, `supports_stop_decision()`, `HOST_DECISIONS`, `to_host_output()` |
| Loop-guard key | `adapters/*/hooks/*.py` | `loop_key()` |
| Attempt state on disk | `adapters/*/hooks/*.py` | `load_attempts()`, `store_attempts()`, `STATE_ENV` |
| Cancellation contract and record | `adapters/common/cancellation.md` | `cancellation-v1`, sections 1–5 |
| Degraded modes and invariants | `adapters/common/degraded_policy.json` | `modes`, `repos[]`, `unknown_repo`, `invariants` |
| Certification limits | `adapters/compatibility.json` | `certification_summary`, `certification_rules`, `enforcement_levels` |
| Policy boundaries | `policy/POLICY.md` | §3, §4, §5, §6 |
| Skill guidance boundary | `skills/*/SKILL.md` | each skill's "workflow guidance" paragraph |
| No universal hard completion gate | `axiom-specs/repo-seeds/axiom-skills/docs/25-HOST-ADAPTERS-AND-HOOKS.md` | §4 |