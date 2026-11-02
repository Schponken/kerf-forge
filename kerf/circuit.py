"""Electronics as a real circuit: project.yaml `wiring:` turned into a pin-level KiCad netlist, checked by SKiDL's ERC,
and drawn as a KiCad schematic (out/kicad/<project>.kicad_sch) plus out/schematic.svg / .pdf next to wiring.svg.

- Pins come from catalog/pins.json (keyed by catalog path or prefix): a KiCad symbol from the kicad-symbols library
  (pin numbers, names and electrical types; `types` overrides where KiCad's generic symbol is all-passive) or a small
  sourced pin table for a module KiCad has no symbol for. Every symbol used is copied into one project library
  (out/kicad/kerf_symbols.kicad_sym), so the schematic opens in KiCad without the system libraries.
- A run's conductors land on ports: a power run uses the `from` item's output port (`psu.dc` -> port 'dc', default '')
  and the `to` item's input port, + first; a signal run uses port 'signal' (instance = its `pin:`, e.g. ch1); `pins:
  {from: [...], to: [...]}` names the pins outright. Named instances (ESC outputs M1..M4, the supply's two terminal
  pairs) are taken in order when the run gives no `pin:`.
- ERC (SKiDL, KiCad's pin-type matrix): two outputs on one net, a power input on a net nothing supplies, and every pin
  left unwired that the pin table does not list as optional (those get a no-connect flag). Plus two Kerf checks: the
  conductors a run declares match the pins it lands on, and no terminal takes more wires than it holds.
- Coverage is reported honestly: when any wired item has no pin table the ERC is not run and a warning lists them.
- Not modelled: in-line fuses (a fuse is a passive series part; the run's + conductor is treated as one net through it).
"""
from __future__ import annotations

import fnmatch
import json
import logging
import math
import os
import re
from pathlib import Path

from . import catalog

ROOT = Path(__file__).resolve().parent.parent
PINS = ROOT / "catalog" / "pins.json"
KICAD_SYMBOLS_TAG = "7.0.11"          # apt kicad-symbols on Ubuntu 24.04; tools/fetch_kicad_symbols.py fetches the same tag
CACHE_SYMBOLS = Path.home() / ".cache" / "kerf" / f"kicad-symbols-{KICAD_SYMBOLS_TAG}"
SCHEMATIC_SEEDS = (1, 2, 3)
TYPES = {"input", "output", "bidirectional", "tristate", "passive", "power_in", "power_out", "open_collector", "open_emitter",
         "unspecified", "no_connect", "free"}


class CircuitError(ValueError):
    pass


# --- pin tables + KiCad symbols ---------------------------------------------------------------------------------------
def load_pins(path: Path | None = None) -> dict:
    return {k: v for k, v in json.loads((path or PINS).read_text(encoding="utf-8")).items() if not k.startswith("_")}


def table_for(cat_path: str, tables: dict | None = None):
    """(key, entry) of the longest pins.json key that is the catalog path or a dotted prefix of it; (None, None)."""
    tables = load_pins() if tables is None else tables
    best = None
    for k in tables:
        if cat_path == k or cat_path.startswith(k + "."):
            if best is None or len(k) > len(best):
                best = k
    return (best, tables[best]) if best else (None, None)


def symbol_dir() -> Path | None:
    for d in (os.environ.get("KICAD_SYMBOL_DIR"), os.environ.get("KICAD7_SYMBOL_DIR"), "/usr/share/kicad/symbols",
              "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols", str(CACHE_SYMBOLS)):
        if d and Path(d).is_dir() and any(Path(d).glob("*.kicad_sym")):
            return Path(d)
    return None


def _block(text: str, start: int) -> str:
    """The balanced s-expression starting at text[start] == '('."""
    depth, i, instr = 0, start, False
    while i < len(text):
        c = text[i]
        if instr:
            if c == "\\":
                i += 1
            elif c == '"':
                instr = False
        elif c == '"':
            instr = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    raise CircuitError("unbalanced KiCad symbol file")


_LIB_CACHE: dict = {}


def kicad_symbol(lib: str, name: str, sdir: Path | None = None) -> list[str]:
    """Symbol text blocks for Lib:Name from the KiCad library (parent first when it `extends` another)."""
    sdir = sdir or symbol_dir()
    if sdir is None:
        raise CircuitError("KiCad symbol libraries not found (apt install kicad-symbols, or run ./setup.sh which fetches "
                           f"kicad-symbols {KICAD_SYMBOLS_TAG} into {CACHE_SYMBOLS})")
    f = sdir / f"{lib}.kicad_sym"
    if not f.exists():
        raise CircuitError(f"KiCad symbol library {lib} not found in {sdir}")
    text = _LIB_CACHE.get(f) or _LIB_CACHE.setdefault(f, f.read_text(encoding="utf-8"))
    m = re.search(r'\n\s*\(symbol "' + re.escape(name) + r'"[\s(]', text)
    if not m:
        raise CircuitError(f"KiCad symbol {lib}:{name} not found in {f}")
    blk = _block(text, text.index("(", m.start()))
    ext = re.match(r'\(symbol "[^"]*"\s*\(extends "([^"]*)"\)', blk)
    return (kicad_symbol(lib, ext.group(1), sdir) if ext else []) + [blk]


_PIN = re.compile(r'\(pin (\w+) \w+\s.*?\(name "((?:[^"\\]|\\.)*)".*?\(number "((?:[^"\\]|\\.)*)"', re.S)


def symbol_pins(blocks: list[str]) -> list[tuple[str, str, str]]:
    """(number, name, type) of a symbol's pins (an extending symbol has its parent's)."""
    out = []
    for b in blocks:
        out = [(num, nm, t) for t, nm, num in _PIN.findall(b)] or out
    return out


def _esc(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def own_symbol(name: str, pins: list, ref: str = "U") -> str:
    """A KiCad 7 symbol for a pin table: a box, inputs / power-in on the left, the rest on the right, 2.54 mm pitch."""
    left = [p for p in pins if p[2] in ("input", "power_in")]
    right = [p for p in pins if p not in left]
    n = max(len(left), len(right), 1)
    longest = max([len(p[1]) for p in pins] + [4])
    w = max(10.16, 2.54 * math.ceil((2 * longest * 0.8 + 2.54) / 2.54))     # room for a left and a right pin name
    h = n * 2.54 + 2.54
    top = (n - 1) * 2.54 / 2
    eff = '(effects (font (size 1.27 1.27)))'
    L = [f'  (symbol "{_esc(name)}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)',
         f'    (property "Reference" "{ref}" (at 0 {h / 2 + 1.27:.2f} 0) {eff})',
         f'    (property "Value" "{_esc(name)}" (at 0 {-h / 2 - 1.27:.2f} 0) {eff})',
         f'    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
         f'    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
         f'    (symbol "{_esc(name)}_0_1" (rectangle (start {-w / 2:.2f} {h / 2:.2f}) (end {w / 2:.2f} {-h / 2:.2f}) '
         f'(stroke (width 0.254) (type default)) (fill (type background))))',
         f'    (symbol "{_esc(name)}_1_1"']
    for side, ps in ((-1, left), (1, right)):
        for i, (num, nm, t) in enumerate(ps):
            x, y = side * (w / 2 + 2.54), top - i * 2.54
            L.append(f'      (pin {t} line (at {x:.2f} {y:.2f} {0 if side < 0 else 180}) (length 2.54) '
                     f'(name "{_esc(nm)}" {eff}) (number "{_esc(num)}" {eff}))')
    L += ["    )", "  )"]
    return "\n".join(L)


# --- the pin-level model (pure Python; SKiDL only does ERC + output) -------------------------------------------------
def _short(name: str) -> str:
    """A part's value text on the schematic: its catalog name up to the first comma / bracket, at most 40 chars."""
    s = re.split(r"[,(]", str(name))[0].strip()
    return s if len(s) <= 40 else s[:39].rstrip() + "~"


def _ref(s):
    item, _, port = str(s).partition(".")
    return item, port


def _cat_path(proj, iid) -> str:
    return str((proj.items[iid].spec if iid in proj.items else {}).get("catalog") or "")


def _runs(proj) -> list[dict]:
    """The project's wiring runs plus the mains jumpers (electrical.mains: inlet L/N/PE -> supply AC/L, AC/N, FG)."""
    runs = [dict(w, id=w.get("id", f"w{i + 1}")) for i, w in enumerate(proj.data.get("wiring") or [])]
    el = proj.data.get("electrical") or {}
    mains = el.get("mains") or {}
    sup = el.get("supply")
    if mains.get("inlet") and sup:
        runs.append({"id": "mains", "from": mains["inlet"], "to": f"{sup}.ac", "kind": "power", "conductors": 3,
                     "v": mains.get("input_v"), "_mains": True})
    return runs


def _port_pins(entry, side, port, inst, used, item, rid):
    ports = (entry.get("ports") or {}).get("out" if side == "from" else "in") or {}
    if port not in ports:
        raise CircuitError(f"run '{rid}': {item} has no {'output' if side == 'from' else 'input'} port "
                           f"'{port or '(default)'}' in catalog/pins.json (has {sorted(ports) or 'none'}); "
                           f"name the pins with `pins: {{{side}: [...]}}`")
    p = ports[port]
    if isinstance(p, dict):
        if inst:
            if inst not in p:
                raise CircuitError(f"run '{rid}': {item} port '{port}' has no '{inst}' (has {sorted(p)})")
            key = inst
        else:
            free = [k for k in p if (item, port, k) not in used]
            if not free:
                raise CircuitError(f"run '{rid}': every {item} '{port}' output ({', '.join(p)}) is already wired")
            key = free[0]
        if (item, port, key) in used:
            raise CircuitError(f"run '{rid}': {item} {port} {key} is already wired by run '{used[(item, port, key)]}'")
        used[(item, port, key)] = rid
        return list(p[key])
    return list(p)


def model(proj, tables: dict | None = None, sdir: Path | None = None) -> dict:
    """{parts, nets, nc, problems, warnings, coverage, missing}. `missing` non-empty = some wired item has no pin table
    (the ERC is then not run). Raises nothing for project data problems: they are returned as problems."""
    tables = load_pins() if tables is None else tables
    runs = _runs(proj)
    ids = []
    for w in runs:
        for k in ("from", "to"):
            i = _ref(w[k])[0]
            if i not in ids:
                ids.append(i)
    parts, missing, problems, warnings = {}, [], [], []
    for iid in ids:
        if iid not in proj.items:
            problems.append(f"circuit: wiring names unknown item '{iid}'")
            continue
        cp = _cat_path(proj, iid)
        key, e = table_for(cp, tables)
        if e is None:
            missing.append(f"{iid} ({cp or 'no catalog entry'})")
            continue
        if e.get("symbol"):
            lib, _, nm = e["symbol"].partition(":")
            blocks = kicad_symbol(lib, nm, sdir)
            pins = symbol_pins(blocks)
            src = f"KiCad {e['symbol']}"
        else:
            blocks, lib, nm = None, "kerf", key.replace(".", "_")
            pins = [tuple(str(x) for x in p) for p in e["pins"]]
            src = "pin table"
        over = e.get("types") or {}
        pins = [(n, nm_, over.get(nm_, t)) for n, nm_, t in pins]
        bad = [t for _, _, t in pins if t not in TYPES]
        if bad:
            raise CircuitError(f"catalog/pins.json {key}: unknown pin type(s) {bad}")
        parts[iid] = {"key": key, "entry": e, "lib": lib, "symbol": nm, "blocks": blocks, "pins": pins, "source": src,
                      "catalog": cp, "value": _short(catalog.get(cp).get("model") or catalog.get(cp).get("name") or cp) if cp else iid}
    cov = {"items": len(ids), "with_pins": len(parts), "kicad_symbol": sorted(i for i, p in parts.items() if p["blocks"]),
           "pin_table": sorted(i for i, p in parts.items() if not p["blocks"]), "missing": missing}
    if missing:
        return {"parts": parts, "nets": {}, "nc": [], "problems": problems, "warnings": warnings, "coverage": cov,
                "missing": missing, "runs": runs}
    # connections: union-find over (item, pin number)
    parent: dict = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        parent[find(a)] = find(b)

    def nums(iid, name, rid):
        hit = [n for n, nm, _ in parts[iid]["pins"] if nm == name]
        if not hit:
            raise CircuitError(f"run '{rid}': {iid} has no pin '{name}' (pins: {', '.join(nm for _, nm, _ in parts[iid]['pins'])})")
        return hit

    used, landings, label = {}, {}, {}
    for w in runs:
        rid = w["id"]
        (fi, fp), (ti, tp) = _ref(w["from"]), _ref(w["to"])
        kind = w.get("kind", "power")
        try:
            explicit = w.get("pins") or {}
            if explicit.get("from") is not None:
                fpins = [str(x) for x in explicit["from"]]
            else:
                fpins = _port_pins(parts[fi]["entry"], "from", fp or ("" if kind == "power" else "signal"),
                                   w.get("pin") if kind == "signal" or fp else None, used, fi, rid)
            if explicit.get("to") is not None:
                tpins = [str(x) for x in explicit["to"]]
            else:
                tpins = _port_pins(parts[ti]["entry"], "to", tp or ("" if kind == "power" else "signal"), None, used, ti, rid)
            if len(fpins) != len(tpins):
                raise CircuitError(f"run '{rid}': {len(fpins)} pins at {fi} ({', '.join(fpins)}) but {len(tpins)} at {ti} "
                                   f"({', '.join(tpins)})")
            n = int(w.get("conductors") or (2 if kind == "power" else 1))
            if len(fpins) != n:
                raise CircuitError(f"run '{rid}' declares {n} conductor(s) but lands on {len(fpins)} pins "
                                   f"({fi} {', '.join(fpins)} -> {ti} {', '.join(tpins)}); set `conductors: {len(fpins)}`")
            for k, (a, b) in enumerate(zip(fpins, tpins)):
                na, nb = nums(fi, a, rid), nums(ti, b, rid)
                for x in na[1:]:
                    union((fi, x), (fi, na[0]))
                for x in nb[1:]:
                    union((ti, x), (ti, nb[0]))
                union((fi, na[0]), (ti, nb[0]))
                for it, nm in ((fi, a), (ti, b)):
                    landings[(it, nm)] = landings.get((it, nm), 0) + 1
                label.setdefault((fi, na[0]), (rid, k, b if kind == "signal" and n > 1 else None))
        except CircuitError as e:
            problems.append(f"circuit: {e}")
    for iid, p in parts.items():                       # pins joined inside the part (a supply's twin terminals)
        for grp in p["entry"].get("tied") or []:
            ns = [n for g in grp for n in nums(iid, g, "tied")]
            for x in ns[1:]:
                union((iid, x), (iid, ns[0]))
    for (it, nm), cnt in sorted(landings.items()):
        mc = parts[it]["entry"].get("max_conductors") or {}
        lim = mc.get(nm, mc.get("*"))
        if lim is not None and cnt > int(lim):
            problems.append(f"circuit: {it} terminal {nm} takes {lim} wire(s) but {cnt} land on it")
    groups: dict = {}
    for node in list(parent):
        groups.setdefault(find(node), []).append(node)
    nets, taken = {}, set()
    for root, nodes in sorted(groups.items(), key=lambda kv: min(str(x) for x in kv[1])):
        nodes = sorted(nodes)
        pinfo = {(i, n): (nm, t) for i in {x[0] for x in nodes} for n, nm, t in parts[i]["pins"]}
        if any(pinfo[x][0] in ("GND", "-", "-V(4)", "BAT-") for x in nodes):
            base = "GND"
        else:
            src = [x for x in nodes if pinfo[x][1] == "power_out"]
            if src:
                base = f"{src[0][0]}_{pinfo[src[0]][0]}"
            else:
                lab = next((label[x] for x in nodes if x in label), None)
                base = (f"{lab[0]}_{lab[2]}" if lab[2] else f"{lab[0]}_{lab[1] + 1}" if lab and lab[1] else lab[0]) if lab else "N"
        base = re.sub(r"[^A-Za-z0-9_+\-]", "", base.replace("(", "").replace(")", "")) or "N"
        name, k = base, 2
        while name in taken:
            name, k = f"{base}_{k}", k + 1
        taken.add(name)
        nets[name] = nodes
    connected = {x for ns in nets.values() for x in ns}
    nc = []
    for iid, p in parts.items():
        opt = (p["entry"].get("optional") or {}).get("pins") or []
        for n, nm, _ in p["pins"]:
            if (iid, n) not in connected and any(fnmatch.fnmatchcase(nm, g) for g in opt):
                nc.append((iid, n))
    return {"parts": parts, "nets": nets, "nc": nc, "problems": problems, "warnings": warnings, "coverage": cov,
            "missing": [], "runs": runs}


# --- SKiDL: ERC, netlist, schematic -----------------------------------------------------------------------------------
def library_text(m: dict) -> str:
    """One KiCad 7 symbol library with every symbol the circuit uses (KiCad's own, copied verbatim, and pin-table ones)."""
    seen, out = set(), []
    for iid, p in m["parts"].items():
        if p["symbol"] in seen:
            continue
        seen.add(p["symbol"])
        if p["blocks"]:
            for b in p["blocks"]:
                nm = re.match(r'\(symbol "([^"]*)"', b).group(1)
                if nm not in seen or nm == p["symbol"]:
                    seen.add(nm)
                    out.append("  " + b)
        else:
            out.append(own_symbol(p["symbol"], p["pins"]))
    return "(kicad_symbol_lib (version 20220914) (generator kerf)\n" + "\n".join(out) + "\n)\n"


def _skidl():
    os.environ.setdefault("KICAD7_SYMBOL_DIR", str(symbol_dir() or ""))
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from skidl.logger import erc_logger, rt_logger, stop_log_file_output
        stop_log_file_output(True)
        import skidl
    for lg in (rt_logger, erc_logger):          # results are collected by erc(), not printed to the console
        for h in lg.handlers:
            if type(h) is logging.StreamHandler:
                h.setLevel(logging.CRITICAL)
    return skidl


class _Grab(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.recs = []

    def emit(self, r):
        self.recs.append((r.levelname, r.getMessage()))


def build_circuit(m: dict, libfile: Path):
    """SKiDL Circuit for the model (parts from libfile, nets, no-connect flags)."""
    sk = _skidl()
    from skidl import KICAD7, Circuit, Net, Part, Pin
    sk.set_default_tool(KICAD7)
    c = Circuit()
    c.no_files = True
    ptype = {"input": Pin.types.INPUT, "output": Pin.types.OUTPUT, "bidirectional": Pin.types.BIDIR,
             "tristate": Pin.types.TRISTATE, "passive": Pin.types.PASSIVE, "power_in": Pin.types.PWRIN,
             "power_out": Pin.types.PWROUT, "open_collector": Pin.types.OPENCOLL, "open_emitter": Pin.types.OPENEMIT,
             "unspecified": Pin.types.UNSPEC, "no_connect": Pin.types.NOCONNECT, "free": Pin.types.FREE}
    parts = {}
    for iid, p in m["parts"].items():
        part = Part(str(libfile), p["symbol"], ref=iid, value=p["value"][:60], footprint="kerf:wired_module", circuit=c)
        for pin in part.pins:
            t = next((t for n, _, t in p["pins"] if n == str(pin.num)), None)
            if t:
                pin.func = ptype[t]
        parts[iid] = part
    for name, nodes in m["nets"].items():
        n = Net(name, circuit=c)
        for iid, num in nodes:
            n += _pin(parts[iid], num)
    for iid, num in m["nc"]:
        pin = _pin(parts[iid], num)
        pin += c.NC
    return c


def _pin(part, num):
    return next(p for p in part.pins if str(p.num) == str(num))


_CONFLICT = re.compile(r"Pin conflict on net (\S+), (.*) <==> (.*) \((.*)\)")


def plain(level: str, msg: str) -> tuple[str, str]:
    """('problem'|'warning', plain-language text) for one SKiDL ERC message."""
    m = _CONFLICT.match(msg)
    if m:
        net, a, b, why = m.groups()
        hint = " - two outputs fighting on one wire (a UART needs TX to RX, crossed)" if "OUTPUT connected to OUTPUT" in why else ""
        return "problem", f"circuit ERC: {why.lower()} on net {net}: {a} and {b}{hint}"
    if msg.startswith("Unconnected pin"):
        return "problem", f"circuit ERC: {msg.rstrip('.')} is not wired (wire it, or list it as optional with a reason in catalog/pins.json)"
    if msg.startswith("Insufficient drive current"):
        return "problem", f"circuit ERC: {msg.rstrip('.')} - a power input on a net that nothing supplies"
    if msg.startswith("No drivers for net"):
        return "problem", f"circuit ERC: {msg.rstrip('.')} - its inputs are driven by nothing"
    return ("problem" if level == "ERROR" else "warning"), f"circuit ERC: {msg}"


def erc(c) -> list[tuple[str, str]]:
    from skidl.logger import erc_logger
    h = _Grab()
    erc_logger.addHandler(h)
    try:
        c.ERC()
    finally:
        erc_logger.removeHandler(h)
    return [(lv, msg) for lv, msg in h.recs if lv in ("WARNING", "ERROR")]


def check(proj, workdir: Path | None = None) -> dict:
    """The circuit check: model + SKiDL ERC. Returns {ok, ran, problems, warnings, coverage, nets, erc, _circuit, _model}."""
    import tempfile
    try:
        m = model(proj)
    except CircuitError as e:
        return {"ran": False, "problems": [f"circuit: {e}"], "warnings": [], "coverage": {}, "nets": 0, "erc": []}
    res = {"ran": False, "problems": list(m["problems"]), "warnings": list(m["warnings"]), "coverage": m["coverage"],
           "nets": len(m["nets"]), "erc": []}
    if m["missing"]:
        res["warnings"].append("circuit: ERC not run - no pin table in catalog/pins.json for " + ", ".join(m["missing"]))
        return res
    if m["problems"]:
        return res
    try:
        sk = _skidl()   # noqa: F841 - import check
    except ImportError as e:
        res["problems"].append(f"circuit: SKiDL is not installed ({e}); run ./setup.sh")
        return res
    wd = Path(workdir or tempfile.mkdtemp(prefix="kerf_circuit_"))
    wd.mkdir(parents=True, exist_ok=True)
    lib = wd / "kerf_symbols.kicad_sym"
    lib.write_text(library_text(m), encoding="utf-8")
    c = build_circuit(m, lib)
    msgs = erc(c)
    res["ran"] = True
    res["erc"] = [f"{lv}: {msg}" for lv, msg in msgs]
    for lv, msg in msgs:
        kind, text = plain(lv, msg)
        res["problems" if kind == "problem" else "warnings"].append(text)
    res["_circuit"], res["_model"], res["_lib"] = c, m, lib
    return res


def svg_to_pdf(svg: Path, pdf: Path) -> str | None:
    """Print an SVG to PDF with the headless Chromium the renders use (tools/render). Returns an error text or None."""
    import subprocess
    script = ROOT / "tools" / "render" / "svg2pdf.mjs"
    r = subprocess.run(["node", str(script), str(svg), str(pdf)], cwd=script.parent, capture_output=True, text=True, timeout=120)
    return None if r.returncode == 0 and pdf.exists() else (r.stderr or r.stdout)[-400:]


def write(proj, out: Path, res: dict) -> dict:
    """out/kicad/: <project>.kicad_sch, <project>.net, kerf_symbols.kicad_sym, erc.txt; out/schematic.svg + .pdf."""
    files, errs = [], []
    if not res.get("ran"):
        return {"files": files, "errors": errs}
    kdir = out / "kicad"
    kdir.mkdir(parents=True, exist_ok=True)
    c, m = res["_circuit"], res["_model"]
    (kdir / "kerf_symbols.kicad_sym").write_text(res["_lib"].read_text(encoding="utf-8"), encoding="utf-8")
    (kdir / f"{proj.dir.name}.net").write_text(c.generate_netlist(), encoding="utf-8")
    cov = m["coverage"]
    (kdir / "erc.txt").write_text(encoding="utf-8", data=
        f"SKiDL ERC for {proj.dir.name}: {len(m['parts'])} parts, {len(m['nets'])} nets, {len(m['nc'])} no-connect flags\n"
        f"KiCad symbols: {', '.join(cov['kicad_symbol']) or '-'}\npin tables: {', '.join(cov['pin_table']) or '-'}\n\n"
        + ("\n".join(res["erc"]) or "no ERC errors or warnings") + "\n")
    files += [f"kicad/{proj.dir.name}.net", "kicad/kerf_symbols.kicad_sym", "kicad/erc.txt"]
    import shutil
    import tempfile
    import random
    name = proj.dir.name
    title = f"{name} wiring (Kerf)"
    for fmt in ("sch", "svg"):
        err = None
        for seed in SCHEMATIC_SEEDS:      # schematizer places parts with `random`: a fixed seed = the same drawing every build
            tmp = Path(tempfile.mkdtemp(prefix=f"kerf_{fmt}_"))
            state = random.getstate()
            random.seed(seed)
            try:
                if fmt == "sch":           # editable KiCad schematic: exact connectivity as net labels (no routing)
                    c.generate_schematic(filepath=str(tmp), top_name=name, title=title, mode="labels")
                    got = sorted(tmp.rglob("*.kicad_sch"))
                    dst, rel = kdir / f"{name}.kicad_sch", f"kicad/{name}.kicad_sch"
                else:
                    c.generate_svg(filepath=str(tmp), top_name=name, title=title)
                    got = sorted(tmp.rglob("*.svg"))
                    dst, rel = out / "schematic.svg", "schematic.svg"
                if got:
                    shutil.copy(got[0], dst)
                    files.append(rel)
                    err = None
                    break
                err = f"schematic ({fmt}): SKiDL wrote no file"
            except Exception as e:  # noqa: BLE001 - placement / routing failures are reported, not silent
                err = f"schematic ({fmt}) could not be drawn (seeds {SCHEMATIC_SEEDS}): {type(e).__name__}: {e}"
            finally:
                random.setstate(state)
                shutil.rmtree(tmp, ignore_errors=True)
        if err:
            errs.append(err)
    if (out / "schematic.svg").exists():
        err = svg_to_pdf(out / "schematic.svg", out / "schematic.pdf")
        if err:
            errs.append(f"schematic.pdf could not be printed: {err}")
        else:
            files.append("schematic.pdf")
    return {"files": files, "errors": errs}
