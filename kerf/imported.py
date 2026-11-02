"""Check it on a user's own design (docs/VISION.md, mode `check`): a printed part can come from a STEP or STL file
instead of a parts/*.py build(), so Kerf runs its fit / motion / strength / balance / wiring checks on a design it did
not make. project.yaml declares, per imported part, what the file cannot say:

  parts:
    lid:
      import: imports/lid.step          # .step / .stp (B-rep) or .stl / .3mf (mesh, sewn into a solid)
      material: PETG
      print_rot: [0, 0, 0]
      units: mm                         # or m / in (the file's unit; STEP files carry theirs, STL files do not)
      joints: {hinge_pin: [10, 0, 5]}                          # rigid joints: label -> point (part frame)
      revolute: {hinge: {at: [0, 0, 5], axis: [1, 0, 0], range: [0, 110]}}   # moving joints
      sites: [{group: lid_screws, screw: M3, at: [5, 5, 0], dir: [0, 0, -1], kind: clearance, grip: 3}]

`sites` are fastener holes in the model's surface, written like a purchased box's (kerf/proxies._box_site): kind
clearance (the screw passes, male, with its clamped `grip`) or threaded / heatset / tap (female, with `engage`).
The joint tree, requirements (fea_static, mass, tip_over, ...) and wiring work exactly as for designed parts.
"""
from __future__ import annotations

from pathlib import Path

UNITS = {"mm": 1.0, "m": 1000.0, "in": 25.4}


class ImportError_(ValueError):
    pass


def load(path: Path, units: str = "mm"):
    """The model as one solid (part frame = the file's frame, mm)."""
    from build123d import Compound, Mesher, Solid, import_step, scale
    if not path.exists():
        raise ImportError_(f"imported model {path} not found")
    ext = path.suffix.lower()
    if ext in (".step", ".stp"):
        shape = import_step(str(path))
    elif ext in (".stl", ".3mf"):
        shapes = Mesher().read(str(path))
        if not shapes:
            raise ImportError_(f"{path.name}: no mesh in the file")
        shape = shapes[0] if len(shapes) == 1 else Compound(shapes)
    else:
        raise ImportError_(f"{path.name}: import STEP (.step / .stp) or a mesh (.stl / .3mf)")
    k = UNITS.get(units)
    if k is None:
        raise ImportError_(f"units '{units}': use {', '.join(UNITS)}")
    if k != 1.0:
        shape = scale(shape, k)
    solids = shape.solids()
    if not solids:
        raise ImportError_(f"{path.name}: the model has no closed solid (a mesh must be watertight to be checked)")
    body = solids[0]
    for s in solids[1:]:
        body = body + s
    if len(body.solids()) != 1:
        raise ImportError_(f"{path.name}: {len(body.solids())} separate bodies; a printed part must be one piece "
                           f"(import each piece as its own part)")
    return Solid(body.solids()[0].wrapped) if not isinstance(body, Solid) else body


def build(ctx, spec: dict, proj_dir: Path):
    """ctx.finish(model) with the joints and fastener sites project.yaml declares for it."""
    from build123d import Axis, Location
    from .proxies import _box_site
    shape = load(proj_dir / spec["import"], spec.get("units", "mm"))
    ctx.rigid("origin", Location((0, 0, 0)))
    for lab, p in (spec.get("joints") or {}).items():
        ctx.rigid(lab, Location(tuple(float(v) for v in p)))
    for lab, j in (spec.get("revolute") or {}).items():
        ctx.revolute(lab, Axis(tuple(float(v) for v in j["at"]), tuple(float(v) for v in j["axis"])),
                     range=tuple(j.get("range", (-180, 180))))
    for st in spec.get("sites") or []:
        ctx.site(_box_site(st))
    return ctx.finish(shape, color=spec.get("color"))
