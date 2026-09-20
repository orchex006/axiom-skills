"""Targeted regression tests for the namespace/ownership-aware bootstrap gitignore fragment.

V2-008 refines ``templates/bootstrap/gitignore.fragment`` so the managed ``.gitignore`` segment
isolates the private native runtime state under the Axiom namespace while keeping portable,
human-owned and ownership content visible to Git.

The tests come in four groups:

* structure checks over the shipped fragment (managed markers, namespace scoping and the
  ownership boundary it must document);
* semantic checks that run the real ``git check-ignore`` in a throwaway repository, so the
  generated/private paths are proven ignored and the portable/owned paths are proven trackable
  by Git itself rather than by a re-implemented matcher;
* negative cases (a fragment that ignores all of ``.axiom/`` and a fragment with unnamespaced
  root-level rules) that must be rejected;
* boundary cases (a fragment that leaks the private runtime state, a fragment whose overbroad
  lock rule swallows the portable ownership file, and a fragment with a broken managed marker)
  that must be rejected, plus an honest minimal fragment that must be accepted.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Never leave bytecode inside a declared bundle scope: an undeclared file there fails the
# shipped reference manifest verifier.
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = "templates/bootstrap/gitignore.fragment"
FIXTURES = ROOT / "tests" / "fixtures" / "gitignore-fragment"

BEGIN = "# BEGIN axiom-graph generated runtime ignores"
END = "# END axiom-graph generated runtime ignores"

# Generated output and private native runtime state that must never be committed.
REQUIRED_IGNORED = (
    ".axiom/graph/demo/proj/live/current.json",
    ".axiom/graph/demo/proj/live/generations/" + "a" * 64 + "/edges.jsonl",
    ".axiom/graph/demo/proj/.staging/stage.json",
    ".axiom/local/hook-state/pending.json",
    ".axiom/tmp/run.log",
    ".axiom/graph/demo/proj/index.sqlite",
    ".axiom/graph/demo/proj/index.sqlite-wal",
    ".axiom/graph/demo/proj/index.sqlite-shm",
    ".axiom/graph/demo/proj/index.sqlite-journal",
    ".axiom/graph/demo/proj/solution.guard",
    ".axiom/graph/demo/proj/current.json.tmp",
)

# Portable, human-owned or ownership content that must stay visible to Git and therefore
# remain eligible for invalidation.
REQUIRED_TRACKABLE = (
    ".axiom/config/solutions/demo.json",
    ".axiom/annotations/api-contracts.md",
    ".axiom/agent/POLICY.md",
    ".axiom/agent/POLICY.local.md",
    ".axiom/agent/bootstrap.lock.json",
    ".axiom/graph/demo/proj/checkpoint/current.json",
    ".axiom/graph/demo/proj/checkpoint/generations/" + "b" * 64 + "/manifest.json",
    "AGENTS.md",
    "docs/guides/hosts.md",
    ".axiom/README.md",
)

DOC_TOKENS = (
    ".axiom/config/",
    ".axiom/annotations/",
    "invalidat",
    "policy.local.md",
    "bootstrap.lock.json",
    "checkpoint",
    "never ignored",
)

BLANKET_RULES = {".axiom", ".axiom/", ".axiom/**", ".axiom/**/", ".axiom/*"}


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def flatten(text: str) -> str:
    return " ".join(text.split()).lower()


class GitignoreFragmentChecks:
    """Reusable rules so the shipped fragment and the stored fixtures run the same checks."""

    @classmethod
    def marker_problems(cls, text: str) -> list[str]:
        problems: list[str] = []
        for label, marker in (("begin", BEGIN), ("end", END)):
            if text.count(marker) != 1:
                problems.append(f"managed marker {label} is not present exactly once")
        if not problems and text.index(BEGIN) > text.index(END):
            problems.append("managed markers are out of order")
        return problems

    @classmethod
    def rules(cls, text: str) -> list[str]:
        return [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

    @classmethod
    def namespace_problems(cls, text: str) -> list[str]:
        problems: list[str] = []
        for rule in cls.rules(text):
            if rule in BLANKET_RULES or rule.rstrip("/") in BLANKET_RULES:
                problems.append(f"rule ignores all of .axiom/: {rule}")
            elif not rule.startswith(".axiom/"):
                problems.append(f"rule is not scoped to the Axiom namespace: {rule}")
        return problems

    @classmethod
    def documentation_problems(cls, text: str) -> list[str]:
        flat = flatten(text)
        return [f"fragment does not document {token!r}" for token in DOC_TOKENS if token not in flat]

    @staticmethod
    def _git_ignored(fragment_text: str, paths: tuple) -> dict:
        git = shutil.which("git")
        if git is None:
            raise unittest.SkipTest("git is required to prove .gitignore semantics")
        work = tempfile.mkdtemp(prefix="axiom-gitignore-")
        try:
            subprocess.run(
                [git, "init", "-q"],
                cwd=work,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            (Path(work) / ".gitignore").write_text(
                fragment_text, encoding="utf-8", newline="\n"
            )
            ignored: dict = {}
            for path in paths:
                probe = subprocess.run(
                    [git, "check-ignore", "--no-index", "-q", "--", path],
                    cwd=work,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                ignored[path] = probe.returncode == 0
            return ignored
        finally:
            shutil.rmtree(work, ignore_errors=True)

    @classmethod
    def runtime_semantics_problems(cls, text: str) -> list[str]:
        ignored = cls._git_ignored(text, REQUIRED_IGNORED + REQUIRED_TRACKABLE)
        problems: list[str] = []
        for path in REQUIRED_IGNORED:
            if not ignored[path]:
                problems.append(f"required generated/private path is not ignored: {path}")
        for path in REQUIRED_TRACKABLE:
            if ignored[path]:
                problems.append(f"trackable path must stay visible to Git: {path}")
        return problems

    @classmethod
    def check(cls, text: str) -> list[str]:
        return (
            cls.marker_problems(text)
            + cls.namespace_problems(text)
            + cls.documentation_problems(text)
            + cls.runtime_semantics_problems(text)
        )


class GitignoreFragmentStructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = read(FRAGMENT)

    def test_shipped_fragment_passes_every_check(self) -> None:
        self.assertEqual([], GitignoreFragmentChecks.check(self.text))

    def test_shipped_fragment_keeps_exactly_one_managed_segment(self) -> None:
        self.assertEqual([], GitignoreFragmentChecks.marker_problems(self.text))

    def test_shipped_fragment_is_namespace_scoped(self) -> None:
        self.assertEqual([], GitignoreFragmentChecks.namespace_problems(self.text))
        self.assertTrue(GitignoreFragmentChecks.rules(self.text))

    def test_shipped_fragment_is_proven_by_real_git(self) -> None:
        self.assertEqual([], GitignoreFragmentChecks.runtime_semantics_problems(self.text))

    def test_shipped_fragment_documents_the_ownership_boundary(self) -> None:
        self.assertEqual([], GitignoreFragmentChecks.documentation_problems(self.text))

    def test_shipped_fragment_matches_the_pinned_manifest_entry(self) -> None:
        manifest = json.loads(read("templates/bootstrap/manifest.json"))
        entry = next(t for t in manifest["templates"] if t["id"] == "gitignore-fragment")
        data = (ROOT / FRAGMENT).read_bytes()
        self.assertEqual(entry["path"], FRAGMENT)
        self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])
        self.assertEqual(len(data), entry["bytes"])

    def test_fragment_stays_outside_the_hashed_bundle_scope(self) -> None:
        manifest = json.loads(read("release/skills-manifest.json"))
        scopes = manifest["install_policy"]["declared_scope"]
        self.assertEqual(["policy", "skills", "adapters", "plugins", ".agents/plugins", ".claude-plugin", "marketplace-plugins"], scopes)
        self.assertNotIn("templates", scopes)
        self.assertNotIn(FRAGMENT, [f["path"] for f in manifest["files"]])

    def test_shipped_manifest_verifier_still_accepts_the_bundle(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "v2008_verify_manifest", ROOT / "release" / "verify_manifest.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual([], module.verify(ROOT / "release" / "skills-manifest.json", ROOT))


class GitignoreFragmentNegativeTests(unittest.TestCase):
    def test_negative_fragment_that_ignores_all_of_axiom_is_rejected(self) -> None:
        text = (FIXTURES / "negative-ignores-whole-axiom.fragment").read_text(encoding="utf-8")
        problems = GitignoreFragmentChecks.namespace_problems(text)
        self.assertTrue(any("ignores all of .axiom/" in p for p in problems), problems)
        runtime = GitignoreFragmentChecks.runtime_semantics_problems(text)
        self.assertTrue(
            any(
                name in problem
                for problem in runtime
                for name in (".axiom/config/solutions/demo.json", ".axiom/annotations/api-contracts.md")
            ),
            problems + runtime,
        )

    def test_negative_unnamespaced_root_level_rule_is_rejected(self) -> None:
        text = (FIXTURES / "negative-root-level-pattern.fragment").read_text(encoding="utf-8")
        problems = GitignoreFragmentChecks.namespace_problems(text)
        self.assertTrue(any("*.sqlite-wal" in p for p in problems), problems)
        self.assertTrue(any("node_modules/" in p for p in problems), problems)


class GitignoreFragmentBoundaryTests(unittest.TestCase):
    def test_boundary_leaking_private_runtime_state_is_rejected(self) -> None:
        text = (FIXTURES / "boundary-leaks-runtime-state.fragment").read_text(encoding="utf-8")
        self.assertEqual([], GitignoreFragmentChecks.marker_problems(text))
        self.assertEqual([], GitignoreFragmentChecks.namespace_problems(text))
        problems = GitignoreFragmentChecks.runtime_semantics_problems(text)
        self.assertTrue(any(".sqlite-wal" in p for p in problems), problems)

    def test_boundary_lock_rule_that_swallows_the_ownership_file_is_rejected(self) -> None:
        text = (FIXTURES / "boundary-overbroad-lock.fragment").read_text(encoding="utf-8")
        self.assertEqual([], GitignoreFragmentChecks.marker_problems(text))
        self.assertEqual([], GitignoreFragmentChecks.namespace_problems(text))
        problems = GitignoreFragmentChecks.runtime_semantics_problems(text)
        self.assertTrue(any("bootstrap.lock.json" in p for p in problems), problems)

    def test_boundary_a_broken_managed_marker_is_rejected(self) -> None:
        text = (FIXTURES / "boundary-missing-marker.fragment").read_text(encoding="utf-8")
        problems = GitignoreFragmentChecks.marker_problems(text)
        self.assertTrue(any("end" in p for p in problems), problems)

    def test_boundary_an_honest_minimal_fragment_is_accepted(self) -> None:
        text = (FIXTURES / "boundary-minimal-accepted.fragment").read_text(encoding="utf-8")
        self.assertEqual([], GitignoreFragmentChecks.marker_problems(text))
        self.assertEqual([], GitignoreFragmentChecks.namespace_problems(text))
        self.assertEqual([], GitignoreFragmentChecks.runtime_semantics_problems(text))

    def test_boundary_the_ownership_file_is_never_matched_by_the_shipped_fragment(self) -> None:
        ignored = GitignoreFragmentChecks._git_ignored(
            read(FRAGMENT), (".axiom/agent/bootstrap.lock.json",)
        )
        self.assertFalse(ignored[".axiom/agent/bootstrap.lock.json"])


if __name__ == "__main__":
    unittest.main()
