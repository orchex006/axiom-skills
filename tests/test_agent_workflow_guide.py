"""D-010 - regression tests for the agent workflow guide slice.

The slice deliverable is `docs/guides/agent-workflow.md`. A workflow guide is only useful if
its runtime claims are grounded in shipped bytes, so these tests treat the guide as a checked
artifact rather than prose:

* every cited file+symbol must resolve to code that actually exists;
* the required timeout / block / cancel / no-universal-gate sections must be present;
* the documented timeout numbers must match `adapters/common/hook_runtime.py`;
* the documented pending behaviour must match what the runtime really returns;
* negative and boundary variants of the guide are rejected by the same checker.

The fixtures for the negative/boundary cases are the mutated guide texts below; copies are
preserved under `evidence/artifacts/D-010/fixtures/` in `axiom-specs`.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import time
import unittest
from pathlib import Path

# Never leave bytecode inside a declared bundle scope: a stray .pyc under policy/, skills/ or
# adapters/ fails the shipped reference manifest verifier.
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
GUIDE = "docs/guides/agent-workflow.md"
RUNTIME = "adapters/common/hook_runtime.py"

REQUIRED_SECTIONS = (
    "timeout behaviour",
    "block behaviour",
    "cancel",
    "what is not guaranteed",
)

# (path, probe): the probe must appear in BOTH the guide and the cited file. This is what keeps
# a citation honest: a rename on either side fails the test instead of silently drifting.
CLAIMS: tuple[tuple[str, str], ...] = (
    (RUNTIME, "bounded_budget"),
    (RUNTIME, "UnboundedBudgetError"),
    (RUNTIME, "HARD_MAX_RETRIES"),
    (RUNTIME, "_run_once"),
    (RUNTIME, "run_bounded"),
    (RUNTIME, "_pending_result"),
    (RUNTIME, "FAILURE_KINDS"),
    (RUNTIME, "EVIDENCE_STATES"),
    (RUNTIME, "ACTIONS"),
    ("adapters/claude/hooks/graph_stop.py", "canonical_decide"),
    ("adapters/claude/hooks/graph_stop.py", "supports_stop_decision"),
    ("adapters/claude/hooks/graph_stop.py", "NEVER_FORCED_STOP_REASONS"),
    ("adapters/claude/hooks/graph_stop.py", "MAX_FORCED_CONTINUATIONS"),
    ("adapters/claude/hooks/graph_stop.py", "to_host_output"),
    ("adapters/claude/hooks/graph_stop.py", "loop_key"),
    ("adapters/claude/hooks/graph_stop.py", "load_attempts"),
    ("adapters/claude/hooks/graph_stop.py", "store_attempts"),
    ("adapters/claude/hooks/graph_task_completed.py", "supports_completion_decision"),
    ("adapters/codex/hooks/graph_stop.py", "to_host_output"),
    ("adapters/gemini/hooks/graph_after_agent.py", "retry_budget"),
    ("adapters/gemini/hooks/graph_after_agent.py", "NEVER_RETRIED_REASONS"),
    ("adapters/antigravity/hooks/graph_stop.py", "HOST_DECISIONS"),
    ("adapters/common/cancellation.md", "cancellation-v1"),
    ("adapters/common/cancellation.md", 'completion_gate: "not_run"'),
    ("adapters/common/degraded_policy.json", "unknown_repo_is_not_fail_open"),
    ("adapters/common/degraded_policy.json", "fail_open_never_claims_a_completion_gate_ran"),
    ("adapters/compatibility.json", "certified_adapters"),
    ("adapters/compatibility.json", "enforcement_level_must_not_exceed_evidence"),
    (
        "adapters/compatibility.json",
        "in_repository_unit_test_is_not_host_certification",
    ),
    ("policy/POLICY.md", "No new permissions"),
    ("policy/POLICY.md", "Degraded operation"),
)

# Behaviour the shipped code does not implement. A guide that asserts any of these is wrong and
# must be rejected, because it would let an agent trust a gate that cannot exist.
FORBIDDEN_CLAIMS = (
    r"guarantees a universal",
    r"universal(?: hard)? completion gate is guaranteed",
    r"always blocks every turn",
    r"terminates the worker thread",
    r"kills the worker thread",
    r"every host is certified",
)


def flatten(text: str) -> str:
    return " ".join(text.split()).lower()


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def guide_problems(text: str, root: Path) -> list[str]:
    """Return every reason the guide cannot be trusted; an empty list means it is grounded."""
    problems: list[str] = []
    flat = flatten(text)
    for section in REQUIRED_SECTIONS:
        if section not in flat:
            problems.append(f"guide does not document the required section: {section}")
    for path, probe in CLAIMS:
        if probe not in text:
            problems.append(f"guide does not cite {probe!r} for {path}")
        target = root / path
        if not target.is_file():
            problems.append(f"guide cites a file that does not exist: {path}")
            continue
        if probe not in target.read_text(encoding="utf-8"):
            problems.append(f"cited symbol {probe!r} is not implemented in {path}")
    for pattern in FORBIDDEN_CLAIMS:
        match = re.search(pattern, flat)
        if match:
            problems.append(
                f"guide claims behaviour the repository does not implement: {match.group(0)!r}"
            )
    return problems


def load_module(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AgentWorkflowGuideTests(unittest.TestCase):
    """D-010 - the shipped guide is present and every citation resolves."""

    def test_guide_satisfies_the_slice_contract(self):
        self.assertEqual(guide_problems(read(GUIDE), ROOT), [])

    def test_guide_names_the_ownership_boundary(self):
        flat = flatten(read(GUIDE))
        self.assertIn("no universal", flat)
        self.assertIn("no certified host", flat)

    def test_guide_documents_timeout_block_and_cancel(self):
        flat = flatten(read(GUIDE))
        for section in ("timeout behaviour", "block behaviour", "cancel", "not guaranteed"):
            self.assertIn(section, flat)

    def test_documented_timeout_numbers_match_the_hook_runtime(self):
        module = load_module(RUNTIME, "axiom_hook_runtime_for_guide")
        guide = read(GUIDE)
        self.assertEqual(module.DEFAULT_TIMEOUT_MS, 2000)
        self.assertEqual(module.HARD_MAX_RETRIES, 2)
        worst_case_ms = (module.DEFAULT_MAX_RETRIES + 1) * module.DEFAULT_TIMEOUT_MS
        self.assertEqual(worst_case_ms, 6000)
        for number in (str(module.DEFAULT_TIMEOUT_MS), str(module.HARD_MAX_RETRIES), str(worst_case_ms)):
            self.assertIn(number, guide)

    def test_runtime_pending_path_is_allow_not_block(self):
        module = load_module(RUNTIME, "axiom_hook_runtime_pending_for_guide")
        result = module.run_bounded(lambda: time.sleep(10), timeout_ms=100, max_retries=1)
        self.assertEqual(result["evidence"], "pending")
        self.assertEqual(result["action"], "allow")
        self.assertEqual(result["pending"], True)
        self.assertIn(result["failure"], module.FAILURE_KINDS)
        self.assertIn("pending evidence", result["reason"])

    def test_runtime_refuses_an_unbounded_budget(self):
        module = load_module(RUNTIME, "axiom_hook_runtime_budget_for_guide")
        for timeout_ms, max_retries in ((0, 0), (-1, 0), (2000, module.HARD_MAX_RETRIES + 1)):
            with self.assertRaises(module.UnboundedBudgetError):
                module.bounded_budget(timeout_ms, max_retries)


class AgentWorkflowGuideNegativeTests(unittest.TestCase):
    """D-010 - negative and boundary variants of the guide are rejected."""

    def setUp(self):
        self.guide = read(GUIDE)

    def test_negative_guide_without_the_timeout_section_is_rejected(self):
        broken = self.guide.replace("## 2. Timeout behaviour", "## 2. Runtime behaviour")
        problems = guide_problems(broken, ROOT)
        self.assertTrue(any("timeout behaviour" in p for p in problems), problems)

    def test_negative_guide_without_the_not_guaranteed_section_is_rejected(self):
        broken = re.sub(r"[Ww]hat is not guaranteed", "additional notes", self.guide)
        problems = guide_problems(broken, ROOT)
        self.assertTrue(any("what is not guaranteed" in p for p in problems), problems)

    def test_negative_guide_that_claims_a_universal_gate_is_rejected(self):
        broken = self.guide + "\n\nAxiom guarantees a universal hard completion gate.\n"
        problems = guide_problems(broken, ROOT)
        self.assertTrue(any("does not implement" in p for p in problems), problems)

    def test_negative_guide_that_cites_a_missing_symbol_is_rejected(self):
        broken = self.guide.replace("`bounded_budget()`", "`unbounded_forever()`")
        problems = guide_problems(broken, ROOT)
        self.assertTrue(problems, problems)
        self.assertTrue(any("bounded_budget" in p for p in problems), problems)

    def test_boundary_guide_with_a_real_file_but_wrong_symbol_is_rejected(self):
        # The Gemini file exists, but a guide that drops the real symbol it credits there must
        # fail the citation check instead of passing on the file name alone.
        broken = self.guide.replace("retry_budget", "some_other_budget")
        problems = guide_problems(broken, ROOT)
        self.assertTrue(any("retry_budget" in p for p in problems), problems)

    def test_boundary_guide_for_an_uncertified_host_is_rejected(self):
        broken = self.guide + "\n\nEvery host is certified after the in-repository unit tests.\n"
        problems = guide_problems(broken, ROOT)
        self.assertTrue(problems, problems)


if __name__ == "__main__":
    unittest.main()