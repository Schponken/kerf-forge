"""Follow live + the Work tab (kerf/live.py, Studio): which parts two commits change, fast-forward only on a clean tree,
a part that fails mid-edit keeps its last good mesh, and the Work tab's data, all from throwaway git repos."""
import base64
import json
import os
import shutil
import subprocess
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pytest
import yaml

from kerf import live, studio

ROOT = Path(__file__).resolve().parent.parent
ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def g(repo, *a, env=None):
    r = subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, env={**ENV, **(env or {})})
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def commit(repo, msg, files: dict, env=None):
    for rel, txt in files.items():
        p = Path(repo) / rel
        if txt is None:
            p.unlink()
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt)
    g(repo, "add", "-A")
    g(repo, "commit", "-q", "-m", msg, env=env)
    return g(repo, "rev-parse", "HEAD")


PROJ = {"name": "demo", "params": {"w": {"value": 10}}, "layout": "parts/layout.py",
        "parts": {"a": {"file": "parts/a.py"}, "b": {"file": "parts/b.py", "material": "PETG"}},
        "purchased": {"s": {"catalog": "servos.MG996R", "proxy": "servo"}},
        "assembly": {"root": "a", "joints": [{"parent": "a.x", "child": "b.y"}, {"parent": "b.z", "child": "s.tabs"}]}}


def _yaml(**over):
    d = json.loads(json.dumps(PROJ))
    for k, v in over.items():
        d[k] = v
    return yaml.safe_dump(d, sort_keys=False)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    g(r, "init", "-q", "-b", "main")
    commit(r, "base", {"projects/demo/project.yaml": _yaml(), "projects/demo/parts/a.py": "A = 1\n",
                       "projects/demo/parts/b.py": "B = 1\n", "projects/demo/parts/layout.py": "L = 1\n",
                       "projects/demo/DESIGN.md": "# d\n", "projects/other/project.yaml": "name: o\nparts: {}\n"})
    return r


# ---------------------------------------------------------------- change detection
def test_changed_parts_maps_files_and_yaml_to_items(repo):
    c0 = g(repo, "rev-parse", "HEAD")
    c1 = commit(repo, "edit a", {"projects/demo/parts/a.py": "A = 2\n"})
    assert live.changed_parts(repo, c0, c1, "demo")["items"] == ["a"]
    c2 = commit(repo, "b material", {"projects/demo/project.yaml": _yaml(parts={**PROJ["parts"], "b": {"file": "parts/b.py", "material": "PLA"}})})
    ch = live.changed_parts(repo, c1, c2, "demo")
    assert ch["items"] == ["b"] and not ch["all"]
    c3 = commit(repo, "docs only + another project", {"projects/demo/DESIGN.md": "# new\n", "projects/other/project.yaml": "name: o2\nparts: {}\n"})
    assert live.changed_parts(repo, c2, c3, "demo")["items"] == []
    c4 = commit(repo, "shared helper", {"projects/demo/parts/layout.py": "L = 2\n"})
    ch = live.changed_parts(repo, c3, c4, "demo")
    assert ch["all"] and ch["items"] == ["a", "b", "s"]
    c5 = commit(repo, "param", {"projects/demo/project.yaml": _yaml(parts={**PROJ["parts"], "b": {"file": "parts/b.py", "material": "PLA"}},
                                                                  params={"w": {"value": 12}})})
    assert live.changed_parts(repo, c4, c5, "demo")["all"]
    c6 = commit(repo, "drop b", {"projects/demo/project.yaml": _yaml(parts={"a": {"file": "parts/a.py"}}, params={"w": {"value": 12}},
                                                                   assembly={"root": "a", "joints": [{"parent": "a.z", "child": "s.tabs"}]})})
    ch = live.changed_parts(repo, c5, c6, "demo")
    assert ch["removed"] == ["b"] and ch["all"]          # the joint tree changed: everything may have moved
    c7 = commit(repo, "new part file", {"projects/demo/parts/c.py": "C = 1\n",
                                        "projects/demo/project.yaml": _yaml(parts={"a": {"file": "parts/a.py"}, "c": {"file": "parts/c.py"}},
                                                                            params={"w": {"value": 12}},
                                                                            assembly={"root": "a", "joints": [{"parent": "a.z", "child": "s.tabs"}]})})
    ch = live.changed_parts(repo, c6, c7, "demo")
    assert ch["items"] == ["c"] and not ch["all"]
    assert live.last_subject(repo, c0, c7, "demo")["subject"] == "new part file"
    assert live.last_subject(repo, c2, c3, "other")["subject"] == "docs only + another project"


def test_needed_takes_children_to_mesh_and_ancestors_to_build():
    mesh, build = live.needed(PROJ, ["b"])
    assert mesh == {"b", "s"} and build == {"a", "b", "s"}
    mesh, build = live.needed(PROJ, ["s"])
    assert mesh == {"s"} and build == {"a", "b", "s"}


# ---------------------------------------------------------------- fast-forward only on a clean tree
@pytest.fixture
def clones(tmp_path, repo):
    origin = tmp_path / "origin.git"
    g(tmp_path, "clone", "-q", "--bare", str(repo), str(origin))
    mac, cloud = tmp_path / "mac", tmp_path / "cloud"
    g(tmp_path, "clone", "-q", str(origin), str(mac))
    g(tmp_path, "clone", "-q", str(origin), str(cloud))
    commit(cloud, "pivot system done", {"projects/demo/parts/b.py": "B = 2\n"})
    g(cloud, "push", "-q")
    return mac, cloud


def test_fast_forward_refuses_a_dirty_tree_then_updates_a_clean_one(clones):
    mac, _ = clones
    assert live.fetch(mac) is None
    head0 = g(mac, "rev-parse", "HEAD")
    (mac / "projects/demo/parts/a.py").write_text("A = 'my local edit'\n")
    assert live.fast_forward(mac) == (False, "can't update: local changes")
    assert g(mac, "rev-parse", "HEAD") == head0 and "my local edit" in (mac / "projects/demo/parts/a.py").read_text()
    g(mac, "checkout", "-q", "--", ".")
    assert live.fast_forward(mac) == (True, "")
    assert g(mac, "rev-parse", "HEAD") == g(mac, "rev-parse", "@{u}") and (mac / "projects/demo/parts/b.py").read_text() == "B = 2\n"


@pytest.fixture
def studio_at(monkeypatch):
    def at(root):
        monkeypatch.setattr(studio, "ROOT", root)
        monkeypatch.setattr(studio, "PROJECTS", root / "projects")
        monkeypatch.setattr(studio, "LIVE", {"follow": {}, "last_fetch": 0.0, "fetch_error": None, "work_until": 0.0,
                                             "work": None, "work_key": None, "thread": None})
        st = studio._live_state("demo")
        st.update(on=True, data={"items": [], "bounds": [[0, 0, 0], [1, 1, 1]]}, seeded=True)
        calls = []
        monkeypatch.setattr(studio, "_live_rebuild", lambda *a: calls.append(a))
        return st, calls
    return at


def test_follow_stops_with_a_reason_on_local_changes(clones, studio_at):
    mac, _ = clones
    st, calls = studio_at(mac)
    (mac / "projects/demo/parts/a.py").write_text("A = 'mid-edit here'\n")
    studio.live_tick(now=1000.0)
    assert st["error"] == "can't update: local changes" and st["on"] is False and calls == []


def test_follow_fetches_at_most_once_a_minute_and_rebuilds_only_changed_parts(clones, studio_at):
    mac, cloud = clones
    st, calls = studio_at(mac)
    studio.live_tick(now=1000.0)
    assert g(mac, "rev-parse", "HEAD") == g(cloud, "rev-parse", "HEAD")
    (name, ids, removed, line), = calls
    assert name == "demo" and ids == ["b"] and removed == [] and line.endswith(" pivot system done") and line[2] == ":"
    commit(cloud, "more", {"projects/demo/parts/a.py": "A = 3\n"})
    g(cloud, "push", "-q")
    studio.live_tick(now=1030.0)                         # 30 s later: no fetch yet
    assert len(calls) == 1 and studio.LIVE["last_fetch"] == 1000.0
    studio.live_tick(now=1061.0)
    assert len(calls) == 2 and calls[1][1] == ["a"]


# ---------------------------------------------------------------- last good mesh on a failed build
def _item(iid, pts):
    v = np.asarray(pts, np.float32)
    return {"id": iid, "role": "printed", "verts": base64.b64encode(v.tobytes()).decode(),
            "tris": base64.b64encode(np.array([[0, 1, 2]], np.uint32).tobytes()).decode(), "nv": 3, "nt": 1}


def test_merge_keeps_the_last_good_mesh_of_a_part_that_failed_and_swaps_the_rest():
    a0, b0 = _item("a", [[0, 0, 0], [1, 0, 0], [0, 1, 0]]), _item("b", [[0, 0, 5], [1, 0, 5], [0, 1, 5]])
    D = {"items": [dict(a0, color="#111", joints=["j"], explode=[0, 0, 0], stress={"u": "x"}), dict(b0, color="#222", joints=[])],
         "bounds": [[0, 0, 0], [1, 1, 5]]}
    b1, c1 = _item("b", [[0, 0, 9], [1, 0, 9], [0, 1, 9]]), _item("c", [[5, 5, 5], [6, 5, 5], [5, 6, 5]])
    m = live.merge(D, {"items": {"b": b1, "c": c1},
                       "errors": {"a": "SyntaxError: a.py line 3"}, "stubs": ["c"]})
    by = {it["id"]: it for it in D["items"]}
    assert by["a"]["verts"] == a0["verts"] and by["a"]["stress"]       # untouched: last good mesh, its colours
    assert by["b"]["verts"] == b1["verts"] and by["b"]["color"] == "#222" and "stress" not in by["b"]
    assert by["c"]["color"] and by["c"]["joints"] == [] and len(by["c"]["explode"]) == 3
    assert m == {"changed": ["b", "c"], "removed": [], "editing": {"a": "SyntaxError: a.py line 3"}, "designing": ["c"]}
    assert D["bounds"][1][2] == 9.0
    assert live.merge(D, {"items": {"b": b1}})["changed"] == []          # same mesh again: nothing to swap
    assert live.merge(D, {"items": {}}, removed=["c"])["removed"] == ["c"] and "c" not in {it["id"] for it in D["items"]}


def test_rebuild_meshes_the_changed_part_and_reports_a_broken_one(tmp_path):
    """The real child path on servo_link: the arm is built (with what places it), meshed at its home pose; with its file
    broken it comes back as an error, so Studio keeps showing its last good mesh."""
    p = tmp_path / "servo_link"
    shutil.copytree(ROOT / "projects" / "servo_link", p, ignore=shutil.ignore_patterns("out", "__pycache__"))
    res = live.rebuild(str(p), ["arm"])
    assert set(res["items"]) == {"arm"} and not res["errors"] and res["joints"] is None
    v = np.frombuffer(base64.b64decode(res["items"]["arm"]["verts"]), np.float32).reshape(-1, 3)
    assert len(v) > 100 and np.ptp(v[:, 2]) > 50                        # the 100 mm arm, standing up at home
    (p / "parts" / "arm.py").write_text((p / "parts" / "arm.py").read_text() + "\ndef build(ctx):\n    return ctx.finish(1 / 0)\n")
    bad = live.rebuild(str(p), ["arm"])
    assert bad["items"] == {} and "arm" in bad["errors"]
    D = {"items": [dict(res["items"]["arm"], color="#4C78A8", explode=[0, 0, 1], joints=["swing"])], "bounds": [[0, 0, 0], [1, 1, 1]]}
    m = live.merge(D, bad)
    assert m["editing"].keys() == {"arm"} and D["items"][0]["verts"] == res["items"]["arm"]["verts"]


# ---------------------------------------------------------------- the Work tab
PLAN = "# plan\n## A\n- [x] old thing\n- [ ] Pivot for demo: hubs\n- [ ] Engine thing\n"


def test_work_data_from_git(repo):
    now = time.time()
    old = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now - 30 * 3600))
    commit(repo, "yesterday-ish work", {"PLAN.md": PLAN}, env={"GIT_COMMITTER_DATE": old, "GIT_AUTHOR_DATE": old})
    stale = {"item": "Engine thing", "session": "s-old", "heartbeat": now - 100 * 60}
    commit(repo, "claim: Engine thing", {"claims/engine-thing.json": json.dumps(stale)},
           env={"GIT_COMMITTER_DATE": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now - 100 * 60))})
    fresh = {"item": "Pivot for demo: hubs " + "x" * 150, "session": "s-new", "heartbeat": now - 10 * 60}
    commit(repo, "claim: Pivot", {"claims/pivot.json": json.dumps(fresh), "claims/broken.json": "{nope"},
           env={"GIT_COMMITTER_DATE": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now - 10 * 60))})
    commit(repo, "demo: hubs done", {"PLAN.md": PLAN.replace("- [ ] Pivot for demo: hubs", "- [x] Pivot for demo: hubs")})
    w = live.work_data(repo, "HEAD", now=now, picture=lambda p: f"/files/{p}/out/renders/assembly.png")
    assert (w["plan_done"], w["plan_total"], w["sessions"], w["today"]) == (2, 3, 1, 1)
    c_new, c_old = w["cards"]
    assert c_new["project"] == "demo" and c_new["picture"] == "/files/demo/out/renders/assembly.png" and not c_new["stale"]
    assert len(c_new["item"]) <= 110 and c_new["item"].endswith("…") and 9 <= c_new["since_commit_min"] <= 11
    assert c_old["stale"] and c_old["project"] is None and c_old["picture"] is None and w["stale_min"] == 90
    assert [f["subject"] for f in w["feed"]][:2] == ["demo: hubs done", "claim: Pivot"]
    assert w["feed"][0]["done"] == ["Pivot for demo: hubs"] and w["feed"][1]["done"] == []
    assert w["feed"][3]["done"] == ["old thing"]                     # added already checked (yesterday: not counted today)


# ---------------------------------------------------------------- Studio smoke: routes answer, page has the controls
def test_studio_live_and_work_routes(monkeypatch):
    monkeypatch.setattr(studio, "_live_thread", lambda: None)            # no background fetch of the real repo in tests
    monkeypatch.setattr(studio, "LIVE", {"follow": {}, "last_fetch": 0.0, "fetch_error": None, "work_until": 0.0,
                                         "work": None, "work_key": None, "thread": None})
    srv = ThreadingHTTPServer(("127.0.0.1", 0), studio.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        def get(path):
            with urllib.request.urlopen(base + path) as r:
                return r.read()
        page = get("/").decode()
        assert "Follow live" in page and "showWork" in page and "liveSwap" in page
        assert json.loads(get("/api/live/servo_link"))["on"] is False
        req = urllib.request.Request(base + "/api/live/follow", data=json.dumps({"project": "servo_link", "on": True}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            assert json.loads(r.read())["on"] is True
        assert json.loads(get("/api/project/servo_link"))["live_on"] is True
        html = get("/live/servo_link/viewer.html").decode()
        assert "liveSwap" in html and '"live_seq":0' in html
        w = json.loads(get("/api/work"))
        assert {"plan_done", "plan_total", "sessions", "today", "cards", "feed"} <= set(w) and w["plan_total"] > 0
    finally:
        srv.shutdown()
