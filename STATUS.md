STATE: IN PROGRESS

_Older entries: docs/status/STATUS-archive-to-2026-11-01.md (read only when you need history)._

## 2026-11-01 23:40 UTC-5 — Human factors (done), session e3d8373e
- kerf/req_human.py + access.repair_reach: `repair_access` (field-repair parts come off the FINISHED device with a hex
  key), use_story `handles` (finger opening, gloved when the story has gloves), `field_repair`, `carry_by`; ASSEMBLY.md
  "Carrying and field repair". fpv_5in: arm_1's 6 screws reachable with a 2.5 mm key on the finished quad (PASS).
- Running in the background: `kerf optimise fpv_5in` (arm_hole_2 / body_t / arm_t) after a full test run, aimed at the
  two real fpv findings (arm_resonance, arm_breaks_first). The body crash couple is now written from the screw radii.

## 2026-11-02 00:05 UTC-5 — Learn from results (done), session e3d8373e
- kerf/feedback.py: `kerf feedback <project> --part arm_1 --what broke --note "..." --case crash --file photo.jpg`
  records a finding with Kerf's own prediction for that part (failure-table row) and keeps the evidence files under
  projects/<p>/feedback/; `kerf feedback --learn [--apply]` writes LEARNED.md proposals (design fix after 2 repeats on a
  part, ENGINEERING.md rule after the same problem on one material in 2 projects, "model gap" when a part broke at
  < 50 % predicted use, fit reports -> the calibration route) and can append the rules to ENGINEERING.md. The old
  `kerf feedback <material> <reports>` calibration route is unchanged. tests/test_feedback.py. **Spencer: record real
  breakages / loose screws / fits with it; nothing real is recorded yet.**

## 2026-11-02 08:20 UTC-5 — fpv_5in optimiser run 1 + test status, session e3d8373e
- `kerf optimise fpv_5in` (9 evaluations, steps 1-2 mm on arm_hole_2 / body_t / arm_t): no passing point.
  arm_resonance and arm_breaks_first fail at every nearby point; arm_t -0.5 also fails arm_strength; body_t +0.25/+0.5
  breaks the body's arm nut-trap walls (< 0.8 mm). Every evaluation also showed "KiCad symbol libraries not found"
  (circuit check, another session's): fetched with tools/fetch_kicad_symbols.py. Run 2 with bigger steps
  (arm_hole_2 52/55/58, arm_t to 12, body_t 6.5-8, 20 runs) is going.
- Full suite: 655 passed; failures left are other sessions' (test_sim / test_urdf need mujoco / pybullet installed,
  circuit.py text write without encoding, catalog board proxy, KST X08 servo dims, aero/sim checks missing from the
  skill toolbox and UNITS). Mine fixed: utf-8 writes, Studio intake count, skill toolbox rows.
## 2026-11-01 ~22:30 UTC-5 — Motion simulated in MuJoCo (session 01S68R6S, PLAN "Prove the whole system")
- `kerf simulate <p>` (kerf/sim.py): loads the URDF Kerf already exports (kerf/urdf.py, real part / catalog masses and
  inertias) into MuJoCo 3.3.7 (pinned in pyproject); geared joints (`sweeps` follows) become joint equalities; each
  catalog servo joint gets a hobby-servo model: catalog stall torque falling linearly to zero at the catalog no-load
  speed (`speed_s_per_60`), full torque at 3 deg error, set point slewed at no-load speed. Prints link masses, servo
  limits, the home pose held under gravity, every simulated requirement; writes out/simulate.json.
- New requirement kinds (kerf/req_motion.py): `joint_speed` (move between poses in time), `grip_hold` (object of
  stated mass / width / friction held under gravity + 1 g shake on 3 axes, arm welded at the pose), `drop_impact`
  (rigid sub-assembly dropped onto a hit point: Hertz contact from the part's catalog E / Poisson in series with the
  part's FEA stiffness, undamped; the peak force goes to fea_static as a crash case). New sourced catalog section
  `friction` (PETG-steel 0.27, PLA-steel 0.30: Stoimenov et al., Tribology in Industry 2024).
- Hand-checked tests (tests/test_sim.py): pendulum period from the URDF inertia (0.5 %), servo holds 0.9 x stall and
  drops 1.1 x stall, no-load 60 deg move = catalog 0.17 s, grip slip threshold 2 mu N = m (g + a) (holds at 0.85 x,
  slips at 1.15 x; actually sharp between 0.9 and 1.1), Hertz impact peak = closed form (1 %), linear-spring drop and
  off-centre effective mass, locked joints welded rigid.
- Found while building it: a joint equality lock is soft (a loaded arm flexed 9 deg and shook the object loose), so
  scenario locks weld the body instead; MuJoCo copies `pos` into `ipos` for bodies added without an explicit inertial
  frame (payload landed at twice its lever) - fixed with explicit ipos.
- robot_arm: new requirements `move_speed` (full-range move with 150 g: 0.44 s, max 1 s, shoulder peaks at 0.87 x
  stall) and `grip_150g` (150 g steel part, 30 mm, mu 0.27, servo at half stall squeezes 9.7 N: 0.0 mm slip; by hand
  it lets go above 268 g). `kerf simulate robot_arm`: SIMULATE PASS.
- Open (PLAN follow-up sub-item): robot_arm 300 mm handling drop of the gripper end (97 g on the fixed-jaw tip):
  212 N peak, the gripper's crash FEA allows 128 N at SF 3 (21.5 MPa vs 13.0; strength margin 1.8, so it would bend,
  not snap) - not added as a requirement until the design fix or drop height is decided. robotic_gripper_desk is
  still being designed by another session (parallel jaws); grip_hold needs prismatic / geared jaw support there.
  Note: req_dynamic.impact_fea (another session, same evening) is the 1-DOF FEA-spring drop; drop_impact adds the
  rigid-body rotation (effective mass of an off-centre hit) and the Hertz contact in series.
- Verification (2026-11-02): tests/test_sim.py 8 passed; tests/test_urdf + test_catalog + test_docs + test_sim: 85 passed, 2 failed
  (test_catalog board_proxy 12.07 vs 10.07 and test_docs `modifiers`, both also fail without this work). `kerf check robot_arm`:
  move_speed / grip_150g ok; the project FAILs on sharp inside corners in yoke_r and gripper (geometry rules, not this item).
  `kerf verify --fast` and a full pytest could not finish here: killed for memory (exit 137) / timed out with other
  sessions' verifies sharing the 7 GB box; rerun them on a quiet machine.

## 2026-11-02 08:50 UTC-5 — Placeholder parts no longer flood the report (Spencer: "don't let this happen again")
- Studio showed the Hawk-fold contract (every part still a STUB box) as "64 problems to fix". Now `ctx.stub("why")`
  (or a part file whose docstring starts with STUB) marks a placeholder; kerf/pipeline._fold_stubs moves every
  problem naming a stub to report.json `stub_problems` and leaves ONE "design in progress: N of M parts are
  placeholders" problem; Studio shows "✎ being designed" and a banner instead of a problem count. On Hawk-fold: 65
  stub problems folded into one line; what is left (motor vs xt60, aileron servos vs the main spars, motor holes with no
  screw yet) are real contract problems for its owner. kerf skill step 2 now says stubs call ctx.stub and a project is
  never left with one. tests/test_stubs.py.

## 2026-11-02 08:45 UTC-5 — drone_foldable_wings is now split (Spencer's call) — READ THIS if you hold the drone
- Spencer asked session e3d8373e to fix the Hawk-fold drone while another session (claim 08:26) was building it, and
  chose to split it: **e3d8373e does the fuselage + pivot system** (fwd_fuse, hatch, motor_mount, aft_fuse, spine,
  hub_r/l, pinion_r/l, parts/layout.py fuselage/pivot functions, their requirements); **the 08:26 session keeps the
  wings + tail** (wing.py, aileron.py, tail_mount, hstab, elevator, fin, rudder). Both are PLAN sub-items under the
  drone. project.yaml: add your own requirement entries only; don't rewrite others' blocks.
- 09:05 update: the session that holds the drone was already designing ALL groups (front, pivot, wings, tail; its WIP
  commits 08:4x), so the split would only duplicate it. e3d8373e stopped its two designers, kept the other session's
  files, removed the split sub-items from PLAN and released its half. The drone stays with its owner.

## 2026-11-02 09:25 UTC-5 — Studio: a failed Build goes straight to fixing (Spencer: "fix those problems instead of just telling me")
- When a Studio build / check ends with problems, the server starts a Claude Code **fix job** by itself (kerf/studio.py
  auto_fix -> fix_job): `kerf fixes --apply` for the mechanical ones, every other problem fixed at its cause (never by
  loosening a check), then check, build, review, STATUS, commit, push; the page follows the fix job's progress. One
  automatic try per design state (fingerprint); not for a design still being built (placeholder parts) or when a fix is
  already running; the fix prompt stops if another session holds the project. "🔧 Fix these" on the Checks banner
  starts one by hand; More -> "Auto-fix failed builds: on / off" (setting `autofix`, on by default). Test in
  tests/test_studio.py.

## 2026-11-02 11:55 UTC-5 — Bambu A2L connection (Spencer sent the printer's LAN Only screen)
- `kerf printer setup --host <ip> --code <access code>` / `kerf printer status` (kerf/bambu.py setup_printer, status,
  ssdp_serial, mqtt_serial): finds the serial from the printer's SSDP announce (UDP 2021) or its MQTT report topic,
  proves the login with a status read, saves ~/.kerf/bambu.json owner-only. Studio: 🖨 button in Activity -> IP +
  access code -> Connect (the code is never sent back to the page). Tests: tests/test_printer_setup.py, test_studio.
- The cloud container and the linked VM cannot reach the printer's LAN (10.11.16.171:8883/990 closed from there), and
  the access code is a credential Claude does not type, so Spencer connects it once on his Mac (git pull, restart Studio).

### 2026-11-02 (session 4c4e3822c9): Checks tab in plain words; build fixes
- Studio Checks tab: every problem and failed requirement is now a card (which part, what is wrong in one sentence,
  why it matters, usual fix, raw check text under "Details"), with a "being worked on / nobody on it" status from
  running Studio jobs and fresh claims; the sidebar says "being worked on" too. Rules in kerf/explain.py (a message
  no rule knows still shows, by its first clause: add a rule there when a new check appears). tests/test_explain.py.
- attribution: the viewer stage's tracer resolved a file path on every Python call; fpv_wing builds hung 40+ min
  there (pod trace now 92 s).
- drawings: ISO 5455 enlargement scales (2:1, 5:1) after the reductions, so tiny parts (fpv_wing horns) get drawings.
- fpv_wing: check PASS (all 14 requirements); full build + review next.

## 2026-11-02 11:50 UTC-5 — Studio: Follow live + Work tab (Spencer: watch the cloud sessions design, without slowing them)
- **Follow live** (3D model tab, off by default): while on, Studio's one background thread runs `git fetch` at most once
  every 60 s; when origin commits touch projects/<p>/ (part files, project.yaml, layout) it fast-forwards the working copy
  with tools/mac/start.sh's rule (clean tree + `--ff-only`; otherwise "can't update: local changes" and following stops;
  it waits while a Studio job runs) and rebuilds ONLY the changed items (plus the ancestors that place them and the
  children that move with them) in a child process through the normal part build + cache: geometry + meshes, no checks,
  FEA, review or tests. The viewer swaps the meshes in place (`__kerf.liveSwap`; camera, pose and selection kept) and the
  changed parts glow ~2 s; one line under it gives "HH:MM <commit subject>". A part that fails mid-edit keeps its last
  good mesh and shows "being edited"; placeholders show "being designed". A project never built on the Mac gets a
  geometry-only model from the first live rebuild. No timeline/scrubber (Spencer: hold off). kerf/live.py.
- **Work** (sidebar, read-only, shares the same fetch): PLAN done / total, sessions working (claims fresher than
  STALE_MIN 90), items checked off today; a card per claim (item, minutes since the claim file's last commit = that
  session's last beat/commit, stale flag; for a project item its out/ render and "View 3D" = open it with Follow live
  on); the last 20 commit subjects with PLAN check-offs marked. Everything from git (log, claims/, PLAN.md at origin).
- Tests: tests/test_live.py (change detection between commits, ff refused on a dirty tree + follow stops, ≤60 s fetch
  cadence, last good mesh kept on a failed build incl. a real servo_link rebuild, Work data from a temp repo with fake
  claims/commits, Studio routes smoke). Also checked by hand in headless Chromium: liveSwap on a real servo_link viewer
  (moved + new part, glow on then off after 2 s, no page errors) and the Studio page (Work tab renders tiles / cards /
  feed; Follow live loads /live/<p>/viewer.html).
- Spencer, on the Mac: quit and reopen Kerf Studio (its start.sh pulls), open a project's 3D model, tick "Follow live".

## 2026-11-02 12:15 UTC-5 — batched testing (Spencer: "ship multiple sessions' features and then test them all at once")
- No more full `kerf verify` per session or per change. Per change: the tests and checks it touches. Full suite: one
  batched run (tools/batch_verify.py) when 4+ PLAN items are checked off since the last batch or untested work is 24 h
  old; pytest no longer stops at the first failure in that run (`kerf verify --all-failures`), so one run reports every
  break, recorded in verify/BATCH.json with the batch's commits as suspects. A failed batch blocks new work until fixed.
- Stop hook: stops when the work is pushed, no claim is held, no batch is due or failed, and other sessions cover the
  open items (it no longer runs verify itself). SessionStart shows the batch status. CLAUDE.md "Batched testing".
- Tests: tests/test_batch_verify.py 6 passed; hook exercised in a scratch clone (dirty tree blocks; SessionStart prints
  the batch status). First batch not run yet: it is due now and the next session that stops will run it.

## 2026-11-02 17:30 UTC - fresh-eyes usability pass handed to ChatGPT Codex (planning chat)
- Spencer asked for a first-time-user pass over Kerf (Studio, viewer, README/setup, CLI, output files). It runs in
  ChatGPT Codex (cloud environment "kerf-forge", thread "Set up kerf-forge") and arrives as pull requests against main
  plus a STATUS.md entry "Fresh-eyes usability pass, ChatGPT". Codex was told to leave the claimed Studio Checks tab,
  Follow live, Work tab and repo cleanup alone.
- Claude sessions: don't take the PLAN item; review and merge Codex's PRs (pull, run pytest, check screenshots) instead.
- Codex's environment has package-manager + listed-domain internet only; Chromium download was blocked during its setup,
  so its screenshots may need a network-settings update in the environment (Spencer's call).

- The 3D model first: runs that make a viewer write a preview viewer.html right after the parts are built and placed
  (fpv_wing: ~3 min from a cold cache, ~5 s warm; it used to arrive after every check and file, ~22 min). Studio opens
  it on the run's "model" event, folds the job panel, and says the rest is running; the full viewer replaces it.

## 2026-11-02 14:20 UTC-5 — Thought web (Spencer: "follow its thinking live, see the branches it explores and drops")
- kerf/thoughtweb.py + kerf/assets/thoughtweb.js (served at /ui/): a growing map in the job panel of every Claude job
  (new design, change, fix) and "More -> 🕸 How Kerf decided" for any project. Built only from the job's visible actions
  and notes (no hidden reasoning): ideas branch, references hang off them, options are chosen (gold) or set aside
  (grey, with the reason), the build trunk grows parts and tests; live every 1.5 s, replay afterwards. Studio's Claude
  stream now records search queries, URLs, paths and notes as events. tests/test_thoughtweb.py (rules + a fake live
  job drawn in the browser + a real project's map).
- 14:45 Mac app, one window (Spencer): the app on his Mac was still the first launcher (a script that opened a new
  Chrome app window on every click and quit, so the Dock never showed it running); the native single-instance app
  never got built (most likely no Apple command line tools for swiftc). install_app.sh now installs, when swiftc is
  missing, a launcher that keeps ONE window: a click while it is open brings that window forward (System Events), a
  click with the engine running but no window opens exactly one, a cold click starts the engine then opens one; the
  native app replaces it once `xcode-select --install` has run. setup.sh changed, so the next launch re-runs setup,
  which rebuilds the app in the background and reopens it. tests/test_mac_launcher.py (stubbed pgrep/curl/osascript/open).

### 2026-11-02 — Engine speed: faster collision checks (session 01S68R6R)
- Merged perf/mesh-prefilter. geom.overlap now caches each shape's own-frame box and runs a mesh prefilter (manifold3d)
  before the exact B-rep boolean. Measured on drone_foldable_wings (A/B in one process): same hits over 6 poses,
  interference pass 48.4 s -> 13.0 s, each motion-sweep step 3.6-4.2 s -> 0.03-0.06 s. Every reported volume is still
  the exact boolean; `KERF_EXACT_OVERLAP=1` turns the prefilter off. Caches copy/pickle as empty (a deep-copied part
  recomputes). Collision-heavy test files: 99 passed.
- Next: part cache keyed on the engine modules a part uses (PLAN "Engine speed").
- Pre-existing failures on main seen while testing (not from this change, owners please look):
  test_board_proxy_keeps_mounting_holes_clear, test_servo_dims_are_the_catalog[servos.KST_X08_Plus],
  test_every_requirement_check_listed, test_no_text_io_without_encoding (circuit.py:502, fwcheck.py:172).

## 2026-11-02 — Fresh-eyes usability pass, ChatGPT: viewer round
- Fixed together in the assembly viewer: previews no longer report unrun checks as successful; pending shopping/print tabs give a next step; known problems stay visible during previews. The writer retains device/off-board mass (servo_link: 198 g on the device, 317 g off it), buying and plate links work, internal references fold under details, and existing shared problem explanations are reused without editing Studio Checks wording.
- Fixed clipboard denial: if both clipboard methods fail, offer the exact text for manual copying instead of falsely saying Copied. Successful fallback still works. Fixed long-name/source-reference wrapping; the reproduced phone overflow was 1713 px on a 390 px screen.
- Validation after pulling current main and the collision/cache changes: 20 targeted tests passed (viewer, new browser regressions, maker output, existing explanations), including desktop/phone and light/dark cases. No full suite or all-project build was run under the updated workflow. Evidence: docs/usability/2026-11-02/VIEWER.md and one 357 KB contact sheet; full captures stay outside Git.
- Environment publication: saved draft and runtime both specify unrestricted public Internet; public HTTPS example.com returned 200. Installation/startup instructions and the explicit kerf-forge checkout path/commit are saved. Publication remains impossible through the exposed tools: they can read status/save drafts but have no Publish/Retry operation or publication-error endpoint. The panel's “Couldn't publish environment” backend cause is not exposed; a saved draft is not a published snapshot. Continue with software work; no extra permission is needed.
- Next round: output files and setup/install recovery, with a fresh main/claims/BOARD check. Reserved Studio areas and claimed project geometry were not edited. PRs are for another session or Spencer to review and merge.

- Viewer round final probe: corrected the contradictory “without hitting anything” text on failed sweeps and marked skipped checks neutrally as not checked; the browser regression asserts both. Final affected-area run: 20 passed.

### 2026-11-02 — Engine speed: part cache follows the engine files a part uses; `kerf req` (session 01S68R6R)
- kerf/partcache.py no longer hashes every kerf/*.py into each key: each build records (sys.monitoring) the engine
  files whose code ran, widened by their imports and the top-level import closure, and lookup re-hashes just those.
  drone_foldable_wings: cold 180 s, warm 1.3 s, after a fea.py edit 2.2 s (was a full ~180 s rebuild), after
  req_aero.py 51 s (3 wing parts reach it through requirements.py's imports: conservative), after iface.py 156 s.
  Also fixed catalog.recording() removing the wrong set when two nested recordings were both empty.
- New `kerf req <p> [id ...]`: only the named requirements (ids or check names) on the assembled project; servo_link
  all 8 in 6.9 s. `kerf check` still decides PASS. Listed in CLAUDE.md's command table.

## 2026-11-02 — Fresh-eyes usability pass, ChatGPT

- Fixed: phone Tune clipping and tab overflow; misleading ready-to-print label; connection-loss recovery; loading/retry states; invalid numeric edits, nonfinite values and one-sided limits; overlapping project jobs and trial preparation; saving/restoring during a running job; visible Claude auto-fix usage notice; CLI project/build/port errors and help; safe CLI starter names and YAML titles; first-run documentation and actionable print instructions.
- Fixed baseline support issues: reusable UTF-8 environment settings, explicit UTF-8 in the firmware test stub, circuit I/O audit formatting, and missing architecture/toolbox documentation. No catalog values, geometry, review.json files, check thresholds or test assertions were changed.
- Evidence: a compressed Studio contact sheet in docs/usability/2026-11-02/; the full 60-pair desktop/phone/light/dark capture is linked in PR #1. Findings and per-item fixed/not-fixed reasons are in FINDINGS.md there. The standalone viewer tabs and section controls were also inspected; their raw technical check notes are recorded for the shared check-wording work.
- Left untouched as requested: Studio Checks wording, Follow live, Work tab and cleanup. Native Mac execution, paid Claude design jobs and physical printer sends were not run here; relevant browser/API/shell behavior was validated without those external actions.
- Not fixed: pre-existing PCA9685 proxy-height assertion versus below-board pins; KST X08 Plus 1.5 mm mounting hole versus M2 screw. These need engineering review/sourced hardware corrections, not looser checks or altered catalog dimensions.
- Setup: ./setup.sh finished ALL OK; servo_link complete build PASS; installation/startup instructions saved in the environment draft. Initial full test run: 707 passed, 12 failed, 5 skipped; UTF-8 resolved locale failures. Targeted suites passed (77 Studio/CLI/docs checks, 39 mode/print/skill checks, 67 guard/Studio checks, 32 CLI compatibility checks). Final full suite: 754 passed, 2 pre-existing failures (listed above), 5 optional firmware checks skipped. PR #1 rebased on current main: 150 affected tests passed, 5 optional firmware tests skipped. Marked ready under Spencer’s review instruction; do not merge without his or a Claude session’s review.

- PR #1 review follow-up: reduced screenshot history to one 152 KB Studio contact sheet; full capture linked in the PR discussion. Rebased again over main’s thought-web and Mac-launcher work, retaining both STATUS entries. The stream regression test now asserts the unchanged visible lines and the complete new upstream note/tool metadata; no geometry or safety assertions changed.

## 2026-11-02 19:45 UTC - Codex PRs #1 + #2 merged; manager live (planning chat)
- Reviewed and merged Codex PR #1 (first-use Studio layout, recovery, CLI guidance) and PR #2 (honest viewer previews,
  supplier/plate links, device mass split): nothing loosened (range checks got stricter: one-sided limits + finite
  only; one stream test rewritten to assert more fields), 520 KB of contact sheets only. 92 affected tests pass.
- Kerf manager (scheduled, every 3 h at :51, auto-approved) is live; its first run wrote docs/status/BOARD.md. Its
  prompt now finds unmerged PRs by "head not on main" (GitHub listing showed none while two were open).
- Blocker for Spencer: the ChatGPT Codex environment "kerf-forge" will not publish ("Couldn't publish environment",
  no reason shown; settings saved, full internet on). Until it publishes, Codex runs one thread: usability rounds,
  then docs/status/CODEX_TASKS.md items in order.

## 2026-11-02 — Repo cleanup, ChatGPT Codex
- Audited tracked files, generated/cache/scratch paths, large binaries, project part/helper references, engine imports and claims. Earlier cleanup and PR #1's screenshot trimming already removed the safe candidates; no additional deletion was justified. Kept the sourced STEP models, offline viewer bundle, six README renders, helper modules, audit/prototype/provenance docs and open-task claims because they have live references. Detailed retention reasons: docs/status/REPO_CLEANUP_2026-11-02.md. No history rewrite, geometry edit or review.json edit.
- Added ignore rules for full-size usability images while retaining compressed contact sheets, plus regression guards against tracked build/cache/scratch files, excess evidence size and missing README render links. Catalog dependency manifests, lockfiles, source/import models and batch records remain trackable.
- Validation after pulling concurrent engine improvements: 6 targeted hygiene/claims tests pass; no full suite or all-project builds were run. No files were removed in this round. The audit closes the remaining cleanup item without manufacturing deletions. Next: Firmware proven, if its claim is available; PRs remain for independent manager review/merge.

## 2026-11-02 20:35 UTC - Codex cloud environment published (Claude)
- The first `kerf-forge` Codex environment was stuck: every publish failed and the draft never kept its settings. It is deleted (Spencer approved); a fresh one is **Published**.
- Settings: install script `cd /workspace/kerf-forge && mkdir -p .cache/{uv,python,npm,playwright,xdg,matplotlib} && ./setup.sh`; full public internet; environment variables put the uv/npm/Playwright/XDG/matplotlib caches under `/workspace/kerf-forge/.cache` (gitignored, so the setup's downloads are still there when a task runs), `CC=gcc CXX=g++`.
- Validation: `./setup.sh` exit 0, `kerf doctor` ALL OK. Warning only: in that sandbox the Arduino core download failed and simavr is missing, so `kerf firmware-check` reports NOT RUN there (whoever holds "Firmware proven" should make setup.sh install simavr or note it).
- No new Codex chats started: open Codex PRs already cover the planned tasks (#4 parallel tests, #5 catalog fingerprints, #6 generated outputs/.gitignore, #3 setup retries); "Firmware proven" is claimed by another session. The Kerf manager reviews and merges them.
- 15:35 Mac app, found on Spencer's Mac: the native app never built because KerfStudio.swift did not compile with his
  Swift (`loaded ? web.reload() : startServer()`: WKNavigation? vs ()), so the old new-window-per-click launcher stayed.
  Fixed (if/else), install_app.sh now falls back to the single-window launcher if the compile ever fails, and
  `tools/mac/Update Kerf Studio.command` (double-click updater) refuses to restart the engine while a Studio job runs
  (the first run of it stopped the Hawk-fold design job; its files were kept: hub.py, DESIGN.md uncommitted on the Mac).

## 2026-11-02 15:25 UTC-5 — drone_foldable_wings: hub root ends faired for the folded mode (Studio request, Spencer)
- Request: hub_r / hub_l's faces where the wing meets the fuselage at full spread face forward when folded and must be
  aerodynamic; keep the aero good at every sweep angle. Folded, the hub's flat root face (y = pivot_y) IS the wing's
  leading edge: at 70 deg it met the flow 20 deg off square, a 206 x 20 mm slab.
- Done (parts/hub.py `root_cap`, collar trim; DESIGN.md hub contract): every chord station of the root face gets a
  half-ellipse nose reaching min(1.25 x local half thickness, 10 mm) inboard (never past y 16), from the LE to x 166,
  fading to a 0.3 mm lip; the collar's inboard flat cut (y 16) is now a half round (its trim aft of the pin stays at
  y 26: that part swings inboard). Flat area within 30 deg of square to the flow at 70 deg fold: 2803 -> 111 mm2 (the
  thin root strip aft of x 166); 0 / 35 deg unchanged (11 / 0 mm2). hub 76.9 -> ~81 g each, AUW 1582 -> 1590 g.
  Builder note (assembly_note): sand the nose's lower half after removing the tree supports.
- Design review (review.json, FAIL) found one real problem in the first version: past full spread the nose reached the
  spine ridge at -1.2 deg, before the stop post bites (~-1.4 deg; the sweep check only covers 0..70 and hard_stop only
  compares aft_fuse with the hub). Fixed: where the ridge is, the reach is held 0.5 mm off it with the panel 3 deg past
  spread (the stop_spread_* angle). Measured nose-to-spine gap: 4.1 / 2.5 / 0.45 mm at 0 / -1.4 / -3 deg, no overlap.
  Ridge width and opening x moved to layout.py so hub, spine and aft_fuse read the same numbers (values unchanged).
- Tried and dropped (scratch FEA): a nose running into the collar, or a collar without its inboard half, made a stress
  notch (hub_fea p99.9 31-40 MPa); a nose ending at x 176 sat on the 2.4 mm ligament inboard of the aileron lead
  channel (local max 15 -> 18 MPa); ending at 166 leaves that ligament as it was (max 15.2, low stress at the new end).
- Check: the same pre-existing failures as before the change, none about the root faces: wiring routes through parts,
  aileron lead length, KiCad symbols missing, deck_fea (meshing error), spine_fea 53.6 MPa, hub_fea. hub_fea reads
  24.3 MPa p99.9 (was 25.8, limit 17.5), deflection 8.1 mm (was 7.8, limit 1.0): NOT a strength change - the nose adds
  lightly loaded elements that move the percentile, and the mesh differs (reviewer compared the fields). Fold sweeps
  clear; sm_*, stall, wing loading, spar, fold moments within 1 %.
- Open (not this change): the V keel under the root still crosses the folded flow as a 45 deg ramp (reviewer: wrap
  the nose down over it for x 130-176, which would also deepen the section where hub_fea fails); moving the aileron
  lead exit >= 3.4 mm behind the root face would let the nose run into the collar; the 0.3 mm lip is under one line
  width (harmless). Engine gap: nothing checks that OTHER parts stay clear during a stop's over-travel (hard_stop
  could report any part that collides before the stop pair does). Drone PLAN item stays open (claim released).
- Re-review (review.json, fingerprint 93aa0e4d, FAIL on pre-existing blockers): the fairing's major is fixed (0.451 mm
  at -3 deg, both sides; ligament back to its old stress). Fairing minors left open: no requirement guards that
  over-travel gap (needs the engine feature above); the nose plan has a 1.4 mm wave at x 100-135 (taking the running
  minimum of the ridge limit from x 95 aft would level it); keel wrap / lead exit as above. New pre-existing findings
  for the drone's owner: spine ridge fillet meets each hub boss at zero clearance; hub and spine stressed past their
  15 % infill lattice (kerf/infill.py, new engine check).

## 2026-11-02 21:00 UTC - Kerf manager: first batch verify was OOM-killed; fixed
- `tools/batch_verify.py run` died (exit -9): `kerf verify` built all 11 projects in one process and grew past 6 GB
  (kernel OOM on a 7 GB cloud box). verify now builds each project in its own child process (`_run_isolated` in
  kerf/cli.py), so memory is freed between projects; tests/test_verify_isolated.py. Nothing about what verify checks changed.
- Session names by task are on docs/status/BOARD.md (app session titles can't be renamed from a cloud run).

## 2026-11-02 — Reviews go stale only for real changes, ChatGPT Codex
- Main already tracked the catalog entries read by check/build. Fixed the remaining live-process gap: the parsed catalog refreshes when its file changes (identity/size/nanosecond modification/change times), so a used-entry edit invalidates a fingerprint in running Studio without manual cache clearing. Unused-entry edits and JSON reformatting leave scoped fingerprints unchanged; unchanged reads still reuse parsed data.
- Missing/malformed dependency manifests conservatively hash the full catalog and the next check repairs them. Valid manifests retain the existing growing union so quick checks cannot drop full-build dependencies. No project geometry, review.json, catalog dimensions, limits or checks were edited. The docs regression exposed a missing `req` table entry; the later main refresh now supplies it and its wording was retained.
- Validation: 55 dependency/cache/engine/calibration/docs tests passed, plus 70 catalog checks. The one previously documented PCA9685 below-board-pin height test was explicitly deselected from the catalog run, not changed or presented as passing. New regressions cover live same-size/restored-mtime edits, atomic replacements, missing used entries, malformed manifests, local design-input changes, quick-check unions and cache-hit dependency replay. No full suite or all-project build/test was run.
- Ready PR for independent review/merge. Next in Spencer's queue: Repo cleanup, then Firmware proven, checking active claims first. Claude now reports the replacement environment Published; this original instance does not establish fresh-task restore validation.

- Latest-main refresh for review fingerprints: merged current engine/Studio changes, retained their architecture/STATUS additions, and reran the 55 dependency/cache/engine/calibration/docs tests: all pass. The original 70 catalog proxy checks remain the earlier targeted result; the documented PCA9685 assertion stays untouched.

## 2026-11-02 (Claude, beginner visualizer)
- Done and pushed: plain-language job narration; workshop stage scene in the job panel; kerf/glossary.py (plain name + meaning for all 43 checks, ~60 terms) with jargon underlines, plain check names in tables and cards, "📖 Words, explained"; Tune "can move: …" and ▲▼ better/worse in tried-vs-saved; Files tab one-liners; "?" Explain-this-page spotlight tour (first-run tour once, skipped for automated browsers); ready-to-print certificate (only for a current passing build, says "independent review: not done yet" when so).
- Activity now lists sessions working on a project from fresh claims (☁ title · N to fix · last active); the Checks banner shows that session's latest commits. A claim covers the whole PLAN item, so per-problem ownership isn't known; the banner says so.
- Not mine, seen while testing: tests/test_studio.py::test_progress_events_are_off_by_default_and_ordered_when_on fails on main (req event order vs start.reqs, after the "check in order of redesign cost" change). Fixed docs: `kerf req` was missing from the ARCHITECTURE CLI row.
- Next: 3D guided tour, History comic strip, new-design briefing room.

## 2026-11-02 (Claude, realistic limits)
- Done: `advisory: <why>` requirements (a miss is a warning; refused on strength checks and without a reason; Studio shows "MISSED · advisory"; the optimiser and problem cards ignore it); thin-wall minimum 0.8 mm only on load-carrying parts (named by a strength check or `structural: true`), others down to one 0.42 mm line as a warning (Bambu Studio default line width, https://forum.bambulab.com/t/default-line-width-of-0-42/20400); squashable items `compress_mm` + `compress_why` (press-in depth measured, deeper = collision). tests/test_realistic_limits.py; docs + kerf skill.
- No existing limit was loosened; every project's results are unchanged until its yaml opts in.
- Candidates not done (need sources or design work): crash energy budget with bumper credit, vibration as stiffness target + filtering note, infill-aware FEA, single overall safety factor, A2L-calibrated motion clearance.

### 2026-11-02 (session 4c4e3822c9): E7 fpv_wing DONE
- `kerf build fpv_wing` PASS (fingerprint 3379006ef48d4ba7), design-reviewer PASS (round 5), evals/fpv_wing acceptance PASS.
  1 m 6S flying wing, 1,361 g AUW, TWR 1.53, ~16 min, SM 9.2 %, wing loading 73 g/dm2, stall ~40 km/h.
- Review rounds 3-5 fixed: hatch flutter (mid-length screws + ribs), antenna clash, pushrod exit slot, outer elevon play
  (second CF rod, reamed push fit), pod alone on its plate (engine: parts >= 150 g print alone), builder notes in
  ASSEMBLY.md (engine: held_by at each step, item tools in the tools list).
- Open minors are one PLAN item ("fpv_wing follow-ups from review round 5").
- Speed audit findings (12 + preflight) reported to Spencer; waiting on his go before implementing.

### 2026-11-02 — Engine speed: redesign-cost order; prop_clearance 7x (session 01S68R6R)
- `kerf check` / `kerf build` run concept + core-structure requirements first (requirements.REDESIGN_TIER,
  redesign_order) and stop before the detail checks when one fails; `--all` runs everything. `--quick` includes the
  core FEA (explicit sketch / print modes still skip FEA). Skill + design-reviewer follow the same order.
- prop_clearance's gap screen: branch and bound on the mesh instead of 1 mm subdivision of every surface.
  drone_foldable_wings: 173 s -> 25 s, same reported 27.5 mm (reported gaps are exact OCC distances).
  A first attempt (prune + 1 mm subdivision) gave no speedup (163 vs 162 s) and the profile had misattributed the
  cost; the direct profile showed long thin wing triangles subdivided into ~1e5 pieces each.
- Open on drone_foldable_wings (found by `kerf req`): spine_fea 53.6 MPa vs 16 MPa allowed - spine needs redesign.

## 2026-11-02 (Claude, realistic limits 2)
- Done: near-miss scale on failed requirements (`requirements.miss_scale`: near miss <= 5 %, close <= 20 %, far off); kerf/infill.py (stress deeper than the walls vs the infill lattice, 0.3 x infill^1.5, Ashby 2006; warning; modifiers may carry a `box`); impact_fea `bumper:` (Gent & Lindley pad stiffness, no credit past 20 % squash, Gallagher 95A).
- Reviewed, unchanged: natural_freq already checks the hover rotor and blade-pass rates against a cited 20 % separation; use-story checks only run for listed hazards; thrust already scales test voltage to the pack.
- servo_link's arm now warns on infill strength (3 % of its volume over the lattice limit near [6.7, -8.1, 4.3]): a boxed 100 % infill modifier or more walls; left for the project's owner.

## 2026-11-02 16:20 UTC-5 — Firmware proven + Electronics as a real circuit checked off (Claude, Spencer's session)
- Code was pushed 2026-11-01 (44df72e firmware, b846908 circuit); this pass verified it on the current tree (batched
  testing: targeted tests only). `pytest tests/test_fwcheck.py tests/test_firmware.py tests/test_circuit.py
  tests/test_electrical.py`: all pass with the real toolchain (arduino-cli 1.3.1 + arduino:avr 1.8.6 + simavr; 26 in
  fwcheck+circuit, incl. the broken-sketch FAIL test and schematic PDF). `kerf firmware-check robot_arm`: PASS, Nano +
  PCA9685, 11210 B flash, every joint's simulated sweep inside its range (e.g. grip ch4 -32.4..31.8 of +/-32.5 deg).
- Note: without arduino-cli + core installed (e.g. the Codex sandbox) the real-toolchain tests skip and
  firmware-check says NOT RUN, never PASS. Both items are in the next batched full run.

## 2026-11-02 (Claude, specific advice)
- kerf/advice.py: every failed requirement gets advice sized from its own numbers (beam-theory section change, catalog materials / servos strong enough, stiffness for frequency, CG shift, wing area, capacity, gear face ...); overlaps say depth, axis, position and which part gets the pocket; joint collisions give the angles and where to end the range. Cards show "What to do" + alternatives; `kerf check` / `kerf req` print "->" lines. Verified end to end on a tightened scratch copy of servo_link (servo pick DS3218/DS3225, bracket 27 % thicker or reorient, mass items from the requirement's include list).
- Couldn't run drone_foldable_wings here: `kerf check --quick` is killed for memory in this container.

## 2026-11-02 21:25 UTC - Kerf manager
- Spencer: hold the full batch test until the other sessions finish. The second run (with the fix) was
  stopped mid-way and its lock removed; BOARD.md says the batch is on hold. Next manager run starts it once no claims
  are active.
- (01S68R6R, later) FEA memory halved: kerf/fea.py builds the intorder-4 stress basis per chunk after the solve and
  sums the stiffness per chunk with int32 indices. drone_foldable_wings mount_fea (70k tets) OOM-killed a 7 GB machine
  (so its full check could never finish there); now 2.7 GB peak, same stresses. MAX_TETS comment corrected.

## 2026-11-02 (Claude, user-facing bug sweep)
- Fixed: auto-fix / Fix no longer start on a project another session holds (they wasted a Claude run that then stopped); Save / Restore / materials / Change something ask before changing such a project (409 `claimed`, `override: true`); switching projects asks before dropping unsaved Tune values; a second Build/Check click opens the running job instead of an error; typed names are cleaned (`studio.slug`: "Hawk Drone" -> hawk_drone) and auto names avoid existing projects; Tune Reset clears material picks too; "1,5" reads as 1.5; a wrong printer access code now says so (was "serial right?"); spaces in a pasted code are ignored. tests/test_user_bugs.py; test_studio's bad-name case now uses "9 Bad!" (a name that can't be cleaned).
- Seen, not mine: running test_studio.py together with the other Studio browser test files in ONE pytest process died with exit 141 after ~44 tests (each file alone passes); worth a look if the batch shows it. test_progress_events_are_off_by_default_and_ordered_when_on still fails on main (noted earlier).
- (Claude, 2026-11-02 later) Mac updates no longer stall on local changes: tools/mac/update_repo.sh (used by start.sh and "Update Kerf Studio") sets aside local edits that don't touch the incoming files, fast-forwards, puts them back; overlapping files block the update with their names instead of silently staying on old code. Test in tests/test_mac_launcher.py.

## 2026-11-02 22:00 UTC - Kerf manager: usage-limit awareness (Spencer: "pause before starting something that will be cut off")
- tools/budget.py: shared budget switch (`stop "<why>" [--until UTC time]`, `resume`, `status`; claims/budget.json,
  pushed; local .claude/state/BUDGET_STOP still works). While on: `claims.py next/take` refuse, the batch run waits.
- Batch run waits until other sessions are done (Spencer): `batch_verify.py status` prints HELD instead of DUE while
  any other session holds a fresh claim; the last one to finish runs it.
- `kerf verify` checkpoints each finished step (pytest, each project) for the commit, so a run cut off by a limit or
  a kill resumes instead of redoing ~1 h of work.
- NOT done, needs Spencer's go-ahead: the Stop hook letting a session stop while the budget switch is on (hook edits
  were refused as self-modification). Until then a budget stop still makes sessions want a free item.
- Tests: tests/test_budget.py (4), test_claims.py (copies budget.py), test_batch_verify.py, test_verify_isolated.py pass.
## 2026-11-02 — Repo cleanup, ChatGPT Codex
- Audited tracked files, generated/cache/scratch paths, large binaries, project part/helper references, engine imports and claims. Earlier cleanup and PR #1's screenshot trimming already removed the safe candidates; no additional deletion was justified. Kept the sourced STEP models, offline viewer bundle, six README renders, helper modules, audit/prototype/provenance docs and open-task claims because they have live references. Detailed retention reasons: docs/status/REPO_CLEANUP_2026-11-02.md. No history rewrite, geometry edit or review.json edit.
- Added ignore rules for full-size usability images while retaining compressed contact sheets, plus regression guards against tracked build/cache/scratch files, excess evidence size and missing README render links. Catalog dependency manifests, lockfiles, source/import models and batch records remain trackable.
- Validation after pulling concurrent engine improvements: 6 targeted hygiene/claims tests pass; no full suite or all-project builds were run. No files were removed in this round. The audit closes the remaining cleanup item without manufacturing deletions. Next: Firmware proven, if its claim is available; PRs remain for independent manager review/merge.
- Cleanup refresh after the later Studio/engine merges: all 6 hygiene/claims tests still pass; retained the new source/test files and all other sessions' changes. The original file-count figures are explicitly identified as the audit's starting snapshot.
## 2026-11-02 — Firmware proven, ChatGPT Codex
- Reproduced and fixed Arduino CLI's cloud download failure: it ignores standard HTTP(S)_PROXY unless copied into ARDUINO_NETWORK_PROXY. Setup and checker now use that supported setting, preserving explicit overrides. The pinned CLI/core/Servo/PCA9685/BusIO downloads installed successfully with TLS/checksums unchanged. This non-root container has no sudo: downloaded simavr 1.6+dfsg-3+b3 from Debian's signed trixie index into a private cache and linked the real harness there. No package/cache/binary files are committed; no setup rerun was needed.
- Fixed proof gaps: check every matching sketch folder, retain individual results, fail if any fails, keep compiled-only distinct from PASS, and handle tool errors/timeouts without abandoning later sketches. Generate mixed Nano-direct/PCA9685 outputs correctly, check each at its existing tolerance, and keep PCA channels out of Nano Servo-slot allocation. PCA programs now also detect unwired Nano-pin pulses. Quotes, backslashes, newlines and Unicode in generated C++/Pi labels are safely encoded; Pi's temporary PWM tree is cleaned after each run. No engineering limits, model assumptions, catalog values or assertions were loosened.
- Validation after pulling/rebasing on current main: 55 targeted firmware/setup/docs/CLI tests pass, with no skips. The real compiler/simulator tests (previously five skipped here) include deliberately broken compile/overtravel/Pi cases, a broken second sketch, mixed outputs, 12 PCA channels plus a direct Nano servo, unwired output, label escaping and pipeline result recording. `kerf firmware-check servo_link` returned PASS: 7,858-byte Nano program; D9 centre 1499.94–1500.12 us, sweep -88.92..88.90 deg within +/-90. No physical hardware, paid service, full suite or all-project build was used. Guide and detailed scope: docs/FIRMWARE_CHECKS.md.
- Queue delivered as one PR per item: #4 Fast tests, #5 catalog review fingerprints, #6 cleanup audit/guards, and this Firmware proven PR. All are for independent manager/Spencer review and merge; Codex does not merge them. Release each completed claim. Refresh older open PRs against concurrent main changes before ending.
- Publication update superseding this thread's earlier blocker: Claude's latest main entry reports the replacement cloud environment Published and setup/doctor validated. This thread remains attached to the original instance; Codex has not independently validated a fresh restore of the replacement. The firmware proxy fix addresses the download issue recorded in that publication note.
- Firmware review refresh: merged the later main Studio/CLI changes, retained their architecture/STATUS text, and reran all 55 targeted firmware/setup/docs/CLI tests: all pass, no skips. All four queued task PRs are ready for independent review; no self-merge or full-suite run.
## 2026-11-02 — Codex-aware Work overview (Codex, delegated design + data work)
- Work now combines main-branch shared claims, repository-scoped Codex session summaries and Studio jobs. Task rows
  show owner, activity, source freshness, attention state, real checklist/stage progress, remaining steps and time
  estimates only when comparable Studio run history exists. Search, assistant/state filters, project navigation,
  expandable scope, recent changes, keyboard focus retention and phone/light/dark layouts make it easier to scan.
- Codex discovery uses read-only app-server list/turn APIs with bounded reads and a 30-second cache; it never starts
  or resumes a chat. Live proxy preferred; this Mac has no live control socket, so saved history is clearly marked
  and never treated as running. Cloud work is represented by shared claims. Old claims without runtime metadata
  remain Session; future claims/heartbeats record explicit Codex/Claude identity and may include a short activity.
- Explicit thread links deduplicate ownership and retain multiple claimed tasks without inflating running counts.
  Missing progress/estimates stay unknown; failed refreshes retain stale data. Main-branch claims stay visible from
  feature branches. Cache invalidation during a slow session read cannot break the response.
- Verification: 28 targeted tests passed (including browser scenarios at 1440/390 px, dark/light, filters, recovery,
  keyboard focus and contrast). Real app-server/history and Studio API/browser smoke succeeded; this Codex task
  appears with its shared claim and current activity. Independent review issues fixed and covered. Screenshots in
  .cache/work-ui use sample tasks, except work-live-1440.png which captures local data. No full-suite/hardware run;
  full batch verification remains with the manager (now on hold). No catalog, geometry, check threshold or review edits.
## 2026-11-02 — Reusable assembly instances (Codex, module-library)
- `kerf modules [name] [--json]` exposes a source assembly's interfaces, parameters, inherited requirements and
  actual `review-status`. `kerf new <name> <title> --module servo_joint` copies an independent editable bench servo
  joint from servo_link, retaining the base, power/wiring, fasteners, every load case and YAML engineering comments.
- Explicit source-file manifest; all part/layout/sibling helpers and imported/mesh assets required; path escapes,
  symlinks and existing targets refused; a failed copy cleans up only its new folder. `MODULE.md` explains limits;
  `module.json` archives source hashes and the full historical review. Outputs/caches/review.json are never copied.
- **46 targeted tests PASS** (test_modules, test_cli_usability, test_docs), including real geometry/joint/torque,
  independent editing, name/path safety, omitted dependencies, 3MF support, title escaping and failed-copy recovery.
  Doctor ALL OK using the existing shared environment; optional Arduino/simavr remain unavailable on this Mac.
- Full `kerf check` on a scratch instance PASS in 28.4 s: 0 overlaps, 12 aligned screws, swing clear over +/-90 deg,
  all 8 requirements PASS (bracket FEA 0.63/13 MPa; arm 4.67/24 MPa). No new geometry or thresholds changed.
  Existing warnings remain: jack has no mass; two servo screws need a ball-end key; circuit ERC NOT RUN for psu/jack
  missing pin tables; bracket overbuilt and 4 sharp inside corners; arm infill lattice reaches 1.5x its local limit.
- Source's historical PASS fingerprint 57044319cfe478bb differs from current ddf0ee5d392760f4: explicitly stale,
  never presented as current proof. The new instance is unreviewed. No full build/render/review, full suite or
  physical hardware run. The batch remains on the owner's hold. Parent review found and resolved imported-asset
  dependency closure; no remaining finding. Only the precise workflow subitem is done; other families/composition
  and current independent source reviews remain open.

## 2026-11-02 21:55 UTC - Kerf manager run
- Merged Codex PRs #5, #6, #7, #9, #10 after reading the diffs and running their targeted tests (all pass;
  STATUS.md conflicts resolved by keeping both entries). #3, #4 need a rebase on main; #8 must move its CLAUDE.md note.
- Blocker for the batch: tests/test_catalog.py::test_board_proxy_keeps_mounting_holes_clear already fails on main.


## 2026-11-02 — Scenario comparison in Studio (Codex, scenario-intake)
- Added a scoped problem-first route to the existing New design/quote flow: success criteria, priorities and hands-on
  effort; researched buy/adapt/build alternatives with fit, risks, source findings, next steps and recommendation reasons.
  Unknown costs/print times stay null and visibly unknown. Existing architecture quotes remain readable.
- The server resolves the saved selected option, rejects changed requests and unanswered blocking questions, and never
  starts a design for a buy-only option. Buy options provide links/next steps; no purchase or printer action. A duplicate
  quote cannot erase active output: original-request capture and output reset use start_job's existing preparation lock.
- 33 targeted tests passed (scenario validator/API/browser, legacy quote/intake/readiness and package-map coverage).
  Desktop 1440 and phone 390, both themes: no browser errors, no horizontal overflow, research links retain keyboard focus.
  The new browser coverage found/fixed long example buttons overflowing on phones. Read-only doctor: ALL OK; optional
  Arduino/simavr tools remain unavailable. Reused the existing environment instead of reinstalling into the shared venv.
- PLAN's Studio subitem is complete; full E8 and scenario requirement checks remain open. The plant-care comparison
  fixture and screenshots are explicitly illustrative, not vendor research, engineering acceptance or a working project.
  No paid Claude generation, physical hardware, full suite, project geometry or review.json was used/changed. Full batch
  remains on the manager's hold. Independent review requested before delivery.

- Scenario PR #11 review: independent parent code and final desktop/phone dark/light screenshot review found no actionable issues in the scoped change. All 33 targeted tests pass again after current-main integration. Full E8 remains pending.

## 2026-11-02 22:05 UTC - Kerf manager
- Merged PR #11 (scenario options; tests/test_scenario.py pass). test_studio's progress-order
  test already fails on main; PR #4 fixes it once rebased.

## 2026-11-02 22:30 UTC - Stress simulations paused (Spencer: "pause all the stress simulations, we will work on that later")
- PAUSED.json at the repo root switches off every FEA-backed check (fea_static, impact_fea, stop_impact,
  natural_freq, drop_impact, weak_link: kerf/requirements.py STRESS_SIMS). They show "PAUSED (stress simulations
  off)", value NOT RUN, and the report warns "strength unproven" - never a pass value. KERF_STRESS=1 runs them once;
  delete the key to resume. Analytic strength checks (cantilever_stress, spar/gear bending) still run.
- PLAN: the 4 FEA items (arm_resonance, impact_fea/stop_impact, arm_breaks_first, creep/flex_strain) are marked
  "PAUSED:"; `claims.py next` and the Stop hook's free-item test skip them (`take` can still claim one).
- Verified: `kerf check servo_link` PASS in 9 s with bracket_fea / arm_fea PAUSED and the warning;
  tests/test_stress_pause.py (3), test_claims.py, test_budget.py pass.
- (01S68R6R, later) Stage timing of a full drone_foldable_wings quick check (--all, 19 min, 3.1 GB peak): two
  clearance_min requirements were 720 s of it. geom.mesh_gap screen -> ~72 s, same exact value. Printed mass now
  cached per shape + spec (~45 s per check). Next hotspots from the same run: core FEA ~300 s (6 parts), print stage
  68 s, fit 23 s.

## 2026-11-02 (Claude, visual pass)
- Screenshotted every Studio screen (project tabs, failing checks, new design, My parts, Work, all projects, printer, light theme, 900 px window). Fixed: in a small window the sidebar's Activity list drew over the page (sidebar now clips, its list scrolls); header buttons compact so the tagline fits in two lines; Files tab label "Optimiser results" instead of out/OPTIMISE.md. Mac installer now keeps exactly one Kerf Studio Dock tile (tools/mac/dock_dedupe.py).
- test_studio's auto-fix test no longer depends on live claims (a claim item containing the word "bad" made it flaky after the claim guard).

### 2026-11-02 (session 4c4e3822c9): viewer "Build it" tab
- Labels sit beside the part they name (right / left / above / below, the first that fits) and are pushed apart.
- Camera: 48 more candidate views (every 30 deg at 15-75 deg up), scored on the new part not being hidden, sliding
  across the screen, and how much of its broad faces the view shows (no edge-on plates).
- Close-up: a small part (or one side of a far-apart left/right pair) is framed with some build round it instead of
  the whole device (fpv_wing 3 mm elevon rods, horns, GPS now readable).
- Bench steps keep the build they join on screen, faint, instead of the bench parts floating alone.
- tests/test_viewer_build_it.py (browser): label clear of its part, close-up, bench context.
- (01S68R6R, later) drone_foldable_wings quick check end to end (--all; FEA paused by Spencer, as this morning's quick
  check had no FEA either): 17 min this morning -> 109 s warm, 224 s right after an engine edit. clearance_min now
  skips the exact distance when the mesh gap clears the limit by > GAP_SCREEN_MM (fold-tail pair 72 s -> 18 s).
- (01S68R6R, wrap-up of the speed round) Warm drone_foldable_wings quick check ~75 s: build 5, concept reqs 6, print
  0 (cached), fit 21 (interference 11.6, hex_key_reach 9.0: spread over tessellation -> build123d Vector conversion,
  no single hotspot), fold-tail clearances 15, prop 7 + load. Tried and reverted: reporting a mesh-refined prop gap
  (20.06 vs exact 20.00 broke test_swinging_prop_is_swept's +-0.01 hand calc; reported gaps stay exact). Left, each a
  few s: tessellation straight to numpy in geom.mesh (skip build123d Vectors), a warm check server (~7 s startup per
  command), cold part rebuilds after engine edits (~180 s, fillets in part code).

## 2026-11-02 22:45 UTC - "How Kerf decided" readable and steerable (Claude)
- Replaced the force-directed thought web (it never settled, so it shook, and labels overlapped / were cut at 46 chars) with a calm trail read top to bottom: 1 You asked (the whole request) -> 2 What it looked into (one card per question: Looking now / Kept coming back / Looked at / Not pursued + why, "Found:" its notes, its sources as links, follow-up questions inside) -> 3 What it decided (each option Chosen / Set aside with why, and "Came out of" the research it rests on) -> 4 What it's building (parts drawn as one step with chips, then tests). Nothing moves except new items fading in; light, dark and phone width checked in screenshots.
- DESIGN.md option parsing: reasons no longer read "chosen." (marker words stripped), and unmarked items of a list with a chosen one count as set aside (fpv_5in, pan_tilt now show all their alternatives).
- Job panel: a one-line strip (stage, current question, counts, latest finding) appears by itself when research starts and stays visible when the panel is folded; it opens the full trail.
- Steering (kerf/steer.py, .claude/hooks/steer.py): Focus / Skip on each question while it is still researching, plus a "Tell Kerf" note. Delivered as extra context on the job's next tool result via a PostToolUse hook that only starts for a Studio job with a steering file: no extra turn, no pause, nothing at all when unused. The trail shows "Kerf has it ✓" once delivered; steering resets with each new job and is refused once the job has finished.
- Tests: tests/test_thoughtweb.py (8 pass: layout still between polls, no label overlap or clipping, strip auto-opens, steer API + hook end to end, reset per job, options link to research). Pre-existing failures NOT from this change (they fail on main without it too): test_studio.py::test_progress_events_are_off_by_default_and_ordered_when_on (requirement order changed by the "check in order of redesign cost" commit) and test_studio_features.py::test_duplicate_copies_design_files_only_and_renames.

## 2026-11-02 17:45 UTC-5 — for Spencer: Studio single-change jobs vs the Stop gate
- A Studio change request says "do exactly this change ... do not start other PLAN work", but .claude/hooks/stop_gate.py
  only lets a session end when every open PLAN item is claimed by others (or on BLOCKED / YIELD / 60 blocks). So a
  finished Studio job (this one: drone_foldable_wings hub fairing, all pushed, claim released) keeps getting told to
  `claims.py next`. I followed the job's instruction and did not take new work, and did not write BLOCKED/YIELD (both
  would be false). Suggested hook change, needs your go-ahead: let a Studio job end once its own work is committed,
  pushed and claim-free (e.g. Studio sets an env var or a .claude/state/STUDIO_JOB marker that stop_gate honours).
- (Claude, 2026-11-02, notifications) Clicking a notification opens what it is about: pop-ups carry a target (`kerfOpen`: project:<p>:<tab> / job:<id> / new; failures open Checks, tries Tune, builds 3D); the Mac app posts real desktop notifications (UserNotifications) that call kerfOpen on click, and the server's osascript one (which opened Script Editor) is skipped while the app is open; jobs that finish while not watched now notify too; Activity rows open their project. tests/test_notify_targets.py.

## 2026-11-02 — Complete declared source downloads (Codex)
- Reproduced omitted nested Python/CSV helpers and declared STEP input in a synthetic Studio download. Source ZIPs
  now retain recursive Python helpers, part/layout/import/Meshy inputs and explicit project.yaml source_files; data
  reads are declared, not inferred by executing or scanning Python. Shared the existing module containment check;
  module manifest policy and generated maker loops/constants remain unchanged for concurrent supplier/BOM work.
- Selected inputs must exist and remain contained with no symlink components; hidden/cache/output/review/known
  credential files are refused. Malformed YAML/UTF-8 and missing inputs return a useful 400 error before an archive
  is sent. The original files stay unchanged; no review approval/build cache is copied into the design folder.
- 39 exact archive/source/module tests PASS in 3.08 s. An extracted synthetic design rebuilds its nested helper,
  declared CSV, layout and imported STEP after deleting the original (body 42 / lid 24 mm3). Parent review found the
  malformed-contract case; its two HTTP regressions plus rebuild/package-map checks PASS (4 tests, 1.94 s).
  Docs explain declared dependency limits; no actual project build, full batch, FEA or paid model call.
- Separate saved follow-up: existing maker-output loops can follow output symlinks; their containment repair is
  assigned separately. This change validates design inputs and intentionally leaves maker-output behavior intact.
- Completion is the source-export child only; the broader Fresh-eyes usability task remains open.
