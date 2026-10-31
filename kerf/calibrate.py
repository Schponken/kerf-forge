"""Print-truth loop: fit offsets measured on Spencer's own printer, per printer + material, applied by kerf/iface.py.

1. `kerf calibrate --material PETG` builds a test coupon (out/calibration/<printer>_<material>/coupon.stl/.3mf + CARD.md):
   M2/M2.5/M3 clearance, self-tap pilot and heat-set holes, 608 and 623 bearing pockets, 3 mm dowel holes at
   0.2/0.3/0.4 mm slip clearance plus one press hole, and an MG90S servo-tab window. Every iface-made feature on it
   already carries the current offsets, so each print tests the sizes the next design would get.
2. Spencer prints it and reports what fit: `kerf feedback PETG hole_M3=tight insert_M3=ok bearing_608=loose pin_0.3=ok`.
   tight = too small (the screw/insert/bearing/servo will not go in nicely) -> hole grows by one step;
   loose = too big (wobbles, strips, falls out) -> shrinks one step; ok = keep; a signed number = that many mm.
   Slip pins: the smallest clearance reported ok becomes the free-pin allowance.
3. Offsets are stored in catalog/printers/<printer>.json with the date and what was reported (history), and every
   later build of a part with that printer + material cuts holes with them (project.build activates the profile).
   With no profile the catalog's textbook sizes are used, exactly as before.
"""
from __future__ import annotations

import contextlib
import contextvars
import datetime as _dt
import json
import re
from pathlib import Path

from . import catalog

ROOT = Path(__file__).resolve().parent.parent
PRINTERS = ROOT / "catalog" / "printers"          # tests point this at a tmp dir
DEFAULT_PRINTER = "Bambu Lab A2L"

SIZES = ("M2", "M2.5", "M3")
BEARINGS = ("608", "623")
PIN_CLEARANCES = (0.2, 0.3, 0.4)
COUPON_SERVO = "servos.MG90S"
# one feedback step, on diameter (mm). Holes: one 0.1 mm step is about one nozzle-line compensation step; pilots and
# bearings are interference fits, so they move in half steps; the servo window is a loose clearance.
STEP = {"hole": 0.1, "tap": 0.05, "insert": 0.1, "bearing": 0.05, "servo_window": 0.2, "pin_press": 0.02}
MAX_OFFSET = 0.6   # mm on diameter; beyond this the printer needs calibrating (flow, XY comp), not the CAD
VERDICT = {"tight": 1, "ok": 0, "loose": -1}

_ACTIVE: contextvars.ContextVar = contextvars.ContextVar("kerf_print_profile", default=None)


def slug(printer: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", printer.lower()).strip("_")


def mat_key(material: str | None) -> str:
    return (material or "PLA").upper().replace("_", "-")


def profile_path(printer: str) -> Path:
    return PRINTERS / f"{slug(printer)}.json"


def load_profile(printer: str) -> dict:
    f = profile_path(printer)
    if not f.exists():
        return {"printer": printer, "materials": {}}
    return json.loads(f.read_text(encoding="utf-8"))


def feature_keys() -> list[str]:
    return ([f"{k}_{s}" for k in ("hole", "tap", "insert") for s in SIZES] + [f"bearing_{b}" for b in BEARINGS]
            + [f"pin_{c:g}" for c in PIN_CLEARANCES] + ["pin_press", "servo_window"])


# ---------------------------------------------------------------- applying offsets (called from iface)
@contextlib.contextmanager
def active(printer: str | None, material: str | None):
    """Use this printer + material's offsets for every iface call inside the block."""
    tok = _ACTIVE.set((printer or DEFAULT_PRINTER, mat_key(material)))
    try:
        yield
    finally:
        _ACTIVE.reset(tok)


def _offsets() -> dict:
    a = _ACTIVE.get()
    if a is None:
        return {}
    return load_profile(a[0]).get("materials", {}).get(a[1], {}).get("offsets", {})


def _num(size: str) -> float:
    return float(str(size).lstrip("M"))


def offset(kind: str, size: str | None = None) -> float:
    """Diameter offset (mm) for a hole kind ('hole', 'tap', 'insert', 'bearing', 'servo_window') under the active
    profile. A size that was not calibrated takes the nearest calibrated size of the same kind (M4 clearance -> M3's;
    a 6802 bearing -> the calibrated bearing with the closest outer diameter); 0 with no profile or no data."""
    off = _offsets()
    if not off:
        return 0.0
    if size is None:
        return float(off.get(kind, 0.0))
    key = f"{kind}_{size}"
    if key in off:
        return float(off[key])
    same = {k[len(kind) + 1:]: v for k, v in off.items() if k.startswith(kind + "_")}
    if not same:
        return 0.0
    if kind == "bearing":
        def D(name):
            return catalog.num(catalog.get(f"bearings.{name}"), "outer_d", "D", "od")
        target = D(size)
        return float(same[min(same, key=lambda n: abs(D(n) - target))])
    target = _num(size)
    return float(same[min(same, key=lambda s: abs(_num(s) - target))])


def pin_allowance(fit: str, default: float) -> float:
    """Diameter allowance for a steel pin hole: the calibrated value for 'free' / 'press' if measured, else default."""
    v = _offsets().get(f"pin_{fit}_allowance")
    return float(v) if v is not None else default


# ---------------------------------------------------------------- feedback
def feedback(material: str, reports: dict, printer: str = DEFAULT_PRINTER, date: str | None = None) -> dict:
    """Apply Spencer's fit report to the stored profile and save it. reports: {key: 'tight'|'ok'|'loose'|'+0.1'}.
    Returns {key: (old, new)} for every value that changed. Raises ValueError for unknown keys or values."""
    keys = feature_keys()
    bad = [k for k in reports if k not in keys]
    if bad:
        raise ValueError(f"unknown coupon feature(s) {bad}; report one of: {', '.join(keys)}")
    prof = load_profile(printer)
    m = prof.setdefault("materials", {}).setdefault(mat_key(material), {"offsets": {}, "history": []})
    off = m.setdefault("offsets", {})
    changed = {}
    pins = {}
    for k, v in reports.items():
        v = str(v).strip().lower()
        if k.startswith("pin_") and k != "pin_press":
            if v not in VERDICT:
                raise ValueError(f"{k}: report tight, ok or loose for a slip-fit pin hole")
            pins[float(k[4:])] = v
            continue
        kind = "servo_window" if k == "servo_window" else ("pin_press" if k == "pin_press" else k.split("_")[0])
        if v in VERDICT:
            delta = VERDICT[v] * STEP[kind]
        else:
            try:
                delta = float(v)
            except ValueError:
                raise ValueError(f"{k}={v}: use tight, ok, loose or a signed mm value like +0.1") from None
        if k == "pin_press":
            store = "pin_press_allowance"
            old = float(off.get(store, catalog.num(catalog.get("fdm_fits.pin"), "press_allowance_d")))
        else:
            store, old = k, float(off.get(k, 0.0))
        new = round(old + delta, 3)
        if k != "pin_press" and abs(new) > MAX_OFFSET:
            raise ValueError(f"{k}: offset {new:+.2f} mm is beyond +/-{MAX_OFFSET} mm; check the printer's flow and "
                             "XY hole compensation in Bambu Studio first, then reprint the coupon")
        if new != old:
            off[store] = new
            changed[store] = (old, new)
    if pins:
        ok = sorted(c for c, v in pins.items() if v == "ok")
        if ok:
            new = ok[0]
        elif all(v == "tight" for v in pins.values()):
            new = max(pins) + 0.1                  # even the loosest was tight: open up past it
        else:
            new = max(0.1, min(pins) - 0.1)        # every tested clearance wobbles
        old = off.get("pin_free_allowance")
        if old != new:
            off["pin_free_allowance"] = round(new, 3)
            changed["pin_free_allowance"] = (old, round(new, 3))
    m.setdefault("history", []).append({"date": date or _dt.date.today().isoformat(), "reported": dict(reports),
                                        "changed": {k: list(v) for k, v in changed.items()}})
    prof["printer"] = printer
    prof["note"] = ("Fit offsets measured on this printer with `kerf calibrate` + `kerf feedback`; diameters in mm, "
                    "added to the catalog's hole sizes by kerf/iface.py (pin_*_allowance replace the catalog's).")
    PRINTERS.mkdir(parents=True, exist_ok=True)
    profile_path(printer).write_text(json.dumps(prof, indent=2) + "\n", encoding="utf-8")
    return changed


def parse_reports(items: list[str]) -> dict:
    out = {}
    for s in items:
        if "=" not in s:
            raise ValueError(f"'{s}': write feature=verdict, e.g. hole_M3=tight")
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip()
    return out


# ---------------------------------------------------------------- the coupon
PLATE = (96.0, 62.0, 8.0)   # x, y, thickness (mm): 8 mm takes the M3 heat-set hole (6.7 + 0.8 floor) and a 608 pocket


def coupon(material: str = "PETG", printer: str = DEFAULT_PRINTER):
    """The calibration coupon as one solid (printed flat, top face up) and the card rows [(key, where, what)]."""
    from build123d import Align, Box, Cylinder, Location, Pos
    from . import features as F, iface
    from .ctx import Ctx

    W, H, T = PLATE
    rows = []
    with active(printer, material):
        ctx = Ctx("coupon", {}, {"spec": {"material": material}, "printer": printer})
        body = Box(W, H, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
        xs = dict(zip(SIZES, (-37.0, -27.0, -17.0)))
        ys = {"hole": 19.0, "tap": 8.0, "insert": -3.0}
        for kind, y in ys.items():
            ik = {"hole": "clearance", "tap": "tap", "insert": "heatset"}[kind]
            for s, x in xs.items():
                body -= iface.bolt_pattern(ctx, f"cal_{kind}_{s}", s, [(x, y)], Location((0, 0, T)), kind=ik, depth=T)
                rows.append((f"{kind}_{s}", f"row {kind.upper()[0]}, column {s}",
                             {"hole": f"{s} screw slides through", "tap": f"{s} screw self-taps in firmly, no cracking",
                              "insert": f"{s} heat-set insert presses in flush and does not spin"}[kind]))
            body -= F.label(kind.upper()[0], 5, loc=Location((-43.5, y, T)), emboss=False)
        for s, x in xs.items():
            body -= F.label(s.lstrip("M"), 5, loc=Location((x - 2.5, 24.0, T)), emboss=False)
        for name, (x, y) in zip(BEARINGS, ((4.0, 12.0), (26.0, 19.0))):
            B = catalog.num(catalog.get(f"bearings.{name}"), "width", "B")
            body -= iface.bearing_seat(ctx, f"bearings.{name}", Location((x, y, T)), fit="press", depth=B,
                                       through=T - B)
            rows.append((f"bearing_{name}", f"pocket '{name}'", f"{name} bearing presses in by thumb/vise and stays"))
        body -= F.label("608", 5, loc=Location((-1.5, -6.0, T)), emboss=False)
        body -= F.label("623", 5, loc=Location((39.0, 19.0, T)), emboss=False)
        pin_d = catalog.num(catalog.get("motion.pin_3mm"), "d")
        press = pin_allowance("press", catalog.num(catalog.get("fdm_fits.pin"), "press_allowance_d"))
        for k, (c, x) in enumerate(zip(PIN_CLEARANCES + (press,), (20.0, 27.0, 34.0, 41.0))):
            body -= Pos(x, 3.0, -1) * Cylinder((pin_d + c) / 2, T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
            key = f"pin_{c:g}" if k < 3 else "pin_press"
            rows.append((key, f"dowel hole {k + 1} of 4 from the left (x {x:g})",
                         "3 mm steel dowel turns freely without wobble" if k < 3 else "3 mm dowel presses in and holds"))
        body -= F.label("234P", 5, loc=Location((22.0, -6.0, T)), emboss=False)
        body -= iface.servo_mount(ctx, COUPON_SERVO, Location((-22.0, -19.0, T)), group="cal_servo", plate_t=T,
                                  kind="tap")
        rows.append(("servo_window", "servo window (bottom left)",
                     "MG90S drops in without forcing and does not rattle; tab screws line up"))
        body -= F.label(mat_key(material)[:6], 5, loc=Location((6.0, -24.0, T)), emboss=False)
    return body, rows


def write_coupon(material: str = "PETG", printer: str = DEFAULT_PRINTER, outdir: Path | None = None) -> Path:
    from build123d import Mesher, export_stl

    body, rows = coupon(material, printer)
    out = outdir or ROOT / "out" / "calibration" / f"{slug(printer)}_{mat_key(material).lower()}"
    out.mkdir(parents=True, exist_ok=True)
    export_stl(body, str(out / "coupon.stl"), tolerance=0.01, angular_tolerance=0.1)
    m = Mesher()
    m.add_shape(body, linear_deflection=0.01, angular_deflection=0.1, part_number="coupon")
    m.write(str(out / "coupon.3mf"))
    with active(printer, material):
        cur = _offsets()
    L = [f"# Fit coupon — {printer}, {mat_key(material)}", "",
         f"Print `coupon.3mf` flat (as exported), {mat_key(material)}, your normal profile, no supports. Then try each "
         "feature and report in one command, for example:", "",
         f"    .venv/bin/kerf feedback {mat_key(material)} hole_M3=tight insert_M3=ok bearing_608=loose pin_0.3=ok", "",
         "tight = too small / will not go in nicely; loose = too big / wobbles, strips or falls out; ok = good; or a "
         "signed mm number (+0.1 makes that hole 0.1 mm bigger). Slip pins: report each of pin_0.2, pin_0.3, pin_0.4.",
         "", f"Offsets already in this coupon: {json.dumps(cur) if cur else 'none (catalog sizes)'}", "",
         "| report as | where on the coupon | it fits when |", "|---|---|---|"]
    L += [f"| `{k}` | {w} | {t} |" for k, w, t in rows]
    (out / "CARD.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return out
