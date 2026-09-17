#!/usr/bin/env python3
"""Codex CLI `Stop` hook adapter for the Axiom graph workflow.

Host:  Codex CLI
Event: Stop
Owner: `axiom-skills/adapters/codex/hooks`

What this hook is
-----------------
This is a stop *decision* hook. It may ask the host to continue a turn once more so that a
bounded graph reconcile can finish. It never claims that the task's work, tests or evidence
are complete: stop continuation is not task-state completion.

Input (stdin, JSON)
-------------------
The host's documented stop-hook payload. Fields this adapter reads:

  session_id, thread_id, turn_id   loop-guard identity
  cwd                              working root
  hook_event_name                  the event this adapter handles
  stop_hook_active                 the host reentrance flag
  stop_reason, reason              user_interrupt / error stops are never forced
  axiom                            the bounded status report the CLI writes:
      schema_profile        must be a profile this adapter declares supported
      status                fresh | stale | unavailable
      dirty                 bool
      pending_jobs          int
      job_id, snapshot, freshness, coverage, retry_after_ms
      source_fingerprint, target_barrier

An absent or unrecognised status is treated as *unknown*, which allows the stop. This hook
never probes the daemon, never parses a conversation transcript and never invents a graph
result.

Output (stdout, JSON)
---------------------
  {"decision": "block", "reason": "..."}   ask the host to continue the turn
  {}                                       no decision: allow the stop

Diagnostics go to stderr only, so the host's structured channel stays clean.

Bounded behaviour
-----------------
* `stop_hook_active` true means a continuation was already requested by a stop hook, so the
  adapter never blocks again. That is what prevents unbounded recursive stopping.
* At most MAX_FORCED_CONTINUATIONS (= 2) blocks are emitted per unchanged loop-guard key.
  After that the adapter surfaces the blocked reason and stops forcing continuation.
* A user interrupt or a host error is never force-continued.
* A malformed payload, an unreadable or unwritable state file, an unavailable graph or an
  unrecognised schema profile degrades to `{}` plus a stderr diagnostic. The adapter never
  fabricates a block it cannot justify.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

HOST = "codex"
EVENT = "Stop"
MAX_FORCED_CONTINUATIONS = 2
SUPPORTED_SCHEMA_PROFILES = ("codex-stop-v1",)
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
NEVER_FORCED_STOP_REASONS = (
    "user_interrupt",
    "interrupt",
    "cancel",
    "cancelled",
    "abort",
    "aborted",
    "error",
    "error_stop",
    "timeout",
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
    """(host, session, source fingerprint, target barrier) for one bounded loop.

    An absent fingerprint intentionally collapses to one key per session, which is the
    conservative choice: the counter then bounds the whole session instead of resetting.
    """
    session = (
        payload.get("session_id")
        or payload.get("thread_id")
        or payload.get("turn_id")
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
    return base / f"{HOST}-{EVENT.lower()}-{digest}.json"


def load_attempts(path):
    """Return (attempts, problem). A problem is fail-safe: the caller must not block."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return 0, None
    except OSError as exc:
        return 0, f"hook state is unreadable ({exc.__class__.__name__}); allowing the stop"
    try:
        obj = json.loads(raw)
        return int(obj["forced_continuations"]), None
    except (ValueError, TypeError, KeyError):
        return 0, "hook state is malformed; allowing the stop"


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
        return f"hook state could not be written ({exc.__class__.__name__}); allowing the stop"
    return None


def _bounded_reason(report, attempts):
    parts = ["the graph still has unindexed work"]
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


def canonical_decide(payload, *, cwd=None, path=None):
    """Return (canonical result, diagnostics) for one stop decision."""
    if not isinstance(payload, dict):
        return canonical_result("allow", "payload is not a JSON object"), [
            "payload is not a JSON object; allowing the stop"
        ]

    diagnostics = []
    event = payload.get("hook_event_name")
    if event and event != EVENT:
        return canonical_result("allow", f"unexpected event {event}"), [
            f"unexpected hook event {event!r}; this adapter only handles {EVENT}"
        ]

    if payload.get("stop_hook_active") is True:
        return (
            canonical_result(
                "allow",
                "stop_hook_active is set after a requested continuation",
            ),
            [
                "stop_hook_active is set: a continuation was already requested, "
                "allowing the stop to prevent unbounded recursive stopping"
            ],
        )

    stop_reason = str(payload.get("stop_reason") or payload.get("reason") or "")
    stop_reason = stop_reason.strip().lower()
    if stop_reason in NEVER_FORCED_STOP_REASONS:
        return canonical_result("allow", f"stop reason {stop_reason} is never forced"), [
            f"stop reason {stop_reason!r} is never force-continued"
        ]

    report = payload.get("axiom")
    if not isinstance(report, dict):
        return (
            canonical_result("allow", "no bounded graph status was reported"),
            [
                "no bounded graph status was reported; allowing the stop instead of "
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
            ["no pending graph work was reported; allowing the stop"],
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
            f"reason and stopping: {_bounded_reason(report, MAX_FORCED_CONTINUATIONS)}"
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
    """Map the canonical result to the documented Codex Stop hook output schema."""
    if canonical.get("action") == "block":
        return {"decision": "block", "reason": canonical.get("reason") or "graph reconcile pending"}
    return {}


def main(argv=None, stdin=None, stderr=None):
    stderr = stderr if stderr is not None else sys.stderr
    raw = (stdin if stdin is not None else sys.stdin).read()
    payload = None
    diagnostics = []
    if not raw.strip():
        diagnostics.append("empty hook payload; allowing the stop")
    else:
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            diagnostics.append(
                f"malformed hook payload ({exc.__class__.__name__}); allowing the stop"
            )

    if payload is None:
        canonical = canonical_result("allow", "no usable payload")
    else:
        cwd = payload.get("cwd") or os.getcwd()
        canonical, extra = canonical_decide(payload, cwd=cwd)
        diagnostics.extend(extra)

    for line in diagnostics:
        print(f"[axiom graph_stop] {line}", file=stderr)
    print(json.dumps(to_host_output(canonical)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
