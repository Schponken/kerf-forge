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
