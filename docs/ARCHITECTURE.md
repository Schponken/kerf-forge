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
| `kerf/ctx.py` | What a part's `build(ctx)` gets: `ctx.p` params, `ctx.cat` catalog, joint + fastener-site declarations, `ctx.finish()` |
| `kerf/iface.py` | Mating-feature generators (bolt patterns, inserts, nut traps, bearing seats, servo/horn/motor/stack mounts, `pin_hole` for pinned hinges). Each returns a cutter solid and registers fastener (or pin) sites |
| `kerf/drives.py` | Printed spur-gear pairs (py_gearworks, FDM backlash, standard centre distance) and GT2 belt maths (length, tooth count, centre for a stock belt, wrap) + belt keep-out solid |
| `kerf/proxies.py` | Purchased parts and keep-outs built from the catalog, with their joints and fastener sites |
| `kerf/catalog.py` | Loads `catalog/hardware.json` (every entry has a `source`) |
| `kerf/project.py` | Loads project.yaml, evaluates params/derived, builds every item |
| `kerf/assembly.py` | Joint tree, solve poses, interference, motion sweeps, coupled poses, fastener alignment + screw lengths |
| `kerf/features.py` | Detailed-modeling helpers: swept channels, uniform shell, gussets, teardrop holes, printed ISO threads (bd_warehouse, phase-matched rod/hole), gear pairs (= drives.spur_pair), snap hooks + living hinges with a strain check, text labels, lightening pockets with a minimum web, `safe_fillet` (applies edge groups one by one, reports failures) |
| `kerf/access.py` | Assembly access, run by every check: hex-key reach for every male screw site (straight, else 25 deg ball-end = warning, else problem; catalog `tools.hex_key`) and insertion paths for items with `insert: {direction, distance}`; results in report.json `assembly.hex_keys` / `assembly.insertion` |
| `kerf/pins.py` | Pinned hinges: every `pin_hole` of a group coaxial (0.05 mm), pin held (press/heatset/tap) on one side of each moving joint and free on the other, the joint turning about the pin axis, and a stocked pin/screw length that reaches every hole |
| `kerf/checks.py` | Per-part print checks in print orientation (solids, validity, bed fit, watertight, overhang, wall thickness, `load_axis` across layers, mass) |
| `kerf/requirements.py` | Engineering checks named in project.yaml (`@check("name")` registry), incl. `fea_static` |
| `kerf/fea.py` | Linear static FEA of one part (gmsh quadratic tets + scikit-fem); force, pressure, torque and bearing loads; validated in tests/test_fea.py, tests/test_fea_loads.py |
| `kerf/fea_render.py` | Von Mises colour picture per FEA check (`out/renders/fea_<id>.png`) |
| `kerf/geom.py` | Geometry helpers: volumes, exact overlaps, meshes, mesh-based overhang / wall-thickness analysis, world points/directions of a Location |
| `kerf/req_balance.py` | Balance requirement `cg` (assembled centre of gravity incl. purchased parts and payload, vs a reference line, over poses) |
| `kerf/vendor.py` | `proxy: step` vendor CAD models: loads catalog/models STEP, keeps the base proxy's joints and sites, refuses a model whose bbox or holes disagree with the catalog |
| `kerf/viewer.py` | Writes the self-contained `out/viewer.html` (meshes, joint sliders from the engine's own kinematics, explode, BOM, print info) |
| `kerf/attribution.py` | Face → part-file line and project param that produced it (viewer click-to-edit) |
| `kerf/export.py` | STEP assembly, STL/3MF per part, plate packing, GLB, BOM |
| `kerf/pipeline.py` | Runs everything for a project, writes `out/report.json`, renders via `tools/render/render.mjs` |
| `kerf/cli.py` | `kerf doctor | check | build | verify | review-status | new | status` |

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
  bracket: {file: parts/bracket.py, material: PETG, qty: 1, print_rot: [0, 0, 0], infill: 0.3, load_axis: X}   # load_axis: main stress direction (part frame); warned if > 30 deg across layers
  # any part or purchased item may add  insert: {direction: [0, 0, -1], distance: 30}  (own frame, the way it moves
  # going IN): kerf check slides it (and what is mounted on it) in from that far and reports collisions on the way
purchased:                      # catalog-backed proxies (real mass + geometry for collisions)
  servo: {catalog: servos.MG996R, proxy: servo, groups: {tabs: bracket_servo}}
  horn:  {catalog: servo_horns.aluminum_25T, proxy: horn, groups: {holes: horn_arm}}
keepouts:                       # volumes nothing may enter (prop discs, camera view, fingers)
  prop_1: {catalog: drone.props.5_1in, proxy: prop_disc, owner: motor_1}
assembly:
  root: base
  joints:                       # parent.joint_label -> child.joint_label; child joints are always rigid
    - {parent: base.bracket_seat, child: bracket.base}
    - {parent: servo.output, child: horn.spline, name: swing, range: [-90, 90], home: 0}
  order: [base, bracket, servo, horn, arm]   # optional build sequence (ids or [ids]); a screw is driven when the later of
                                # its two parts goes on, so only parts installed by then can block its hex key
  allow_overlap:                # only with a physical reason
    - {pair: [servo, horn], max_mm3: 60, why: horn spline engages the servo output shaft}
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
| `static_torque` | `joint`, `actuator` or `stall_kgcm`, `max_fraction`, `payload_g`, `payload_at`, `poses` | worst gravity torque (kg·cm) |
| `thrust_to_weight` | `thrust_g_total`, `min_ratio` | thrust / all-up mass |
| `fea_static` | `part`, `fixed`, `loads`, `sf`, `direction`, `max_disp_mm` | stress / deflection (FEA) |
| `cantilever_stress` | `part`, `section`, `loads`, `sf`, `kt`, `direction` | beam-theory stress at a section |
| `cg` | `ref` or `point`, `axis`, `max_lateral_mm`, `min_along_mm`/`max_along_mm`, `include`, `payload_g`, `payload_at`, `poses` | CG offset from the line |
| `tip_over` | `min_deg`, `support`, `poses`, `payload_g`, `payload_at` | smallest tip-over angle (deg) |
| `channel_clear` | `path`, `diameter`, `poses`, `ignore` | largest diameter that passes (mm) |
| `prop_clearance` | `min_mm`, `min_between_mm`, `props`, `ignore`, `joints`, `poses` | tightest prop-disc gap (mm) |

`cantilever_stress` cuts the part with the section plane, takes the section's area and second-moment tensor, and
reports kt x max |N/A + unsymmetric bending stress| over the outline. Torsion is reported, not included.
`tip_over` (`min_deg`, optional `support: [items]`, `poses: [{joint: deg}]`, `payload_g` + `payload_at: item.joint`)
finds the floor contacts (mesh points within `tol` 0.5 mm of the lowest point), takes their convex hull and reports the
smallest atan(CG-to-edge distance / CG height) in degrees over the poses; negative means it falls over by itself.

`channel_clear` sweeps a ball along the polyline at every pose and reports the largest diameter that passes (0.01 mm).

`prop_clearance` (`min_mm`, optional `min_between_mm` tip-to-tip, `props`, `ignore`, `joints` to sweep (default all),
`samples`, `poses`) measures every prop disc (keep-out, `proxy: prop_disc`) to every other disc and to every non-keep-out
item except its `owner` and allow_overlap partners, at home and over the sweeps, and reports the tightest gap.
FEA loads: region keys (`box`, `sites`, `near_joint`, or `cylinder: {at: [x,y,z] | joint, dir, r, tol: 0.3, span}`
for a bore) plus one of `force_n: [fx,fy,fz]` (total, spread evenly), `pressure_mpa: p` (into the surface),
`torque_nmm: T` with `axis: {at, dir}` (tangential, proportional to radius) or `bearing_n: [fx,fy,fz]` (cosine pressure
on the half of a bore facing the load). Each FEA result reports `applied_force_n` / `applied_moment_nmm` (part origin),
and `kerf build` writes `out/renders/fea_<id>.png` (kerf/fea_render.py: von Mises, magenta above the limit).
Numbers inside requirement regions and forces may be expressions over params/layout values.

## Item keys
- Printed parts: `file`, `material`, `qty`, `print_rot` [deg about X, Y, Z onto the bed], `infill` (mass model),
  `load_axis` (x / -y / [x, y, z] / list: main stress direction in the part frame; warned if > 30 deg across layers),
  `supports` (per-part override), `params` (per-part param overrides), `note` (shown in the BOM).
- Purchased items: `catalog`, `proxy`, `groups` (proxy site key -> fastener group), `qty`, `mass_g` (overrides the
  catalog mass), `note`, `color`, `tab_screws_from: bottom` (servo screws from behind the tabs, with
  `servo_mount(top_through=True)`), proxy-specific sizes (`length` rod, `size` box, `h` prop-disc thickness,
  `diameter` prop disc, `hole_start_deg` horn holes, `component_height` board, `model`/`model_rot`/`model_pos`/
  `models_dir`/`base` vendor STEP, `center`/`teeth`/`width` belt).
- Keep-outs: as purchased, plus `owner` (the item the volume belongs to; never an interference with it).
- Project level: `name`, `printer`, `supports`, `params` (`value`, `min`, `max`, `step`, `label`), `derived`, `layout`,
  `parts`, `purchased`, `keepouts`, `assembly`, `requirements`, `bom_extra` ([{item, qty, type, spec, note}] extra BOM
  rows such as straps, wire, glue).

## Proxies (kerf/proxies.py) — purchased parts and keep-outs
| proxy | from catalog | joints | fastener sites (`groups:` key) |
|---|---|---|---|
| servo | servos.* | tabs, output (revolute), output_base | tabs: male screws through the tab holes |
| horn | servo_horns.* | spline, face | holes: female threaded holes on the face |
| bearing | bearings.* | face, top, spin (revolute) | – |
| motor | drone motor entry | base, prop | mount: female threaded holes in the base |
| prop_disc | drone prop entry or `diameter` | hub | – (keep-out, set `owner:`) |
| stepper | steppers.* | face, shaft (revolute) | face: female threaded holes |
| rod | rods.* + `length` | end_a, end_b, mid | – |
| board | boards.* | bottom | holes: male screws through the board |
| box | `size` or catalog L/W/H | bottom, top, + `joints:` | – |
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
    ctx.rigid("base", Location((0, 0, 0)))           # attachment frames other items connect to
    ctx.revolute("pivot", Axis((0, 0, 10), (1, 0, 0)), range=(-45, 45))  # moving joints live on the parent
    return ctx.finish(body)                          # must be ONE solid for a printed part
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

## report.json (out/report.json, written by check/build)
`ok`, `problems[]`, `warnings[]`, `fingerprint`, `parts{id: print checks}`, `purchased{}`,
`assembly{interference[], fasteners[], pins[], sweeps[], joints[], positions{}, joint_origins{}}`, `requirements[]`,
`files{parts, plates}`, `bom[]`. Evals read this file; reviews are tied to `fingerprint`.

## Definition of done (`kerf verify`)
pytest passes; every project builds with `ok: true`; every project has a design-reviewer `review.json` with verdict
PASS for the current fingerprint; every eval's `acceptance.py` passes on a fresh report; PLAN.md has no unchecked box.
