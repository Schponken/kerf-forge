# Running tests without repeating the full batch

Setup installs pinned pytest-xdist. Pytest uses **two processes**, grouped by file so module/session fixtures stay
useful and test modules that patch module globals do not run in threads. Use `-n 0` to debug sequentially, or
`-n 4` when the machine has enough memory for four independent CAD/Python processes. Do not use `-n auto` on
machines that report many host CPUs but have a small memory limit.

For each change, name the affected files. Start with their quick tests:

```sh
.venv/bin/pytest -q -m "not slow" tests/test_studio.py tests/test_usability.py
```

Then include the marked tests for anything the change touches:

```sh
.venv/bin/pytest -q tests/test_viewer.py tests/test_viewer_usability.py
.venv/bin/pytest -q -m browser tests/test_studio.py
```

- `slow`: CAD/solver, long-running lifecycle or external-tool integration tests.
- `browser`: real Chromium tests, also `slow`. Direct page tests share one Chromium server per worker, with fresh
  contexts on each connection; renderer integration still runs the production render command.
- `all_projects`: cross-project coverage, also `slow`. Run these when changing the general contract they verify,
  or leave them to the scheduled batch. This marker does not make all-project builds part of per-change testing.

The viewer's three-part fixture builds once per worker; every test receives a deep copy so moving joints cannot
alter the next test's starting pose. Tests that change source, parameters, caches or environment keep their own fixtures.

An unfiltered pytest invocation still includes **every test**, including all markers. `kerf verify` and the batch
runner retain that behavior. No default marker exclusion is hidden in configuration. Spencer's workflow reserves
full-suite and all-project verification for the manager's batched run; ordinary feature PRs report targeted results.

## Measured sample (2026-11-02)

On the same cached cloud machine, the same 68 tests in `test_viewer.py`, `test_viewer_usability.py`,
`test_studio.py`, `test_usability.py` and `test_render.py` took **67.01 s before / 45.30 s after** (32.4% less wall
time). Both runs passed all 68, including browser and lifecycle tests. The after command excludes only the new
fixture-isolation regression when comparing counts; it is tested separately. This is a targeted sample, not a
full-suite timing claim, and timings vary with machine load.
