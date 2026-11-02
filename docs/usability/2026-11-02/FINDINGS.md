# Fresh-eyes usability pass

The inspection covered Studio and the standalone viewer at 1280×800 and 390×844, light and dark themes, the CLI help pages, setup scripts, and a complete Servo test rig build. [The contact sheet and full PR capture](README.md) use the same built outputs. The standalone viewer's six tabs and section controls were also captured under `/workspace/usability/before` during inspection.

| Finding | Outcome |
|---|---|
| Phone Tune controls extend outside the screen. | Fixed: narrower page gutters, flexible grid columns and sliders, local scrolling for wide material tables. Project list remains visible. |
| Phone tabs run outside the page. | Fixed: the tab strip scrolls horizontally. |
| Passing checks say “ready to print” before print files or a review exist. | Fixed: “checks pass” describes the result without claiming print readiness. |
| Network failures say Studio is closed and try to close the window. | Fixed: connection-loss screen has Reconnect and restart instructions; explicit Quit retains its close behavior. |
| A slow project load has no status, and a failed load offers no recovery. | Fixed: loading status and Try again action. Existing request tickets still prevent old replies replacing a newer selection. |
| Invalid Tune input disappears silently. | Fixed: explain the allowed range and retain previous valid edits. |
| NaN/infinity and one-sided parameter limits can slip past server validation. | Fixed: reject before writing the design. |
| Multiple jobs can write the same design or trial directory. | Fixed: serialize conflict checks and process registration; reject conflicting jobs before preparing a trial. Other projects can still run independently. |
| Saving parameters/materials or restoring a version can change a running build. | Fixed: reject with an Activity recovery message while that project or an all-project job runs. |
| Auto-fix can use a Claude plan and edit a design without a visible notice beside Build. | Fixed: show a notice and point to More to turn it off. Existing functionality and default preserved. |
| Mistyped project names and an unbuilt review pack print tracebacks. | Fixed: show project-list and first-build commands. |
| Subcommand help does not explain common actions or the project argument. | Fixed: descriptions and project-folder guidance. Every help page was executed. |
| Invalid port numbers or exhausting the range at 65535 can fail confusingly. | Fixed: validate CLI range and stop scanning at the highest valid port. Existing alternate-port startup remains. |
| `kerf new` accepts path-like names and writes punctuation/newlines as raw YAML. | Fixed: validate folder names, serialize titles safely, explain that the result is a starter project. Plain-title format preserved. |
| Setup docs do not give a clear first Studio workflow or explain when Claude is required. | Fixed: first-run path, local-build versus Claude usage, output order, offline/local-edit behavior, printer optionality and Mac limitations. |
| Print settings send a maker to Python source for the next step. | Fixed: explain opening, selecting printer/filament, slicing and reviewing in Bambu Studio. |
| Locale-dependent text I/O breaks tests on this machine. | Fixed in reusable environment: PYTHONUTF8=1; production firmware stub now names UTF-8 explicitly. Circuit output keeps explicit UTF-8 on the call line so the existing source audit recognizes it. |
| Architecture/toolbox docs lag recently added checks and modifiers. | Fixed: document the module and modifier settings and list the existing motion/aircraft checks. No thresholds changed. |
| Studio Checks wording, Follow live, Work tab, cleanup. | Not changed: explicitly reserved for other sessions. Raw technical notes in the standalone viewer also share the check-output wording; recorded for that work's owner rather than rewriting it here. |
| PCA9685 proxy test expects a height that excludes its modeled 2 mm of below-board pins. | Not changed: pre-existing geometry/test discrepancy. Preserved the real geometry, catalog values and assertion. Requires engineering review. |
| KST X08 Plus has a 1.5 mm catalog mounting hole but the selected screw is M2. | Not changed: pre-existing engineering inconsistency. No compatible smaller screw is in the stock catalog. A sourced hardware/interface correction is needed; do not change dimensions or weaken the test to force a pass. |

Existing safeguards also checked: missing/sign-in-required Claude states; failed and running job panels; close/quit behavior in existing tests; unbuilt projects; search and long text wrapping; printer not configured; local changes and offline pull behavior in the Mac launcher. No physical printer send or paid Claude design was started. Native macOS app execution is unavailable in this Linux environment; the three shell scripts pass `bash -n`.

Full-suite results are recorded in the PR and the dated STATUS.md entry. The geometry failures above prevent an all-green claim. Five firmware checks are skipped without optional firmware tools; they are not passes.

Integration on current main: the pre-thought-web stream test expected only the old event schema. It now checks the same visible lines and exact note/tool events, including every newly added metadata field; no event is skipped and no check is disabled.
