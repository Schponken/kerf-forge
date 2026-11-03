# Studio redesign checkpoint

The design now centers the object in a full-width workspace, with a compact project tray and contextual model tools. Work distinguishes observed execution, assignments, pauses, input requests and incomplete sources. Briefing, Tune, History, Files, live job narration and help share the same restrained visual contract. Marked technical words explain themselves on hover, keyboard focus or a direct touch tap, including inside offline 3D viewers.

## Validation

- Integrated source `d5148800dd26f9f4a1771b5b41001f1b18e4927b`: **28 targeted tests passed in 123.91 seconds**, clean before and after. Covers navigation/draft preservation, all redesigned surfaces, Work observations/source gaps, compatible saved-viewer serving, existing model inspection/assembly and help/print-summary behavior.
- Final viewer definitions at `ff242e6b4a173124eb0f411c609ed0ed3470f0a9`: **5 targeted tests passed in 21.16 seconds**, clean before and after. Three repeat affected viewer interactions; two add definition serialization/desktop/touch behavior. This is 30 distinct test cases across the selections, not 33.
- Twelve browser marker warnings are inherited from pending test-configuration work. The full batch remains held; no full-suite, geometry rebuild, real provider job, physical action or installed-app update was performed.
- Independent source review found no actionable new defect in Tune, History, guidance, briefing and navigation. A bounded combined visual review inspected desktop/phone examples across the two themes. No overlap or overflow blocker was found. This is heuristic/interface verification, not a human usability study.
- Captures use mocked Studio APIs. The composed model screenshots use existing saved FPV geometry and matching report fingerprints, refreshed through the current viewer template without changing saved outputs. Other journeys use explicit synthetic fixtures.

## Reviewed feature queue

All changes remain pull requests for an independent manager; this task does not merge its own work.

| PR | Scope |
|---|---|
| [47](https://github.com/Schponken/kerf-forge/pull/47) | Native Follow live overlap |
| [48](https://github.com/Schponken/kerf-forge/pull/48) | Project context/actions/model space |
| [49](https://github.com/Schponken/kerf-forge/pull/49) | Work ownership, remaining steps and observed updates |
| [50](https://github.com/Schponken/kerf-forge/pull/50) | Shared shell and project collection |
| [51](https://github.com/Schponken/kerf-forge/pull/51) | Work source limits and filtering |
| [52](https://github.com/Schponken/kerf-forge/pull/52) | Files and making guides |
| [53](https://github.com/Schponken/kerf-forge/pull/53) | New-design briefing |
| [54](https://github.com/Schponken/kerf-forge/pull/54) | Reversible Tune workbench |
| [55](https://github.com/Schponken/kerf-forge/pull/55) | Job narration and decision evidence |
| [56](https://github.com/Schponken/kerf-forge/pull/56) | Contextual help and direct definitions |
| [57](https://github.com/Schponken/kerf-forge/pull/57) | Bounded session-response parsing |
| [58](https://github.com/Schponken/kerf-forge/pull/58) | Saved-build History |
| [59](https://github.com/Schponken/kerf-forge/pull/59) | Navigation, retry and unsaved-draft guards |
| [60](https://github.com/Schponken/kerf-forge/pull/60) | Object stage and compatible saved viewers |
| [61](https://github.com/Schponken/kerf-forge/pull/61) | Correct-worktree test imports and focused receipts |
| [62](https://github.com/Schponken/kerf-forge/pull/62) | Offline direct viewer definitions |
| [63](https://github.com/Schponken/kerf-forge/pull/63) | Accurate Activity assignment label |

The immutable `codex/studio-redesign-base` at `59f305e` holds prior reviewed dependencies for focused feature diffs. The integration branch is a reproducible combination, not permission to merge the feature queue without review. Preserve all owners' intent when merging: native shell controls plus draft guards; Work reset and polling state; Files/History tour targets and refresh focus; the original standalone print-summary style. Do not copy unrelated surface CSS into that print document. Exact duplicate PLAN entries created by additive merges were removed so scope counts remain meaningful. Activity's accessible label says claimed assignments, not that every claim is running.

## Evidence and next round

Local receipts, JUnit, logs and viewport captures are under `.cache/redesign-integration/` in the integration worktree. `initial-receipt.json`, `visual-receipt.json` and the final-viewer receipt identify exact revisions and fixture limitations.

A focused synthetic parser measurement in PR57 reduced a 2.97 MB response's median local parsing time from 4.679 to 2.006 ms (2.33x), with equal output and essentially unchanged peak memory. This does not establish end-to-end Studio latency. PR61 prevents a shared editable environment from silently testing another checkout.

Spencer deferred the additional ten-worker speed, motion, gap-filling, optimization and debugging round until the design settles. Do not launch that round or a recurring task from this note. At that checkpoint, use High effort and the smallest model adequate for each concrete task; prioritize observed friction and measured bottlenecks, with bounded checks.
