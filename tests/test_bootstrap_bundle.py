"""The consumer receives canonical bootstrap bytes and one policy source."""
import hashlib
import json
from pathlib import Path

from release.verify_manifest import verify

ROOT = Path(__file__).resolve().parents[1]


def test_complete_canonical_bootstrap_inputs_are_owned_and_hash_pinned():
    owner = json.loads((ROOT / "release/skills-manifest.json").read_text())
    content = json.loads((ROOT / "templates/bootstrap/manifest.json").read_text())
    declared = {entry["path"]: entry for entry in owner["files"]}
    expected = content["templates"] + [content["single_policy_source"]]
    for entry in expected:
        path = entry["path"]
        raw = (ROOT / path).read_bytes()
        assert path in declared
        assert declared[path]["sha256"] == entry["sha256"] == hashlib.sha256(raw).hexdigest()
        assert declared[path]["bytes"] == entry["bytes"] == len(raw)
    assert content["install_policy"]["policy_source_count"] == 1
    assert verify(ROOT / "release/skills-manifest.json", ROOT) == []


def test_changed_or_missing_template_declaration_refuses(tmp_path):
    owner = json.loads((ROOT / "release/skills-manifest.json").read_text())
    entry = next(row for row in owner["files"] if row["path"] == "templates/bootstrap/AGENTS.block.md")
    entry["sha256"] = "0" * 64
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(owner))
    assert "hash mismatch for declared file: templates/bootstrap/AGENTS.block.md" in verify(manifest, ROOT)
    owner["files"] = [row for row in owner["files"] if row["path"] != entry["path"]]
    manifest.write_text(json.dumps(owner))
    assert verify(manifest, ROOT), "a missing canonical template declaration must refuse the owner payload"
