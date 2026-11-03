# Tune: inspect a change before keeping it

Tune extends the shared Studio design system in `DESIGN.md` (owned by the shell change). This is an Operate surface:
a first-time, noncoder user adjusts a real measurement or material, sees what it touches, tests a separate version,
and deliberately saves it. This lens is an assumption from the user brief, not audience research.

Measurements occupy an unboxed work surface. A change ledger pairs saved and edited values, with immediate
Try/Save state and individual Undo controls. On a phone the ledger moves ahead of the measurements. Input labels,
units, assumed units, declared ranges and suggested slider ranges stay explicit. Typing does not rerender or blur
the active control. Invalid input remains editable and blocks dispatch without replacing the last valid value.

The recorded trial is a separate region below editing. It identifies its input values and whether they match the
current entries, without claiming the geometry or engineering evidence is current. Material density is distinct
from part weight; catalog layer strength is distinct from part strength. Paused checks remain unproven.

A Save snapshots the original project and values, prevents duplicate dispatch, and only clears edits acknowledged
by each endpoint. If measurements save and materials fail, the material edits remain available for retry. Navigation
guards are owned by the shared journey change; this surface exposes rejected entries in `S.tune.invalid`, valid only
when `S.tune.edits === S.edits`.

Verification uses mocked API responses and a static viewer fixture. It covers typing, keyboard sliders, validation,
Undo/discard, units and effects, trial requests, partial save failure and navigation during an in-flight save. No
geometry or strength calculation is represented as having been run. Global identity, model rendering, job stories,
Checks, Files, History and New design are outside this change.
