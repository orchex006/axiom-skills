#!/usr/bin/env python3
"""Antigravity (AGY) `Stop` hook adapter for the Axiom graph workflow.

Host:  Antigravity (AGY)
Event: Stop
Owner: `axiom-skills/adapters/antigravity/hooks`

What this hook is
-----------------
This is a stop *decision* hook. It may ask the host to continue a turn once more so that a
bounded graph reconcile can finish. It never claims that the turn's work, tests or evidence
are complete: stop-style continuation is not task-state completion.

Documented continue/reason semantics are the host's
---------------------------------------------------
The pinned `antigravity-stop-v1` profile documents this host's Stop decision as `continue`
with the reason carried alongside it. The Claude payload shape
`{"decision": "block", "reason": ...}` is therefore not reused blindly here: `block` is only
used where the pinned version documents it, and the adapter otherwise reports `advisory`.
One host's decision payload is never copied into another host's schema.

Input (stdin, JSON)
-------------------
Fields this adapter reads:

  session_id                  loop-guard identity
  cwd                         working root
  hook_event_name             the event this adapter handles
  stop_hook_active            the host's reentrance flag
  stop_reason, reason         a user interrupt or host error is never forced
  axiom                       the bounded status report the CLI writes:
      schema_profile        must be a profile this adapter declares supported
      status                fresh | stale | unavailable
      dirty                 bool
      pending_jobs          int
      capabilities          {stop_decision: bool} for the installed host version
      job_id, snapshot, freshness, coverage, retry_after_ms
      source_fingerprint, target_barrier

An absent or unrecognised status is treated as *unknown*, which allows the stop. This hook
never parses a conversation transcript and never invents a graph result.

Output (stdout, JSON)
---------------------
  {"decision": "continue", "reason": "..."}   ask the host to continue the turn
  {}                                          no decision: allow the stop

Diagnostics go to stderr only, so the host's structured channel stays clean.

Bounded behaviour
-----------------
* `stop_hook_active` true means a continuation was already requested, so the adapter never
  asks for another one: stop_hook_active is set, and no further continuation is forced.
* At most MAX_FORCED_CONTINUATIONS (= 2) continue decisions are emitted per unchanged
  loop-guard key.
* A bounded reconcile failure is surfaced only where the installed host actually supports a
  stop decision. When the reported capability is explicitly absent, the adapter reports
  `advisory` and allows the stop rather than claiming a gate it cannot enforce.
* A malformed payload, an unreadable or unwritable state file, an unavailable graph or an
  unrecognised schema profile degrades to `{}` plus a stderr diagnostic.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

HOST = "antigravity"
EVENT = "Stop"
MAX_FORCED_CONTINUATIONS = 2
SUPPORTED_SCHEMA_PROFILES = ("antigravity-stop-v1",)
HOST_DECISIONS = ("continue",)
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
    "shutdown",
    "shutdown_stop",
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


def supports_stop_decision(report):
    """The host's documented Stop decision is opt-in: absent capability is not trusted."""
    capabilities = report.get("capabilities")
    if not isinstance(capabilities, dict):
        return None
    value = capabilities.get("stop_decision")
    return value if isinstance(value, bool) else None


def loop_key(payload):
    """(host, session, source fingerprint, target barrier) for one bounded loop."""
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
    parts.append(f"continuation {attempts} of {MAX_FORCED_CONTINUATIONS}")
    return "; ".join(parts)


def canonical_decide(payload, cwd=None, path=None):
    """Map the host payload to (canonical result, stderr diagnostics)."""
    diagnostics = []

    event = payload.get("hook_event_name")
    if event is not None and event != EVENT:
        return (
            canonical_result("allow", f"unexpected event {event}"),
            [f"unexpected hook event {event!r}; this adapter only handles {EVENT}"],
        )

    if payload.get("stop_hook_active") is True:
        return (
            canonical_result(
                "allow",
                "stop_hook_active is set after a requested continuation",
            ),
            [
                "stop_hook_active is set: a continuation was already requested, so the "
                "adapter allows the stop to prevent unbounded recursive stopping"
            ],
        )

    stop_reason = str(payload.get("stop_reason") or payload.get("reason") or "")
    stop_reason = stop_reason.strip().lower()
    if stop_reason in NEVER_FORCED_STOP_REASONS:
        return canonical_result("allow", f"stop reason {stop_reason} is never forced"), [
            f"stop reason {stop_reason!r} is never force-continued; only the documented Stop "
            "event is handled"
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
                "continue payload"
            ],
        )

    if str(report.get("status") or "").strip().lower() == "unavailable":
        return (
            canonical_result("advisory", "graph status is unavailable"),
            ["graph status is unavailable; degraded to advisory without continuing"],
        )

    pending = report.get("pending_jobs")
    has_pending = isinstance(pending, int) and not isinstance(pending, bool) and pending > 0
    if report.get("dirty") is not True and not has_pending:
        return (
            canonical_result("allow", "no pending graph work was reported"),
            ["no pending graph work was reported; allowing the stop"],
        )

    if supports_stop_decision(report) is False:
        return (
            canonical_result("advisory", "this host does not support a stop decision"),
            [
                "the installed host does not support a stop decision, so a bounded "
                "reconcile failure is advisory here and does not continue the turn"
            ],
        )

    key = loop_key(payload)
    attempts, problem = load_attempts(
        path if path is not None else state_path(cwd or ".", payload)
    )
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
    """Map the canonical result to the host's documented `continue` decision schema.

    The canonical `block` action means "do not accept the stop yet". On this host that is
    expressed as the documented `continue` decision, never as another host's block payload.
    """
    if canonical.get("action") == "block":
        return {
            "decision": "continue",
            "reason": canonical.get("reason") or "graph reconcile pending",
        }
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