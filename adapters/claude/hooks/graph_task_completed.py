#!/usr/bin/env python3
"""Claude Code `TaskCompleted` hook adapter for the Axiom graph workflow.

Host:  Claude Code
Event: TaskCompleted
Owner: `axiom-skills/adapters/claude/hooks`

Scope, stated plainly
---------------------
This adapter is limited to the documented task lifecycle. It fires when the host reports that
a *task* reached the completed state, and it may block that task transition while a bounded
graph reconcile is still pending. It is **not a universal response-completion hook**: an
ordinary assistant turn, a message, a tool result and a user interrupt are not task
completions, and this adapter does nothing at all for them. Only the documented `TaskCompleted`
event with a task identity is handled.

Input (stdin, JSON)
-------------------
  hook_event_name            MUST be the documented task-completion event
  task_id, task_subject      the task identity; without one nothing is enforced
  session_id                 loop-guard identity
  cwd                        working root
  stop_hook_active           honoured when the host supplies it
  axiom                      the bounded status report the CLI writes:
      schema_profile        must be a profile this adapter declares supported
      status                fresh | stale | unavailable
      dirty                 bool
      pending_jobs          int
      capabilities          {task_completed_decision: bool} for the installed version
      job_id, snapshot, freshness, coverage, retry_after_ms
      source_fingerprint, target_barrier

Output (stdout, JSON)
---------------------
  {"decision": "block", "reason": "..."}   block this task completion
  {}                                       no decision: allow the task to complete

Diagnostics go to stderr only. This hook never parses a conversation transcript, never reads
the model's own claim that a task is finished, and never invents a graph result.

Bounded behaviour
-----------------
* At most MAX_FORCED_CONTINUATIONS (= 2) blocks are emitted per unchanged loop-guard key.
* `stop_hook_active` is set for a host-driven continuation and is honoured when supplied.
* A malformed payload, a missing task identity, an unreadable or unwritable state file, an
  unavailable graph or an unrecognised schema profile degrades to `{}` plus a stderr
  diagnostic. The adapter never fabricates a block, and never turns a non-task event into a
  completion gate.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

HOST = "claude"
EVENT = "TaskCompleted"
MAX_FORCED_CONTINUATIONS = 2
SUPPORTED_SCHEMA_PROFILES = ("claude-task-completed-v1",)
ACTIONS = ("allow", "continue", "block", "advisory")
RESULT_FIELDS = (
    "action",
    "reason",
    "job_id",
    "snapshot",
    "freshness",
    "coverage",
    "retry_after_ms",
    "hook_attempt",
)
STATE_ENV = "AXIOM_HOOK_STATE_DIR"


def canonical_result(
    action,
    reason=None,
    *,
    job_id=None,
    snapshot=None,
    freshness=None,
    coverage=None,
    retry_after_ms=None,
    hook_attempt=0,
):
    """Build the canonical hook result shared by every Axiom host adapter."""
    if action not in ACTIONS:
        raise ValueError(f"unknown canonical action: {action}")
    return {
        "action": action,
        "reason": reason,
        "job_id": job_id,
        "snapshot": snapshot,
        "freshness": freshness,
        "coverage": coverage,
        "retry_after_ms": retry_after_ms,
        "hook_attempt": hook_attempt,
    }


def loop_key(payload):
    """(host, session or task, source fingerprint, target barrier) for one bounded loop."""
    session = (
        payload.get("session_id")
        or payload.get("task_id")
        or payload.get("task_subject")
        or "unknown-session"
    )
    report = payload.get("axiom")
    report = report if isinstance(report, dict) else {}
    fingerprint = report.get("source_fingerprint") or ""
    barrier = report.get("target_barrier") or "graph-fresh"
    return f"{HOST}|{session}|{fingerprint}|{barrier}"


def state_path(cwd, payload):
    override = os.environ.get(STATE_ENV)
    base = Path(override) if override else Path(cwd) / ".axiom" / "local" / "hook-state"
    digest = hashlib.sha256(loop_key(payload).encode("utf-8")).hexdigest()
    return base / f"{HOST}-task-completed-{digest}.json"


def load_attempts(path):
    """Return (attempts, problem). A problem is fail-safe: the caller must not block."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return 0, None
    except OSError as exc:
        return 0, f"hook state is unreadable ({exc.__class__.__name__}); allowing the task"
    try:
        obj = json.loads(raw)
        return int(obj["forced_continuations"]), None
    except (ValueError, TypeError, KeyError):
        return 0, "hook state is malformed; allowing the task"


def store_attempts(path, attempts, key):
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(
            json.dumps({"forced_continuations": attempts, "key": key}, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except OSError as exc:
        return f"hook state could not be written ({exc.__class__.__name__}); allowing the task"
    return None


def _bounded_reason(report, attempts):
    parts = ["the task's graph work is not reconciled yet"]
    if report.get("job_id"):
        parts.append(f"job {report['job_id']}")
    if report.get("freshness"):
        parts.append(f"freshness {report['freshness']}")
    if report.get("coverage"):
        parts.append(f"coverage {report['coverage']}")
    if report.get("retry_after_ms") is not None:
        parts.append(f"retry_after_ms {report['retry_after_ms']}")
    parts.append(f"forced continuation {attempts} of {MAX_FORCED_CONTINUATIONS}")
    return "; ".join(parts)


def supports_completion_decision(report):
    """True, False, or None when the installed host capability was not reported."""
    capabilities = report.get("capabilities")
    if not isinstance(capabilities, dict):
        return None
    value = capabilities.get("task_completed_decision")
    return value if isinstance(value, bool) else None


def canonical_decide(payload, *, cwd=None, path=None):
    """Return (canonical result, diagnostics) for one task-completion decision."""
    if not isinstance(payload, dict):
        return canonical_result("allow", "payload is not a JSON object"), [
            "payload is not a JSON object; allowing the task to complete"
        ]

    diagnostics = []
    event = payload.get("hook_event_name")
    if event != EVENT:
        return (
            canonical_result("allow", f"event {event} is outside the task lifecycle"),
            [
                f"hook event {event!r} is not the documented {EVENT} task lifecycle event; "
                "this adapter is not a universal response-completion hook, so it does nothing"
            ],
        )

    task_id = payload.get("task_id") or payload.get("task_subject")
    if not task_id:
        return (
            canonical_result("allow", "the task-completion event carries no task identity"),
            [
                "the task-completion event carries no task identity; refusing to enforce a "
                "completion gate without one"
            ],
        )

    if payload.get("stop_hook_active") is True:
        return (
            canonical_result("allow", "reentrance flag is set"),
            [
                "the host reentrance flag is set: a continuation was already requested, "
                "allowing the task transition to prevent unbounded recursion"
            ],
        )

    report = payload.get("axiom")
    if not isinstance(report, dict):
        return (
            canonical_result("allow", "no bounded graph status was reported"),
            [
                "no bounded graph status was reported; allowing the task instead of "
                "assuming that work is pending"
            ],
        )

    profile = report.get("schema_profile")
    if profile not in SUPPORTED_SCHEMA_PROFILES:
        return (
            canonical_result("allow", f"unsupported schema profile {profile}"),
            [
                f"unrecognised schema profile {profile!r}; refusing to emit an assumed "
                "block payload"
            ],
        )

    if str(report.get("status") or "").strip().lower() == "unavailable":
        return (
            canonical_result("advisory", "graph status is unavailable"),
            ["graph status is unavailable; degraded to advisory without blocking"],
        )

    pending = report.get("pending_jobs")
    has_pending = isinstance(pending, int) and not isinstance(pending, bool) and pending > 0
    if report.get("dirty") is not True and not has_pending:
        return (
            canonical_result("allow", "no pending graph work was reported"),
            ["no pending graph work was reported; allowing the task to complete"],
        )

    capability = supports_completion_decision(report)
    if capability is False:
        return (
            canonical_result("advisory", "this host does not support a completion decision"),
            [
                "the installed host reports no task-completion decision capability, so the "
                "pending reconcile is advisory here and does not block"
            ],
        )

    key = loop_key(payload)
    attempts, problem = load_attempts(path if path is not None else state_path(cwd or ".", payload))
    if problem:
        return canonical_result("allow", "hook loop state is unavailable"), [problem]

    attempts += 1
    context = {
        "job_id": report.get("job_id"),
        "snapshot": report.get("snapshot"),
        "freshness": report.get("freshness"),
        "coverage": report.get("coverage"),
        "retry_after_ms": report.get("retry_after_ms"),
    }

    if attempts > MAX_FORCED_CONTINUATIONS:
        diagnostics.append(
            f"loop guard: {attempts - 1} forced continuations for one unchanged fingerprint "
            f"reached the maximum of {MAX_FORCED_CONTINUATIONS}; surfacing the blocked "
            f"reason and allowing the task: {_bounded_reason(report, MAX_FORCED_CONTINUATIONS)}"
        )
        return canonical_result("allow", "forced continuation budget is exhausted"), diagnostics

    problem = store_attempts(
        path if path is not None else state_path(cwd or ".", payload), attempts, key
    )
    if problem:
        return canonical_result("allow", "hook loop state could not be recorded"), [problem]

    return (
        canonical_result(
            "block",
            _bounded_reason(report, attempts),
            hook_attempt=attempts,
            **context,
        ),
        diagnostics,
    )


def to_host_output(canonical):
    """Map the canonical result to the documented Claude Code TaskCompleted output schema."""
    if canonical.get("action") == "block":
        return {"decision": "block", "reason": canonical.get("reason") or "task graph work pending"}
    return {}


def main(argv=None, stdin=None, stderr=None):
    stderr = stderr if stderr is not None else sys.stderr
    raw = (stdin if stdin is not None else sys.stdin).read()
    payload = None
    diagnostics = []
    if not raw.strip():
        diagnostics.append("empty hook payload; allowing the task to complete")
    else:
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            diagnostics.append(
                f"malformed hook payload ({exc.__class__.__name__}); allowing the task"
            )

    if payload is None:
        canonical = canonical_result("allow", "no usable payload")
    else:
        cwd = payload.get("cwd") or os.getcwd()
        canonical, extra = canonical_decide(payload, cwd=cwd)
        diagnostics.extend(extra)

    for line in diagnostics:
        print(f"[axiom graph_task_completed] {line}", file=stderr)
    print(json.dumps(to_host_output(canonical)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
