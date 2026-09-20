#!/usr/bin/env python3
"""Copy or verify the canonical skills and policy in the portable plugin."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "axiom"


def source_files() -> list[Path]:
    return [
        *sorted(path for path in (ROOT / "skills").rglob("*") if path.is_file()),
        ROOT / "policy" / "POLICY.md",
    ]


def destination(source: Path, plugin: Path) -> Path:
    return plugin / source.relative_to(ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="copy canonical bytes into the plugin")
    parser.add_argument("--force", action="store_true", help="replace a differing packaged copy")
    parser.add_argument("--plugin-root", type=Path, default=PLUGIN, help="package to check")
    args = parser.parse_args()
    plugin = args.plugin_root.resolve()
    if args.write and plugin != PLUGIN.resolve():
        parser.error("--write is permitted only for the repository plugin")
    if args.force and not args.write:
        parser.error("--force requires --write")
    errors: list[str] = []
    sources = source_files()
    if not sources or any(not path.is_file() for path in sources):
        print("FAIL canonical skill or policy source is missing")
        return 1
    skill_count = len(list((ROOT / "skills").glob("*/SKILL.md")))
    if not skill_count:
        print("FAIL canonical skills are missing")
        return 1
    expected = {destination(source, plugin) for source in sources}
    for source in sources:
        target = destination(source, plugin)
        if args.write:
            if target.exists() and target.read_bytes() != source.read_bytes() and not args.force:
                errors.append(f"refusing to replace differing file: {target.relative_to(plugin)}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        if not target.is_file() or target.read_bytes() != source.read_bytes():
            errors.append(str(target.relative_to(plugin)))
    for folder in (plugin / "skills", plugin / "policy"):
        if folder.exists():
            errors.extend(
                str(path.relative_to(plugin))
                for path in folder.rglob("*")
                if path.is_file() and path not in expected
            )
    if errors:
        for path in errors:
            print(f"FAIL plugin bundle differs from canonical source: {path}")
        return 1
    print(f"OK plugin bundle: {skill_count} skills and policy match canonical bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
