#!/usr/bin/env python3
"""Bounded hook runtime shared by the Axiom completion-hook adapters.

Owner: `axiom-skills/adapters/common`

What this module is
-------------------
Every Axiom completion hook asks a graph service for a bounded amount of work and then has to
answer the host *even when that service never answers*. This module is the shared, testable
half of that promise: it runs one operation under a wall-clock budget, returns pending
evidence instead of blocking, and caps retries so a hook can never hang completion forever.

The canonical hook result
-------------------------
The result keeps the canonical vocabulary every adapter already publishes: `action`
(`allow` | `continue` | `block` | `advisory`), `reason`, `job_id`, `snapshot`, `freshness`,
`coverage`, `retry_after_ms` and `hook_attempt`. A bounded run adds the runtime evidence
fields: `evidence` (`complete` | `pending`), `failure` (`timeout` | `crashed` |
`retry_cap`), `pending`, `retries_left`, `hook_attempt` (the attempt that produced the
answer) and `elapsed_ms`.

Bounding rules
--------------
* One attempt is capped at `timeout_ms`, so a hung daemon call cannot hold the hook open.
  The operation runs in a daemon worker thread; when the budget expires the worker is
  abandoned and the hook answers anyway. That is what makes a daemon crash or a dead socket
  unable to hang completion indefinitely.
* At most `max_retries` retries follow the first attempt, and `max_retries` is capped by
  HARD_MAX_RETRIES (= 2), the same two-continuation bound the host hooks use for one
  unchanged loop-guard key. When the retries are spent the caller gets pending evidence
  whose reason carries the blocked/`retry_cap` status, and no further attempt is made.
* A crash is data, not an exception: an operation that raises is recorded as `crashed`
  pending evidence and never propagates into the host's structured channel.
* An unbounded budget (a non-positive timeout, a negative retry count, or a retry count above
  HARD_MAX_RETRIES) is refused by `bounded_budget` instead of being silently clamped, so a
  caller cannot configure a hook that never returns.

This module performs no I/O of its own: it never probes a daemon, never parses a conversation
transcript, never invents a graph result and never writes to stdout.
"""
from __future__ import annotations

import threading
import time

DEFAULT_TIMEOUT_MS = 2000
DEFAULT_MAX_RETRIES = 2
HARD_MAX_RETRIES = 2
DEFAULT_RETRY_AFTER_MS = 250
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
EVIDENCE_STATES = ("complete", "pending")
FAILURE_KINDS = ("timeout", "crashed", "retry_cap")


class UnboundedBudgetError(ValueError):
    """A budget that could hang completion was refused instead of quietly clamped."""


def bounded_budget(timeout_ms=DEFAULT_TIMEOUT_MS, max_retries=DEFAULT_MAX_RETRIES):
    """Validate one budget, or refuse it loudly.

    A budget is bounded only when the timeout is a positive integer and the retry count is an
    integer between zero and HARD_MAX_RETRIES. Anything else is refused, so a misconfigured
    runtime cannot become an unbounded wait.
    """
    if type(timeout_ms) is not int or timeout_ms <= 0:
        raise UnboundedBudgetError(
            f"timeout_ms must be a positive integer, not {timeout_ms!r}"
        )
    if type(max_retries) is not int or max_retries < 0:
        raise UnboundedBudgetError(
            f"max_retries must be a non-negative integer, not {max_retries!r}"
        )
    if max_retries > HARD_MAX_RETRIES:
        raise UnboundedBudgetError(
            f"max_retries {max_retries} exceeds the documented cap {HARD_MAX_RETRIES}"
        )
    return {"timeout_ms": timeout_ms, "max_retries": max_retries}


def _run_once(operation, timeout_ms):
    """Run one attempt in an abandonable daemon thread.

    Returns (result, failure) where failure is None on success, `timeout` when the worker was
    still running at the deadline, or `crashed` when it raised. A crash in the worker is
    captured here so it can never reach the host's structured channel.
    """
    holder = {}
    finished = threading.Event()

    def worker():
        try:
            holder["result"] = operation()
        except BaseException as exc:  # a crash is evidence, not a propagated error
            holder["crash"] = f"{exc.__class__.__name__}: {exc}"
        finally:
            finished.set()

    thread = threading.Thread(target=worker, name="axiom-hook-budget", daemon=True)
    thread.start()
    if not finished.wait(timeout_ms / 1000.0):
        return None, "timeout"
    if "crash" in holder:
        return None, "crashed"
    return holder.get("result"), None


def _blank_result():
    """The canonical result fields every adapter publishes, with no evidence yet."""
    return {
        "action": "allow",
        "reason": None,
        "job_id": None,
        "snapshot": None,
        "freshness": None,
        "coverage": None,
        "retry_after_ms": None,
        "hook_attempt": 0,
    }


def _pending_result(reason, failure, attempts, budget, elapsed_ms,
                    detail=None, retry_after_ms=DEFAULT_RETRY_AFTER_MS):
    result = _blank_result()
    result.update(
        {
            "action": "allow",
            "reason": reason,
            "evidence": "pending",
            "failure": failure,
            "pending": True,
            "retries_left": 0,
            "hook_attempt": attempts,
            "attempts": attempts,
            "retry_after_ms": retry_after_ms,
            "elapsed_ms": elapsed_ms,
            "max_retries": budget["max_retries"],
            "timeout_ms": budget["timeout_ms"],
            "detail": detail,
        }
    )
    return result


def run_bounded(
    operation,
    *,
    timeout_ms=DEFAULT_TIMEOUT_MS,
    max_retries=DEFAULT_MAX_RETRIES,
    retry_after_ms=DEFAULT_RETRY_AFTER_MS,
    on_attempt=None,
):
    """Run `operation` under a bounded budget and always return a canonical result.

    The operation is retried at most `max_retries` times. A success is returned as
    `evidence == "complete"`; an exhausted budget, a timeout or a daemon crash is returned as
    pending evidence naming the failure, and the caller is never left waiting.
    """
    budget = bounded_budget(timeout_ms, max_retries)
    started = time.monotonic()
    attempts = 0
    last_failure = "timeout"
    last_detail = None

    for attempt in range(1, budget["max_retries"] + 2):
        attempts = attempt
        result, failure = _run_once(operation, budget["timeout_ms"])
        if on_attempt is not None:
            on_attempt(attempt, result, failure)
        if failure is None:
            elapsed_ms = int(round((time.monotonic() - started) * 1000))
            outcome = _blank_result()
            if isinstance(result, dict):
                for field in RESULT_FIELDS:
                    if field in result:
                        outcome[field] = result[field]
            outcome.update(
                {
                    "action": result.get("action") if isinstance(result, dict)
                    and result.get("action") in ACTIONS else "allow",
                    "reason": result.get("reason") if isinstance(result, dict)
                    and result.get("reason") else "the bounded operation completed",
                    "evidence": "complete",
                    "failure": None,
                    "pending": False,
                    "retries_left": budget["max_retries"] - (attempt - 1),
                    "hook_attempt": attempt,
                    "attempts": attempt,
                    "retry_after_ms": retry_after_ms,
                    "elapsed_ms": elapsed_ms,
                    "max_retries": budget["max_retries"],
                    "timeout_ms": budget["timeout_ms"],
                }
            )
            return outcome
        last_failure = failure
        last_detail = (
            f"attempt {attempt} of {budget['max_retries'] + 1} did not finish"
            if failure == "timeout"
            else f"attempt {attempt} of {budget['max_retries'] + 1} raised in the worker"
        )

    elapsed_ms = int(round((time.monotonic() - started) * 1000))
    kind = "retry_cap" if attempts > 1 else last_failure
    reason = (
        f"bounded hook runtime returned pending evidence after {attempts} attempt(s): "
        f"{kind}; the daemon call did not complete inside the "
        f"{budget['timeout_ms']} ms budget and the retry cap "
        f"{budget['max_retries']} was reached, so completion is not blocked further"
    )
    return _pending_result(
        reason, kind, attempts, budget, elapsed_ms, detail=last_detail,
        retry_after_ms=retry_after_ms,
    )