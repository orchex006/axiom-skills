# axiom-skills documentation

These guides are owned and released with `axiom-skills`. They describe intended
behaviour and record what has actually been executed; they are not a
certification for any host or target. Canonical contracts live in `axiom-specs`
and are resolved through the pinned revision - do not fork them as an editable
copy here.

## Guides

- [Host compatibility and version probing](host-compatibility.md) - the probing
  and compatibility-discipline guide: what "version-probed" means, the
  independent compatibility dimensions, and why a documented capability table is
  not certification.
- [Host setup guides](guides/hosts.md) - the wiring guide, with the shared versus
  host-specific split, the certification links each claim is grounded in, and a
  per-host quick reference for Codex CLI, Claude Code, Gemini CLI and Antigravity
  (AGY).
- [Agent workflow](guides/agent-workflow.md) - the bounded runtime contract: the
  timeout budget and retry cap, per-host block behaviour and the loop guard, the
  cancellation record, and what the workflow explicitly does not guarantee.

## Adapter and policy sources

Documentation follows the shipped bytes; the authoritative records are:

- `adapters/compatibility.json` - per-adapter, per-feature status, in-repository
  test evidence and the certification blockers.
- `policy/POLICY.md` - the managed-item policy, least privilege and degraded
  operation.
- `release/skills-manifest.json` - the hash-pinned bundle declaration and its
  fail-closed install policy.

## Ownership

Documentation for this bundle is owned here and changes in the same branch as the
code it describes. A published site can aggregate documentation from immutable
revisions without a separate documentation repository or a second version train.
