"""Thought web: a simplified, near-live map of how a design job explores (Studio's "🕸 Thought web").

Built only from what the job already shows the user: its actions (web searches, pages opened, files read and written,
commands run) and the short notes it writes between them. Nothing is taken from hidden reasoning. Fixed rules turn
those into a growing graph:

- the request is the core node;
- each new line of inquiry (a web search, a research sub-task) becomes an IDEA; it branches off the existing idea it
  shares the most words with (Jaccard >= JOIN), else off the core;
- each page opened or reference file read becomes a SOURCE leaf on the idea it serves (the latest one, or the one it
  matches best);
- the job's own notes attach to the idea being worked on (first sentence, plain text, short);
- writing the plan (DESIGN.md) adds a DECISION node; its "options considered" become OPTION nodes, chosen ones glow,
  the others are set aside with their one-line reason; drawing parts and running checks grow the BUILD trunk;
- each idea's state follows its activity: active (touched in the last RECENT steps), pursued (worked on again, or
  has branches), set aside (left alone for IDLE steps).

`from_events(events, request)` is the live version (Studio job events), `from_project(dir)` rebuilds the map of a
finished project from its REFERENCES.md and DESIGN.md.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

JOIN = 0.15         # word overlap needed to grow from an existing idea instead of the core
RECENT = 6          # steps an idea stays "active" after it was touched
IDLE = 15           # steps without a touch before a leaf idea counts as set aside
NOTE_MAX = 110
STOP = set("""a an and are as at be by can do does for from has have how in is it its of on or that the this to was
were what when where which who why will with into than then over under about using use used vs versus best good
make made get your you our we i me my site com www http https html pdf""".split())


def words(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", str(text).lower()) if len(w) > 2 and w not in STOP}


def plain(text: str, n: int = NOTE_MAX) -> str:
    """First sentence of a note, without markdown, code or paths, at most n characters."""
    t = re.sub(r"```.*?```", " ", str(text), flags=re.S)
    t = re.sub(r"`[^`]*`", "", t)
    t = re.sub(r"[*_#>\[\]]", "", t)
    t = re.sub(r"\(?https?://\S+\)?", "", t)
    t = re.sub(r"\S*/\S+\.\w{1,5}\b", "", t)          # file paths
    t = " ".join(t.split())
    m = re.match(r"(.+?[.!?])(\s|$)", t)
    t = m.group(1) if m else t
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def _site(url: str) -> str:
    h = urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


class Web:
    def __init__(self, request: str):
        self.nodes: dict[str, dict] = {}
        self.step = 0
        self.root = self._add("core", None, plain(request, 80) or "Your request", kind="core",
                              detail=" ".join(str(request).split())[:600])   # the whole request, for the readable story
        self.last_idea = self.root
        self.build = None
        self.known = None
        self.seen_src = {}

    # -- graph primitives
    def _add(self, key, parent, label, kind, detail="", url=None):
        nid = f"n{len(self.nodes)}"
        self.nodes[nid] = {"id": nid, "parent": parent, "kind": kind, "label": label, "detail": detail, "url": url,
                           "t": self.step, "touched": self.step, "touches": 1, "words": set(), "notes": [], "state": "active",
                           "reason": ""}
        self.touch(parent)
        return nid

    def touch(self, nid):
        while nid:
            n = self.nodes[nid]
            n["touched"], n["touches"] = self.step, n["touches"] + 1
            nid = n["parent"]

    def _best_idea(self, ws: set):
        best, score = None, 0.0
        for n in self.nodes.values():
            if n["kind"] in ("idea", "option") and n["words"]:
                s = len(ws & n["words"]) / len(ws | n["words"])
                if s > score:
                    best, score = n["id"], s
        return best, score

    # -- what the job does
    def idea(self, text: str, detail: str = ""):
        ws = words(text)
        if not ws:
            return self.last_idea
        best, score = self._best_idea(ws)
        if best and score >= 0.9:                     # the same question again: it is pursuing that idea
            self.touch(best)
            self.last_idea = best
            return best
        parent = best if best and score >= JOIN else self.root
        nid = self._add(None, parent, plain(text, 120), "idea", detail)
        self.nodes[nid]["words"] = ws
        self.last_idea = nid
        return nid

    def source(self, label: str, key: str, url: str | None = None, near: str = ""):
        if key in self.seen_src:                     # opened again: that source (and its idea) is pursued
            self.touch(self.seen_src[key])
            return self.seen_src[key]
        parent = self.last_idea
        ws = words(near or label)
        best, score = self._best_idea(ws)
        if best and score >= JOIN and self.nodes[parent]["kind"] == "core":
            parent = best
        nid = self._add(None, parent, label, "source", url=url)
        self.seen_src[key] = nid
        return nid

    def note(self, text: str):
        t = plain(text)
        if len(t) < 20:
            return
        n = self.nodes[self.last_idea]
        if t not in n["notes"]:
            n["notes"] = (n["notes"] + [t])[-3:]
        self.touch(self.last_idea)

    def decision(self, label: str):
        nid = self._add(None, self.root, label, "decision")
        self.last_idea = nid
        return nid

    def build_step(self, label: str, key: str):
        if self.build is None:
            self.build = self._add(None, self.root, "Building it", "trunk")
        if key in self.seen_src:
            self.touch(self.seen_src[key])
            return
        self.seen_src[key] = self._add(None, self.build, label, "build")

    def options(self, opts: list):
        """Options the plan weighed: [(text, chosen, reason)] -> option nodes under the latest decision."""
        parent = next((n["id"] for n in reversed(list(self.nodes.values())) if n["kind"] == "decision"), self.root)
        for text, chosen, reason in opts:
            ws = words(text)
            best, score = self._best_idea(ws)
            nid = self._add(None, parent, plain(text, 70), "option")
            self.nodes[nid].update(words=ws, state="chosen" if chosen else "set_aside", reason=plain(reason, 160))
            if best and score >= JOIN and self.nodes[best]["kind"] == "idea":   # the research this option came out of
                self.nodes[nid]["based_on"] = best
            if best and score >= JOIN and not chosen and self.nodes[best]["kind"] == "idea":
                self.nodes[best].update(state="set_aside", reason=plain(reason, 160))

    # -- one Studio job event
    def event(self, ev: dict):
        self.step += 1
        k = ev.get("k")
        if k == "note":
            return self.note(ev.get("text", ""))
        if k != "tool":
            return
        name, what = ev.get("name", ""), str(ev.get("what") or "")
        q, url, path, cmd = (str(ev.get(x) or "") for x in ("query", "url", "path", "cmd"))
        if name == "WebSearch":
            self.idea(q or what)
        elif name == "WebFetch":
            u = url or what
            if u.startswith("http"):
                p = urlparse(u)
                tail = " ".join(w for w in re.split(r"[/_\-.]+", p.path) if w and not w.isdigit())[:48]
                self.source(f"{_site(u)}{' · ' + tail if tail else ''}", u, url=u, near=tail)
        elif name in ("Agent", "Task"):
            self.idea(what, detail="a helper explores this")
        elif name == "Read" and path:
            label, key = _ref_label(path)
            if label:                                 # Kerf's own knowledge: past builds, the parts catalog, rule books
                if key in self.seen_src:
                    return self.touch(self.seen_src[key])
                if self.known is None:
                    self.known = self._add(None, self.root, "What Kerf already knows", "idea")
                    self.nodes[self.known]["words"] = {"kerf", "knows"}
                self.seen_src[key] = self._add(None, self.known, label, "source")
        elif name in ("Write", "Edit") and path:
            if path.endswith("DESIGN.md"):
                if not any(n["kind"] == "decision" for n in self.nodes.values()):
                    self.decision("The plan: what to build and why")
            elif path.endswith("REFERENCES.md"):
                self.note("Wrote down what it learned from the references.")
            elif re.search(r"/parts/([^/]+)\.py$", path):
                part = re.search(r"/parts/([^/]+)\.py$", path).group(1)
                if part != "layout":
                    self.build_step(f"Drawing the {part.replace('_', ' ')}", f"part:{part}")
            elif path.endswith("project.yaml"):
                self.build_step("Listing the parts and how they connect", "contract")
        elif name == "Bash" and cmd:
            if "kerf check" in cmd or "kerf build" in cmd:
                self.build_step("Testing that it fits, moves and holds", "test")
            elif "kerf find" in cmd:
                self.idea(cmd.split("kerf find", 1)[1].strip(" \"'"))

    def finish(self):
        for n in self.nodes.values():
            if n["kind"] in ("core", "trunk", "decision") or n["state"] in ("chosen", "set_aside"):
                continue
            kids = any(m["parent"] == n["id"] for m in self.nodes.values())
            age = self.step - n["touched"]
            if age <= RECENT:
                n["state"] = "active"
            elif n["kind"] == "idea" and not kids and n["touches"] < 3 and age >= IDLE:
                n["state"] = "set_aside"
                n["reason"] = n["reason"] or "it moved on to other questions"
            else:
                n["state"] = "pursued" if (kids or n["touches"] >= 3) else "explored"
        return self

    def json(self) -> dict:
        out = []
        for n in self.nodes.values():
            out.append({k: v for k, v in n.items() if k != "words"})
        return {"nodes": out, "steps": self.step}


def _ref_label(path: str):
    p = path.replace("\\", "/")
    m = re.search(r"projects/([^/]+)/", p)
    if m:
        return f"Past build: {m.group(1).replace('_', ' ')}", f"proj:{m.group(1)}"
    if "catalog/" in p:
        return "Parts catalog (real sizes)", "catalog"
    m = re.search(r"docs/([A-Z_]+)\.md$", p)
    if m:
        return f"Rule book: {m.group(1).title().replace('_', ' ')}", f"doc:{m.group(1)}"
    return None, None


def from_events(events: list, request: str = "") -> dict:
    w = Web(request)
    for ev in events:
        w.event(ev)
    return w.finish().json()


# ---------------------------------------------------------------- a finished project, from its own files

_CHOSEN = re.compile(r"\b(chosen|picked|selected)\b", re.I)
_REJECTED = re.compile(r"\b(rejected|ruled out|not chosen|dropped)\b", re.I)
_MARK = re.compile(r"^\s*\(?(chosen|picked|selected|rejected|ruled out|not chosen|dropped)\)?\s*(for a first build|here)?\s*[.;:,]?\s*", re.I)


def design_options(text: str) -> list:
    """(option, chosen, reason) from DESIGN.md's options list: a numbered list where items are marked chosen / picked /
    rejected. Unmarked items of a list that has a chosen one were set aside too. The reason drops the marker words, so
    it says why ("one joint per side, printable…"), not "chosen."."""
    groups, cur, last = [], [], 0
    for m in re.finditer(r"^\s*(\d+)\.\s+(.+?)$((?:\n\s{2,}.+$)*)", text, re.M):
        n = int(m.group(1))
        if n <= last or (cur and text[cur[-1][0]:m.start()].count("\n\n") > 1):   # numbering restarted: a new list
            groups.append(cur); cur = []
        cur.append((m.end(), " ".join((m.group(2) + " " + m.group(3)).split())))
        last = n
    groups.append(cur)
    out = []
    for g in groups:
        lines = [ln for _, ln in g]
        if not any(_CHOSEN.search(ln) for ln in lines):
            lines = [ln for ln in lines if _REJECTED.search(ln)]          # a list of rejections only: keep just those
            if not lines:
                continue
        for line in lines:
            chosen = bool(_CHOSEN.search(line)) and not _REJECTED.search(line)
            parts = re.split(r"\s[-:—]\s|:\s|\*\*\s*[.;:]?\s+", line, maxsplit=1)
            name = re.sub(r"\*\*", "", parts[0])
            name = re.sub(r"\s*\((chosen|picked|selected|rejected)\)\s*$", "", name, flags=re.I).strip(" .")
            rest = re.sub(r"\*\*", "", parts[1]).lstrip(" -:—") if len(parts) > 1 else ""
            m = re.match(r"\s*\((chosen|picked|selected|rejected)\)\s*[.:]?\s*(.*)$", rest, re.I)
            rest = m.group(2) if m else rest
            rest = _MARK.sub("", rest)
            rest = re.sub(r"[;,.]?\s*(rejected|ruled out|dropped)\b[^.]*\.?\s*$", ".", rest, flags=re.I).strip()
            out.append((name, chosen, "" if rest in ("", ".") else rest))
    return out


def _heading(h: str) -> str:
    """A REFERENCES.md heading as a question label: search text out of `kerf find "..."`, no dates, numbers or code."""
    h = re.sub(r'`kerf find\s+"([^"]+)"`', r"Searched past builds: \1", h)
    h = h.replace("`", "")
    h = re.sub(r"\([^)]*/[^)]*\)", "", h)                          # "(catalog/hardware.json)"
    h = re.sub(r"\(\d{4}-\d\d-\d\d\)|\d{4}-\d\d-\d\d", "", h)
    h = re.sub(r"^\s*[\d.]+\s+", "", h)
    h = re.sub(r"\(\s*\)", "", h)
    return " ".join(h.split()) or "Research"


def from_project(proj_dir: Path, request: str = "") -> dict:
    """Map of how a finished project was decided: REFERENCES.md sections -> ideas, their links -> sources, DESIGN.md
    options -> chosen / set aside, parts -> the build trunk."""
    import yaml
    d = Path(proj_dir)
    data = yaml.safe_load((d / "project.yaml").read_text(encoding="utf-8")) if (d / "project.yaml").exists() else {}
    w = Web(request or (data or {}).get("description") or (data or {}).get("name") or d.name)
    ref = (d / "REFERENCES.md").read_text(encoding="utf-8") if (d / "REFERENCES.md").exists() else ""
    for sec in re.split(r"^#{2,3}\s+", ref, flags=re.M)[1:]:
        head, _, body = sec.partition("\n")
        w.step += 1
        w.idea(_heading(head))
        for url in list(dict.fromkeys(re.findall(r"https?://[^\s)>\]]+", body)))[:6]:
            w.step += 1
            w.event({"k": "tool", "name": "WebFetch", "url": url.rstrip(".,")})
        first = next((ln for ln in body.splitlines() if len(ln.strip()) > 30 and not ln.strip().startswith(("|", "http"))), "")
        if first:
            w.note(first)
    des = (d / "DESIGN.md").read_text(encoding="utf-8") if (d / "DESIGN.md").exists() else ""
    if des:
        w.step += 1
        w.decision("The plan: what to build and why")
        w.options(design_options(des))
    for pid in (data or {}).get("parts") or {}:
        w.step += 1
        w.build_step(f"Drawing the {pid.replace('_', ' ')}", f"part:{pid}")
    w.step += 1
    w.build_step("Testing that it fits, moves and holds", "test")
    return w.finish().json()
