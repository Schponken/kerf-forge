"""Self-correcting errors: deliberately broken parts must fail with the part, the feature (file line + operation) and a
concrete fix hint; applying the hint must make the part build (the part-designer retry loop, without the LLM)."""
import re
import textwrap
from pathlib import Path

import pytest

from kerf import pipeline, project as P

YAML = """
name: Broken parts
params: {w: 20, t: 2.4}
parts:
  plate: {file: parts/plate.py, material: PETG}
assembly:
  root: plate
"""

HEAD = "from build123d import *\nfrom kerf import iface, features as F\n\n\ndef build(ctx):\n    p = ctx.p\n"


def _proj(tmp: Path, body: str, yaml_text: str = YAML) -> Path:
    (tmp / "parts").mkdir(parents=True, exist_ok=True)
    (tmp / "project.yaml").write_text(textwrap.dedent(yaml_text))
    (tmp / "parts" / "plate.py").write_text(HEAD + textwrap.indent(textwrap.dedent(body), "    "))
    return tmp


def _fail(d: Path):
    proj = P.build(P.load(str(d)))
    it = proj.items["plate"]
    assert it.error and it.diag is not None, "the broken part must fail to build"
    return it.diag, it.error


def _line_of(d: Path, needle: str) -> int:
    lines = (d / "parts" / "plate.py").read_text().splitlines()
    return next(i + 1 for i, l in enumerate(lines) if needle in l)


def test_fillet_too_big_names_line_and_gives_working_radius(tmp_path):
    d = _proj(tmp_path, """
        body = Box(p.w, p.w, p.t)
        body = fillet(body.edges().group_by(Axis.Z)[-1], 3)
        return ctx.finish(body)
    """)
    diag, msg = _fail(d)
    assert diag.part == "plate" and diag.file == "plate.py"
    assert diag.line == _line_of(d, "fillet(") and "fillet(" in diag.code
    assert diag.feature == "fillet"
    assert "plate.py line" in msg and "fix:" in msg
    use = float(re.search(r"use <= ([\d.]+)", diag.hint).group(1))
    assert 0 < use < 2.4          # the top edges of a 2.4 mm plate cannot take more than the plate thickness
    # the retry loop: put the hinted radius in, rebuild, it passes
    src = (d / "parts" / "plate.py").read_text().replace("[-1], 3)", f"[-1], {use})")
    (d / "parts" / "plate.py").write_text(src)
    proj = P.build(P.load(str(d)))
    assert proj.items["plate"].error is None


def test_chamfer_too_big_gives_working_size(tmp_path):
    d = _proj(tmp_path, """
        body = Box(p.w, p.w, p.t)
        body = chamfer(body.edges().group_by(Axis.Z)[-1], 4)
        return ctx.finish(body)
    """)
    diag, _ = _fail(d)
    assert diag.feature == "chamfer" and diag.line == _line_of(d, "chamfer(")
    use = float(re.search(r"use <= ([\d.]+)", diag.hint).group(1))
    src = (d / "parts" / "plate.py").read_text().replace("[-1], 4)", f"[-1], {use})")
    (d / "parts" / "plate.py").write_text(src)
    assert P.build(P.load(str(d))).items["plate"].error is None


def test_unknown_param_suggests_nearest(tmp_path):
    d = _proj(tmp_path, """
        body = Box(p.width, p.w, p.t)
        return ctx.finish(body)
    """)
    diag, _ = _fail(d)
    assert diag.feature == "ctx.p" and diag.line == _line_of(d, "p.width")
    assert "'width'" in diag.hint and "Did you mean w" in diag.hint and "project.yaml" in diag.hint


def test_name_typo_suggests_build123d_name(tmp_path):
    d = _proj(tmp_path, """
        body = Bx(p.w, p.w, p.t)
        return ctx.finish(body)
    """)
    diag, _ = _fail(d)
    assert "Box" in diag.hint and diag.line == _line_of(d, "Bx(")


def test_catalog_typo_suggests_key(tmp_path):
    d = _proj(tmp_path, """
        s = ctx.cat.get("servos.MG90")
        return ctx.finish(Box(p.w, p.w, p.t))
    """)
    diag, _ = _fail(d)
    assert diag.line == _line_of(d, "ctx.cat.get")
    assert "MG90S" in diag.hint


def test_feature_minimum_names_limit(tmp_path):
    d = _proj(tmp_path, """
        body = Box(p.w, p.w, p.t)
        body -= F.channel([(-15, 0, 0), (15, 0, 0)], d=0.5)
        return ctx.finish(body)
    """)
    diag, _ = _fail(d)
    assert diag.feature == "features.channel" and diag.line == _line_of(d, "F.channel")
    assert ">= 0.8" in diag.hint


def test_heatset_too_thin_gives_needed_thickness(tmp_path):
    d = _proj(tmp_path, """
        body = Box(p.w, p.w, p.t, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body -= iface.bolt_pattern(ctx, "g", "M3", [(0, 0)], Location((0, 0, p.t)), kind="heatset", depth=p.t)
        return ctx.finish(body)
    """)
    diag, _ = _fail(d)
    assert diag.feature.startswith("iface.") and diag.line == _line_of(d, "iface.bolt_pattern")
    assert re.search(r">= [\d.]+ mm of material", diag.hint)


def test_missing_finish_and_syntax_error(tmp_path):
    d = _proj(tmp_path, """
        return Box(p.w, p.w, p.t)
    """)
    diag, _ = _fail(d)
    assert "ctx.finish" in diag.hint
    d2 = _proj(tmp_path / "syn", """
        body = Box(p.w, p.w, p.t
        return ctx.finish(body)
    """)
    diag, _ = _fail(d2)
    assert diag.feature == "syntax" and diag.line > 0


def test_report_and_cli_carry_the_fix(tmp_path):
    d = _proj(tmp_path, """
        body = Box(p.w, p.w, p.t)
        body = fillet(body.edges().group_by(Axis.Z)[-1], 3)
        return ctx.finish(body)
    """)
    rep = pipeline.run(str(d), sweeps=False)
    assert not rep["ok"]
    assert rep["diagnoses"]["plate"]["hint"].startswith("the largest fillet")
    assert any("fix:" in p for p in rep["problems"])


def test_after_edit_hook_feeds_the_fix_back(tmp_path):
    """The part-designer loop: editing a broken part makes the PostToolUse hook exit 2 with the fix hint up front."""
    import json, os, subprocess, sys
    root = Path(__file__).resolve().parent.parent
    (tmp_path / ".venv").symlink_to(root / ".venv")
    d = _proj(tmp_path / "projects" / "broken", """
        body = Box(p.w, p.w, p.t)
        body = fillet(body.edges().group_by(Axis.Z)[-1], 3)
        return ctx.finish(body)
    """)
    part = d / "parts" / "plate.py"
    r = subprocess.run([sys.executable, str(root / ".claude/hooks/after_edit.py")], cwd=tmp_path,
                       input=json.dumps({"tool_input": {"file_path": str(part)}}), capture_output=True, text=True,
                       env={**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}, timeout=300)
    assert r.returncode == 2
    first = r.stderr.split("FIX THESE FIRST")[1][:600]
    assert "plate.py line" in first and "fix: the largest fillet" in first
