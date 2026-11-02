"""The person using it (kerf/req_human.py): field-repair key access on the finished device, handles from the use
story, carry / repair notes."""
from types import SimpleNamespace as NS

from kerf import assembly as A, project as P, requirements as R, usestory as U
from kerf.req_human import notes
from test_engine import BOLT_BLOCK, BOLT_PLATE, _write_project

LID = """
from build123d import *
def build(ctx):
    ctx.rigid("bottom", Location((0, 0, 0)))
    return ctx.finish(Pos(0, 0, {z}) * Box(40, 40, 3, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""
Y = """
name: Repair test
params: {}
parts:
  plate: {file: parts/plate.py}
  block: {file: parts/block.py}
  lid: {file: parts/lid.py}
assembly:
  root: block
  joints:
    - {parent: block.top, child: plate.bottom}
    - {parent: block.top, child: lid.bottom}
requirements:
  - {id: fix, check: repair_access, parts: [plate]}
"""


def _rows(tmp_path, z):
    d = _write_project(tmp_path / f"r{z}", Y, {"block": BOLT_BLOCK, "plate": BOLT_PLATE, "lid": LID.format(z=z)})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    A.solve(asm)
    return R.run_all(proj, asm)[0]


def test_field_repair_needs_the_screws_reachable_on_the_finished_device(tmp_path):
    clear = _rows(tmp_path, 60)                 # a lid 56 mm above the screw heads: the key goes in under it
    covered = _rows(tmp_path, 8)                # a lid 4 mm over the screw heads: no key reaches them with it fitted
    assert covered["value"] == 2 and not covered["ok"] and "lid" in covered["detail"]
    assert clear["ok"] and clear["keys_mm"] == [2.5]


def test_story_handles_get_a_finger_opening_gloved_only_with_a_gloves_hazard():
    st = {"who": "a", "where": ["x"], "how_often": "y", "handles": [{"item": "switch"}, {"item": "battery"}],
          "field_repair": ["arm"], "goes_wrong": []}
    reqs = U.requirements(NS(data={"use_story": st}))
    assert [(r["check"], r.get("gloved")) for r in reqs] == [("access_opening", False), ("access_opening", False),
                                                            ("repair_access", None)]
    st["goes_wrong"] = [{"hazard": "gloves", "handles": [{"item": "battery"}]}]
    reqs = U.requirements(NS(data={"use_story": st}))
    assert [(r["item"], r["gloved"]) for r in reqs if r["check"] == "access_opening"] == [("battery", True), ("switch", True)]


def test_carry_and_repair_notes():
    items = {"p": NS(spec={"catalog": "drone.props.5_1in"})}
    proj = NS(items=items, data={"use_story": {"carry_by": "the top plate", "field_repair": ["arm_1"]}})
    rep = {"mass": {"device_g": 612.4}, "requirements": [{"check": "repair_access", "keys_mm": [2.0, 2.5]},
                                                        {"check": "weak_link", "ok": True}]}
    L = "\n".join(notes(proj, rep))
    assert "612 g" in L and "carry it by the top plate" in L and "props off" in L
    assert "arm_1 come off the finished device with a 2 / 2.5 mm hex key" in L and "weak link" in L
