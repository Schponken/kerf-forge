# Strength simulation activation receipt — 2026-11-02

Spencer authorized: “you can resume the strength simulations too”. Removed only the
`stress_sims` key from `PAUSED.json`. Existing pause machinery still honors future
strength holds; unrelated flags and the full-suite batch hold are unchanged.
Current strength work prioritizes normal flight and operating loads. Existing
crash/impact checks are preserved; crash optimization is outside the current objective.

Same-fingerprint saved outputs with paused/skipped FEA-backed checks now need a
rebuild after activation (`kerf review-status`: `out_stale`, explicit unproven
strength reason). The saved report and review fingerprint remain unchanged; the
old paused record never becomes a solved result merely because policy changed.
Geometry follow-ups remain unchecked in PLAN.md and are a separate work item.

Validation from isolated branch `codex/round2-strength-resume`, based on 06cbf88:

- `PYTHONPATH="$PWD" .venv/bin/python -m pytest -q tests/test_strength_resume.py
  tests/test_stress_pause.py tests/test_eng_minors.py::test_eng18_review_status_flags_stale_out
  tests/test_lessons.py --junitxml=.cache/strength-resume/results.xml` — **24 passed in 1.85 s**.
  Tests cover every FEA-backed check type after removing only the strength flag;
  paused/skipped saved evidence after activation; completed strength evidence;
  unchanged report bytes; unchanged paused behavior; and existing output freshness.
- One bounded, cache-disabled real `requirements._run_one(..., quick=False)`
  `fea_static` check ran without `KERF_STRESS`: 10 × 10 × 40 mm PETG axial bar,
  clamp at z=0, total end force 100 N at z=40, 5 mm mesh, 420 tetrahedra, 0.266 s.
  Catalog E=1460 MPa and SF=2; p99.9 stress **1.10 MPa**, limit **24 MPa**,
  displacement **0.027 mm**, maximum allowed **0.1 mm**: **PASS**.
  The interior stress was 1.000221 MPa vs F/A=1 MPa, and displacement compared with
  FL/EA=0.0273973 mm. The first ad hoc comparison incorrectly treated the clamp-local
  p99.9 as uniform axial stress; the corrected comparison uses the interior field.
  No engine tolerances or project checks were changed. Raw receipt and script are
  `.cache/strength-resume/axial.json` and `axial_check.py` in this worktree.

Solver access was serialized with the fpv_5in design task. No project build, design
redraw, catalog change, review.json edit, installation, full suite, or batch run.
Existing project strength findings remain real failures until separately fixed.
