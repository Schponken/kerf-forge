"""Turn an exception raised while building a part into a diagnosis a designer (human or subagent) can act on:
which part, which feature (the line of the part file and the operation that failed) and a concrete fix hint.

    d = diagnose.explain(exc, part_id="arm", part_file=Path(".../parts/arm.py"))
    d.message()  ->  "arm.py line 23 `body = fillet(top, 3)`: fillet r 3 failed on 4 edges.
                      fix: the largest fillet these edges take is 1.24 mm; use <= 1.1"

Hints are computed, not guessed, where the failing call's own arguments allow it (fillet/chamfer: the largest size
OCC accepts on those edges, found with build123d's max_fillet or by bisection; unknown names: the closest existing
param, catalog key or variable). The part-designer subagent and the after-edit hook feed `fix:` straight back.
"""
from __future__ import annotations

import difflib
import math
import re
import traceback
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Diagnosis:
    part: str
    file: str = ""        # part file name
    line: int = 0         # line in the part file where the failing call is made (0 = unknown)
    code: str = ""        # that source line
    feature: str = ""     # operation that failed: "fillet", "chamfer", "sweep", "iface.bolt_pattern", "ctx.p", ...
    error: str = ""       # "<Type>: <message>"
    hint: str = ""        # the concrete fix

    def message(self) -> str:
        where = f"{self.file} line {self.line}" if self.line else (self.file or self.part)
        code = f" `{self.code}`" if self.code else ""
        feat = f" [{self.feature}]" if self.feature else ""
        s = f"{where}{code}{feat}: {self.error}"
        return s + (f"\n    fix: {self.hint}" if self.hint else "")

    def as_dict(self) -> dict:
        return dict(self.__dict__)


# build123d / OCC operations worth naming, innermost first wins
_OPS = ("fillet", "chamfer", "max_fillet", "sweep", "loft", "offset", "extrude", "revolve", "split", "thicken",
        "make_face", "section", "_bool_op", "fuse", "cut", "intersect")


def explain(exc: BaseException, part_id: str, part_file: Path | None = None) -> Diagnosis:
    d = Diagnosis(part=part_id, file=part_file.name if part_file else "", error=f"{type(exc).__name__}: {exc}")
    frames = list(_walk(exc.__traceback__))
    pf = str(part_file.resolve()) if part_file else None
    if isinstance(exc, SyntaxError) and pf and exc.filename and Path(exc.filename).resolve() == Path(pf):
        d.line, d.code = exc.lineno or 0, (exc.text or "").strip()
        d.feature = "syntax"
        d.hint = "fix the Python syntax on that line (unclosed bracket, missing colon or comma)"
        return d
    # the part-file frame closest to the failure = the feature line
    own = [f for f in frames if pf and _same(f.f_code.co_filename, pf)]
    if own:
        fr = own[-1]
        d.line = _lineno(exc.__traceback__, fr)
        d.code = _src(fr.f_code.co_filename, d.line)
    # the named operation: innermost build123d / kerf frame after the part's own frame
    tail = frames[frames.index(own[-1]) + 1:] if own else frames
    for fr in reversed(tail):
        fn, mod = fr.f_code.co_name, fr.f_code.co_filename
        if "build123d" in mod and fn in _OPS:
            d.feature = fn.lstrip("_")
            break
        if "/kerf/" in mod and not mod.endswith(("project.py", "diagnose.py")):
            d.feature = f"{Path(mod).stem}.{fn}"
            break
    d.hint = _hint(exc, d, tail, own[-1] if own else None)
    return d


def _walk(tb):
    while tb is not None:
        yield tb.tb_frame
        tb = tb.tb_next


def _lineno(tb, frame):
    while tb is not None:
        if tb.tb_frame is frame:
            return tb.tb_lineno
        tb = tb.tb_next
    return frame.f_lineno


def _same(a, b):
    try:
        return Path(a).resolve() == Path(b)
    except OSError:
        return False


def _src(path, line):
    try:
        return Path(path).read_text(encoding="utf-8").splitlines()[line - 1].strip()
    except (OSError, IndexError):
        return ""


def _frame(tail, name, module_part="build123d"):
    for fr in reversed(tail):
        if fr.f_code.co_name == name and module_part in fr.f_code.co_filename:
            return fr
    return None


def _round_down(x, step=0.1):
    return math.floor(x / step + 1e-9) * step


def _hint(exc, d: Diagnosis, tail, own) -> str:
    msg = str(exc)
    # ---- fillet / chamfer too big: compute the largest size that works on the same edges
    fr = _frame(tail, "fillet")
    if fr is not None and "self" in fr.f_locals and "radius" in fr.f_locals:
        solid, r, edges = fr.f_locals["self"], fr.f_locals["radius"], list(fr.f_locals.get("edge_list") or [])
        d.feature = "fillet"
        d.error = f"fillet r {r:g} failed on {len(edges)} edge(s)"
        mx = _max_size(lambda s: solid.fillet(s, edges), r)
        if mx is None:
            return ("no fillet radius works on this edge selection (an edge is too short or meets a tangent face); "
                    "select fewer edges, e.g. filter_by/group_by to only the corner you mean, or use "
                    "features.safe_fillet to skip the bad ones")
        use = _round_down(mx * 0.9)
        return f"the largest fillet these {len(edges)} edge(s) take is {mx:.2f} mm (wall or edge too short for r {r:g}); use <= {use:.1f}"
    fr = _frame(tail, "chamfer")
    if fr is not None and "self" in fr.f_locals and "length" in fr.f_locals:
        solid, L, L2 = fr.f_locals["self"], fr.f_locals["length"], fr.f_locals.get("length2")
        edges, face = list(fr.f_locals.get("edge_list") or []), fr.f_locals.get("face")
        d.feature = "chamfer"
        d.error = f"chamfer {L:g} failed on {len(edges)} edge(s)"
        k = (L2 / L) if L2 else None
        mx = _max_size(lambda s: solid.chamfer(s, s * k if k else None, edges, face), L)
        if mx is None:
            return "no chamfer size works on this edge selection; select fewer edges (filter_by/group_by) or use features.safe_fillet(kind='chamfer')"
        return f"the largest chamfer these {len(edges)} edge(s) take is {mx:.2f} mm; use <= {_round_down(mx * 0.9):.1f}"
    # ---- one part file importing another (parts are loaded by path, not as a package)
    if (isinstance(exc, ModuleNotFoundError) and own is not None and exc.name
            and (Path(own.f_code.co_filename).parent / f"{exc.name}.py").exists()):
        d.feature = "import"
        return (f"part files can't import each other ('{exc.name}' is a sibling in parts/). Put values two parts share "
                f"in the layout module (project.yaml `layout: parts/layout.py`, its dict is added to every ctx.p) or "
                f"in params/derived")
    # ---- unknown param / name / catalog key: nearest existing spelling
    if isinstance(exc, AttributeError):
        m = re.search(r"'(?:types\.)?SimpleNamespace' object has no attribute '(\w+)'", msg)
        if m and own is not None:
            p = own.f_locals.get("p") or getattr(own.f_locals.get("ctx"), "p", None)
            names = sorted(vars(p)) if p is not None else []
            d.feature = "ctx.p"
            near = _near(m.group(1), names)
            return (f"'{m.group(1)}' is not a param of this part. "
                    + (f"Did you mean {', '.join(near)}? " if near else
                       (f"Params: {', '.join(names)}. " if len(names) <= 25 else ""))
                    + "Add it under params: (or derived:) in project.yaml, or return it from the layout module")
    if isinstance(exc, NameError) and own is not None:
        m = re.search(r"name '(\w+)' is not defined", msg)
        if m:
            import build123d
            pool = list(own.f_locals) + list(own.f_globals) + dir(build123d)
            near = difflib.get_close_matches(m.group(1), pool, n=3)
            return (f"'{m.group(1)}' is not defined here. " + (f"Did you mean {', '.join(near)}? " if near else "")
                    + "Check the spelling and the imports (`from build123d import *`, `from kerf import iface, features as F`)")
    if type(exc).__name__ == "CatalogError":
        d.feature = d.feature or "catalog.get"
        if "Options here" in msg:
            m = re.search(r"has no '([\w.]+)'. Options here: \[(.*)\]", msg)
            if m:
                opts = re.findall(r"'([^']+)'", m.group(2))
                near = difflib.get_close_matches(m.group(1).split(".")[-1], opts, n=3)
                return ((f"use {', '.join(repr(n) for n in near)}; " if near else "")
                        + "if the part really is missing, research it and add it to catalog/hardware.json with a source URL first")
        return "use a key that exists in that catalog entry (the message lists them)"
    # ---- kerf feature helpers state their own limit; point at it
    m = re.search(r"([\d.]+) mm is below the ([\d.]+) mm", msg)
    if m:
        return f"raise that value to >= {m.group(2)} mm (docs/ENGINEERING.md section 5: printable minimum)"
    m = re.search(r"needs a ([\d.]+) mm deep hole plus a 0.8 mm floor; only ([\d.]+) mm", msg)
    if m:
        need = float(m.group(1)) + 0.8
        return f"give the boss/plate >= {need:.1f} mm of material there, or use kind='tap' / a shorter insert"
    m = re.search(r"pilot hole needs ([\d.]+) mm of material; only", msg)
    if m:
        return f"give the boss/plate >= {m.group(1)} mm of material there, or use kind='heatset' with a through boss"
    # ---- geometry kernels without numbers to compute
    if d.feature == "sweep":
        return ("the sweep path is too tight for the profile or kinked: keep every bend radius > the profile radius, "
                "start the profile perpendicular to the path, or add intermediate points so the spline is smooth")
    if d.feature == "offset":
        return ("shell/offset failed: the wall is thicker than the thinnest region or a fillet radius is smaller than "
                "the wall; use a thinner wall, larger fillets, or shell before adding small details")
    if d.feature == "loft":
        return "loft failed: give every section the same number of edges and keep them in order along the loft direction"
    if d.feature in ("bool_op", "fuse", "cut", "intersect") or "BRep_API" in msg or "StdFail" in msg:
        return ("a boolean failed: two faces are exactly coplanar/tangent or a tool is invalid; overlap cutters by "
                "iface.EXTRA (0.05 mm) past the surface and avoid zero-thickness touches")
    if "ctx.finish" in msg:
        return "end build() with `return ctx.finish(body)` (the final solid), not a sketch or None"
    if isinstance(exc, TypeError) and "NoneType" in msg:
        return "a value on that line is None: a helper or boolean returned nothing; check the call above produced a shape"
    if isinstance(exc, ZeroDivisionError):
        return "a param on that line is 0; check params/derived values in project.yaml"
    return "read the error on that line; fix the call or the param it uses, then re-run kerf check --quick"


def _near(name: str, pool) -> list[str]:
    """Closest spellings: difflib matches plus names that are a prefix/abbreviation of `name` or contain it."""
    pool = [n for n in dict.fromkeys(pool) if not n.startswith("__")]
    near = difflib.get_close_matches(name, pool, n=3, cutoff=0.6)
    low = name.lower()
    near += [n for n in pool if n not in near and (low.startswith(n.lower()) or low in n.lower())
             and len(n) >= 1 and n.lower() != low][:3]
    return near[:4]


def _max_size(attempt, start: float):
    """Largest size in (0, start) for which attempt(size) builds a valid shape, by bisection (8 tries, ~0.4 %)."""
    lo, hi = 0.0, float(start)
    ok = None
    for _ in range(9):
        mid = (lo + hi) / 2
        try:
            r = attempt(mid)
            good = r is not None and r.is_valid
        except Exception:  # noqa: BLE001
            good = False
        if good:
            lo, ok = mid, mid
        else:
            hi = mid
    return ok


def short_trace(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__, limit=6))
