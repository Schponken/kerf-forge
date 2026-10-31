# Teardown: earthtojake/text-to-cad (cadgen 0.8.4)

Method: the vendored teardown skill (.claude/skills/teardown), applied by hand: repo downloaded as data, measured with
wc/grep, heaviest files read before the README. Nothing from the repo was run. 2026-10-31, commit of 2026-11-01.

**What it is.** An agent harness for build123d CAD (Claude Code / Codex / Cursor / Gemini plugin + MCP server + web
viewer) around a Python engine, `cadgen`, plus 12 agent skills and ~400 example model scripts.

**Weight: fork-class.** ~279k code lines, but most of that is example models (models/tendon_hand alone: 25k lines in two
files). The engine package is the real product: `packages/cadgen/src/cadgen/engine` (kernel/memo.py 4,873 lines,
kernel/trace.py 2,457, daemon.py 2,843, mechanism.py 2,379, document.py 2,108).
Licence: MIT. Pins `build123d>=0.13.0,<0.14` (packages/cadgen/pyproject.toml:50), the same version Kerf uses, and
`uv pip install cadgen` into Kerf's venv resolves cleanly (adds only shapely).

| Claim | Code |
|---|---|
| Fast, precise iterative edits | kernel/memo.py patches every build123d topology constructor and replays unchanged operations from a key of (operation, settings, parameters, input-shape keys): warm rebuilds only redo what changed. kernel/trace.py names faces/edges by construction history (the basis of `@cad[...]` references). Verified in code. |
| Kinematics | mechanism.py harvests build123d joints into an ISO 10303-105 / STEP AP242 mechanism (links, pairs, gear / rack / screw couplings). Verified in code. |
| URDF / SRDF / SDF | urdf_source.py (1,427 lines) is a validator (inertia tensors, mesh URIs, limits), not a generator; robots are authored as URDF by the agent per skills/urdf. |
| Engineering drawings | eng_drawing.py (1,554 lines): `Sheet.three_views` (line 462), hole callouts (line 342), ISO title block, PDF via ezdxf + matplotlib. Verified in code. |
| Printing | skills/gcode (OrcaSlicer CLI, built-in printer profiles), skills/bambu-labs (Bambu Connect / Studio handoff), skills/dfam-check (mesh printability per process). |

**Verdict: ADOPT parts, STEAL one idea.**
- ADOPT `cadgen` as a pinned dependency for (1) engineering-drawing PDFs of every printed part and (2) validating the
  URDFs Kerf will export. Replaces nothing in Kerf; both are new outputs.
- STEAL the memo idea at Kerf's scale: a per-part build cache (part source + params + catalog deps + engine version ->
  BREP on disk), so `kerf check` and Studio "Try" rebuild only the parts that changed. Kerf already caches FEA
  (kerf/fea.py); this is the same principle one level up. Do not adopt the whole engine: Kerf's pipeline, checks and
  joint model are its own and the memo patches build123d internals (pinned <0.14 for that reason, pyproject.toml:41-49).

**What we already have that overlaps.** kerf/assembly.py (joints, sweeps), kerf/viewer.py (3D viewer), kerf/export.py
(STEP/STL/3MF/plates), kerf/bambu.py (handoff), kerf/checks.py (print checks). Kerf goes further on engineering proof
(fasteners, FEA, access, electrical, independent review); text-to-cad goes further on rebuild speed, face naming,
drawings and robot formats.

**What breaks if we take it.** cadgen pins build123d <0.14, so Kerf cannot move to build123d 0.14 until cadgen does.
