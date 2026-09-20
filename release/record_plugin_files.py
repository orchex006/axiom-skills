#!/usr/bin/env python3
"""Record exact plugin and marketplace bytes in the skills install manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "release" / "skills-manifest.json"
SCOPES = ("plugins", ".agents/plugins", ".claude-plugin", "marketplace-plugins")


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = data["files"]
    files[:] = [entry for entry in files if not any(
        entry["path"] == scope or entry["path"].startswith(scope + "/")
        for scope in SCOPES
    )]
    for scope in SCOPES:
        for path in sorted((ROOT / scope).rglob("*")):
            if not path.is_file():
                continue
            raw = path.read_bytes()
            files.append({
                "path": path.relative_to(ROOT).as_posix(),
                "role": "plugin-package" if scope == "plugins" else "plugin-marketplace",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
            })
    scopes = data["install_policy"]["declared_scope"]
    for scope in SCOPES:
        if scope not in scopes:
            scopes.append(scope)
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Recorded {sum(any(entry['path'].startswith(scope + '/') for scope in SCOPES) for entry in files)} plugin files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
