"""Keep the owner manifest convertible to the engine's reviewed skills bundle."""

from __future__ import annotations

import json
from pathlib import Path

from release.verify_manifest import verify


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release/skills-manifest.json"


def changed_manifest(tmp_path: Path, change) -> Path:
    manifest = json.loads(MANIFEST.read_text())
    change(manifest)
    path = tmp_path / "skills-manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def test_owner_manifest_pins_spec_and_reviews_every_executable() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["spec_revision"] == json.loads((ROOT / "spec.lock.json").read_text())["spec_revision"]
    assert verify(MANIFEST, ROOT) == []
    executable = [entry for entry in manifest["files"] if entry["path"].endswith(".py")]
    assert len(executable) == 6
    assert all("execute" in entry["capabilities"] for entry in executable)


def test_missing_spec_revision_refuses(tmp_path: Path) -> None:
    path = changed_manifest(tmp_path, lambda manifest: manifest.pop("spec_revision"))
    assert "manifest does not pin a 40-hex spec_revision" in verify(path, ROOT)


def test_unreviewed_executable_refuses(tmp_path: Path) -> None:
    def strip_review(manifest):
        next(entry for entry in manifest["files"] if entry["path"] == "adapters/codex/hooks/graph_stop.py").pop("capabilities")

    path = changed_manifest(tmp_path, strip_review)
    assert "executable lacks valid capability review: adapters/codex/hooks/graph_stop.py" in verify(path, ROOT)


def test_unknown_capability_refuses(tmp_path: Path) -> None:
    def invent_capability(manifest):
        next(entry for entry in manifest["files"] if entry["path"] == "adapters/common/hook_runtime.py")["capabilities"] = ["execute", "elevate"]

    path = changed_manifest(tmp_path, invent_capability)
    assert "executable lacks valid capability review: adapters/common/hook_runtime.py" in verify(path, ROOT)
