"""Check the four portable plugin entrypoints and their canonical payload."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "axiom"


class PluginPackageTests(unittest.TestCase):
    def test_catalog_and_manifests_resolve_to_one_package(self) -> None:
        catalog = json.loads((ROOT / "marketplace-plugins" / "catalog.json").read_text())
        self.assertEqual(catalog["package"], "plugins/axiom")
        self.assertEqual(set(catalog["hosts"]), {"codex", "claude", "gemini", "antigravity"})
        for manifest_path in catalog["hosts"].values():
            self.assertTrue((ROOT / manifest_path).is_file(), manifest_path)
        for relative in (
            ".codex-plugin/plugin.json",
            ".claude-plugin/plugin.json",
            "gemini-extension.json",
            "plugin.json",
        ):
            self.assertEqual(json.loads((PLUGIN / relative).read_text())["name"], "axiom")
        self.assertNotIn("mcpServers", json.loads((PLUGIN / "gemini-extension.json").read_text()))
        self.assertFalse((PLUGIN / "mcp_config.json").exists())
        codex = json.loads((ROOT / catalog["hosts"]["codex"]).read_text())
        claude = json.loads((ROOT / catalog["hosts"]["claude"]).read_text())
        self.assertEqual(codex["plugins"][0]["source"]["path"], "./plugins/axiom")
        self.assertEqual(claude["plugins"][0]["source"], "./plugins/axiom")

    def test_packaged_skills_and_policy_match_canonical_bytes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "release" / "build_plugin_bundle.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_bundle_checker_rejects_a_modified_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "axiom"
            shutil.copytree(PLUGIN, candidate)
            packaged = candidate / "skills" / "graph-context" / "SKILL.md"
            packaged.write_bytes(packaged.read_bytes() + b"\nchanged\n")
            result = subprocess.run(
                [sys.executable, str(ROOT / "release" / "build_plugin_bundle.py"), "--plugin-root", str(candidate)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("skills/graph-context/SKILL.md", result.stdout.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
