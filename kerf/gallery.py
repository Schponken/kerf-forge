"""One gallery page for every project: status (build, review, eval), key numbers, renders, the 3D viewer and the BOM.

    kerf gallery            -> out/gallery/index.html + out/gallery/<project>/{viewer.html, assembly.jpg, exploded.jpg}
                               + out/gallery/files.json (published path -> source, for the Artifact tool's `files`)

Built from each project's out/ (run `kerf build <p>` first; projects without a build are listed as not built).
index.html is page content only (the Artifact tool adds the document skeleton); the viewers are full documents.
"""
from __future__ import annotations

import datetime as _dt
import html
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "gallery"
IMG_W = 1400


def _jpg(src: Path, dest: Path) -> bool:
    if not src.exists():
        return False
    from PIL import Image
    im = Image.open(src).convert("RGB")
    if im.width > IMG_W:
        im = im.resize((IMG_W, round(im.height * IMG_W / im.width)), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=82, optimize=True)
    return True


def collect(name: str, evals: dict) -> dict:
    """Everything the page shows about one project, from project.yaml, out/report.json, the review and the eval."""
    from . import cli, project as P
    d = ROOT / "projects" / name
    data = yaml.safe_load((d / "project.yaml").read_text(encoding="utf-8")) or {}
    rp = d / "out" / "report.json"
    rep = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else None
    fp = P.load(name).fingerprint()
    built = bool(rep) and rep.get("fingerprint") == fp and bool(rep.get("files"))
    rv = cli.review_status(name)
    ev = evals.get(name)
    info = {"name": name, "title": data.get("name", name), "description": " ".join(str(data.get("description", "")).split()),
            "built": built, "ok": bool(rep and rep.get("ok")) and built, "review": rv["ok"], "review_why": rv.get("why", ""),
            "eval": None if ev is None else ev["ok"], "eval_fail": [] if ev is None else ev["failures"][:3],
            "fingerprint": fp, "parts": [], "purchased": 0, "mass_g": None, "plates": 0, "bom_total": None,
            "requirements": [], "bom": []}
    if not rep:
        return info
    info["parts"] = list(rep.get("parts", {}))
    info["purchased"] = sum(int(v.get("qty", 1)) for v in rep.get("purchased", {}).values())
    m = sum(float(p.get("mass_est_g") or 0) for p in rep.get("parts", {}).values())
    m += sum(float(v.get("mass_g") or 0) * int(v.get("qty", 1)) for v in rep.get("purchased", {}).values())
    info["mass_g"] = round(m)
    files = rep.get("files") or {}
    info["plates"] = len(files.get("plates") or [])
    info["bom_total"] = ((files.get("ship") or {}).get("bom") or {}).get("total_usd")
    for r in rep.get("requirements", []):
        info["requirements"].append({"id": r["id"], "check": r.get("check", ""), "ok": r.get("ok"),
                                     "value": r.get("value"), "limit": r.get("limit"), "skipped": r.get("skipped", False)})
    info["bom"] = [{k: b.get(k) for k in ("type", "item", "qty", "spec", "buy", "total_usd")} for b in rep.get("bom", [])]
    return info


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.3g}" if abs(v) < 1000 else f"{v:.0f}"
    if isinstance(v, list):
        return "–".join("…" if x is None else _fmt(x) for x in v)
    return "–" if v is None else str(v)


def _chip(state, yes, no, unknown="n/a"):
    cls = {True: "ok", False: "bad", None: "na"}[state]
    return f'<span class="chip {cls}">{html.escape({True: yes, False: no, None: unknown}[state])}</span>'


def page(projects: list[dict], when: str) -> str:
    e = html.escape
    rows, sections = [], []
    for p in projects:
        n = p["name"]
        rows.append(
            f'<tr><td><a href="#{e(n)}">{e(p["title"])}</a><div class="sub mono">{e(n)}</div></td>'
            f'<td>{_chip(p["ok"] if p["built"] else None, "PASS", "FAIL", "not built")}</td>'
            f'<td>{_chip(p["review"], "PASS", "pending")}</td>'
            f'<td>{_chip(p["eval"], "PASS", "open", "seed")}</td>'
            f'<td class="num">{len(p["parts"])}</td><td class="num">{p["purchased"]}</td>'
            f'<td class="num">{_fmt(p["mass_g"])}</td><td class="num">{p["plates"]}</td>'
            f'<td class="num">{"–" if p["bom_total"] is None else f"${p["bom_total"]:.2f}"}</td></tr>')
        reqs = "".join(
            f'<li class="{"skip" if r["skipped"] else ("ok" if r["ok"] else "bad")}"><span class="mono">{e(r["id"])}</span>'
            f'<span class="rq-check">{e(r["check"])}</span><span class="mono rq-val">'
            f'{"skipped" if r["skipped"] else e(_fmt(r["value"]))} <span class="lim">/ {e(_fmt(r["limit"]))}</span></span></li>'
            for r in p["requirements"])
        bom = "".join(
            f'<tr><td>{e(str(b["type"] or ""))}</td><td>{e(str(b["item"] or ""))}</td><td class="num">{e(_fmt(b["qty"]))}</td>'
            f'<td>{e(str(b["spec"] or ""))}</td><td>{f"<a href=\"{e(b["buy"])}\">buy</a>" if b.get("buy") else ""}</td>'
            f'<td class="num">{"" if b.get("total_usd") in (None, "") else f"${float(b["total_usd"]):.2f}"}</td></tr>'
            for b in p["bom"])
        pics = "".join(f'<figure><img src="{e(n)}/{k}.jpg" alt="{e(p["title"])}: {k} view sheet" loading="lazy">'
                       f'<figcaption>{k}</figcaption></figure>' for k in ("assembly", "exploded") if p.get(f"img_{k}"))
        notes = ""
        if not p["review"]:
            notes += f'<p class="note">Review: {e(p["review_why"])}</p>'
        if p["eval"] is False:
            notes += "".join(f'<p class="note">Eval: {e(f)}</p>' for f in p["eval_fail"])
        viewer = (f'<a class="btn" href="{e(n)}/viewer.html" target="_blank" rel="noopener">Open 3D viewer</a>'
                  if p.get("viewer") else '<span class="sub">no viewer yet (not built)</span>')
        sections.append(f"""
<section class="proj" id="{e(n)}">
  <header class="proj-head">
    <div><h2>{e(p["title"])}</h2><p class="desc">{e(p["description"])}</p></div>
    <div class="proj-actions">{viewer}</div>
  </header>
  {notes}
  <div class="pics">{pics or '<p class="sub">No renders yet.</p>'}</div>
  <div class="split">
    <div class="block"><h3>Requirements <span class="sub">value / limit</span></h3><ul class="reqs">{reqs or '<li class="skip">none recorded</li>'}</ul></div>
    <details class="block"><summary><h3>Bill of materials</h3><span class="sub">{len(p["bom"])} rows{"" if p["bom_total"] is None else f", ${p["bom_total"]:.2f}"}</span></summary>
      <div class="scroll"><table class="bom"><thead><tr><th>type</th><th>item</th><th>qty</th><th>spec</th><th></th><th>total</th></tr></thead><tbody>{bom}</tbody></table></div>
    </details>
  </div>
</section>""")
    return f"""<title>Kerf Forge Gallery</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500&display=swap">
<style>
/* layout: a build sheet — status table up top, then one plate per project (renders, requirements, BOM) */
:root {{
  --bg: #f3f4f1; --panel: #ffffff; --ink: #1d2226; --muted: #5d666b; --rule: #d6dad5; --accent: #1f6f8b;
  --ok: #2e7d4f; --ok-bg: #e2f1e7; --bad: #a33a2a; --bad-bg: #f8e4df; --na: #6b7175; --na-bg: #e8eae8;
  --display: "IBM Plex Sans Condensed", "Arial Narrow", sans-serif; --body: "IBM Plex Sans", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #15191b; --panel: #1d2326; --ink: #e6e9e7; --muted: #9aa3a6; --rule: #2f383c; --accent: #6cb6cf;
  --ok: #7fd09d; --ok-bg: #1f3428; --bad: #f09a88; --bad-bg: #3a221d; --na: #a3a9ac; --na-bg: #2a3033; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --bg: #15191b; --panel: #1d2326; --ink: #e6e9e7; --muted: #9aa3a6; --rule: #2f383c; --accent: #6cb6cf;
  --ok: #7fd09d; --ok-bg: #1f3428; --bad: #f09a88; --bad-bg: #3a221d; --na: #a3a9ac; --na-bg: #2a3033; color-scheme: dark }}
body {{ background: var(--bg); color: var(--ink); font: 15px/1.55 var(--body);
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 28px 64px; }}
main {{ max-width: 1120px; margin: 0 auto; display: grid; gap: 28px; }}
a {{ color: var(--accent); }} a:focus-visible, summary:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
h1, h2, h3 {{ font-family: var(--display); font-weight: 600; text-wrap: balance; margin: 0; }}
h1 {{ font-size: clamp(28px, 4.5vw, 40px); letter-spacing: .01em; }}
h2 {{ font-size: 24px; }} h3 {{ font-size: 15px; text-transform: uppercase; letter-spacing: .08em; }}
.mono {{ font-family: var(--mono); font-size: 13px; }} .sub {{ color: var(--muted); font-size: 13px; }}
.lede {{ max-width: 68ch; color: var(--muted); margin: 6px 0 0; }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }}
th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--rule); vertical-align: top; }}
th {{ font: 500 12px var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }}
td.num, th.num {{ text-align: right; font-family: var(--mono); font-size: 13px; }}
.status {{ background: var(--panel); border: 1px solid var(--rule); border-radius: 6px; }}
.chip {{ display: inline-block; font: 500 12px var(--mono); padding: 2px 8px; border-radius: 999px; white-space: nowrap; }}
.chip.ok {{ color: var(--ok); background: var(--ok-bg); }} .chip.bad {{ color: var(--bad); background: var(--bad-bg); }}
.chip.na {{ color: var(--na); background: var(--na-bg); }}
.proj {{ border-top: 2px solid var(--ink); padding-top: 18px; display: grid; gap: 16px; scroll-margin-top: 16px; }}
.proj-head {{ display: flex; flex-wrap: wrap; gap: 12px 24px; justify-content: space-between; align-items: flex-start; }}
.proj-head > div:first-child {{ min-width: 0; flex: 1 1 420px; }}
.desc {{ margin: 6px 0 0; max-width: 72ch; color: var(--muted); }}
.btn {{ display: inline-block; font: 500 14px var(--body); color: var(--bg); background: var(--accent); padding: 8px 14px;
  border-radius: 4px; text-decoration: none; }}
.note {{ margin: 0; font-size: 13px; color: var(--bad); }}
.pics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 12px; }}
figure {{ margin: 0; background: var(--panel); border: 1px solid var(--rule); border-radius: 6px; overflow: hidden; }}
figure img {{ display: block; width: 100%; height: auto; }}
figcaption {{ font: 12px var(--mono); color: var(--muted); padding: 6px 10px; text-transform: uppercase; letter-spacing: .06em; }}
.split {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 380px), 1fr)); gap: 16px; align-items: start; }}
.block {{ min-width: 0; display: grid; gap: 8px; }}
summary {{ cursor: pointer; display: flex; gap: 10px; align-items: baseline; list-style: none; }}
summary::-webkit-details-marker {{ display: none; }} summary::before {{ content: "+"; font-family: var(--mono); color: var(--accent); }}
details[open] summary::before {{ content: "−"; }}
.reqs {{ list-style: none; margin: 0; padding: 0; display: grid; }}
.reqs li {{ display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr) auto; gap: 8px; padding: 6px 0 6px 10px;
  border-bottom: 1px solid var(--rule); border-left: 3px solid var(--na); align-items: baseline; }}
.reqs li.ok {{ border-left-color: var(--ok); }} .reqs li.bad {{ border-left-color: var(--bad); }}
.rq-check {{ color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }} .rq-val {{ text-align: right; }} .lim {{ color: var(--muted); }}
.bom td {{ font-size: 13px; }}
footer {{ color: var(--muted); font-size: 13px; }}
@media (prefers-reduced-motion: reduce) {{ * {{ scroll-behavior: auto !important; }} }}
</style>
<main>
  <header>
    <h1>Kerf Forge Gallery</h1>
    <p class="lede">Every Kerf Forge design so far: what it is, whether it builds, passed its independent review and its eval, and what it costs to buy and print. Open a 3D viewer to move the joints, explode the assembly and click a face to see which part file made it.</p>
  </header>
  <div class="status scroll"><table>
    <thead><tr><th>project</th><th>build</th><th>review</th><th>eval</th><th class="num">printed</th><th class="num">bought</th><th class="num">mass g</th><th class="num">plates</th><th class="num">BOM</th></tr></thead>
    <tbody>{"".join(rows)}</tbody></table></div>
  {"".join(sections)}
  <footer>Generated by <span class="mono">kerf gallery</span> on {e(when)} from each project's last <span class="mono">kerf build</span>. Mass = printed parts (estimated from geometry and infill) + purchased parts (catalog). BOM totals are a dated price snapshot without shipping.</footer>
</main>
"""


def build(names: list[str] | None = None, out: Path = OUT, when: str | None = None) -> dict:
    """Write the gallery into `out`; returns {"index": path, "files": {published path: source path}, "projects": [...]}."""
    from . import cli
    names = names or cli.projects()
    try:
        from evals import run_evals
        evals = {e["id"]: e for e in run_evals.run_all()}
    except Exception:  # noqa: BLE001 — the gallery still shows builds and reviews
        evals = {}
    out.mkdir(parents=True, exist_ok=True)
    files, infos = {}, []
    for n in names:
        p = collect(n, evals)
        od = ROOT / "projects" / n / "out"
        for k, src in (("assembly", od / "renders" / "assembly_sheet.png"), ("exploded", od / "renders" / "exploded_sheet.png")):
            if p["built"] and _jpg(src, out / n / f"{k}.jpg"):
                p[f"img_{k}"] = True
                files[f"{n}/{k}.jpg"] = str(out / n / f"{k}.jpg")
        v = od / "viewer.html"
        if p["built"] and v.exists():
            (out / n).mkdir(parents=True, exist_ok=True)
            (out / n / "viewer.html").write_bytes(v.read_bytes())
            files[f"{n}/viewer.html"] = str(out / n / "viewer.html")
            p["viewer"] = True
        infos.append(p)
    idx = out / "index.html"
    idx.write_text(page(infos, when or _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")), encoding="utf-8")
    (out / "files.json").write_text(json.dumps(files, indent=1), encoding="utf-8")
    return {"index": str(idx), "files": files, "projects": infos}
