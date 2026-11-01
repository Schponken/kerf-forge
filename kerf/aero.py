"""Fixed-wing aircraft: airfoils, wing planform numbers and printable wing geometry.

Coordinates: X aft (chord direction, leading edge first), Y spanwise (+Y = right wing), Z up. Lengths in mm.

Airfoils
  `airfoil(name)` -> (N, 2) unit-chord points in Selig order (upper TE -> LE -> lower TE). `naca0010`, `naca2412`, ...
  are generated (NACA 4-digit equations, closed-TE coefficient); any other name is read unchanged from
  catalog/airfoils/<name>.dat (UIUC coordinate database, Selig or Lednicer format; sources in catalog/airfoils/SOURCES.md).
  `airfoil_data(name)` -> catalog/airfoils/airfoils.json entry (thickness, Cm0, CLmax at a Reynolds number, sources).

Planform (`Planform`): a straight-tapered, swept wing measured from the aircraft centreline: root chord at y = 0,
  tip chord at y = span/2, leading-edge sweep, dihedral, linear washout to `twist_tip_deg` (negative = tip nose down),
  twist about the quarter chord. `geometry()` gives area, aspect ratio, taper, MAC, its spanwise station and leading
  edge x, and the neutral point (aerodynamic centre of a tailless wing = quarter MAC; Nickel & Wohlfahrt, "Tailless
  Aircraft in Theory and Practice", ch. 2; also the standard trapezoid MAC formulas).

Printable geometry
  `wing_solid(pf, y0, y1)` lofts the wing between two span stations (a straight loft between sections, exact for a
  straight-tapered wing), with the trailing edge thickened to `te_min` so it prints and makes a valid solid.
  `spar_line(pf, frac_root, frac_tip)` is a straight spar through the wing's thickness centre at two chord fractions;
  `spar_channel(...)` the cylinder to cut for it. `elevon_split(pf, solid, y0, y1, hinge_frac)` cuts a control
  surface off a wing solid: bottom hinge line (tape / TPU hinge) at `hinge_frac` of the local chord, a V gap opening
  on top so the surface can deflect up by `gap_deg` and down freely. Returns (wing, elevon, hinge axis).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
AIRFOILS = ROOT / "catalog" / "airfoils"


# ---------------------------------------------------------------- airfoils
def naca4(code: str, n: int = 60) -> np.ndarray:
    """NACA 4-digit section (m p tt), closed trailing edge, cosine spacing; Selig order."""
    m, p, t = int(code[0]) / 100, int(code[1]) / 10, int(code[2:]) / 100
    beta = np.linspace(0, math.pi, n)
    x = (1 - np.cos(beta)) / 2
    yt = 5 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1036 * x ** 4)
    if m and p:
        yc = np.where(x < p, m / p ** 2 * (2 * p * x - x ** 2), m / (1 - p) ** 2 * (1 - 2 * p + 2 * p * x - x ** 2))
        dy = np.where(x < p, 2 * m / p ** 2 * (p - x), 2 * m / (1 - p) ** 2 * (p - x))
    else:
        yc, dy = np.zeros_like(x), np.zeros_like(x)
    th = np.arctan(dy)
    xu, zu = x - yt * np.sin(th), yc + yt * np.cos(th)
    xl, zl = x + yt * np.sin(th), yc - yt * np.cos(th)
    up = np.c_[xu, zu][::-1]
    lo = np.c_[xl, zl][1:]
    return np.vstack([up, lo])


def parse_dat(text: str) -> np.ndarray:
    """UIUC .dat: a name line, then x z pairs. Selig = one loop TE->LE->TE; Lednicer = a 'n_up n_lo' count line, then
    upper LE->TE and lower LE->TE. Returns Selig order, x scaled to 0..1."""
    rows = []
    for ln in text.splitlines()[1:]:
        parts = ln.replace(",", " ").split()
        if len(parts) >= 2:
            try:
                rows.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
    a = np.array(rows, float)
    if len(a) and a[0, 0] > 1.5 and a[0, 0] == int(a[0, 0]) and a[0, 1] == int(a[0, 1]) \
            and int(a[0, 0] + a[0, 1]) == len(a) - 1:   # Lednicer: first row is the point counts
        nu, nl = int(a[0, 0]), int(a[0, 1])
        up, lo = a[1:1 + nu], a[1 + nu:1 + nu + nl]
        a = np.vstack([up[::-1], lo[1:] if np.allclose(lo[0], up[0]) else lo])
    xmin, xmax = a[:, 0].min(), a[:, 0].max()
    a[:, 0] = (a[:, 0] - xmin) / (xmax - xmin)
    a[:, 1] = a[:, 1] / (xmax - xmin)
    keep = np.r_[True, np.any(np.abs(np.diff(a, axis=0)) > 1e-9, axis=1)]   # repeated points break splines
    return a[keep]


def airfoil(name: str) -> np.ndarray:
    name = name.lower()
    if name.startswith("naca") and len(name) == 8 and name[4:].isdigit():
        return naca4(name[4:], 50)
    f = AIRFOILS / f"{name}.dat"
    if not f.exists():
        raise ValueError(f"airfoil '{name}': no catalog/airfoils/{name}.dat (download it from the UIUC database and "
                         f"list it in catalog/airfoils/SOURCES.md) and not a NACA 4-digit name")
    return parse_dat(f.read_text(encoding="utf-8", errors="replace"))


def airfoil_data(name: str) -> dict:
    f = AIRFOILS / "airfoils.json"
    data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    hit = {k.lower(): v for k, v in data.items() if not k.startswith("_")}.get(name.lower())
    if hit is None:
        raise ValueError(f"airfoil '{name}' has no entry in catalog/airfoils/airfoils.json (thickness, Cm0, CLmax, sources)")
    return hit


def clmax_2d(name: str, re: float | None = None) -> tuple[float, float]:
    """(2D clmax, Reynolds number it is for) from airfoils.json `re: {"200000": {"clmax": ...}}`: the highest listed
    Reynolds number not above `re` (the lowest listed when re is None or below all: lower Re = lower clmax = safe)."""
    d = airfoil_data(name)
    rows = sorted((float(k), v) for k, v in (d.get("re") or {}).items())
    if not rows:
        if "cl_max" in d:
            return float(d["cl_max"]), float(d.get("re_ref", 0))
        raise ValueError(f"airfoil '{name}': no clmax in catalog/airfoils/airfoils.json")
    pick = rows[0]
    for r, v in rows:
        if re is not None and r <= re:
            pick = (r, v)
    return float(pick[1]["clmax"]), pick[0]


def thickness(af: np.ndarray) -> float:
    """Max thickness / chord, from the upper and lower curves on a common x grid."""
    i = int(np.argmin(af[:, 0]))
    up, lo = af[:i + 1][::-1], af[i:]
    xs = np.linspace(0.01, 0.99, 197)
    zu = np.interp(xs, up[:, 0], up[:, 1])
    zl = np.interp(xs, lo[:, 0], lo[:, 1])
    return float(np.max(zu - zl))


def mid_z(af: np.ndarray, x: float) -> tuple[float, float]:
    """(upper z, lower z) of a unit-chord airfoil at chord fraction x."""
    i = int(np.argmin(af[:, 0]))
    up, lo = af[:i + 1][::-1], af[i:]
    return float(np.interp(x, up[:, 0], up[:, 1])), float(np.interp(x, lo[:, 0], lo[:, 1]))


# ---------------------------------------------------------------- planform
@dataclass
class Planform:
    span: float                    # tip to tip, mm
    root_chord: float              # at the centreline (y = 0)
    tip_chord: float
    sweep_le_deg: float = 0.0
    dihedral_deg: float = 0.0
    twist_tip_deg: float = 0.0     # washout: negative = tip nose down (twist about the quarter chord)
    root_airfoil: str = "naca0010"
    tip_airfoil: str | None = None
    x_le0: float = 0.0             # leading edge x at the centreline
    z0: float = 0.0                # chord line height at the centreline
    te_min: float = 0.6            # printed trailing-edge thickness, mm

    @classmethod
    def from_params(cls, p, prefix: str = "wing_") -> "Planform":
        g = lambda k, d=None: getattr(p, prefix + k, d)
        return cls(span=g("span"), root_chord=g("root_chord"), tip_chord=g("tip_chord"), sweep_le_deg=g("sweep_le_deg", 0.0),
                   dihedral_deg=g("dihedral_deg", 0.0), twist_tip_deg=g("twist_tip_deg", 0.0),
                   root_airfoil=g("airfoil", "naca0010"), tip_airfoil=g("tip_airfoil"), x_le0=g("x_le0", 0.0), z0=g("z0", 0.0),
                   te_min=g("te_min", 0.6))

    @property
    def semi(self) -> float:
        return self.span / 2

    def chord(self, y: float) -> float:
        return self.root_chord + (self.tip_chord - self.root_chord) * abs(y) / self.semi

    def x_le(self, y: float) -> float:
        return self.x_le0 + abs(y) * math.tan(math.radians(self.sweep_le_deg))

    def z_le(self, y: float) -> float:
        return self.z0 + abs(y) * math.tan(math.radians(self.dihedral_deg))

    def twist(self, y: float) -> float:
        return self.twist_tip_deg * abs(y) / self.semi

    def section_af(self, y: float) -> np.ndarray:
        a = airfoil(self.root_airfoil)
        if not self.tip_airfoil or self.tip_airfoil == self.root_airfoil:
            return a
        b = airfoil(self.tip_airfoil)
        t = abs(y) / self.semi
        # blend on a common cosine grid (upper and lower separately)
        return (1 - t) * _resample(a) + t * _resample(b)

    def section(self, y: float, n_te: bool = True) -> np.ndarray:
        """(N, 3) world points of the section at span station y: chord-scaled, TE thickened to te_min, twisted about
        the quarter chord (positive = nose up), placed at the planform's leading edge."""
        c = self.chord(y)
        af = self.section_af(y).copy()
        if n_te and self.te_min > 0:
            i = int(np.argmin(af[:, 0]))
            half = self.te_min / 2 / c
            af[:i, 1] += half * af[:i, 0]                 # upper surface lifts towards the TE
            af[i + 1:, 1] -= half * af[i + 1:, 0]         # lower surface drops towards the TE
        x, z = af[:, 0] * c, af[:, 1] * c
        th = math.radians(self.twist(y))
        xq = 0.25 * c
        xr = xq + (x - xq) * math.cos(th) + z * math.sin(th)
        zr = -(x - xq) * math.sin(th) + z * math.cos(th)
        return np.c_[xr + self.x_le(y), np.full_like(xr, y), zr + self.z_le(y)]

    def geometry(self) -> dict:
        """Area, aspect ratio, taper, MAC (length, spanwise station, leading-edge x) and the neutral point x (quarter
        MAC), for the whole trapezoid (the part inside a fuselage counts: it lifts on a flying wing)."""
        cr, ct, b = self.root_chord, self.tip_chord, self.span
        lam = ct / cr
        S = b * (cr + ct) / 2
        mac = 2 / 3 * cr * (1 + lam + lam ** 2) / (1 + lam)
        y_mac = b / 6 * (1 + 2 * lam) / (1 + lam)
        x_mac = self.x_le(y_mac)
        return {"area_mm2": S, "area_dm2": S / 1e4, "aspect_ratio": b ** 2 / S, "taper": lam, "mac_mm": mac,
                "y_mac_mm": y_mac, "x_le_mac_mm": x_mac, "x_np_mm": x_mac + 0.25 * mac,
                "sweep_c4_deg": math.degrees(math.atan(math.tan(math.radians(self.sweep_le_deg)) - (cr - ct) / (2 * b)))}


def _resample(af: np.ndarray, n: int = 81) -> np.ndarray:
    xs = (1 - np.cos(np.linspace(0, math.pi, n))) / 2
    i = int(np.argmin(af[:, 0]))
    up, lo = af[:i + 1][::-1], af[i:]
    zu = np.interp(xs, up[:, 0], up[:, 1])
    zl = np.interp(xs, lo[:, 0], lo[:, 1])
    return np.vstack([np.c_[xs, zu][::-1], np.c_[xs, zl][1:]])


# ---------------------------------------------------------------- solids
def _section_face(pts: np.ndarray):
    """Closed section face: a polygon through the airfoil points (the TE thickness closes it). Polygons, not splines:
    a ruled loft between them has flat / ruled faces whose volume, mass and booleans OCC computes exactly (a spline loft
    of the same wing reported 20 % too little volume with the default integration)."""
    from build123d import Face, Wire
    P = [tuple(map(float, q)) for q in pts]
    f = Face(Wire.make_polygon(P, close=True))
    if f.normal_at().Y < 0:          # lofts run towards +Y: keep every section facing +Y
        f = Face(Wire.make_polygon(P[::-1], close=True))
    return f


def wing_solid(pf: Planform, y0: float, y1: float, stations: int = 2):
    """The wing between span stations y0 < y1 (same side), lofted through `stations` sections (2 = straight loft,
    exact for a straight-tapered wing with linear twist only at its ends; use more when twist or airfoil blend vary)."""
    from build123d import Solid
    ys = np.linspace(y0, y1, max(2, stations))
    faces = [_section_face(pf.section(float(y))) for y in ys]
    return Solid.make_loft([f.outer_wire() for f in faces], ruled=True)


def spar_point(pf: Planform, y: float, frac: float) -> np.ndarray:
    """Point at chord fraction `frac` of station y, half-way between the upper and lower surfaces (untwisted
    section frame; twist moves it by well under a millimetre at the small angles used)."""
    c = pf.chord(y)
    zu, zl = mid_z(pf.section_af(y), frac)
    th = math.radians(pf.twist(y))
    x, z = frac * c, (zu + zl) / 2 * c
    xq = 0.25 * c
    xr = xq + (x - xq) * math.cos(th) + z * math.sin(th)
    zr = -(x - xq) * math.sin(th) + z * math.cos(th)
    return np.array([xr + pf.x_le(y), y, zr + pf.z_le(y)])


def depth_at(pf: Planform, y: float, frac: float) -> float:
    """Wing thickness (mm) at chord fraction `frac` of station y."""
    zu, zl = mid_z(pf.section_af(y), frac)
    return (zu - zl) * pf.chord(y)


def spar_line(pf: Planform, frac_root: float, frac_tip: float, y_root: float, y_tip: float) -> tuple[np.ndarray, np.ndarray]:
    """A straight spar from (y_root, frac_root) to (y_tip, frac_tip), through the thickness centre at both ends."""
    return spar_point(pf, y_root, frac_root), spar_point(pf, y_tip, frac_tip)


def cylinder_between(a, b, d: float, extend: float = 0.0):
    """A cylinder of diameter d from point a to point b (extended by `extend` at both ends)."""
    from build123d import Align, Cylinder, Location, Plane
    a, b = np.asarray(a, float), np.asarray(b, float)
    u = (b - a) / np.linalg.norm(b - a)
    a2 = a - u * extend
    L = float(np.linalg.norm(b - a)) + 2 * extend
    c = Cylinder(d / 2, L, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return Location(Plane(origin=tuple(a2), z_dir=tuple(u))) * c


def spar_channel(pf: Planform, line, d: float, extend: float = 30.0):
    return cylinder_between(line[0], line[1], d, extend)


def hinge_axis(pf: Planform, y0: float, y1: float, frac: float) -> tuple[np.ndarray, np.ndarray]:
    """The elevon hinge line: through the lower surface at chord fraction `frac` at y0 and y1 (bottom hinge)."""
    pts = []
    for y in (y0, y1):
        c = pf.chord(y)
        zu, zl = mid_z(pf.section_af(y), frac)
        lo_half = pf.te_min / 2 * frac                       # the TE thickening at that station
        x, z = frac * c, zl * c - lo_half
        th = math.radians(pf.twist(y))
        xq = 0.25 * c
        xr = xq + (x - xq) * math.cos(th) + z * math.sin(th)
        zr = -(x - xq) * math.sin(th) + z * math.cos(th)
        pts.append(np.array([xr + pf.x_le(y), y, zr + pf.z_le(y)]))
    return pts[0], pts[1]


def _halfspace(origin, axis_dir, normal, size=4000.0):
    """A big box filling the side of the plane (through `origin`, containing `axis_dir`) that `normal` points to."""
    from build123d import Align, Box, Location, Plane
    n = np.asarray(normal, float) / np.linalg.norm(normal)
    d = np.asarray(axis_dir, float) / np.linalg.norm(axis_dir)
    pl = Plane(origin=tuple(map(float, origin)), x_dir=tuple(map(float, d)), z_dir=tuple(map(float, n)))
    return Location(pl) * Box(size, size, size / 2, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _slab(a, b, inset=0.0):
    """The region between the planes through a and b square to the line a-b (moved `inset` mm inwards at both ends).
    Square to the hinge, not to Y: a surface turning about a swept hinge keeps its ends in those planes."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = (b - a) / np.linalg.norm(b - a)
    x = np.cross(d, [0, 0, 1.0]) if abs(d[2]) < 0.9 else np.cross(d, [1.0, 0, 0])
    return _halfspace(a + d * inset, x, d) & _halfspace(b - d * inset, x, -d)


def elevon_split(pf: Planform, solid, y0: float, y1: float, hinge_frac: float, gap_deg: float = 30.0, gap: float = 0.6,
                 end_gap: float = 1.0):
    """Cut a control surface between span stations y0 < y1 (same side) off `solid`. Bottom hinge at `hinge_frac` of
    the chord; on top a V gap of `gap_deg` (half on the wing, half on the surface) lets it deflect up by about
    gap_deg and down freely; `gap` mm of clearance at the hinge line; the surface's ends are square to the hinge with
    `end_gap` mm to the wing. Returns (wing, surface, (hinge_a, hinge_b))."""
    a, b = hinge_axis(pf, y0, y1, hinge_frac)
    d = (b - a) / np.linalg.norm(b - a)
    half = math.radians(gap_deg / 2)
    # in the plane normal to the hinge: "aft" = +X projected off the hinge axis, "up" = +Z likewise
    aft = np.array([1.0, 0, 0]) - d * d[0]
    aft /= np.linalg.norm(aft)
    up = np.cross(d, aft)
    if up[2] < 0:
        up = -up
    # wing keeps what is in front of a face leaning forward by `half` from vertical; the surface what is behind a face
    # leaning aft by `half`, moved back by `gap`
    n_wing = aft * math.cos(half) + up * math.sin(half)          # normal of the wing's aft face (pointing aft)
    n_surf = aft * math.cos(half) - up * math.sin(half)          # normal of the surface's front face (pointing aft)
    cut_wing = _halfspace(a, d, n_wing) & _slab(a, b)
    surf_region = _halfspace(a + aft * gap, d, n_surf) & _slab(a, b, end_gap)
    wing = solid - cut_wing
    surf = solid & surf_region
    return wing, surf, (a, b)


def largest(shape):
    """The biggest solid of a boolean result (slivers from a cut are dropped)."""
    sols = shape.solids() if hasattr(shape, "solids") else [shape]
    return max(sols, key=lambda s: s.volume)


# ---------------------------------------------------------------- aerodynamics
RHO = 1.225          # kg/m^3, ISA sea level
G = 9.80665


def stall_speed_kmh(mass_g: float, area_m2: float, cl_max: float, rho: float = RHO) -> float:
    """Level-flight stall speed V = sqrt(2 W / (rho S CLmax))."""
    W = mass_g / 1000 * G
    return math.sqrt(2 * W / (rho * area_m2 * cl_max)) * 3.6


def reynolds(v_ms: float, chord_mm: float, nu: float = 1.46e-5) -> float:
    return v_ms * chord_mm / 1000 / nu


def root_moment_nmm(mass_g: float, n: float, semi_mm: float, y_root_mm: float) -> float:
    """Bending moment at span station y_root of one wing half carrying n g with an elliptical lift distribution:
    the half's lift n W / 2 integrated outboard of y_root with its moment arm about y_root."""
    W = mass_g / 1000 * G * n
    s = semi_mm
    ys = np.linspace(y_root_mm, s, 2001)
    q = np.sqrt(np.clip(1 - (ys / s) ** 2, 0, None))           # elliptical loading shape
    q0 = (W / 2) / (math.pi * s / 4)                            # N/mm: integral of q0 sqrt(1-(y/s)^2) over 0..s = W/2
    return float(np.trapezoid(q0 * q * (ys - y_root_mm), ys))
