"""Keep the owner manifest convertible to the engine's reviewed skills bundle."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
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


def test_corrupt_and_missing_payload_refuse(tmp_path: Path) -> None:
    corrupt = changed_manifest(
        tmp_path, lambda manifest: manifest["files"][0].update(sha256="0" * 64)
    )
    assert "hash mismatch for declared file: policy/POLICY.md" in verify(corrupt, ROOT)

    def add_missing(manifest):
        manifest["files"].append({"path": "skills/missing/SKILL.md", "sha256": "0" * 64, "bytes": 1})

    missing = changed_manifest(tmp_path, add_missing)
    assert "declared file is missing: skills/missing/SKILL.md" in verify(missing, ROOT)


def test_path_escape_and_undeclared_payload_refuse(tmp_path: Path) -> None:
    escaped = changed_manifest(
        tmp_path, lambda manifest: manifest["files"][0].update(path="../outside.txt")
    )
    assert "unsafe declared path: ../outside.txt" in verify(escaped, ROOT)

    for scope in json.loads(MANIFEST.read_text())["install_policy"]["declared_scope"]:
        shutil.copytree(ROOT / scope, tmp_path / scope)
    extra = tmp_path / "skills/graph-context/undeclared.md"
    extra.write_text("not reviewed")
    assert "unknown file inside a declared scope fails install: skills/graph-context/undeclared.md" in verify(MANIFEST, tmp_path)


def test_full_owner_payload_stages_for_distribution_converter(tmp_path: Path) -> None:
    output = tmp_path / "owner source ไทย"
    command = [sys.executable, "release/build_engine_source.py", "--out", str(output)]
    built = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert built.returncode == 0, built.stdout + built.stderr
    assert (output / "skills-manifest.json").read_bytes() == MANIFEST.read_bytes()
    assert verify(output / "skills-manifest.json", output) == []
    assert len(json.loads(MANIFEST.read_text())["files"]) == 41
    for row in json.loads(MANIFEST.read_text())["files"]:
        assert (output / row["path"]).read_bytes() == (ROOT / row["path"]).read_bytes()
    refused = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert refused.returncode == 2
    assert "candidate output already exists" in refused.stdout


def test_windows_absolute_and_alternate_paths_refuse(tmp_path: Path) -> None:
    for value in ("C:/outside.txt", "C:outside.txt", "//server/share/file", "skills\\outside.md", "skills/file:stream"):
        path = changed_manifest(
            tmp_path, lambda manifest: manifest["files"][0].update(path=value)
        )
        assert f"unsafe declared path: {value}" in verify(path, ROOT)
