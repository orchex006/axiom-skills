"""Verify owner pin metadata offline; does not claim to read private spec bytes."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(root: Path) -> None:
    lock = json.loads((root / "spec.lock.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "release/skills-manifest.json").read_text(encoding="utf-8"))
    if lock.get("owner_repository") != "axiom-skills" or lock.get("spec_repository") != "axiom-specs":
        raise ValueError("wrong pin owner or specification repository")
    revision = lock.get("spec_revision", "")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("specification pin must be immutable")
    if manifest.get("spec_revision") != revision or manifest.get("spec_version") != lock.get("spec_version"):
        raise ValueError("manifest and pin disagree")
    digests = lock.get("contract_digests")
    if not isinstance(digests, dict) or not digests:
        raise ValueError("missing contract digests")
    for path, digest in digests.items():
        if not isinstance(path, str) or not path or ":" in path or "\\" in path or path.startswith("/") or any(part in ("", ".", "..") for part in path.split("/")):
            raise ValueError("unsafe contract path")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("invalid contract digest")
    rollup = hashlib.sha256(json.dumps(digests, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if lock.get("spec_content_sha256") != rollup:
        raise ValueError("specification digest rollup mismatch")


if __name__ == "__main__":
    verify(ROOT)
    print("OK immutable owner pin metadata; private specification content not fetched")
