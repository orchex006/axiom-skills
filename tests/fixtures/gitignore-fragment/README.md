Stored fixtures for the V2-008 gitignore-fragment checks.

These files are fragments, not complete .gitignore documents. The tests replay the
shipped GitignoreFragmentChecks against each one so the negative and boundary
cases are preserved as reviewable bytes rather than described in prose.

* negative-ignores-whole-axiom.fragment  -> AC1 violation: ignores all of .axiom/
* negative-root-level-pattern.fragment   -> namespace violation: unnamespaced rules
* boundary-leaks-runtime-state.fragment  -> private native runtime state leaks in
* boundary-missing-marker.fragment       -> managed-segment marker boundary broken
* boundary-minimal-accepted.fragment     -> honest minimal fragment, must be accepted
