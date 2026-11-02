"""User-facing bug sweep (Spencer, 2026-11-02): things a user does that used to go wrong."""
import json
import urllib.request

import pytest

from kerf import bambu, studio
from test_studio import _browser, server  # noqa: F401  (fixture)


def test_typed_names_are_cleaned_not_rejected():
    assert studio.slug("Hawk Drone") == "hawk_drone" and studio.slug(" desk-arm v2! ") == "desk_arm_v2"
    assert studio.NAME_RE.match(studio.slug("My  Cool---Thing"))


def test_no_fix_and_no_silent_edits_on_a_project_another_session_is_editing(monkeypatch):
    monkeypatch.setattr(studio, "_worked_on", lambda n: True)
    monkeypatch.setattr(studio, "_report", lambda d: {"ok": False, "problems": ["x"]})
    ok, why = studio.fixable("servo_link")
    assert not ok and "another Claude session" in why           # auto-fix and the Fix button stand down
    with pytest.raises(studio.Claimed):
        studio.guard_claimed("servo_link", False)
    studio.guard_claimed("servo_link", True)                   # the user said "change it anyway"


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_save_asks_before_changing_a_claimed_project(server, monkeypatch):  # noqa: F811
    monkeypatch.setattr(studio, "_worked_on", lambda n: True)
    monkeypatch.setattr(studio, "write_params", lambda path, vals: list(vals))   # never touch the real project.yaml
    code, j = _post(server + "/api/save", {"project": "servo_link", "values": {"arm_len": 80}})
    assert code == 409 and j["claimed"] and "Change it anyway" in j["error"]
    code, j = _post(server + "/api/save", {"project": "servo_link", "values": {"arm_len": 80}, "override": True})
    assert code == 200 and j["changed"] == ["arm_len"]


def test_wrong_access_code_says_so():
    class Link:
        rc, reports = 5, []
        def publish(self, p): raise AssertionError("must not publish after a refused login")
    with pytest.raises(PermissionError, match="refused the access code"):
        bambu.status({"printer": {"host": "10.0.0.2", "serial": "S", "access_code": "x"}}, link=Link())


def test_page_keeps_unsaved_tune_values_and_reuses_running_jobs(server, tmp_path):  # noqa: F811
    out = _browser(server + "/", """
await p.waitForFunction(() => typeof select === 'function' && S.projects.length > 1);
const names = await p.evaluate(() => S.projects.map(x => x.name));
await p.evaluate(n => select(n), names[0]); await p.waitForFunction(n => S.detail && S.detail.name === n, names[0]);
await p.evaluate(() => { S.edits = {x: 1}; });
p.once('dialog', d => d.dismiss());                          // "Leave and discard?" -> No
await p.evaluate(n => select(n), names[1]);
out.stayed = await p.evaluate(n => S.sel === n && Object.keys(S.edits).length === 1, names[0]);
p.once('dialog', d => d.accept());                           // -> Yes
await p.evaluate(n => select(n), names[1]);
await p.waitForFunction(n => S.detail && S.detail.name === n, names[1]);
out.left = await p.evaluate(() => Object.keys(S.edits).length === 0);
out.slug = await p.evaluate(() => slugName(' Hawk Drone 2 '));
out.uniq = await p.evaluate(n => uniqueName(n) !== n && uniqueName(n).startsWith(n + '_'), names[0]);
out.opened = await p.evaluate(n => { S.jobsList = [{id: 'j1', state: 'running', project: n}]; let w = null; window.watch = id => { w = id; }; return openRunning(n) && w === 'j1'; }, names[1]);
out.comma = await p.evaluate(() => { const k = S.detail.params[0] && S.detail.params[0].key; if (!k) return true;
  const p0 = S.detail.params[0]; setParam(k, String(p0.value).replace('.', ',')); return !(k in S.edits) || Math.abs(S.edits[k] - p0.value) < 1e-9; });""", tmp_path)
    assert out["errs"] == [], out
    assert out["stayed"] and out["left"] and out["slug"] == "hawk_drone_2" and out["uniq"] and out["opened"] and out["comma"], out
