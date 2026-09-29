"""Capture exact K-101 owner checks against the committed source candidate."""

import hashlib
import json
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, command):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    path = OUT / f"{name}.txt"
    path.write_text(f"cwd=axiom-skills (root workspace)\ncommand={' '.join(command)}\nexit={result.returncode}\n"
                    + result.stdout + result.stderr)
    return {"id": name, "command": command, "cwd": "axiom-skills",
            "exit_code": result.returncode, "output": str(path.relative_to(ROOT)),
            "output_sha256": digest(path)}


rows = [
    run("owner-tests", ["uv", "run", "--offline", "--python", "3.13", "--with", "pytest",
                        "python", "-m", "pytest", "tests", "-q"]),
    run("negative-tests", ["uv", "run", "--offline", "--python", "3.13", "--with", "pytest",
                           "python", "-m", "pytest", "tests/test_release_manifest_handoff.py",
                           "-k", "corrupt_and_missing or path_escape_and_undeclared", "-q", "--no-header"]),
    run("manifest", ["python3", "release/verify_manifest.py"]),
    run("plugin", ["python3", "release/build_plugin_bundle.py"]),
    run("consumer-archive", ["python3", "evidence/K-101/verify_archive.py"]),
]
report = {
    "task_id": "K-101", "host": {"os": platform.system(), "arch": platform.machine(),
                                  "os_version": platform.mac_ver()[0]},
    "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "spec_revision": json.loads((ROOT / "spec.lock.json").read_text())["spec_revision"],
    "artifacts": {
        "manifest_sha256": digest(ROOT / "release/skills-manifest.json"),
        "spec_lock_sha256": digest(ROOT / "spec.lock.json"),
        "owner_archive_sha256": digest(OUT / "owner-source.tar"),
    },
    "commands": rows,
    "all_passed": all(row["exit_code"] == 0 for row in rows),
    "provenance": "candidate", "certified": False,
}
(OUT / "check.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(json.dumps({"all_passed": report["all_passed"], "exit_codes": [row["exit_code"] for row in rows]}))
raise SystemExit(0 if report["all_passed"] else 1)
