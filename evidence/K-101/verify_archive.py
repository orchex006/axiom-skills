"""Verify the durable owner payload archive without trusting tar paths."""

import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ARCHIVE = Path(__file__).with_name("owner-source.tar")
ROOT = Path(__file__).resolve().parents[2]

with tempfile.TemporaryDirectory(prefix="axiom-k101-consumer-") as scratch:
    destination = Path(scratch)
    with tarfile.open(ARCHIVE) as bundle:
        members = bundle.getmembers()
        if not members or any(
            not member.isfile()
            or not member.name
            or member.name.startswith("/")
            or "\\" in member.name
            or any(part in ("", ".", "..") for part in member.name.split("/"))
            for member in members
        ):
            raise SystemExit("FAIL unsafe archive member")
        bundle.extractall(destination)
    manifest = json.loads((destination / "skills-manifest.json").read_text())
    if len(members) != len(manifest["files"]) + 1:
        raise SystemExit("FAIL archive member count")
    if (destination / "skills-manifest.json").read_bytes() != (ROOT / "release/skills-manifest.json").read_bytes():
        raise SystemExit("FAIL source manifest differs")
    command = [sys.executable, str(ROOT / "release/verify_manifest.py"),
               "--manifest", str(destination / "skills-manifest.json"),
               "--root", str(destination)]
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    print(f"archive_members={len(members)} exit={result.returncode}")
    raise SystemExit(result.returncode)
