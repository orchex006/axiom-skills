"""Targeted regression tests for the host setup guide (D-008).

This slice ships `docs/guides/hosts.md`: the operator guide for wiring the Axiom graph
workflow into Codex CLI, Claude Code, Gemini CLI and Antigravity (AGY). The guide is
version-specific and must cite only real, retrieved host documentation; it must never present
a fabricated URL as certification, and it must never claim a host is certified.

The tests come in four groups:

* structure/coverage checks over the shipped guide, driven by a reusable ``HostsGuideChecks``
  so the same rules can be replayed against stored negative and boundary fixtures;
* drift checks that re-read the shipped hook adapters and the compatibility record, so the
  guide cannot silently contradict the code it documents;
* negative cases (a fabricated certification URL, a missing host) that must be rejected;
* boundary cases (every link honestly marked pending, and an allowlisted source URL whose
  final URL differs after a redirect) that must be accepted.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

# Never leave bytecode inside a declared bundle scope: an undeclared file there fails the
# shipped reference manifest verifier.
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
GUIDE = "docs/guides/hosts.md"
FIXTURES = ROOT / "tests" / "fixtures" / "hosts-guide"

HOOKS = (
    "adapters/codex/hooks/graph_stop.py",
    "adapters/claude/hooks/graph_stop.py",
    "adapters/claude/hooks/graph_task_completed.py",
    "adapters/gemini/hooks/graph_after_agent.py",
    "adapters/antigravity/hooks/graph_stop.py",
)

# The retrieved host-documentation links. Every key returned HTTP 200 on 2026-09-18 and the
# cited token was present in the decoded body; the raw log is preserved as D-008 evidence.
VERIFIED_LINKS: dict[str, str] = {
    "https://developers.openai.com/codex/guides/agents-md": "S09",
    "https://developers.openai.com/codex/mcp": "S10",
    "https://developers.openai.com/codex/hooks": "S11",
    "https://code.claude.com/docs/en/hooks": "S12",
    "https://code.claude.com/docs/en/mcp": "S20",
    "https://antigravity.google/docs/skills/": "S13",
    "https://antigravity.google/docs/rules-workflows/": "S14",
    "https://antigravity.google/docs/mcp/": "S15",
    "https://antigravity.google/docs/hooks/": "S16",
    "https://geminicli.com/docs/hooks/": "S17",
    "https://geminicli.com/docs/tools/mcp-server/": "S18",
}

# Each host must be documented version-specifically: its instruction file, its version-specific
# MCP field and hook schema, and the host output decision the shipped adapter emits.
HOST_TOKENS: dict[str, tuple[str, ...]] = {
    "codex": (
        "codex",
        "agents.md",
        "bearer_token_env_var",
        "graph_stop.py",
        "codex-stop-v1",
        '"decision": "block"',
    ),
    "claude": (
        "claude",
        "claude.md",
        "taskcompleted",
        "claude-stop-v1",
        "claude-task-completed-v1",
        "mcpservers",
    ),
    "gemini": (
        "gemini",
        "gemini.md",
        "httpurl",
        "afteragent",
        "aftertool",
        "gemini-after-agent-v1",
        '"decision": "retry"',
    ),
    "antigravity": (
        "antigravity",
        ".agent/rules",
        ".agents/skills",
        "serverurl",
        "posttooluse",
        "antigravity-stop-v1",
        '"decision": "continue"',
    ),
}

SHARED_TOKENS: tuple[str, ...] = (
    ".axiom/agent/policy.md",
    "<!-- axiom-graph:begin -->",
    "<!-- axiom-graph:end -->",
    "is not evidence",
    "instructions_only",
    "hook_verified",
    "ci_verified",
    "not certified",
    "certified_adapters: 0",
    "installed version",
    "version-specific",
)

URL_RE = re.compile(r"https?://[^\s|)>\]`\"']+")
CERTIFIED_TRUE_RE = re.compile(r'"certified"\s*:\s*true|certified\s*:\s*true')


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def flatten(text: str) -> str:
    """Lowercase and collapse whitespace so line-wrapped phrasing still matches."""
    return " ".join(text.split()).lower()


class HostsGuideChecks:
    """Reusable rules so the shipped guide and the stored fixtures run the same checks."""

    @classmethod
    def structure_problems(cls, text: str) -> list[str]:
        problems: list[str] = []
        flat = flatten(text)
        for host, tokens in HOST_TOKENS.items():
            for token in tokens:
                if token not in flat:
                    problems.append(f"{host}: guide is missing required token {token!r}")
        for token in SHARED_TOKENS:
            if token not in flat:
                problems.append(f"guide is missing shared content {token!r}")
        return problems

    @classmethod
    def fabrication_problems(cls, text: str) -> list[str]:
        problems: list[str] = []
        for url in URL_RE.findall(text):
            if url not in VERIFIED_LINKS:
                problems.append(
                    f"guide cites a URL that is not a retrieved host-documentation link: {url}"
                )
        if CERTIFIED_TRUE_RE.search(text):
            problems.append("guide claims certified: true, which no host evidence supports")
        return problems

    @classmethod
    def link_problems(cls, text: str) -> list[str]:
        problems: list[str] = []
        for url, source in VERIFIED_LINKS.items():
            if url not in text:
                problems.append(f"guide is missing retrieved link {source}: {url}")
        return problems

    @classmethod
    def check(cls, text: str) -> list[str]:
        return (
            cls.structure_problems(text)
            + cls.fabrication_problems(text)
            + cls.link_problems(text)
        )


class HostsGuideStructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = read(GUIDE)
        self.flat = flatten(self.text)

    def test_guide_passes_every_shipped_check(self) -> None:
        """Regression: the shipped guide satisfies structure, honesty and link coverage."""
        self.assertEqual([], HostsGuideChecks.check(self.text))

    def test_guide_documents_all_four_hosts(self) -> None:
        for host in HOST_TOKENS:
            self.assertIn(f"### {host}", self.flat.replace("antigravity (agy)", "antigravity"), host)

    def test_guide_lists_every_retrieved_link(self) -> None:
        self.assertEqual([], HostsGuideChecks.link_problems(self.text))
        for url in VERIFIED_LINKS:
            self.assertIn(url, self.text)

    def test_guide_never_presents_a_fabricated_url(self) -> None:
        self.assertEqual([], HostsGuideChecks.fabrication_problems(self.text))

    def test_guide_states_the_host_is_not_certified(self) -> None:
        self.assertIn("certified_adapters: 0", self.flat)
        self.assertIn("not certified", self.flat)
        self.assertNotRegex(self.text, CERTIFIED_TRUE_RE)


class HostsGuideDriftTests(unittest.TestCase):
    """The guide must keep matching the shipped adapters it documents."""

    @staticmethod
    def _host_decisions(hook_text: str) -> set[str]:
        """Decisions the adapter actually maps to the host, not mentions in prose."""
        start = hook_text.find("def to_host_output")
        if start == -1:
            return set()
        body = hook_text[start:]
        match = re.search(r"\ndef ", body[3:])
        if match:
            body = body[: match.start() + 3]
        return set(re.findall(r'"decision"\s*:\s*"([a-z]+)"', body))

    def test_schema_profiles_in_guide_match_shipped_hooks(self) -> None:
        guide = read(GUIDE)
        for hook in HOOKS:
            hook_text = read(hook)
            match = re.search(r"SUPPORTED_SCHEMA_PROFILES\s*=\s*\(([^)]*)\)", hook_text)
            self.assertIsNotNone(match, f"{hook} declares no schema-profile tuple")
            profiles = re.findall(r'"([^"]+)"', match.group(1))
            self.assertTrue(profiles, f"{hook} declares an empty profile tuple")
            for profile in profiles:
                self.assertIn(profile, guide, f"{hook}: {profile} is undocumented")

    def test_host_output_decisions_in_guide_match_shipped_hooks(self) -> None:
        guide_lines = read(GUIDE).splitlines()
        for hook in HOOKS:
            hook_text = read(hook)
            match = re.search(r"SUPPORTED_SCHEMA_PROFILES\s*=\s*\(([^)]*)\)", hook_text)
            profiles = re.findall(r'"([^"]+)"', match.group(1))
            decisions = self._host_decisions(hook_text)
            self.assertTrue(decisions, f"{hook} maps no host output decision")
            rows = [line for line in guide_lines if any(p in line for p in profiles)]
            self.assertTrue(rows, f"{hook}: no guide row references its schema profile")
            for decision in decisions:
                self.assertTrue(
                    any(f'"{decision}"' in row for row in rows),
                    f"{hook}: decision {decision!r} is not documented next to its profile",
                )

    def test_guide_covers_compatibility_adapters_and_sources(self) -> None:
        record = json.loads(read("adapters/compatibility.json"))
        guide = read(GUIDE)
        self.assertEqual(4, len(record["adapters"]))
        for adapter in record["adapters"]:
            self.assertIn(adapter["adapter_id"], guide)
            for source in adapter["documented_sources"]:
                self.assertIn(source, guide, f"{adapter['adapter_id']}: {source} not cited")

    def test_guide_does_not_change_the_declared_bundle_scope(self) -> None:
        manifest = json.loads(read("release/skills-manifest.json"))
        scopes = manifest["install_policy"]["declared_scope"]
        self.assertEqual(["policy", "skills", "adapters", "plugins", ".agents/plugins", ".claude-plugin", "marketplace-plugins"], scopes)
        for added in ("docs", "tests"):
            self.assertNotIn(added, scopes, f"{added}/ must stay outside the hashed bundle scope")
        self.assertEqual(41, len(manifest["files"]))

    def test_shipped_manifest_verifier_still_accepts_the_bundle(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "d008_verify_manifest", ROOT / "release" / "verify_manifest.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        problems = module.verify(ROOT / "release" / "skills-manifest.json", ROOT)
        self.assertEqual([], problems)


class HostsGuideNegativeTests(unittest.TestCase):
    """Every declared negative case must be rejected by the guide checks."""

    def test_negative_fabricated_certification_url_is_rejected(self) -> None:
        text = (FIXTURES / "negative-fabricated-link.md").read_text(encoding="utf-8")
        problems = HostsGuideChecks.fabrication_problems(text)
        self.assertTrue(problems, "a fabricated certification URL was accepted")
        self.assertTrue(
            any("not a retrieved host-documentation link" in p for p in problems),
            f"expected a fabricated-URL problem, got {problems}",
        )

    def test_negative_missing_host_is_rejected(self) -> None:
        text = (FIXTURES / "negative-missing-host.md").read_text(encoding="utf-8")
        problems = HostsGuideChecks.structure_problems(text)
        self.assertTrue(problems, "a guide missing a host was accepted")
        self.assertTrue(
            any(p.startswith("antigravity:") for p in problems),
            f"expected a missing-antigravity problem, got {problems}",
        )


class HostsGuideBoundaryTests(unittest.TestCase):
    """Boundary cases must be accepted when they stay honest."""

    def test_boundary_all_links_pending_is_accepted(self) -> None:
        text = (FIXTURES / "boundary-links-pending.md").read_text(encoding="utf-8")
        self.assertEqual([], HostsGuideChecks.link_problems(text))
        self.assertEqual([], HostsGuideChecks.fabrication_problems(text))

    def test_boundary_redirected_final_url_is_accepted(self) -> None:
        text = (FIXTURES / "boundary-redirect-final-url.md").read_text(encoding="utf-8")
        self.assertEqual([], HostsGuideChecks.fabrication_problems(text))


if __name__ == "__main__":
    unittest.main()
