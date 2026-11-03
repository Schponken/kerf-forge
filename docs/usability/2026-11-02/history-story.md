# Saved-build History

Scope: the project History view. It inherits the Studio shell palette and controls; no global visual identity,
viewer, build pipeline, stored snapshots or restore API changed. The surface is for reading evidence and choosing
an intentional parameter restore. First-time use is a design lens, not interview evidence.

The saved-build sequence replaces repeated full-size cards with a chronological selector and one selected record.
Only an existing snapshot thumbnail is shown; missing pictures remain explicit text. The selected build shows
its recorded check outcome, device mass and parts cost, with all saved values/checks and build source disclosed.
Comparison defaults to the preceding saved build. The current built report is a separate choice, with newer
unbuilt edits called out. Only explicit false-to-true/true-to-false check outcomes are called improved/failed;
new, missing and numeric-only results carry no inferred quality or causal claim. Restoring previews exact current
project values against the saved values, preserves unknown/deleted parameter semantics and the existing API
confirmation/ownership/job guards, and warns that unsaved Tune drafts remain separate.

Keyboard support covers selection, native disclosures and picture dialog, Escape, focus after polling, and
selected-build/disclosure/strip position persistence. A late restore response refreshes the current project
without changing the user's chosen tab. Long identifiers wrap; wide comparisons scroll within a labelled region.
Reduced motion removes disclosure transitions.

Validation: the isolated browser test uses synthetic build records explicitly labelled as a fixture, with no real
project writes, builds or provider jobs. A one-pixel PNG verifies picture-dialog behavior without appearing in
captured design imagery. Desktop 1512×982 and phone 390×844 run in light/dark. The initial capture pass found no
scoped horizontal page overflow. One correction batch added the full saved record for an earliest/only snapshot,
exact restore-value labels, Tune-draft notice and final navigation coverage. Existing saved-history/restore and
geometry-comparison tests retain the original storage/API contract. Final result is recorded in STATUS.md.

Limits: snapshots expose at most the latest 30 saved builds. They do not store reasons for changes, full design
source, historical review approval or complete paused-check context. No such claims are inferred. Browser evidence
runs under the dependency baseline shell; the integration owner verifies the replacement shell separately.
