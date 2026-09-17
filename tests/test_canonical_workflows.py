"""Targeted regression tests for the canonical policy and workflow skills.

These tests cover the six canonical-workflow slices by checking the shipped artifacts and
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


def flatten(text: str) -> str:
    """Lowercase and collapse whitespace so line-wrapped phrasing still matches."""
    return " ".join(text.split()).lower()


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


class GraphImpactChecks:
    """A-004 — impact review.

    Expected impact must be stated before the query, actual dependencies must be compared
    against it, and a missing edge must never be upgraded into a no-impact claim.
    """

    EXPECTATION_MARKER = "State the expected impact before you query."
    COMPARISON_MARKER = "Compare expected against actual."
    NO_EDGE_MARKER = "Absence of an edge is not evidence of no impact."

    @classmethod
    def check(cls, text: str) -> list[str]:
        problems: list[str] = []
        meta = frontmatter(text)
        if meta.get("name") != "graph-impact":
            problems.append("frontmatter name is missing or wrong")
        if not meta.get("description"):
            problems.append("frontmatter description is missing")
        if not has_command(text, "graph_query"):
            problems.append("skill never requests a graph query")
        if '"operation": "impact"' not in text:
            problems.append("skill never requests the impact operation")
        if cls.EXPECTATION_MARKER not in text:
            problems.append("skill does not require the expected impact to be stated first")
        if cls.COMPARISON_MARKER not in text:
            problems.append("skill does not compare expected against actual dependencies")
        expectation_at = text.find(cls.EXPECTATION_MARKER)
        comparison_at = text.find(cls.COMPARISON_MARKER)
        if expectation_at == -1 or comparison_at == -1 or comparison_at < expectation_at:
            problems.append("expected impact is not stated before the actual comparison")
        if cls.NO_EDGE_MARKER not in text:
            problems.append("skill does not deny that a missing edge proves no impact")
        flat = flatten(text)
        if "unresolved" not in flat:
            problems.append("skill does not report unresolved references")
        if "coverage" not in flat:
            problems.append("skill does not report analyzer coverage limits")
        if "not evidence of no impact" not in flat and "not proof of no impact" not in flat:
            problems.append("skill does not reject the no-impact conclusion")
        if "never silently upgrade an empty result" not in flat:
            problems.append("skill does not forbid upgrading an empty result into a safe claim")
        return problems


class GraphCheckpointChecks:
    """A-005 — checkpoint publication.

    The source selector decides what a checkpoint describes, so a checkpoint built from an
    unstaged source must never be committed as if it described the staged index.
    """

    SOURCE_MARKER = "Name the source selector explicitly before creating a checkpoint."
    UNSTAGED_MARKER = "Never commit a checkpoint whose source was not the staged index."

    @classmethod
    def check(cls, text: str) -> list[str]:
        problems: list[str] = []
        meta = frontmatter(text)
        if meta.get("name") != "graph-checkpoint":
            problems.append("frontmatter name is missing or wrong")
        if not meta.get("description"):
            problems.append("frontmatter description is missing")
        for selector in ("--source staged", "--source worktree --verify-stable", "--source commit --ref"):
            if selector not in text:
                problems.append(f"skill does not name the {selector} source selector")
        if cls.SOURCE_MARKER not in text:
            problems.append("skill does not require an explicit source selector")
        if cls.UNSTAGED_MARKER not in text:
            problems.append("skill does not forbid committing an unstaged-source checkpoint")
        flat = flatten(text)
        if "materialize the git index" not in flat:
            problems.append("skill does not analyze the staged index as an isolated tree")
        if "worktree_busy" not in flat:
            problems.append("skill does not report an unstable working-tree source")
        if "dirty barrier" not in flat:
            problems.append("skill does not require a dirty barrier for a working-tree export")
        if "verify from staged" not in flat:
            problems.append("skill does not verify the checkpoint against the staged source")
        if "not to publish a git checkpoint on every save" not in flat:
            problems.append("skill does not bound checkpoint publication to an explicit boundary")
        if "hard stop" not in flat or "20 mib" not in flat:
            problems.append("skill does not state the checkpoint size budgets")
        if "`live/`" not in text or "`checkpoint/`" not in text:
            problems.append("skill does not separate the live and checkpoint lanes")
        if re.search(r"`live/`\s*(is\s+)?(tracked|committed)", flat) or "track `live/`" in flat or "commit `live/`" in flat:
            problems.append("skill tracks or commits the ignored live lane")
        if "union" not in flat:
            problems.append("skill does not prohibit union-merging generated graph output")
        return problems


class GraphDoctorChecks:
    """A-006 — graph diagnostics.

    A missing daemon, a partial snapshot and a bounded timeout must map to distinct recovery
    steps, and none of them may be answered by deleting or rebuilding live state.
    """

    TRIAGE_ROWS = (
        "Daemon missing or not reachable",
        "Partial snapshot or missing catalog member",
        "Bounded wait timed out, job still pending",
    )
    RECOVERY_STEPS = (
        "approved service lifecycle",
        "scoped reconcile for the missing project scope",
        "retry_after_ms",
    )
    SAFETY_MARKER = (
        "Deleting the live graph, the queue database or daemon state is not a recovery step."
    )

    @classmethod
    def check(cls, text: str) -> list[str]:
        problems: list[str] = []
        meta = frontmatter(text)
        if meta.get("name") != "graph-doctor":
            problems.append("frontmatter name is missing or wrong")
        if not meta.get("description"):
            problems.append("frontmatter description is missing")
        if not has_command(text, "graph_status"):
            problems.append("skill never collects graph status")
        for row in cls.TRIAGE_ROWS:
            if row not in text:
                problems.append(f"triage table does not distinguish: {row}")
        for step in cls.RECOVERY_STEPS:
            if step not in text:
                problems.append(f"triage table does not give the matching recovery step: {step}")
        if cls.SAFETY_MARKER not in text:
            problems.append("skill does not forbid deleting live state as recovery")
        flat = flatten(text)
        if "delete .axiom/graph and rebuild" in flat:
            problems.append("skill recommends deleting and rebuilding the graph")
        if "a timeout is not fresh" not in flat:
            problems.append("skill does not state that a timeout is not fresh")
        if "forced continuation against unchanged input is two attempts" not in flat:
            problems.append("skill does not bound retries")
        if "report the blocker" not in flat:
            problems.append("skill does not surface a blocked state when recovery is bounded out")
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



class GraphImpactSkillTests(unittest.TestCase):
    """A-004 — impact review skill."""

    def test_skill_satisfies_contract(self):
        self.assertEqual(GraphImpactChecks.check(read("skills/graph-impact/SKILL.md")), [])

    def test_skill_denies_no_impact_from_a_missing_edge(self):
        text = read("skills/graph-impact/SKILL.md").lower()
        self.assertIn("not evidence of no impact", text)
        self.assertIn("never silently upgrade an empty result", text)

    def test_negative_skill_that_claims_no_impact_is_rejected(self):
        fixture = (
            "---\n"
            "name: graph-impact\n"
            "description: Assume an empty result means nothing depends on the change.\n"
            "---\n\n"
            "Query `graph_query` with `\"operation\": \"impact\"` and if no edge comes back,\n"
            "report that the change has no impact and skip source reading and tests.\n"
        )
        problems = GraphImpactChecks.check(fixture)
        self.assertTrue(any("stated first" in p for p in problems), problems)
        self.assertTrue(any("no-impact conclusion" in p for p in problems), problems)
        self.assertTrue(any("missing edge proves no impact" in p for p in problems), problems)

    def test_boundary_skill_that_states_expectations_after_the_query_is_rejected(self):
        text = read("skills/graph-impact/SKILL.md")
        expected_at = text.find(GraphImpactChecks.EXPECTATION_MARKER)
        head = text[:expected_at]
        tail = text[expected_at:]
        reordered = head + GraphImpactChecks.COMPARISON_MARKER + tail
        problems = GraphImpactChecks.check(reordered)
        self.assertTrue(any("not stated before" in p for p in problems), problems)


class GraphCheckpointSkillTests(unittest.TestCase):
    """A-005 — checkpoint publication skill."""

    def test_skill_satisfies_contract(self):
        self.assertEqual(GraphCheckpointChecks.check(read("skills/graph-checkpoint/SKILL.md")), [])

    def test_skill_never_commits_an_unstaged_source_snapshot(self):
        text = read("skills/graph-checkpoint/SKILL.md")
        self.assertIn(GraphCheckpointChecks.UNSTAGED_MARKER, text)
        self.assertIn("never reset the working tree, stash,", flatten(text))

    def test_negative_skill_that_commits_a_worktree_snapshot_is_rejected(self):
        fixture = (
            "---\n"
            "name: graph-checkpoint\n"
            "description: Export the live working tree and commit it with the source.\n"
            "---\n\n"
            "Run the export against the working tree as it is, drop the output into\n"
            "`checkpoint/` and commit it together with whatever change happens to be staged.\n"
            "Leave `live/` tracked as well, and if a conflict appears take both sides with a\n"
            "union merge.\n"
        )
        problems = GraphCheckpointChecks.check(fixture)
        self.assertTrue(any("source selector" in p for p in problems), problems)
        self.assertTrue(any("unstaged-source checkpoint" in p for p in problems), problems)
        self.assertTrue(any("ignored live lane" in p for p in problems), problems)

    def test_boundary_skill_without_a_dirty_barrier_is_rejected(self):
        text = read("skills/graph-checkpoint/SKILL.md").replace("dirty barrier", "best effort")
        problems = GraphCheckpointChecks.check(text)
        self.assertTrue(any("dirty barrier" in p for p in problems), problems)


class GraphDoctorSkillTests(unittest.TestCase):
    """A-006 — graph diagnostics skill."""

    def test_skill_satisfies_contract(self):
        self.assertEqual(GraphDoctorChecks.check(read("skills/graph-doctor/SKILL.md")), [])

    def test_skill_separates_the_three_main_states(self):
        text = read("skills/graph-doctor/SKILL.md")
        for row in GraphDoctorChecks.TRIAGE_ROWS:
            self.assertIn(row, text)
        for step in GraphDoctorChecks.RECOVERY_STEPS:
            self.assertIn(step, text)

    def test_negative_skill_that_deletes_and_rebuilds_is_rejected(self):
        fixture = (
            "---\n"
            "name: graph-doctor\n"
            "description: Repair the graph by wiping it.\n"
            "---\n\n"
            "If `graph_status` looks wrong, delete .axiom/graph and rebuild everything.\n"
            "A timeout may be reported as fresh once the rebuild starts.\n"
            "Loop until the status is green.\n"
        )
        problems = GraphDoctorChecks.check(fixture)
        self.assertTrue(any("distinguish" in p for p in problems), problems)
        self.assertTrue(any("forbid deleting live state" in p for p in problems), problems)
        self.assertTrue(any("deleting and rebuilding" in p for p in problems), problems)
        self.assertTrue(any("not fresh" in p for p in problems), problems)

    def test_boundary_skill_that_collapses_the_states_is_rejected(self):
        text = (
            read("skills/graph-doctor/SKILL.md")
            .replace("Partial snapshot or missing catalog member", "Generic graph problem")
            .replace("scoped reconcile for the missing project scope", "restart everything")
        )
        problems = GraphDoctorChecks.check(text)
        self.assertTrue(any("distinguish: Partial snapshot" in p for p in problems), problems)
        self.assertTrue(
            any("recovery step: scoped reconcile for the missing project scope" in p for p in problems),
            problems,
        )


if __name__ == "__main__":
    unittest.main()
