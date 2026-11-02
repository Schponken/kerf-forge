"""Kerf Studio: param writing keeps the file intact, trials never touch the real project, API basics + safety."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest
import yaml

from kerf import studio

YAML = """name: t   # title
params:
  arm_len: {value: 100, min: 60, max: 140, step: 1, label: Arm length}   # pivot to tip
  plain: 7.5   # a bare value
  other: {value: 3, min: 1, max: 5}
parts: {}
"""


def test_write_params_keeps_comments_and_checks_ranges(tmp_path):
    f = tmp_path / "project.yaml"
    f.write_text(YAML)
    assert sorted(studio.write_params(f, {"arm_len": 120, "plain": 8})) == ["arm_len", "plain"]
    txt = f.read_text()
    assert "# pivot to tip" in txt and "# a bare value" in txt and "# title" in txt
    d = yaml.safe_load(txt)
    assert d["params"]["arm_len"]["value"] == 120 and d["params"]["plain"] == 8 and d["params"]["other"]["value"] == 3
    with pytest.raises(ValueError, match="outside its allowed range"):
        studio.write_params(f, {"arm_len": 200})
    with pytest.raises(ValueError, match="unknown param"):
        studio.write_params(f, {"nope": 1})
    assert yaml.safe_load(f.read_text())["params"]["arm_len"]["value"] == 120   # failed writes change nothing


def test_trial_copy_leaves_the_real_project_alone(tmp_path, monkeypatch):
    proj = tmp_path / "projects" / "demo"
    (proj / "parts").mkdir(parents=True)
    (proj / "project.yaml").write_text(YAML)
    (proj / "review.json").write_text("{}")
    (proj / "out").mkdir()
    monkeypatch.setattr(studio, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(studio, "TRIALS", tmp_path / "trials")
    dst = studio.trial_copy("demo", {"arm_len": 90})
    assert yaml.safe_load((dst / "project.yaml").read_text())["params"]["arm_len"]["value"] == 90
    assert yaml.safe_load((proj / "project.yaml").read_text())["params"]["arm_len"]["value"] == 100
    assert not (dst / "out").exists() and not (dst / "review.json").exists()


def test_claude_stream_lines():
    ev = {"type": "assistant", "message": {"content": [{"type": "text", "text": "Researching"},
                                                       {"type": "tool_use", "name": "Bash", "input": {"command": "kerf check x\nmore"}}]}}
    lines = studio._claude_lines(json.dumps(ev))
    assert [line for line in lines if not line.startswith("@@")] == ["Researching", "  > Bash: kerf check x"]
    assert [json.loads(line[2:]) for line in lines if line.startswith("@@")] == [
        {"k": "note", "text": "Researching"},
        {"k": "tool", "name": "Bash", "what": "kerf check x", "phase": "check",
         "query": "", "url": "", "path": "", "cmd": "kerf check x"},
    ]


@pytest.mark.parametrize("tool,inp,phase", [
    ("WebSearch", {"query": "servo arm"}, "research"),
    ("Agent", {"subagent_type": "design-researcher"}, "research"),
    ("Write", {"file_path": "/r/projects/x/DESIGN.md"}, "plan"),
    ("Edit", {"file_path": "/r/projects/x/project.yaml"}, "contract"),
    ("Write", {"file_path": "/r/projects/x/parts/arm.py"}, "parts"),
    ("Agent", {"subagent_type": "part-designer", "description": "arm"}, "parts"),
    ("Bash", {"command": ".venv/bin/kerf build x"}, "build"),
    ("Agent", {"subagent_type": "design-reviewer"}, "review"),
    ("Bash", {"command": "git pull --rebase && git push"}, "ship"),
    ("Read", {"file_path": "/r/CLAUDE.md"}, None)])
def test_design_phase_classifier(tool, inp, phase):
    assert studio._phase(tool, inp) == phase
    assert studio._claude_lines("plain text") == ["plain text"]


@pytest.fixture(scope="module")
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), studio.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _get(url):
    with urllib.request.urlopen(url) as r:
        return r.status, r.read()


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_api_pages_and_projects(server):
    code, html = _get(server + "/")
    assert code == 200 and b"Kerf Studio" in html
    code, body = _get(server + "/api/projects")
    names = [p["name"] for p in json.loads(body)["projects"]]
    assert "servo_link" in names
    code, body = _get(server + "/api/project/servo_link")
    d = json.loads(body)
    assert any(p["key"] == "arm_len" for p in d["params"]) and "DESIGN.md" in d["docs"]
    code, body = _get(server + "/files/servo_link/DESIGN.md")
    assert code == 200 and body.startswith(b"#")


def test_api_refuses_bad_input(server):
    for path in ("/files/servo_link/../../CLAUDE.md", "/files/servo_link/..%2F..%2FCLAUDE.md", "/api/project/nope"):
        with pytest.raises(urllib.error.HTTPError) as e:
            _get(server + path)
        assert e.value.code == 404
    assert _post(server + "/api/run", {"project": "nope", "action": "check"})[0] == 404
    assert _post(server + "/api/run", {"project": "servo_link", "action": "rm"})[0] == 400
    assert _post(server + "/api/save", {"project": "servo_link", "values": {"arm_len": 9999}})[0] == 400
    assert _post(server + "/api/new", {"name": "Bad Name!", "description": "x"})[0] == 400
    assert _post(server + "/api/new", {"name": "servo_link", "description": "x"})[0] == 400


@pytest.mark.slow
def test_progress_events_are_off_by_default_and_ordered_when_on(capsys, monkeypatch, tmp_path):
    from kerf import pipeline, progress
    monkeypatch.delenv("KERF_PROGRESS", raising=False)
    progress.emit("x")
    assert capsys.readouterr().out == ""
    monkeypatch.setenv("KERF_PROGRESS", "1")
    import shutil
    src = studio.PROJECTS / "servo_link"     # a copy: a test must never overwrite a real project's out/report.json
    dst = tmp_path / "servo_link"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("out", "__pycache__"))
    pipeline.run(str(dst), sweeps=False)
    ev = [json.loads(l[2:]) for l in capsys.readouterr().out.splitlines() if l.startswith("@@")]
    stages = [e["stage"] for e in ev if e["k"] == "stage"]
    assert ev[0]["k"] == "start" and ev[-1]["k"] == "done" and stages == ["build", "print", "fit", "requirements"]
    assert {e["id"] for e in ev if e["k"] == "part"} == set(ev[0]["parts"])
    assert [e["id"] for e in ev if e["k"] == "req"] == ev[0]["reqs"]


def _start(tmp_env, *extra):
    import os, socket, subprocess, sys, time
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    p = subprocess.Popen([sys.executable, "-m", "kerf.cli", "studio", "--no-open", "--port", str(port), *extra],
                         env={**os.environ, **tmp_env}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    url = f"http://127.0.0.1:{port}"
    for _ in range(80):
        try:
            urllib.request.urlopen(url + "/api/jobs", timeout=1); break
        except Exception:
            time.sleep(0.1)
    return p, url


@pytest.mark.slow
def test_closing_the_last_window_stops_the_server():
    import time
    p, url = _start({"KERF_STUDIO_GRACE": "30"}, "--idle-exit", "60")
    try:
        urllib.request.urlopen(urllib.request.Request(url + "/api/bye", data=b"{}", method="POST"))
        t0 = time.time()
        p.wait(timeout=20)                               # goodbye + 6 s with no other window -> exits
        assert time.time() - t0 < 15 and "closing" in p.stdout.read()
    finally:
        p.kill()


def test_quit_asks_first_when_a_job_runs_and_stays_up_without_idle_limit():
    p, url = _start({})
    try:
        # a trial runs on a scratch copy, so this test never overwrites the real project's report
        code, body = _post(url + "/api/run", {"project": "servo_link", "action": "trial", "values": {}})
        assert code == 200
        code, body = _post(url + "/api/quit", {})
        assert code == 409 and body["running"]           # a job is running: the page asks before quitting
        code, body = _post(url + "/api/quit", {"force": True})
        assert code == 200
        p.wait(timeout=10)
    finally:
        p.kill()


@pytest.mark.slow
def test_a_window_still_open_cancels_the_goodbye():
    import time
    p, url = _start({"KERF_STUDIO_GRACE": "30"}, "--idle-exit", "60")
    try:
        urllib.request.urlopen(urllib.request.Request(url + "/api/bye", data=b"{}", method="POST"))
        for _ in range(4):                                # another window keeps polling every ~3 s
            time.sleep(3)
            urllib.request.urlopen(url + "/api/jobs")
        assert p.poll() is None                           # still running
    finally:
        p.kill()


SPENCER_ERRORS = [   # verbatim from the failed run on Spencer's Mac, 2026-10-31
    ('Ignoring 14 permissions.allow entries from .claude/settings.json: this workspace has not been trusted. Run Claude '
     'Code interactively here once and accept the trust dialog, or set projects["/Users/x/kerf-forge"].'
     'hasTrustDialogAccepted: true in /Users/x/.claude.json.', "trust"),
    ("Failed to authenticate: OAuth session expired and could not be refreshed", "auth"),
]


@pytest.mark.parametrize("line,code", SPENCER_ERRORS)
def test_claude_setup_problems_are_recognised(line, code):
    out = studio._claude_lines(line)
    assert out[0] == line
    assert json.loads(out[-1][2:]) == {"k": "hint", "code": code}


def test_failed_result_is_not_reported_as_success():
    out = studio._claude_lines(json.dumps({"type": "result", "subtype": "success", "is_error": True, "duration_ms": 10}))
    assert "stopped with an error" in out[0]


def test_claude_ready_checks_install_trust_and_sign_in(tmp_path, monkeypatch):
    import subprocess as sp
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(studio, "claude_bin", lambda: None)
    assert studio.claude_ready()["code"] == "missing"
    monkeypatch.setattr(studio, "claude_bin", lambda: "/bin/claude")
    assert studio.claude_ready()["code"] == "trust"                      # no config at all
    (tmp_path / ".claude.json").write_text(json.dumps({"projects": {str(studio.ROOT.parent): {"hasTrustDialogAccepted": True}}}))
    calls = []
    def fake_run(cmd, **kw):
        calls.append(cmd)
        return sp.CompletedProcess(cmd, 0, stdout=json.dumps({"loggedIn": False}), stderr="")
    monkeypatch.setattr(studio.subprocess, "run", fake_run)
    assert studio.claude_ready()["code"] == "auth"                       # trusted via a parent folder, not signed in
    assert calls[-1][1:] == ["auth", "status", "--json"]                 # free status check, no model call
    monkeypatch.setattr(studio.subprocess, "run", lambda cmd, **kw: sp.CompletedProcess(cmd, 0, stdout='{"loggedIn": true}', stderr=""))
    assert studio.claude_ready()["ok"] is True


def test_new_design_refuses_to_start_when_not_ready(monkeypatch):
    monkeypatch.setattr(studio, "claude_ready", lambda: {"ok": False, "code": "auth", "why": "expired"})
    with pytest.raises(studio.ClaudeNotReady):
        studio.new_design("zz_never", "a test")
    assert not (studio.PROJECTS / "zz_never").exists()


def test_a_setup_problem_stops_the_job_as_failed(tmp_path):
    import sys, time
    script = tmp_path / "fake.py"
    script.write_text("import time\nprint('Failed to authenticate: OAuth session expired and could not be refreshed', flush=True)\n"
                      "time.sleep(30)\n")
    j = studio.Job("design", "x", [sys.executable, str(script)], "t", parse=studio._claude_lines)
    for _ in range(50):
        if j.state != "running":
            break
        time.sleep(0.1)
    assert j.state == "failed" and any(e.get("code") == "auth" for e in j.events)


def test_waking_from_sleep_does_not_close_an_open_window(monkeypatch):
    """A Mac that slept for an hour must not look like 'every window closed' the moment it wakes."""
    import threading
    clock = {"t": 1000.0}
    slept = {"done": False}

    def fake_sleep(_):
        if not slept["done"] and clock["t"] >= 1005.0:
            clock["t"] += 3600.0                      # lid closed for an hour
            slept["done"] = True
        else:
            clock["t"] += 1.0

    monkeypatch.setattr(studio.time, "time", lambda: clock["t"])
    monkeypatch.setattr(studio.time, "sleep", fake_sleep)
    monkeypatch.setattr(studio, "busy", lambda: False)
    monkeypatch.setitem(studio.LIFE, "last", 1000.0)
    monkeypatch.setitem(studio.LIFE, "seen", True)
    monkeypatch.setitem(studio.LIFE, "bye", None)
    stopped = []

    class Srv:
        def shutdown(self):
            stopped.append(clock["t"])

    t = threading.Thread(target=studio._watchdog, args=(Srv(), 150.0, 450.0), daemon=True)
    t.start(); t.join(timeout=10)
    assert stopped, "watchdog never finished"
    woke = 1006.0 + 3600.0
    assert stopped[0] - woke >= 149, f"closed {stopped[0] - woke:.0f} s after waking; must wait the idle limit"


def test_detail_lists_the_bring_up_program_and_guide(tmp_path, monkeypatch):
    proj = tmp_path / "projects" / "demo"
    fw = proj / "out" / "firmware" / "demo_bringup"
    fw.mkdir(parents=True)
    (proj / "project.yaml").write_text(YAML)
    (fw / "demo_bringup.ino").write_text("// sketch")
    (proj / "out" / "firmware" / "BRINGUP.md").write_text("# Bring-up")
    monkeypatch.setattr(studio, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(studio, "TRIALS", tmp_path / "trials")
    d = studio.detail("demo")
    assert "out/firmware/demo_bringup/demo_bringup.ino" in d["files"] and "out/firmware/BRINGUP.md" in d["docs"]


def test_times_history_restore_and_export(tmp_path, monkeypatch):
    proj = tmp_path / "projects" / "demo"
    (proj / "parts").mkdir(parents=True)
    (proj / "out" / "plates").mkdir(parents=True)
    (proj / "project.yaml").write_text(YAML)
    (proj / "parts" / "arm.py").write_text("def build(ctx):\n    return ctx.finish(box(ctx.p.arm_len))\n")
    (proj / "out" / "plates" / "plate_1.3mf").write_bytes(b"3mf")
    (proj / "out" / "bom.md").write_text("# BOM")
    (proj / "out" / "report.json").write_text(json.dumps({"ok": True, "params": {"arm_len": 120, "plain": 7.5, "other": 3},
                                                          "requirements": [{"id": "r1", "value": 2.0, "ok": True}],
                                                          "mass": {"printed_g": 10, "device_g": 30}, "seconds": 50,
                                                          "files": {"ship": {"bom": {"total_usd": 12.5, "packs_usd": 40}}}}))
    monkeypatch.setattr(studio, "PROJECTS", tmp_path / "projects")
    monkeypatch.setattr(studio, "TRIALS", tmp_path / "trials")
    monkeypatch.setattr(studio, "TIMES", tmp_path / "times.json")
    monkeypatch.setattr(studio, "HISTORY", tmp_path / "hist")
    assert studio.estimate("demo", "build") == 50                 # no Studio runs yet: the last report's time
    for s in (100, 300, 200):
        studio.record_time("demo", "build", s)
    assert studio.estimate("demo", "build") == 200                # median of the recorded runs
    e = studio.snapshot("demo")
    assert e["cost"] == 12.5 and e["params"]["arm_len"] == 120 and studio.history("demo")[0]["stamp"] == e["stamp"]
    assert studio.restore("demo", e["stamp"]) == ["arm_len"]       # file value 100 -> the version's 120
    assert yaml.safe_load((proj / "project.yaml").read_text())["params"]["arm_len"]["value"] == 120
    assert "# pivot to tip" in (proj / "project.yaml").read_text()  # comments kept
    with pytest.raises(ValueError):
        studio.restore("demo", "../../x")
    import io
    import zipfile
    names = zipfile.ZipFile(io.BytesIO(studio.export_zip("demo"))).namelist()
    assert {"demo/plates/plate_1.3mf", "demo/bom.md", "demo/design/project.yaml", "demo/design/parts/arm.py"} <= set(names)
    d = studio.detail("demo")
    arm = next(p for p in d["params"] if p["key"] == "arm_len")
    assert arm["unit"] == "mm" and arm["unit_assumed"] and arm["affects"]["parts"] == ["arm"]
    assert d["summary_numbers"]["cost_usd"] == 12.5 and d["summary_numbers"]["filament_g"] == 10


def test_param_units():
    assert studio.param_unit("x", {"unit": "N"}) == ("N", False)
    assert studio.param_unit("mcp_max", {"label": "mcp flexion range (deg)"}) == ("°", True)
    assert studio.param_unit("gear_z", {"label": "Pinion teeth"}) == ("teeth", True)
    assert studio.param_unit("arm_t", {"label": "Arm thickness"}) == ("mm", True)


def _browser(url, steps_js, tmp_path):
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    js = tmp_path / "b.mjs"
    js.write_text(f"""import {{ browser }} from '{root}/tests/browser.mjs';
const b = await browser(); const p = await b.newPage({{ viewport: {{ width: 1300, height: 900 }} }}); const errs = [];
p.on('pageerror', e => errs.push(e.message));
await p.goto('{url}'); const out = {{}};
{steps_js}
console.log(JSON.stringify({{ errs, ...out }})); await b.close();""")
    r = subprocess.run(["node", str(js)], capture_output=True, text=True, timeout=180)
    assert r.stdout.strip(), r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


@pytest.mark.browser
def test_studio_page_shows_numbers_units_effects_history_and_export(server, tmp_path):
    out = _browser(server + "/", """
await p.waitForSelector('.pitem'); await p.waitForSelector('#tabs'); await p.click('text=Servo test rig');
await p.waitForFunction(() => (document.querySelector('.head h1') || {}).textContent === 'Servo test rig');
out.export = await p.getAttribute('a[download][href^="/export/"]', 'href');
await p.click('.tab[data-t=tune]'); await p.waitForSelector('.param');
out.units = await p.$$eval('.param .unit', e => e.length); out.affects = await p.$$eval('.param .affects', e => e.length);
await p.click('.tab[data-t=history]'); await p.waitForTimeout(300);
out.history = await p.evaluate(() => document.querySelector('#tabbody').textContent.length > 20);""", tmp_path)
    assert out["errs"] == [] and out["export"] == "/export/servo_link.zip", out
    assert out["units"] > 0 and out["affects"] > 0 and out["history"], out


@pytest.mark.browser
def test_welcome_when_there_are_no_projects(tmp_path, monkeypatch):
    (tmp_path / "projects").mkdir()
    monkeypatch.setattr(studio, "PROJECTS", tmp_path / "projects")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), studio.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        out = _browser(f"http://127.0.0.1:{srv.server_address[1]}/", """
await p.waitForSelector('text=Welcome to Kerf Studio', { timeout: 15000 }); out.welcome = true;""", tmp_path)
    finally:
        srv.shutdown()
    assert out["errs"] == [] and out["welcome"], out


@pytest.mark.all_projects
def test_every_finished_project_states_its_param_units():
    """Studio shows each slider's unit; the six finished projects state it (`unit:`) rather than leaving it assumed."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "projects"
    missing = [f"{n}.{k}" for n in ("bionic_finger", "fpv_5in", "pan_tilt", "robot_arm", "servo_link", "tvc_drone")
               for k, v in (yaml.safe_load((root / n / "project.yaml").read_text(encoding="utf-8")).get("params") or {}).items()
               if isinstance(v, dict) and "unit" not in v]
    assert missing == []


def test_brief_carries_intake_inventory_and_the_picked_option(tmp_path, monkeypatch):
    from kerf import ship
    inv = tmp_path / "inv.json"
    inv.write_text(json.dumps({"items": {"servos.SG90": 2}}))
    monkeypatch.setattr(ship, "INVENTORY", inv)
    b = studio.brief("a desk gripper", {"budget": "40", "power": "USB", "bogus": "x"},
                     {"title": "Rack jaws", "summary": "two racks", "purchased": [{"key": "servos.SG90", "qty": 1}]})
    assert "a desk gripper" in b and "40" in b and "USB" in b and "bogus" not in b
    assert "servos.SG90 x2" in b and "Rack jaws" in b and "servos.SG90 x1" in b
    assert "use_story" not in b
    b = studio.brief("a desk gripper", {"who": "me at my desk", "goes_wrong": "knocked off the desk"})
    assert "who uses it: me at my desk" in b and "knocked off the desk" in b and "`use_story`" in b


def test_read_quote_checks_its_options(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, "QUOTES", tmp_path)
    with pytest.raises(ValueError, match="no quote yet"):
        studio.read_quote("arm")
    (tmp_path / "arm.json").write_text(json.dumps({"options": [{"title": "A", "summary": "s", "parts_printed": 3,
                                                                "cost_usd": 20}]}))
    with pytest.raises(ValueError, match="print_hours"):
        studio.read_quote("arm")
    good = {"title": "A", "summary": "s", "parts_printed": 3, "cost_usd": 20, "print_hours": 4}
    (tmp_path / "arm.json").write_text(json.dumps({"options": [good, good | {"title": "B"}], "recommended": 1}))
    assert [o["title"] for o in studio.read_quote("arm")["options"]] == ["A", "B"]
    (tmp_path / "arm.json").write_text(json.dumps({"options": [good] * 4}))
    with pytest.raises(ValueError, match="1-3"):
        studio.read_quote("arm")


def test_save_inventory_keeps_only_known_parts(tmp_path, monkeypatch):
    from kerf import ship
    inv = tmp_path / "inv.json"
    inv.write_text(json.dumps({"_note": "mine", "items": {}}))
    monkeypatch.setattr(ship, "INVENTORY", inv)
    assert studio.save_inventory({"servos.SG90": "2", "screw:M3x8:socket": 0}) == {"servos.SG90": 2}
    assert json.loads(inv.read_text()) == {"_note": "mine", "items": {"servos.SG90": 2}}
    assert ship.load_inventory() == {"servos.SG90": 2.0}
    with pytest.raises(ValueError, match="unknown part"):
        studio.save_inventory({"servos.NOPE": 1})
    with pytest.raises(ValueError, match="0 or more"):
        studio.save_inventory({"servos.SG90": -1})
    assert any(k["key"] == "servos.SG90" for k in studio.inventory_keys())


@pytest.mark.browser
def test_new_design_page_has_intake_quote_options_and_my_parts(server, tmp_path, monkeypatch):
    from kerf import ship
    inv = tmp_path / "inv.json"
    inv.write_text(json.dumps({"items": {}}))
    monkeypatch.setattr(ship, "INVENTORY", inv)
    qd = tmp_path / "quotes"
    qd.mkdir()
    monkeypatch.setattr(studio, "QUOTES", qd)
    good = {"title": "Rack jaws", "summary": "two racks", "parts_printed": 5, "cost_usd": 21.5, "print_hours": 6,
            "risks": ["servo stall"]}
    (qd / "grip.json").write_text(json.dumps({"options": [good, good | {"title": "Linkage claw"}], "recommended": 1,
                                              "assumptions": ["USB power"]}))
    out = _browser(server + "/", """
await p.waitForSelector('.pitem'); await p.click('#newbtn'); await p.waitForSelector('#i_budget', { timeout: 90000 });
out.intake = await p.$$eval('.igrid label', e => e.length);
await p.evaluate(() => showQuote('grip')); await p.waitForSelector('.qopt');
out.opts = await p.$$eval('.qopt b', e => e.map(x => x.textContent)); out.rec = await p.$eval('.qopt.rec b', e => e.textContent);
await p.click('#nav_parts'); await p.waitForSelector('#invadd');
await p.fill('#invadd', 'servos.SG90'); await p.fill('#invqty', '2'); await p.click('text=Add');
await p.click('button.primary:has-text("Save")'); await p.waitForTimeout(500);""", tmp_path)
    assert out["errs"] == [] and out["intake"] == 9, out      # 6 + the 3 use-story questions
    assert out["opts"] == ["Rack jaws", "Linkage claw"] and out["rec"] == "Linkage claw", out
    assert json.loads(inv.read_text())["items"] == {"servos.SG90": 2}


@pytest.mark.browser
def test_mode_menu_and_ship_needs_its_own_confirmation(server, tmp_path):
    menu = studio.mode_menu("servo_link", studio._report(studio.PROJECTS / "servo_link"))
    assert [m["mode"] for m in menu] == ["sketch", "print", "check", "simulate", "kit", "ship"]
    assert all("no Claude usage" in m["cost"] for m in menu[:-1]) and "printer" in menu[-1]["cost"] and menu[-1]["confirm"]
    code, body = _post(server + "/api/run", {"project": "servo_link", "action": "mode", "mode": "ship"})
    assert code == 400 and "confirmation" in body["error"]                    # nothing started without the click
    code, body = _post(server + "/api/run", {"project": "servo_link", "action": "mode", "mode": "fast"})
    assert code == 400
    out = _browser(server + "/", """
await p.waitForSelector('.pitem'); await p.click('text=Servo test rig');
await p.waitForFunction(() => (document.querySelector('.head h1') || {}).textContent === 'Servo test rig');
await p.click('button:has-text("Depth")'); await p.waitForSelector('#modemenu.open');
out.modes = await p.$$eval('#modemenu button b', e => e.map(x => x.textContent));
await p.click('text=Ship it…'); await p.waitForSelector('#shipask');
out.ask = await p.textContent('#shipask h3');
await p.click('#shipno'); out.closed = await p.$('#shipask') === null;""", tmp_path)
    assert out["errs"] == [], out
    assert out["modes"] == ["Sketch", "Print it", "Check it", "Simulate it", "Build kit", "📦 Ship it…"], out
    assert "Ship it" in out["ask"] and out["closed"], out


def test_optimise_is_offered_where_the_project_declares_it():
    assert studio._yaml(studio.PROJECTS / "fpv_5in").get("optimise")
    assert not (studio._yaml(studio.PROJECTS / "servo_link") or {}).get("optimise")
    page = (studio.ASSETS / "studio.html").read_text() if hasattr(studio, "ASSETS") else ""
    assert not page or "run('optimise')" in page


def test_failed_build_starts_a_fix_job_once_per_design_state(monkeypatch):
    from types import SimpleNamespace as NS
    reports = {"good": {"ok": True}, "bad": {"ok": False, "problems": ["a and b overlap"], "fingerprint": "f1"},
               "wip": {"ok": False, "problems": ["design in progress"], "stubs": ["hull"], "fingerprint": "f2"}}
    monkeypatch.setattr(studio, "_report", lambda d: reports.get(d.name))
    monkeypatch.setattr(studio, "claude_bin", lambda: "/usr/bin/claude")
    monkeypatch.setattr(studio, "settings", lambda: {"notify": False, "sound": False, "autofix": True})
    monkeypatch.setattr(studio, "AUTOFIXED", {})
    started = []
    monkeypatch.setattr(studio, "fix_job", lambda name: started.append(name) or NS(id="j"))
    job = lambda name, kind="build": NS(kind=kind, project=name, state="failed")   # noqa: E731
    assert studio.fixable("good")[0] is False and "being designed" in studio.fixable("wip")[1]
    for n in ("good", "wip", "bad", "bad"):
        studio.auto_fix(job(n))
    assert started == ["bad"]                                  # passed / mid-design: none; the same failure: only once
    studio.auto_fix(job("bad", kind="edit"))                   # a change request's own build is not re-fixed
    reports["bad"]["fingerprint"] = "f3"                       # the design changed and failed again: one more try
    studio.auto_fix(job("bad"))
    assert started == ["bad", "bad"]
    monkeypatch.setattr(studio, "settings", lambda: {"autofix": False})
    reports["bad"]["fingerprint"] = "f4"
    studio.auto_fix(job("bad"))
    assert started == ["bad", "bad"]                           # switched off: the Fix button only


def test_printer_setup_validates_and_never_returns_the_code(monkeypatch, tmp_path):
    from kerf import bambu
    cfg = tmp_path / "b.json"
    monkeypatch.setenv("KERF_BAMBU_CONFIG", str(cfg))
    with pytest.raises(ValueError, match="printer IP"):
        studio.printer_setup("printer.local", "abc")
    monkeypatch.setattr(bambu, "setup_printer", lambda h, c, s, say=None: bambu.save_config(
        {"printer": {"host": h, "serial": "SER9", "access_code": c}}) and {"serial": "SER9", "status": {"gcode_state": "IDLE"}})
    r = studio.printer_setup("10.11.16.171", "abcd1234")
    assert r["serial"] == "SER9" and "abcd1234" not in str(r)
    info = studio.printer_info()
    assert info == {"configured": True, "host": "10.11.16.171", "serial": "SER9"} and "abcd1234" not in str(info)
