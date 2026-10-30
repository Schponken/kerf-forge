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
| `kerf/proxies.py` | Purchased parts and keep-outs built from the catalog, with their joints and fastener sites |
| `kerf/catalog.py` | Loads `catalog/hardware.json` (every entry has a `source`) |
| `kerf/project.py` | Loads project.yaml, evaluates params/derived, builds every item |
| `kerf/assembly.py` | Joint tree, solve poses, interference, motion sweeps, coupled poses, fastener alignment + screw lengths |
| `kerf/pins.py` | Pinned hinges: every `pin_hole` of a group coaxial (0.05 mm), pin held (press/heatset/tap) on one side of each moving joint and free on the other, the joint turning about the pin axis, and a stocked pin/screw length that reaches every hole |
| `kerf/checks.py` | Per-part print checks in print orientation (solids, validity, bed fit, watertight, overhang, wall thickness, mass) |
| `kerf/requirements.py` | Engineering checks named in project.yaml (`@check("name")` registry), incl. `fea_static` |
| `kerf/fea.py` | Linear static FEA of one part (gmsh quadratic tets + scikit-fem); validated in tests/test_fea.py |
| `kerf/export.py` | STEP assembly, STL/3MF per part, plate packing, GLB, BOM |
| `kerf/pipeline.py` | Runs everything for a project, writes `out/report.json`, renders via `tools/render/render.mjs` |
| `kerf/cli.py` | `kerf doctor | check | build | verify | review-status | new` |

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
  allow_overlap:                # only with a physical reason
    - {pair: [servo, horn], max_mm3: 60, why: horn spline engages the servo output shaft}
  sweeps:
    - {joint: swing, samples: 13}             # finer sweep for one joint
    - {name: curl, poses: [{mcp: 30, pip: 30}, {mcp: 80, pip: 80}]}   # coupled poses
requirements:
  - {id: arm_torque, check: static_torque, joint: swing, actuator: servo, payload_g: 50, payload_at: arm.tip, max_fraction: 0.5}
  - id: bracket_fea               # finite-element strength check of one printed part (part frame, mm, N)
    check: fea_static
    part: bracket
    direction: z                  # judge against layer-direction strength when the load crosses layers
    sf: 2.0
    max_disp_mm: 0.3
    fixed: {box: [[-200, -1, -1], [200, 200, 0.01]]}             # or {sites: group, radius: r} / {near_joint: label, radius: r}
    loads: [{box: [[1, wall_t - 0.01, pivot_h - 12], [40, wall_t + 0.01, pivot_h + 12]], force_n: [0, 0, 18.6]}]
```
Numbers inside requirement regions and forces may be expressions over params/layout values.

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

## report.json (out/report.json, written by check/build)
`ok`, `problems[]`, `warnings[]`, `fingerprint`, `parts{id: print checks}`, `purchased{}`,
`assembly{interference[], fasteners[], pins[], sweeps[], joints[], positions{}, joint_origins{}}`, `requirements[]`,
`files{parts, plates}`, `bom[]`. Evals read this file; reviews are tied to `fingerprint`.

## Definition of done (`kerf verify`)
pytest passes; every project builds with `ok: true`; every project has a design-reviewer `review.json` with verdict
PASS for the current fingerprint; every eval's `acceptance.py` passes on a fresh report; PLAN.md has no unchecked box.
