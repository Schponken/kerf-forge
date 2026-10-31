"""Engine fixes from the E6 blind pan_tilt run (evals/pan_tilt/BLIND_RUN.md)."""
import json
from types import SimpleNamespace

import numpy as np
import pytest
from build123d import Box, Location

from kerf import catalog, electrical, export, geom
from kerf.pipeline import req_line


def test_catalog_refuses_duplicate_keys(tmp_path, monkeypatch):
    f = tmp_path / "hw.json"
    f.write_text('{"electronics": {"connectors": {"a": 1}, "connectors": {"b": 2}}}')
    monkeypatch.setattr(catalog, "CATALOG", f)
    catalog.load.cache_clear()
    try:
        with pytest.raises(catalog.CatalogError, match="duplicate key 'connectors'"):
            catalog.load()
    finally:
        catalog.load.cache_clear()


def test_real_catalog_has_no_duplicate_keys():
    catalog.load.cache_clear()
    assert catalog.load()


def test_exact_45_degree_face_is_not_overhang():
    # a 45 deg roof: normal (0, -1, -1)/sqrt2 -> nz = -sin45 exactly; plus float noise
    e = 1e-7
    v = np.array([[0, 0, 0], [10, 0, 0], [0, 10, -10 - e], [0, 0, -50]], float)
    f = np.array([[0, 2, 1]])
    oh, frac, _ = geom.overhang(v, f, bed_z=-100)
    assert oh == 0.0
    # 50 deg past vertical is still flagged
    v2 = np.array([[0, 0, 0], [10, 0, 0], [0, 10, -10 * np.tan(np.radians(40))]], float)
    oh2, _, _ = geom.overhang(v2, np.array([[0, 2, 1]]), bed_z=-100)
    assert oh2 > 0


def test_req_line_flags_failure_hidden_by_rounding():
    assert "less than the shown rounding" in req_line({"ok": False, "value": 0.8, "limit": 0.8})
    assert "rounding" not in req_line({"ok": False, "value": 0.7, "limit": 0.8})
    assert req_line({"ok": True, "value": 0.9, "limit": 0.8}).startswith("ok")


def test_route_points_evaluate_param_expressions():
    sh = Box(1, 1, 1)
    sh.location = Location((5, 0, 0))
    proj = SimpleNamespace(params={"wall_out": 10.0}, items={"base": SimpleNamespace(shape=sh)})
    p = electrical._point(proj, {"item": "base", "at": ["wall_out + 18", 0, "2 * wall_out"]})
    assert np.allclose(p, [33, 0, 20])
    assert np.allclose(electrical._point(proj, ["wall_out", 1, 2]), [10, 1, 2])


def test_bom_survives_pin_without_valid_length(tmp_path):
    proj = SimpleNamespace(printed={}, items={}, data={})
    pins = [{"pin": "M3", "d_mm": 3.0, "length_mm": None, "screw_pivot": True, "fixed_fit": "tap", "group": "g",
             "fixed_in": ["a"]}]
    try:
        rows = export.bom(proj, [], {}, tmp_path, pins=pins)
    except TypeError as e:  # pragma: no cover
        pytest.fail(f"bom crashed on a pin with no length: {e}")
    text = json.dumps(rows, default=str) if rows is not None else (tmp_path / "bom.md").read_text()
    assert "no stocked length" in text or any("no stocked length" in p.read_text() for p in tmp_path.glob("bom*"))


def test_tripod_socket_cutter():
    from build123d import Box, Align, Location
    from kerf import iface
    blk = Box(30, 30, 12, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cut = iface.tripod_socket(Location((0, 0, 0)), floor_t=1.5)
    out = blk - cut
    lo, hi = geom.bbox(cut)
    nut = catalog.get("tripod_nut_1_4_20")
    assert abs((hi[2]) - (1.5 + nut["thickness"] + 0.3)) < 1e-6        # pocket top
    removed = blk.volume - out.volume
    hex_v = 3 * 3 ** 0.5 / 2 * ((nut["across_flats"] + 0.2) / 3 ** 0.5) ** 2 * (nut["thickness"] + 0.3)
    assert hex_v < removed < hex_v + 3.14159 * 4.3 ** 2 * 1.6               # + the clearance hole and lead-in
