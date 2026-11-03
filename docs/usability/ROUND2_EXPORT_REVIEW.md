# Studio round 2: export handoff

Base: `06cbf88` (assembly-guide integration). This branch incorporates the existing source-export fix
`3a9088f25ef222f0bf0eba5759011ee7fe4d7982`, its scoped completion correction
`47aba1b77f2821caaa9cad3a3015f66f352425d0`, and maker-output containment fix
`b7e1ece1ed0b6e79027809810d0b4f5a93abc46e`. These were absent from the integration base.
No original PR was merged remotely; existing implementations and tests were reused.

## Findings and fixes

- Editable ZIPs on the integration base omitted declared imported assets, nested helpers and data dependencies;
  generated output loops could follow links or read special files. The prior fixes retain declared sources,
  validate all selected files before constructing a ZIP, and explain rejected inputs with a 400 response.
- The saved simulation package appeared in Files & guides but was omitted from Download everything. The ZIP
  now includes it byte-for-byte, with the same output validation as the other named generated files.
- Individual downloads contained only the path tail. A project-name segment of `..` or a linked project folder
  changed the containment root, exposing a parent fixture file. Project, trial and history-thumbnail routes now
  validate that segment through the existing source containment helper; invalid requests return 404.

## Evidence

New temporary-fixture regressions reproduced **8 failures and 1 valid-download pass** before the two new fixes.
The failures directly demonstrated the missing simulation member and parent fixture bytes returned over HTTP.
The same 9 regressions passed after the fix. No private user file was accessed for the reproductions.

Clean tested code head: `65964a655acec95d9e28332e35be50e0d3f2d7c8`; Git status was empty.

```sh
PYTHONPATH="$PWD" .venv/bin/python -m pytest -q \
  tests/test_source_export.py tests/test_maker_export_safety.py \
  tests/test_studio_download_round2.py \
  tests/test_modules.py::test_source_symlink_is_rejected \
  tests/test_modules.py::test_imported_asset_is_required_and_confined \
  --junitxml=.cache/round2-export/results.xml
```

**60 passed in 3.67 s.** Local receipt, JUnit and output: `.cache/round2-export/`.
Doctor: ALL OK after linking existing local virtualenv/renderer dependencies; no installation. Firmware tool
warnings remain pre-existing and unrelated. Batch was HELD. Final documentation is a descendant of the tested
code head and changes no tested source bytes.

The test slice includes an extracted synthetic design rebuilt after deleting its original, byte-preserving
imports and Meshy sources, invalid/missing/escaping dependencies, malformed contracts, contained nested maker
outputs, symlinks, pipes, sockets, unreadable folders, simulation inclusion, and HTTP recovery/containment.
No real project build, Studio job, FEA, full suite, UI capture, app update or engineering-readiness claim.
Python data reads outside declared dependencies remain the documented source export limit.
