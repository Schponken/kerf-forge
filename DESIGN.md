# Kerf Studio design system

The shared visual contract is the current `kerf/assets/studio.html` shell. Studio is an object-first workspace:
models, decisions and observed work occupy the screen. Navigation is a 72px top strip, or two rows totaling 108px
at widths up to 900px. Project search, Activity and Studio tools open as native disclosures; no permanent side rail.

## Shared tokens

| Role | Light | Dark |
|---|---|---|
| Background | `#f5f6f7` | `#171b20` |
| Alternate background | `#eef0f2` | `#1e242b` |
| Panel | `#ffffff` | `#252c34` |
| Alternate panel | `#f5f6f8` | `#2d3540` |
| Text | `#202832` | `#edf1f5` |
| Secondary text | `#5d6874` | `#b0bac6` |
| Divider | `#d4dae0` | `#46515e` |
| Hover surface | `#e4e9ee` | `#35404b` |
| Accent | `#305f86` | `#9bc1e0` |
| Text on accent | `#ffffff` | `#142735` |
| Control border | `#7a8794` | `#8495a6` |

Use existing semantic success, warning, error and information tokens for observed evidence. A muted or paused
state must remain explicit in words. Accent is a control cue; large decorative blue areas are outside the direction.

## Typography and shape

Use the system face at 15px/1.45 for ordinary text, with concise 12–13px secondary information. Headings use
weight and space, not a contrasting display face. Monospace belongs to code, measured values and identifiers.
Controls have 8px corners; disclosure trays use 14px corners and one soft offset shadow. Most content has no
container: spacing and thin rules group it. Avoid nested cards, generic tile grids, gradients, glows, grids behind
ordinary content, emoji controls and decorative eyebrows. Authored SVG icons share a 1.7px rounded stroke.

## Surface behavior

- The object stage is full width; the viewer may hide tools in labelled trays while keeping its immediate actions visible.
- All projects gives saved model images generous unboxed space. Projects without previews use compact rows;
  no blank image tiles imply a model exists. Build/check/review evidence stays distinct.
- Work, New design, History, Tune, Files and job stories have independent owners. Use scoped selectors and these
  globals; do not change another surface's functions or invent workflow state to make the layout look complete.
- Essential status, primary actions, errors and data-loss choices remain visible. Secondary explanations and
  advanced controls use labelled, keyboard-accessible disclosures with clear focus and Escape behavior.
- Phone layouts reflow naturally; avoid horizontal page overflow and never reserve empty space for closed tools.
- Motion is short, functional and respects reduced motion. Shell disclosures reveal in 160ms with a small vertical
  movement; repeated polling must not replay entrances. Browser/native keyboard behavior is part of the design.

## Evidence and limits

The intended user is a first-time, noncoder client; this is a design lens, not interview evidence. Saved assets are
read-only proof of existing geometry, not a new build or check. Fixtures label synthetic work honestly. The system
uses no new font, package or media dependency. Final validation is bounded desktop/phone, light/dark inspection
plus the changed surfaces' targeted tests; no live jobs, geometry builds, full suite or stress simulations.
