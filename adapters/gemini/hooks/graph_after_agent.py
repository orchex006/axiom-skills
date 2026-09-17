#!/usr/bin/env python3
"""Gemini CLI `AfterAgent` hook adapter for the Axiom graph workflow.

Host:  Gemini CLI
Event: AfterAgent
Owner: `axiom-skills/adapters/gemini/hooks`

What this hook is
-----------------
This is a bounded after-turn decision hook. It may ask the host to retry the turn's graph
reconcile once more, and it never claims that the turn's work, tests or evidence are complete.

Retry and halt semantics are the host's own
-------------------------------------------
The pinned `gemini-after-agent-v1` profile documents a strict-JSON response with a bounded
`retry` decision and the host's own halt condition. It is not the Claude exit convention and
it is not the other host's `{"decision": "block", "reason": ...}` payload shape, so that
payload is not reused blindly here. The adapter emits the host's documented retry decision
while a bounded retry is still allowed, and otherwise halts the retry loop and surfaces the
blocked reason instead of asking for one more unbounded retry.

The effective bound is the smaller of the host-reported retry budget (when the profile
carries one) and MAX_FORCED_CONTINUATIONS (= 2), which is the same bound the other adapters
use for one unchanged loop-guard key.

Strict stdout
-------------
The host parses stdout as one JSON object. Every diagnostic and every log line therefore goes
to stderr, and stdout carries exactly one strict JSON document and nothing else, so a log
line cannot corrupt the hook response.

Input (stdin, JSON)
-------------------
Fields this adapter reads:

  session_id, turn_id            loop-guard identity
  cwd                            working root
  hook_event_name                the event this adapter handles
  stop_hook_active               the host's reentrance flag, honoured when supplied
  reason, stop_reason            a user interrupt, shutdown or host error is never retried
  axiom                          the bounded status report the CLI writes:
      schema_profile             must be the profile this adapter declares supported
      status                     fresh | stale | unavailable
      dirty, pending_jobs        the pending work this hook may act on
      retry_remaining            the host's documented retry budget, when it has one
      job_id, snapshot, freshness, coverage, retry_after_ms
      source_fingerprint, target_barrier

An absent or unrecognised status is treated as unknown, which ends the turn. This hook never
parses a conversation transcript and never invents a graph result.

Output (stdout, JSON)
---------------------
  {"decision": "retry", "reason": "..."}    ask the host for a bounded retry
  {}                                        no decision: halt, end the turn

Bounded behaviour
-----------------
* `stop_hook_active` true means a retry was already requested, so the adapter never asks for
  another one: stop_hook_active is set, and no further retry is forced.
* At most MAX_FORCED_CONTINUATIONS (= 2) retry decisions are emitted per unchanged loop-guard
  key, and never more than the host-reported retry budget.
* A user interrupt, a shutdown or a host error is never retried.
* A malformed payload, an unreadable or unwritable state file, an unavailable graph or an
  unrecognised schema profile degrades to `{}` plus a stderr diagnostic.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

HOST = "gemini"
EVENT = "AfterAgent"
MAX_FORCED_CONTINUATIONS = 2
SUPPORTED_SCHEMA_PROFILES = ("gemini-after-agent-v1",)
HOST_DECISIONS = ("retry", "halt")
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
NEVER_RETRIED_REASONS = (
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


def loop_key(payload):
    """(host, session, source fingerprint, target barrier) for one bounded retry loop."""
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
    """Return (attempts, problem). A problem is fail-safe: the caller must not retry."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return 0, None
    except OSError as exc:
        return 0, f"hook state is unreadable ({exc.__class__.__name__}); ending the turn"
    try:
        obj = json.loads(raw)
        return int(obj["forced_continuations"]), None
    except (ValueError, TypeError, KeyError):
        return 0, "hook state is malformed; ending the turn"


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
        return f"hook state could not be written ({exc.__class__.__name__}); ending the turn"
    return None


def retry_budget(report):
    """The smaller of the host-reported retry budget and the documented adapter cap.

    An absent or non-integer budget is not treated as unlimited: it collapses to the
    documented cap, so a host that reports nothing cannot widen the bound.
    """
    reported = report.get("retry_remaining")
    if isinstance(reported, int) and not isinstance(reported, bool):
        return max(0, min(reported, MAX_FORCED_CONTINUATIONS))
    return MAX_FORCED_CONTINUATIONS


def _bounded_reason(report, attempts, budget):
    parts = ["the graph still has unindexed work"]
    if report.get("job_id"):
        parts.append(f"job {report['job_id']}")
    if report.get("freshness"):
        parts.append(f"freshness {report['freshness']}")
    if report.get("coverage"):
        parts.append(f"coverage {report['coverage']}")
    if report.get("retry_after_ms") is not None:
        parts.append(f"retry_after_ms {report['retry_after_ms']}")
    parts.append(f"bounded retry {attempts} of {budget}")
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
            canonical_result("allow", "stop_hook_active is set after a requested retry"),
            [
                "stop_hook_active is set: a retry was already requested, so the retry loop "
                "is halted to prevent unbounded recursion"
            ],
        )

    stop_reason = str(payload.get("stop_reason") or payload.get("reason") or "")
    stop_reason = stop_reason.strip().lower()
    if stop_reason in NEVER_RETRIED_REASONS:
        return canonical_result("allow", f"reason {stop_reason} is never retried"), [
            f"turn reason {stop_reason!r} is never force-retried; the turn is left alone"
        ]

    report = payload.get("axiom")
    if not isinstance(report, dict):
        return (
            canonical_result("allow", "no bounded graph status was reported"),
            ["no bounded graph status was reported; ending the turn instead of assuming "
             "that work is pending"],
        )

    profile = report.get("schema_profile")
    if profile not in SUPPORTED_SCHEMA_PROFILES:
        return (
            canonical_result("allow", f"unsupported schema profile {profile}"),
            [f"unrecognised schema profile {profile!r}; refusing to emit an assumed retry "
             "payload"],
        )

    if str(report.get("status") or "").strip().lower() == "unavailable":
        return (
            canonical_result("advisory", "graph status is unavailable"),
            ["graph status is unavailable; degraded to advisory without retrying"],
        )

    pending = report.get("pending_jobs")
    has_pending = isinstance(pending, int) and not isinstance(pending, bool) and pending > 0
    if report.get("dirty") is not True and not has_pending:
        return (
            canonical_result("allow", "no pending graph work was reported"),
            ["no pending graph work was reported; ending the turn"],
        )

    budget = retry_budget(report)
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

    if attempts > budget:
        diagnostics.append(
            f"loop guard: {attempts - 1} bounded retries for one unchanged fingerprint "
            f"reached the budget of {budget} (adapter cap {MAX_FORCED_CONTINUATIONS}); "
            f"halting the retry loop and surfacing the blocked reason: "
            f"{_bounded_reason(report, budget, budget)}"
        )
        return canonical_result("allow", "retry budget is exhausted"), diagnostics

    problem = store_attempts(
        path if path is not None else state_path(cwd or ".", payload), attempts, key
    )
    if problem:
        return canonical_result("allow", "hook loop state could not be recorded"), [problem]

    return (
        canonical_result(
            "block",
            _bounded_reason(report, attempts, budget),
            hook_attempt=attempts,
            **context,
        ),
        diagnostics,
    )


def to_host_output(canonical):
    """Map the canonical result to the documented Gemini `AfterAgent` response schema."""
    if canonical.get("action") == "block":
        payload = {
            "decision": "retry",
            "reason": canonical.get("reason") or "graph reconcile pending",
        }
        if canonical.get("retry_after_ms") is not None:
            payload["retry_after_ms"] = canonical["retry_after_ms"]
        return payload
    return {}


def main(argv=None, stdin=None, stderr=None):
    stderr = stderr if stderr is not None else sys.stderr
    raw = (stdin if stdin is not None else sys.stdin).read()
    payload = None
    diagnostics = []
    if not raw.strip():
        diagnostics.append("empty hook payload; ending the turn")
    else:
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            diagnostics.append(
                f"malformed hook payload ({exc.__class__.__name__}); ending the turn"
            )

    if payload is None:
        canonical = canonical_result("allow", "no usable payload")
    else:
        cwd = payload.get("cwd") or os.getcwd()
        canonical, extra = canonical_decide(payload, cwd=cwd)
        diagnostics.extend(extra)

    for line in diagnostics:
        print(f"[axiom graph_after_agent] {line}", file=stderr)
    print(json.dumps(to_host_output(canonical)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())