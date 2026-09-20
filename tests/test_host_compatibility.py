"""Targeted regression tests for the host compatibility and version-probing guide (V2-028).

This slice ships ``docs/host-compatibility.md``: the guide that keeps every host example
``unverified`` until its exact installed version was probed and recorded, states that provider
settings never override host permissions, and inherits the axiom-skills component version
instead of carrying an independent documentation version.

The tests come in four groups:

* structure/coverage checks over the shipped guide, driven by a reusable
  ``HostCompatibilityChecks`` so the same rules can be replayed against stored fixtures;
* drift checks that re-read the shipped compatibility record and the companion wiring guide,
  so the two documents and the record cannot silently contradict each other;
* negative cases (a host marked verified without a probed version, an affirmative
  provider-settings-override claim, a self-declared documentation version) that must be
  rejected;
* boundary cases (every host honestly unverified, a fully evidenced probed host, and an
  unknown version left unverified) that must be accepted.
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
DOC = "docs/host-compatibility.md"
HOSTS_GUIDE = "docs/guides/hosts.md"
RECORD = "adapters/compatibility.json"
FIXTURES = ROOT / "tests" / "fixtures" / "host-compatibility"

# Each supported host, with the shipped adapter path its section must reference.
HOSTS: dict[str, str] = {
    "codex": "adapters/codex/instructions.md",
    "claude": "adapters/claude/instructions.md",
    "gemini": "adapters/gemini/instructions.md",
    "antigravity": "adapters/antigravity/instructions.md",
}

# The independent compatibility dimensions (R23): none may be collapsed into a single claim.
DIMENSIONS: tuple[str, ...] = (
    "installed version",
    "operating system",
    "surface",
    "protocol version",
    "adapter version",
    "enforcement level",
)

SHARED_TOKENS: tuple[str, ...] = (
    "inherits the axiom-skills component version",
    "no independent version",
    "version-probed",
    "unverified",
    "not tested",
    "provider settings",
    "host permissions",
    "never override host permissions",
    "host approval",
    "certified_adapters: 0",
    "not certified",
    "independent",
)

PROBE_STATUS_RE = re.compile(r"probe status:\s*`?(unverified|verified)`?", re.I)
INSTALLED_VERSION_RE = re.compile(r"installed version:\s*`?([^`\n]*)`?", re.I)
OS_RE = re.compile(r"operating system:\s*`?([^`\n]+)`?", re.I)
EVIDENCE_RE = re.compile(r"evidence sha256:\s*`?([0-9a-f]{64})`?", re.I)
EMPTY_VERSION_TOKENS = ("", "unknown", "unverified", "not probed", "not-probed", "none", "tbd", "n/a")

# An affirmative claim that Axiom configuration widens or replaces the host's own controls.
PROVIDER_OVERRIDE_RE = re.compile(
    r"provider settings\s+(?:can\s+|may\s+)?(?:grant|widen|relax|replace|override|bypass|supersede)\b[^.\n]*\bhost (?:permissions|approval)",
    re.I,
)
INDEPENDENT_VERSION_RE = re.compile(r"\b(?:documentation|docs)\s+version:\s*`?\d", re.I)
CERTIFIED_TRUE_RE = re.compile(
    r'"certified"\s*:\s*true|certified\s*:\s*true|certified_adapters:\s*[1-9]', re.I
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def flatten(text: str) -> str:
    """Lowercase and collapse whitespace so line-wrapped phrasing still matches."""
    return " ".join(text.split()).lower()


def host_blocks(text: str) -> dict[str, str]:
    """Return the level-3 host sections, keyed by their flattened heading."""
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            current = flatten(match.group(2)) if len(match.group(1)) == 3 else None
            if current is not None:
                blocks.setdefault(current, [])
            continue
        if current is not None:
            blocks[current].append(line)
    return {key: "\n".join(value) for key, value in blocks.items()}


class HostCompatibilityChecks:
    """Reusable rules so the shipped guide and the stored fixtures run the same checks."""

    @classmethod
    def structure_problems(cls, text: str) -> list[str]:
        problems: list[str] = []
        flat = flatten(text)
        for token in SHARED_TOKENS:
            if token not in flat:
                problems.append(f"guide is missing shared content {token!r}")
        for dimension in DIMENSIONS:
            if dimension not in flat:
                problems.append(f"guide is missing compatibility dimension {dimension!r}")
        blocks = host_blocks(text)
        for host, adapter in HOSTS.items():
            matches = [key for key in blocks if host in key]
            if not matches:
                problems.append(f"{host}: guide has no host section")
                continue
            body = blocks[matches[0]]
            if adapter not in body:
                problems.append(f"{host}: section does not reference its shipped adapter {adapter}")
        return problems

    @classmethod
    def version_inheritance_problems(cls, text: str) -> list[str]:
        problems: list[str] = []
        flat = flatten(text)
        if "inherits the axiom-skills component version" not in flat:
            problems.append("guide does not state that it inherits the axiom-skills component version")
        if "no independent version" not in flat:
            problems.append("guide does not disclaim an independent documentation version")
        if INDEPENDENT_VERSION_RE.search(text):
            problems.append("guide declares its own numeric documentation version")
        return problems

    @classmethod
    def permission_problems(cls, text: str) -> list[str]:
        problems: list[str] = []
        flat = flatten(text)
        if "host permissions" not in flat:
            problems.append("guide does not discuss host permissions")
        if "never override host permissions" not in flat:
            problems.append("guide does not state that provider settings never override host permissions")
        if "host approval" not in flat:
            problems.append("guide does not state that host approval stays authoritative")
        if PROVIDER_OVERRIDE_RE.search(text):
            problems.append("guide claims provider settings can grant or override host permissions")
        return problems

    @classmethod
    def probe_status_problems(cls, text: str) -> list[str]:
        problems: list[str] = []
        for host in HOSTS:
            matches = [key for key in host_blocks(text) if host in key]
            if not matches:
                problems.append(f"{host}: guide has no host section")
                continue
            body = host_blocks(text)[matches[0]]
            statuses = PROBE_STATUS_RE.findall(body)
            if len(statuses) != 1:
                problems.append(f"{host}: expected exactly one probe status, found {len(statuses)}")
                continue
            status = statuses[0].lower()
            if status == "verified":
                version = INSTALLED_VERSION_RE.search(body)
                value = flatten(version.group(1)) if version else ""
                if value in EMPTY_VERSION_TOKENS:
                    problems.append(f"{host}: marked verified without a probed installed version")
                if not OS_RE.search(body):
                    problems.append(f"{host}: marked verified without a tested operating system")
                if not EVIDENCE_RE.search(body):
                    problems.append(f"{host}: marked verified without a runtime evidence sha256")
            elif CERTIFIED_TRUE_RE.search(body):
                problems.append(f"{host}: unverified section claims certification")
        return problems

    @classmethod
    def certification_problems(cls, text: str) -> list[str]:
        problems: list[str] = []
        flat = flatten(text)
        if "certified_adapters: 0" not in flat:
            problems.append("guide does not report certified_adapters: 0")
        if "not certified" not in flat:
            problems.append("guide does not state that the adapters are not certified")
        if CERTIFIED_TRUE_RE.search(text):
            problems.append("guide claims certification that no host evidence supports")
        return problems

    @classmethod
    def check(cls, text: str) -> list[str]:
        return (
            cls.structure_problems(text)
            + cls.version_inheritance_problems(text)
            + cls.permission_problems(text)
            + cls.probe_status_problems(text)
            + cls.certification_problems(text)
        )


class HostCompatibilityStructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = read(DOC)

    def test_guide_passes_every_shipped_check(self) -> None:
        """Regression: the shipped guide satisfies structure, honesty and probe rules."""
        self.assertEqual([], HostCompatibilityChecks.check(self.text))

    def test_guide_documents_all_four_hosts_with_their_adapters(self) -> None:
        blocks = host_blocks(self.text)
        for host, adapter in HOSTS.items():
            self.assertTrue(
                any(host in key for key in blocks), f"{host} has no host section"
            )
            self.assertIn(adapter, self.text, f"{host}: adapter path missing")

    def test_guide_declares_every_independent_dimension(self) -> None:
        flat = flatten(self.text)
        for dimension in DIMENSIONS:
            self.assertIn(dimension, flat, f"dimension {dimension!r} not declared")

    def test_guide_inherits_the_skills_version(self) -> None:
        self.assertEqual([], HostCompatibilityChecks.version_inheritance_problems(self.text))

    def test_guide_states_provider_settings_do_not_override_host_permissions(self) -> None:
        self.assertEqual([], HostCompatibilityChecks.permission_problems(self.text))

    def test_guide_keeps_every_host_unverified(self) -> None:
        self.assertEqual([], HostCompatibilityChecks.probe_status_problems(self.text))
        for key, body in host_blocks(self.text).items():
            if any(host in key for host in HOSTS):
                self.assertEqual(
                    ["unverified"], PROBE_STATUS_RE.findall(body), f"{key}: probe status not unverified"
                )

    def test_guide_does_not_claim_certification(self) -> None:
        self.assertEqual([], HostCompatibilityChecks.certification_problems(self.text))
        self.assertNotRegex(self.text, CERTIFIED_TRUE_RE)


class HostCompatibilityDriftTests(unittest.TestCase):
    """The guide must keep matching the record and the companion wiring guide."""

    def test_record_and_guide_agree_each_adapter_is_unverified(self) -> None:
        record = json.loads(read(RECORD))
        blocks = host_blocks(read(DOC))
        self.assertEqual(4, len(record["adapters"]))
        self.assertEqual(0, record["certification_summary"]["certified_adapters"])
        for adapter in record["adapters"]:
            host = adapter["adapter_id"]
            self.assertEqual(
                "not_run", adapter["version_probe"], f"{host}: record says version_probe != not_run"
            )
            self.assertIs(False, adapter["certified"], f"{host}: record says certified is not False")
            self.assertEqual(
                "instructions_only",
                adapter["enforcement_level"],
                f"{host}: enforcement level exceeds the evidence",
            )
            matches = [key for key in blocks if host in key]
            self.assertTrue(matches, f"{host}: no host section in the guide")
            self.assertEqual(
                ["unverified"],
                PROBE_STATUS_RE.findall(blocks[matches[0]]),
                f"{host}: guide probe status contradicts the record",
            )

    def test_guide_aligns_with_the_wiring_guide(self) -> None:
        wiring = read(HOSTS_GUIDE)
        for host, adapter in HOSTS.items():
            self.assertIn(host, flatten(wiring), f"{host} missing from {HOSTS_GUIDE}")
            self.assertIn(adapter, wiring, f"{adapter} missing from {HOSTS_GUIDE}")
        self.assertIn("certified_adapters: 0", flatten(wiring))
        self.assertIn("not certified", flatten(wiring))

    def test_docs_stay_outside_the_declared_bundle_scope(self) -> None:
        manifest = json.loads(read("release/skills-manifest.json"))
        scopes = manifest["install_policy"]["declared_scope"]
        self.assertEqual(["policy", "skills", "adapters", "plugins", ".agents/plugins", ".claude-plugin", "marketplace-plugins"], scopes)
        for added in ("docs", "tests"):
            self.assertNotIn(added, scopes, f"{added}/ must stay outside the hashed bundle scope")
        self.assertEqual(41, len(manifest["files"]))

    def test_shipped_manifest_verifier_still_accepts_the_bundle(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "v2028_verify_manifest", ROOT / "release" / "verify_manifest.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        problems = module.verify(ROOT / "release" / "skills-manifest.json", ROOT)
        self.assertEqual([], problems)


class HostCompatibilityNegativeTests(unittest.TestCase):
    """Every declared negative case must be rejected by the guide checks."""

    def test_negative_verified_without_a_probed_version_is_rejected(self) -> None:
        text = (FIXTURES / "negative-verified-without-probe.md").read_text(encoding="utf-8")
        problems = HostCompatibilityChecks.probe_status_problems(text)
        self.assertTrue(problems, "a host marked verified without a probed version was accepted")
        self.assertTrue(
            any("marked verified without a probed installed version" in p for p in problems),
            f"expected a probed-version problem, got {problems}",
        )

    def test_negative_provider_settings_override_claim_is_rejected(self) -> None:
        text = (FIXTURES / "negative-provider-overrides-permissions.md").read_text(
            encoding="utf-8"
        )
        problems = HostCompatibilityChecks.permission_problems(text)
        self.assertTrue(problems, "an affirmative provider-override claim was accepted")
        self.assertTrue(
            any("grant or override host permissions" in p for p in problems),
            f"expected a provider-override problem, got {problems}",
        )

    def test_negative_independent_documentation_version_is_rejected(self) -> None:
        text = (FIXTURES / "negative-independent-docs-version.md").read_text(encoding="utf-8")
        problems = HostCompatibilityChecks.version_inheritance_problems(text)
        self.assertTrue(problems, "a self-declared documentation version was accepted")
        self.assertTrue(
            any("own numeric documentation version" in p for p in problems),
            f"expected an independent-version problem, got {problems}",
        )


class HostCompatibilityBoundaryTests(unittest.TestCase):
    """Boundary cases must be accepted when they stay honest."""

    def test_boundary_all_hosts_unverified_is_accepted(self) -> None:
        text = (FIXTURES / "boundary-all-hosts-unverified.md").read_text(encoding="utf-8")
        self.assertEqual([], HostCompatibilityChecks.probe_status_problems(text))

    def test_boundary_verified_with_full_evidence_is_accepted(self) -> None:
        text = (FIXTURES / "boundary-verified-with-evidence.md").read_text(encoding="utf-8")
        self.assertEqual([], HostCompatibilityChecks.probe_status_problems(text))

    def test_boundary_unknown_version_stays_unverified_is_accepted(self) -> None:
        text = (FIXTURES / "boundary-unknown-version-stays-unverified.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual([], HostCompatibilityChecks.probe_status_problems(text))


if __name__ == "__main__":
    unittest.main()
