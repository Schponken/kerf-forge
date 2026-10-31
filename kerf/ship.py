"""Ship package: priced BOM (buy link, unit and total cost per row) and out/ASSEMBLY.md (step-by-step build order with
an exploded render per step and the inserts, pins and screws each step needs).

Prices live in catalog/prices.json, separate from hardware.json: dimensions are engineering facts, prices are a dated
snapshot. Each entry has `buy` (where to order), `pack_qty` and `pack_usd` (unit = pack_usd / pack_qty), `checked`
(date) and `source` (the page the price was read from; usually the buy page). Keys:
  catalog paths ("servos.MG996R"), "screw:M3x8:socket" (exact), "screw:M3:socket" (size fallback, from an assortment
  pack), "screw:M3:flat", "insert:M3", "nut:M3", "washer:M3", "dowel:3x16" (exact) / "dowel:3" (fallback),
  "material:PETG" (pack_qty in grams), and any key a bom_extra row names with `price_key`.
A row nobody priced keeps an empty price and is counted as unpriced; prices never change the design checks.

Assembly steps: the root item first, then `assembly.order` entries (an id or a list of ids fitted together); items
the order does not name are fitted right after their parent. A screw is driven in the step where the later of the two
parts it joins goes on (same rule as kerf/access.py); `assembly.key_access` groups are flagged as bench sub-assemblies.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import geom

ROOT = Path(__file__).resolve().parent.parent
PRICES = ROOT / "catalog" / "prices.json"
OLD = "#C9CDCB"        # parts already fitted in a step render
NEW = "#F58518"        # the part(s) this step adds
NEW_PURCHASED = "#2F6FDB"


# ---------------------------------------------------------------- prices

def load_prices(path: Path | None = None) -> dict:
    p = Path(path or PRICES)
    if not p.exists():
        return {}
    return {k: v for k, v in json.loads(p.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def price_key(row: dict) -> list[str]:
    """Candidate price keys for one BOM row, most specific first."""
    item, spec, typ = row.get("item", ""), row.get("spec", ""), row.get("type", "")
    if row.get("price_key"):
        return [row["price_key"]]
    if typ == "purchased" and spec:
        return [spec]
    m = re.match(r"(M[\d.]+) x ([\d.]+) mm (socket|flat) head screw", item)
    if m:
        size, length, head = m.group(1), float(m.group(2)), m.group(3)
        return [f"screw:{size}x{length:g}:{head}", f"screw:{size}:{head}"]
    m = re.match(r"(M[\d.]+) heat-set insert", item)
    if m:
        return [f"insert:{m.group(1)}"]
    m = re.match(r"(M[\d.]+) hex nut", item)
    if m:
        return [f"nut:{m.group(1)}"]
    m = re.match(r"(M[\d.]+) flat washer", item)
    if m:
        return [f"washer:{m.group(1)}"]
    m = re.match(r"([\d.]+) x ([\d.]+) mm steel dowel pin", item)
    if m:
        return [f"dowel:{float(m.group(1)):g}x{float(m.group(2)):g}", f"dowel:{float(m.group(1)):g}"]
    return []


def price_bom(rows: list[dict], prices: dict, part_reports: dict | None = None) -> dict:
    """Adds buy / unit_usd / total_usd / price_key to every row in place. Printed rows are priced as filament
    (estimated mass x material price per gram). Returns the summary."""
    part_reports = part_reports or {}
    total, unpriced, approx = 0.0, [], []
    for r in rows:
        cands = price_key(r)                      # before clearing: a bom_extra row may carry its own price_key
        r.update(buy=r.get("link", ""), unit_usd="", total_usd="", price_key="")   # unpriced rows keep the catalog link
        qty = float(r.get("qty") or 1)
        if r["type"] == "printed":
            mat = r.get("spec") or "PETG"
            e = prices.get(f"material:{mat}")
            mass = part_reports.get(r["item"], {}).get("mass_est_g")
            if e and isinstance(mass, (int, float)):
                unit = e["pack_usd"] / e["pack_qty"] * mass
                r.update(buy=e["buy"], unit_usd=round(unit, 2), total_usd=round(unit * qty, 2), price_key=f"material:{mat}")
                total += unit * qty
            else:
                unpriced.append(r["item"])
            continue
        key = next((k for k in cands if k in prices), None)
        if key is None:
            unpriced.append(r["item"])
            continue
        e = prices[key]
        unit = float(e["pack_usd"]) / float(e["pack_qty"])
        r.update(buy=e["buy"], unit_usd=round(unit, 2), total_usd=round(unit * qty, 2), price_key=key)
        if key != cands[0]:
            # size-only fallback (e.g. screw:M3:socket for an M3 x 12): the price is indicative, the link is for another
            # length; say so on the row so a wrong length is never bought silently
            r["note"] = (f"{r.get('note') or ''} " if r.get("note") else "") + \
                f"PRICE FROM A DIFFERENT PACK ({key}): the link is not this length, buy {r['item']}"
            approx.append(r["item"])
        total += unit * qty
    return {"total_usd": round(total, 2), "unpriced": unpriced, "approximate": approx, "rows": len(rows)}


def write_bom(rows: list[dict], summary: dict, outdir: Path):
    fields = ["type", "item", "qty", "spec", "note", "buy", "unit_usd", "total_usd"]
    with open(outdir / "bom.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    md = ["| Type | Item | Qty | Spec | Note | Buy | Unit $ | Total $ |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        buy = f"[link]({r['buy']})" if r.get("buy") else ""
        md.append(f"| {r['type']} | {r['item']} | {r['qty']} | {r['spec']} | {r['note']} | {buy} | {r['unit_usd']} | {r['total_usd']} |")
    md.append("")
    md.append(f"**Total: ${summary['total_usd']:.2f}**"
              + (f" — {len(summary['unpriced'])} row(s) not priced: {', '.join(summary['unpriced'])}" if summary["unpriced"] else "")
              + (f" — {len(summary['approximate'])} row(s) priced from a different pack (see their notes): "
                 f"{', '.join(summary['approximate'])}" if summary.get("approximate") else "")
              + ". Fasteners are priced per piece from assortment packs; printed parts as filament only. Prices are a "
                "dated snapshot (catalog/prices.json), shipping and tax excluded.")
    (outdir / "bom.md").write_text("\n".join(md) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- assembly steps

def steps(asm) -> list[list[str]]:
    """Ordered build steps, each a list of item ids fitted together (keep-outs excluded)."""
    proj = asm.proj
    real = {i for i, it in proj.items.items() if it.role != "keepout" and it.shape is not None}
    order = proj.data["assembly"].get("order") or []
    out = [[asm.root]] if asm.root in real else []
    placed = set(out[0]) if out else set()
    named = {i for e in order for i in ([e] if isinstance(e, str) else e)}
    for i in named:
        if i not in proj.items:
            raise ValueError(f"assembly.order names unknown item '{i}'")

    def add_children(of):  # unnamed descendants go on right after their parent (breadth first)
        queue = list(of)
        while queue:
            n = queue.pop(0)
            for c in asm.children.get(n, []):
                if c in real and c not in placed and c not in named:
                    out.append([c])
                    placed.add(c)
                    queue.append(c)

    add_children(list(placed))
    for e in order:
        grp = [i for i in ([e] if isinstance(e, str) else e) if i in real and i not in placed]
        if grp:
            out.append(grp)
            placed.update(grp)
            add_children(grp)
    for e in asm.edges:  # anything still missing (named only by a keep-out chain): keep tree order
        if e.child in real and e.child not in placed:
            out.append([e.child])
            placed.add(e.child)
            add_children([e.child])
    return out


def _step_of(seq) -> dict:
    return {i: k for k, grp in enumerate(seq, start=1) for i in grp}


def plan(asm, fasteners: list, pins: list) -> list[dict]:
    """Per step: items, how each attaches, inserts to press first, pins, screws to drive."""
    proj = asm.proj
    seq = steps(asm)
    at = _step_of(seq)
    later = {k["group"]: k for k in proj.data["assembly"].get("key_access") or []}
    inserts = defaultdict(Counter)
    for iid, it in proj.items.items():
        for s in getattr(it.shape, "kerf_sites", []) if it.shape is not None else []:
            if s.role == "female" and s.kind == "heatset":
                inserts[iid][s.screw] += 1
        for s in getattr(it.shape, "kerf_pins", []) if it.shape is not None else []:   # screw-pivot inserts
            if s.fit == "heatset":
                from .iface import pin_dims
                inserts[iid][pin_dims(s.pin).get("thread", s.pin)] += 1
    screws = defaultdict(list)
    for j in fasteners:
        k = max(at.get(j["male"], 0), at.get(j["female"], 0))
        screws[k].append(j)
    pin_at = defaultdict(list)
    for pj in pins:
        k = max([at.get(i, 0) for i in pj.get("fixed_in", []) + pj.get("free_in", [])] or [0])
        pin_at[k].append(pj)
    out = []
    for k, grp in enumerate(seq, start=1):
        fits = []
        for i in grp:
            e = asm.by_child.get(i)
            it = proj.items[i]
            what = it.spec.get("catalog") if it.role == "purchased" else f"printed, {it.spec.get('material', 'PETG')}"
            how = None
            if e is not None:
                how = {"parent": e.parent, "joint": e.name, "kind": e.kind,
                       "range": list(e.range) if e.kind != "rigid" else None}
            fits.append({"item": i, "what": what, "qty": it.spec.get("qty", 1), "onto": how})
        sc = Counter((j["screw"], j["length_mm"], "flat head" if j["head"] == "countersink" else "socket head") for j in screws[k])
        groups = sorted({j["group"] for j in screws[k]})
        out.append({
            "step": k, "items": grp, "fits": fits,
            "inserts": [{"item": i, "screw": s, "qty": n} for i in grp for s, n in sorted(inserts[i].items())],
            "pins": pin_at[k],
            "screws": [{"screw": s, "length_mm": L, "head": h, "qty": n} for (s, L, h), n in sorted(sc.items(), key=str)],
            "groups": groups,
            "bench": [later[g] for g in groups if g in later],
        })
    return out


def _explode_offset(proj, asm, iid, present) -> np.ndarray:
    """Where to draw a part that is about to go on: back along its declared `insert` path, else along the axis of the
    joint it mates on (pointing away from the parent), else away from the parent's centre; 40 % of its size, 15-40 mm."""
    it = proj.items[iid]
    lo, hi = geom.bbox(it.shape)
    size = float(np.linalg.norm(hi - lo))
    dist = min(max(15.0, 0.4 * size), 40.0)
    ins = it.spec.get("insert")
    if ins and "direction" in ins:
        d = geom.world_dir(it.shape.location, ins["direction"])
        return -d / (np.linalg.norm(d) or 1.0) * float(ins.get("distance", dist))
    e = asm.by_child.get(iid)
    c = (lo + hi) / 2
    if e is not None and e.parent in present:
        plo, phi = geom.bbox(proj.items[e.parent].shape)
        away = c - (plo + phi) / 2
        # parts slide on along the mating joint's axis (screw axis of a seat, shaft of a spline or pin): use it,
        # pointing away from the parent; fall back to centre-to-centre when the axis is across that direction
        pj = proj.items[e.parent].shape.joints.get(e.pjoint)
        if pj is not None:
            ax = geom.world_dir(pj.location, (0, 0, 1))
            ax = ax / (np.linalg.norm(ax) or 1.0)
            dot = float(np.dot(ax, away))
            return (ax if dot >= 0 else -ax) * dist
        if np.linalg.norm(away) > 1e-6:
            return away / np.linalg.norm(away) * dist
    return np.array([0.0, 0.0, dist])


def step_glb(proj, asm, present: list, new: list, path: Path):
    from build123d import Color, Location, Pos
    shapes = []
    for iid in present:
        it = proj.items[iid]
        s = it.shape.moved(Location())
        if iid in new:
            s = Pos(*_explode_offset(proj, asm, iid, present)) * s
            s.color = Color(NEW_PURCHASED if it.role == "purchased" else NEW)
        else:
            s.color = Color(OLD)
        s.label = iid
        shapes.append(s)
    geom.write_glb(shapes, path, 0.08, 0.3, label=proj.name)


from .pins import lock_advice  # noqa: E402


def wiring_tools(model) -> list:
    """Hand tools the electrical steps need, from how each wire end is joined (kerf/electrical.py TERMINALS)."""
    if not model or not model.get("wires"):
        return []
    terms = {t for w in model["wires"] for t in (w.get("terms") or {"from": "solder", "to": "solder"}).values()}
    if any(w.get("fuse_holder") for w in model["wires"]):
        terms.add("solder")
    out = ["wire stripper and cutter", "multimeter"]
    if terms & {"solder", "header"}:
        out.append("soldering iron, solder and a heat gun for the heat-shrink")
    if "crimp" in terms:
        out.append("crimp tool for 0.1 in (Dupont-style) pins")
    if "screw" in terms:
        out.append("ferrule crimper and a small flat screwdriver for the screw terminals")
    if (model.get("mains_side") or {}).get("tab_receptacle"):
        out.append("crimp tool for insulated 4.8 mm receptacles")
    return out


def write_assembly(proj, asm, rep: dict, outdir: Path, render=None) -> dict:
    """out/ASSEMBLY.md (+ out/assembly_steps/step_NN_iso.png when `render` is given: render(glb, prefix))."""
    from .access import key_spec
    st = plan(asm, rep.get("assembly", {}).get("fasteners", []), rep.get("assembly", {}).get("pins", []))
    sd = outdir / "assembly_steps"
    sd.mkdir(exist_ok=True)
    keys = set()
    for j in rep.get("assembly", {}).get("fasteners", []):
        try:
            keys.add(f"{key_spec(j['screw'], j['head'])['s']:g} mm hex key ({j['screw']}{' flat head' if j['head'] == 'countersink' else ''})")
        except Exception:  # noqa: BLE001 - a size without a key entry is listed without one
            keys.add(f"driver for {j['screw']}")
    any_insert = any(s["inserts"] for s in st)
    L = [f"# Assembly — {proj.data.get('name', proj.name)}", "",
         "Generated by `kerf build` from the joint tree, `assembly.order` and the fastener/pin checks. Each picture shows "
         "the parts already fitted in grey and this step's part(s) in colour, moved back along the way they go on.", "",
         "## Before you start", "",
         f"- Print every part in `plates/` (orientation is already set). Parts: {', '.join(proj.printed)}.",
         "- Tools: " + ("; ".join(sorted(keys)
                                  + (["soldering iron with a heat-set insert tip", "a flat plate to press inserts flush"] if any_insert else [])
                                  + (["a vise or small hammer to press dowel pins"] if any(not p.get('screw_pivot') for s in st for p in s['pins']) else [])
                                  + (["a screwdriver that fits the shoulder screws' heads"] if any(p.get('shoulder') for s in st for p in s['pins']) else [])
                                  + wiring_tools(rep.get("electrical")))
                         or "none") + ".", "- Shopping list with links and prices: `bom.md`.", ""]
    for s in st:
        L.append(f"## Step {s['step']} — {', '.join(s['items'])}")
        L.append("")
        if render is not None:
            present = [i for x in st[: s["step"]] for i in x["items"]]
            glb = sd / f"step_{s['step']:02d}.glb"
            step_glb(proj, asm, present, s["items"], glb)
            render(glb, sd / f"step_{s['step']:02d}")
            glb.unlink(missing_ok=True)
            L += [f"![step {s['step']}](assembly_steps/step_{s['step']:02d}_iso.png)", ""]
        for x in s["inserts"]:
            L.append(f"- First press {x['qty']} x {x['screw']} heat-set insert(s) into **{x['item']}** (iron tip, press square until flush with or just below the face, hold a flat plate on it while it cools, trim any plastic lip).")
        for f in s["fits"]:
            qty = f" x{f['qty']}" if f["qty"] != 1 else ""
            if f["onto"] is None:
                L.append(f"- Start with **{f['item']}**{qty} ({f['what']}).")
            else:
                o = f["onto"]
                moves = f" — it must then move freely over {o['range'][0]:g} to {o['range'][1]:g}" + (" deg" if o["kind"] == "revolute" else " mm") if o["range"] else ""
                L.append(f"- Fit **{f['item']}**{qty} ({f['what']}) onto **{o['parent']}** (joint `{o['joint']}`){moves}.")
            L += fit_notes(proj, rep, f["item"])
        for p in s["pins"]:
            if p.get("shoulder"):
                L.append(f"- Pivot `{p['group']}`: {p['d_mm']:g} x {p['length_mm']:g} mm shoulder screw through {', '.join(p['free_in'])} "
                         f"into {', '.join(p['fixed_in'])}; tighten gently (0.2-0.3 N m: more only pulls a heat-set insert back out) until the shoulder bottoms, then check the joint "
                         f"turns freely (the shoulder bottoms on the insert, so an insert left proud only adds play; one set deeper "
                         f"than the free band's length lets the shoulder clamp the stack and stop the joint).")
            elif p.get("screw_pivot"):
                L.append(f"- Pivot `{p['group']}`: {p['pin']} x {p['length_mm']:g} mm screw through {', '.join(p['free_in'])} into "
                         f"{', '.join(p['fixed_in'])}; back off ~1/8 turn so it turns freely and lock it: {lock_advice(p.get('fixed_fit'))}.")
            else:
                L.append(f"- Hinge `{p['group']}`: press the {p['d_mm']:g} x {p['length_mm']:g} mm dowel into {', '.join(p['fixed_in'])}; "
                         f"it turns in {', '.join(p['free_in'])}.")
        for x in s["screws"]:
            L.append(f"- Drive {x['qty']} x {x['screw']} x {x['length_mm']:g} mm {x['head']} screw(s) (groups: {', '.join(s['groups'])}).")
        L += screw_notes(proj, rep, s["groups"])
        for b in s["bench"]:
            L.append(f"- Bench sub-assembly: do group `{b['group']}` before fitting {', '.join(b['before'])} — {b['why']}.")
        L.append("")
    (outdir / "ASSEMBLY.md").write_text("\n".join(L), encoding="utf-8")
    return {"file": "ASSEMBLY.md", "steps": len(st), "renders": render is not None}


def _dir_words(d) -> str:
    names = (("+X", "-X"), ("+Y", "-Y"), ("+Z (up)", "-Z (down)"))
    k = int(np.argmax(np.abs(d)))
    return names[k][0 if d[k] > 0 else 1] + ("" if abs(d[k]) > 0.97 else f" ({[round(float(x), 2) for x in d]})")


def fit_notes(proj, rep: dict, iid: str) -> list[str]:
    """Extra lines for fitting one item: its `assembly_note` and the checked `insert` path."""
    out = []
    note = proj.items[iid].spec.get("assembly_note")
    if note:
        out.append(f"  - {note}")
    for r in rep.get("assembly", {}).get("insertion", []) or []:
        if r["item"] == iid:
            out.append(f"  - It goes in moving {_dir_words(np.asarray(r['direction'], float))} (world), from "
                       f"{r['distance_mm']:g} mm away" + (" — this path is checked clear." if r["clear"] else
                                                          " — WARNING: the check found this path blocked."))
    return out


def screw_notes(proj, rep: dict, groups: list) -> list[str]:
    """Extra lines for a step's screws: bom_extra items tied to their group (washers, spacers) and hex-key warnings."""
    out = []
    for x in proj.data.get("bom_extra") or []:
        if x.get("group") in groups:
            out.append(f"  - With: {x.get('qty', '')} x {x['item']}" + (f" — {x['spec']}" if x.get("spec") else "") + ".")
    ball = Counter(r["group"] for r in rep.get("assembly", {}).get("hex_keys", []) or []
                   if r["group"] in groups and not r["straight"] and r.get("ball_end"))
    for g, n in sorted(ball.items()):
        out.append(f"  - {n} screw(s) of `{g}` need a ball-end hex key (a straight key is blocked; tilt up to 25 deg).")
    return out


def write(proj, asm, rep: dict, outdir: Path, render=None, prices: dict | None = None) -> dict:
    """Price the BOM rows in rep['bom'] (rewrites bom.csv / bom.md) and write ASSEMBLY.md."""
    prices = load_prices() if prices is None else prices
    extra_keys = {x["item"]: x["price_key"] for x in proj.data.get("bom_extra") or [] if x.get("price_key")}
    for r in rep.get("bom", []):
        if r["item"] in extra_keys:
            r["price_key"] = extra_keys[r["item"]]
    summary = price_bom(rep.get("bom", []), prices, rep.get("parts", {}))
    write_bom(rep.get("bom", []), summary, outdir)
    return {"bom": summary, "assembly": write_assembly(proj, asm, rep, outdir, render=render)}
