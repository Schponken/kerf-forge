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


@dataclass
class RackPinion:
    module: float
    z: int                 # pinion teeth
    rack_teeth: int
    width: float
    pitch_r: float         # pinion pitch radius = rack pitch line height above the pinion axis
    tip_r: float
    root_r: float
    pitch: float           # linear tooth pitch pi * m
    mm_per_deg: float      # rack travel per degree of pinion turn (pitch_r * pi / 180)
    rack_y: tuple          # rack (tooth tip, tooth root, back) heights above the pinion axis
    backlash_mm: float
    warnings: list


def rack_pinion(module: float, z: int, rack_teeth: int, width: float, backlash: float = GEAR_BACKLASH_MM,
                bore: float | None = None):
    """A spur pinion and a straight rack meshed with it (20 deg involute, py_gearworks), returned as
    (pinion, rack, info). Pinion: axis = +Z through its origin, face 0..width, a tooth pointing +Y at angle 0.
    Rack: pitch line at y = +info.pitch_r, teeth pointing -Y, running along X and centred on x = 0, phased so it meshes
    at pinion angle 0 (a tooth gap over the pinion's top tooth). Turning the pinion +a deg (counter-clockwise about +Z)
    moves the rack by -a * info.mm_per_deg along X; a second rack under the pinion (the first one rotated 180 deg
    about the pinion axis) moves the other way, which is how a parallel gripper drives its two jaws. In project.yaml
    the rack joint is `linear` and follows the pinion joint: {joint: <rack slide>, follows: <pinion joint>,
    ratio: +-info.mm_per_deg}. rack_teeth must be odd (py_gearworks centres an odd rack on a tooth). Backlash as for
    spur_pair: 0.3 mm total, split between pinion and rack flanks."""
    if module < MIN_MODULE:
        raise ValueError(f"module {module} is below {MIN_MODULE}: teeth that small do not print with a 0.4 mm nozzle")
    if z < MIN_TEETH:
        raise ValueError(f"{z} teeth is below {MIN_TEETH}; the undercut tooth root is too weak to print")
    if rack_teeth < 3 or rack_teeth % 2 == 0:
        raise ValueError(f"rack_teeth must be odd and >= 3 (got {rack_teeth})")
    if width <= 0:
        raise ValueError("gear width must be positive")
    import py_gearworks as gw
    warn = [] if module >= GOOD_MODULE else [f"module {module} < {GOOD_MODULE}: only for a well-tuned printer; test-print first"]
    coef = backlash / module / 2.0
    r = module * z / 2.0
    pinion = _gear(z, width, module, coef).build_part()
    # rack line along X, teeth pointing -Y: rotate the py_gearworks rack (teeth along +X, line along Y) by -90 deg
    rk = gw.InvoluteRack(number_of_teeth=int(rack_teeth), height=width, module=module, backlash=coef,
                         position=np.array([0.0, r, 0.0]),
                         orientation=np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]))
    rack = Pos(math.pi * module / 2.0, 0, 0) * rk.build_part()     # half a pitch: a gap over the pinion's top tooth
    if bore:
        root_d = module * (z - 2.5)
        if (root_d - bore) / 2 < 2.0:
            raise ValueError(f"{z}-tooth pinion: bore {bore} mm leaves {(root_d - bore) / 2:.1f} mm under the tooth roots (< 2 mm)")
        pinion = pinion - Pos(0, 0, -1) * Cylinder(bore / 2, width + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    bb = rack.bounding_box()
    # py_gearworks: addendum 1.0 m, dedendum 1.2 m on both pinion and rack
    info = RackPinion(module, int(z), int(rack_teeth), width, r, r + module, r - 1.2 * module, math.pi * module,
                      r * math.pi / 180.0, (round(bb.min.Y, 4), round(r + 1.2 * module, 4), round(bb.max.Y, 4)),
                      backlash, warn)
    return Part(pinion.wrapped), Part(rack.wrapped), info


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
    from build123d import Edge, extrude, make_hull
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


@dataclass
class Planetary:
    module: float
    z_sun: int
    z_planet: int
    z_ring: int
    n_planets: int
    width: float
    center: float          # sun-to-planet centre distance m (z_sun + z_planet) / 2 (= the carrier pin radius)
    ratio: float           # ring fixed, sun in, carrier out: 1 + z_ring / z_sun
    planet_xy: list        # planet centres (mm), evenly spaced, the first on +X
    ring_od: float         # outside diameter of the ring's rim
    backlash_mm: float
    warnings: list


def planetary_rules(z_sun: int, z_planet: int, z_ring: int, n: int, module: float) -> list[str]:
    """Why a planetary set cannot be built (empty = it can): tooth-count geometry, the equal-spacing assembly
    condition (z_sun + z_ring) / n whole, and neighbouring planets' tip circles clear by >= 1 mm."""
    bad = []
    if z_ring != z_sun + 2 * z_planet:
        bad.append(f"z_ring {z_ring} must be z_sun + 2 z_planet = {z_sun + 2 * z_planet} (coaxial sun and ring)")
    if (z_sun + z_ring) % n:
        bad.append(f"(z_sun + z_ring) / n = {(z_sun + z_ring) / n:.2f} is not whole: {n} equally spaced planets cannot "
                   f"all mesh (pick tooth counts whose sum divides by {n})")
    a = module * (z_sun + z_planet) / 2
    gap = 2 * a * math.sin(math.pi / n) - module * (z_planet + 2)
    if gap < 1.0:
        bad.append(f"neighbouring planets' tips are {gap:.2f} mm apart (< 1 mm): use fewer planets or a bigger sun")
    return bad


def planetary(module: float, z_sun: int, z_planet: int, z_ring: int, n_planets: int, width: float,
              backlash: float = GEAR_BACKLASH_MM):
    """Sun, planets and ring of a printed planetary set, meshed in place (sun on the origin, planets at their carrier
    positions, ring coaxial). Returns (sun, [planets], ring, Planetary). Ring fixed + carrier output: ratio
    1 + z_ring / z_sun. The carrier (pins at `center` on planet_xy) is the project's own part."""
    import py_gearworks as gw
    if module < MIN_MODULE:
        raise ValueError(f"module {module} is below {MIN_MODULE}: teeth that small do not print with a 0.4 mm nozzle")
    if min(z_sun, z_planet) < MIN_TEETH:
        raise ValueError(f"{min(z_sun, z_planet)} teeth is below {MIN_TEETH}; the undercut tooth root is too weak to print")
    bad = planetary_rules(z_sun, z_planet, z_ring, n_planets, module)
    if bad:
        raise ValueError("; ".join(bad))
    warn = [f"module {module} < {GOOD_MODULE}: only for a well-tuned printer; test-print the set first"] if module < GOOD_MODULE else []
    coef = backlash / module / 2.0
    sun = gw.SpurGear(int(z_sun), height=width, module=module, backlash=coef)
    planets, xy = [], []
    for k in range(n_planets):
        th = 2 * math.pi * k / n_planets
        p = gw.SpurGear(int(z_planet), height=width, module=module, backlash=coef)
        p.mesh_to(sun, target_dir=np.array([math.cos(th), math.sin(th), 0.0]))
        planets.append(p)
        xy.append([round(float(p.center[0]), 4), round(float(p.center[1]), 4)])
    ring = gw.SpurRingGear(int(z_ring), height=width, module=module, backlash=coef)
    ring.mesh_to(planets[0], target_dir=np.array([1.0, 0.0, 0.0]))      # an internal mesh: this puts its centre on the sun's
    if float(np.linalg.norm(np.asarray(ring.center)[:2])) > 1e-6:
        raise RuntimeError(f"py_gearworks put the ring at {ring.center}, not on the sun axis")
    R = ring.build_part()
    info = Planetary(module, int(z_sun), int(z_planet), int(z_ring), int(n_planets), width,
                     module * (z_sun + z_planet) / 2, 1 + z_ring / z_sun, xy, float(R.bounding_box().size.X), backlash, warn)
    return Part(sun.build_part().wrapped), [Part(p.build_part().wrapped) for p in planets], Part(R.wrapped), info


# ---- worm sets ----

@dataclass
class WormSet:
    module: float            # axial module of the worm = transverse module of the wheel
    starts: int
    z_wheel: int
    worm_d: float            # worm pitch diameter
    center: float            # (worm_d + m z_wheel) / 2
    ratio: float             # z_wheel / starts
    lead_deg: float          # lead angle: atan(starts m / worm_d)
    efficiency: float        # worm driving, at friction mu
    self_locking: bool       # the wheel cannot drive the worm back (tan(lead) < mu)
    mu: float


def worm_numbers(module: float, starts: int, z_wheel: int, worm_d: float, mu: float, pressure_deg: float = 20.0) -> WormSet:
    """Worm-set geometry and efficiency. Lead angle L = atan(starts m / d); worm driving efficiency
    eta = (cos(phi_n) - mu tan L) / (cos(phi_n) + mu cot L) (the standard worm-driving efficiency, as in Shigley's
    Mechanical Engineering Design, worm gearing); self-locking when the wheel cannot back-drive it: tan L < mu (the friction angle exceeds the lead
    angle; vibration can still creep it, so a holding brake is safer where it matters)."""
    lam = math.atan(starts * module / worm_d)
    pn = math.radians(pressure_deg)
    eta = (math.cos(pn) - mu * math.tan(lam)) / (math.cos(pn) + mu / math.tan(lam))
    return WormSet(module, int(starts), int(z_wheel), worm_d, (worm_d + module * z_wheel) / 2, z_wheel / starts,
                   math.degrees(lam), eta, math.tan(lam) < mu, mu)


def worm(module: float, starts: int, worm_d: float, length: float, bore: float | None = None):
    """A printable worm: 20 deg trapezoid thread (addendum 1 m, dedendum 1.25 m) swept on a helix of lead
    pi m starts around a root cylinder, trimmed to `length` (Z from 0). Prints standing up: the flanks are 70 deg from
    the bed, no support."""
    from build123d import Box, Helix, Plane, Polyline, Wire, make_face, sweep
    lead = math.pi * module * starts
    r_root, h, pa = worm_d / 2 - 1.25 * module, 2.25 * module, math.radians(20)
    w_root = math.pi * module / 2 + 2 * 1.25 * module * math.tan(pa)
    w_tip = math.pi * module / 2 - 2 * 1.0 * module * math.tan(pa)
    if worm_d / 2 - 1.25 * module < 2.0 + (bore or 0) / 2:
        raise ValueError(f"worm pitch diameter {worm_d} leaves under 2 mm of root around the bore")
    body = Cylinder(r_root, length + 2 * module * 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body = Pos(0, 0, -module * 4) * body
    for k in range(starts):
        prof = Polyline((r_root - 0.2, -w_root / 2), (r_root + h, -w_tip / 2), (r_root + h, w_tip / 2), (r_root - 0.2, w_root / 2), close=True)
        face = Pos(0, 0, -module * 4 + k * lead / starts) * (Plane.XZ * make_face(prof))
        hx = Pos(0, 0, -module * 4 + k * lead / starts) * Helix(pitch=lead, height=length + 8 * module, radius=0.001)
        body += sweep(face, path=Wire(hx), is_frenet=True)
    body &= Box(worm_d * 2, worm_d * 2, length, align=(Align.CENTER, Align.CENTER, Align.MIN))
    if bore:
        body -= Cylinder(bore / 2, length, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return Part(body.wrapped)
