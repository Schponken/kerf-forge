"""Engineering drawings: one PDF per printed part (out/drawings/<part>.pdf), made with cadgen's `eng_drawing`
(cadgen 0.8.4, MIT; docs/teardowns/text-to-cad.md).

Each sheet has the top, front and right views (third angle, hidden lines) plus an isometric, the overall dimensions,
one hole callout per interface hole group, and a title block with the part, project, material and slicer settings and
the print orientation. Hole sizes are MEASURED on the built part (the coaxial cylinder faces at each fastener / pin
site), so a callout states what the printer will cut, measured fits included; the label says what the hole is for
(heat-set insert, self-tap pilot, nut trap, clearance, pin fit).
"""
from __future__ import annotations

import contextlib
import json
import math
import os
from pathlib import Path

from build123d import Location, Rot, Vector

from . import partcache

os.environ.setdefault("CADGEN_TELEMETRY", "0")     # cadgen counts usage by default; Kerf sends nothing anywhere

SCALES = (1.0, 0.5, 0.4, 0.2, 0.1)                 # ISO 5455 scales, largest first
# ISO 5455 enlargements, tried after the reductions: a part a few mm across (a control horn) leaves cadgen's view
# labels hanging off the frame at 1:1, so it is drawn bigger
ENLARGE = (2.0, 5.0)
SIZES = ("A4", "A3", "A2")
LABEL = {"heatset": "HEAT-SET INSERT", "tap": "SELF-TAP PILOT", "nut_trap": "NUT TRAP", "clearance": "CLEARANCE",
         "counterbore": "CLEARANCE", "countersink": "CLEARANCE", "threaded": "THREADED",
         "free": "PIN, FREE FIT", "press": "PIN, PRESS FIT"}


def _axis_of(loc):
    """Site origin and its +Z (out of the material) in the part frame."""
    o = loc.position
    return Vector(o), ((loc * Location((0, 0, 1))).position - o).normalized()


def _coaxial(shape, o, a, tol=0.05):
    """Concave (hole) cylinder and cone faces of `shape` coaxial with the line (o, a): [(type, r_max, t_min, t_max)],
    t along a."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder
    out = []
    for f in shape.faces():
        s = BRepAdaptor_Surface(f.wrapped)
        st = s.GetType()
        if st not in (GeomAbs_Cylinder, GeomAbs_Cone):
            continue
        ax = (s.Cylinder() if st == GeomAbs_Cylinder else s.Cone()).Axis()
        d = ax.Direction()
        if abs(d.X() * a.X + d.Y() * a.Y + d.Z() * a.Z) < 0.999:
            continue
        p = ax.Location()
        w = (p.X() - o.X, p.Y() - o.Y, p.Z() - o.Z)
        along = w[0] * a.X + w[1] * a.Y + w[2] * a.Z
        off = math.sqrt(max(0.0, w[0] ** 2 + w[1] ** 2 + w[2] ** 2 - along ** 2))
        if off > tol:
            continue
        pt, nv = f.position_at(0.5, 0.5), f.normal_at(0.5, 0.5)     # a bore, not a boss: the face's outward
        rad = (pt - o) - a * ((pt - o).dot(a))                        # normal points at the axis
        if nv.dot(rad) >= 0:
            continue
        ts, rs = [], []
        for v in f.vertices():
            q = (v.X - o.X, v.Y - o.Y, v.Z - o.Z)
            t = q[0] * a.X + q[1] * a.Y + q[2] * a.Z
            ts.append(t)
            rs.append(math.sqrt(max(0.0, q[0] ** 2 + q[1] ** 2 + q[2] ** 2 - t ** 2)))
        if st == GeomAbs_Cylinder:
            r = s.Cylinder().Radius()
        else:
            r = max(rs) if rs else 0.0
        if not ts:                                  # full cylinder without vertices: use its parameter range
            ts = [s.FirstVParameter(), s.LastVParameter()]
        out.append(("cyl" if st == GeomAbs_Cylinder else "cone", r, min(ts), max(ts)))
    return out


def measure(shape, loc, kind: str) -> dict | None:
    """The hole at a site as a cadgen hole spec: diameter, depth or THRU, counterbore / countersink. None when no
    coaxial round face is found there (e.g. a hex-only pocket)."""
    o, a = _axis_of(loc)
    faces = _coaxial(shape, o, a)
    cyl = [f for f in faces if f[0] == "cyl"]
    if not cyl:
        return None
    hole = {}
    if kind == "counterbore":                       # the site sits on the counterbore floor; the head pocket is above
        main = min(cyl, key=lambda f: f[1])
        above = [f for f in cyl if f[1] > main[1] + 0.05 and f[2] >= -0.05]
        if above:
            cb = max(above, key=lambda f: f[1])
            hole["cbore"] = (round(2 * cb[1], 2), round(cb[3] - cb[2], 2))
    else:
        entry = [f for f in cyl if f[3] >= -0.3]    # the bore that opens at the site's surface
        main = min(entry, key=lambda f: f[1]) if entry else max(cyl, key=lambda f: f[3])   # the bore itself, not a
                                                    # larger coaxial recess (knuckle slot) around it
        cones = [f for f in faces if f[0] == "cone"]
        if kind == "countersink" and cones:
            hole["csk"] = (round(2 * max(c[1] for c in cones), 2), 90.0)
    hole["diameter"] = round(2 * main[1], 2)
    # blind or through: material just past the bore's end, off the axis inside the bore's radius (a narrower relief
    # bore continuing on the axis does not make it THRU)
    side = a.cross(Vector(1, 0, 0) if abs(a.X) < 0.9 else Vector(0, 1, 0)).normalized()
    probe = o + a * (main[2] - 0.5) + side * (0.8 * main[1])
    if shape.is_inside(probe):
        hole["depth"] = round(-main[2], 2)
    else:
        hole["thru"] = True
    return hole


def _view_for(a) -> str:
    """The orthographic view that looks straight down a hole axis."""
    ax = max(((abs(a.X), "right"), (abs(a.Y), "front"), (abs(a.Z), "top")))
    return ax[1]


def callouts(it) -> list[dict]:
    """One callout per (interface group, hole kind, measured size, view) on this part, with the hole count."""
    groups: dict = {}
    sh = it.shape
    for s in getattr(sh, "kerf_sites", []):
        groups.setdefault(("site", s.group, s.kind, s.screw), []).append(s.loc)
    for p in getattr(sh, "kerf_pins", []):
        groups.setdefault(("pin", p.group, p.fit, p.pin), []).append(p.loc)
    out = []
    for (src, group, kind, what), locs in groups.items():
        sub: dict = {}
        for loc in locs:
            m = measure(sh, loc, kind)
            o, a = _axis_of(loc)
            k = (json.dumps(m, sort_keys=True), _view_for(a))
            sub.setdefault(k, []).append((o, m))
        for (_, view), pts in sub.items():
            pts.sort(key=lambda q: -_SHEET_XY[view](q[0])[0])   # lead from the rightmost hole: callout text to the
            m = pts[0][1]                                       # right, where the sheet has room
            name = what.split(".")[-1].upper() if src == "pin" else what
            label = f"{name} {LABEL.get(kind, kind.upper())}"
            out.append({"group": group, "kind": kind, "what": what, "count": len(pts), "view": view,
                        "at": [round(v, 3) for v in pts[0][0]], "hole": m, "label": label})
    seen: dict = {}                                  # same text twice in one view: name the groups apart
    for c in out:
        seen.setdefault((c["view"], c["label"], json.dumps(c["hole"], sort_keys=True)), []).append(c)
    for same in seen.values():
        if len(same) > 1:
            for c in same:
                c["label"] += f" ({c['group']})"
    return out


def _print_up(spec) -> str:
    """Which part-frame direction faces up on the printer bed (print_rot applied as checks.oriented does)."""
    rot = spec.get("print_rot", [0, 0, 0])
    if not any(rot):
        return "+Z (AS DRAWN, TOP VIEW UP)"
    best = None
    for n, v in (("+X", (1, 0, 0)), ("-X", (-1, 0, 0)), ("+Y", (0, 1, 0)), ("-Y", (0, -1, 0)), ("+Z", (0, 0, 1)), ("-Z", (0, 0, -1))):
        w = (Rot(*rot) * Location(v)).position
        if best is None or w.Z > best[1]:
            best = (n, w.Z)
    return f"{best[0]} (PRINT_ROT {list(rot)})"


def _sheet(proj, pid, it, size, scale, calls, hidden=True):
    from cadgen.eng_drawing import Sheet
    spec = it.spec
    mat = str(spec.get("material", "PETG")).upper()
    notes = [f"PRINT ON {str(proj.data.get('printer', 'Bambu Lab A2L')).upper()}: {mat}, "
             f"{int(spec.get('walls', 2))} WALLS, {round(float(spec.get('infill', 0.25)) * 100)} % INFILL.",
             f"PRINT ORIENTATION: PART {_print_up(spec)} FACES UP.",
             "HOLE SIZES AS MODELLED FOR FDM (MEASURED FITS INCLUDED); DO NOT DRILL OUT."]
    if it.role == "manufactured":
        from .manufacturing import label
        mat = it.spec["manufacturing"]["stock"]
        notes = [label(it).upper(), "PART FRAME, MILLIMETRES; FINISHED GEOMETRY IN STEP.",
                 "CONFIRM TOLERANCES, TOOLING AND STOCK STRENGTH WITH SUPPLIER; SEE MANUFACTURING/ORDER.MD."]
    if not hidden:
        notes.append("HIDDEN LINES OMITTED; SEE THE ISOMETRIC AND THE 3D MODEL (STEP / VIEWER).")
    sh = Sheet(size, scale=scale, title=pid.upper().replace("_", " "), part_number=f"{proj.dir.name}/{pid}",
               material=mat, author="KERF FORGE", notes=notes,
               general_tolerance="AGREE WITH SUPPLIER" if it.role == "manufactured" else "ISO 2768-m")
    top, front, right, _iso = sh.three_views(it.shape, iso=True, hidden=hidden)
    front.overall()                                 # width (X) and height (Z)
    right.overall()                                 # depth (Y) and height
    views = {"top": top, "front": front, "right": right}
    for c in calls:
        v = views[c["view"]]
        if c["hole"]:
            h = c["hole"]
            v.hole(c["at"], h["diameter"], **{k: x for k, x in h.items() if k != "diameter"},   # depth|thru, cbore, csk
                   count=c["count"] if c["count"] > 1 else None, label=c["label"])
        else:
            v.note(f"{c['count']}x {c['label']}" if c["count"] > 1 else c["label"], c["at"])
    return sh


# sheet (x, y) of a model vector in each view (cadgen VIEW_DIRECTIONS: top looks down -Z with +Y up, front looks
# along +Y with +Z up, right looks along -X with +Z up)
_SHEET_XY = {"top": lambda d: (d.X, d.Y), "front": lambda d: (d.X, d.Z), "right": lambda d: (d.Y, d.Z)}


def _on_sheet(sheet) -> bool:
    """Everything cadgen drew (views, dimensions, callout text, notes) lies inside the sheet frame. cadgen refuses
    views that run off the frame but not annotations, which can (a dimension above the top view, a long callout)."""
    import ezdxf.bbox
    from cadgen import eng_drawing as E
    doc = E._render_sheet(sheet, index=1, count=1, label=sheet.part_number)
    ext = ezdxf.bbox.extents(doc.modelspace(), fast=False)
    m = E._MARGIN - 0.5
    return ext.extmin.x >= m and ext.extmin.y >= m and ext.extmax.x <= sheet.width - m and ext.extmax.y <= sheet.height - m


MIN_EDGE_MM = 1e-3


@contextlib.contextmanager
def _no_point_edges():
    """cadgen 0.8.4's hidden-line projection keeps edges that run straight along the view direction; they project to
    a point and cadgen's own DXF validation then refuses the sheet (zero_length_entity). Drop edges shorter than a
    micron from the projection while Kerf draws (nothing that short can be seen on paper)."""
    from build123d import ShapeList
    from cadgen import eng_drawing as E
    orig = E._project_to_viewport

    def project(*a, **k):
        vis, hid = orig(*a, **k)
        return (ShapeList(e for e in vis if e.length >= MIN_EDGE_MM), ShapeList(e for e in hid if e.length >= MIN_EDGE_MM))
    E._project_to_viewport = project
    try:
        yield
    finally:
        E._project_to_viewport = orig


def part_drawing(proj, pid, it, path: Path) -> dict:
    """Write one part's drawing; returns what is on it (views, sheet size, scale, callouts, hidden lines).
    Drawn in the part's own frame (the frame its sites are in), whatever assembled position the check left it in."""
    from types import SimpleNamespace
    sh = it.shape.located(Location())
    for a in ("kerf_sites", "kerf_pins"):
        setattr(sh, a, getattr(it.shape, a, []))
    it = SimpleNamespace(id=it.id, role=it.role, spec=it.spec, shape=sh)
    with _no_point_edges():
        return _part_drawing(proj, pid, it, path)


def _part_drawing(proj, pid, it, path: Path) -> dict:
    import io
    from cadgen.eng_drawing import eng_drawing
    from cadgen.engine.export.dxf import DrawingValidationError
    calls = callouts(it)
    err = None
    for hidden in (True, False):
        for scale in SCALES + ENLARGE:
            for size in SIZES:
                try:
                    sheet = _sheet(proj, pid, it, size, scale, calls, hidden)
                    if not _on_sheet(sheet):
                        err = "annotations run off the sheet"
                        continue

                    def drawing():
                        return sheet
                    drawing.__name__ = drawing.__qualname__ = pid       # cadgen labels the sheet with this name
                    with contextlib.redirect_stdout(io.StringIO()):
                        eng_drawing(out=str(path.resolve()))(drawing)()
                    return {"part": pid, "pdf": path.name, "sheet": size, "scale": scale, "hidden_lines": hidden,
                            "views": ["top", "front", "right", "iso"], "callouts": calls}
                except DrawingValidationError as e:
                    # cadgen's hidden-line projection of some fillets yields zero-length edges, which its own DXF
                    # validation refuses: draw that part without hidden lines (a note on the sheet says so)
                    if hidden and all(getattr(f, "layer", None) == "HIDDEN" or "HIDDEN" in f.render() for f in e.findings):
                        err = e
                        break
                    raise
                except ValueError as e:                # a view or a note runs off this sheet: next size / scale
                    err = e
            else:
                continue
            break
    raise RuntimeError(f"{pid}: no sheet up to {SIZES[-1]} from 1:{round(1 / SCALES[-1])} to {max(SCALES + ENLARGE):g}:1 fits the drawing ({err})")


def write_all(proj, outdir: Path) -> dict:
    """out/drawings/<part>.pdf for every printed part, and index.json listing them. Returns {part: summary|error}."""
    outdir.mkdir(parents=True, exist_ok=True)
    res = {}
    for pid, it in proj.fabricated.items():
        if it.shape is None:
            continue
        pdf = outdir / f"{pid}.pdf"
        hit = partcache.lookup_extra(it.cache_key, "drawing") if it.cached else None
        if hit is not None:                                       # unchanged part: same drawing (kerf/partcache.py)
            pdf.write_bytes(hit["pdf_bytes"])
            res[pid] = hit["summary"]
            continue
        try:
            with partcache.recording() as deps:
                res[pid] = part_drawing(proj, pid, it, pdf)
            partcache.store_extra(it.cache_key, "drawing", {"summary": res[pid], "pdf_bytes": pdf.read_bytes()}, deps)
        except Exception as e:  # noqa: BLE001 — one part's drawing failing is reported, the rest still draw
            res[pid] = {"part": pid, "error": f"{type(e).__name__}: {e}"}
    (outdir / "index.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    return res
