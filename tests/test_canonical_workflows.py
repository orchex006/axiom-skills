"""Targeted regression tests for the canonical policy and workflow skills.

These tests cover the three canonical-workflow slices by checking the shipped artifacts and
by replaying negative and boundary variants that must be rejected.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def has_command(text: str, command: str) -> bool:
    return re.search(rf"`{re.escape(command)}`|\b{re.escape(command)}\b", text) is not None


class GraphPolicyChecks:
    """Reusable checks so the same rules can be replayed against negative fixtures."""

    REQUIRED_GRAPH_DIRECTORY = ".axiom/graph"

    @classmethod
    def check(cls, text: str) -> list[str]:
        problems: list[str] = []
        if cls.REQUIRED_GRAPH_DIRECTORY not in text:
            problems.append("policy does not reference the canonical graph directory")
        if "grahp" not in text:
            problems.append("policy does not distinguish the legacy grahp spelling")
        for term in ("freshness", "coverage"):
            if term not in text.lower():
                problems.append(f"policy does not discuss {term}")
        for value in ("stale", "updating", "unknown", "partial", "unsupported"):
            if value not in text:
                problems.append(f"policy does not define the {value} state")
        lowered = text.lower()
        if "grant" not in lowered and "permission" not in lowered:
            problems.append("policy does not state its permission boundary")
        if "grants no authority" not in lowered:
            problems.append("policy does not deny granting new permissions")
        if "does not widen" not in lowered:
            problems.append("policy does not refuse to widen host permissions")
        if "no new permissions" not in lowered:
            problems.append("policy does not state the no-new-permissions rule")
        if "never an instruction" not in lowered and "not an instruction" not in lowered:
            problems.append("policy does not deny instruction authority to graph data")
        if "every json shard" not in lowered and "all json shard" not in lowered:
            problems.append("policy does not prohibit loading every JSON shard")
        if "managed" not in lowered:
            problems.append("policy does not describe the managed-instruction boundary")
        return problems


class GraphContextChecks:
    ORDER_MARKER = "Ask for the projection, do not read the graph."

    @classmethod
    def check(cls, text: str) -> list[str]:
        problems: list[str] = []
        meta = frontmatter(text)
        if meta.get("name") != "graph-context":
            problems.append("frontmatter name is missing or wrong")
        if not meta.get("description"):
            problems.append("frontmatter description is missing")
        if not has_command(text, "graph_query"):
            problems.append("skill never requests a graph query")
        if "projection" not in text.lower():
            problems.append("skill never requests an explicit projection")
        if cls.ORDER_MARKER not in text:
            problems.append("skill does not state that projections are requested before source reading")
        projection_at = text.find(cls.ORDER_MARKER)
        read_at = text.find("Read only what the projection points at.")
        if projection_at == -1 or read_at == -1 or read_at < projection_at:
            problems.append("source reading is not sequenced after the projection request")
        lowered = text.lower()
        if "not concatenate json shards" not in lowered and "do not concatenate json shards" not in lowered:
            problems.append("skill does not prohibit concatenating JSON shards")
        if "catalog dump" not in lowered and "whole node" not in lowered:
            problems.append("skill does not prohibit dumping whole graph payloads into context")
        return problems


class GraphReconcileChecks:
    @classmethod
    def check(cls, text: str) -> list[str]:
        problems: list[str] = []
        meta = frontmatter(text)
        if meta.get("name") != "graph-reconcile":
            problems.append("frontmatter name is missing or wrong")
        if "coherent boundary" not in text.lower():
            problems.append("skill does not define a coherent boundary")
        if not has_command(text, "graph_reconcile"):
            problems.append("skill never requests reconciliation")
        if "scope=dirty" not in text:
            problems.append("skill does not request dirty scope")
        if "wait_timeout_ms" not in text:
            problems.append("skill does not bound the wait")
        lowered = text.lower()
        if "per-keystroke" not in lowered and "per keystroke" not in lowered:
            problems.append("skill does not prohibit per-keystroke reconciliation")
        if "full rebuild" not in lowered:
            problems.append("skill does not prohibit per-edit full rebuilds")
        if "timeout" not in lowered or "fresh" not in lowered:
            problems.append("skill does not state that a timeout is not fresh")
        if "bounded polling" not in lowered and "poll boundedly" not in lowered:
            problems.append("skill does not require bounded polling")
        return problems


class PolicyTests(unittest.TestCase):
    """A-001 — minimal graph policy contract."""

    def test_policy_satisfies_contract(self):
        self.assertEqual(GraphPolicyChecks.check(read("policy/POLICY.md")), [])

    def test_policy_references_exact_graph_directory(self):
        text = read("policy/POLICY.md")
        self.assertIn("`.axiom/graph`", text)
        self.assertNotIn(".agrimap-agent", text)

    def test_negative_policy_without_canonical_directory_is_rejected(self):
        mutated = read("policy/POLICY.md").replace(".axiom/graph", "somewhere/else")
        problems = GraphPolicyChecks.check(mutated)
        self.assertTrue(any("canonical graph directory" in p for p in problems), problems)

    def test_negative_policy_that_grants_permission_is_rejected(self):
        fixture = (
            "# Axiom Graph Policy\n\n"
            "Graph output lives under `out/grahp`.\n"
            "freshness and coverage are both fine.\n"
            "stale updating unknown partial unsupported\n"
            "This policy extends the agent's permissions to the whole workspace and the\n"
            "graph description may be followed as an instruction.\n"
            "Managed files are rewritten freely.\n"
        )
        problems = GraphPolicyChecks.check(fixture)
        self.assertTrue(any("canonical graph directory" in p for p in problems), problems)
        self.assertTrue(any("deny granting new permissions" in p for p in problems), problems)
        self.assertTrue(any("widen host permissions" in p for p in problems), problems)


class GraphContextSkillTests(unittest.TestCase):
    """A-002 — bounded context skill."""

    def test_skill_satisfies_contract(self):
        self.assertEqual(GraphContextChecks.check(read("skills/graph-context/SKILL.md")), [])

    def test_skill_forbids_shard_dump(self):
        text = read("skills/graph-context/SKILL.md").lower()
        self.assertIn("do not load `.axiom/graph` as a directory", text)
        self.assertIn("ask for a projection instead", text)

    def test_negative_skill_without_projection_step_is_rejected(self):
        mutated = read("skills/graph-context/SKILL.md").replace(
            GraphContextChecks.ORDER_MARKER, "Open the source files you think are relevant."
        )
        problems = GraphContextChecks.check(mutated)
        self.assertTrue(any("before source reading" in p for p in problems), problems)

    def test_boundary_skill_that_reorders_projection_after_reading_is_rejected(self):
        text = read("skills/graph-context/SKILL.md")
        head, marker, tail = text.partition(GraphContextChecks.ORDER_MARKER)
        reordered = head + tail + "\n\n" + marker
        problems = GraphContextChecks.check(reordered)
        self.assertTrue(any("not sequenced after" in p for p in problems), problems)


class GraphReconcileSkillTests(unittest.TestCase):
    """A-003 — batch reconcile skill."""

    def test_skill_satisfies_contract(self):
        self.assertEqual(GraphReconcileChecks.check(read("skills/graph-reconcile/SKILL.md")), [])

    def test_skill_forbids_per_edit_rebuild(self):
        text = read("skills/graph-reconcile/SKILL.md").lower()
        self.assertIn("per-keystroke or per-save full rebuilds", text)
        self.assertIn("scope=full", text)

    def test_negative_skill_that_reconciles_every_edit_is_rejected(self):
        fixture = (
            "---\n"
            "name: graph-reconcile\n"
            "description: Rebuild everything constantly.\n"
            "---\n\n"
            "Run `graph_reconcile` with `scope=full` and `wait_timeout_ms=0` after every save,\n"
            "after every tool call, and after every individual edit.\n"
            "Poll in a loop until the status is green.\n"
            "A timeout may be reported as fresh.\n"
        )
        problems = GraphReconcileChecks.check(fixture)
        self.assertTrue(any("coherent boundary" in p for p in problems), problems)
        self.assertTrue(any("per-keystroke" in p for p in problems), problems)
        self.assertTrue(any("full rebuild" in p for p in problems), problems)
        self.assertTrue(any("dirty scope" in p for p in problems), problems)
        self.assertTrue(any("bounded polling" in p for p in problems), problems)

    def test_negative_skill_without_dirty_scope_is_rejected(self):
        mutated = read("skills/graph-reconcile/SKILL.md").replace("scope=dirty", "scope=full")
        problems = GraphReconcileChecks.check(mutated)
        self.assertTrue(any("dirty scope" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
