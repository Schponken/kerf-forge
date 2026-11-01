"""Auto-fixes the engine applies itself: teardrop="auto" holes (iface._auto_td)."""
from build123d import Location

from kerf import iface
from kerf.ctx import Ctx


def _ctx(rot):
    return Ctx("p", {}, {"spec": {"print_rot": rot}})


def test_auto_teardrop_follows_the_print_orientation():
    ctx = _ctx([90, 0, 0])                                  # printed standing: part -Y on the bed
    iface.bolt_pattern(ctx, "g", "M3", [(0, 0)], Location((0, 0, 10)), "clearance", 5, teardrop="auto")
    assert ctx.sites[-1].teardrop is True                   # part-Z holes lie along the bed -> teardrop
    iface.bolt_pattern(ctx, "h", "M3", [(0, 0)], Location((0, 10, 0), (-90, 0, 0)), "clearance", 5, teardrop="auto")
    assert ctx.sites[-1].teardrop is False                  # part-Y holes print vertical -> round
    flat = _ctx([0, 0, 0])
    iface.bolt_pattern(flat, "g", "M3", [(0, 0)], Location((0, 0, 10)), "clearance", 5, teardrop="auto")
    assert flat.sites[-1].teardrop is False
    # a counterbore cannot be teardropped: "auto" leaves it round instead of failing the part
    iface.bolt_pattern(ctx, "c", "M3", [(0, 0)], Location((0, 0, 10)), "counterbore", 8, counterbore_depth=3, teardrop="auto")
    assert ctx.sites[-1].teardrop is False


def test_auto_teardrop_on_pin_holes():
    ctx = _ctx([90, 0, 0])
    iface.pin_hole(ctx, "motion.pin_3mm", Location((0, 0, 0)), "hinge", 6, teardrop="auto")
    assert ctx.pins[-1].teardrop is True


def test_kerf_fixes_edits_only_the_named_group(tmp_path):
    import json
    from kerf import autofix
    d = tmp_path / "p"
    (d / "parts").mkdir(parents=True)
    (d / "out").mkdir()
    (d / "project.yaml").write_text("name: t\nparts:\n  plate: {file: parts/plate.py}\n")
    (d / "parts" / "plate.py").write_text(
        "from kerf import iface\n# 30° wall, 2 × M3\n"
        "def build(ctx):\n"
        "    a = iface.bolt_pattern(ctx, \"lid\", \"M3\", [(0, 0)], LOC, \"clearance\", 5)\n"
        "    b = iface.bolt_pattern(ctx, \"feet\", \"M3\", [(0, 0)],\n                           LOC, \"tap\", 8)\n"
        "    c = iface.bolt_pattern(ctx, \"other\", \"M3\", [(0, 0)], LOC, \"tap\", 8)\n")
    (d / "out" / "report.json").write_text(json.dumps({"problems": [], "warnings": [
        "plate: 2 clearance hole(s) of group 'lid' print horizontal and are cut round (the top sags, a ...",
        "plate: 1 M3 tap hole(s) of group 'feet' sit closer than 1.5 x d (4.5 mm) to a free edge (worst 60 % ...",
        "plate: 1 M3 clearance hole(s) of group 'other' sit closer than 1.5 x d (4.5 mm) to a free edge ..."]}))
    dry = autofix.fixes(d)
    assert [f["kind"] for f in dry] == ["teardrop", "heatset", "manual"] and not any(f["applied"] for f in dry)
    assert "teardrop" not in (d / "parts" / "plate.py").read_text()                 # a dry run writes nothing
    safe = autofix.fixes(d, apply=True)                                         # teardrops only
    assert [f["applied"] for f in safe] == [True, False, False] and '"tap", 8)' in (d / "parts" / "plate.py").read_text()
    done = autofix.fixes(d, apply=True, heatset=True)
    src = (d / "parts" / "plate.py").read_text()
    assert 'LOC, "clearance", 5, teardrop="auto")' in src
    assert 'LOC, "heatset", 8)' in src and '"other", "M3", [(0, 0)], LOC, "tap", 8)' in src   # only group feet changed
    assert [f["applied"] for f in done] == [False, True, False]                 # the teardrop was already there
    compile(src, "plate.py", "exec")
