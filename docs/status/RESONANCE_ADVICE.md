# Normal-operation resonance advice correction — 2026-11-02

The frequency check uses `abs(excitation - fn) / fn >= separation`. Previous
advice multiplied the excitation by `1 +/- separation`, so its proposed fix could
still fail the actual check. The check and its thresholds are unchanged.

For positive excitation e and 0 < s < 1, the allowable sides are fn <= e/(1+s)
and fn >= e/(1-s). Guidance now rounds outward to whole Hz and visits every
reported excitation band, so a proposed change also clears overlapping bands.
For the normal-flight screen with 200.2/600.5 Hz excitations, fn=185 Hz and s=0.2,
the proposed targets are at least 251 Hz or at most 166 Hz. The exact nearby
boundaries are 250.25 Hz and 166.8333 Hz; a 240.24 Hz recommendation fails.

The separate `min_ratio` rule uses the highest excitation and has precedence when
both settings exist, matching the check. Ratios at/above 1 for `separation` have
no high-side solution for positive excitations, so only the valid lower side is
suggested. Zero separation is no longer replaced with 0.2; invalid/nonpositive
natural frequencies do not yield made-up targets.

Validation: `PYTHONPATH="$PWD" .venv/bin/python -m pytest -q tests/test_advice.py
--junitxml=.cache/resonance-advice/results.xml` — **11 passed in 1.64 s**.
New tests call the actual natural-frequency check with mocked compliance and mass,
covering high/low targets, multiple overlapping excitations and ordering, both
check branches, zero/large separation, invalid numbers, exact representable
equality, and values 1e-6 Hz either side of the 20% boundaries. A first boundary
fixture at 250 Hz acquired floating-point square-root roundoff; the equality
fixture uses exactly representable values while epsilon tests retain the 20% case.

No FEA/CAD solve, benchmark, project geometry/material/load changes, catalog edits,
check/threshold changes, fatigue-life claim, installation, or full-suite run.
