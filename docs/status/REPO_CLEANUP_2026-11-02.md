# Repo cleanup audit — 2026-11-02, ChatGPT Codex

At the start of the audit, main had about 410 tracked files / 10 MB; later main merges added source/tests. Earlier cleanup already added the general
build/cache/scratch ignore rules. PR #1 removed the large usability screenshot set from its retained history.
This round found **no additional files that were safe to delete** after checking tracked paths, references,
project manifests/helper imports, engine imports and claims. No history rewrite or project build was needed.

| Kept category | Why it stays |
|---|---|
| Vendor STEP models (largest: PCA9685 1.80 MB, Pico 1.72 MB) | Tests, catalog source notes and SOURCES.md refer to them; the robot arm uses the PCA9685 model. They are design inputs. |
| `kerf/assets/viewer3d.js` (567 KB) | `kerf/viewer.py` embeds it for the offline viewer; `tools/viewer/build.mjs` regenerates it. |
| `docs/results/*.png` | README links all six renders. |
| Usability contact sheets | PR evidence, already compressed; combined total remains below 1 MB, including the handoff sheet in PR #3. |
| `fingerlib.py`, `armlib.py`, claw `detail.py` | Imported by active part modules; not unused geometry files. |
| `kerf/intent.py` | Used by the after-edit hook and its tests. The other engine modules are statically reachable from CLI/package imports. |
| `docs/prototypes/mesh_merge.py` | Linked by PLAN.md and kerf/meshy.py as the measured basis for the mesh workflow. |
| AUDIT.md, references, status archive, skill licenses | Referenced engineering/provenance/workflow material. |
| `catalog_deps.json`, lockfiles, models under project `imports/` | Inputs used by review fingerprints, setup or import tests. |
| Claims | No stale claim for a checked-off item was found; active/open task claims and the batch lock were left to their owners. |

There are no tracked project/eval `out/` trees, Python bytecode, dependency/cache directories or scratch backups.
New ignore rules keep full-resolution usability images out while allowing compressed `*-contact.jpg/webp` sheets.
`tests/test_repo_hygiene.py` checks these rules, tracked generated files, the evidence budget and retained README
render links. It does not delete files automatically or prevent sourced CAD models from being committed.
