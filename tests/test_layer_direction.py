"""Layer-direction check: a part's declared main load axis vs. its print orientation."""
from types import SimpleNamespace

import pytest

from kerf import catalog, checks


def _item(**spec):
    return SimpleNamespace(id="arm", spec={"material": "PETG", **spec})


def test_no_load_axis_no_warning():
    assert checks.layer_direction(_item()) == ([], [])


def test_flat_arm_along_layers_ok():
    # arm length along X, printed flat: the load runs in the bed plane
    assert checks.layer_direction(_item(load_axis="x")) == ([], [])
    assert checks.layer_direction(_item(load_axis=[1, 1, 0])) == ([], [])


def test_standing_arm_warns_with_blended_strength():
    # arm length along X, printed standing up (rotated 90 deg about Y): X becomes build Z -> fully across layers
    p, w = checks.layer_direction(_item(load_axis="x", print_rot=[0, 90, 0]))
    assert p == [] and len(w) == 1 and "90 deg out of the layer plane" in w[0]
    m = catalog.get("materials.PETG")
    z = catalog.num(m, "tensile_strength_z_mpa", "tensile_strength_z", default=-1)
    if z > 0:
        assert f"~{z:.0f} of" in w[0]


def test_threshold_is_30_degrees():
    # rotate the part about Y so the X load axis tilts out of the bed plane by 25 deg (ok) and 35 deg (warn)
    assert checks.layer_direction(_item(load_axis="x", print_rot=[0, 25, 0]))[1] == []
    assert len(checks.layer_direction(_item(load_axis="x", print_rot=[0, 35, 0]))[1]) == 1


def test_list_of_axes_and_bad_axis():
    p, w = checks.layer_direction(_item(load_axis=["x", "z"]))  # flat: z is across layers
    assert len(w) == 1 and "load axis z" in w[0]
    p, w = checks.layer_direction(_item(load_axis="q"))
    assert len(p) == 1


def test_reported_by_part_checks(tmp_path):
    from build123d import Align, Box
    it = SimpleNamespace(id="arm", spec={"material": "PETG", "load_axis": "z"}, build_ms=0,
                         shape=Box(10, 10, 40, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    r = checks.part_checks(it, "Bambu Lab A2L")
    assert any("out of the layer plane" in w for w in r["warnings"])
