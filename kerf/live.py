"""Follow live: Kerf Studio shows a project's 3D model updating while cloud sessions design it (and the Work tab).

Everything here is local and git-only: Studio runs `git fetch` at most once a minute while someone is following a project
(or looking at the Work tab), and when new commits on origin touch projects/<p>/ it fast-forwards the working copy
(same rule as tools/mac/start.sh: only a clean tree, only a fast-forward) and rebuilds ONLY the parts that changed:
geometry and viewer meshes, no checks, FEA, review or tests. The rebuild runs in a child process (`python -m kerf.live`)
through the normal part build and its cache (kerf/partcache.py), so the Studio server stays small and responsive.

  changed_parts(root, old, new, project)   which items two commits change (the unit-tested core)
  fast_forward(root)                       clean tree + ff-only, else a reason ("can't update: local changes")
  rebuild(name, ids)                       child: build those items (+ what places them), mesh them at the home pose
  merge(D, result)                         put a rebuild's meshes into the viewer data; a part that failed to build
                                           keeps its last good mesh and is marked "being edited"
  work_data(root, ref)                     the Work tab: PLAN progress, fresh claims, the commit feed (all from git)
"""
from __future__ import annotations

import base64
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FETCH_EVERY = 60.0            # seconds between `git fetch`es, never less
FEED_N = 20
ITEM_SECTIONS = ("parts", "purchased", "keepouts")
GLOBAL_KEYS = ("params", "layout", "derived", "assembly", "printer", "supports")   # a change here can move every item


def git(root, *args, timeout=60) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=timeout)


def _out(root, *args) -> str:
    r = git(root, *args)
    return r.stdout.strip() if r.returncode == 0 else ""


def _yaml_at(root, rev: str, rel: str) -> dict | None:
    r = git(root, "show", f"{rev}:{rel}")
    if r.returncode != 0:
        return None
    try:
        return yaml.safe_load(r.stdout) or {}
    except Exception:  # noqa: BLE001 - a half-written project.yaml: treat as "everything may have changed"
        return {"_unreadable": True}


def _items(data: dict) -> dict:
    return {iid: spec for sec in ITEM_SECTIONS for iid, spec in ((data or {}).get(sec) or {}).items()}


def _part_file(pid: str, spec) -> str:
    return str((spec or {}).get("file") or f"parts/{pid}.py") if isinstance(spec, dict) or spec is None else f"parts/{pid}.py"


# ---------------------------------------------------------------- which parts changed between two commits
def changed_parts(root, old: str, new: str, project: str) -> dict:
    """What `new` changes in projects/<project>/ compared with `old`: {"all": bool, "items": [ids], "removed": [ids],
    "files": [paths]}. A part file maps to the item(s) built from it; a helper in parts/ (not a part module, e.g.
    layout.py) or a change to params / layout / assembly in project.yaml can move anything, so it is "all"; a changed
    item spec in project.yaml is that item. Docs (DESIGN.md, REFERENCES.md) and out/ change nothing."""
    base = f"projects/{project}/"
    files = [f for f in _out(root, "diff", "--name-only", old, new, "--", base).splitlines() if f]
    res = {"all": False, "items": [], "removed": [], "files": files}
    if not files:
        return res
    y_new, y_old = _yaml_at(root, new, base + "project.yaml"), _yaml_at(root, old, base + "project.yaml")
    if y_new is None:                                   # the project was deleted
        res["removed"] = sorted(_items(y_old or {}))
        return res
    new_items, old_items = _items(y_new), _items(y_old or {})
    res["removed"] = sorted(set(old_items) - set(new_items))
    changed: set[str] = set()
    if y_old is None or y_new.get("_unreadable") or y_old.get("_unreadable") or \
            any(y_new.get(k) != y_old.get(k) for k in GLOBAL_KEYS):
        res["all"] = True
    else:
        changed |= {i for i in new_items if new_items[i] != old_items.get(i)}
    by_file: dict[str, list[str]] = {}
    for pid, spec in (y_new.get("parts") or {}).items():
        if not (spec or {}).get("import"):
            by_file.setdefault(_part_file(pid, spec), []).append(pid)
    for f in files:
        rel = f[len(base):]
        if rel.startswith("parts/") and rel.endswith(".py"):
            if rel in by_file:
                changed |= set(by_file[rel])
            else:                                       # a shared helper (layout.py, fingerlib.py ...): any part may use it
                res["all"] = True
        elif rel.startswith("parts/") and not rel.endswith((".md", ".txt")):
            res["all"] = True                           # data a part reads (a mesh, a table)
    res["items"] = sorted(new_items) if res["all"] else sorted(changed & set(new_items))
    return res


def last_subject(root, old: str, new: str, project: str) -> dict | None:
    """The newest commit in old..new that touches projects/<project>/: {hash, time, subject}."""
    ln = _out(root, "log", "-1", "--format=%h%x09%ct%x09%s", f"{old}..{new}", "--", f"projects/{project}/")
    if not ln:
        return None
    h, ct, s = ln.split("\t", 2)
    return {"hash": h, "time": int(ct), "subject": s}


# ---------------------------------------------------------------- fetch + fast-forward (same rules as start.sh)
def fetch(root) -> str | None:
    """`git fetch` of the current upstream; None when it worked, else a short reason (offline is not an error)."""
    r = git(root, "-c", "http.lowSpeedLimit=1000", "-c", "http.lowSpeedTime=10", "fetch", "-q", timeout=90)
    return None if r.returncode == 0 else (r.stderr.strip().splitlines() or ["git fetch failed"])[-1][:200]


def upstream(root) -> str:
    return _out(root, "rev-parse", "--verify", "-q", "@{u}")


def dirty(root) -> bool:
    return bool(_out(root, "status", "--porcelain", "--untracked-files=no"))


def fast_forward(root) -> tuple[bool, str]:
    """Move the working copy to its upstream, only when the tree is clean and it is a fast-forward."""
    up = upstream(root)
    if not up:
        return False, "can't update: this branch has no upstream"
    if dirty(root):
        return False, "can't update: local changes"
    if git(root, "merge-base", "--is-ancestor", "HEAD", up).returncode != 0:
        return False, "can't update: local commits that aren't on origin"
    r = git(root, "merge", "--ff-only", "-q", up)
    if r.returncode != 0:
        return False, "can't update: " + ((r.stderr or r.stdout).strip().splitlines() or ["fast-forward failed"])[-1][:160]
    return True, ""


# ---------------------------------------------------------------- the rebuild (child process)
def _tree(data: dict) -> tuple[str | None, dict]:
    a = (data or {}).get("assembly") or {}
    parent = {}
    for j in a.get("joints") or []:
        try:
            parent[str(j["child"]).split(".", 1)[0]] = str(j["parent"]).split(".", 1)[0]
        except Exception:  # noqa: BLE001
            continue
    return a.get("root"), parent


def needed(data: dict, ids: list[str]) -> tuple[set, set]:
    """(to mesh, to build): the changed items and everything hanging below them (a moved parent moves its children),
    plus their ancestors up to the root (their joints place the changed ones)."""
    root, parent = _tree(data)
    kids: dict[str, list[str]] = {}
    for c, p in parent.items():
        kids.setdefault(p, []).append(c)
    mesh_set, todo = set(), list(ids)
    while todo:
        n = todo.pop()
        if n not in mesh_set:
            mesh_set.add(n)
            todo += kids.get(n, [])
    build = set(mesh_set)
    for n in list(mesh_set):
        seen = set()
        while n in parent and n not in seen:
            seen.add(n)
            n = parent[n]
            build.add(n)
    if root:
        build.add(root)
    return mesh_set, build


def _place(proj) -> set:
    """Put every item that can be placed at its home pose; an item whose own build or any ancestor's failed stays
    unplaced (assembly.solve() needs every shape)."""
    from build123d import Location
    from . import assembly as A
    from .project import ProjectError
    items = proj.items
    for _ in range(len(items) + 1):
        try:
            asm = A.plan(proj)
            break
        except ProjectError as e:                       # a part mid-edit without its joint label: drop it, retry
            hit = [i for i in items if items[i].shape is not None and re.search(rf"\b{re.escape(i)}\b", str(e))]
            if not hit:
                return set()
            for i in hit:
                items[i].shape, items[i].error = None, items[i].error or str(e)
    else:
        return set()
    root = items[asm.root].shape
    if root is None:
        return set()
    root.location = Location(getattr(root, "kerf_home_loc", Location()).wrapped)
    placed = {asm.root}
    for e in asm.edges:
        if e.parent not in placed or items[e.child].shape is None:
            continue
        try:
            pj, cj = items[e.parent].shape.joints[e.pjoint], items[e.child].shape.joints[e.cjoint]
            if e.kind == "revolute":
                pj.connect_to(cj, angle=e.home)
            elif e.kind == "linear":
                pj.connect_to(cj, position=e.home)
            else:
                pj.connect_to(cj)
            placed.add(e.child)
        except Exception as ex:  # noqa: BLE001
            items[e.child].error = items[e.child].error or f"could not place: {ex}"
    return placed


def rebuild(name: str, ids: list[str] | None) -> dict:
    """Build `ids` (None = every item) through the normal part build + cache, place them, and mesh them.
    {"items": {id: viewer item}, "errors": {id: why}, "stubs": [...], "joints": [...] (full builds only)}."""
    from . import project as P
    from . import viewer as V
    proj = P.load(name)
    all_ids = list(proj.items)
    mesh_set, build_set = needed(proj.data, all_ids if ids is None else [i for i in ids if i in proj.items])
    P.build(proj, only=sorted(build_set))
    placed = _place(proj)
    out = {"items": {}, "errors": {}, "stubs": [], "joints": None}
    root, parent = _tree(proj.data)
    movable = set()
    for iid in mesh_set:
        it = proj.items[iid]
        if it.error or it.shape is None or iid not in placed:
            out["errors"][iid] = (it.error or "its parent part could not be built").splitlines()[0][:200]
            continue
        if getattr(it.shape, "kerf_stub", None):
            out["stubs"].append(iid)
        v, t, fs = V.mesh(it.shape, face_starts=True)
        out["items"][iid] = {"id": iid, "role": it.role, "verts": V._b64(v), "tris": V._b64(t), "nv": int(len(v)),
                             "nt": int(len(t)), "faceStart": V._b64(fs), "src": it.spec.get("file"),
                             "catalog": it.spec.get("catalog"), "material": it.spec.get("material"),
                             "label": V._label(it), "off_board": bool(it.spec.get("off_board")), "attr": None}
    if ids is None and not out["errors"]:             # whole model built: joints for the viewer's sliders
        try:
            from . import assembly as A
            asm = A.plan(proj)
            out["joints"] = [V.joint_motion(asm, e) for e in asm.movable]
            movable = {e.name for e in asm.movable}
            for iid, d in out["items"].items():
                js, n = [], iid
                while n in asm.by_child:
                    e = asm.by_child[n]
                    if e.name in movable:
                        js.append(e.name)
                    n = e.parent
                d["joints"] = list(reversed(js))
        except Exception:  # noqa: BLE001 - the model still shows, just without moving joints
            out["joints"] = None
    out["stubs"].sort()
    return out


# ---------------------------------------------------------------- merge a rebuild into the viewer data
def _bbox(it: dict):
    import numpy as np
    v = np.frombuffer(base64.b64decode(it["verts"]), np.float32).reshape(-1, 3)
    return (v.min(axis=0), v.max(axis=0)) if len(v) else (np.zeros(3), np.zeros(3))


def merge(D: dict, result: dict, removed: list[str] | None = None) -> dict:
    """Swap a rebuild's meshes into viewer data D (in place). A part that failed to build keeps its last good mesh and is
    listed under "editing"; a placeholder part is "designing". Returns {"changed": [ids whose mesh changed or are new],
    "removed": [...], "editing": {id: why}, "designing": [...]}."""
    import numpy as np
    from .viewer import KEEPOUT, PALETTE, PURCHASED
    by_id = {it["id"]: it for it in D.setdefault("items", [])}
    lo, hi = (np.asarray(b, float) for b in D.get("bounds") or [[0, 0, 0], [0, 0, 0]])
    center = (lo + hi) / 2
    changed = []
    for iid, new in (result.get("items") or {}).items():
        old = by_id.get(iid)
        if old is not None and old.get("verts") == new["verts"] and old.get("tris") == new["tris"]:
            continue
        it = dict(old or {})
        it.update(new)                                  # partial rebuilds carry no "joints": the old chain stays
        it.pop("stress", None)                          # the FEA colours belonged to the old shape
        it["attr"] = None
        if old is None:
            k = len(D["items"])
            role = it.get("role")
            it.setdefault("color", PALETTE[k % len(PALETTE)] if role == "printed" else (KEEPOUT if role == "keepout" else PURCHASED))
            it.setdefault("joints", [])
            it.setdefault("catalog_source", None)
            D["items"].append(it)
        else:
            D["items"][D["items"].index(old)] = it
        b0, b1 = _bbox(it)
        dvec = (b0 + b1) / 2 - center
        n = float(np.linalg.norm(dvec)) or 1.0
        it["explode"] = [round(float(x), 4) for x in dvec / n * (1 + n / 100)]
        by_id[iid] = it
        changed.append(iid)
    gone = [i for i in (removed or []) if i in by_id]
    if gone:
        D["items"] = [it for it in D["items"] if it["id"] not in gone]
    if result.get("joints") is not None:
        D["joints"] = result["joints"]
    solid = [it for it in D["items"] if it.get("role") != "keepout" and it.get("nv")]
    if solid and changed:
        bb = [_bbox(it) for it in solid]
        D["bounds"] = [[round(float(x), 3) for x in np.min([b[0] for b in bb], axis=0)],
                       [round(float(x), 3) for x in np.max([b[1] for b in bb], axis=0)]]
    return {"changed": changed, "removed": gone, "editing": dict(result.get("errors") or {}),
            "designing": list(result.get("stubs") or [])}


def blank_data(name: str, project_dir: str) -> dict:
    """Viewer data for a project that has never been built on this computer: geometry only, honestly labelled."""
    return {"items": [], "joints": [], "params": {}, "steps": None, "steps_error": "live view: geometry only",
            "attr_error": "live view: geometry only", "project_dir": project_dir, "bounds": [[0, 0, 0], [1, 1, 1]],
            "report": {"project": name, "ok": False, "problems": ["live view: geometry only, not checked yet (Build it for the checks)"],
                       "warnings": [], "parts": {}, "purchased": {}, "requirements": [], "assembly": {}}}


# ---------------------------------------------------------------- the Work tab (all from git)
def _claims_mod():
    spec = importlib.util.spec_from_file_location("kerf_claims_tool", ROOT / "tools" / "claims.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _checked_off(patch: str) -> list[str]:
    """PLAN.md items a diff checks off: `- [x]` lines it adds that weren't already checked under the same text."""
    added, removed = [], set()
    for ln in patch.splitlines():
        m = re.match(r"^([+-])\s*- \[[xX]\] (.+)$", ln)
        if m and not ln.startswith(("+++", "---")):
            (added.append if m.group(1) == "+" else removed.add)(m.group(2).strip())
    return [a for a in added if a not in removed]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def project_of(text: str, names: list[str]) -> str | None:
    """The project a PLAN item is about: its folder name (or the same words) appears in the item text."""
    t = f" {_norm(text)} "
    for n in sorted(names, key=len, reverse=True):
        if f" {_norm(n)} " in t:
            return n
    return None


def work_data(root, ref: str = "@{u}", now: float | None = None, picture=None) -> dict:
    """Everything the Work tab shows, read from `ref` (the fetched origin branch): PLAN done/total, fresh claims as
    cards (item, project, minutes since that session's last commit, stale flag), items checked off today, and the
    last FEED_N commit subjects. picture(project) -> image URL or None (Studio passes its out/ snapshot lookup)."""
    from .work import number, plan_steps
    now = time.time() if now is None else now
    cl = _claims_mod()
    rev = _out(root, "rev-parse", "--verify", "-q", ref) or _out(root, "rev-parse", "HEAD")
    plan = git(root, "show", f"{rev}:PLAN.md").stdout
    done = len(re.findall(r"^\s*- \[[xX]\] ", plan, re.M))
    total = done + len(re.findall(r"^\s*- \[ \] ", plan, re.M))
    names = [Path(p).name for p in _out(root, "ls-tree", "--name-only", rev, "projects/").splitlines()]
    cards, sessions = [], set()
    for f in _out(root, "ls-tree", "--name-only", rev, "claims/").splitlines():
        if not f.endswith(".json"):
            continue
        try:
            c = json.loads(git(root, "show", f"{rev}:{f}").stdout)
        except Exception:  # noqa: BLE001 - a broken claim file is no claim (same as tools/claims.py)
            continue
        if not isinstance(c, dict):
            continue
        heartbeat = number(c.get("heartbeat"), 0)
        last = max(heartbeat, number(_out(root, "log", "-1", "--format=%ct", rev, "--", f), 0))
        age_min = max(0, now - last) / 60
        if age_min >= cl.STALE_MIN * 2:                 # long gone: not "working" and not worth a card
            continue
        item = str(c.get("item", ""))
        proj = project_of(item, names)
        cards.append({"item": item if len(item) <= 110 else item[:107].rstrip() + "…", "full": item,
                      "session": c.get("session"), "since_commit_min": round(age_min, 1),
                      "stale": age_min >= cl.STALE_MIN, "project": proj,
                      "picture": picture(proj) if (proj and picture) else None,
                      "claim_id": Path(f).stem, "provider": c.get("provider"), "thread_id": c.get("thread_id"),
                      "started_at": number(c.get("since")), "updated_at": last,
                      "heartbeat_at": heartbeat or None, "steps": plan_steps(plan, item),
                      "activity": c.get("activity"), "title": c.get("title")})
        if age_min < cl.STALE_MIN:
            sessions.add(c.get("session"))
    cards.sort(key=lambda x: (x["stale"], x["since_commit_min"]))
    midnight = time.mktime(time.localtime(now)[:3] + (0, 0, 0, 0, 0, -1))
    feed = []
    for ln in _out(root, "log", f"-{FEED_N}", "--format=%H%x09%ct%x09%s", rev).splitlines():
        h, ct, subj = ln.split("\t", 2)
        feed.append({"hash": h, "time": int(ct), "subject": subj})
    since = min([midnight] + [f["time"] for f in feed])
    offs, today = {}, 0                                 # one `git log -p` for every PLAN.md change in the window
    for chunk in _out(root, "log", "-p", "-U0", "--format=%x00%H%x09%ct", f"--since={int(since) - 1}", rev, "--",
                      "PLAN.md").split("\x00")[1:]:
        head, _, patch = chunk.partition("\n")
        h, ct = head.split("\t")
        offs[h] = _checked_off(patch)
        today += len(offs[h]) if int(ct) >= midnight else 0
    for f in feed:
        f["done"] = offs.get(f["hash"], [])
        f["hash"] = f["hash"][:7]
    return {"ref": rev[:7], "plan_done": done, "plan_total": total, "sessions": len(sessions),
            "today": today, "cards": cards, "feed": feed, "stale_min": cl.STALE_MIN}


def main(argv: list[str]) -> int:
    """Child process: python -m kerf.live <project> <out.json> [ALL | id ...]."""
    import os
    try:
        os.nice(5)                                      # a background refresh: the Mac stays responsive
    except Exception:  # noqa: BLE001
        pass
    name, out = argv[0], Path(argv[1])
    ids = None if not argv[2:] or argv[2:] == ["ALL"] else argv[2:]
    res = rebuild(name, ids)
    out.write_text(json.dumps(res), encoding="utf-8")
    print(f"live: {len(res['items'])} meshed, {len(res['errors'])} being edited", flush=True)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    sys.exit(main(sys.argv[1:]))
