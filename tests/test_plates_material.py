"""Plates hold one material each (PLA / PETG / TPU need different temperatures), and part modifiers reach
PRINT_SETTINGS.md."""
from types import SimpleNamespace as S

from build123d import Box

from kerf import export


def _proj():
    mk = lambda mat, **kw: S(role="printed", shape=Box(20, 20, 10), spec={"material": mat, **kw})
    items = {"a": mk("PLA"), "b": mk("TPU"), "c": mk("PLA", modifiers=[{"where": "round the insert", "size": "10 mm",
                                                                         "infill": 1.0, "why": "insert grip"}]),
             "d": mk("PETG")}
    return S(items=items, printed=items)


def test_plates_are_single_material(tmp_path):
    out = export.plates(_proj(), tmp_path)
    mats = [p["material"] for p in out]
    assert sorted(mats) == ["PETG", "PLA", "TPU"]
    pla = next(p for p in out if p["material"] == "PLA")
    assert sorted(x.split()[0] for x in pla["parts"]) == ["a", "c"]


def test_modifiers_reach_print_settings():
    md = export.print_settings_md(_proj())
    assert "## Modifiers" in md and "| c | round the insert | 10 mm | 100 % |" in md


def test_heavy_part_prints_alone(tmp_path):
    """A part of SOLO_G or more gets its own plate: a tall neighbour coming loose must not ruin a many-hour print."""
    big = S(role="printed", shape=Box(80, 80, 40), spec={"material": "PLA", "infill": 1.0})
    small = lambda: S(role="printed", shape=Box(10, 10, 60), spec={"material": "PLA"})
    items = {"pod": big, "fin_l": small(), "fin_r": small()}
    proj = S(items=items, printed=items)
    from kerf import checks
    assert checks.item_mass_g(big) >= export.SOLO_G > checks.item_mass_g(items["fin_l"])
    out = [p for p in export.plates(proj, tmp_path) if p["material"] == "PLA"]
    assert len(out) == 2
    assert [x.split()[0] for x in out[0]["parts"]] == ["pod"]
    assert sorted(x.split()[0] for x in out[1]["parts"]) == ["fin_l", "fin_r"]
