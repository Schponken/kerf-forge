"""Thought web (kerf/thoughtweb.py + assets/thoughtweb.js): a simplified, near-live map built only from a job's visible
actions and notes; branches, sources, set-aside options and the build trunk; the Studio panel and project modal draw it."""
import json
import sys
import time
from pathlib import Path

from kerf import studio, thoughtweb as T
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


def test_studio_draws_it_live_and_for_a_project(server, tmp_path):  # noqa: F811
    j = studio.start_job("design", "servo_link", [sys.executable, str(FAKE), "0.25"], "New design: hawk drone",
                         parse=studio._claude_lines)
    out = _browser(server + "/", f"""
await p.waitForFunction(() => typeof watch === 'function' && window.TW);
await p.evaluate(() => watch('{j.id}'));
await p.waitForSelector('#mctw .tw .n.idea', {{timeout: 15000}});
await p.waitForTimeout(3500);
out.ideas = await p.$$eval('#mctw .n.idea', e => e.length);
out.sources = await p.$$eval('#mctw .n.source', e => e.length);
out.now = await p.textContent('#mctw .now');
out.feed = await p.$$eval('#mc .feed .fi .w', e => e.map(x => x.textContent));
out.tips = await p.$$eval('#mc .feed .fi', e => e.map(x => x.title));
out.scene = await p.textContent('#mc .scene b');
await p.screenshot({{path: '{tmp_path}/live.png'}});
await p.evaluate(() => closeMc());
await p.evaluate(() => showDecided('drone_foldable_wings'));
await p.waitForSelector('.twmodal .n.option', {{timeout: 15000}});
await p.waitForTimeout(2500);
out.opts = await p.$$eval('.twmodal .n.option', e => e.map(x => x.getAttribute('class')));
await p.screenshot({{path: '{tmp_path}/project.png'}});""", tmp_path)
    assert out["errs"] == [], out
    assert out["ideas"] >= 3 and out["sources"] >= 2 and ":" in out["now"]
    feed = " | ".join(out["feed"])   # plain-language narration, newest first; raw tool + argument kept on hover
    for said in ("Testing that everything fits", "Drawing the hub", "Writing the plan", "real part sizes in the parts catalog",
                 "Reading a page on shop.iflight.com", "Looking up “2806.5 motor thrust"):
        assert said in feed, feed
    assert any(t.startswith("Bash: ") for t in out["tips"]), out["tips"]
    assert out["scene"] in ("Testing and fixing", "Finished"), out["scene"]   # the workshop scene for the current stage
    assert any("chosen" in c for c in out["opts"]) and any("set_aside" in c for c in out["opts"])
    import shutil
    shutil.copy(tmp_path / "live.png", ROOT / ".cache" / "tw_live.png")
    shutil.copy(tmp_path / "project.png", ROOT / ".cache" / "tw_project.png")
