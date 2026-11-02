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
NEW_SCREW = "#E4572E"  # this step's screws, drawn backed out of their holes along their axis
OLD_SCREW = "#6B7075"  # screws already driven


# ---------------------------------------------------------------- prices

def load_prices(path: Path | None = None) -> dict:
    p = Path(path or PRICES)
    if not p.exists():
        return {}
    return {k: v for k, v in json.loads(p.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def price_key(row: dict) -> list[str]:
    """Candidate price keys for one BOM row, most specific first."""
    item, spec, typ = row.get("item", ""), row.get("spec", ""), row.get("type", "")
    if row.get("price_key"):              # a list = exact pack first, then a fallback (flagged as a different pack)
        pk = row["price_key"]
        return list(pk) if isinstance(pk, (list, tuple)) else [pk]
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


INVENTORY = Path(__file__).resolve().parent.parent / "catalog" / "inventory.json"


def load_inventory(path: Path | None = None) -> dict:
    """Parts Spencer already has: {key: qty}, keyed like the BOM (a catalog path such as servos.MG996R, or a price key
    such as screw:M3x8:socket). Edited in Kerf Studio ("My parts")."""
    p = Path(path or INVENTORY)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    items = d.get("items", d) if isinstance(d, dict) else {}
    return {str(k): float(v) for k, v in items.items() if not str(k).startswith("_") and isinstance(v, (int, float)) and v > 0}


def price_bom(rows: list[dict], prices: dict, part_reports: dict | None = None, inventory: dict | None = None) -> dict:
    """Adds buy / unit_usd / total_usd / price_key to every row in place. Printed rows are priced as filament
    (estimated mass x material price per gram). Parts on hand (`inventory`, {key: qty}) cover rows of the exact same
    key first: those pieces cost nothing and need no pack. Returns the summary."""
    part_reports = part_reports or {}
    left = dict(inventory or {})
    on_hand = []
    total, unpriced, approx = 0.0, [], []
    need = defaultdict(float)                     # per price key: how much of it the build uses (pieces or grams)
    for r in rows:
        cands = price_key(r)                      # before clearing: a bom_extra row may carry its own price_key
        r.update(buy=r.get("link", ""), unit_usd="", total_usd="", price_key="")   # unpriced rows keep the catalog link
        qty = float(r.get("qty") or 1)
        if r.get("included"):                     # ships with another item (a horn's centre screw with the servo)
            r.update(unit_usd=0, total_usd=0, note=r.get("note") or "included")
            continue
        if r["type"] == "printed":
            mat = r.get("spec") or "PETG"
            e = prices.get(f"material:{mat}")
            mass = part_reports.get(r["item"], {}).get("mass_est_g")
            if e and isinstance(mass, (int, float)):
                unit = e["pack_usd"] / e["pack_qty"] * mass
                r.update(buy=e["buy"], unit_usd=round(unit, 2), total_usd=round(unit * qty, 2), price_key=f"material:{mat}")
                total += unit * qty
                need[f"material:{mat}"] += mass * qty
            else:
                unpriced.append(r["item"])
            continue
        key = next((k for k in cands if k in prices), None)
        if key is None:
            unpriced.append(r["item"])
            continue
        e = prices[key]
        unit = float(e["pack_usd"]) / float(e["pack_qty"])
        have_key = next((k for k in (cands[:1] + [r.get("spec") or ""]) if k and left.get(k, 0) > 0), None)
        have = min(qty, left[have_key]) if have_key else 0.0
        if have:
            left[have_key] -= have
            on_hand.append(r["item"])
            r["on_hand"] = have
            r["note"] = (f"{r.get('note')}; " if r.get("note") else "") + f"you have {have:g} (My parts)"
        qty_buy = qty - have
        r.update(buy=e["buy"], unit_usd=round(unit, 2), total_usd=round(unit * qty_buy, 2), price_key=key)
        if key != cands[0]:
            # size-only fallback (e.g. screw:M3:socket for an M3 x 12): the price is indicative, the link is for another
            # length; say so on the row so a wrong length is never bought silently
            r["note"] = (f"{r.get('note') or ''} " if r.get("note") else "") + \
                f"PRICE FROM A DIFFERENT PACK ({key}): the link is not this length, buy {r['item']}"
            approx.append(r["item"])
        total += unit * qty_buy
        need[key] += qty_buy
    # what the shopper actually pays: whole packs (a 100-pack of screws, a 1 kg spool), one pack per started pack
    import math
    packs = {k: math.ceil(n / float(prices[k]["pack_qty"]) - 1e-9) for k, n in need.items() if n > 0}
    pack_cost = {k: round(c * float(prices[k]["pack_usd"]), 2) for k, c in packs.items()}
    packs_usd = sum(pack_cost.values())
    return {"total_usd": round(total, 2), "packs_usd": round(packs_usd, 2), "packs": packs, "pack_cost": pack_cost,
            "on_hand": on_hand,
            "pack_qty": {k: float(prices[k]["pack_qty"]) for k in packs}, "unpriced": unpriced,
            "approximate": approx, "rows": len(rows)}


def write_bom(rows: list[dict], summary: dict, outdir: Path):
    from html import escape
    from urllib.parse import quote, urlsplit

    def cell(value):
        text = str(value).replace("\r\n", "\n").replace("\r", "\n")
        return escape(text, quote=False).replace("|", "\\|").replace("\n", "<br>")

    fields = ["type", "item", "qty", "spec", "note", "buy", "unit_usd", "total_usd"]
    with open(outdir / "bom.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    md = ["# Shopping list", "",
          "Use this list to gather parts before assembly. Printed rows account for filament, not a print service. "
          "Unit $ and Total $ price the quantity used; buying whole packs can cost more (see the pack estimate below). "
          "A source link is a reference page, not a confirmed shop link.", "",
          *( ["Some items are not priced yet: the subtotal is not a complete budget.", ""] if summary.get("unpriced") else [] ),
          "| Type | Item | Qty | Spec | Note | Buy | Unit $ | Total $ |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        # a priced row links where to buy; an unpriced one only has its datasheet / source page, and says so
        raw_url = r.get("buy") or ""
        try:
            parsed = urlsplit(raw_url)
            url = quote(raw_url, safe=":/?#[]@!$&'*+,;=%~._-") if parsed.scheme in ("http", "https") and parsed.netloc else ""
        except ValueError:
            url = ""
        buy = (f"[buy]({url})" if r.get("price_key") or r.get("type") == "printed" and r.get("unit_usd") != ""
               else f"[source]({url})") if url else ("Link unavailable" if raw_url else "")
        values = [cell(r[k]) if k != "buy" else buy for k in fields]
        md.append("| " + " | ".join(values) + " |")
    md.append("")
    md.append((f"**Priced so far: ${summary['total_usd']:.2f}**. Not priced yet ({len(summary['unpriced'])}): "
               f"{', '.join(summary['unpriced'])}, so the real total is higher"
               if summary["unpriced"] else f"**Total: ${summary['total_usd']:.2f}**")
              + (f" — {len(summary['approximate'])} row(s) priced from a different pack (see their notes): "
                 f"{', '.join(summary['approximate'])}" if summary.get("approximate") else "")
              + (f" — {len(summary['on_hand'])} row(s) partly or wholly from your parts on hand (not counted): "
                 f"{', '.join(summary['on_hand'])}" if summary.get("on_hand") else "")
              + ". Fasteners are priced per piece from assortment packs; printed parts as filament only. Prices are a "
                "dated snapshot; confirm current prices at the shop. Shipping and tax are excluded.")
    if summary.get("packs_usd"):
        md.append("")
        md.append(f"**Buying whole packs** (a 100-pack of screws, a filament spool, ...) for the priced rows costs "
                  f"**${summary['packs_usd']:.2f}** up front; the per-piece total above is what this build uses of them.")
        # say which packs make that number, so a maker who already has screws or can buy a smaller pack knows
        cost = summary.get("pack_cost") or {}
        names = {r["price_key"]: r["item"] for r in rows if r.get("price_key") and r.get("type") != "printed"}

        def pack(k):
            n, q = summary["packs"][k], summary["pack_qty"][k]
            what = (f"{k.split(':', 1)[1]} filament, {n} x {q / 1000:g} kg spool" if k.startswith("material:")
                    else f"{names.get(k, k)}, {n} x pack of {q:g}")
            return f"{what} = ${cost[k]:.2f}"
        big = sorted(cost, key=lambda k: -cost[k])[:3]
        if big:
            md.append("Biggest packs: " + "; ".join(pack(k) for k in big) + ".")
    (outdir / "bom.md").write_text("\n".join(md) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- assembly steps

def steps(asm) -> list[list[str]]:
    """Ordered build steps, each a list of item ids fitted together (keep-outs excluded)."""
    proj = asm.proj
    # off-board items (a power adapter or controller on the desk) are not fitted to the device: they get their own
    # section in ASSEMBLY.md, not a "fit onto" step, and stay out of the step pictures
    real = {i for i, it in proj.items.items() if it.role != "keepout" and it.shape is not None and not it.spec.get("off_board")}
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


def joins(asm, seq) -> tuple[dict, dict]:
    """When items become one piece. A step whose part mates onto a parent that is only fitted LATER is a bench
    sub-assembly (e.g. a horn screwed to a bracket on the bench, pressed onto its servo once the servo is in): it is
    joined to the device at its parent's step, after that step's own parts. Returns (bench, attach):
    bench[k] = step where bench step k joins; attach[m] = [(k, item, parent)] joined at step m.
    Steps are walked in order with a union-find, so chained sub-assemblies resolve too."""
    at = _step_of(seq)
    bench, attach = {}, defaultdict(list)
    for k, grp in enumerate(seq, start=1):
        for i in grp:
            e = asm.by_child.get(i)
            if e is not None and e.parent not in grp and at.get(e.parent, 0) > k:
                m = at[e.parent]
                bench[k] = max(bench.get(k, 0), m)
                attach[m].append((k, i, e.parent))
    return bench, dict(attach)


def _connect_steps(asm, seq, attach) -> dict:
    """A function: at which (step, phase) a set of items first forms one piece. Phase 1 = with the step's own parts,
    phase 2 = after the bench sub-assemblies that join at this step are on."""
    parent = {}

    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    events = []                                   # (step, phase, snapshot of roots) after each phase
    placed = set()
    for k, grp in enumerate(seq, start=1):
        placed.update(grp)
        for i in grp:
            e = asm.by_child.get(i)
            if e is not None and e.parent in placed:
                union(i, e.parent)
        events.append((k, 1, {i: find(i) for i in placed}))
        for _, c, p in attach.get(k, []):
            union(c, p)
        events.append((k, 2, {i: find(i) for i in placed}))

    def when(items):
        items = [i for i in items if i in placed]
        for k, ph, roots in events:
            if all(i in roots for i in items) and len({roots[i] for i in items}) <= 1:
                return k, ph
        at = _step_of(seq)
        return max([at.get(i, 0) for i in items] or [0]), 2
    return when


def plan(asm, fasteners: list, pins: list) -> list[dict]:
    """Per step: items, how each attaches, inserts to press first, pins, screws to drive. Screws and pins go in at the
    step (and phase) where the parts they join first form one piece, so a bench sub-assembly's own screws are driven
    on the bench and the screws that hold it to the device come after it is joined (no forward references)."""
    proj = asm.proj
    seq = steps(asm)
    at = _step_of(seq)
    bench, attach = joins(asm, seq)
    when = _connect_steps(asm, seq, attach)
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
        screws[when([j["male"], j["female"]])].append(j)
    pin_at = defaultdict(list)
    for pj in pins:
        pin_at[when(pj.get("fixed_in", []) + pj.get("free_in", []))].append(pj)

    def how(e):
        return {"parent": e.parent, "joint": e.name, "kind": e.kind, "range": list(e.range) if e.kind != "rigid" else None}

    def screw_rows(js):
        sc = Counter((j["screw"], j["length_mm"], "flat head" if j["head"] == "countersink" else "socket head") for j in js)
        return [{"screw": s, "length_mm": L, "head": h, "qty": n} for (s, L, h), n in sorted(sc.items(), key=str)]

    out = []
    for k, grp in enumerate(seq, start=1):
        fits = []
        for i in grp:
            e = asm.by_child.get(i)
            it = proj.items[i]
            what = human_item(it) if it.role == "purchased" else f"printed, {it.spec.get('material', 'PETG')}"
            later_parent = e is not None and e.parent not in grp and at.get(e.parent, 0) > k   # joined at its parent's step
            fits.append({"item": i, "what": what, "qty": it.spec.get("qty", 1),
                         "onto": None if e is None or later_parent else how(e), "joins_later": later_parent})
        js1, js2 = screws[(k, 1)], screws[(k, 2)]
        groups = sorted({j["group"] for j in js1 + js2})
        out.append({
            "step": k, "items": grp, "fits": fits, "bench_for": bench.get(k),
            "inserts": [{"item": i, "screw": s, "qty": n} for i in grp for s, n in sorted(inserts[i].items())],
            "pins": pin_at[(k, 1)], "screws": screw_rows(js1), "groups": sorted({j["group"] for j in js1}),
            "attach": [{"step": b, "items": seq[b - 1], "via": c, **how(asm.by_child[c])} for b, c, _ in attach.get(k, [])],
            "pins_after": pin_at[(k, 2)], "screws_after": screw_rows(js2), "groups_after": sorted({j["group"] for j in js2}),
            "fastener_joints": js1 + js2,
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


def _screw_solid(j, backed_out: float):
    """A socket-head screw at a fastener joint: shank from the seat (`at`) along `dir` for its length, head above the
    seat; moved back out of the hole by `backed_out` mm (this step's screws are drawn ready to go in)."""
    from build123d import Cylinder, Align, Location, Plane, Pos
    d = float(str(j["screw"]).lstrip("M") or 3)
    L = float(j.get("length_mm") or 6)
    at, dr = np.asarray(j["at"], float), np.asarray(j["dir"], float)
    at = at - dr * backed_out
    shank = Cylinder(d / 2, L, align=(Align.CENTER, Align.CENTER, Align.MIN))
    head = Pos(0, 0, -d) * Cylinder(0.85 * d, d, align=(Align.CENTER, Align.CENTER, Align.MIN))
    loc = Location(Plane(origin=tuple(at), z_dir=tuple(dr)))
    return loc * (shank + head)


def step_glb(proj, asm, present: list, new: list, path: Path, screws: list | None = None, done_screws: list | None = None):
    """GLB of one assembly step: parts already on in grey, this step's parts in colour pulled back along the way they
    go on, this step's screws in red backed out of their holes, screws already driven in dark grey."""
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
    for k, j in enumerate(screws or []):
        try:
            sc = _screw_solid(j, float(j.get("length_mm") or 6) + 6)
        except Exception:  # noqa: BLE001 - a screw glyph that cannot be placed is left out, never a failed build
            continue
        sc.color, sc.label = Color(NEW_SCREW), f"screw_{k}"
        shapes.append(sc)
    for k, j in enumerate(done_screws or []):
        try:
            sc = _screw_solid(j, 0.0)
        except Exception:  # noqa: BLE001
            continue
        sc.color, sc.label = Color(OLD_SCREW), f"done_screw_{k}"
        shapes.append(sc)
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


ELECTRONIC_PREFIXES = ("electronics.", "boards.", "drone.stacks.", "drone.batteries.", "drone.receivers.", "drone.vtx")


def feel(screw: str) -> str:
    """How tight, in hand terms (a printed part strips long before a steel screw is hurt)."""
    d = float(re.sub(r"[^\d.]", "", screw) or 3)
    return ("snug: turn with the short arm of the key until the head seats, then stop" if d <= 3
            else "firm: the short arm of the key, a solid pull once the head seats, then stop")


def _split(note: str, indent: str = "  ") -> list[str]:
    """A long note becomes one sub-bullet per sentence or clause, so no step line is a wall of text."""
    if len(note) <= 160:
        return [f"{indent}- {note}"]
    parts = [x.strip() for x in re.split(r"(?<=[.;:])\s+(?=[A-Za-z(])", note) if x.strip()]
    return [f"{indent}- {x[0].upper() + x[1:]}" for x in parts]


def _is_horn_on_servo(proj, child: str, parent: str) -> bool:
    c = proj.items[child].spec.get("catalog", "") if child in proj.items else ""
    pa = proj.items[parent].spec.get("catalog", "") if parent in proj.items else ""
    return c.startswith("servo_horns.") and pa.startswith("servos.")


def _test_fit_step(proj) -> list[str]:
    """Step 0: make the printer's fits match before printing every part (kerf/calibrate.py)."""
    if not proj.printed:
        return []
    from . import calibrate as C
    printer = proj.data.get("printer") or C.DEFAULT_PRINTER
    mats = sorted({it.spec.get("material", "PETG") for it in proj.printed.values()})
    have = C.load_profile(printer).get("materials", {})
    L = ["## Step 0 — test-fit before printing everything", ""]
    for m in mats:
        if C.mat_key(m) in have:
            L.append(f"- {printer} / {m}: your measured fit offsets are already applied (calibration profile), so holes, "
                     "insert bores and servo pockets are sized for your printer.")
        else:
            L += [f"- {printer} / {m}: no calibration yet, so holes use textbook sizes. Skipping this risks loose or tight "
                  "fits on every part:",
                  f"  - run `kerf calibrate --material {m}` and print the coupon;",
                  "  - try a screw, an insert, a pin and a servo tab in it;",
                  f"  - report what fit with `kerf feedback {m} hole_M3=ok ...` (the coupon's CARD.md lists the names), then rebuild."]
    L += ["- Then print the smallest part with a screw hole or servo pocket first and try the real screw / servo in it "
          "before printing the rest.", ""]
    return L


def write_assembly(proj, asm, rep: dict, outdir: Path, render=None, firmware_info: dict | None = None) -> dict:
    """out/ASSEMBLY.md (+ out/assembly_steps/step_NN_iso.png when `render` is given: render(glb, prefix))."""
    from .access import key_spec
    from . import firmware
    st = plan(asm, rep.get("assembly", {}).get("fasteners", []), rep.get("assembly", {}).get("pins", []))
    sd = outdir / "assembly_steps"
    sd.mkdir(exist_ok=True)
    if render is not None:
        for old in sd.glob("step_*"):            # a project with fewer steps than its last build leaves no stale pictures
            old.unlink()
    keys = set()
    for j in rep.get("assembly", {}).get("fasteners", []):
        try:
            keys.add(f"{key_spec(j['screw'], j['head'])['s']:g} mm hex key ({j['screw']}{' flat head' if j['head'] == 'countersink' else ''})")
        except Exception:  # noqa: BLE001 - a size without a key entry is listed without one
            keys.add(f"driver for {j['screw']}")
    any_insert = any(s["inserts"] for s in st)
    all_pins = [p for s in st for p in s["pins"] + s["pins_after"]]
    L = [f"# Assembly — {proj.data.get('name', proj.name)}", "",
         "Generated by `kerf build` from the joint tree, `assembly.order` and the fastener/pin checks. Each picture shows "
         "the parts already fitted in grey and this step's part(s) in colour, moved back along the way they go on.", "",
         "## Before you start", "",
         (f"- Start with the test-fit in Step 0, then print the remaining parts from `plates/`. "
          f"Read [print settings](plates/PRINT_SETTINGS.md) first; orientation is already set. Parts: {', '.join(proj.printed)}."
          if proj.printed else "- This assembly has no printed parts. Gather the purchased parts from the shopping list before starting.")]
    tools = (sorted(keys) + (["soldering iron with a heat-set insert tip", "a flat plate to press inserts flush"] if any_insert else [])
             + (["a vise or small hammer to press dowel pins"] if any(not p.get('screw_pivot') and not p.get('shoulder') for p in all_pins) else [])
             + (["a screwdriver that fits the shoulder screws' heads"] if any(p.get('shoulder') for p in all_pins) else [])
             + wiring_tools(rep.get("electrical")))
    L += ["- Tools:" + ("" if tools else " none")] + [f"  - {t}" for t in tools]
    L += ["- Shopping list with links and prices: [bom.md](bom.md)."]
    if firmware_info:
        L.append("- First power-up and test: [firmware/BRINGUP.md](firmware/BRINGUP.md)" + (f" with the program `{firmware_info['program']}`."
                                                                      if firmware_info.get("program") else "."))
    L.append("")
    L += _test_fit_step(proj)
    horns = any(_is_horn_on_servo(proj, e.child, e.parent) for e in asm.edges)
    if firmware_info and horns:
        L += firmware.centre_step(firmware_info)
    elif horns:
        L += ["## Step 0b — centre the servos (before any horn goes on)", "",
              "- Power each servo with a servo tester (or its controller) at 1500 us so it sits at its centre; do not turn "
              "the shaft by hand afterwards.", ""]

    def pin_lines(pins):
        out = []
        for p in pins:
            if p.get("shoulder"):
                out += [f"- Pivot `{p['group']}`: {p['d_mm']:g} x {p['length_mm']:g} mm shoulder screw through "
                        f"{', '.join(p['free_in'])} into {', '.join(p['fixed_in'])}.",
                        "  - Tighten finger-tight on the short arm of the driver (about 0.2-0.3 N·m) until the shoulder "
                        "bottoms; more only pulls the heat-set insert back out.",
                        "  - Check the joint turns freely: an insert left proud only adds play, but one set too deep lets "
                        "the shoulder clamp the stack and stop the joint (reseat it flush)."]
            elif p.get("screw_pivot"):
                out += [f"- Pivot `{p['group']}`: {p['pin']} x {p['length_mm']:g} mm screw through {', '.join(p['free_in'])} "
                        f"into {', '.join(p['fixed_in'])}.",
                        "  - Snug it, then back off about 1/8 turn so the joint turns freely.",
                        f"  - Lock it: {lock_advice(p.get('fixed_fit'))}."]
            else:
                out.append(f"- Hinge `{p['group']}`: press the {p['d_mm']:g} x {p['length_mm']:g} mm dowel into "
                           f"{', '.join(p['fixed_in'])}; it turns in {', '.join(p['free_in'])}.")
        return out

    def screw_lines(screws, groups):
        out = [f"- Drive {x['qty']} x {x['screw']} x {x['length_mm']:g} mm {x['head']} screw(s) (groups: {', '.join(groups)}) "
               f"— {feel(x['screw'])}." for x in screws]
        return out + screw_notes(proj, rep, groups)

    def horn_note(child, parent):
        if not _is_horn_on_servo(proj, child, parent):
            return []
        e = asm.by_child.get(child)
        if e is None or e.kind != "revolute" or e.parent != parent:
            return [f"  - The servo is centred (Step 0b): press **{child}** onto the spline, then fit the horn's centre screw."]
        lo, hi = e.range
        c = firmware.centre_of(e, lo, hi)
        pose = ("as in the picture" if abs(c - e.home) < 0.5 else
                f"not the pose in the picture (that shows {e.home:g} deg): set the driven parts to {c:g} deg, then fit it")
        where = f"joint `{e.name}` at {c:g} deg ({'the middle of its' if e.centre is None else 'in its'} {lo:g} to {hi:g} deg travel)"
        from .access import servo_goes_last
        if servo_goes_last(asm, parent, child):       # the servo goes in last, onto the horn held in place
            return [f"  - The servo is centred (Step 0b) and goes in last: hold **{child}** (and what is built onto it) in "
                    f"place with {where}, {pose}, and slide **{parent}** in until its spline enters the horn; then fit the "
                    "horn's centre screw. The bring-up program counts degrees from this position."]
        return [f"  - The servo is centred (Step 0b): press **{child}** onto the spline with {where}, {pose}; "
                "then fit the horn's centre screw. The bring-up program counts degrees from this position."]

    for s in st:
        title = ", ".join(s["items"])
        if s["bench_for"]:
            title += f" (bench sub-assembly, joins the build in step {s['bench_for']})"
        L += [f"## Step {s['step']} — {title}", ""]
        if render is not None:
            if s["bench_for"]:            # a bench sub-assembly is drawn on its own, not floating in the build
                present = list(s["items"])
            else:
                joined = [i for a in s["attach"] for i in a["items"]]
                present = [i for x in st[: s["step"]] if not x["bench_for"] or x["bench_for"] <= s["step"] for i in x["items"]]
                present += [i for i in joined if i not in present]
            new = list(s["items"]) + [i for a in s["attach"] for i in a["items"]]
            done = [j for x in st[: s["step"] - 1] for j in x["fastener_joints"] if j["male"] in present and j["female"] in present]
            glb = sd / f"step_{s['step']:02d}.glb"
            step_glb(proj, asm, present, new, glb, screws=s["fastener_joints"], done_screws=done)
            render(glb, sd / f"step_{s['step']:02d}", labels=new, focus=new)
            glb.unlink(missing_ok=True)
            L += [f"![step {s['step']}](assembly_steps/step_{s['step']:02d}_iso.png)", ""]
        for x in s["inserts"]:
            L.append(f"- First press {x['qty']} x {x['screw']} heat-set insert(s) into **{x['item']}**: iron tip, press "
                     "square until flush with or just below the face, hold a flat plate on it while it cools, trim any lip.")
        for f in s["fits"]:
            qty = f" x{f['qty']}" if f["qty"] != 1 else ""
            if f["onto"] is None and f.get("joins_later"):
                L.append(f"- Take **{f['item']}**{qty} ({f['what']}); it goes onto the build in step {s['bench_for']}.")
            elif f["onto"] is None:
                L.append(f"- Start with **{f['item']}**{qty} ({f['what']}).")
            else:
                o = f["onto"]
                moves = f" — it must then move freely over {o['range'][0]:g} to {o['range'][1]:g}" + (" deg" if o["kind"] == "revolute" else " mm") if o["range"] else ""
                L.append(f"- Fit **{f['item']}**{qty} ({f['what']}) onto **{o['parent']}** (joint `{o['joint']}`){moves}.")
                L += horn_note(f["item"], o["parent"])
            L += fit_notes(proj, rep, f["item"])
        L += pin_lines(s["pins"])
        L += screw_lines(s["screws"], s["groups"])
        for a in s["attach"]:
            moves = (f" — it must then move freely over {a['range'][0]:g} to {a['range'][1]:g}"
                     + (" deg" if a["kind"] == "revolute" else " mm")) if a["range"] else ""
            L.append(f"- Now join the step-{a['step']} sub-assembly ({', '.join(a['items'])}): fit **{a['via']}** onto "
                     f"**{a['parent']}** (joint `{a['joint']}`){moves}.")
            L += horn_note(a["via"], a["parent"])
        L += pin_lines(s["pins_after"])
        L += screw_lines(s["screws_after"], s["groups_after"])
        for b in s["bench"]:
            L.append(f"- Bench sub-assembly: do group `{b['group']}` before fitting {', '.join(b['before'])} — {b['why']}.")
        L.append("")
    off = [(i, it) for i, it in proj.items.items() if it.spec.get("off_board")]
    if off:
        elec = all(str(it.spec.get("catalog", "")).startswith(ELECTRONIC_PREFIXES) for _, it in off)
        L += [f"## {'Bench electronics' if elec else 'Off the device'} (not mounted)", "",
              "These are not fitted to the build: place them as described and connect them as `WIRING.md` says.", ""]
        L += [f"- **{i}** ({human_item(it)}): {it.spec['off_board']}." for i, it in off]
        L.append("")
    lock = next((q.get("locking") for q in proj.data.get("requirements") or [] if q.get("check") == "screw_locking"), None)
    if lock:
        L += ["## Lock the screws that vibrate", "",
              "Motors shake screws loose. Lock these groups as you fit them (threadlocker: a small drop on the screw's "
              "last threads only, kept off the printed plastic; nyloc: the nylon ring goes on last):", ""]
        L += [f"- `{g}`: {m}" for g, m in sorted(lock.items())] + [""]
    L += story_notes(rep.get("use_story"))
    from .req_human import notes as carry_notes
    L += carry_notes(proj, rep)
    if rep.get("failure_modes"):
        from .failure import lines
        L += ["## If it breaks", "",
              "Which part gives way first in each part's worst load case, what it takes with it, and the repair:", ""]
        L += lines(rep["failure_modes"]) + [""]
    (outdir / "ASSEMBLY.md").write_text("\n".join(L), encoding="utf-8")
    return {"file": "ASSEMBLY.md", "steps": len(st), "renders": render is not None}


def story_notes(story: dict | None) -> list[str]:
    """ASSEMBLY.md 'When something goes wrong': the use story's accepted failures (what breaks, how to fix it)."""
    acc = (story or {}).get("accepted_failures") or []
    if not acc:
        return []
    return (["## When something goes wrong", "",
             "Designed for: " + f"{story.get('who')}, {', '.join(story.get('where') or [])}, {story.get('how_often')}.", "",
             "These are expected and accepted, not defects:", ""]
            + [f"- **{a['hazard']}**: {a['consequence']}" for a in acc] + [""])


def human_item(it) -> str:
    from .export import human_name
    return human_name(it.spec.get("catalog", ""), "") if it.spec.get("catalog") else "printed"


def _dir_words(d) -> str:
    names = (("+X", "-X"), ("+Y", "-Y"), ("+Z (up)", "-Z (down)"))
    k = int(np.argmax(np.abs(d)))
    return names[k][0 if d[k] > 0 else 1] + ("" if abs(d[k]) > 0.97 else f" ({[round(float(x), 2) for x in d]})")


def fit_notes(proj, rep: dict, iid: str) -> list[str]:
    """Extra lines for fitting one item: its `assembly_note` and the checked `insert` path."""
    out = []
    note = proj.items[iid].spec.get("assembly_note")
    if note:
        out += _split(note)
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
    summary = price_bom(rep.get("bom", []), prices, rep.get("parts", {}), load_inventory())
    write_bom(rep.get("bom", []), summary, outdir)
    from . import firmware
    fw = firmware.write(proj, asm, outdir)        # bring-up / sweep-test program (None: no controller-driven servo)
    return {"bom": summary, "firmware": fw and {"program": fw["program"], "servos": len(fw["rows"])},
            "assembly": write_assembly(proj, asm, rep, outdir, render=render, firmware_info=fw)}
