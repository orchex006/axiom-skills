# hosts-guide fixtures

Fixtures replayed by tests/test_hosts_guide.py for the D-008 slice.

- `negative-fabricated-link.md`: a fabricated URL presented as certification must be rejected.
- `negative-missing-host.md`: a guide missing the Antigravity host must be rejected.
- `boundary-links-pending.md`: every link honestly marked pending is accepted.
- `boundary-redirect-final-url.md`: an allowlisted source URL whose final URL differs is accepted.
