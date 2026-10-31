"""Search-first: before a part is designed, look for an existing design that already does the job.

    kerf find "608 bearing pulley" --project robot_arm        # writes a candidates table into REFERENCES.md

Sources by what they allow:
- Printables: public GraphQL (no key). Name, license, author, likes/downloads, files; the top candidates' STL files
  are downloaded and measured (bounding box per file = the key dimensions to compare against the contract).
- Thingiverse: official REST API, needs an app token in THINGIVERSE_TOKEN (thingiverse.com/developers, free).
  Without it the source is listed as skipped with that instruction; the site itself sits behind a bot wall.
- MakerWorld, GrabCAD: no public API and both refuse scripted requests; the section lists the exact web searches for
  the design-researcher subagent (WebSearch + WebFetch), which adds what it finds with `kerf find --add`.
- McMaster-Carr: blocks automated downloads; for purchased hardware the section gives the search link and asks
  Spencer to download the part's STEP into catalog/models/ (see catalog/models/SOURCES.md).

Every search gets a "Decision:" line the designer fills in (reuse / adapt / design new, and why). `kerf check`
warns while a decision is still TODO (pending_decisions).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

UA = "kerf-forge/1.0 (+https://github.com/Schponken/kerf-forge)"
PRINTABLES_API = "https://api.printables.com/graphql/"
THINGIVERSE_API = "https://api.thingiverse.com"
MAX_STL_BYTES = 25_000_000
SECTION = "## Existing designs (kerf find)"
TODO = "Decision: TODO"


# ---------------------------------------------------------------- http (monkeypatched in tests)
def _post_json(url, payload, headers=None, timeout=30):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"content-type": "application/json", "user-agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _get_json(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers={"user-agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _download(url, dest: Path, timeout=60) -> Path:
    req = urllib.request.Request(url, headers={"user-agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        n = int(r.headers.get("content-length") or 0)
        if n > MAX_STL_BYTES:
            raise ValueError(f"file is {n / 1e6:.0f} MB (> {MAX_STL_BYTES / 1e6:.0f} MB), not measured")
        data = r.read(MAX_STL_BYTES + 1)
    if len(data) > MAX_STL_BYTES:
        raise ValueError("file too large, not measured")
    dest.write_bytes(data)
    return dest


# ---------------------------------------------------------------- licenses
def license_use(lic: str) -> str:
    """What Kerf may do with a design under this license (Spencer prints for himself; designs may be shared)."""
    l = (lic or "").upper().replace("CREATIVE COMMONS", "CC").replace("—", "-").replace(" ", "-")
    if not l or l in ("NONE", "UNKNOWN", "-"):
        return "reference only (no license stated)"
    if "SDFL" in l or "STANDARD-DIGITAL" in l or "ALL-RIGHTS" in l:
        return "print as-is only (no remix)"
    if "ND" in l.split("-") or "NODERIVATIVES" in l or "NO-DERIV" in l:
        return "print as-is only (no remix)"
    nc = "NC" in l.split("-") or "NONCOMMERCIAL" in l
    if any(k in l for k in ("CC0", "PUBLIC-DOMAIN", "MIT", "BSD", "APACHE", "GPL", "CC-BY", "ATTRIBUTION", "CERN")):
        return "adapt OK, credit" + (", non-commercial" if nc else "") + (", share-alike" if "SA" in l.split("-") or "SHARE" in l or "GPL" in l else "")
    return f"check license ({lic})"


# ---------------------------------------------------------------- sources
def printables(query: str, limit: int = 8) -> list[dict]:
    """Printables matches every word, so a long description finds little: if the full query returns fewer than
    `limit`, also try its 3-word windows (at most 3 more requests) and merge, best-first, without duplicates."""
    words = query.split()
    queries = [query] + [" ".join(words[i:i + 3]) for i in range(len(words) - 2)][:3] if len(words) > 3 else [query]
    out, seen = [], set()
    for q in queries:
        for c in _printables_one(q, limit):
            if c["url"] not in seen:
                seen.add(c["url"])
                out.append(c)
        if len(out) >= limit:
            break
    return out[:limit]


def _printables_one(query: str, limit: int) -> list[dict]:
    q = ("query($q: String!, $n: Int!) { searchPrints2(query: $q, limit: $n) { items { id name slug summary "
         "likesCount downloadCount license { name abbreviation } user { publicUsername } stls { id name fileSize } } } }")
    resp = _post_json(PRINTABLES_API, {"query": q, "variables": {"q": query, "n": limit}})
    if resp.get("errors"):
        raise RuntimeError(f"Printables: {resp['errors'][0].get('message')}")
    out = []
    for it in resp["data"]["searchPrints2"]["items"]:
        lic = (it.get("license") or {}).get("abbreviation") or (it.get("license") or {}).get("name") or ""
        out.append({"source": "Printables", "title": it["name"], "url": f"https://www.printables.com/model/{it['id']}-{it['slug']}",
                    "license": lic, "use": license_use(lic), "author": (it.get("user") or {}).get("publicUsername", ""),
                    "popularity": f"{it.get('likesCount', 0)} likes, {it.get('downloadCount', 0)} downloads",
                    "summary": (it.get("summary") or "").strip()[:140],
                    "_printables": {"id": it["id"], "stls": [s for s in (it.get("stls") or []) if s["name"].lower().endswith(".stl")]}})
    return out


def _printables_link(print_id, file_id) -> str:
    q = ("mutation($id: ID!, $p: ID!) { getDownloadLink(id: $id, printId: $p, fileType: stl, source: model_detail) "
         "{ ok output { link } } }")
    d = _post_json(PRINTABLES_API, {"query": q, "variables": {"id": str(file_id), "p": str(print_id)}})
    r = (d.get("data") or {}).get("getDownloadLink") or {}
    if not r.get("ok"):
        raise RuntimeError("Printables refused the download link")
    return r["output"]["link"]


def measure_stl(path: Path) -> dict:
    import trimesh
    m = trimesh.load(str(path), force="mesh")
    if getattr(m, "extents", None) is None or len(m.faces) == 0:
        raise ValueError("not a mesh file")
    ext = [round(float(x), 1) for x in sorted(m.extents, reverse=True)]
    return {"bbox_mm": ext, "watertight": bool(m.is_watertight)}


def measure_printables(c: dict, max_files: int = 3) -> None:
    """Download up to max_files STLs of a Printables candidate and record their bounding boxes in c['dims']."""
    dims = []
    with tempfile.TemporaryDirectory() as td:
        for s in c["_printables"]["stls"][:max_files]:
            if s.get("fileSize", 0) > MAX_STL_BYTES:
                dims.append(f"{s['name']}: {s['fileSize'] / 1e6:.0f} MB, not measured")
                continue
            try:
                f = _download(_printables_link(c["_printables"]["id"], s["id"]), Path(td) / "m.stl")
                m = measure_stl(f)
                dims.append(f"{s['name']}: {' x '.join(f'{v:g}' for v in m['bbox_mm'])} mm")
            except Exception as e:  # noqa: BLE001 — one bad file must not lose the rest
                dims.append(f"{s['name']}: not measured ({e if isinstance(e, ValueError) else type(e).__name__})")
    c["dims"] = "; ".join(dims) if dims else "no STL files"


def thingiverse(query: str, limit: int = 8, token: str | None = None) -> list[dict]:
    token = token or os.environ.get("THINGIVERSE_TOKEN")
    if not token:
        raise PermissionError("set THINGIVERSE_TOKEN (free app token from https://www.thingiverse.com/developers) "
                              "to search Thingiverse; its website blocks scripted access")
    h = {"Authorization": f"Bearer {token}"}
    d = _get_json(f"{THINGIVERSE_API}/search/{urllib.parse.quote(query)}?type=things&per_page={limit}", h)
    hits = d.get("hits", d if isinstance(d, list) else [])
    out = []
    for t in hits[:limit]:
        try:
            lic = _get_json(f"{THINGIVERSE_API}/things/{t['id']}", h).get("license", "")
        except Exception:  # noqa: BLE001
            lic = ""
        out.append({"source": "Thingiverse", "title": t.get("name", ""), "url": t.get("public_url", f"https://www.thingiverse.com/thing:{t['id']}"),
                    "license": lic, "use": license_use(lic), "author": (t.get("creator") or {}).get("name", ""),
                    "popularity": f"{t.get('like_count', 0)} likes", "summary": ""})
    return out


def web_queries(query: str) -> list[str]:
    """Searches the design-researcher runs with WebSearch for sites without an API (then `kerf find --add`)."""
    return [f"site:makerworld.com {query}", f"site:grabcad.com/library {query}", f"{query} STEP model site:mcmaster.com"]


def mcmaster_link(query: str) -> str:
    return f"https://www.mcmaster.com/products/{urllib.parse.quote(query.replace(' ', '-').lower())}/"


# ---------------------------------------------------------------- REFERENCES.md
def _row(c: dict) -> str:
    cells = [c.get("source", ""), f"[{c.get('title', '').replace('|', '/')}]({c.get('url', '')})", c.get("license") or "—",
             c.get("use", ""), c.get("dims", "—"), c.get("popularity", "")]
    return "| " + " | ".join(str(x).replace("\n", " ") for x in cells) + " |"


def section(query: str, cands: list[dict], skipped: dict[str, str], date: str | None = None) -> str:
    L = [f"### `kerf find \"{query}\"` ({date or _dt.date.today().isoformat()})", "",
         "| source | design | license | Kerf may | key dimensions (STL bounding boxes) | popularity |",
         "|---|---|---|---|---|---|"]
    L += [_row(c) for c in cands] or ["| — | nothing found | | | | |"]
    L += ["", "Not searched by script (run these, add fits with `kerf find --add`):"]
    L += [f"- {s}: {why}" for s, why in skipped.items()]
    L += [f"- web search: `{q}`" for q in web_queries(query)]
    L += [f"- McMaster-Carr (purchased hardware): {mcmaster_link(query)} — download the part's STEP by hand into "
          "catalog/models/ and list it in catalog/models/SOURCES.md (McMaster blocks automated downloads)", "",
          f"{TODO} — reuse / adapt <which, with credit> / design new, and why (fit to the contract, license, strength).", ""]
    return "\n".join(L)


def write_section(refs: Path, query: str, text: str) -> None:
    """Insert or replace this query's block under the SECTION heading of REFERENCES.md (other content untouched)."""
    s = refs.read_text(encoding="utf-8") if refs.exists() else f"# References\n"
    head = f"### `kerf find \"{query}\"`"
    if SECTION not in s:
        s = s.rstrip("\n") + f"\n\n{SECTION}\n\n"
    start = s.find(head)
    if start >= 0:
        nxt = [i for i in (s.find("\n### ", start + 1), s.find("\n## ", start + 1)) if i >= 0]
        end = min(nxt) + 1 if nxt else len(s)
        old = s[start:end]
        m = re.search(r"^Decision:(?! TODO).*$", old, re.M)        # keep a decision already made
        if m:
            text = text.replace(next(l for l in text.splitlines() if l.startswith(TODO)), m.group(0))
        s = s[:start] + text.rstrip("\n") + "\n\n" + s[end:].lstrip("\n")
    else:
        i = s.find(SECTION) + len(SECTION)
        nxt = s.find("\n## ", i)
        at = nxt + 1 if nxt >= 0 else len(s)
        s = s[:at].rstrip("\n") + "\n\n" + text.rstrip("\n") + "\n\n" + s[at:]
    refs.write_text(s.rstrip("\n") + "\n", encoding="utf-8")


def add(refs: Path, query: str, cand: dict) -> None:
    """Add one hand-found candidate (MakerWorld, GrabCAD, a vendor STEP) to an existing query block."""
    s = refs.read_text(encoding="utf-8")
    head = f"### `kerf find \"{query}\"`"
    start = s.find(head)
    if start < 0:
        raise ValueError(f"no `kerf find \"{query}\"` block in {refs.name}; run kerf find first")
    cand.setdefault("use", license_use(cand.get("license", "")))
    blank = s.find("\n\nNot searched by script", start)
    s = s[:blank] + "\n" + _row(cand) + s[blank:]
    refs.write_text(s.replace("| — | nothing found | | | | |\n", ""), encoding="utf-8")


def pending_decisions(proj_dir: Path) -> list[str]:
    """Queries in REFERENCES.md whose reuse decision is still TODO."""
    f = Path(proj_dir) / "REFERENCES.md"
    if not f.exists():
        return []
    out, q = [], None
    for line in f.read_text(encoding="utf-8").splitlines():
        m = re.match(r'### `kerf find "(.*)"`', line)
        if m:
            q = m.group(1)
        elif line.startswith(TODO) and q:
            out.append(q)
    return out


def find(query: str, project_dir: Path | None = None, limit: int = 8, measure: int = 4, date: str | None = None) -> dict:
    """Search every scriptable source, measure the top `measure` Printables hits, and (with project_dir) write the
    block into its REFERENCES.md. Returns {"candidates": [...], "skipped": {source: why}, "text": section}."""
    cands, skipped = [], {}
    for name, fn in (("Printables", printables), ("Thingiverse", thingiverse)):
        try:
            got = fn(query, limit)
        except PermissionError as e:
            skipped[name] = str(e)
            continue
        except Exception as e:  # noqa: BLE001 — a source being down must not stop the search
            skipped[name] = f"failed ({type(e).__name__}: {str(e)[:120]})"
            continue
        if name == "Printables":
            for c in got[:measure]:
                measure_printables(c)
        cands += got
    for c in cands:
        c.pop("_printables", None)
    text = section(query, cands, skipped, date)
    if project_dir is not None:
        write_section(Path(project_dir) / "REFERENCES.md", query, text)
    return {"candidates": cands, "skipped": skipped, "text": text}
