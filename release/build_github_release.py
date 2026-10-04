"""Build one portable, manifest-checked skills Release archive."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path
from release.verify_manifest import verify

ROOT = Path(__file__).resolve().parents[1]

def verify_source(root: Path, revision: str) -> None:
    """Bind every shipped byte to the chosen commit before labeling an archive."""
    manifest = json.loads((root / "release/skills-manifest.json").read_text(encoding="utf-8"))
    paths = ["release/skills-manifest.json", *[row["path"] for row in manifest["files"]]]
    for path in paths:
        committed = subprocess.check_output(["git", "show", revision + ":" + path], cwd=root)
        if committed != (root / path).read_bytes():
            raise ValueError("uncommitted or changed release payload: " + path)

def build(root: Path, output: Path, tag: str, source_revision: str) -> Path:
    manifest_path = root / "release/skills-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if tag != "v" + manifest["component_version"]:
        raise ValueError("tag does not match component version")
    if not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        raise ValueError("source revision must be an immutable Git commit")
    problems = verify(manifest_path, root)
    if problems:
        raise ValueError("; ".join(problems))
    if output.exists():
        raise ValueError("output must be a new directory")
    output.mkdir(parents=True)
    archive = output / f"axiom-skills-{manifest['component_version']}.zip"
    payload = {entry["path"]: (root / entry["path"]).read_bytes() for entry in manifest["files"]}
    payload["skills-manifest.json"] = manifest_path.read_bytes()
    # Fixed metadata and sorted members make the portable archive deterministic.
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, data)
    # Verify the completed bytes, not just the staging inputs.
    with zipfile.ZipFile(archive) as bundle:
        if set(bundle.namelist()) != set(payload) or len(bundle.namelist()) != len(payload):
            raise ValueError("archive members differ from declared payload")
        for name, data in payload.items():
            if bundle.read(name) != data:
                raise ValueError("archive payload changed: " + name)
    record = {"component": "axiom-skills", "version": manifest["component_version"],
              "source_revision": source_revision, "archive": archive.name,
              "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
              "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              "portable": True, "publication": "not_published"}
    (output / "RELEASE-SOURCES.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    (output / "SOURCE-REVISION.txt").write_text(source_revision + "\n", encoding="utf-8", newline="\n")
    (output / "RELEASE-NOTES.md").write_text(
        "# Axiom portable skills " + manifest["component_version"] + "\n\n"
        "One skills bundle for Codex, Claude Code, Gemini CLI and Antigravity. "
        "No OS-specific skill variants, certification, signing or attestation prerequisite. "
        "Host runtime hooks remain version/capability-specific and unverified where not exercised. "
        "This bundle does not install the Axiom runtime.\n", encoding="utf-8", newline="\n")
    checksum = "".join(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name + "\n"
                       for path in sorted(output.iterdir()) if path.is_file())
    (output / "SHA256SUMS").write_text(checksum, encoding="utf-8", newline="\n")
    return archive

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    verify_source(ROOT, revision)
    build(ROOT, args.out.resolve(), args.tag, revision)
    print("OK portable release archive, source record and SHA256SUMS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
