"""Build a deterministic, byte-verified portable owner payload for K-305."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def main() -> None:
    archive = OUT / "owner-source.tar"
    with tempfile.TemporaryDirectory(prefix="axiom-k301-") as temporary:
        staged = Path(temporary) / "owner source ไทย"
        subprocess.run(
            [sys.executable, "release/build_engine_source.py", "--out", str(staged)],
            cwd=ROOT, check=True,
        )
        manifest = json.loads((staged / "skills-manifest.json").read_text(encoding="utf-8"))
        names = ["skills-manifest.json", *(row["path"] for row in manifest["files"])]
        with tarfile.open(archive, "w", format=tarfile.USTAR_FORMAT) as bundle:
            for name in sorted(names):
                data = (staged / name).read_bytes()
                member = tarfile.TarInfo(name)
                member.size = len(data)
                member.mode = 0o644
                bundle.addfile(member, io.BytesIO(data))
        # Verify what a downstream consumer receives, not just the staging tree.
        with tarfile.open(archive) as bundle:
            members = bundle.getmembers()
            assert len(members) == len(names)
            assert {member.name for member in members} == set(names)
            for member in members:
                assert member.isfile()
                stream = bundle.extractfile(member)
                assert stream is not None
                assert stream.read() == (staged / member.name).read_bytes()
        subprocess.run(
            [sys.executable, "release/verify_manifest.py", "--manifest",
             str(staged / "skills-manifest.json"), "--root", str(staged)],
            cwd=ROOT, check=True,
        )
    print(json.dumps({
        "artifact": "evidence/K-301/owner-source.tar",
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "members": len(names), "payload_files": len(manifest["files"]),
        "spec_revision": manifest["spec_revision"], "certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
