"""Wiring outputs from electrical.analyse(): out/WIRING.md, out/wiring.svg, the electrical steps in out/ASSEMBLY.md and the BOM rows for
wire, heat-shrink and every electrical item."""
from __future__ import annotations

import html
import math
from collections import Counter, defaultdict

from . import catalog

HEATSHRINK_MM = 20       # one piece per soldered conductor end


def link(path: str) -> str:
    """First URL of a catalog entry's source (the page the numbers came from; for purchased parts a shop page)."""
    try:
        e = catalog.get(path)
    except Exception:  # noqa: BLE001
        return ""
    src = str(e.get("buy") or e.get("source") or "")
    for tok in src.replace(";", " ").split():
        if tok.startswith("http"):
            return tok
    return ""


def wire_link(gauge) -> str:
    """Buy link for this gauge from catalog/prices.json key 'wire:AWG<g>' (kept out of hardware.json so a shop link
    never changes a project's design fingerprint). Empty when not yet priced."""
    try:
        from .ship import load_prices
        return (load_prices().get(f"wire:AWG{int(gauge)}") or {}).get("buy", "")
    except Exception:  # noqa: BLE001
        return ""


def _conductors(w):
    """Conductors in a run: a power run is a +/- pair unless it says otherwise (e.g. 3 motor phases)."""
    return int(w.get("conductors") or (2 if w["kind"] == "power" else 1))


SOLDERED = {"solder", "header"}      # ends that get a solder joint and a heat-shrink sleeve


def join(term: str, item: str) -> str:
    """The action for one wire end, by how it joins the item (electrical.TERMINALS)."""
    return {"solder": f"solder to {item}",
            "screw": f"crimp a bootlace ferrule on each conductor and clamp it in {item}'s screw terminal",
            "lever": f"strip 11 mm and push into {item}'s lever connector", "plug": f"plug into {item}",
            "header": f"solder to the pin header {item}'s plug pushes onto",
            "crimp": f"crimp a female 0.1 in pin on each conductor, click it into a housing and push it onto {item}'s header pin"}[term]


def ferrule_for(gauge) -> str:
    """Catalog path of the bootlace ferrule for this AWG (electronics.wire_misc.ferrule_*), '' if none is catalogued."""
    for k, e in (catalog.get("electronics.wire_misc") or {}).items():
        if k.startswith("ferrule") and isinstance(e, dict) and int(e.get("wire_awg", -1)) == int(gauge):
            return f"electronics.wire_misc.{k}"
    return ""


def _item_name(path: str) -> str:
    e = catalog.get(path)
    return str(e.get("model") or e.get("name") or path.split(".")[-1])


def _buy(rows, path, qty, note):
    rows.append({"type": "purchased", "item": _item_name(path), "qty": qty, "spec": path, "link": link(path), "note": note})


def bom_rows(model) -> list:
    rows = []
    wire = defaultdict(float)
    ends = Counter()
    ferrules, crimps, housings = Counter(), 0, Counter()
    leads, fuses, holders = Counter(), Counter(), Counter()
    for w in model["wires"]:
        if w.get("supplied"):          # a lead that comes with an item (adapter cord, pack lead): nothing to buy or solder
            continue
        n = _conductors(w)
        terms = w.get("terms") or {"from": "solder", "to": "solder"}
        for side, t in terms.items():
            if t == "screw":
                ferrules[int(w["gauge"])] += n
            if t == "crimp":
                crimps += n
                housings[w.get("crimp_housing") or "electronics.connectors.servo_housing_1x3_pololu1902"] += 1 if n <= 3 else math.ceil(n / 3)
        if w.get("fuse"):
            fuses[w["fuse"]] += 1
            if w.get("fuse_holder"):
                holders[w["fuse_holder"]] += 1
                ends[int(catalog.get(w["fuse_holder"]).get("wire_awg", w["gauge"]))] += 1   # holder lead soldered to the + wire
        if w.get("lead_parts") or w.get("lead_of"):    # ready-made lead: nothing cut from a reel
            for x in w.get("lead_parts") or []:
                if "." in x:
                    leads[x] += 1
            ends[int(w["gauge"])] += n * sum(1 for t in terms.values() if t in SOLDERED)
            continue
        wire[(int(w["gauge"]), w.get("color") or ("red/black" if n == 2 else "any"))] += float(w["length_mm"]) * n
        terms = w.get("terms") or {"from": "solder", "to": "solder"}
        ends[int(w["gauge"])] += n * sum(1 for t in terms.values() if t in SOLDERED)
    for (g, col), mm in sorted(wire.items()):
        rows.append({"type": "wire", "item": f"AWG {g} silicone stranded wire ({col}), metres", "qty": math.ceil(mm / 100) / 10,
                     "spec": f"chassis rating {catalog.get('wire.awg')['ampacity_a'][str(g)]} A", "link": wire_link(g), "price_key": f"wire:AWG{g}",
                     "note": f"{mm:g} mm of cut lengths in WIRING.md, rounded up to 0.1 m"})
    for g, n in sorted((g, n) for g, n in ends.items() if n > 0):
        d = float(catalog.get("wire.awg")["diameter_mm"][str(g)])
        rows.append({"type": "wire", "item": f"heat-shrink for AWG {g} joints, {HEATSHRINK_MM} mm pieces", "qty": n,
                     "spec": f"2:1, expanded ID >= {max(1.5, round(d * 2.2 + 0.5, 1)):g} mm", "link": link("electronics.wire_misc.heatshrink_3mm"), "price_key": "heatshrink",
                     "note": "one per soldered conductor end"})
    for x, q in sorted(leads.items()):
        _buy(rows, x, q, "ready-made lead pieces (WIRING.md: runs with a lead)")
    for x, q in sorted(fuses.items()):
        _buy(rows, x, q + 1, f"{q} fitted + 1 spare")
    for x, q in sorted(holders.items()):
        _buy(rows, x, q, "inline, in the + conductor at the feeding end of each fused run")
    for g, q in sorted(ferrules.items()):
        f = ferrule_for(g)
        if f:
            _buy(rows, f, q, f"AWG {g} conductor ends into screw terminals")
        else:
            rows.append({"type": "hardware", "item": f"bootlace ferrule for AWG {g}", "qty": q, "spec": "", "link": "",
                         "note": "no ferrule for this gauge in the catalog: add one with a source"})
    if crimps:
        _buy(rows, "electronics.connectors.crimp_pin_female_pololu1930", crimps, "female 0.1 in crimp pins, one per crimped conductor")
    for x, q in sorted(housings.items()):
        _buy(rows, x, q, "housings for the crimped pins (unused positions stay empty)")
    m = model.get("mains_side")
    if m:
        if m.get("cord"):
            _buy(rows, m["cord"], 1, "mains cord")
        if m.get("fuse"):
            inl = m.get("inlet_catalog")
            n = int(catalog.get(inl).get("fuses_per_inlet", 1)) if inl else 1
            _buy(rows, m["fuse"], n + 1, f"{n} in the inlet's fuse drawer + 1 spare")
        if m.get("wire"):
            mm = 3 * float(m.get("jumper_mm", 120))
            _buy(rows, m["wire"], round(mm / 1000, 2), f"3 x {m.get('jumper_mm', 120)} mm jumpers inlet -> supply (L, N, PE), metres")
            g = int(catalog.get(m["wire"])["gauge"])
            f = ferrule_for(g)
            if f:
                _buy(rows, f, 3, "mains jumpers into the supply's L, N and FG screw terminals")
        if m.get("tab_receptacle"):
            _buy(rows, m["tab_receptacle"], 3, "insulated receptacles on the inlet's L, N and PE tabs")
    return rows


def wiring_md(proj, model) -> str:
    if model.get("mains"):
        L = [f"# Wiring — {proj.name}", "", f"Supply: **{model['battery']}** ({model['v_bat']:g} V, mains adapter). "
             f"Average draw {model['avg_a']} A, peak {model['peak_a']} A.", ""]
    else:
        L = [f"# Wiring — {proj.name}", "",
             f"Battery: **{model['battery']}** ({model['cells']}S, {model['capacity_ah'] * 1000:g} mAh, {model['v_bat']:g} V full). "
             f"Average draw {model['avg_a']} A, peak {model['peak_a']} A; "
             + (f"hover time **{model['minutes']} min** ({model['usable']:.0%} of capacity; an ideal steady-hover "
                f"estimate: real flying draws more and gives less)." if model["hover"]
                else f"run time **{model['minutes']} min** ({model['usable']:.0%} of capacity)."), ""]
    if model["hover"]:
        h = model["hover"]
        L += [f"Hover power {h['power_w']} W for {h['mass_g']} g on {h['rotors']} x {h['prop_d_mm']:g} mm props "
              f"(momentum theory, figure of merit and motor efficiency in docs/ENGINEERING.md).", ""]
    if model.get("limits"):
        L += ["## Configure before the first power-up", "",
              "These ratings only hold with the following caps set; the checks below assume them:", ""]
        L += [f"- **{', '.join(ids)}**: {why} (peak {pk:g} A{' each' if len(ids) > 1 else ''})."
              for (why, pk), ids in _limit_groups(model).items()] + [""]
    L += ["## Runs (cut each wire to the length shown; it includes 15 % slack over the routed path)", "",
          "| Run | From | To | Kind | V | AWG | Colour | Avg A | Peak A | Routed mm | Cut mm |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for w in model["wires"]:
        L.append(f"| {w['id']} | {w['from']} | {w['to']} | {w['kind']} | {w.get('v') or ''} | {w['gauge']} | {w.get('color') or ''} | "
                 f"{w['avg_a']:.2f} | {w['peak_a']:.2f} | {w['routed_mm']} | {w['length_mm']} |")
    L += ["", "## Loads", "", "| Item | Avg A | Peak A | From |", "|---|---|---|---|"]
    for i, d in model["loads"].items():
        L.append(f"| {i} | {d['avg_a']:.3f} | {d['peak_a']:.3f} | {d['source']} |")
    L += ["", "## Ratings", "", "| Element | Check | Value | Limit | OK |", "|---|---|---|---|---|"]
    for r in model["ratings"]:
        L.append(f"| {r['what']} | {r['kind']} | {r['value']} | {r['limit']} | {'yes' if r['ok'] else ('sags (brief, at peak)' if r.get('soft') else '**NO**')} |")
    L += ["", "## Solder and wiring steps", ""] + [f"{k}. {s}" for k, s in enumerate(steps(model), 1)]
    return "\n".join(L) + "\n"


def _limit_groups(model) -> dict:
    """electrical.limits grouped by identical (why, peak) so one setting that caps four motors is one instruction."""
    g = {}
    for i, d in (model.get("limits") or {}).items():
        g.setdefault((d["why"], d["peak_a"]), []).append(i)
    return g


def steps(model) -> list:
    out = []
    for w in model["wires"]:
        n = _conductors(w)
        if w.get("supplied"):
            who = w["supplied"] if isinstance(w["supplied"], str) else w["from"]
            out.append(f"**{w['id']}** is the lead that comes with {who} ({w['length_mm']} mm): connect {w['from']} -> "
                       f"{w['to']}, nothing to cut.")
            continue
        what = w.get("color") or ("red (+) and black (-) pair" if n == 2 else f"{n} conductors")
        terms = w.get("terms") or {"from": "solder", "to": "solder"}
        shrink = "; heat-shrink each soldered end" if any(t in SOLDERED for t in terms.values()) else ""
        if w.get("lead_parts") or w.get("lead_of"):
            if w.get("lead_parts"):
                pieces = " + ".join(f"{x}'s own lead" if "." not in x else _item_name(x) for x in w["lead_parts"])
                head = (f"**{w['id']}** is a ready-made lead, {pieces} plugged together ({w['length_mm']:g} mm; the route "
                        f"needs {w['cut_min_mm']:g} mm incl. 15 % slack). Cut the plug off its {w['from']} end")
            else:
                head = f"**{w['id']}** is the {what} conductor of {w['lead_of']}'s lead: peel it off at the {w['from']} end"
            out.append(f"{head}; {w.get('color') or what} ({n} conductor{'s' if n > 1 else ''}): {join(terms['from'], w['from'])}"
                       + (f", {join(terms['to'], w['to'])}" if terms["to"] != "plug" else f"; the other end plugs into {w['to']}")
                       + f"{shrink}. Route: {' -> '.join(str(p) for p in w['points'])}." + (f" {w['note']}." if w.get("note") else ""))
        else:
            out.append(f"Cut {n} x {w['length_mm']} mm of AWG {w['gauge']} ({what}) for **{w['id']}**: "
                       f"{join(terms['from'], w['from'])}, {join(terms['to'], w['to'])}{shrink}. "
                       f"Route: {' -> '.join(str(p) for p in w['points'])}."
                       + (f" {w['note']}." if w.get("note") else ""))
        if w.get("fuse"):
            f = catalog.get(w["fuse"])
            hold = _item_name(w["fuse_holder"]) if w.get("fuse_holder") else "an inline fuse holder"
            out.append(f"Fuse **{w['id']}**: fit {hold} in its + conductor at the {w['from']} end (the holder's input lead "
                       f"goes where the + conductor went; solder its output lead to the + conductor and heat-shrink it), "
                       f"then plug in a {f['current_a']:g} A {_item_name(w['fuse'])}.")
    for (why, pk), ids in _limit_groups(model).items():
        out.append(f"Configure before the first power-up: **{', '.join(ids)}**: {why} (the wiring is rated for a {pk:g} A "
                   f"peak{' each' if len(ids) > 1 else ''} only with this set).")
    m = model.get("mains_side")
    if m:
        jm = m.get("jumper_mm", 120)
        out.append(f"Mains side (a competent person, unplugged): crimp an insulated 4.8 mm receptacle on one end of three "
                   f"{jm} mm jumpers ({_item_name(m['wire']) if m.get('wire') else 'mains-rated wire'}: black = L, white = N, "
                   f"green = earth), push them onto the inlet {m.get('inlet', '')}'s L, N and PE tabs; crimp a ferrule on "
                   f"the other ends and clamp them in the supply's AC/L, AC/N and FG (earth) screw terminals at the rated torque. "
                   f"The earth jumper is not optional: it bonds the supply's metal case to the cord's earth pin. Fit the fuses "
                   f"in the inlet drawer"
                   + (f" ({catalog.get(m['fuse'])['current_a']:g} A {_item_name(m['fuse'])})" if m.get("fuse") else "")
                   + ", close the cover over the terminals before plugging in the cord.")
    if model.get("supply_v"):
        out.append(f"Before plugging any load in: set {model['battery']}'s output to {model['supply_v']:g} V with its "
                   f"adjustment pot, measured with a meter at its output terminals (the ratings above assume it).")
    out.append("Before the first battery: check every + to - pair for a short with a multimeter, then power up through "
               "a smoke stopper (fused lead)." if not model.get("mains") else
               "Before plugging in the adapter: check every + to - pair for a short with a multimeter.")
    return out


def svg(proj, model) -> str:
    """Left-to-right power tree: columns by depth from the battery; power runs thick, signal thin dashed."""
    depth = {model["battery"]: 0}
    wires = model["wires"]
    for _ in range(len(wires) + 1):
        for w in wires:
            a, b = w["from"].split(".")[0], w["to"].split(".")[0]
            if a in depth and w["kind"] == "power":
                depth[b] = max(depth.get(b, 0), depth[a] + 1)
    for w in wires:
        for x in (w["from"].split(".")[0], w["to"].split(".")[0]):
            depth.setdefault(x, max(depth.values()) + 1 if x not in depth else depth[x])
    cols = defaultdict(list)
    for i, d in depth.items():
        cols[d].append(i)
    W, H, bw, bh = 360, 70, 150, 40
    pos = {}
    for d, ids in cols.items():
        for k, i in enumerate(sorted(ids)):
            pos[i] = (30 + d * W, 40 + k * H)
    width = 60 + (max(cols) + 1) * W
    height = 80 + max(len(v) for v in cols.values()) * H
    colors = {"red/black": "#c0392b", "red": "#c0392b", "black": "#222"}
    S = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="sans-serif" font-size="11">',
         f'<rect width="100%" height="100%" fill="#fff"/><text x="10" y="18" font-size="14" font-weight="bold">'
         f'{html.escape(proj.name)} wiring — {model["avg_a"]} A avg, {model["peak_a"]} A peak</text>']
    into = Counter()
    for w in wires:
        a, b = w["from"].split(".")[0], w["to"].split(".")[0]
        (x1, y1), (x2, y2) = pos[a], pos[b]
        x1, y1, x2, y2 = x1 + bw, y1 + bh / 2, x2, y2 + bh / 2
        p = w["kind"] == "power"
        c = colors.get(w.get("color") or "", "#c0392b" if p else "#2c6fbb")
        sw = max(1.0, 7 - int(w["gauge"]) / 4) if p else 1.2
        dash = '' if p else ' stroke-dasharray="5,3"'
        if x2 <= x1:
            x2, y2 = pos[b][0] + bw / 2, pos[b][1] + bh
        S.append(f'<path d="M{x1},{y1} C{x1 + 90},{y1} {x2 - 90},{y2} {x2},{y2}" fill="none" stroke="{c}" stroke-width="{sw:.1f}"{dash}/>')
        pin = w["from"].partition(".")[2]
        lab = (f"{w['id']}{' (' + pin + ')' if pin else ''}: AWG {w['gauge']}"
               + (f", {w['v']:g} V, {w['peak_a']:.1f} A pk" if p else ", signal") + f", {w['length_mm']} mm")
        k = into[b]
        into[b] += 1
        S.append(f'<text x="{x2 - 6}" y="{y2 - 5 - 12 * k:.0f}" text-anchor="end" font-size="10" fill="{c}" stroke="#fff" stroke-width="3" paint-order="stroke">{html.escape(lab)}</text>')
    for i, (x, y) in pos.items():
        cat = proj.items[i].spec.get("catalog", "")
        S.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="6" fill="#f4f4f4" stroke="#555"/>'
                 f'<text x="{x + 8}" y="{y + 17}" font-weight="bold">{html.escape(i)}</text>'
                 f'<text x="{x + 8}" y="{y + 32}" fill="#666" font-size="9">{html.escape(cat.split(".")[-1])}</text>')
    S.append("</svg>")
    return "\n".join(S) + "\n"


def append_assembly(path, model):
    """Add the electrical (solder and wiring) steps to out/ASSEMBLY.md, after the mechanical steps."""
    L = ["", "## Electrical — solder and wire (runs, currents and ratings in WIRING.md, diagram in wiring.svg)", ""]
    L += [f"{k}. {s}" for k, s in enumerate(steps(model), 1)]
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(old.rstrip("\n") + "\n" + "\n".join(L) + "\n", encoding="utf-8")
