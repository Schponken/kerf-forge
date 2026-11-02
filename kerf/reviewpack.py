"""Review pack: what the design-reviewer subagent needs, in a fraction of the tokens.

A review used to read report.json whole (up to 160 kB), catalog/hardware.json whole (140 kB) and every render one by
one (35-60 PNGs, many of them the single views that the *_sheet.png files already combine) - about 150k tokens a
review. `kerf build` now also writes out/review/:
- PACK.md: the report digested (requirements with value / limit / FEA peak and deflection, problems, warnings, each
  part's print and stress summary, declared sharp corners with their reasons, the fastener lengths), the files that
  changed since the last review, and which renders exist;
- catalog.json: only the catalog entries this project's items use;
- contact_*.png: the FEA plots, poses and keep-outs on a few labelled sheets (the assembly, exploded and part sheets
  are already one image each).
The reviewer starts from these and opens a single render, report.json section or catalog entry only when the pack
points at something to check (.claude/agents/design-reviewer.md).
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

THUMB_W = 420          # contact-sheet cell width (px); 3 columns -> 1260 px wide sheets
COLS, ROWS = 3, 3      # cells per contact sheet


def _short(s: str, n: int = 240) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _peak(detail: str) -> str:
    m = re.search(r"peak ([\d.]+) MPa at (\[[^\]]*\])", detail or "")
    d = re.search(r"deflection ([\d.]+) mm( \(limit [\d.]+\))?", detail or "")
    out = []
    if m:
        out.append(f"peak {m.group(1)} MPa at {m.group(2)}")
    if d:
        out.append(f"defl {d.group(1)} mm{d.group(2) or ''}")
    return "; ".join(out)


def _changed_since_review(proj_dir: Path) -> list[str]:
    """Files of the project changed since just before the commit that last wrote its review.json (empty if never
    reviewed)."""
    root = proj_dir.parent.parent
    rel = proj_dir.relative_to(root)
    try:
        last = subprocess.run(["git", "log", "-1", "--format=%H", "--", str(rel / "review.json")], cwd=root,
                              capture_output=True, text=True, timeout=30).stdout.strip()
        if not last:
            return []
        # from the commit BEFORE the one that wrote the review: a review is often committed together with its fixes
        out = subprocess.run(["git", "diff", "--stat", last + "^", "--", str(rel), f":(exclude){rel}/out",
                              f":(exclude){rel}/review.json"], cwd=root,
                             capture_output=True, text=True, timeout=30).stdout.strip().splitlines()
        return out
    except Exception:  # noqa: BLE001 - no git: the pack just leaves the section out
        return []


def catalog_subset(proj) -> dict:
    """{catalog path: entry} for every item that names a catalog entry (servos, horns, boards, fasteners' screws)."""
    from . import catalog
    out = {}
    for it in proj.items.values():
        key = it.spec.get("catalog")
        if key and key not in out:
            try:
                out[key] = catalog.get(key)
            except Exception:  # noqa: BLE001
                pass
    return out


def contact_sheets(renders: Path, outdir: Path) -> list[str]:
    """FEA plots, poses and keep-outs as labelled grids; returns the sheet file names."""
    from PIL import Image, ImageDraw, ImageOps
    picks = sorted(p for p in renders.glob("*.png")
                   if p.name.startswith(("fea_", "pose_", "keepouts_")) and "_sheet" not in p.name)
    names = []
    per = COLS * ROWS
    for k in range(0, len(picks), per):
        cells = []
        for p in picks[k:k + per]:
            im = Image.open(p).convert("RGB")
            box = ImageOps.invert(im).getbbox()          # trim the plots' white margins before shrinking
            if box:
                im = im.crop(box)
            im.thumbnail((THUMB_W, THUMB_W * 2))
            cells.append((p.stem, im))
        h = max(im.height for _, im in cells) + 22
        rows = (len(cells) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * THUMB_W, rows * h), "white")
        d = ImageDraw.Draw(sheet)
        for i, (name, im) in enumerate(cells):
            x, y = (i % COLS) * THUMB_W, (i // COLS) * h
            sheet.paste(im, (x, y + 20))
            d.text((x + 4, y + 4), name, fill="black")
        n = f"contact_{k // per + 1}.png"
        sheet.save(outdir / n, optimize=True)
        names.append(n)
    return names


def write(proj, rep: dict, outdir: Path) -> Path:
    """out/review/PACK.md + catalog.json + contact sheets. Returns the PACK.md path."""
    rd = outdir / "review"
    rd.mkdir(parents=True, exist_ok=True)
    for old in rd.glob("contact_*.png"):
        old.unlink()
    L = [f"# Review pack — {rep.get('project', proj.name)}", "",
         f"Fingerprint `{rep.get('fingerprint')}`; build {'PASS' if rep.get('ok') else 'FAIL'} "
         f"({rep.get('seconds', 0):.0f} s). Full data: out/report.json (open a section only when this pack points at it).", ""]
    if rep.get("problems"):
        L += ["## Problems", ""] + [f"- {_short(p, 400)}" for p in rep["problems"]] + [""]
    L += ["## Requirements", "", "| id | check | value | limit | ok | FEA / note |", "|---|---|---|---|---|---|"]
    for q in rep.get("requirements", []):
        lim = q.get("limit")
        L.append(f"| {q.get('id')} | {q.get('check')} | {q.get('value')} {q.get('unit', '') or ''} | "
                 f"{'' if lim is None else lim} {q.get('bound', '') or ''} | {'ok' if q.get('ok') else 'BAD'} | "
                 f"{_peak(q.get('detail', '')) or _short(q.get('detail', ''), 120)} |")
    L += ["", "## Warnings", ""] + [f"- {_short(w)}" for w in dict.fromkeys(rep.get("warnings", []))] + [""]
    L += ["## Parts", "", "| part | material | print_rot | size mm | mass g | overhang % | thinnest wall mm | stress use (peak) | "
          "cold vol % | sharp corners left / declared |", "|---|---|---|---|---|---|---|---|---|---|"]
    for pid, p in rep.get("parts", {}).items():
        st = p.get("stress") or {}
        L.append(f"| {pid} | {p.get('material')} | {p.get('print_rot')} | {p.get('size_mm')} | {p.get('mass_est_g')} | "
                 f"{p.get('overhang_pct')} | {p.get('wall_p02_mm')} | {st.get('utilisation', '-')} | "
                 f"{st.get('cold_volume_pct', '-')} | {len(p.get('sharp_inside') or [])} / {len(p.get('sharp_kept') or [])} |")
    hot = [(pid, z) for pid, p in rep.get("parts", {}).items() for z in ((p.get("stress") or {}).get("hot_zones") or [])]
    if hot:
        L += ["", "Hot zones (top 3 per part, utilisation of the allowable): "
              + "; ".join(f"{pid} {z['at']} peak {z['peak']}" for pid, z in hot)]
    kept = [(pid, k) for pid, p in rep.get("parts", {}).items() for k in (p.get("sharp_kept") or [])]
    if kept:
        L += ["", "## Corners declared sharp (judge each reason)", ""]
        by = {}
        for pid, k in kept:
            by.setdefault((pid, k.get("why", "")), []).append(k.get("at"))
        L += [f"- {pid}: {len(ats)} x {why} — e.g. {ats[0]}" for (pid, why), ats in by.items()]
    fast = (rep.get("assembly") or {}).get("fasteners") or []
    if fast:
        L += ["", "## Fasteners", "", "| group | screw | length mm | grip mm | head / receiver |", "|---|---|---|---|---|"]
        seen = {}
        for f in fast:
            k = (f.get("group"), f.get("screw"), f.get("length_mm"), f.get("grip_mm"), f.get("head"), f.get("receiver"))
            seen[k] = seen.get(k, 0) + 1
        L += [f"| {g} | {n} x {s} | {ln} | {gr} | {h} / {rc} |" for (g, s, ln, gr, h, rc), n in seen.items()]
    ch = _changed_since_review(Path(proj.dir))
    L += ["", "## Changed since the last review", ""] + ([f"    {c.strip()}" for c in ch] if ch else ["(never reviewed, or no git)"])
    cat = catalog_subset(proj)
    (rd / "catalog.json").write_text(json.dumps(cat, indent=1), encoding="utf-8")
    renders = outdir / "renders"
    sheets = contact_sheets(renders, rd) if renders.exists() else []
    allr = sorted(p.name for p in renders.glob("*.png")) if renders.exists() else []
    L += ["", "## Renders", "",
          "Look at these first: " + ", ".join(f"renders/{n}" for n in allr if n.endswith("_sheet.png"))
          + (", and " + ", ".join(f"review/{n}" for n in sheets) + " (FEA plots, poses, keep-outs)" if sheets else "") + ".",
          "The single views (" + str(sum(1 for n in allr if not n.endswith("_sheet.png"))) + " files: *_iso, *_front, ...) "
          "repeat the sheets at full size: open one only to check a detail.", "",
          f"Catalog entries this project uses: review/catalog.json ({len(cat)} entries; catalog/hardware.json has them all)."]
    f = rd / "PACK.md"
    f.write_text("\n".join(L) + "\n", encoding="utf-8")
    return f
