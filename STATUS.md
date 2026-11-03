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

## 2026-11-02 — Studio cancellation keeps its project locked (Codex)
- A Stop request, or an authentication/trust hint, used to publish a terminal job state before the child process
  exited. Builds, trials, parameter/material saves and restores could then overlap that process's remaining writes;
  Studio's busy/quit/watchdog guards also treated it as finished.
- Job now records the requested outcome privately, keeps the existing running state while draining output and
  waiting for exit, then publishes stopped/failed. Manual Stop logs that it is waiting; repeated stops preserve the
  original outcome. No new UI state or dependency.
- `tests/test_studio_lifecycle.py`: real children acknowledge SIGTERM but wait for a release file. Both manual and
  auth-failure cases reproduced the bug before the fix; afterward, conflicting jobs/trial preparation stay blocked,
  another project remains available, cleanup output is retained, and a graceful exit preserves stopped/failed.
- Verification: 68 targeted Studio/usability/lifecycle tests passed; the existing progress-order test is excluded
  because PR #4 already fixes that separate main-branch regression. `kerf doctor`: ALL OK (optional Arduino/simavr
  tools remain unavailable). Independent code review found no actionable issues. No full suite or hardware run.
- Resource review saved and reread in CLAUDE.md: keep the current subprocess/progress design; revisit only for
  jobs that must survive Studio restarts or run across machines. The broad fresh-eyes PLAN item remains open.

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

## 2026-11-02 — PR #8 manager follow-up (Codex)
- Moved the completed resource review from CLAUDE.md into this session record, as the manager requested. The
  standing instructions retain current budget controls and the stress-simulation pause. No new resource review.
- Reviewed decision: **keep** Studio's existing subprocess runner and progress stream. The concrete gap was
  releasing a project before cancellation finished; recording the requested outcome until process exit fixes it
  within the current design. A separate job framework adds migration and maintenance without a demonstrated gain.
  Revisit if jobs must persist across Studio restarts or run on multiple machines. No CAD/simulation replacement
  was identified for this usability task.
- Latest main merged without lifecycle code changes. Rechecked the saved note, standing instructions and PR scope;
  the two real-process cancellation regressions pass again after integration (0.16 s). No full batch or stress solve.
- Queue refresh against main 9e39eab: resolved only additive STATUS text, preserving both dated entries and their
  context. Lifecycle source/tests are byte-identical to the prior validated revision; CLAUDE.md and PAUSED.json match
  current main. No repeated process tests for this documentation-only resolution, and no new feature count.

## 2026-11-02 22:45 UTC - "How Kerf decided" readable and steerable (Claude)
- Replaced the force-directed thought web (it never settled, so it shook, and labels overlapped / were cut at 46 chars) with a calm trail read top to bottom: 1 You asked (the whole request) -> 2 What it looked into (one card per question: Looking now / Kept coming back / Looked at / Not pursued + why, "Found:" its notes, its sources as links, follow-up questions inside) -> 3 What it decided (each option Chosen / Set aside with why, and "Came out of" the research it rests on) -> 4 What it's building (parts drawn as one step with chips, then tests). Nothing moves except new items fading in; light, dark and phone width checked in screenshots.
- DESIGN.md option parsing: reasons no longer read "chosen." (marker words stripped), and unmarked items of a list with a chosen one count as set aside (fpv_5in, pan_tilt now show all their alternatives).
- Job panel: a one-line strip (stage, current question, counts, latest finding) appears by itself when research starts and stays visible when the panel is folded; it opens the full trail.
- Steering (kerf/steer.py, .claude/hooks/steer.py): Focus / Skip on each question while it is still researching, plus a "Tell Kerf" note. Delivered as extra context on the job's next tool result via a PostToolUse hook that only starts for a Studio job with a steering file: no extra turn, no pause, nothing at all when unused. The trail shows "Kerf has it ✓" once delivered; steering resets with each new job and is refused once the job has finished.
- Tests: tests/test_thoughtweb.py (8 pass: layout still between polls, no label overlap or clipping, strip auto-opens, steer API + hook end to end, reset per job, options link to research). Pre-existing failures NOT from this change (they fail on main without it too): test_studio.py::test_progress_events_are_off_by_default_and_ordered_when_on (requirement order changed by the "check in order of redesign cost" commit) and test_studio_features.py::test_duplicate_copies_design_files_only_and_renames.


## 2026-11-02 — Shared claims from PR branches (Codex)
- Claim take/heartbeat/release now publish only the current session's claim changes to freshly fetched main,
  using a private Git index and normal fast-forward pushes. Concurrent pushes retry from current ownership and
  budget state. Caller branch/HEAD, staged bytes and dirty/untracked files stay unchanged; no pull, stash, reset,
  feature-code publication or local claim mirror. Explicit session identity overrides an old worktree identity.
- Budget stop/resume use the same isolated path; status, claim readers and batch lock readers see shared main.
  Current shared/local budget stops block new work while allowing heartbeat/release. Reserved control names,
  unfinished Git operations and unreadable/unreachable shared state refuse safely. Detached worktrees work;
  origin/main is required. PLAN selection remains local so explicitly scoped PR-only tasks can be claimed.
- 41 focused tests passed in 37.04 s (claims, budget, batch status and Codex Work metadata). Real bare-remote
  tests cover byte-for-byte caller preservation, detached linked worktrees, concurrent unrelated/same-owner
  claim races, budget changes during retry, expired/local stops, stale takeover, corrupt records, missing remote
  and rejected pushes. Doctor ALL OK with the existing environment; optional firmware tools remain unavailable.
- Boundary: batch lock/result publication still uses its older caller-index/upstream implementation. Only its
  read side is fixed here; a separate repair is needed before using a PR checkout to publish a batch. No batch,
  stress solve, physical hardware, project geometry, catalog, engineering threshold or review.json changed.

## 2026-11-02 17:45 UTC-5 — for Spencer: Studio single-change jobs vs the Stop gate
- A Studio change request says "do exactly this change ... do not start other PLAN work", but .claude/hooks/stop_gate.py
  only lets a session end when every open PLAN item is claimed by others (or on BLOCKED / YIELD / 60 blocks). So a
  finished Studio job (this one: drone_foldable_wings hub fairing, all pushed, claim released) keeps getting told to
  `claims.py next`. I followed the job's instruction and did not take new work, and did not write BLOCKED/YIELD (both
  would be false). Suggested hook change, needs your go-ahead: let a Studio job end once its own work is committed,
  pushed and claim-free (e.g. Studio sets an env var or a .claude/state/STUDIO_JOB marker that stop_gate honours).
- (Claude, 2026-11-02, notifications) Clicking a notification opens what it is about: pop-ups carry a target (`kerfOpen`: project:<p>:<tab> / job:<id> / new; failures open Checks, tries Tune, builds 3D); the Mac app posts real desktop notifications (UserNotifications) that call kerfOpen on click, and the server's osascript one (which opened Script Editor) is skipped while the app is open; jobs that finish while not watched now notify too; Activity rows open their project. tests/test_notify_targets.py.

## 2026-11-02 23:10 UTC — Validate physical mass inputs (Codex, mass-input-validation)
- Reproduced on a synthetic 10 mm cube: walls=-10 gave -1.105 g; infill=2 gave 1.87 g against 1.25 g solid;
  walls=2.5 counted 2.5 loops in mass but exported 2. NaN/Inf infill reached physical mass; NaN/Inf walls could
  saturate shell volume and then crash integer print output. Purchased mass_g=-5/NaN/Inf passed loading unchanged.
- Shared scalar validation now rejects nonfinite/boolean inputs, infill outside [0,1], non-whole or negative walls,
  and negative explicit purchased mass_g. Project loading reports item/field paths before geometry; direct mass,
  cached-mass, shell-volume and print-output paths use the same rules. Numeric wall strings including "2.0" normalize
  consistently with numeric 2.0. Zero/one infill, zero walls, 2/4-wall defaults and missing/zero purchased-mass warnings
  retain their semantics. Purchased specs must be mappings; modifier collections lists of mappings with valid scalars.
- Local modifier validation does not alter the whole-part mass or FEA model. Geometry, density/catalog values,
  formulas, structural thresholds and solver behavior are unchanged. Pending mixed-manufacturing PR13's early
  manufactured-part branch must retain its continue before these FDM-only input checks during integration.
- Read-only doctor ALL OK with shared existing dependencies; optional firmware tools remain unavailable. Batch
  status/process checks preceded each focused test run; no full batch, project build, stress/FEA run or install.
- Final exact selection, without environment overrides: `.venv/bin/python -m pytest -q tests/test_mass_inputs.py
  tests/test_item_mass.py tests/test_print_settings.py tests/test_printpkg.py tests/test_docs.py
  tests/test_maker_output.py::test_report_mass_split_unattached_and_units` — **99 passed in 2.67 s**.
  Tests cover invalid load/helper boundaries, finite hand-calculated mass, cached-spec edits, valid zeros/defaults,
  numeric strings, malformed mappings, unchanged local-modifier mass and existing print/maker output contracts.
- Initial selection was 98 pass/1 failure: existing printpkg test read UTF-8 output using the process locale after
  Mesher.write(.3mf) changed it to US-ASCII. With PYTHONUTF8=1 it then exposed an unquoted fake interpreter path with
  spaces (exit126). Isolated unmodified origin/main 2a6662a source copy reproduced the exact printpkg node failure:
  1 failed in 2.41 s. Fixed only the adjacent test fixture: explicit UTF-8 on two output reads and shlex.quote on
  fake executable/script paths. Every assertion is retained; no Mesher, global locale or production slicer change.
- Independent parent review approved the final validation/fixture diff. Only this precise PLAN item is complete;
  no new physical validation or finished-project claim.

### 2026-11-02 — Full-suite speed (session 01S68R6R; measured on slices, no full run, per Spencer)
- Found by timing one project's verify build by stage: viewer click-to-edit (kerf/attribution.py: traced rebuild of
  every part + one rebuild per param, budget 240 s for the params alone) was 29 s of servo_link's 63 s and 303 s on
  pan_tilt, in every project build of `kerf verify` and every test that writes a viewer, and it cannot change a result.
  `kerf verify` and tests/conftest.py now set KERF_NO_ATTRIBUTION; `kerf build` keeps it; the two tests that use it
  through the viewer turn it back on. pan_tilt verify build ~500 s -> 202 s; a 4-file test group 194 s -> 43 s.
- geom.mesh_gap grows its search radius from 1 mm: a 1e4 mm radius made close curved parts 3.7 s per pose (worse than
  exact); pan_tilt cam_clear 100 s -> 20 s, same values.
- VERIFY.json now keeps the 30 slowest tests (--durations=30) and each project's build seconds: the next suite
  speed-up should start there, not from a guess.
- Not changed on purpose: projects still build from scratch (KERF_NO_CACHE) and drawings / renders stay in verify
  (their failures are real problems). Seen while testing, not mine: test_studio_features duplicate (DID NOT RAISE) and
  test_utf8_io (studio.py:956), both from the Studio commit at ~17:15.

## 2026-11-02 — Work claim ownership details (Codex)
- A shared chat keeps each linked claim's reported owner/provider, activity, update time, scope, attention and
  checklist. Existing scope details show these as compact task rows; full owner names and activities are searchable,
  and provider filtering also matches the linked owners. One chat remains one card and one observed live session.
- Stale ownership updates flag the card for attention without implying that its live chat or another owner stopped.
  In-progress/recent status filters can overlap attention, each counting a card once. Unknown checklists/times stay
  unknown; combined progress still requires every claim's checklist. A sole claim cannot hide the chat's own next
  steps, and identical claim/chat steps are shown once. No subagent execution or ETA is inferred from ownership.
- 31 focused tests passed in 6.26 s (Work overview/browser, Codex Work, docs); after the independent review's
  overlapping-filter correction, both browser scenarios passed in 5.14 s. Tests include mixed/stale owners, unknown
  and complete checklists, live-state retention, owner/activity search, provider matching, refresh focus/open state,
  escaping and long owners at desktop/phone sizes in both themes. Work's light warning text now clears 4.5:1.
- Viewed the illustrative captures in .cache/work-owners (work-owners-sample-{dark,light}-{1440,390}-{top,details}.png).
  No horizontal overflow or browser errors. Impeccable's one mechanical scan found only 13 existing patterns outside
  the edited Work selectors; no redesign or new design artifacts. The existing tall phone app shell is a separate
  accepted limitation. Doctor ALL OK using shared dependencies; optional firmware tools remain unavailable.
- Parent code/screenshot review findings are fixed and covered. No full batch, stress solve, physical hardware,
  project geometry, catalog, engineering threshold or review.json changed; full verification remains on hold.


### 2026-11-02 — Preserve useful Work progress descriptions (Codex; stacked on PR #23)
- Reproduced public progress text being replaced by a generic tool label. Codex records now retain
  the latest nonempty public message in `activity` and separately report the later tool's bounded
  `action` label. A newer public message clears the old action. Live in-progress and saved/waiting
  actions retain their distinct wording; raw commands, arguments, outputs and reasoning stay private.
- Work renders the action as a secondary line below the progress description and includes it in search.
  No-summary fallback stays a single line. Claim records cannot assert tool activity, both claim-overlay
  paths clear displaced session actions, and stale snapshots clear current actions and set `live=None`.
  A newer claim can replace stale text while the runtime warning remains; no running/stopped inference.
- Validation: **37 focused tests pass in 13.70 s** (Codex reader, Work overview, both browser scenarios,
  docs). Final freshness integration and affected reader/overview selection: **31 pass in 3.25 s**.
  These selections overlap. Browser checks cover 1440/390 px, light/dark, search, escaping, duplicate
  suppression, active/attention filters, refresh/focus/open details and no overflow. New text contrast
  is measured against the actual Work background at the unchanged 4.5:1 threshold; the initial test
  incorrectly treated a transparent row as black. Four action captures reviewed in `.cache/work-activity/`.
- Test integration only: copied the exact existing 13-line `tests/browser.mjs` from PR #4's
  fast-tests-refresh worktree, verified byte-identical, and routed both Work scripts through it. It
  reuses a worker browser when supplied, otherwise starts its own; no marker/config/fixture edits.
- Impeccable incumbent refinement: 13 preexisting mechanical findings, none in changed Work selectors.
  Doctor ALL OK with reused dependencies (optional Arduino/simavr unavailable). Existing phone shell
  height is unchanged. No real Codex session connection, full batch, stress run, geometry or review edits.


### 2026-11-02 — Work links identify real observed Codex chats (Codex; stacked on PR #29)
- Found that only hand-written browser fixtures supplied chat URLs: the actual Codex reader did not,
  so real sessions had no Open chat action. Verified the existing-chat route in the official
  [desktop app Commands reference](https://learn.chatgpt.com/docs/app/commands#deep-links), which documents
  `codex://threads/<thread-id>` separately from the new-chat route. Local Info.plist confirms scheme
  registration; no route was inferred from registration alone. One targeted official source lookup.
- The reader now supplies the documented link from the full observed technical ID, percent-encoded as
  a single path segment. Invalid/non-string/control/reserved IDs get no link. Work accepts only existing
  chat routes for codex links (no new/settings route, credentials, port, query, fragment or decoded
  path separator); HTTPS handling remains. Open chat uses target=_blank plus noopener/noreferrer,
  reusing the native shell's existing external-window delegate without changing Swift or the launcher.
- Full observed Chat ID is escaped and wrapped in Scope & next steps. Shared claims alone cannot
  supply that observed identity. No clipboard flow, synthetic URLs or automatic navigation was added.
- Validation: **52 focused tests pass in 16.25 s** (Codex reader, Work overview, browser, docs).
  Final full-ID escaping/capture browser selection: **2 pass in 13.70 s**, overlapping the earlier run.
  The browser fixture goes through actual `_record` → overview → DOM, asserts full href/ID/target/rel,
  intercepts keyboard activation before navigation, and preserves focus through refresh. Invalid route,
  escaping, 1440/390 px, light/dark, no-overflow and existing Work filtering checks pass. Full-ID and top
  captures in `.cache/work-chat-links/` visually reviewed. Mechanical audit: 13 incumbent findings,
  none in changed Work selectors. Doctor ALL OK; existing optional Arduino/simavr unavailable.
- No production chat, native app, real session connection, full batch or stress run. The native external
  handoff is verified by source path and DOM attributes, not a live app launch. Opening a documented
  link still depends on an installed app handler and the chat existing on that computer. Phone shell
  height remains the previously accepted separate limitation.


### 2026-11-02 — Codex executable discovery under the native launcher (Codex)
- Reproduced the concrete app-only install gap without launching Kerf Studio: `codex` is absent from
  `tools/mac/start.sh` prefixes plus the standard GUI PATH, while the installed ChatGPT nested bundle
  declares `CFBundleExecutable=codex` and provides a regular executable file.
- Work now prefers the PATH executable and, on macOS only, falls back to the verified
  `/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex` layout.
  Other installation locations must be on PATH. Missing/nonexecutable files, directories and broken
  symlinks remain unavailable, with explicit source guidance; shared claims still appear.
- Validation: **25 targeted tests pass in 2.09 s** (`tests/test_codex_work.py tests/test_docs.py`),
  including PATH preference, platform restriction, unusable candidates and both discovery routes
  through the existing harmless read-only protocol fixture. Tests substitute the app candidate,
  so they cannot discover the real bundle. Initial Windows simulation exposed a test-only global
  `sys.platform` side effect in `shutil.which`; the final platform-system gate/mock avoids it.
- Doctor: ALL OK with reused dependencies; optional Arduino/simavr unavailable. Read-only real helper
  resolution under the native launcher PATH succeeds; `--version` exits 0 (`codex-cli 0.166.0-alpha.5.1`).
  No app-server/native app launch, updater, installer, PATH mutation, full batch or stress run.
  The fallback intentionally covers only this verified bundle layout; custom installs use PATH.
## 2026-11-02 (Claude, Learning Mode phases 2 and 3)
- `kerf diary <p>` / `--all` (kerf/diary.py) rebuilds each project's diary from git history into learning/diary/<p>.json + .md:
  review.json versions followed from round to round, check PASS/FAIL events and commit-noted problems ("crashed at 97 deg"),
  stage per problem (before parts / rough / detail / final review, from the part files in the tree at that commit) and cost
  (active-minute estimate, part modules redrawn). Costs are ESTIMATES. `kerf diary <p> --log-session [FILE]` adds a Claude Code
  session log's measured token usage (counted once per API message id; the log repeats usage on every content block).
- `kerf lookback [<p>]` (kerf/lessons.py) maps each problem to a lesson by keyword rules (no AI), says the earliest stage and what
  would have caught it, groups across projects, and writes learning/lessons.json + learning/LESSONS.md. Ladder: 1 project = note,
  2+ = instruction, 2+ with final-review finding or redraws = PROPOSED gate (nothing is enforced; Spencer approves).
- Limits: the stage of a review finding is always "final review" once parts are real (every review.json is the design reviewer's),
  so nearly every cross-project lesson reaches "proposed gate"; the keyword rules leave ~80 of ~700 problems unclassified; check
  results are only read from commit messages. No check, threshold, catalog value or test was changed; .claude/ untouched.
- Tests: tests/test_diary.py, tests/test_lessons.py, tests/test_docs.py (targeted only).
- (Claude, 2026-11-02, options + usage failsafes) Options: "💡 Options ready" sidebar badge from any page and an "Options ready to choose from" list on New design (`/api/quotes`, `studio.list_quotes`); `openQuote(name)` loads THAT request's description and options, so two option runs never mix or block each other's buttons. Usage: a Claude job cut off by the usage limit is PAUSED (session id kept, reset time read from the message), resumes by itself after the reset (setting `autoresume`, skipped while tools/budget.py's switch is on) or now with ▶ Resume (`/api/resume`, `claude -p --resume <session>`); no Claude job starts and auto-fix waits while usage is out (claude_ready code `usage`); every Claude job prompt says to commit as it goes. tests/test_usage_failsafe.py, tests/test_notify_targets.py.

## 2026-11-02 19:00 UTC-5 — leftover engine edits stashed (portable_launcher_gets quote job)
- Found uncommitted edits in the local tree from before this session (no claim held, author unknown): `edges.part_sharp` (kept
  sharp corners matched in the part's own frame via kerf_home_loc), its caller in pipeline._print_checks, and a test in
  tests/test_edges.py (6 pass). Not committed (author's intent unknown): saved as the stash "leftover uncommitted work found in
  the local tree, author unknown..." (`git stash list`; restore with `git stash pop` on that entry). If finished, note
  kerf/coves.py:86 and features.py:367/414 still call sharp_inside directly, which may need the same own-frame treatment.
- The quote itself (.cache/studio/quotes/portable_launcher_gets.json, bungee rail recommended) is untracked by design.

## 2026-11-02 — hawk_wing (Studio request, option 0 picked): swing-wing FPV plane, IN PROGRESS (Claude)
- Claimed PLAN item `hawk_wing`. Done: research (REFERENCES.md incl. Spencer's two notes: folding-wing gliders, what
  breaks on these aircraft), catalog `rods.ss_rod_5` + sourced `bearings.625` (C0 380 N) + prices, DESIGN.md,
  project.yaml contract, parts/layout.py (every shared interface position), copied sibling wing/tail/pinion parts.
- Concept numbers on stubs (kerf req): static margin 11 % spread / 41 % half / 94 % folded / 40 % uneven, all inside
  the elevator's trim limits; sweep servo at 43 % of half its stall (4 g pull), gears 13.6 of 16 MPa; spar 0.37.
  Mass on stubs 2.4 kg (stubs are solid blocks); finished estimate ~1.65 kg.
- Engine: `size_max include:` (items subset, test), `kerf req` advice loop no longer shadows its timer (TypeError).
- Next: part-designers on pod/cap/hub, glove, body, wings, tail (running); then wiring routes, kerf check PASS, build,
  renders, design-reviewer. FEA is PAUSED: pivot strength is designed by load path + hand checks, unproven.

## 2026-11-02 20:15 UTC-5 — Claude offline: Codex takes over (Spencer), session 01S68R6S
- Claude is out of usage. AGENTS.md (Codex reads it automatically) maps CLAUDE.md's rules onto Codex and switches on
  "CLAUDE OFFLINE MODE": a Codex manager task merges other Codex PRs (22 open, none merged since #11); Codex never
  writes review.json (design-reviewer sub-line left for Claude). Snapshot, priorities and ready-to-paste task prompts:
  docs/status/CODEX_TAKEOVER.md. First Claude session back: end the mode as AGENTS.md says.

## 2026-11-02 20:40 UTC-5 — portable_launcher_gets IN PROGRESS (Claude, Studio job, still running)
- This Claude session is still working on it (claim heartbeats fresh); Codex: don't take it over unless the claim goes
  stale. State in git: research + catalog (V-slot 2040, V-wheel, tee nut, 6 mm QR pin, alu tube, latex force curves,
  shock cord, braid, stake), DESIGN.md (sizing, load cases, per-part contracts, joint tree), project.yaml contract,
  layout.py, stub parts; five part designers are replacing the stubs now.
- Engine (all tested): `fit="lock"` pins (removable QR / clevis pins that lock a fold or slide joint at home);
  `bungee_launch` requirement (kerf/req_launch.py: exit speed / peak g / setting table from a sourced elastic force
  curve, named curves, V-cord brake stop with pre-stretch); box proxy joints with a rotation; rod proxy reads `d`.
- Design decisions: 6 strands of the catalogued 3/16 in latex (commodity curve) instead of the quote's 1-4 (documented
  latex is weaker than the quote guessed); brake = pre-stretched latex V-cord (shock cord has no published force
  curve); fold joints = two QR pins per joint 44 mm out (outside the sled wheels) with lugs top and bottom so each joint
  holds bending both ways; rear-foot pivot on the rail centre line (launch recoil bends nothing).
- Next: integrate parts, strength hand checks (FEA paused), build, renders, design-reviewer.
## 2026-11-02 20:25 UTC-5 — Codex runs Studio jobs when Claude is out (session 01S68R6S)
- kerf/agent.py + `kerf agent [auto|claude|codex]`: Studio design / quote / edit / fix jobs pick Claude Code or Codex;
  auto switches to Codex when Claude's usage is out and hands a cut-off Claude job to Codex at once (codex_takeover).
  tests/test_agent.py (9). Learning Mode phases 1, 4-8 added to PLAN for Codex. test_studio_features duplicate test
  already fails on main (not this change).

## 2026-11-03 01:52 UTC — Work reflects agent jobs, usage pauses and continuations (Codex)
- Reproduced through `studio.work()` with in-memory jobs: a Codex edit appeared as Claude, while a usage-paused
  design became idle/Not running and still said it was designing a part. The Work serialization now carries the
  known agent, ended timestamp, usage/resume metadata and current retry/budget policy. No Job lifecycle, timer,
  resume, cancellation or agent-selection code changed; `Job.info` did not need modification.
- Work labels paused runs explicitly, groups them for attention without claiming user input is required, and
  separates the reported usage reset from finish ETA. Pause details say whether retry is enabled/off/budget-blocked
  or a resumable session is missing; enabled policy never promises a queued timer. A prior run with `resumed_by`
  becomes Continued, not Finished, and shows an observed successor's provider/state with Watch continuing job;
  unobserved successors get no dead navigation. Previous-run activity remains accessible. Historical missing or
  invalid agent metadata retains Claude fallback; known non-agent jobs stay Studio. Claim/session behavior is unchanged.
- Validation: **81 passed in 18.79 s** (`tests/test_work_job_states.py`, `tests/test_work_job_page.py`,
  `tests/test_work_overview.py`, `tests/test_work_page.py`, `tests/test_codex_work.py`, plus docs requirement/YAML/
  engineering-contract nodes). Initial 75 pass / 3 browser failures came from old fixture routes returning `{}`
  for main's new `/api/quotes` poll; corrected all three to the actual empty `{quotes: []}` schema, keeping every
  assertion. One browser-marker registration warning remains until the pending fast-tests configuration lands;
  the new browser node is explicitly marked. Known agent docs-map failures are covered by PR #34, not repeated here.
- The actual serialization-to-DOM fixture verifies provider labels, pause/active/recent filters, reset-vs-ETA,
  escaping, unknown successors, keyboard navigation/focus and no overflow at 1440/390 px in dark/light themes.
  Viewed `.cache/work-job-states/work-job-{paused,continuation}-{light,dark}-{1440,390}.png`; existing tall phone
  app-shell height remains unchanged. Impeccable's one mechanical scan found 13 existing issues outside edited
  Work selectors. `kerf doctor`: **ALL OK**, existing optional firmware tools unavailable.
- Based on PR #31 and current main, preserving both STATUS sides of their additive conflict. Budget off and
  batch/duplicate-process status checked before focused runs. No real agent process/chat, timer, physical project,
  stress solve, full suite or full batch. Exact observed session/job dedup is a separate pending investigation.

## 2026-11-03 — Studio progress descriptions survive tool updates in Work (Codex)
- Reproduced through actual `studio.work()` with an in-memory job: a public note about hinge clearance
  followed by a tool event became only "Checking the design". Running design/edit/fix/quote jobs now retain
  the latest nonempty public note with the existing bounded phase/stage label as a separate action. A newer
  note clears the action; no-note and identical-note fallbacks stay one line. Raw tool names, arguments,
  commands, output and reasoning do not enter these descriptions; no progress or ETA is inferred.
- Hint/result boundaries prevent an old note from returning, including cleanup tools after a setup failure.
  Setup attention stays visible; the activity says it is waiting only while the process runs, and says it
  stopped once failed/stopped. Paused and continued jobs keep PR #37's status descriptions and no action.
  Build progress/results retain their existing behavior. No lifecycle, serialization, overview dedup, HTML,
  CSS or source-reader changes; the existing Work action/search/escaping/refresh controls render the fields.
- **70 targeted tests pass in 4.54 s** (`test_work_job_activity`, `test_work_job_states`, `test_work_overview`);
  **1 overlapping browser test passes in 4.47 s** after adjusting only the capture scroll position. The first
  browser attempt caught a harness assignment to `S.work` instead of its data; the harness now exercises
  the actual refresh through mocked `/api/work`, preserving all assertions. One browser-marker warning
  remains until pending PR #4 registers the marker. Doctor ALL OK; optional firmware tools unavailable.
- Viewed `.cache/work-job-activity/work-job-activity-{dark,light}-{1440,390}.png`: actual serialized note/action,
  escaped long content, search, keyboard activation, refresh focus/open details and wrapping all verified.
  The existing tall phone shell is owned by the separate mobile-layout lane. No real model/session launch,
  native chat opening, project build, stress solve or full suite; shared claims/budget checked, full batch HELD.


### 2026-11-02 — Studio Codex command compatibility (Codex)
- Parent's read-only installed-CLI probe (`codex-cli 0.166.0-alpha.5.1`) found that `--full-auto`
  exits 2 as an unexpected argument before a job can start. Studio now uses `--sandbox workspace-write`,
  matching the official [noninteractive recommendation](https://learn.chatgpt.com/docs/agent-approvals-security)
  (opened 2026-11-02). The existing network config and skip-git flag remain; explicit KERF_CODEX_ARGS
  still replaces defaults. No approval override, bypass flag or persistent configuration change.
- Updated only current command documentation; historical STATUS entries remain intact. **11 targeted
  test_agent tests pass in 3.36 s**, including new/resume default argument order and explicit override
  preservation. Generated `agent.command` argv with its prompt replaced by `--help` exits 0 for both
  exec and exec resume on the installed binary; no prompt or real session was submitted.
- Doctor ALL OK using existing dependencies (optional Arduino/simavr unavailable). No actual agent,
  auth/config mutation, model call, project build, full batch or stress run. Live job execution was
  deliberately not exercised; the queued automatic-resume setting race is a separate task.

## 2026-11-03 — Studio agent commands use the same bundled Codex discovery as Work (Codex)
- Integration audit found `agent.codex_bin` importing a nonexistent `codex_work.codex_bin`; the caught
  import error silently fell back to PATH. A read-only probe using PR #26's actual helper and a fake
  executable reproduced Work finding the bundle while the agent returned None. The import now names
  the existing `_executable` helper. PATH preference and the exception/PATH fallback remain unchanged.
- **36 targeted tests pass in 1.33 s** (`test_agent`, `test_codex_work`). Five new cases prove the actual
  helper reaches agent selection and new/resume argv for bundle-only and preferred PATH installs,
  including a path with spaces, and preserve fallback after helper failure. Agent fixtures now isolate
  the host app bundle and prohibit app-server discovery; existing fake-binary lifecycle tests remain.
  No real Codex process, app-server, prompt, chat or paid model launched by these tests.
- Dependencies: PR #26's discovery helper plus PR #36's supported CLI flags/current-main agent code.
  Normal dependency merge `046389c` kept both PLAN/STATUS histories and inherited files unchanged;
  the actual one-line fix and regression tests are a separate commit. Doctor ALL OK with existing
  dependencies; optional firmware tools unavailable. No full suite, project build or stress solve.


### 2026-11-02 — PR #8 integration with usage pause and Codex handoff (Codex)
- Merged current main into the existing cancellation branch, resolving the real Job completion conflict
  and retaining both STATUS histories. Main's AGENTS, stress pause, session/usage metadata, agent selection,
  notification and handoff behavior remain. Explicit stop/auth outcomes now take precedence over usage
  pause only after output is drained and the child exits; the project stays busy until then.
- Stop can cancel an already-paused job's queued retry. Completion, Stop and resume/handoff registration
  share the existing reentrant JOB_LOCK. A callback revalidates after its budget check; if successor
  registration already won the lock, delayed Stop forwards to that successor. No wait/communicate or
  budget fetch is held under the lock; process registration uses the existing start_job lock.
- **21 targeted tests pass in 0.67 s** (`test_studio_lifecycle`, `test_usage_failsafe`, `test_agent`).
  Harmless real-child cases preserve cleanup and project exclusion through graceful exit for stop/auth,
  with and without usage events, while genuine usage pause schedules only after exit. Event/fake-Timer
  tests cover Stop racing a started retry callback and both registered successor paths without sleeps.
  The first run had 20 passes and one fixture error: the old fake paused job lacked `state`; it now
  explicitly reports paused, preserving all assertions. Claude-only usage tests isolate host Codex;
  fake-binary agent tests independently retain successful takeover coverage. No paid agents launched.
- Doctor ALL OK with existing dependencies; optional Arduino/simavr unavailable. No full suite, project
  build, stress solve, review.json, CLI-flag change or new runner framework. The separate installed-Codex
  CLI flag compatibility finding is queued for its own lane.

### 2026-11-02 — Queued usage retries respect automatic resume being turned off (Codex)
- A captured fake-Timer callback reproduced the bug on PR #8: schedule while automatic resume is on,
  turn it off, dispatch the callback, and one mocked agent launch still occurs. `resume_job(auto=True)`
  now reads the current setting after its budget lookup, inside the existing job lock, before launch.
  A disabled callback leaves the job paused, preserves its usage deadline, and records why it did not
  resume. Manual Resume still works; re-enabling before a queued callback dispatches permits that retry.
- **25 targeted tests pass in 0.67 s** (`test_studio_lifecycle`, `test_usage_failsafe`, `test_agent`).
  Four new cases cover off before dispatch, re-enabled before dispatch, off while the callback waits
  on its budget check, and manual Resume while off (the old callback cannot duplicate its successor).
  New tests use fake timers and mocked launches; existing lifecycle tests use harmless Python children.
  No real model/session launched. Doctor ALL OK; optional firmware tools unavailable.
- Stacked on PR #8's cancellation lock. No new timer registry, settings synchronization, or automatic
  rescheduling of an already-skipped callback; after such a skip the existing manual Resume remains.
  Full suite, project builds and stress solves remain unrun under the existing holds.


## 2026-11-02 — Studio readers follow shared ownership (Codex)
- Activity, Checks, edit/auto-fix guards and Work now read the same fetched main snapshot. Released claims never
  return from stale feature files; non-Git copies retain valid local claims. Control files and malformed/nonfinite
  records cannot become work cards. Claim freshness/update time comes only from heartbeat, not a newer file commit.
- Claim text identifies Codex/Claude when explicit, otherwise another session, and says claimed rather than running.
  Activity polling on any Studio page keeps the existing one-minute fetch loop active and refreshes its cached list;
  no second fetch service or per-card network calls. Offline Work retains its partial-source indication.
- Five focused regressions failed before their respective fixes. Final selection: 29 tests PASS in 9.09 s, including
  real temporary Git snapshots, release/staleness/control handling, normal-page refresh, API guards and a real Activity
  browser. The browser caught/fixed the age parser after wording changed to last update. No full batch, project build,
  solver, paid model call or layout redesign. Architecture map updated; git diff --check passes.

## 2026-11-02 — Shared claim publisher/Studio integration (Codex)
- Folded the reviewed Studio reader compatibility into PR #17 so shared publication and its consumers ship
  together; preserved both STATUS histories and publisher/immutable-ref tests. No local claim mirroring.
- A new real-Git regression reproduced index-byte changes when only an unchanged tracked file's mtime moved.
  Disabled optional Git locks and replaced the conflict check's worktree-refreshing git diff with ls-files --unmerged;
  private GIT_INDEX_FILE remains intact. Take, heartbeat and release now preserve the exact original index bytes.
- 14 combined focused tests PASS in 13.50 s: index lifecycle, dirty-feature preservation, mid-rebase refusal,
  shared readers/refresh, Codex publisher metadata, Activity browser and API guards. Earlier 41 publisher and
  29 reader results remain separate historical selections, not an accumulated unique count. No full batch or FEA.

## 2026-11-02 — Keep New design open after leaving Work (Codex, handoff-refresh)
- Leaving Work for New design now clears the Work navigation flag, so an in-flight Work response or later poll cannot replace the request being typed. One state reset; no layout change. This follow-up carries the fix that was pushed after the manager captured PR #11 for merging.
- Three focused browser tests pass: delayed Work response, scenario option flow and existing Work-page filters/progress/recovery. Parent independently reviewed the one-line fix and deferred-response regression. No full suite, hardware or paid model run.

## 2026-11-03 02:02 UTC — content-sized mobile sidebar with scroll access (Codex)
- Inspected the layout history and current shared claim before the scoped claim: a0f4846 fixed Activity spilling
  by setting the mobile sidebar to 44vh and clipping overflow. The retained Claude layout heartbeat was still
  1793657319 (2026-11-02 22:48 UTC), over 90 minutes old; its existing PLAN completion and claim remain untouched.
- Two mobile-only CSS values change: `height:auto` and `overflow:auto`. The 44vh ceiling, 56px project-list
  minimum and existing internal list scrolling remain. Empty/short lists no longer stretch the sidebar into
  blank space, while very short screens can scroll the outer sidebar to controls that were previously clipped.
  Desktop sizing and navigation behavior are unchanged; no new menu or route state.
- Same illustrative Work fixture, before/after: at 390x844 the empty sidebar shrinks 371.36 -> 254.97px, recovering
  116.39px for content; at 390x1000 it shrinks 440 -> 254.97px, recovering 185.03px. **Populated lists still use the
  44vh ceiling** (440px at 390x1000); this is not a complete many-project mobile navigation redesign. A separate
  Work-only navigation refinement remains useful because All projects already provides project navigation.
- Validation: **5 focused browser tests passed in 26.21 s**: new `tests/test_mobile_shell.py`, both existing
  `tests/test_work_page.py` cases, `tests/test_work_job_page.py`, and
  `tests/test_usability.py::test_phone_tune_and_connection_recovery`. The new fixture covers 390x844, 390x1000,
  320x568, 844x390 and 1440x900 in both themes, empty and 30-project/30-job sidebars, bounded containers, internal
  and outer scrolling, last-project/job clicks, every sidebar button's focus visibility, Tab/Enter navigation,
  no horizontal overflow and unchanged desktop geometry. Two expected browser-marker registration warnings
  remain until the pending fast-tests configuration lands; no assertion changed or loosened.
- Viewed matching `.cache/mobile-shell/{before,after}/work-dark-390-844.png` and populated after captures;
  before/after light/dark captures at both phone heights are saved there. Impeccable's one mechanical scan found
  13 existing patterns outside the edited sidebar rule. `kerf doctor`: **ALL OK**, existing optional firmware
  tools unavailable. Budget off, batch held, duplicate-process status checked; no real project/agent, full suite,
  stress or batch run. Stacked on PR #37 for independent review, never self-merged.

## 2026-11-03 02:13 UTC — mobile Work puts tasks ahead of the project catalog (Codex)
- One mobile-only CSS rule hides the sidebar project search/list while `#main` directly contains the rendered
  Work page. Existing All projects navigation restores the searchable catalog; normal project pages, New design
  and desktop retain it. Using the rendered page avoids adding route state and does not depend on the unrelated
  pending asynchronous navigation fix. Browsers without `:has` retain the previous accessible sidebar layout.
- Activity, saved Options ready, New design, All projects, My parts, Work, help, theme, quit, printer and mute
  controls remain. The existing sidebar/list scroll behavior and 44vh ceiling remain; no JavaScript, backend,
  navigation lifecycle or native-app behavior changed. The prior shell regression now exercises its original
  strict catalog/scroll assertions through All projects instead of Work.
- Same populated fixture (30 projects / 30 jobs), viewed before/after: at 390x844 the sidebar shrinks
  371.36 -> 223px (148.36px recovered); at 390x1000 it shrinks 440 -> 223px (217px recovered). Task descriptions
  and progress context now fit higher in the first viewport. Captures are in
  `.cache/work-mobile-navigation/work-populated-{dark,light}-390-{844,1000}.png`; the before captures are PR #40's
  `.cache/mobile-shell/after/work-populated-*.png` in the work-mobile-shell worktree. Short landscape screens
  still use the height cap and scrolling; no claim that all jobs or task details fit simultaneously.
- Validation: **6 focused browser tests passed in 37.16 s**: `tests/test_work_mobile_navigation.py`,
  `tests/test_mobile_shell.py`, both `tests/test_work_page.py` cases, `tests/test_work_job_page.py`, and
  `tests/test_usability.py::test_phone_tune_and_connection_recovery`. New coverage includes four phone dimensions,
  both themes, 30 projects/jobs, keyboard/scroll access, saved options, actual project navigation, New design,
  viewport resizing, nested class isolation and no horizontal overflow. Desktop remains 292px wide. Three
  expected browser-marker warnings remain until the pending fast-tests configuration lands.
- Initial selection: 5 pass / 1 new-fixture failure from an overly broad HTML placeholder replacement, fixed
  with a unique placeholder. The next node exposed Chromium's one-frame stale geometry immediately after
  resizing; a condition-based wait now precedes the unchanged exact size assertion (no arbitrary sleep).
  `kerf doctor`: **ALL OK**, existing optional firmware tooling unavailable. One Impeccable mechanical scan
  found 13 existing patterns outside the changed selector. Budget/batch/process checks preceded runs; no real
  project, agent, physical check, full suite or batch run. Stacked on PR #40; no self-merge.

## 2026-11-03 02:11 UTC — One active Studio run and its exact Codex chat (Codex)
- Reproduced through actual `studio.work()` serialization: one running Studio Codex job and its observed chat
  produced two running cards because the serializer omitted `Job.session`. It now carries that identity; overview
  folds exactly one running Codex agent job into exactly one observed Codex thread with the same explicit nonempty
  ID. No title/project/time matching. Multiple active matches and paused/continued/done/failed/stopped history stay
  separate, preserving observed continuation links.
- The combined card keeps stable `job:<id>`, Watch job and Open chat, the full chat ID/title, public description,
  branch/projects and every claimed owner's scope/checklist/attention. Studio notes and bounded actions remain
  authoritative; only its literal startup placeholder can use a fresh live chat summary. Saved/pre-start chat
  activity/checklists do not become current progress, and finish ETA stays unknown. Live input waits must also be
  at least as recent as the latest job update, with no setup attention or latest hint/done boundary; cleanup tool
  events cannot resurrect an obsolete approval request. Claim-owner warnings remain independently visible.
- Stacked on reviewed job-description PR #41 (`101003f`), itself based on #37; `_job` and frontend code are untouched.
  Validation: **98 passed, 2 browser nodes deselected in 0.14 s** (new dedup cases plus job states/activity/overview);
  dedicated discovery/refresh browser node **1 passed in 4.86 s**; two final note-precedence cases plus three docs
  contract checks **5 passed in 2.16 s**. These initial selections do not overlap. Browser markers are explicit; this
  stack retains the known marker-registration warning until pending fast-tests config lands.
- Final review caught timestamp precision: installed Codex app-server schema defines thread updatedAt as int64 Unix
  seconds, while Studio start/events use fractional seconds. Same-second wait fixtures first produced **2 failed /
  2 passed in 0.06 s**. Freshness now compares whole-second buckets; ordering within a second is explicitly unknown,
  genuinely older seconds remain stale, and hint/done/attention still win. The affected dedup core file then had
  **35 passed, 1 browser deselected in 0.05 s**, overlapping the earlier selection; not added as unique tests.
- Browser fixtures use actual serialized data without agents: job-only to joined refresh keeps keyboard focus and
  open details, both controls, two owner scopes and full IDs at 1440/390 px in dark/light themes. Captures are in
  `.cache/work-job-dedup/`; inspected dark desktop and light phone. Existing tall phone sidebar is addressed by the
  separate mobile-shell PR #40. `kerf doctor`: **ALL OK**, existing optional firmware tools unavailable. No UI redesign,
  real chat/process, timer, project build, stress solve or full suite.

## 2026-11-03 02:51 UTC — Project workspace: model space and evidence before decoration (Codex)
- Reproduced the original header defects in an offline main fixture: the truncated description was an unfocusable
  paragraph, and the tab underline made scrollHeight exceed clientHeight by 1px. The project now has an escaped
  two-line brief with a keyboard disclosure, proper keyboard tabs/selection, stable refresh focus and horizontal
  tab position, and a flex model pane with a usable 360px minimum. Desktop uses the actual remaining space; short
  screens retain main scrolling. Existing build/depth/change/menu/export handlers and geometry remain intact.
- Status and the primary next step remain visible: Review checks for a failed build, Build kit for unbuilt/stale
  designs. The user's follow-up requested less persistent prose: saved cost/mass/print facts and advisory context
  now live in a native Build details popover with click/tap/keyboard, Close/Escape/outside dismissal, refresh state,
  and reduced motion. No essential state requires hover. Stale Checks explicitly describe the previous build;
  the printable record is now Build check summary, keeping its fields/PDF action without unconditional readiness
  promises. Help targets the stable Build kit control rather than relying on its contextual primary styling.
- Final hierarchy correction groups Build kit/Depth as a split control, moves Optimise/Upgrade into More, and
  places the lighter Build details text disclosure beside status. The action row has four groups rather than six
  competing controls. The affected workspace node then **passed in 12.70 s**, overlapping the selections below;
  it also verifies the moved action dispatches. A fixture click initially hit its still-open popover; explicit
  Close before the next action corrected the test flow, with all interaction assertions retained.
- Latest affected selection: **2 passed in 13.96 s** (new workspace browser + existing Depth/Ship confirmation).
  Prior correction selection: **2 passed in 11.60 s** (same workspace + existing glossary/tour/summary), and the
  original phone Tune/recovery node passed. These overlap: four distinct nodes, not summed repeated passes.
  The new node covers 1512x982, 390x844 and 844x390, both themes, escaped/long text, all status branches, keyboard
  and refresh, popover dismissal/containment/reduced motion, model bounds and harmless action dispatch. Initial
  new-node failure came from my empty glossary fixture; a representative nonempty fixture fixed it without
  changing production or weakening assertions. One expected browser-marker warning remains until PR #4 lands.
- Final native WKWebView fixture (no visible app/server): both themes at widths 1512/390 passed tab overflow,
  keyboard disclosure/selection and popover bounds/close checks. At 1512x982 the frame spans y280..958 (678px);
  phone retains the 360px minimum and main scroll. Earlier fixture attempted to reassign a const URL helper;
  fixture-only URL replacement corrected that setup error. No live app was launched or modified.
- Visual evidence: `.cache/project-workspace/grouped/` contains closed/open-details and phone-model captures.
  The saved FPV viewer, its matching report fingerprint and real-length description were read from an existing
  output only; reported cost/mass/print facts are preserved. Mocked Studio APIs, no rebuild. Root and sibling
  reviewed the first desktop/phone batch; sibling found no workspace-specific blocker. Current branch retains
  the old global shell; manager owns combined shell/Work/project visual proof. Phone space is not declared solved.
- `kerf doctor`: **ALL OK**, existing optional firmware tools absent. Budget/process checks preceded targeted
  runs; full batch and stress remain on hold. One Impeccable scan reported 12 existing patterns outside this scope.
  No geometry/check thresholds, catalog, review.json, backend or paid-agent launch. Surface decisions/limits are
  in docs/usability/PROJECT_WORKSPACE.md. New tests reuse the reviewed browser helper byte-for-byte.

## 2026-11-03 02:58 UTC — Work explains assignments, immediate actions and observed changes (Codex)
- Assessed seven synthetic tasks on the reviewed Work integration proof `4323f79`: the old In progress count mixed
  two running items with one claim, opaque/truncated identities distracted from ownership, remaining steps were
  hidden, repeated unknown-progress/ETA paragraphs crowded the phone, and only Git commits explained changes.
- Work now separates working/assigned/paused counts, provides a waiting-for-input filter, orders actual running
  work before pauses/stale ownership, keeps readable owners visible and exact technical IDs in Details, and exposes
  the first reported remaining item. The label says Reported remaining because build lists include the current
  stage. Waiting cards put the existing Open chat/Watch job beside the status; no new job or chat is launched.
  Custom warnings, public note/current action, known progress/estimate basis, all owner scopes and navigation remain.
- Text audit: removed redundant queue headings and only the exact generic waiting sentence (kept in Details).
  Unknown progress/time remain visible as quiet metadata; their explanations and full identity/provenance stay in
  keyboard/tap disclosures. Scan copy says assigned/owners, retaining exact Git claim evidence within details.
- A bounded six-entry local changes list records successful observations while this view is open, with stable
  entry IDs and jump-to-task controls. It creates no history on first load, timestamp-only heartbeat or disappearance,
  and says Observed rather than inventing event time. Per-source field validity keeps healthy Studio jobs visible
  when Codex or shared Git is unavailable, suppresses stale derived context and false completions, and records a
  reliable local terminal result as observed status without asserting an uncertain prior transition.
- Validation: **7 focused tests passed in 33.78 s** (`test_work_clarity`, existing Work/owner/browser, job-page,
  job-activity browser and exact dedup browser). They cover mixed-source failures/recovery, bounded history, escaping,
  identity/focus/open-disclosure preservation, input filtering, remaining scope and all existing controls. Initial
  browser pass was **5 passed / 1 failed in 31.67 s**: the unchanged long-owner fixture caught a new feed title button
  inheriting global nowrap; max-width/wrapping fixed it. Root review also caught an overly broad outage guard; the
  final selection includes independent healthy local jobs and joined-job evidence under unavailable external sources.
- Before/after fixtures at 1440/390 px, both themes, are under `.cache/work-clarity/{before-*,round1,round2}`.
  The new fixture temporarily substitutes only Work CSS/JS into the frozen combined proof to retain mobile #43;
  the feature branch itself remains based only on #44. Inspected final queue and changes captures; waiting action
  is now in the first phone viewport. A final copy-only change uses Reported remaining rather than Next reported step.
- Impeccable context/new-work/operate/craft-floor applied as an existing-surface refinement. One detector found 13
  incumbent patterns outside the edited Work selectors. Sibling newcomer review identified waiting action placement
  and repeated waiting text; both corrected in one batch. No new visual-world/DESIGN rewrite; the shell worker owns
  that separate direction. Reciprocal review flagged duplicate phone project navigation in the shell for its owner.
- No backend data schema, global shell/tokens, project header/viewer, real user data, live agent, model call, geometry,
  stress solve or full suite. Browser marker registration still awaits pending test configuration. Root will validate
  the final creative shell/project/Work integration separately; this PR is a scoped Work feature, not an aggregate.

## 2026-11-03 — Follow live label overlap fixed in native WebKit (Codex)
- Reproduced the user's two desktop screenshots in an isolated system WKWebView fixture using Studio's actual
  CSS/liveBar function. The global input width of 100% made the checkbox 80.55px wide at a 1440px viewport;
  label text occupied x412.55–483.08 while the adjacent helper began at x414.55. Chromium's native checkbox
  stayed 13px and did not reproduce this overlap, so Chromium alone would have missed the reported defect.
- Four scoped CSS rules give the checkbox its intrinsic width, prevent label shrinking, let the control row wrap,
  and wrap long status/error messages within the row. Native after: checkbox 12px, text x344–414.53 contained
  in its label, helper begins x426.55 (12px gap). No markup, wording, polling, API, project or global input change.
- Validation: **2 browser tests passed in 4.89s** (`tests/test_follow_live_layout.py` and the existing
  `tests/test_usability.py::test_phone_tune_and_connection_recovery`), with one expected browser-marker warning
  until the pending marker registration lands. New coverage uses 1440/1024/390/320px, both themes, on/off/long
  unbroken error text, label click, focused Space-key toggle, exact mocked API calls and nonoverlapping bounds.
  The interrupted tool call completed successfully in the background; its final log and no remaining process
  were verified on resume, without repeating the completed selection.
- Temporary native WKWebView harness assertions also pass 18 width/theme/state combinations (1440/390/320px,
  dark/light, off/on/error). This uses the installed system engine, not the running Kerf app; no toolchain install.
  Viewed `.cache/follow-live-layout/follow-off-dark-1440.png` and `follow-error-light-390.png`; other browser
  captures are saved alongside them. One mechanical scan found 13 pre-existing patterns outside the edited rules.
  `kerf doctor`: **ALL OK**, existing optional firmware tooling unavailable. Budget/batch/process checks made;
  no real live-follow request, native app interaction, geometry/build, stress solve, full suite or batch run.

## 2026-11-03 — Studio shell accessibility and visual baseline checkpoint (Codex, WIP)
- Checkpointed neutral tokens, readable contrast, native keyboard project/Activity buttons, explicit utility labels,
  and removal of decorative shared-shell gradients/glows. This is an intermediate design, not a finished PLAN item.
- Loaded synthetic gallery/Work captures use existing saved thumbnails/reports with an explicit fixture caption;
  no physical checks, real app interaction or new build ran. The focused shell browser test passes (1 in 17.07s);
  shell plus strict short-screen scroll regression passed (2 in 25.25s). Initial checks exposed asynchronous fixture
  timing and real 1.125px focus clipping; condition waits and 6px scroll padding resolved them without weakened assertions.
- The user rejected the conventional permanent sidebar composition after review. Next: replace it with an object-first
  full-width stage and on-demand project/activity trays, preserving the verified access and color improvements.
  The current desktop/mobile captures are baseline evidence, not acceptance of the final direction.


## 2026-11-03 03:15 UTC — full-width Studio shell and object-led project collection (Codex)
- Replaced the permanent sidebar with a 72px top navigation strip, or two 108px rows on phones. Projects,
  Activity and utilities open in labelled native disclosures with close/Escape, outside-click and focus behavior.
  Empty or busy project/job lists no longer consume the workspace. Phone search and New design have distinct
  grid areas. Closed panels explicitly leave layout, preventing invisible fixed trays from retaining hit geometry.
- The project collection displays saved model images at larger scale without decorative tiles. Projects without
  previews use compact rows; all projects remain selectable, and observed build/check/review/stale evidence stays
  explicit. Search explains a no-match result. Polling preserves the focused project and scroll position; All
  projects invalidates pending project requests so a slower response cannot replace that destination.
- Shared PRODUCT.md, DESIGN.md and surface brief record the neutral/graphite palette, restrained steel blue,
  system typography, scoped ownership and disclosure contract. Contract sent to all active surface owners and
  reread after saving. No new dependency or font. Other surfaces' content/behavior remains their owners' work.
- Validation: **3 passed in 18.78s** (`tests/test_studio_shell.py`, `tests/test_mobile_shell.py`,
  `tests/test_work_mobile_navigation.py`), with three existing unregistered browser-marker warnings. Coverage
  includes OS theme/default persistence, measured text/control contrast, keyboard navigation/focus, project and
  activity scrolling, saved options, full-width resize behavior, no overlapping header controls or horizontal
  overflow, empty/30-item lists, and 320/390/844/1440px viewports. Prior correction run: 2 pass / 1 fail in 14.80s;
  explicit closed-tray display fixed the original strict overlap assertion, with no loosened threshold.
- Viewed the final light/dark desktop/phone collection captures in `.cache/studio-shell/final`; they use three
  read-only saved model renders in a labelled illustrative workspace. One detector pass reported 12 incumbent
  findings in other surfaces (tabs, job progress/toasts and lightbox); passed to integration instead of changing
  another owner's selectors. Sibling/integration critique remains the parent task's responsibility.
- `kerf doctor`: **ALL OK**, with existing optional firmware-tool warnings. Batch remains HELD; duplicate-process
  checks and the shared two-suite browser coordinator preceded runs. No real jobs, geometry/project builds,
  stress solve, full suite, new review.json or native app run. This shell is a scoped PR, not a finished whole-UI claim.

## 2026-11-03 — Work makes source limits visible beside its counts (Codex)
- Follow-through on #49 found two consequential gaps: partial/unavailable source details were below the work list
  on phones while summary counts looked complete; project shortcuts retained unrelated state/assistant filters.
  A compact Partial view disclosure now qualifies those counts, keeps diagnostics behind keyboard/tap expansion,
  preserves expansion/focus through refresh, and disappears on recovery. Empty limited views explicitly say no
  work is visible from available sources. Healthy local jobs remain counted. Project shortcuts clear conflicting
  filters and focus the populated search. No speculative worker capacity, progress or finish times were added.
- Eight focused nodes pass across the final selections: six passed in the first integrated run, then the two
  corrected test nodes passed in 11.41 s. The first integrated run was 6 passed / 2 failed in 36.62 s: one old empty
  label assertion required the new exact wording; one new late-response test raced New's unrelated readiness fetch.
  It now verifies navigation to All projects; the shared navigation owner covers New. An earlier 3-node attempt
  imported main's older package through the shared venv; explicit PYTHONPATH fixed the harness, with no product change.
- Viewed all four 1440/390 px light/dark source captures under `.cache/work-observation/round1/`. Tests cover omitted
  sessions, partial/loading/unavailable sources, healthy local counts, escaped diagnostics, recovery, native keyboard
  disclosure, refresh state/focus, project filtering and late-response navigation. The frozen integration HTML was
  used only for the two env-aware fixtures, replacing its Work blocks; all other nodes read this branch directly.
  Impeccable's single detector scan found 13 incumbent issues outside edited Work selectors. No visual correction
  was needed. No global shell/token edits, backend changes, live jobs/chats, geometry, stress solve or full suite;
  shared batch remains HELD. Doctor ALL OK; existing optional firmware tools and browser-marker warning remain.

## 2026-11-03 03:22 UTC — Files & guides making handoff (Codex)
- Six scoped improvements turn the format list into a making handoff: essential assembly/shopping/print guides
  first, purchased-component guidance, task-based file groups, saved-build context, keyboard disclosures and
  inspectable provenance. Every API-listed file/document remains downloadable, including unknown future formats;
  guide-only projects keep their source docs. The existing project ZIP, render lightbox and source links remain.
- Stale, failed, incomplete, running and paused evidence stays explicit. Individual file versions are not proven by
  this API and are labelled unverified; no print-readiness, safety or physical-performance promise is added.
  No export backend, hardware action, geometry, check threshold, catalog or review.json change. Files help-tour
  targets/claims now match the surface. One scoped renderProject predicate preserves focused handoff controls.
- Validation: new mocked browser node passed in **7.30 s** after final corrections; existing project_workspace
  node passed in the immediately preceding two-node selection (**1 pass / 1 fail in 13.01 s**, not re-run).
  Earlier new-node pass was 6.36 s; these overlap and are not summed. Coverage includes 1512×982 / 390×844,
  both themes, all listed outputs/docs, unknown/escaped/long filenames, guide routes, source-only and missing
  outputs, stale/failed/running/paused/skipped states, keyboard opening/closing, refresh focus, render inspection,
  reduced motion and no horizontal overflow. All network requests are mocked GETs; Build kit dispatch is stubbed.
- Initial meaningful fixture failure found refresh losing focus; fixed the caller, retaining the assertion.
  Final reduced-motion assertion found the existing global !important 0.01ms transition rule overriding local
  none; scoped handoff override now ensures actual zero (assertion retained). Known browser-marker warnings
  remain until the pending registration PR lands. `kerf doctor`: ALL OK, existing optional firmware tools absent.
- Viewed the first desktop/phone batch, then one confirmation batch: `.cache/making-handoff/{first,final}/`
  holds eight images per batch (dark/light, desktop/phone, top/files). Read links now have persistent affordance;
  phone targets are 44px. Impeccable scan: 13 existing global patterns plus the deliberately short intrinsic-size
  native disclosure transition, reduced-motion disabled. Shared shell integration owns final combined visuals.
  Budget off; full batch HELD and stress paused. No real build/app/provider/printer, full suite or batch run.
  Scope and decisions are saved in docs/usability/MAKING_HANDOFF.md.

## 2026-11-03 — New-design briefing and researched choices (Codex)
- Replaced the long intake card with a spacious brief and optional Use & constraints / Build preferences
  disclosures. Every field, default, example, manual name, inventory link and direct-design path is retained;
  scenario mode still requires comparison. Removed the fixed 1–4 hour estimate and universal strength-proof copy.
- Results now foreground route, cost/print unknowns and fit. Effort, risks, next steps, research and assumptions
  remain in native disclosures; buy-only options retain research links without a design/purchase button.
  Unresolved questions have an answer field that appends to existing notes before requesting a fresh comparison.
  Stale answers and unresolved questions still disable design actions; server validation is unchanged.
- Saved-option replies cannot overwrite a replacement New screen. A cancelled New navigation stops a saved-quote
  load before its request, for the shared navigation guard being integrated by the journey-quality lane.
- Targeted validation: scenario API/evidence cases **27 passed, 2 browser cases deselected in 2.13 s**;
  `test_design_briefing.py`, Studio intake/inventory browser node, scenario comparison browser node
  **3 passed in 10.51 s**. Existing assertions remain; selectors now open optional disclosures and use option
  headings. One pre-existing unregistered browser-marker warning on this base. The final cancellation guard
  additionally passed a direct Node assertion without a browser rerun; its browser assertion is included.
- Inspected desktop 1440 and phone 390 in dark/light with synthetic routes and a temporary three-way compose of
  this HTML and the shared shell (59f305e base); no live provider job. Captures: `.cache/design-briefing/round1/`
  (`briefing`, `options`, `clarify` × themes/widths). No clipping or horizontal overflow; comparison becomes one
  column on phones. Scenario setup requires normal scrolling. Onboarding owns the readiness banner.
- Detector ran once: 12 existing findings outside this lane, none in briefing code. Doctor ALL OK; existing optional
  firmware tools unavailable. No installs, project build/check, geometry, stress simulation, real print, actual
  provider run, full suite or app launch. Full batch remains HELD. Root reviews/integrates the focused PR.

## 2026-11-02 — Tune experience (Codex, in review)
- Replaced Tune's nested cards with an unboxed measurements/materials workbench and a saved-to-edited draft ledger.
  Each parameter and material has Undo; discard resets the draft. Typing/keyboard sliders update actions immediately
  without losing focus. Blank, nonfinite, nondecimal and declared out-of-range values stay editable with an associated
  error and block Try/Save; the last valid edit remains intact. Units, assumptions and range provenance stay visible.
- Trials now identify their recorded values and distinguish them from later edits. Copy promises enabled checks only;
  paused stress checks do not prove strength. Material density is no longer called weight; catalog strength is distinct
  from part strength. Existing requirement effects and better/worse comparison logic are retained.
- Save and Try snapshot the original project and inputs and suppress duplicate dispatch. Successful parameter saves
  clear only acknowledged parameter edits; if the material save fails, those edits remain for retry. Responses from
  another project cannot clear the newly selected project's draft. Backend parameter/material writer fixes are separate.
- Mocked `tests/test_tune_experience.py`: 1 passed in 6.60 s across desktop/phone and both themes, including partial save
  failure and navigation during save. Initial mock run used an empty glossary and failed before Tune assertions; fixed
  the fixture to supply a normal glossary term. Existing assertions were not changed. Final shared-shell visual
  confirmation is pending; no geometry, build, full suite, native app or live provider job was run. Batch remains HELD.
- Source frozen after the green run; latest usage guidance defers the final composed-shell review to the root
  integration pass. The first screenshot batch exposed clipped tall-element captures inside the scrolling app;
  the fixture now captures viewport top/controls/trial views. It can optionally compose frozen shell cc8aa48 for a
  clearly labelled integration preview. One added material-Undo assertion and these capture-only changes await
  that integrated run; no production source changed after the passing test. Detector ran once; its findings are
  in incumbent global chrome outside Tune. No claim of completed combined visual review is made here.

## 2026-11-02 — Studio saved-build History (Codex, design-history)
- Replaced repeated snapshot cards with a real chronological saved-build selector and one readable record. Existing
  thumbnails only; absent pictures/measurements/checks remain explicit. Full saved values and build source disclose
  on demand, including the earliest/only available snapshot; no invented design reasons, approval or older versions.
- Comparisons separate adjacent saved builds from the current built report and flag newer unbuilt edits. Exact
  parameter values, recorded pass/fail transitions and added/missing check results are visible; numeric movement
  alone never implies improvement. Restore previews exact current project/saved values, warns about separate Tune
  drafts and preserves native confirmation plus existing ownership/job guards and numeric-parameter-only API.
- Selection, disclosures, scroll and focus survive refresh; keyboard Escape and the native picture dialog work;
  late restore completion preserves the tab selected while it was pending. No history writes or schema changes.
- Validation checkpoint: saved-history/restore + geometry regression selection 3 passed (2.19s); initial isolated
  browser selection 1 passed, four desktop/phone light/dark combinations (6.99s). One correction/confirmation round
  pending. Full batch HELD; no real project changes/builds, stress/FEA, installs or provider jobs. Scope and evidence
  limits: docs/usability/2026-11-02/history-story.md. Captures outside git: /tmp/kerf-history-captures.

## 2026-11-02 — Studio History final confirmation (Codex, design-history)
- Final correction keeps table row labels readable and clears fixture toasts through the DOM. The existing History
  browser node passed: **1 passed in 7.33 s**, covering four desktop/phone light/dark contexts, exact comparisons,
  disclosures/focus, cancellation, restore failure, picture dismissal, late-response navigation and empty history.
  This overlaps the earlier browser run; it is not additional unique coverage. Existing browser-marker warning remains.
- Retained the earlier saved-history/restore and geometry regression result: **3 passed in 2.19 s**. No further test
  expansion, project builds, real jobs, geometry or review.json edits. Full batch HELD; stress/FEA remain paused.
- PLAN item complete; ready for manager integration against codex/studio-redesign-base (59f305e). The replacement
  shell and combined onboarding remain the integration owner's validation. Final captures: /tmp/kerf-history-captures.


## 2026-11-02 — First-use studio guidance (Codex, first-use)
- Replaced the interrupting first-run spotlight with an optional contextual page guide. The short tour keeps the
  workspace usable, has Back/End/Escape and focus return, and retains the stable project-build target. Definitions
  now open beside the term by mouse, touch, Enter or Space. The searchable glossary uses a named native dialog,
  labelled search, result count, keyboard-scrollable definitions and explicit empty-search recovery.
- Welcome now starts from the object the user wants to make, gives one direct design action and keeps incomplete
  verification explicit. Successful assistant readiness is a compact disclosure with last-check time and recheck;
  unavailable/auth/usage explanations and disabled design actions are preserved. No automatic tour or design job.
- Mocked browser test tests/test_first_use.py: **1 passed in 8.48s**, covering 1440x960 and 390x844 in light/dark,
  no page errors, GET-only requests, viewport bounds, reduced motion, focus return, tour navigation, glossary
  filtering/recovery and readiness failure states. Two glossary contract tests: **2 passed in 1.63s**. A native
  dialog reverse-Tab boundary was corrected; test waits for its asynchronous close event before asserting removal.
  Browser marker is not registered on this base (existing marker-refresh work is separate).
- Captures inspected in /tmp/kerf-first-use-review: welcome/help/tour/glossary, four contexts each. They include
  the earlier shell. After this pass, scoped CSS removes the welcome's inherited entrance, enlarges close/ready
  hit targets and wraps glossary keys; capture settling and the older start-tour test were made deterministic.
  Per shared usage limit, final CSS confirmation belongs to the manager's single integrated shell review.
- Doctor ALL OK; batch HELD and process checks preceded targeted tests. One Impeccable detector run found only
  existing out-of-scope patterns. No installs, full suite, geometry builds, FEA, review.json, backend or live jobs.


## 2026-11-02 — Definitions directly at the word (Codex, first-use follow-up)
- User requested no typing or menu hunting for definitions. Every marked occurrence now opens its meaning beside
  the word immediately on mouse hover or keyboard focus; touch needs one tap. Native title hints are replaced
  by the same readable definition. The searchable glossary remains optional.
- Hover/focus does not steal focus; pointer travel into the popup keeps it open. Escape and the close button
  dismiss it without reopening during focus return. Definitions retain named dialog semantics and connect the
  focused word to its explanation; viewport placement and reduced-motion behavior use the existing guide.
- Focused mocked browser regression: **1 passed in 5.17s**, desktop 1440x960 and touch 390x844. Covers hover,
  keyboard focus/Enter/Escape, single-tap access, repeated occurrences, pointer continuity, focus restoration,
  bottom/right viewport edges, reduced motion, outside dismissal and GET-only requests with no page errors.
  Initial fixture omitted /api/quotes; adding its empty response corrected the fixture. Existing broad first-use
  and glossary suites were not repeated; their prior results are above. Browser-marker warning remains on base.
- No new dependencies, live jobs, geometry, stress simulation or full batch. Full batch remains HELD. This changes
  the shared definition layer used by project text; controls and code retain their existing exclusion from wrapping.

## 2026-11-02 — Active job and decision story (Codex)
- Active jobs lead with the reported action, provider, state and measured elapsed time. Removed invented percent
  progress and phase-completion inferences; remaining build stages come from the recorded start event, while
  agent work explicitly says when its remaining work is unreported. Notes, actions, stages and logs expand on demand.
- The decision trail keeps source links, findings, options and reasons in native disclosures. Paused, failed and
  stopped jobs no longer appear finished; steering notes show queued/received acknowledgements. Polling preserves
  drafts, disclosure state and keyboard focus; refresh errors retain the last evidence.
- Job.info adds its existing agent identity; thoughtweb adds authoritative job state. No provider/process lifecycle
  changes. Cancellation controls and error logs are preserved.
- Verification: 11 selected pure job/thoughtweb tests passed; tests/test_job_story.py all 7 passed in 48.95 s, using
  static fixtures only at 1440/390 px in light/dark themes. Captures visually reviewed in .cache/job-story/confirmation.
  Shared venv requires PYTHONPATH=$PWD. The browser marker is unregistered on this base (warning only).
- No live app, real agent job, geometry/build, full batch or stress simulation run. Parent integration owns the new
  shell; these captures show this branch's inherited shell around the revised job surfaces.


## 2026-11-03 — Studio journey reliability (Codex)
- Delayed project loads and refreshes now respect the current project visit. My parts provides loading, failure and keyboard retry states; its late load/save replies cannot replace another screen. Empty project polling preserves explicit Work and All projects navigation.
- Guides show loading and recoverable HTTP failures, mark the selected guide, and ignore responses whose original panel has been replaced. The approved Tune exit guard counts invalid drafts as well as valid edits, deduplicates a parameter, and preserves route/draft state when any global exit is canceled.
- Final focused browser node: **1 passed in 10.34 s**, four contexts (1512x982 and 390x844, dark/light), including stale successes/failures, retries, invalid blank/whitespace and zero drafts, all global exits, openSession cancellation, and no unexpected mutation requests. Prior run was the same node before final exit coverage, not an additional distinct test. Captures: `.cache/journey-quality/final/`; inspected phone inventory and desktop guide recovery states.
- `kerf doctor`: **ALL OK** with existing optional firmware-tool warnings. Existing unregistered browser-marker warning remains. No real jobs, geometry, FEA, review.json, full suite or native-app changes. Combined shell/Tune/Files journeys remain assigned to the integration task.

## 2026-11-03 — Object stage: current saved meshes, contextual tools (Codex)
- The actual viewer now opens with full-width geometry, neutral display materials and a compact tool rail.
  Parts, motion, inspection, assembly, shopping, print and checks remain available in dismissible contextual
  trays; optional part colors, edges and ground grid preserve the original data. Warning access stays visible.
  Keyboard parts/inspection, model orbit/zoom/fit, named controls, Escape and reduced motion are supported.
- Current-template delivery reads compatible saved kerf-data for existing files/trial viewer routes, with a
  schema tag on newly generated data and original-file fallback for unsupported/incomplete saved contracts.
  Saved exports are not rewritten. No geometry, catalog, check threshold, review.json, job or FEA changes.
- First visual review used the existing FPV viewer (38 items, two joints) at desktop/phone in both themes.
  The one correction fits projected bounds and reserves actual canvas space beside/above open trays. Existing
  final desktop-light and phone-dark/Parts captures in .cache/viewer-stage/{desktop,phone}-confirm.png confirm
  visible model framing and persistent warnings; these were read again on resume, not recaptured.
- Prior recorded validation: seven helper/route cases passed; three browser nodes passed in 19.42 s.
  Final 14-node confirmation was interrupted and its summary is unavailable. A recovery invocation through
  the shared .venv/bin/pytest entrypoint imported the installed root checkout (missing current_html and #notice),
  yielding 12 failed / 2 passed in 43.89 s; it is not current-branch evidence. No production workaround was made.
  Integration owns the pending final selection: PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_viewer_stage.py
  tests/test_viewer.py::test_page_cut_stress_build_it_compare_and_picture
  tests/test_viewer_build_it.py::test_build_it_labels_closeups_and_bench_context. PLAN remains unchecked until green.
- Full batch remains HELD. No actual project rebuild or native app launch. The surface brief records limits;
  inherited small engineering text was the only mechanical design-detector warning. Combined shell validation
  belongs to the integration owner; this branch is frozen for that handoff.
