#!/usr/bin/env python3
"""Stage the complete owner manifest and payload for axiom-cli conversion."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

from verify_manifest import DEFAULT_MANIFEST, load_manifest, portable_relative, verify


ROOT = Path(__file__).resolve().parents[1]


def build(output: Path) -> int:
    manifest = ROOT / DEFAULT_MANIFEST
    problems = verify(manifest, ROOT)
    if problems:
        for problem in problems:
            print(f"FAIL {problem}")
        return 1
    if output.exists() or output.is_symlink():
        print("FAIL candidate output already exists")
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="axiom-skills-source-", dir=output.parent) as temporary:
        stage = Path(temporary) / "source"
        stage.mkdir()
        shutil.copyfile(manifest, stage / "skills-manifest.json")
        rows = load_manifest(manifest)["files"]
        for row in rows:
            rel = row["path"]
            if not portable_relative(rel):
                print(f"FAIL unsafe declared path: {rel}")
                return 1
            destination = stage / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, destination)
        problems = verify(stage / "skills-manifest.json", stage)
        if problems:
            for problem in problems:
                print(f"FAIL staged {problem}")
            return 1
        os.replace(stage, output)
    print(f"OK owner engine source: {len(rows)} files; manifest=skills-manifest.json")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(build(args.out.resolve()))
