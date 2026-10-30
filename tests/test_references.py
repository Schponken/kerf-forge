"""references/INDEX.md is the shared library of open designs studied: complete rows, and every design a project's
REFERENCES.md links from a design-hosting site is listed there, so later projects reuse the research."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "references" / "INDEX.md"
DESIGN_HOSTS = ("github.com", "printables.com", "thingiverse.com", "makerworld.com", "myminifactory.com",
                "grabcad.com", "onshape.com", "cults3d.com", "3d.nih.gov")
URL = re.compile(r"https?://[^\s|)>\]]+")


def _tables(text):
    """{section heading: [row cells]} for every markdown table."""
    out, sec = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            sec = line[3:].strip()
        elif line.startswith("|") and not re.match(r"^\|[\s\-|]+\|$", line):
            out.setdefault(sec, []).append([c.strip() for c in line.strip().strip("|").split("|")])
    return {k: v[1:] for k, v in out.items()}  # drop header rows


def _norm(u):
    return u.rstrip("/.,;").lower().replace("http://", "https://").removesuffix(".git")


def test_index_rows_complete():
    t = _tables(INDEX.read_text(encoding="utf-8"))
    rows = t["Designs"]
    assert len(rows) >= 10
    evals = {p.name for p in (ROOT / "evals").iterdir() if p.is_dir()} | {"general"}
    for r in rows:
        assert len(r) == 6 and all(r), f"incomplete row: {r[:1]}"
        design, link, lic, dims, lessons, ev = r
        assert URL.search(link), f"{design}: no link"
        assert re.search(r"\d", dims) or "none published" in dims, f"{design}: key dimensions need numbers (or say none published)"
        assert re.search(r"\b(read|measured)\b", dims, re.I), f"{design}: say whether dimensions were read or measured"
        assert ev in evals, f"{design}: eval '{ev}' unknown"
    names = [r[0] for r in rows]
    assert len(names) == len(set(names)), "duplicate designs"


def test_project_design_links_are_indexed():
    indexed = {_norm(u) for u in URL.findall(INDEX.read_text(encoding="utf-8"))}
    missing = []
    for ref in (ROOT / "projects").glob("*/REFERENCES.md"):
        for u in URL.findall(ref.read_text(encoding="utf-8")):
            if any(h in u for h in DESIGN_HOSTS) and not any(_norm(u).startswith(i) or i.startswith(_norm(u)) for i in indexed):
                missing.append(f"{ref.parent.name}: {u}")
    assert not missing, f"add these designs to references/INDEX.md: {missing}"
