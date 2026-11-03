# Focused test receipts

Before a focused run, use the active checkout:

```sh
.venv/bin/python tools/test_context.py
.venv/bin/python tools/batch_verify.py status
.venv/bin/python -m pytest -q tests/test_changed_area.py
```

Replace the example with the files or nodes covering the change. The first command reads local Git state
without optional index locks and lists local pytest PIDs with literal `tests/...` selections only; it does
not fetch, acquire a lock, inspect other machines, or decide whether a batch may run. Expressions, options,
absolute test paths and parametrized node IDs may be omitted. Check an unclear selection before starting
potentially overlapping work; an empty snapshot is not a reservation. The existing batch/claims rules still
apply. Run batch status separately using that checkout's matching helper revisions: newer versions may
fetch shared state, and an older checkout can report stale state. Do not borrow a batch script without its
matching imports or interpret a local snapshot as shared approval. An explicit hold remains a hold.

`pyproject.toml` uses pytest's built-in `pythonpath = ["."]`, relative to its config root, so both the pytest
console script and `python -m pytest` import this checkout even if the virtualenv was installed editable
from another tree. This does not change standalone Python or the `kerf` console entrypoint. Verify those
commands' import location separately when sharing a virtualenv. Keep xdist, addopts and marker settings
from other changes when resolving config conflicts; this fix adds only `pythonpath`.

Record one review receipt with:

- Checkout path, full HEAD before and after the run, and dirty files (or clean).
- Exact command, selection, result/count, and elapsed time.
- Dependency PRs/commits present and any required checks not run, with the reason.

A dirty-tree pass belongs to that working state, not automatically to its HEAD. Commit the tested changes
and report that relationship explicitly; never label a later head as tested without evidence. Reuse the
receipt for the same unchanged code, environment and selection instead of repeating it for another reviewer.
Re-run affected checks after a relevant edit, dependency update or conflict resolution. Historical passes
on different heads remain separate; don't add them into a unique-test total.

For stacked PRs, distinguish the feature's base from the frozen integration head containing its dependencies.
Validate in an isolated worktree at that head, confirm imports resolve there, and run one combined affected
selection after the stack stops changing. A feature receipt does not prove the combined stack. Preserve
other sessions' files and use the existing claim workflow. Full-suite runs remain exclusively with the batch
helper under the existing policy; this guide grants no exception or new automation.
