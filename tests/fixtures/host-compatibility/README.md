# host-compatibility fixtures (V2-028)

Preserved byte fixtures replayed by `tests/test_host_compatibility.py` against the reusable
`HostCompatibilityChecks` rules, so the same checks that guard the shipped
`docs/host-compatibility.md` also run against known-bad and known-good copies.

- `negative-verified-without-probe.md` — a host marked `verified` with no probed installed
  version; `probe_status_problems` must reject it.
- `negative-provider-overrides-permissions.md` — an affirmative claim that provider settings
  can grant host permissions; `permission_problems` must reject it.
- `negative-independent-docs-version.md` — a self-declared numeric documentation version;
  `version_inheritance_problems` must reject it.
- `boundary-all-hosts-unverified.md` — every host honestly unverified; must be accepted.
- `boundary-verified-with-evidence.md` — one host verified with a probed version, a tested
  operating system and a runtime evidence SHA256; must be accepted.
- `boundary-unknown-version-stays-unverified.md` — an unknown version left unverified; must be
  accepted because it claims no version.