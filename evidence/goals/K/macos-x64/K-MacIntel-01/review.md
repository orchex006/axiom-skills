# K-101 owner review — Mac Intel candidate

The owner source commit `eade281614677f96fd86260dc28e1fe0cbdeac0a`
updates the immutable K-012 draft pin, keeps the 41-file owner manifest on an
unreleased candidate, adds a source-bundle builder and refuses unsafe manifest
paths before reading them. It also corrects the owner Development.md's fixed
Windows checkout path and records the four required release lanes in README.
No skill or policy content was changed. The candidate archive contains the
actual 41 declared owner files and `skills-manifest.json`, not a synthetic
skills fixture.

`evidence/K-101/check.json` records five successful checks. The full owner
suite passed 207 tests with CPython 3.13.15. Focused corrupt/missing and
escape/undeclared tests passed. The 41-file verifier, plugin byte comparison
and archive extraction/reverification passed. The archive digest is
`e4b6a013b4971d93298886655debef5b11b912ca7a881c2ab1648477124b1a3a`.
The earlier system Python 3.9.6 suite failed seven existing gitignore tests
because `Path.write_text(newline=...)` requires a newer Python; that runtime is
not used for the required owner suite. The system Python 3.9.6 did run the
manifest verifier and archive builder successfully.

The builder checks the owner manifest before copying, stages in a sibling
temporary directory, rechecks the staged bytes, and refuses an existing
output. The verifier rejects traversal and platform-specific path spellings,
symlinks, changed bytes and undeclared files. An existing manual install or
host configuration is untouched. This owner payload is portable; K-105 must
prove installed Mac Intel consumption and the final CLI result separately.

The source feature commit was pushed to the canonical owner remote and the
remote SHA matched. Evidence delivery, canonical after-stage validation and
main integration are tracked separately in `handoff.json`. No release, tag,
signing, certification or native host adapter proof is claimed.
