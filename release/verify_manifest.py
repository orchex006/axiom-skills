#!/usr/bin/env python3
"""Reference verifier for the canonical skills bundle manifest.

The install/update contract for this bundle: a bundle is installable only when every
declared file is present with the declared SHA256 and byte count, and no undeclared
file exists inside a declared scope. Unknown files fail install; they are never
silently accepted, and a hash mismatch is never repaired in place.

This module is intentionally dependency-free (standard library only) so `axiom` can
reuse it as the reference behaviour for `axiom skills install/update`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

DEFAULT_MANIFEST = "release/skills-manifest.json"
SEMVER = r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.\-]+)?$"


class ManifestError(Exception):
    """The manifest itself is malformed and cannot be used as an install input."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"{path}: {exc}") from exc
    if not isinstance(obj, dict):
        raise ManifestError(f"{path}: manifest must be a JSON object")
    return obj


def declared_scopes(manifest: dict) -> list[str]:
    policy = manifest.get("install_policy")
    if not isinstance(policy, dict):
        return []
    scopes = policy.get("declared_scope")
    if not isinstance(scopes, list):
        return []
    return [s.strip("/").replace("\\", "/") for s in scopes if isinstance(s, str) and s.strip("/")]


def verify(manifest_path: Path, root: Path) -> list[str]:
    """Return the list of install-blocking problems; an empty list means installable."""
    problems: list[str] = []
    manifest = load_manifest(manifest_path)
    if not manifest.get("component"):
        problems.append("manifest does not declare a component identity")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return problems + ["manifest declares no files"]
    declared: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            problems.append("manifest file entry is not an object")
            continue
        rel = entry.get("path")
        if not isinstance(rel, str) or not rel:
            problems.append("manifest file entry is missing a path")
            continue
        rel = rel.replace("\\", "/")
        if rel in declared:
            problems.append(f"duplicate declaration fails install: {rel}")
            continue
        declared.add(rel)
        target = root / rel
        if not target.is_file():
            problems.append(f"declared file is missing: {rel}")
            continue
        data = target.read_bytes()
        if entry.get("sha256") != sha256_bytes(data):
            problems.append(f"hash mismatch for declared file: {rel}")
        if entry.get("bytes") is not None and entry["bytes"] != len(data):
            problems.append(f"byte count mismatch for declared file: {rel}")
    scopes = declared_scopes(manifest)
    if not scopes:
        problems.append("manifest declares no install scope")
    for scope in scopes:
        base = root / scope
        if not base.exists():
            problems.append(f"declared scope is missing: {scope}")
            continue
        for found in sorted(base.rglob("*")):
            if not found.is_file():
                continue
            rel = found.relative_to(root).as_posix()
            if rel not in declared:
                problems.append(f"unknown file inside a declared scope fails install: {rel}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    manifest_path = Path(args.manifest).resolve()
    root = Path(args.root).resolve()
    try:
        problems = verify(manifest_path, root)
        manifest = load_manifest(manifest_path)
    except ManifestError as exc:
        print(f"FAIL {exc}")
        return 1
    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        print(f"FAIL skills bundle verification: {len(problems)} problem(s)")
        return 1
    scopes = ",".join(declared_scopes(manifest))
    print(
        "OK skills bundle verification: "
        f"component={manifest['component']} version={manifest['component_version']} "
        f"channel={manifest.get('channel')} files={len(manifest['files'])} scopes={scopes}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
