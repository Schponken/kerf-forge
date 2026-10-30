# Competitor study (2026-10-30)

What Kerf Forge takes from each AI/CAD tool, and where it already matches or beats them. PLAN.md Phase 4b holds the new items.

| Tool | What it does well | Kerf Forge status |
|---|---|---|
| Zoo (Design Studio, KCL) | Code is the source of truth (KCL feature tree); clear errors that let the model fix its own code; sliders + text-to-edit | Code-first via build123d: have. Self-correcting errors: Phase 4b |
| AdamCAD | LLM writes CadQuery/OpenSCAD; two modes, Parametric vs Creative | Parametric: have. Creative (organic) via Meshy: Phase 4b |
| Spectral Labs SGS-1 | Text-to-CAD model; benchmark target for single parts | Compare on eval projects |
| earthtojake/text-to-cad (open source) | Agent skills on build123d/OpenCascade; STEP/STL/3MF/DXF/GLB | Same kernel; have |
| Leo AI | Search and reuse existing parts before generating new ones | Search-first `kerf find`: Phase 4b |
| McMaster-Carr | Free vendor CAD for real hardware | Catalog with sources: have; vendor STEP proxies: Phase 1 |
| OpenSCAD Customizer / MakerWorld Parametric Model Maker | Parameters as sliders; one click to a Bambu printer | Viewer sliders: Phase 4. A2L slice + send + monitor: Phase 4b |
| Onshape FeatureScript / Fusion 360 | Mates, joints, motion study, timeline, generative design / FEA | Joint tree, sweeps, FEA: have |
| Shapr3D / Plasticity | Fast direct editing | Click-to-edit faces in viewer: Phase 4b |
| Bambu Studio / OrcaSlicer | Auto-orient, supports, per-part material | A2L handoff: Phase 4b |

The gap none of the competitors fill: multi-part assemblies with mates, proven fits and strength checks before printing. That is Kerf Forge's core.

Sources: getleo.ai text-to-CAD comparisons (2026), Wevolver "We tested 7 text-to-CAD tools", zoo.dev blog, AdamCAD reviews.
