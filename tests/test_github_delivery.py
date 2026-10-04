"""Release bytes, portable delivery and refusal boundaries."""
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from release.build_github_release import build, verify_source

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "a" * 40


def version():
    return "v" + json.loads((ROOT / "release/skills-manifest.json").read_text(encoding="utf-8"))["component_version"]


def test_checked_archive_is_deterministic_and_complete(tmp_path):
    first = build(ROOT, tmp_path / "a", version(), SOURCE)
    second = build(ROOT, tmp_path / "b", version(), SOURCE)
    assert first.read_bytes() == second.read_bytes()
    record = json.loads((first.parent / "RELEASE-SOURCES.json").read_text())
    assert record["source_revision"] == SOURCE
    assert record["publication"] == "not_published"
    assert record["archive_sha256"] == hashlib.sha256(first.read_bytes()).hexdigest()
    with zipfile.ZipFile(first) as archive:
        manifest = json.loads(archive.read("skills-manifest.json"))
        assert set(archive.namelist()) == {e["path"] for e in manifest["files"]} | {"skills-manifest.json"}
        for entry in manifest["files"]:
            assert hashlib.sha256(archive.read(entry["path"])).hexdigest() == entry["sha256"]
    for line in (first.parent / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ")
        assert hashlib.sha256((first.parent / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("tag,source,reason", [
    ("v999.0.0", SOURCE, "component version"),
    (None, "main", "immutable Git commit"),
])
def test_incompatible_or_moving_input_refuses_before_output(tmp_path, tag, source, reason):
    out = tmp_path / "out"
    with pytest.raises(ValueError, match=reason):
        build(ROOT, out, tag or version(), source)
    assert not out.exists()


def test_existing_output_and_corrupt_bytes_refuse(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    sentinel = out / "human.txt"
    sentinel.write_text("preserve")
    with pytest.raises(ValueError, match="new directory"):
        build(ROOT, out, version(), SOURCE)
    assert sentinel.read_text() == "preserve"
    staging = tmp_path / "source"
    manifest = json.loads((ROOT / "release/skills-manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = staging / entry["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / entry["path"], path)
    (staging / "release").mkdir()
    shutil.copyfile(ROOT / "release/skills-manifest.json", staging / "release/skills-manifest.json")
    (staging / "skills/graph-context/SKILL.md").write_text("corrupt")
    with pytest.raises(ValueError, match="hash mismatch"):
        build(staging, tmp_path / "bad", version(), SOURCE)
    assert not (tmp_path / "bad").exists()


def test_runtime_claims_do_not_gate_portable_delivery():
    record = json.loads((ROOT / "adapters/compatibility.json").read_text(encoding="utf-8"))
    assert record["release_policy"]["host_runtime_tests_required_for_download"] is False
    assert record["release_policy"]["portable_skills"] is True
    assert record["release_policy"]["verification"] == "github_actions"
    assert record["release_policy"]["delivery"] == "github_releases"
    assert "certification_rules" not in record
    assert all("certified" not in adapter for adapter in record["adapters"])
    assert all(adapter["runtime_verified"] is False for adapter in record["adapters"])


def test_source_binding_rejects_changed_payload(tmp_path):
    # A real temporary Git commit, without changing any user repository/configuration.
    (tmp_path / "release").mkdir()
    (tmp_path / "payload.md").write_text("committed", newline="\n")
    (tmp_path / "release/skills-manifest.json").write_text(
        json.dumps({"files": [{"path": "payload.md"}]}), newline="\n"
    )
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, stderr=subprocess.STDOUT)
    git("init")
    git("add", "--", "payload.md", "release/skills-manifest.json")
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")
    revision = git("rev-parse", "HEAD").decode().strip()
    verify_source(tmp_path, revision)
    (tmp_path / "payload.md").write_text("changed", newline="\n")
    with pytest.raises(ValueError, match="changed release payload"):
        verify_source(tmp_path, revision)
