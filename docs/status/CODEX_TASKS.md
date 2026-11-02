# Parallel Codex tasks (start each as its own Codex chat in the kerf-forge environment once it is published)

Common rules (paste with every task): You are one of several AI sessions (Claude + Codex) on this repo. 1) `git pull`,
then claim your item: `.venv/bin/python tools/claims.py take "<item start>"` (pushes a claim to main; if push is
rejected, open your PR as a draft at once so the claim is visible). If it is already claimed, pick another free
software item from `tools/claims.py list` instead. `tools/claims.py beat` before each commit. Read
docs/status/BOARD.md if present and the latest STATUS.md entries. 2) Speed: setup is cached; run ./setup.sh only if
imports fail; run only the tests for files you change, never the full suite, never `kerf build` of every project.
3) CLAUDE.md non-negotiables: no faked passes, no loosened tests/checks/thresholds/catalog values, no review.json
edits, targeted edits to shared files. 4) One PR with tests, the PLAN box checked in it and a short STATUS.md entry;
mark it ready when its tests pass; never merge it yourself; then `tools/claims.py release`. Full permission: don't stop
to ask; make reasonable calls and note them in the PR.

1. "Fast tests" (PLAN): parallel pytest (xdist, pinned), slow/browser/all-project markers, cached fixtures, before/after wall time.
2. "Reviews go stale only for real changes" (PLAN): fingerprint only the catalog entries a project uses; tests.
3. "Firmware proven" (PLAN): `kerf firmware-check <p>` compiles every generated sketch with arduino-cli; tests.
4. "Repo cleanup" (PLAN): remove committed build outputs / scratch / oversized binaries (incl. docs/usability screenshots
   beyond a small contact sheet), .gitignore them; nothing a test or doc links to.
