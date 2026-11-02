"""Sourced hardware inventory from final BOM quantities; deliberately separate from engineering mass/CG.

Stock must be selected explicitly for the exact generated hardware key. No material, screw-length or price-pack
fallback supplies a mass. Unknown hardware remains unknown, including fasteners supplied free with another part.
"""
from __future__ import annotations

import html
import math
from pathlib import Path

from . import catalog

NOTICE = ("Hardware inventory only: generated fasteners are not explicitly included in engineering mass, CG, "
          "inertia, strength or runtime totals. Some supplied hardware may already be in purchased-part weights; "
          "do not add this subtotal blindly.")


def _positive(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite positive number")
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f"{name} must be a finite positive number") from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return value


def _stock_key(e):
    if not isinstance(e, dict):
        raise ValueError("selected stock must be a catalog entry, not a scalar value")
    kind, size = e.get("kind"), e.get("size")
    if kind == "screw" and e.get("head") in ("socket", "flat"):
        length = _positive(e.get("length_mm"), "stock length_mm")
        return f"screw:{size}x{length:g}:{e['head']}"
    if kind == "insert":
        length = _positive(e.get("length_mm"), "insert length_mm")
        expected = catalog.num(catalog.get(f"fdm_holes.{size}"), "heatset_length")
        if length != expected:
            raise ValueError(f"insert length {length:g} mm does not match the catalog fit's {expected:g} mm")
        return f"insert:{size}"
    if kind == "nut":
        return f"nut:{size}"
    raise ValueError("stock must describe a screw (socket/flat), insert or nut matching the generated hardware")


def inventory(rows, stock=None):
    """Classify the final BOM hardware quantities; total_g is null if any row is unknown/invalid.

    Each stock entry is a catalog path, keyed by an exact generated hardware_key. The source catalog entry records
    reported_mass_g / reported_qty, mass_kind (vendor-published | measured | estimated), source and mass_basis.
    Quantities are the pieces in the final BOM, never the vendor's pack size or the number of stock mappings.
    """
    problems, warnings, records, used = [], [], [], set()
    if stock is None:
        stock = {}
    if not isinstance(stock, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not v.strip()
                                          for k, v in stock.items()):
        problems.append("fastener_stock must map exact generated hardware keys to nonempty catalog paths")
        stock = {}
    subtotals = {k: 0.0 for k in ("vendor-published", "measured", "estimated")}
    for index, row in enumerate(rows):
        if row.get("type") not in ("fastener", "pin", "hardware"):
            continue
        key = row.get("hardware_key")
        record = {"row": index, "item": row["item"], "qty": row.get("qty"), "hardware_key": key,
                  "status": "unknown", "unit_g": None, "total_g": None,
                  "included_for_cost": bool(row.get("included")), "source": None, "basis": None}
        records.append(record)
        try:
            qty = _positive(row.get("qty"), f"{row['item']} quantity")
            if not qty.is_integer():
                raise ValueError("hardware quantity must be an integer number of pieces")
            if key is None:
                record["reason"] = "No exact supported generated hardware identity; supply dimensional evidence first"
                continue
            if key not in stock:
                record["reason"] = f"No stock selected for {key}; choose a sourced catalog entry in fastener_stock"
                continue
            used.add(key)
            path = stock[key]
            e = catalog.get(path)
            if _stock_key(e) != key:
                raise ValueError(f"selected stock {path} does not match type/size/head/length of {key}")
            kind = e.get("mass_kind")
            if kind not in subtotals:
                raise ValueError("stock mass_kind must be vendor-published, measured or estimated")
            if any(not isinstance(e.get(k), str) or not e[k].strip() for k in ("source", "mass_basis")):
                raise ValueError("stock needs a source and mass_basis explaining the measurement or estimate")
            reported = _positive(e.get("reported_mass_g"), "stock reported_mass_g")
            count = _positive(e.get("reported_qty"), "stock reported_qty")
            if not count.is_integer():
                raise ValueError("stock reported_qty must count whole hardware pieces")
            unit = reported / count
            total = unit * qty
            if not math.isfinite(total) or total <= 0:
                raise ValueError("stock mass arithmetic must produce a finite positive total")
            record.update(status=kind, unit_g=unit, total_g=total, catalog=path, source=e["source"],
                          basis=e["mass_basis"], reported_mass_g=reported, reported_qty=count)
            subtotals[kind] += total
        except (ValueError, TypeError, KeyError, OverflowError) as e:
            record["reason"] = str(e)
            problems.append(f"{row['item']}: {e}")
    for key in sorted(set(stock) - used):
        warnings.append(f"fastener_stock {key!r} was not used by this generated hardware inventory")
    known = sum(subtotals.values())
    if not math.isfinite(known):
        problems.append("hardware mass subtotal overflowed; check stock masses and quantities")
        known = None
        subtotals = {k: v if math.isfinite(v) else None for k, v in subtotals.items()}
    unknown = [r["item"] for r in records if r["status"] == "unknown"]
    return {"evaluated": True, "rows": records, "subtotals_g": subtotals, "known_g": known,
            "total_g": known if not unknown and not problems else None, "unknown": unknown,
            "complete": not unknown and not problems, "problems": problems, "warnings": warnings,
            "included_in_engineering_totals": False, "notice": NOTICE}


def annotate(rows, result):
    """Expose mass status in existing BOM notes, which also survive ship.write_bom's pricing pass."""
    for record in result["rows"]:
        row = rows[record["row"]]
        mass = (f"{record['unit_g']:g} g each / {record['total_g']:g} g for this row ({record['status']})"
                if record["total_g"] is not None else f"unknown ({record['reason']})")
        row["note"] = (row.get("note", "") + f"; hardware mass: {mass}; inventory only, see FASTENER_MASS.md").lstrip("; ")


def write(result, outdir):
    """A readable companion to report.json; source precision and missing rows remain visible."""
    lines = ["# Fastener mass inventory", "", NOTICE, "", "| Hardware | Qty | Mass per piece | Row mass | Status / evidence |",
             "|---|---:|---:|---:|---|"]
    def cell(value):
        return html.escape(str(value)).replace("|", "\\|").replace("\r", " ").replace("\n", " ")
    for r in result["rows"]:
        unit = "unknown" if r["unit_g"] is None else f"{r['unit_g']:g} g"
        total = "unknown" if r["total_g"] is None else f"{r['total_g']:g} g"
        evidence = r.get("reason") or (f"{r['status']}: {r['basis']}; {r['source']}")
        lines.append(f"| {cell(r['item'])} | {cell(r['qty'])} | {unit} | {total} | {cell(evidence)} |")
    lines += ["", "Subtotals (distinct evidence categories):"]
    lines += [f"- {kind}: {'unknown' if value is None else f'{value:g} g'}" for kind, value in result["subtotals_g"].items()]
    lines += ["", f"Total hardware inventory: {'unknown — missing/invalid rows remain' if result['total_g'] is None else str(result['total_g']) + ' g'}."]
    lines += [f"- Problem: {cell(p)}" for p in result["problems"]]
    lines += [f"- Note: {cell(p)}" for p in result["warnings"]]
    (Path(outdir) / "FASTENER_MASS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
