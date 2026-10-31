"""Assembly access: hex-key reach and insertion paths, with hand-placed obstructions."""
import pytest

from kerf import access, assembly as A, catalog, project as P
from test_engine import BOLT_BLOCK, BOLT_PLATE, _write_project

ROOF = """
from build123d import *
def build(ctx):
    ctx.rigid("origin", Location((0, 0, 0)))
    return ctx.finish(Pos(RX, 0, RZ) * Box(RW, 40, 2, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""
KEY_YAML = """
name: Key test
params: {}
parts:
  plate: {file: parts/plate.py}
  block: {file: parts/block.py}
  roof: {file: parts/roof.py}
assembly:
  root: block
  joints:
    - {parent: block.top, child: plate.bottom}
    - {parent: block.origin, child: roof.origin}
"""


def _keys(tmp_path, rx, rz, rw):
    block = BOLT_BLOCK.replace('    ctx.rigid("top"', '    ctx.rigid("origin", Location((0, 0, 0)))\n    ctx.rigid("top"')
    roof = ROOF.replace("RX", str(rx)).replace("RZ", str(rz)).replace("RW", str(rw))
    d = _write_project(tmp_path / f"k{rx}_{rz}_{rw}", KEY_YAML, {"block": block, "plate": BOLT_PLATE, "roof": roof})
    proj = P.build(P.load(str(d)))
    assert all(it.error is None for it in proj.items.values()), [it.error for it in proj.items.values()]
    asm = A.plan(proj)
    A.solve(asm)
    return access.hex_key_reach(asm)


def test_key_spec_from_catalog():
    k = access.key_spec("M3", "clearance")
    assert k["s"] == 2.5 and k["reach"] == pytest.approx(52.4) and k["r"] == pytest.approx(2.5 / 3 ** 0.5)
    assert access.key_spec("M3", "countersink")["s"] == 2.0                  # ISO 10642
    assert catalog.get("tools.hex_key")["ball_end_max_deg"] == 25


def test_open_screws_are_reachable(tmp_path):
    # M3 heads (3 mm tall) on the plate top (z 24): head tops at z 27; roof just beyond the 52.4 mm key reach
    res, problems, warnings = _keys(tmp_path, 0, 27 + 52.4 + 1, 100)
    assert problems == [] and warnings == [] and all(r["straight"] for r in res) and len(res) == 2
    assert res[0]["at"][2] == pytest.approx(27.0)            # clearance hole: head sits on the surface
    res, problems, warnings = _keys(tmp_path, 0, 27 + 52.4 - 1, 100)    # same roof 2 mm lower: inside the reach
    assert not any(r["straight"] for r in res)
    # a 25 deg ball-end key ends lower: (78.4 - 28.49) / cos 25 = 55.1 mm > 52.4 reach, so it still fits
    assert problems == [] and len(warnings) == 2


def test_narrow_obstruction_needs_ball_end(tmp_path):
    # 6 mm strip right over the x = 10 screw, 23 mm above its head: a 25 deg ball-end key passes beside it
    res, problems, warnings = _keys(tmp_path, 10, 50, 6)
    assert problems == []
    assert len(warnings) == 1 and "ball-end" in warnings[0] and "roof" in warnings[0]
    by_x = {round(r["at"][0]): r for r in res}
    assert by_x[-10]["straight"] and not by_x[10]["straight"] and by_x[10]["ball_end"]


def test_covered_screw_is_a_problem(tmp_path):
    _, problems, _ = _keys(tmp_path, 0, 30, 200)
    assert len(problems) == 2 and all("no 2.5 mm hex key" in p for p in problems)


BASE = """
from build123d import *
def build(ctx):
    s = Box(40, 40, 20, align=(Align.CENTER, Align.CENTER, Align.MIN)) - Pos(0, 0, 10) * Box(12, 12, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctx.rigid("seat", Location((0, 0, 10)))
    ctx.rigid("origin", Location((0, 0, 0)))
    return ctx.finish(s)
"""
PEG = """
from build123d import *
def build(ctx):
    ctx.rigid("foot", Location((0, 0, 0)))
    return ctx.finish(Box(10, 10, 10, align=(Align.CENTER, Align.CENTER, Align.MIN)))
"""
LIP = """
from build123d import *
def build(ctx):
    ctx.rigid("origin", Location((0, 0, 0)))
    return ctx.finish(Pos(0, 0, 25) * (Box(40, 40, 2, align=(Align.CENTER, Align.CENTER, Align.MIN)) - Box(8, 8, 2, align=(Align.CENTER, Align.CENTER, Align.MIN))))
"""


def _insert(tmp_path, direction, lip):
    y = f"""
name: Insert test
params: {{}}
parts:
  base: {{file: parts/base.py}}
  peg: {{file: parts/peg.py, insert: {{direction: {direction}, distance: 25}}}}
{"  lip: {file: parts/lip.py}" if lip else ""}
assembly:
  root: base
  joints:
    - {{parent: base.seat, child: peg.foot}}
{"    - {parent: base.origin, child: lip.origin}" if lip else ""}
"""
    d = _write_project(tmp_path / f"ins{lip}{direction}".replace(" ", ""), y, {"base": BASE, "peg": PEG, "lip": LIP})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    A.solve(asm)
    out = access.insertion_paths(asm)
    assert proj.items["peg"].shape.location.position.Z == pytest.approx(10)   # put back where it was
    return out


def test_drops_into_open_pocket(tmp_path):
    res, problems = _insert(tmp_path, "[0, 0, -1]", lip=False)
    assert problems == [] and res[0]["clear"] and res[0]["distance_mm"] == 25


def test_lip_over_pocket_blocks(tmp_path):
    res, problems = _insert(tmp_path, "[0, 0, -1]", lip=True)
    # 10 mm peg (z 10+b .. 20+b) meets the 8 mm opening at z 25..27 for 5 < b < 17 (1 mm steps: 6..16)
    backs = sorted({c["mm_from_seat"] for c in res[0]["collisions"]})
    assert len(problems) == 1 and "lip" in problems[0] and "16.0 mm before" in problems[0]
    assert min(backs) == 6.0


def test_sideways_through_wall_blocks(tmp_path):
    res, problems = _insert(tmp_path, "[1, 0, 0]", lip=False)
    assert len(problems) == 1 and "base" in problems[0]


def test_assembly_order_lets_later_parts_cover_screws(tmp_path):
    """A lid installed after the screws are driven may cover them (assembly.order); without the order it blocks."""
    res, problems, _ = _keys(tmp_path, 0, 30, 100)           # roof 3 mm above the heads, over both screws
    assert len(problems) == 2
    block = BOLT_BLOCK.replace('    ctx.rigid("top"', '    ctx.rigid("origin", Location((0, 0, 0)))\n    ctx.rigid("top"')
    roof = ROOF.replace("RX", "0").replace("RZ", "30").replace("RW", "100")
    yaml = KEY_YAML + "  order: [block, plate, roof]\n"
    d = _write_project(tmp_path / "ordered", yaml, {"block": block, "plate": BOLT_PLATE, "roof": roof})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    A.solve(asm)
    res, problems, warnings = access.hex_key_reach(asm)
    assert problems == [] and warnings == [] and all(r["straight"] for r in res)
    # the roof installed BEFORE the plate still blocks
    d = _write_project(tmp_path / "ordered2", KEY_YAML + "  order: [block, roof, plate]\n", {"block": block, "plate": BOLT_PLATE, "roof": roof})
    proj = P.build(P.load(str(d)))
    asm = A.plan(proj)
    A.solve(asm)
    assert len(access.hex_key_reach(asm)[1]) == 2


def test_key_access_order(tmp_path):
    """A part fitted after the screws are driven (assembly.key_access) does not block them; 'why' is required."""
    block = BOLT_BLOCK.replace('    ctx.rigid("top"', '    ctx.rigid("origin", Location((0, 0, 0)))\n    ctx.rigid("top"')
    roof = ROOF.replace("RX", "0").replace("RZ", "30").replace("RW", "200")
    for why, expect in (("roof goes on after the plate is screwed down", 0), ("", None)):
        y = KEY_YAML + f"  key_access:\n    - {{group: g, before: [roof], why: '{why}'}}\n"
        d = _write_project(tmp_path / f"order{bool(why)}", y, {"block": block, "plate": BOLT_PLATE, "roof": roof})
        proj = P.build(P.load(str(d)))
        asm = A.plan(proj)
        A.solve(asm)
        if expect is None:
            with pytest.raises(ValueError, match="needs a 'why'"):
                access.hex_key_reach(asm)
        else:
            res, problems, warnings = access.hex_key_reach(asm)
            assert problems == [] and warnings == [] and all(r["straight"] for r in res)
