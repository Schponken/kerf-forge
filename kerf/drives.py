"""Power-transmission helpers: printed spur-gear pairs (py_gearworks involute gears) and GT2 belt drives.

Spur gears
- `spur_pair(module, z1, z2, width)` -> (gear1, gear2, info). gear1 is centred on its own origin; gear2 is centred on
  ITS own origin and already rotated into mesh phase for a centre at (+info.center, 0, 0) in gear1's frame. Put gear1 on
  a revolute joint and gear2 on a revolute joint `info.center` mm away along +X of gear1's joint frame, then couple
  them in project.yaml so the motion sweep turns them together:
      assembly: {sweeps: [{joint: <gear2 joint>, follows: <gear1 joint>, ratio: <info.ratio_signed>}]}
- Backlash for FDM: 0.2-0.4 mm total meshing clearance (Sovol, "3D Printing Gears That Actually Work",
  https://www.sovol3d.com/blogs/news/3d-printing-gears-that-actually-work-backlash-orientation-and-material-tips);
  we use 0.3 mm, split equally between the two gears' flanks, at the STANDARD centre distance m (z1 + z2) / 2.
- Module: >= 1.5 for a 0.4 mm nozzle, >= 1.0 only for tuned printers (same source). < 1.0 is refused.

GT2 belts (2 mm pitch; catalog motion.GT2_belt / motion.GT2_*_pulley)
- pitch diameter = teeth * pitch / pi; open-belt pitch length L = 2C + pi (D1 + D2) / 2 + (D2 - D1)^2 / (4C).
- Closed belts are sold by tooth count, so `belt_teeth` rounds to a whole tooth and `center_for_belt` gives the exact
  centre distance for a belt you can buy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from build123d import Align, Cylinder, Part, Pos

from . import catalog

GEAR_BACKLASH_MM = 0.3   # total circumferential clearance at the pitch circle (source in the module docstring)
MIN_MODULE = 1.0
GOOD_MODULE = 1.5
MIN_TEETH = 10           # py_gearworks undercuts below 17; under 10 the printed tooth root is too weak


@dataclass
class GearPair:
    module: float
    z1: int
    z2: int
    width: float
    center: float          # mm, standard centre distance
    ratio: float           # speed reduction z2 / z1 (>1 = gear2 turns slower, with more torque)
    ratio_signed: float    # gear2 angle = ratio_signed * gear1 angle (external gears turn opposite ways)
    pitch_d: tuple
    tip_d: tuple
    backlash_mm: float
    phase2_deg: float      # rotation already applied to gear2 so it meshes at joint angle 0
    warnings: list


def center_distance(module: float, z1: int, z2: int) -> float:
    return module * (z1 + z2) / 2.0


def _gear(z, width, module, backlash_coef):
    import py_gearworks as gw
    return gw.SpurGear(int(z), height=width, module=module, backlash=backlash_coef)


def spur_pair(module: float, z1: int, z2: int, width: float, backlash: float = GEAR_BACKLASH_MM,
              bore1: float | None = None, bore2: float | None = None):
    """Two meshing involute spur gears (20 deg pressure angle). Returns (gear1, gear2, GearPair).
    bore1/bore2: optional through-bore diameters (mm) for a shaft or bearing; pass the fitted size (e.g. from
    iface.FIT / catalog), this function does not add clearance."""
    if module < MIN_MODULE:
        raise ValueError(f"module {module} is below {MIN_MODULE}: teeth that small do not print with a 0.4 mm nozzle")
    if min(z1, z2) < MIN_TEETH:
        raise ValueError(f"{min(z1, z2)} teeth is below {MIN_TEETH}; the undercut tooth root is too weak to print")
    if width <= 0:
        raise ValueError("gear width must be positive")
    warn = []
    if module < GOOD_MODULE:
        warn.append(f"module {module} < {GOOD_MODULE}: only for a well-tuned printer; test-print the pair first")
    coef = backlash / module / 2.0          # py_gearworks backlash is per gear, in units of module
    g1, g2 = _gear(z1, width, module, coef), _gear(z2, width, module, coef)
    g2.mesh_to(g1, target_dir=np.array([1.0, 0.0, 0.0]))
    c = float(np.linalg.norm(np.asarray(g2.center)[:2]))
    if abs(c - center_distance(module, z1, z2)) > 1e-6:
        raise RuntimeError(f"py_gearworks placed the gears {c:.4f} mm apart, expected {center_distance(module, z1, z2):.4f}")
    phase = math.degrees(float(g2.angle))
    p1 = g1.build_part()
    g2.center = np.array([0.0, 0.0, 0.0])
    p2 = g2.build_part()                    # still carries the mesh phase rotation, now about its own origin
    if bore1:
        p1 = p1 - Pos(0, 0, -1) * Cylinder(bore1 / 2, width + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    if bore2:
        p2 = p2 - Pos(0, 0, -1) * Cylinder(bore2 / 2, width + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for z, b in ((z1, bore1), (z2, bore2)):
        root_d = module * (z - 2.5)
        if b and (root_d - b) / 2 < 2.0:
            raise ValueError(f"{z}-tooth gear: bore {b} mm leaves {(root_d - b) / 2:.1f} mm under the tooth roots (< 2 mm)")
    info = GearPair(module, int(z1), int(z2), width, center_distance(module, z1, z2), z2 / z1, -z1 / z2,
                    (module * z1, module * z2), (module * (z1 + 2), module * (z2 + 2)), backlash, phase, warn)
    return Part(p1.wrapped), Part(p2.wrapped), info


# ------------------------------------------------------------------------------------------- GT2 belts
def _belt():
    return catalog.get("motion.GT2_belt")


def pulley_pitch_d(teeth: int, pitch: float | None = None) -> float:
    p = pitch if pitch is not None else catalog.num(_belt(), "pitch")
    return teeth * p / math.pi


def belt_length(center: float, z1: int, z2: int, pitch: float | None = None) -> float:
    """Pitch length (mm) of an open belt around two pulleys `center` mm apart."""
    d1, d2 = sorted((pulley_pitch_d(z1, pitch), pulley_pitch_d(z2, pitch)))
    if center <= (d1 + d2) / 2:
        raise ValueError(f"pulleys {center} mm apart overlap (pitch diameters {d1:.2f} and {d2:.2f})")
    return 2 * center + math.pi * (d1 + d2) / 2 + (d2 - d1) ** 2 / (4 * center)


def belt_teeth(center: float, z1: int, z2: int, pitch: float | None = None) -> int:
    p = pitch if pitch is not None else catalog.num(_belt(), "pitch")
    return int(round(belt_length(center, z1, z2, p) / p))


def center_for_belt(belt_teeth_: int, z1: int, z2: int, pitch: float | None = None) -> float:
    """Exact centre distance for a closed belt of `belt_teeth_` teeth (inverse of belt_length)."""
    p = pitch if pitch is not None else catalog.num(_belt(), "pitch")
    L = belt_teeth_ * p
    d1, d2 = pulley_pitch_d(z1, p), pulley_pitch_d(z2, p)
    b = L - math.pi * (d1 + d2) / 2
    disc = b * b - 2 * (d2 - d1) ** 2
    if b <= 0 or disc < 0:
        raise ValueError(f"a {belt_teeth_}-tooth belt is too short for {z1}T and {z2}T pulleys")
    c = (b + math.sqrt(disc)) / 4
    if c <= (d1 + d2) / 2:
        raise ValueError(f"a {belt_teeth_}-tooth belt is too short for {z1}T and {z2}T pulleys")
    return c


def wrap_deg(center: float, z1: int, z2: int) -> float:
    """Belt wrap angle on the SMALLER pulley (degrees)."""
    d1, d2 = sorted((pulley_pitch_d(z1), pulley_pitch_d(z2)))
    return 180.0 - 2 * math.degrees(math.asin((d2 - d1) / (2 * center)))


MIN_TEETH_IN_MESH = 6    # SDP-SI belt design guide: six or more teeth in mesh on the smaller pulley for rated power


def teeth_in_mesh(center: float, z1: int, z2: int) -> float:
    return min(z1, z2) * wrap_deg(center, z1, z2) / 360.0


def pulley_pld() -> float:
    """Pitch-line differential: pitch radius minus tooth-tip radius, from the catalogued 20T pulley (both measured)."""
    e = catalog.get("motion.GT2_20T_pulley")
    return (catalog.num(e, "pitch_d") - catalog.num(e, "tip_od")) / 2


def belt_keepout(center: float, z1: int, z2: int, width: float, margin: float = 0.5):
    """Solid the running belt occupies (plus `margin` on every side): from each pulley's tooth tips out to the belt
    back (belt height from the catalog), straight spans tangent between. Frame: pulley 1 axis at the origin, pulley 2
    at (center, 0, 0), belt from z = 0 to z = width (centred on the pulley's toothed section)."""
    from build123d import Edge, Face, Wire, extrude, make_hull
    h = catalog.num(_belt(), "height")
    pld = pulley_pld()
    r1, r2 = pulley_pitch_d(z1) / 2 - pld, pulley_pitch_d(z2) / 2 - pld

    def hull(dr):
        c1 = Edge.make_circle(r1 + dr)
        c2 = Pos(center, 0, 0) * Edge.make_circle(r2 + dr)
        return make_hull([c1, c2])

    outer, inner = hull(h + margin), hull(-margin)
    band = Pos(0, 0, -margin) * extrude(outer, width + 2 * margin) - Pos(0, 0, -margin - 1) * extrude(inner, width + 2 * margin + 2)
    return band
