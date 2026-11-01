# Kerf Forge architecture

```
description ──► DESIGN.md ──► project.yaml ──► parts/*.py ──► kerf check / build ──► review ──► out/
 (Spencer)     (sizing,      (params, items,   (build123d,      (print checks,        (design-     (STEP, STL, 3MF
                interfaces)   joints, reqs)     kerf.iface)      sweeps, fasteners,    reviewer)    plates, BOM,
                                                                 requirements)                      renders, viewer)
```

## Package map
| Module | Job |
|---|---|
| `kerf/ctx.py` | What a part's `build(ctx)` gets: `ctx.p` params, `ctx.cat` catalog, joint + fastener-site declarations, `ctx.finish()`; `ctx.keep_sharp(at, why)` declares an inside corner sharp on purpose |
| `kerf/iface.py` | Mating-feature generators (bolt patterns, inserts, nut traps, bearing seats, servo/horn/motor/stack mounts, `pin_hole` for pinned hinges). Each returns a cutter solid and registers fastener (or pin) sites |
| `kerf/drives.py` | Printed spur-gear pairs (py_gearworks, FDM backlash, standard centre distance) and GT2 belt maths (length, tooth count, centre for a stock belt, wrap) + belt keep-out solid |
| `kerf/proxies.py` | Purchased parts and keep-outs built from the catalog, with their joints and fastener sites |
| `kerf/catalog.py` | Loads `catalog/hardware.json` (every entry has a `source`) |
| `kerf/project.py` | Loads project.yaml, evaluates params/derived, builds every item |
| `kerf/assembly.py` | Joint tree, solve poses, interference, motion sweeps, coupled poses, fastener alignment + screw lengths |
| `kerf/features.py` | Detailed-modeling helpers: swept channels, uniform shell, gussets, teardrop holes, printed ISO threads (bd_warehouse, phase-matched rod/hole), gear pairs (= drives.spur_pair), snap hooks + living hinges with a strain check, text labels, lightening pockets with a minimum web, `safe_fillet` (applies edge groups one by one, reports failures); `fillet_inside(ctx, body, r, keep=)`: rounds every corner kerf.edges reports with kerf.coves prisms (r, then r/2; no OCC fillet, which can crash; coves gmsh cannot mesh are dropped; corners under a ceiling stay square), keep(at) -> reason declares the mating ones |
| `kerf/access.py` | Assembly access, run by every check: hex-key reach for every male screw site (straight, else 25 deg ball-end = warning, else problem; catalog `tools.hex_key`) and insertion paths for items with `insert: {direction, distance}`; results in report.json `assembly.hex_keys` / `assembly.insertion` |
| `kerf/pins.py` | Pinned hinges: every `pin_hole` of a group coaxial (0.05 mm), pin held (press/heatset/tap) on one side of each moving joint and free on the other, the joint turning about the pin axis, and a stocked pin/screw length that reaches every hole |
| `kerf/holewall.py` | Material around every fastener hole of a printed part: a ring at hole radius + min wall (insert: catalog `insert_wall`, else 0.8 mm) must be >= 95 % material over the working depth (PROBLEM: the hole breaks out), and a ring at 1.5 d from the centre >= 90 % (WARNING: s7 edge distance) |
| `kerf/checks.py` | Per-part print checks in print orientation (solids, validity, bed fit, watertight, overhang, wall thickness, `load_axis` across layers, mass) |
| `kerf/requirements.py` | Engineering checks named in project.yaml (`@check("name")` registry), incl. `fea_static` |
| `kerf/fea.py` | Linear static FEA of one part (gmsh quadratic tets + scikit-fem); force, pressure, torque and bearing loads; validated in tests/test_fea.py, tests/test_fea_loads.py |
| `kerf/fea_render.py` | Von Mises colour picture per FEA check (`out/renders/fea_<id>.png`) |
| `kerf/geom.py` | Geometry helpers: volumes, exact overlaps, meshes, mesh-based overhang / wall-thickness analysis, world points/directions of a Location |
| `kerf/req_balance.py` | Balance requirement `cg` (assembled centre of gravity incl. purchased parts and payload, vs a reference line, over poses) |
| `kerf/vendor.py` | `proxy: step` vendor CAD models: loads catalog/models STEP, keeps the base proxy's joints and sites, refuses a model whose bbox or holes disagree with the catalog |
| `kerf/viewer.py` | Writes the self-contained `out/viewer.html` (meshes, joint sliders from the engine's own kinematics, explode, BOM, print info). Written after ASSEMBLY.md. **Cut**: a clipping plane on X / Y / Z (starts through the printed parts, keeps the far side), cut faces hatched (back faces inside a closed part). **Stress**: each `fea_static` surface field (pipeline `fea_viz`, part frame) moved to the home pose and mapped onto the viewer vertices (4 nearest FEA surface triangles, inverse-distance, worst load case), stored as one byte per vertex = utilisation × 200. **Build it**: `assembly_steps()` = kerf/ship.py `plan()` per step (parts already on, parts going on with `_explode_offset`, bench sub-assemblies joining as one group, heat-set insert sites, screws with seat point + axis from the fastener check, joints to demonstrate) + the step's ASSEMBLY.md text (`## Step N` sections; earlier sections = intro, later = outro); the page animates it (occlusion-tested camera per step, screws turning home, inserts pressed, joints swept, done ticks in localStorage). `snapshot()` (picture for Studio cards) and `compare()` (ghost + per-vertex change colours from Studio) are page APIs. Tests: tests/test_viewer.py |
| `kerf/attribution.py` | Face → part-file line and project param that produced it (viewer click-to-edit) |
| `kerf/gallery.py` | `kerf gallery`: one page for every project (build / review / eval status, printed and bought counts, mass, plates, BOM total, renders as JPEG, requirements, BOM, link to each 3D viewer) in out/gallery/, with files.json mapping published paths for the Artifact tool |
| `kerf/find.py` | Search-first: `kerf find "<description>" --project <p>` searches Printables (public GraphQL; top hits' STLs downloaded and measured), Thingiverse (official API, `THINGIVERSE_TOKEN`), and lists the web searches for MakerWorld/GrabCAD and the McMaster link for hand-downloaded STEP files; writes a candidates table (license -> what Kerf may do, key dimensions) with a `Decision:` line into REFERENCES.md; `--add` records a hand-found candidate; `kerf check` warns while a decision is TODO |
| `kerf/calibrate.py` | Print-truth loop: `kerf calibrate` writes a fit coupon (M2/M2.5/M3 clearance, pilot and heat-set holes, 608/623 pockets, 3 mm dowel holes at 0.2/0.3/0.4 slip + press, MG90S window) with a CARD.md; `kerf feedback <material> hole_M3=tight ...` stores per-printer+material diameter offsets with dated history in `catalog/printers/<printer>.json`; iface applies them (screw holes, bearing seats, servo windows, pin allowances) while a part builds; the profile is part of the project fingerprint |
| `kerf/diagnose.py` | Self-correcting build errors: an exception from part code becomes part + file line + operation (fillet, chamfer, sweep, iface.*, ctx.p, catalog) + a computed `fix:` hint (largest fillet/chamfer the same edges take, nearest param/name/catalog key, the material a heat-set or pilot hole needs); in the PROBLEM line, report.json `diagnoses{}`, and fed first by the after-edit hook |
| `kerf/heads.py` | Socket screw heads as solids fixed to the part they seat on (catalog head_d x head_h), so interference and every sweep check a head standing proud of a moving part; countersunk heads are skipped |
| `kerf/shanks.py` | Screw bodies: after fastener sizing, each screw (head seat to tip, 0.8 d cylinder) must not run into any item but the two it joins (a tip poking out of a nut into a neighbour, a screw reaching a prop disc) |
| `kerf/electrical.py` | Complete electrical system from `electrical:` + `wiring:`: power tree, current per item and run (avg + peak), hover power (momentum theory), ratings (battery C, BEC/ESC outputs, connectors, wire ampacity + burst heating, input voltage), routed wire lengths |
| `kerf/req_electrical.py` | Electrical requirements `power_budget`, `flight_time`, `run_time`, `connector_access` |
| `kerf/req_gears.py` | Requirement `gear_bending`: Lewis tooth bending of a spur pair at actuator stall |
| `kerf/aero.py` | Fixed wings: airfoils (NACA 4-digit generated; UIUC .dat files in catalog/airfoils, Selig or Lednicer, data in airfoils.json), `Planform` (straight-tapered swept wing from the centreline: chord, LE, twist, sections; `geometry()` = area, AR, taper, MAC, its station and LE x, neutral point at quarter MAC), `wing_solid` (ruled loft of polygon sections, TE thickened to `te_min`: exact volumes), `spar_point` / `spar_line` / `spar_channel`, `elevon_split` (bottom hinge at a chord fraction, top V gap, ends square to the hinge), stall speed, Reynolds number, elliptical-lift root moment. Tests: tests/test_aero.py |
| `kerf/req_aero.py` | Requirements `static_margin`, `wing_loading`, `stall_speed`, `spar_bending`, judged on the planform in params (`wing_` prefix) |
| `kerf/hole_axes.py` | Horizontal holes cut round (iface knows whether it cut a teardrop): pin holes = problem, fastener holes = warning (ENGINEERING s4) |
| `kerf/req_stops.py` | Requirement `hard_stop`: a joint moved past an end of its range must collide (proves a mechanical stop) |
| `kerf/wiring_out.py` | `out/WIRING.md`, `out/wiring.svg`, the solder/wiring steps appended to `out/ASSEMBLY.md`, and the BOM rows for wire and heat-shrink; buy links from catalog sources. Routes are told by landmarks (`landmarks`: a waypoint `item.joint` is "item's joint", a free point is "along/near" the nearest part and its nearest named feature within 12 mm; never coordinates); a signal run's `pin:` is named at the controller end with the Pi's physical header pin (and the GND pin next to it for a 2-conductor run); every electrical `bom_extra` row (a capacitor, a USB supply) gets its own fitting step |
| `kerf/progress.py` | Progress events for Kerf Studio: with KERF_PROGRESS=1 the pipeline and requirement runner print one `@@{json}` line per event (start with stage/part/requirement lists, stage, part, sweep, req, done). Off by default, so CLI output is unchanged. Tests: tests/test_studio.py |
| `kerf/stressmap.py` | Turns each part's FEA stress fields (all its load cases, element by element) into design feedback: utilisation (stress / allowable), % of volume idling below 15 %, hot and cold zones (part frame). report.json `parts.<p>.stress`; a part whose strength checks never pass 25 % utilisation and whose deflection checks stay under half their limit gets an 'overbuilt' warning naming where material idles. Tests: tests/test_fea.py |
| `kerf/drawings.py` | Engineering drawings with cadgen 0.8.4 `eng_drawing` (MIT): `kerf build` writes out/drawings/<part>.pdf per printed part (top/front/right third angle + iso, overall dimensions, one hole callout per interface hole group with diameter / depth or THRU / counterbore MEASURED on the part at its sites and pins, title block + notes with material, walls, infill, print orientation) and out/drawings/index.json. Smallest sheet A4..A2 at the largest scale where views AND annotations stay inside the frame. Cached per part with the build cache. cadgen telemetry is switched off (CADGEN_TELEMETRY=0). Studio Files tab lists the PDFs. Tests: tests/test_drawings.py |
| `kerf/urdf.py` | URDF export for projects with moving joints: `kerf build` writes out/<project>.urdf, out/urdf_meshes/<item>.stl and out/<project>_urdf.zip. Links = items moving together (rigid / zero-range joints merge into the parent link, keep-outs left out), revolute / prismatic joints with the joint-tree ranges as limits, `sweeps: {joint, follows, ratio}` couplings as <mimic>; link frames parallel to the assembly frame at all-joints-zero with the origin on the parent joint axis; inertials from each item's check mass spread over its mesh (trimesh) summed per link with the parallel-axis theorem; SI units. Validated with cadgen.urdf_source (errors = build problems). Tests (tests/test_urdf.py) load it in PyBullet and compare forward kinematics with Kerf's own joint solver. |
| `kerf/sections.py` | Structural section generators (re-exported in kerf.features): `section_profile` (rect, I, T, C, box, tube) in textbook or print-ready form for the side on the bed (45 deg chamfers under flanges, peaked hollow ceilings, teardrop tube; refuses I / T lying on their side), `beam(path, section, depth=f(s), width=f(s), wall, up, bed)` by sweep or loft (taper with the moment), `fork_link(L, ends, section, depth, taper, channel_d)` (pivot bosses with round vertical bores, solid body with root fillets hollowed between the bosses, teardrop wire channel), `rib_along(face, path, h, t)`, `teardrop_channel`, `bending_I` (area + second moment of a cut, via requirements.section_props). Tests: tests/test_sections.py (hand formulas, zero overhang) |
| `kerf/idioms.py` | Mechanical idioms (re-exported in kerf.features), detail features built in: `boss` (revolved root fillet), `side_plate` + `clevis` (fork of two side plates, filleted webs; robot_arm upper_arm / forearm), `yoke_cheek` (cheek on a foot, root + end fillets, gussets; robot_arm yokes via parts/armlib.py), `servo_cradle` (plate sized to a catalog servo's tab screws + iface.servo_mount), `cable_saddle` (groove + cable-tie tunnel with a peaked roof; catalog wire.cable_tie_2_5), `grip_pad` (90 deg serrations or a dovetailed TPU-insert pocket). Tests: tests/test_idioms.py |
| `kerf/intent.py` | Design-intent ledger + lint: `ctx.add(shape, why=, kind=)` / `ctx.cut(...)` record each feature (op, kind, why, where, volume); iface features register themselves through ctx.site / ctx.pin_site (one row per interface group and hole type, with the count). The ledger is `shape.kerf_features` -> report.json `parts.<p>.features` -> the viewer Print tab's "Feature / Why" table; cached with the part. `unexplained(src)`: body booleans (the variable passed to ctx.finish) with no ctx.add/cut, no iface / idioms / features / sections call and no `# why:` comment on or above the line; the after-edit hook reports them as context (not a block). Tests: tests/test_intent.py |
| `kerf/partcache.py` | Per-part build cache: key = part source + project helper files + resolved params + spec + printer fit profile + engine version (kerf/*.py, build123d), plus the catalog entries the part read (hashed on lookup). Stores the exact BREP and everything `ctx.finish` attached (sites, pins, joints, notes, BOM, colour) and the part's print-check results under .cache/parts/, so `kerf check` / `kerf build` / Studio rebuild and re-check only changed parts. `KERF_NO_CACHE=1` bypasses it; `kerf verify` and kerf/attribution.py always build fresh. Tests: tests/test_partcache.py |
| `kerf/edges.py` | Sharp inside corners: every unfilleted concave straight edge between two planar faces of a printed part (>= 2 mm), corners within 6 mm of an interface site exempt (fastener features). report.json `parts.<p>.sharp_inside`; one warning per part, corners in the stress map's hot zones first. Tests: tests/test_edges.py; `split_kept` moves ctx.keep_sharp corners to report.json `sharp_kept` with their reason |
| `kerf/coves.py` | Concave fillets by boolean: `cove_fillets(shape, edges, r)` (and `cove_sharp(shape, radii, only=, skip=)`: every sharp inside corner in or out of boxes, one call so attribution does not line-trace a per-edge loop in the part file) unions a fillet-shaped prism (corner, two exact tangent points, minus the arc disc) into each straight concave edge between two flat faces; edges whose faces end within r are skipped and reported. Use where OCC's fillet fails or crashes (segfault on many-slab bodies, e.g. robotic_gripper_desk gripper; rack tooth roots). Tests: tests/test_coves.py |
| (report.json, maker-facing) | `mass`: printed_g / on_board_g / device_g (headline) / off_board_g; each requirement carries `unit` and `bound` (max / min / range / clear, requirements.UNITS; requirements.describe -> "0.55 kg·cm (max 4.7)"); `maker_notes`: warnings that change what the builder does, rewritten as instructions (pipeline.maker_notes: ball-end key, self-tapping near an edge); everything else stays in `warnings` for the designer. Tests: tests/test_maker_output.py |
| `kerf/studio.py` | `kerf studio`: local web app (stdlib http.server on 127.0.0.1; page in kerf/assets/studio.html). Lists projects with build/review state, serves each project's out/ files and viewer, runs check / build / trial / build-all / new-design jobs as subprocesses with streamed logs. A trial copies the project to .cache/studio/<p> with new params (the real project is untouched); Save edits project.yaml params in place, keeping comments, within each param's min/max. New design runs `claude -p "/kerf ..." --output-format stream-json`. tools/mac/install_app.sh wraps it as ~/Applications/Kerf Studio.app on the Dock. Tests: tests/test_studio.py Also: a welcome page when there are no projects; Build / Check / Build-all show how long they usually take (median of the last Studio runs in .cache/studio_times.json, else the last report's time); every Studio build saves a version (.cache/studio_history/<project>/<stamp>: values, results, cost, mass, picture, commit) shown in the History tab with what changed since, and "Restore these values" writes that version's params back (part code is never touched); the Tune tab shows each param's unit (`unit:` in project.yaml, else assumed and marked) and which parts and checks it reaches (`param_effects`), and puts a tried design's results next to the saved build's; the header shows cost, filament grams and device mass; `/export/<p>.zip` = plates, parts, STEP, BOM, guides, drawings, bring-up program and the design files New design asks intake questions (budget, power, mounting, environment, printer, material) and can quote first: a `quote` job has Claude write 2-3 options (cost, print hours, part count; kerf skill "Quote mode") to .cache/studio/quotes/<name>.json, `read_quote` checks them, and the picked option goes into the design brief. "My parts" edits catalog/inventory.json (`save_inventory`: priced keys only). **Do it / Change something**: `edit_job` runs `claude -p` with the request, scoped to one project (env KERF_STUDIO_JOB, also set for new designs); the viewer inside Studio calls `window.kerfStudio.edit`. **Duplicate**: copies design files only (no out/, no review) and retitles project.yaml; an optional change starts an edit job on the copy. **Materials**: per printed part from the catalog (strength XY/Z, stiffness, density, $/kg from prices.json), tried with the params (`trial_copy(..., mats)`) and saved with `write_materials` (flow or block YAML, comments kept). **Compare**: each Studio build version also stores its geometry (`geom.json.gz`, from viewer.html); `compare(name, source, target)` = per-vertex closest-surface distances both ways (trimesh, 0.05 mm steps) + per-part added / removed / changed; the Tune tab compares a Try with the saved design. **Pictures**: the viewer's own transparent snapshot, kept per geometry fingerprint in .cache/studio_thumbs (cards, all-projects grid). **Notifications**: osascript (macOS, with sound) / notify-send when a job of 20 s+ (any Claude Code job) ends, unless switched off (.cache/studio_settings.json); the page chimes. Tests: tests/test_studio_features.py |
| `kerf/bambu.py` | `kerf print <p>`: orients each printed part (24 axis-aligned rotations scored on one tessellation: bed fit, `load_axis` within 30 deg of the layers, least >45 deg overhang, then height; the yaml `print_rot` is kept unless another needs clearly less support, and every change is reported), packs plates into `out/print/`, slices each with the Bambu Studio / OrcaSlicer CLI (full exported machine/process/filament JSON from `~/.kerf/bambu.json`) to `.gcode.3mf`, and with `--send N` uploads plate N over FTPS (implicit TLS, 990) and starts it with MQTT `print.project_file` (TLS 8883, Developer Mode), polling `pushall` reports until it starts; without a slicer config it writes the plates and opens them in Bambu Studio / Bambu Connect; `--dry-run` prints every command and payload (access code masked) |
| `kerf/meshy.py` | Creative mode: a `source: meshy` part's cached Meshy model is scaled to `bounds`, repaired per connected piece (merge + fill holes, else voxel remesh) and unioned, then fused with the part's B-rep features and cut by its `ctx.mesh_cut` solids in mesh space (manifold3d), simplified at 10 um; the result rides on the shape as `kerf_mesh` and geom uses it for print checks, overlaps, bbox, volume, STL/3MF/plates and GLB, while joints, fastener/pin sites, FEA and STEP keep the exact features; a missing model reports the prompt and path to generate |
| `kerf/ship.py` | Ship package: prices every BOM row from `catalog/prices.json` (dated snapshot: buy link, pack qty/price, source; keys = catalog path, `screw:M3x8:socket` -> `screw:M3:socket`, `insert:M3`, `nut:M3`, `dowel:3x16` -> `dowel:3`, `material:PETG` per gram, or a bom_extra / `ctx.bom_item` row's `price_key` - a list = exact pack then a fallback pack, flagged on the row; `included: true` rows ship with another item and cost 0), adds buy / unit $ / total $ columns, the per-piece total and the whole-pack cost to `bom.md`/`bom.csv` (export.tidy merges identical rows first: one row per thing to buy, shared notes said once, hinge names folded into one 'hinges ...'); tests/test_ship.py fails if any project's purchased item or extra row has no priced shop entry; writes `out/ASSEMBLY.md`: Step 0 test-fit / `kerf calibrate` (or the applied printer profile), Step 0b servo centring (kerf/firmware.py), then root first, `assembly.order` (unnamed items right after their parent); a step whose part mates onto a parent fitted LATER is a bench sub-assembly joined at the parent's step (`joins`), and every screw / pin goes in at the step and phase where its parts first form one piece (no forward references); screws carry hand-feel tightening, long notes are split into sub-bullets, off-board items go under "Bench electronics (not mounted)"; per step the heat-set inserts to press first, pins, screws (driven when the later of their two parts goes on), bench sub-assemblies from `key_access`, its `insert` path (checked clear) and `assembly_note`, per screw group the `bom_extra` rows with that `group` and ball-end key warnings, and an iso render in `out/assembly_steps/` with the new part pulled back along its mating joint axis (or its `insert` path) Parts on hand (catalog/inventory.json, "My parts") cover BOM rows first: not bought, not counted in the cost, named in BOM.md |
| `kerf/autofix.py` | `kerf fixes <p> [--apply] [--heatset]`: the last check's common findings as edits of the part code, made with the Python AST on the iface call that names the finding's group: a horizontal hole cut round -> `teardrop="auto"` (iface works the angle out from print_rot); a self-tapping hole near an edge -> `"heatset"` (opt-in: the insert bore is larger); bosses, thin walls and sharp corners are listed for the designer |
| `kerf/printpkg.py` | Print package: per plate grams (the build's mass estimate) and print time (a Bambu Studio / OrcaSlicer command line slices each plate when found - KERF_SLICER or the usual install paths - and its own prediction is read from the sliced 3MF; otherwise a lower bound: plastic volume at the filament's max volumetric speed), material settings from Bambu Studio's profiles (nozzle, bed, plate, fan), per part orientation in words, layer height, supports (on for `supports: needed` or > 5 % of the surface steeper than 45 deg) and brim (outer 5 mm when height > 3 x the narrow footprint side) in `out/plates/PRINT_SETTINGS.md` and in each plate 3MF's per-object settings (layer_height, enable_support, support_type, brim_type, brim_width, infill, wall loops) |
| `kerf/firmware.py` | Bring-up / sweep-test programs from the `wiring:` signal rows' `pin:` (Nano `D9`, Pi `GPIO18`, PCA9685 `ch3`, flight controller `M4`) and each servo's horn-joint range: an Arduino sketch (Nano direct, or Nano + PCA9685) or a Raspberry Pi Python script (hardware PWM, `dtoverlay=pwm-2chan`) in `out/firmware/`, plus BRINGUP.md (flight-controller projects: a props-off first power-up checklist). Commands: c centre (1500 us), s sweep, j/+/- jog, x stop. Degrees use the smallest us/deg the servo's datasheet allows (`servos.<x>.pulse_us` / `pulse_travel_deg`, else 1000-2000 us = 180 deg), so a joint never moves further than commanded; the automatic sweep stays inside +/- the smaller end of the range because the servo's + direction is unknown. ASSEMBLY.md Step 0b uses it to centre servos before any horn goes on |
| `kerf/export.py` | STEP assembly, STL/3MF per part, plate packing, GLB, BOM (with a buy / source link column) |
| `kerf/pipeline.py` | Runs everything for a project, writes `out/report.json`, renders via `tools/render/render.mjs` (parts drawn as plastic, not glTF's default metal; near-black parts lifted with light edges; a 10 mm grid plate as the floor; `labels` = call-outs with leaders, `focus` = camera framed on those nodes with context, `title` = a line on the sheet). Assembly-step images: a bench sub-assembly alone, otherwise the parts on so far plus this step's parts in colour, framed and labelled, this step's screws in red backed out of their holes, earlier screws grey; part sheets carry the overall size and show the part as printed on the plate |
| `kerf/cli.py` | `kerf doctor | gallery | check | build | verify | review-status | new | status | calibrate | feedback | find | fixes | price | print | studio` |

## project.yaml
```yaml
name: Servo test rig
printer: Bambu Lab A2L          # bed size for checks and plates
supports: allowed               # or "avoid": any overhang > 45 deg fails
params:                         # shared by every part; sliders in the viewer
  arm_len: {value: 100, min: 60, max: 140, label: Arm length}
derived:                        # python expressions over params (math functions allowed)
  hub_r: arm_len * 0.1
layout: parts/layout.py         # optional: def layout(p, cat) -> dict of shared values computed from params + catalog
                                # (hole positions, seat heights) that several parts must agree on; added to ctx.p
parts:                          # printed parts
  bracket: {file: parts/bracket.py, material: PETG, qty: 1, print_rot: [0, 0, 0], infill: 0.3, load_axis: X}
  # wing / fin parts add `airfoil: mh45` (catalog/airfoils or a NACA 4-digit name; reported per part, must exist);
  # thin-wall printed wings set `walls: 1` and a low `infill` so the mass estimate matches the print   # load_axis: main stress direction (part frame); warned if > 30 deg across layers
  # any part or purchased item may add  insert: {direction: [0, 0, -1], distance: 30}  (own frame, the way it moves
  # going IN): kerf check slides it (and what is mounted on it) in from that far and reports collisions on the way;
  # with assembly.order, parts installed after it neither ride along nor block
purchased:                      # catalog-backed proxies (real mass + geometry for collisions)
  servo: {catalog: servos.MG996R, proxy: servo, groups: {tabs: bracket_servo}}
  horn:  {catalog: servo_horns.aluminum_25T, proxy: horn, groups: {holes: horn_arm}}
  psu:   {catalog: ..., proxy: box, render: false}  # render: false = left out of the GLB views/renders only (an
                                # off-device supply that would shrink the device in them); still checked, in STEP + BOM
  # Every purchased item must be held: by a screw or pin the checks see, or by saying how (`held_by:`), or by saying it
  # lives off the device (`off_board:`). Otherwise `kerf check` warns "nothing holds it" (pipeline.unattached).
  #   bearing: {..., held_by: "press fit in the base tower's seat"}     strap / cable tie / glue / snap-on likewise
  #   psu:     {..., off_board: "on the desk beside the rig"}  -> not a "fit onto" step: ASSEMBLY.md lists it under
  #            "Off the device (not mounted)"; its mass is report.json mass.off_board_g, not the device headline
keepouts:                       # volumes nothing may enter (prop discs, camera view, fingers)
  prop_1: {catalog: drone.props.5_1in, proxy: prop_disc, owner: motor_1}
  cam_view: {catalog: boards.rpi_camera_module_3, proxy: view_cone, length: 30, owner: camera}  # FOV frustum from the
                                # catalog (or spec `hfov_deg`, `vfov_deg`, `aperture: [w, h]` at the lens); join it to
                                # the board's `lens` joint (camera boards with lens_offset)
assembly:
  root: base
  joints:                       # parent.joint_label -> child.joint_label; child joints are always rigid
    - {parent: base.bracket_seat, child: bracket.base}
    - {parent: servo.output, child: horn.spline, name: swing, range: [-90, 90], home: 0}
  order: [base, bracket, servo, horn, arm]   # optional build sequence (ids or [ids]); a screw is driven when the later of
                                # its two parts goes on, so only parts installed by then can block its hex key; an
                                # `insert:` item's children installed EARLIER stay put and block it (servo in last
                                # onto a mounted horn), same-step children ride along
  allow_overlap:                # only with a physical reason
    - {pair: [servo, horn], max_mm3: 60, why: horn spline engages the servo output shaft}  # horn proxies with
      # catalog spline_engage get a spline bore and sit that far down over the spline, so need no allowance
  key_access:                   # assembly order for the hex-key check: these items go on after the group's screws
    - {group: hub_motor_top, before: [motor_plate, motor_bottom], why: top motor is screwed on before the bottom plate}
  sweeps:
    - {joint: swing, samples: 13}             # finer sweep for one joint
    - {name: curl, poses: [{mcp: 30, pip: 30}, {mcp: 80, pip: 80}]}   # coupled poses
    - {joint: driven, follows: drive, ratio: -0.5}   # geared/belted: `driven` turns ratio x `drive`, never alone
requirements:
  - {id: arm_torque, check: static_torque, joint: swing, actuator: servo, payload_g: 50, payload_at: arm.tip, max_fraction: 0.5}
  - {id: base_cg, check: cg, ref: base.yaw, max_lateral_mm: 20, max_along_mm: 40, payload_g: 50, payload_at: arm.tip, poses: [{shoulder: 90}]}
                                # CG vs the line through ref (or point) along axis (default vertical); worst over home + poses
  - id: bracket_fea               # finite-element strength check of one printed part (part frame, mm, N)
    check: fea_static
    part: bracket
    direction: z                  # judge against layer-direction strength when the load crosses layers
    sf: 2.0
    max_disp_mm: 0.3
    fixed: {box: [[-200, -1, -1], [200, 200, 0.01]]}             # or {sites: group, radius: r} / {near_joint: label, radius: r}
    loads: [{box: [[1, wall_t - 0.01, pivot_h - 12], [40, wall_t + 0.01, pivot_h + 12]], force_n: [0, 0, 18.6]}]
  - id: arm_root                  # beam-theory sizing check at one cross-section (fast; FEA stays the proof)
    check: cantilever_stress
    part: arm
    section: {name: root, at: [12, 0, 0], normal: [1, 0, 0]}   # part frame; normal points toward the loads
    loads: [{at: tip, force_n: [0, 9.2, 0]}]                    # joint label or [x, y, z]; any number of loads
    load_case: stall into obstacle
    sf: 2.0
    kt: 1.0                       # stress concentration (holes/notches at the section)
    direction: auto               # auto = from print_rot (stress along build Z uses Z strength); or xy / z
  - id: tendon                    # internal channel open end to end (tendon, wire, air)
    check: channel_clear
    path: [{item: base, at: [0, 0, 5]}, {item: base, at: tendon_exit}, {item: tip, at: [20, 0, 4]}]  # [x,y,z] or joint label, item frame
    diameter: 1.5                 # tendon/wire diameter PLUS the running clearance you want
    poses: [{mcp: 80, pip: 80}]   # checked besides home; the path follows the parts
    ignore: [tendon]              # items allowed inside the channel
```
Requirement checks (all in `kerf.requirements.REGISTRY`; arguments in each function's docstring):
| check | arguments (main) | value |
|---|---|---|
| `mass_max` | `max_g`, `include` | estimated mass (g) |
| `size_max` | `max_mm` [x, y, z] | assembled bounding box at home |
| `distance` | `a`, `b` (item.joint), `min_mm`/`max_mm`, `pose` | joint-origin distance (mm) |
| `clearance_min` | `a`, `b`, `min_mm`, `joints`, `samples` | smallest gap over the sweeps |
| `static_torque` | `joint`, `actuator` or `stall_kgcm`, `max_fraction`, `payload_g`, `payload_at`, `poses`, `gravity` (direction, default [0, 0, -1]; e.g. a device used on its side) | worst gravity torque (kg·cm) |
| `thrust_to_weight` | `thrust_g_total`, `min_ratio` | thrust / all-up mass |
| `fea_static` | `part`, `fixed`, `loads`, `sf`, `direction`, `max_disp_mm` | stress / deflection (FEA) |
| `cantilever_stress` | `part`, `section`, `loads`, `sf`, `kt`, `direction` | beam-theory stress at a section |
| `cg` | `ref` or `point`, `axis`, `max_lateral_mm`, `min_along_mm`/`max_along_mm`, `include`, `payload_g`, `payload_at`, `poses` | CG offset from the line |
| `tip_over` | `min_deg`, `support`, `poses`, `payload_g`, `payload_at` | smallest tip-over angle (deg) |
| `channel_clear` | `path`, `diameter`, `poses`, `ignore` | largest diameter that passes (mm) |
| `hard_stop` | `joint`, `beyond` (a value past an end of the range), `min_mm3` (default 1) | parent/child overlap at `beyond` (mm3) |
| `static_margin` | `min` (0.05), `max` (0.15), `wing` (param prefix, `wing_`) | (neutral point x - assembled CG x) / MAC (range) |
| `wing_loading` | `max_g_dm2`, `wing` | all-up mass / wing area (g/dm²) |
| `stall_speed` | `max_kmh`, `cl_max` (wing; else 0.9 x airfoil clmax x cos quarter-chord sweep), `airfoil`, `wing` | sea-level stall speed (km/h) |
| `spar_bending` | `tubes` (catalog tube paths in one half), `y_root` (mm, where they leave the centre section), `load_factor` (6), `sf` (1.5), `wing` | spar stress at y_root under load_factor g, elliptical lift, tubes sharing by E I / (strength / sf) |
| `gear_bending` | `module`, `z_driver`, `z_driven`, `width`, `torque_nmm` (the driving actuator's stall), `material`, `sf` (3), `direction` | Lewis tooth-root stress (MPa, Shigley Table 14-2 form factor) vs strength / sf |
| `prop_clearance` | `min_mm`, `min_between_mm`, `props`, `ignore`, `joints`, `poses` | tightest prop-disc gap (mm) |
| `power_budget` | (`fm`, `eta`) — reads `electrical:` / `wiring:` | worst load / rating (must be <= 1) |
| `flight_time` | `min_min`, (`fm`, `eta`) | hover minutes on usable capacity |
| `run_time` | `min_min` | minutes at every load's average draw |
| `connector_access` | `item`, `direction` (item axis), `length_mm`, `size`, `at`, `ignore`, `pose` | `clear` or the items in the way |

`cantilever_stress` cuts the part with the section plane, takes the section's area and second-moment tensor, and
reports kt x max |N/A + unsymmetric bending stress| over the outline. Torsion is reported, not included.
`tip_over` (`min_deg`, optional `support: [items]`, `poses: [{joint: deg}]`, `payload_g` + `payload_at: item.joint`)
finds the floor contacts (mesh points within `tol` 0.5 mm of the lowest point), takes their convex hull and reports the
smallest atan(CG-to-edge distance / CG height) in degrees over the poses; negative means it falls over by itself.

`channel_clear` sweeps a ball along the polyline at every pose and reports the largest diameter that passes (0.01 mm).

`prop_clearance` (`min_mm`, optional `min_between_mm` tip-to-tip, `props`, `ignore`, `joints` to sweep (default all),
`samples`, `poses`) measures every prop disc (keep-out, `proxy: prop_disc`) to every other disc and to every non-keep-out
item except its `owner` and allow_overlap partners, at home and over the sweeps, and reports the tightest gap.
FEA loads: region keys (`box`, `sites`, `near_joint`, `cylinder: {at: [x,y,z] | joint, dir, r, tol: 0.3, span}`
for a bore, or `any: [region, ...]` for a union, e.g. `fixed` at both pivots) plus one of `force_n: [fx,fy,fz]` (total, spread evenly), `pressure_mpa: p` (into the surface),
`torque_nmm: T` with `axis: {at, dir}` (tangential, proportional to radius) or `bearing_n: [fx,fy,fz]` (cosine pressure
on the half of a bore facing the load; when the pin group puts the other parts' bands off this part's, the single-shear
lever moment is added automatically, `single_shear: false` opts out). Each FEA result reports `applied_force_n` / `applied_moment_nmm` (part origin),
and `kerf build` writes `out/renders/fea_<id>.png` (kerf/fea_render.py: von Mises, magenta above the limit).
Numbers inside requirement regions and forces may be expressions over params/layout values.

## Electrical (`electrical:` + `wiring:`; kerf/electrical.py)
Every project that moves or powers anything declares its whole electrical system: each board, ESC, receiver, BEC,
battery, connector, strap is a catalog-backed purchased item, and every connection is a run:

```yaml
electrical:
  battery: battery            # the pack item (catalog cells, capacity_mah, c_rating, c_burst)
  # supply: psu               # ...or a mains adapter (catalog output_v, current_a): rated by current, no run time
  burst_s: 5                  # longest full-power burst (s) for wire heating; default 5
  usable: 0.8                 # usable capacity fraction (80 % rule); fm / eta / bec_eff override the defaults
  # cruise: {speed_kmh: 70, l_over_d: 8, eta: 0.5, why: "..."}   # fixed wing: motor draw = W V / (L/D) / eta instead of hover
  draw: {rx: {avg_a: 0.1, peak_a: 0.1, why: "..."}}         # only where the catalog has no current figure
  limits: {stack: {peak_a: 100, why: "ESC current limit configured to 25 A per motor"}}   # a real, set cap
  # kind: current_limit (default: configured and enforced) | throttle_estimate (how hard it will be driven: the wiring
  # is then rated for peak_a x 1.15, since nothing stops the real current exceeding an estimate)
wiring:
  - {id: main, from: xt60, to: stack, kind: power, v: 25.2, gauge: 12, color: red/black, length_mm: 90,
     route: [top_plate.xt60, body.stack]}            # waypoints: item, item.joint or [x, y, z]; ends = item centres
  - {id: ph1, from: stack.esc, to: motor_1, v: 25.2, gauge: 20, conductors: 3, length_mm: 120, route: [arm_1.motor]}
  - {id: crsf, from: stack, to: receiver, kind: signal, gauge: 28, length_mm: 60}
```
- Wire ends: `ends: {from: screw, to: header}` on a run, else the item's catalog `terminal`, else `solder`
  (solder | screw | lever | header | plug): the WIRING/ASSEMBLY step says what to do at each end and heat-shrink is
  counted only for soldered ends. `power_budget` also checks voltage drop: each load's input after the IR drop of
  every +/- pair back to its source or regulator, at average current (40 C wire, must be >= its voltage_min) and at
  peak (100 C wire, reported as a brief sag, not failed); skipped where the catalog gives one nominal voltage.
- `ends` also takes `crimp` (a female 0.1 in crimp pin per conductor in a 1x3 housing, pushed onto a male header;
  pins + housings go in the BOM). `screw` ends get a bootlace ferrule per conductor (catalog
  `electronics.wire_misc.ferrule_*` of that AWG, BOM row; a missing gauge is flagged in the BOM).
- `lead: [item, catalog.path, ...]`: the run is a ready-made lead, e.g. a servo's own pigtail (catalog
  `lead_length_mm`) plus extension cables (catalog `length`) plugged in series. Its length is their sum (a given
  `length_mm` may not exceed it), nothing is cut from a reel, the extensions are BOM rows. `lead: <run id>`: another
  conductor of that run's lead (a servo's signal wire whose +/- pair is the power run): same length, no BOM.
- `fuse: <catalog fuse>` (+ `fuse_holder: <catalog holder>`) on a power run: rows check avg <= derate x rating
  (catalog `derate`, Littelfuse 75 %), peak <= rating, rating <= the smallest chassis ampacity of the run and every
  power run downstream of it (the fuse protects those wires), holder current/voltage; BOM fuse (+1 spare) + holder.
- `pin:` on a `kind: signal` run from a controller to a servo names the output (Nano `D9`, Pi `GPIO18`/`GPIO19`, PCA9685 `ch0`..`ch15`, flight controller `M4`): kerf/firmware.py builds the bring-up program from it (required for every servo signal from a controller Kerf knows).
- `electrical.supply_v`: an adjustable mains supply trimmed to this voltage (must be inside catalog
  `output_v_adj_min..max`); runs from it then carry that `v`.
- `electrical.mains: {inlet: <item>, fuse, cord, wire, tab_receptacle, jumper_mm, input_v}`: the AC side. The
  supply's catalog `input_current_a_<input_v>vac` must fit the inlet (`current_a`, UL figure if lower), the derated
  inlet fuse, the cord and the jumper wire (ampacity, and `voltage_max` >= input_v); BOM cord, fuses (+1 spare),
  jumper wire, ferrules and tab receptacles; WIRING/ASSEMBLY get the L/N/earth step.
- `supplied: <item>` marks a lead that comes with an item (an adapter's DC cord, a pack's own lead): rated and
  length-checked like any run, but no wire or heat-shrink in the BOM and its step says connect, not cut.
- A power run (`kind: power`, default) is the +/- pair (`conductors` overrides, e.g. 3 motor phases) and carries
  everything downstream of its `to` item. A run at a lower `v` than the item's feed is a regulator output and is
  referred back to the input at `bec_eff` (0.8). Each item has one feed; the tree starts at the battery.
- Item draw: motors `max_current_a` (peak) and, when prop discs exist, their hover share (momentum theory, figure of
  merit `fm` 0.5, motor efficiency `eta` 0.75); servos `running_current_a` / `stall_current_a`; others `current_a`
  [/`current_peak_a`]; connectors (catalog path `...connectors...`) and regulators (`output_v`) draw nothing themselves.
- Ratings: battery avg <= C x Ah and peak <= C_burst x Ah; output pins `<pin>_current_a` / `<pin>_burst_a`
  (per run, e.g. ESC channels) or `bec_<pin>_a` (summed); a regulator by `current_a`; connectors `current_a` /
  `current_peak_a`; each power run avg <= chassis ampacity (catalog `wire.awg`) and adiabatic burst rise at peak for
  `burst_s` <= 60 K; `v` within the `to` item's `voltage_min..max` / `input_v_min..max`; battery runs at 4.2 V/cell.
- Route waypoints: `item`, `item.joint`, `[x, y, z]` (world, fixed) or `{item, at: [x, y, z] | joint}` (a tie point
  in that item's frame that moves with it — use these on anything past a moving joint).
- `length_mm` is the cut length: it must be >= the routed 3D length (ends + waypoints) + 15 % at home and, in the full
  check, at both ends of every moving joint and every named sweep pose (`electrical.route_check`). The full check also
  sweeps a tube of the wire's outer diameter (catalog `wire.silicone`) along each route at those poses: it must not
  pass through any item but the two it connects, nor through a prop disc, nor through a screw shank or head of a joint
  not involving those two items (`asm.screws`, kerf/shanks.py; problems).
- Wire mass (catalog `wire.silicone` g/m x cut length x conductors) is added to hover power, `thrust_to_weight` and
  the all-up `mass_max`.
- `kerf build` writes `out/WIRING.md` (runs, loads, ratings, solder steps), `out/wiring.svg`, the electrical steps of `out/ASSEMBLY.md`, and
  adds wire (per gauge/colour, total mm) and heat-shrink rows with buy links to the BOM.

## Item keys
- Printed parts: `file`, `material`, `qty`, `print_rot` [deg about X, Y, Z onto the bed], `infill` (mass model),
  `walls` (perimeter loops; default 4 on strength-checked parts, else 2; written into the plate 3MF),
  `load_axis` (x / -y / [x, y, z] / list: main stress direction in the part frame; warned if > 30 deg across layers),
  `supports` (per-part override: `avoid`, `allowed`, or `needed` = slicer supports on in the plate file), `params` (per-part param overrides), `note` (shown in the BOM).
- Creative mode (kerf/meshy.py): a printed part with `source: meshy`, `prompt` (what to ask Meshy text-to-3D for),
  `mesh` (cached model, default `meshes/<part>.glb|stl|obj`), `bounds` [[x0,y0,z0],[x1,y1,z1]] (part frame; the
  model is scaled to fill it) and `fit` (`stretch` default, or `uniform`) is fused with its exact features into one
  body. Its part file builds the features as usual and calls `ctx.mesh_cut(solid)` for every hole, key-access bore
  or pocket that must also go through the shell. Files in `meshes/` are part of the fingerprint.
- Purchased items: `catalog`, `proxy`, `groups` (proxy site key -> fastener group), `qty`, `mass_g` (overrides the
  catalog mass), `note`, `color`, `tab_screws_from: bottom` (servo screws from behind the tabs, with
  `servo_mount(top_through=True)`), `tab_washers: true` (a flat washer under each tab screw head: catalog
  `washer_h` added to the grip), proxy-specific sizes (`length` rod, `size` box, `h` prop-disc thickness,
  `diameter` prop disc, `hole_start_deg` / `use_holes` horn holes, `component_height` board, `model`/`model_rot`/`model_pos`/
  `models_dir`/`base` vendor STEP, `center`/`teeth`/`width` belt).
- Keep-outs: as purchased, plus `owner` (the item the volume belongs to; never an interference with it).
- Project level: `name`, `printer`, `supports`, `params` (`value`, `min`, `max`, `step`, `label`), `derived`, `layout`,
  `parts`, `purchased`, `keepouts`, `assembly`, `requirements`, `bom_extra` ([{item, qty, type, spec, note}] extra BOM
  rows such as straps, wire, glue; `group: <fastener group>` lists the row in ASSEMBLY.md at that group's screws,
  e.g. washers), and any item may carry `assembly_note` (printed in ASSEMBLY.md where it is fitted).

## Proxies (kerf/proxies.py) — purchased parts and keep-outs
| proxy | from catalog | joints | fastener sites (`groups:` key) |
|---|---|---|---|
| servo | servos.* (catalog `gear_boss_*` output-gear housing; `cable_boss_*` lead exit, `cable_boss_flex`: loose wires = interference but not tool reach) | tabs, output (revolute), output_base | tabs: male screws through the tab holes |
| horn | servo_horns.* (disc, or arm horn with catalog `arms`: stock SG90 1/2/4-arm) | spline, face | holes: female threaded holes on the face (arm horns: `use_holes: ends` (default, innermost + outermost per arm) or `all`; match `horn_mount(use=...)`); the centre screw is key-checked when the horn goes on |
| bearing | bearings.* | face, top, spin (revolute) | – |
| motor | drone motor entry | base, prop | mount: female threaded holes in the base |
| prop_disc | drone prop entry or `diameter` | hub | – (keep-out, set `owner:`) |
| stepper | steppers.* | face, shaft (revolute) | face: female threaded holes |
| rod | rods.* + `length` | end_a, end_b, mid | – |
| board | boards.* | bottom | holes: male screws through the board |
| box | `size` or catalog L/W/H | bottom, top, + `joints:` | `sites:` [{group, screw, at, dir, kind: threaded (female, `engage`, `min_engage`) or clearance (male, `grip`)}] — holes in the bought part's own case (positions from its catalog drawing) |
| panel_module | panel_cutout_w/h(+corner_r), flange_w/h/t, body_w/h, depth_behind_flange, front_protrusion, screw_hole_spacing/_d (+ spec `screw`) | panel (flange rear face, +Z out of the front) | holes: male screws through the flange |
| step | any catalog entry + `base:` proxy kind + `model:` file in catalog/models (`model_rot`, `model_pos` into the base frame) | the base proxy's | the base proxy's; refused unless the STEP bbox is within 0.5 mm of the base proxy's and every site has a real hole (kerf/vendor.py) |
| pulley | motion.GT2_*_pulley (envelope: flange OD x length) | bore, top | – |
| belt | `center`, `teeth: [z1, z2]`, `width` (keep-out; `owner:` pulley 1, allow_overlap pulley 2) | axis1 | – |

## Part module contract
```python
from build123d import *
from kerf import iface

def build(ctx):
    p = ctx.p                                        # params (+ derived) as attributes
    servo = ctx.cat.get("servos.MG996R")             # real dimensions
    body = Box(...)                                  # build123d algebra
    body -= iface.servo_mount(ctx, "servos.MG996R", Location((0, 0, t)), group="bracket_servo", plate_t=t)
    body += ctx.add(rib, why="carries the servo stall torque into the base", kind="rib")   # design-intent ledger
    ctx.rigid("base", Location((0, 0, 0)))           # attachment frames other items connect to
    ctx.revolute("pivot", Axis((0, 0, 10), (1, 0, 0)), range=(-45, 45))  # moving joints live on the parent
    return ctx.finish(body)                          # must be ONE solid for a printed part
    # source: meshy parts: ctx.mesh_cut(hole_solid) also cuts it through the generated shell (kerf/meshy.py)
```
Frames: millimetres, Z up, in the part's own frame. `print_rot` in project.yaml rotates the part onto the bed for
checks and print files; design geometry in whatever frame is clearest.

## Fastener sites (how alignment is proven)
A site is one end of one screw: origin on the surface, +Z pointing toward the screw head (male side, screw passes
through) or toward the mating part (female side: insert, tapped hole, nut trap, threaded metal). Both sides of a
connection register sites with the same `group`. After assembly the checker pairs every male site with a female
site on the same axis (within 0.15 mm, 1°), measures the grip, flags gaps (parts not clamped) and picks the shortest
standard screw that reaches the minimum engagement without bottoming out. Unpaired sites are failures.

## Pin sites (how pinned hinges are proven)
`iface.pin_hole(ctx, pin, loc, group, depth, fit)` cuts one knuckle and registers a pin site (origin on the entry
face, +Z along the pin out of the material). `pin` is a catalog dowel (`motion.pin_3mm`, sizes and stocked `lengths`
from the catalog) or a screw size (`M3`) used as a pivot; `fit` is `free` (turns), `press` (dowel held,
`fdm_fits.pin` allowances) or `heatset`/`tap` (screw pivot thread). kerf/pins.py proves per group: every hole coaxial
(0.05 mm, 0.5 deg), the pin held by some part, each moving joint that splits the group turns about the pin axis (or
slides along it) with the pin held on one side only, and a stocked length that reaches every hole by min(hole,
1.5 d). Screw pivots get a threadlocker warning; pins, pivot screws and inserts go into the BOM.

## Fingerprint and catalog_deps.json
`kerf review-status` ties a review to the project's fingerprint: project.yaml, parts/*.py, meshes, the printer
calibration profile, and the catalog entries the project reads. Every check/build records the catalog paths it read
into `projects/<p>/catalog_deps.json` (a growing union; commit it), so an edit to a catalog entry the project does
not use leaves its review current, and an edit to one it uses makes it stale. Without that file the whole catalog
file is hashed.
It also reports `out_stale` (and says so in `why`) when `out/report.json` was built from another fingerprint: the
review stands, but the shipped ASSEMBLY.md / BOM / renders need `kerf build` (verify rebuilds everything anyway).

## report.json (out/report.json, written by check/build)
`ok`, `problems[]`, `warnings[]`, `fingerprint`, `parts{id: print checks}`, `purchased{}`,
`assembly{interference[], fasteners[], pins[], sweeps[], joints[], positions{}, joint_origins{}}`, `requirements[]`,
`files{parts, plates}`, `bom[]`, `diagnoses{item: {part, file, line, code, feature, error, hint}}` for items that failed to build. Evals read this file; reviews are tied to `fingerprint`.

## Definition of done (`kerf verify`)
pytest passes; every project builds with `ok: true`; every project has a design-reviewer `review.json` with verdict
PASS for the current fingerprint; every eval's `acceptance.py` passes on a fresh report; PLAN.md has no unchecked box.
