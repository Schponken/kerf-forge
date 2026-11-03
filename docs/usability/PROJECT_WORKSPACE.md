# Project workspace

Mode: Operate. A maker should be able to identify the design, understand its current evidence, inspect the model,
and choose a useful next action. The workspace inherits Studio's theme tokens and system typography; the shell
and Work overview are separate surfaces.

The before review found four related problems: a pointer-only one-line description, an underline extending beyond
the tab strip (one pixel of vertical overflow), a viewer sized against a guessed header height, and Build kit being
the prominent action even when saved checks report problems. The original Checks summary also called an unreviewed
build “Ready to print.”

## What stays visible

- Project name and a two-line brief establish what is being made. A real disclosure button reveals the rest and
  retains its state on refresh of the same project.
- Current status and reported problem count support the next decision. Review checks leads a failed build;
  Build kit leads an unbuilt or changed design. Build kit and Depth form one split group; Change and More remain
  distinct. Optimise and Upgrade live in More. Existing export and other actions remain.
- Project tabs and the model remain the main workspace. Tabs use keyboard selection and a contained selected
  indicator. The model fills available desktop space with a 360px minimum; small screens scroll to it.

## What moves behind a control

The text disclosure beside status, Build details, holds the longer explanation and saved cost, mass and print estimates. These are useful evidence,
but do not need a permanent extra header row. The native disclosure supports touch, keyboard, Escape, Close and
outside dismissal, preserves its state on same-project refresh, and uses a short entrance with reduced-motion
support. Important failure/stale/review states remain visible when it is closed. Nothing requires hover.

The Checks view calls stale results a previous build, and names the printable record Build check summary. Passing
reported checks do not imply that every possible check ran or that an independent review exists. No engineering
result, threshold, review file or process behavior changes.

## Evidence and limits

`tests/test_project_workspace.py` uses intercepted APIs and no job launches. It covers long/escaped content,
description and popover disclosure, refresh state/focus, tab keys and horizontal position, all build states,
existing action dispatch, desktop fit and phone/short-landscape access in both themes. `tests/browser.mjs` is the
existing shared-browser helper, copied unchanged from the reviewed fast-test work; it also works standalone.

Local captures in `.cache/project-workspace/grouped/` show a saved FPV viewer and its matching report/description
inside a mocked Studio page. They are not screenshots of an updated live app. Its old global shell remains in
these branch-only captures; the combined shell changes require the manager's separate integration check. Native
WKWebView checks use an isolated temporary HTML fixture with fetch blocked and a blank model frame, not the app.

The peer review found the workspace hierarchy clear and no specific visual blocker. The phone still requires
scrolling, especially with the old sidebar or a short landscape viewport; this change does not promise that the
entire project and model controls fit at once. Geometry, full verification and paused stress work were not run.
