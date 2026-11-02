"""Plain-words problems (kerf/explain.py): every check message becomes a card a non-engineer can read (part, what is
wrong, why it matters, usual fix, raw detail kept), failed requirements are shown once, and the work status says
whether a Studio job or a fresh claim is on the project."""
import time

from kerf import explain, studio

MSGS = {
    "pod: exported mesh is not watertight": ("print", "pod", "hole in the surface"),
    "nose: walls as thin as 0.78 mm (2nd percentile); minimum is 0.8 mm, aim for 1.2+": ("print", "nose", "0.78 mm"),
    "arm is 2 separate solids; a printed part must be one piece": ("print", "arm", "2 loose pieces"),
    "pod: M3 heatset hole (group 'hatch') at [4.0, -30.0, 20.3] has less than 1.6 mm of wall around it (82 % of a ring)": ("fit", "pod", "too close to the edge"),
    "top_plate and strap_l overlap by 0.13 mm3 in the assembled position": ("fit", "top_plate ↔ strap_l", "same space"),
    "moving joint 'elevon_l' collides: elevon_l hits wing_l1 (3.1 mm3) at max": ("motion", "elevon_l ↔ wing_l1", "crash"),
    "fastener group 'nose': M3 hole in nose at [1, 2, 3] has no matching receiver hole (aligned within 0.15 mm)": ("fit", "nose", "no partner"),
    "fastener group 'lid': lid sits 0.40 mm off box along the screw axis (parts not clamped together)": ("fit", "lid ↔ box", "don't touch"),
    "wiring 'main' runs through pod at rest (12 mm3): route it round, through a hole, or ...": ("wiring", "pod", "solid plastic"),
    "wiring 'servo': length_mm 100 < 120 mm (routed 118 mm)": ("wiring", None, "too short"),
    "drawing of horn_l could not be made: RuntimeError: horn_l: no sheet up to A2": ("files", "horn_l", "drawing"),
    "body failed to build: ValueError: x": ("build", "body", "could not be built"),
    "requirement 'pod_strength': part pod has no load_axis, so its print orientation is not judged": ("engineering", None, "set up wrong"),
}


def test_every_known_message_gets_a_plain_card():
    for msg, (kind, part, words) in MSGS.items():
        c = explain.explain(msg)
        assert c["kind"] == kind, msg
        assert c["part"] == part, msg
        assert words.lower() in (c["title"] + " " + c["why"]).lower(), (msg, c)
        assert c["detail"] == msg and c["why"] and c["fix"]
        assert "{" not in c["title"] + c["why"] + c["fix"]                  # every placeholder filled


def test_unknown_message_still_shown():
    c = explain.explain("gizmo: the flux capacitor is misaligned; turn it", parts=["gizmo"])
    assert c["part"] == "gizmo" and c["title"] == "The flux capacitor is misaligned" and c["detail"].startswith("gizmo:")


def test_failed_requirement_shown_once_in_plain_words():
    rep = {"problems": ["requirement 'twr' failed: 3691 g / 629 g = 5.87:1 (min 6)", "a and b overlap by 1 mm3 in the assembled position"],
           "requirements": [{"id": "twr", "check": "thrust_to_weight", "unit": ":1", "bound": "min", "ok": False, "value": 5.87,
                             "limit": 6, "detail": "3691 g thrust / 629 g", "why": "freestyle needs 6:1"},
                            {"id": "m", "check": "mass_max", "ok": True, "value": 1, "limit": 2}]}
    cards = explain.cards(rep)
    assert len(cards) == 2
    req = cards[-1]
    assert req["title"] == "Thrust vs weight: target missed" and "It is 5.87:1; it needs to be at least 6:1." in req["why"]


def test_work_status():
    now = time.time()
    claims = [{"item": "E7 `fpv_wing` - 1 m wing: REFERENCES.md", "heartbeat": now - 120},
              {"item": "old `robot_arm` thing", "heartbeat": now - 4 * 3600}]
    assert explain.work_status("x", [{"kind": "fix", "label": "Fix x", "started": now}], [], now)["state"] == "fixing"
    assert explain.work_status("x", [{"kind": "check", "label": "Check", "started": now}], [], now)["state"] == "checking"
    w = explain.work_status("fpv_wing", [], claims, now)
    assert w["state"] == "claimed" and w["task"] == "E7 `fpv_wing`" and "2 min ago" in w["text"]
    assert explain.work_status("robot_arm", [], claims, now)["state"] == "idle"          # stale claim: nobody on it
    assert explain.work_status("fpv", [], claims, now)["state"] == "idle"                # whole names only
    for provider, owner in (("Codex", "Codex"), ("Claude Code", "Claude Code"), (None, "Another session"), ([], "Another session")):
        w = explain.work_status("fpv_wing", [], [{**claims[0], "provider": provider}], now)
        assert w["text"].startswith(f"{owner} has claimed") and "working" not in w["text"]


def test_studio_detail_and_page_use_it(tmp_path, monkeypatch):
    rep = {"ok": False, "problems": ["pod: exported mesh is not watertight"], "requirements": []}
    out = studio.explained("p", rep, {"parts": {"pod": {}}})
    assert out["cards"][0]["title"] == "Its print file has a hole in the surface" and out["work"]["state"] in ("idle", "claimed")
    html = (studio.Path(studio.__file__).parent / "assets" / "studio.html").read_text(encoding="utf-8")
    assert "issueCards(S.detail.issues" in html and "workBanner(S.detail.issues)" in html and "nobody on it" in html
