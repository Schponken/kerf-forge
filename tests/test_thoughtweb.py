"""Thought web (kerf/thoughtweb.py + assets/thoughtweb.js): a simplified, near-live map built only from a job's visible
actions and notes; branches, sources, set-aside options and the build trunk; the Studio panel and project modal draw it."""
import json
import sys
import time
from pathlib import Path

import urllib.request

import pytest

from kerf import steer as T_steer, studio, thoughtweb as T
from test_studio import _browser, server  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parent.parent
FAKE = ROOT / "tests" / "fixtures" / "fake_claude_stream.py"


def _events():
    evs = []
    from subprocess import run
    out = run([sys.executable, str(FAKE), "0"], capture_output=True, text=True).stdout
    for ln in out.splitlines():
        for x in studio._claude_lines(ln):
            if x.startswith("@@"):
                evs.append(json.loads(x[2:]))
    return evs


def test_branches_sources_notes_and_the_build_trunk():
    g = {n["label"]: n for n in T.from_events(_events(), "A drone with wings that fold like a hawk")["nodes"]}
    by_id = {n["id"]: n for n in g.values()}
    core = g["A drone with wings that fold like a hawk"]
    assert core["kind"] == "core" and core["parent"] is None
    hawk = g["morphing wing drone folding wings like a hawk EPFL"]
    assert by_id[hawk["parent"]]["label"] == "Research morphing-wing drones"      # a follow-up branches off its idea
    lishawk = next(n for n in g.values() if n["label"].startswith("epfl.ch"))
    assert lishawk["kind"] == "source" and lishawk["parent"] == hawk["id"] and lishawk["url"].startswith("https://")
    assert any("rigid pivoting panel" in t for t in hawk["notes"])               # the job's own note, first sentence
    motor = g["2806.5 motor thrust 4S 7 inch prop"]
    assert motor["parent"] == core["id"]                                        # a new line of inquiry: off the core
    assert by_id[g["Past build: fpv wing"]["parent"]]["label"] == "What Kerf already knows"
    assert g["The plan: what to build and why"]["kind"] == "decision"
    assert g["Drawing the hub"]["kind"] == "build" and by_id[g["Drawing the hub"]["parent"]]["label"] == "Building it"
    assert g["feathered telescoping printed wing"]["state"] in ("explored", "active", "set_aside")


def test_idle_branches_are_set_aside_and_repeats_are_pursued():
    w = T.Web("make a lamp")
    w.event({"k": "tool", "name": "WebSearch", "query": "lamp shade printable diffuser"})
    w.event({"k": "tool", "name": "WebSearch", "query": "led strip 5V current"})
    for _ in range(T.IDLE + 2):
        w.event({"k": "tool", "name": "WebSearch", "query": "led strip 5V current"})   # keeps returning to this one
    g = {n["label"]: n for n in w.finish().json()["nodes"]}
    assert g["lamp shade printable diffuser"]["state"] == "set_aside" and g["lamp shade printable diffuser"]["reason"]
    assert g["led strip 5V current"]["state"] in ("active", "pursued")


def test_design_options_chosen_and_set_aside_with_reasons():
    txt = """Options considered:
1. **Rigid panels on a root pivot** - chosen. One joint per side.
2. Feathered wing (LisHawk): closer to a bird, but dozens of thin parts that flutter. Rejected for a first build.
3. Tailless that sweeps: nose-heavy with nothing to trim it. Rejected.
"""
    o = T.design_options(txt)
    assert [(a[:12], c) for a, c, _ in o] == [("Rigid panels", True), ("Feathered wi", False), ("Tailless tha", False)]
    assert "flutter" in o[1][2]
    g = T.from_project(ROOT / "projects" / "drone_foldable_wings")
    opts = [n for n in g["nodes"] if n["kind"] == "option"]
    assert any(n["state"] == "chosen" for n in opts) and any(n["state"] == "set_aside" and n["reason"] for n in opts)
    assert sum(n["kind"] == "source" for n in g["nodes"]) >= 10 and all("words" not in n for n in g["nodes"])


def test_plain_notes_drop_code_paths_and_links():
    t = T.plain("Read `kerf/x.py` and https://a.b/c then **decided** to use /repo/parts/hub.py. More text.")
    assert "http" not in t and "kerf/x.py" not in t and "*" not in t and "More text" not in t
    t = T.plain("The `servo` in /a/b/c.py is weak. Second sentence.")
    assert "servo" not in t and "/a/b" not in t and t.endswith("weak.")


@pytest.mark.browser
def test_studio_draws_it_live_and_for_a_project(server, tmp_path):  # noqa: F811
    """The job panel shows a one-line strip by itself once research starts; it opens the full story, which reads top to
    bottom (asked -> looked into -> decided -> building), keeps still between polls and never overlaps or cuts labels."""
    j = studio.start_job("design", "servo_link", [sys.executable, str(FAKE), "0.8"], "New design: hawk drone",
                         parse=studio._claude_lines, env={"KERF_STUDIO_JOB": "servo_link"})
    out = _browser(server + "/", f"""
await p.waitForFunction(() => typeof watch === 'function' && window.TW);
await p.evaluate(() => watch('{j.id}'));
out.hiddenAtStart = await p.evaluate(() => document.querySelector('#mctw').hidden);
await p.waitForSelector('#mctw:not([hidden]) .twv.strip', {{timeout: 15000}});
out.strip = await p.textContent('#mctw .twv.strip');
await p.click('#mctw .twv.strip button.open');
await p.waitForSelector('.twmodal .twv.full .twc.q', {{timeout: 15000}});
out.steerButtons = await p.$$eval('.twmodal [data-steer]', e => e.length);
await p.click('.twmodal .twc.q [data-steer=focus]');
await p.waitForSelector('.twmodal .steer .sd', {{timeout: 8000}});
out.steerSaid = await p.textContent('.twmodal .steer .sd');
await p.waitForFunction(() => !/Now/.test(document.querySelector('.twmodal .nowt').textContent), null, {{timeout: 30000}});
await p.waitForTimeout(400);
out.steps = await p.$$eval('.twmodal .st h4', e => e.map(x => x.firstChild.textContent));
out.questions = await p.$$eval('.twmodal .twc.q', e => e.length);
out.sources = await p.$$eval('.twmodal .src', e => e.length);
out.building = await p.$$eval('.twmodal .steps li', e => e.map(x => x.textContent));
await p.screenshot({{path: '{tmp_path}/live.png'}});
await p.click('#twclose');
await p.evaluate(() => closeMc());
await p.evaluate(() => showDecided('drone_foldable_wings'));
await p.waitForSelector('.twmodal .twc.opt', {{timeout: 15000}});
const rects = () => p.$$eval('.twmodal .qt', e => e.map(x => {{ const r = x.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom, x.scrollWidth <= x.clientWidth + 1]; }}));
const ra = await rects(); await p.waitForTimeout(2500); const rb = await rects();
out.still = JSON.stringify(ra) === JSON.stringify(rb);
out.fits = ra.every(r => r[4]);
out.overlap = ra.some((r, i) => ra.some((q, k) => k > i && r[0] < q[2] - 1 && q[0] < r[2] - 1 && r[1] < q[3] - 1 && q[1] < r[3] - 1));
out.opts = await p.$$eval('.twmodal .twc.opt', e => e.map(x => x.className));
out.why = await p.$$eval('.twmodal .twc.opt .why', e => e.length);
out.steerOnFinished = await p.$$eval('.twmodal [data-steer]', e => e.length);
await p.screenshot({{path: '{tmp_path}/project.png'}});
await p.evaluate(() => document.documentElement.dataset.theme = 'light');
await p.screenshot({{path: '{tmp_path}/project_light.png'}});""", tmp_path)
    j.proc.wait()
    assert out["errs"] == [], out
    assert out["hiddenAtStart"] and out["strip"].split("·")[0].strip() in ("Researching", "Deciding", "Building", "Finished"), out
    assert out["steerButtons"] >= 2 and "focus" in out["steerSaid"], out
    assert out["steps"] == ["You asked", "What it looked into", "What it decided", "What it's building"], out
    assert out["questions"] >= 3 and out["sources"] >= 2 and any("hub" in t for t in out["building"]), out
    assert out["still"] and out["fits"] and not out["overlap"], out                  # calm: no motion, readable labels
    assert any("chosen" in c for c in out["opts"]) and any("aside" in c for c in out["opts"]) and out["why"] >= 2, out
    assert out["steerOnFinished"] == 0, out                                          # nothing to steer once it is done
    steer_entries = T_steer.read("servo_link")
    T_steer.reset("servo_link")
    assert steer_entries and steer_entries[0]["action"] == "focus", steer_entries
    import shutil
    for f in ("live", "project", "project_light"):
        shutil.copy(tmp_path / f"{f}.png", ROOT / ".cache" / f"tw_{f}.png")


def test_steering_reaches_the_job_once_through_the_hook_and_resets_per_job(tmp_path, monkeypatch):
    import os
    import subprocess
    monkeypatch.setattr(T_steer, "DIR", tmp_path)
    T_steer.add("demo", "focus", "Research morphing-wing drones", node="n1")
    T_steer.add("demo", "skip", "Research morphing-wing drones", node="n1")    # the latest word on one question wins
    T_steer.add("demo", "note", text="keep it under 200 g")
    assert [e["action"] for e in T_steer.read("demo")] == ["skip", "note"]
    for bad in (("shout", "x", ""), ("note", "", ""), ("focus", "", "")):
        try:
            T_steer.add("demo", *bad)
            raise AssertionError(bad)
        except ValueError:
            pass
    # the real hook, as Claude Code runs it: prints extra context once, then nothing; untouched without a Studio job
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT), "KERF_STUDIO_JOB": "demo_steer_test"}
    T_steer.DIR = ROOT / ".cache" / "studio" / "steer"          # the hook runs as its own process: the real folder
    real = T_steer.path("demo_steer_test")
    try:
        T_steer.add("demo_steer_test", "focus", "folding-wing gliders", node="n4")
        hook = ROOT / ".claude" / "hooks" / "steer.py"
        r1 = subprocess.run([sys.executable, str(hook)], input="{}", capture_output=True, text=True, env=env)
        msg = json.loads(r1.stdout)["hookSpecificOutput"]["additionalContext"]
        assert "Focus on: folding-wing gliders" in msg and "don't stop" in msg
        assert T_steer.read("demo_steer_test")[0]["delivered"]
        r2 = subprocess.run([sys.executable, str(hook)], input="{}", capture_output=True, text=True, env=env)
        assert r2.stdout.strip() == "" and r2.returncode == 0
        r3 = subprocess.run([sys.executable, str(hook)], input="{}", capture_output=True, text=True,
                            env={k: v for k, v in env.items() if k != "KERF_STUDIO_JOB"})
        assert r3.stdout.strip() == ""
        # settings.json runs the hook on every tool only through a guard that is a no-op without a Studio job
        cmd = [h for e in json.loads((ROOT / ".claude/settings.json").read_text())["hooks"]["PostToolUse"]
               for h in e["hooks"] if "steer.py" in h["command"]][0]["command"]
        assert cmd.startswith('[ -n "$KERF_STUDIO_JOB" ]') and "steer/$KERF_STUDIO_JOB.json" in cmd
        # a new Studio job on the project starts with no leftover steering
        T_steer.add("demo_steer_test", "note", text="old")
        jb = studio.start_job("design", "demo_steer_test", [sys.executable, "-c", "pass"], "x", env={"KERF_STUDIO_JOB": "demo_steer_test"})
        assert not real.exists()
        jb.proc.wait()
    finally:
        real.unlink(missing_ok=True)


def test_steering_api_only_for_a_running_design_job(server):  # noqa: F811
    from test_studio import _post
    j = studio.start_job("design", "servo_link", [sys.executable, str(FAKE), "0.5"], "New design: x", parse=studio._claude_lines,
                         env={"KERF_STUDIO_JOB": "servo_link"})
    try:
        code, body = _post(server + "/api/steer", {"job": j.id, "action": "note", "text": "prefer M3 screws"})
        assert code == 200 and body["action"] == "note", body
        code, body = _post(server + "/api/steer", {"job": j.id, "action": "nope", "label": "x"})
        assert code >= 400 and "focus" in body["error"], body
        code, body = _post(server + "/api/steer", {"job": "missing", "action": "note", "text": "x"})
        assert code == 404
        with urllib.request.urlopen(f"{server}/api/thoughtweb?job={j.id}") as r:
            d = json.loads(r.read())
        assert d["steerable"] is True and d["steer"][0]["text"] == "prefer M3 screws"
    finally:
        j.proc.wait()
        deadline = time.time() + 10
        while j.state == "running" and time.time() < deadline:
            time.sleep(0.1)
    code, body = _post(server + "/api/steer", {"job": j.id, "action": "note", "text": "too late"})
    assert code >= 400 and "finished" in body["error"], body
    T_steer.reset("servo_link")


def test_options_point_back_to_the_research_they_came_from():
    w = T.Web("a folding drone")
    w.event({"k": "tool", "name": "WebSearch", "query": "rigid wing panels root pivot servo"})
    w.event({"k": "tool", "name": "Write", "path": "/r/projects/x/DESIGN.md"})
    w.options([("Rigid panels on a root pivot", True, "one joint per side, prints flat"), ("Feathered wing", False, "dozens of parts")])
    g = {n["label"]: n for n in w.finish().json()["nodes"]}
    assert g["Rigid panels on a root pivot"]["based_on"] == g["rigid wing panels root pivot servo"]["id"]
    assert "based_on" not in g["Feathered wing"]
