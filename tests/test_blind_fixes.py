"""Engine fixes from the E6 blind pan_tilt run (evals/pan_tilt/BLIND_RUN.md)."""
import json
from types import SimpleNamespace

import numpy as np
import pytest
from build123d import Align, Box, Location, Pos

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


def test_tap_and_heatset_holes_take_a_teardrop():
    from kerf import iface
    for kind in ("tap", "heatset"):
        plain = iface.hole("M3", kind, 10.0)[0]
        td = iface.hole("M3", kind, 10.0, teardrop=90)[0]
        assert td.volume > plain.volume + 0.05, kind      # the roof is really there
        lo, hi = geom.bbox(td)
        assert hi[1] > geom.bbox(plain)[1][1] + 0.3       # pointed toward +Y (up on the printer)
    with pytest.raises(ValueError, match="teardrop is not available"):
        iface.hole("M3", "counterbore", 10.0, teardrop=90)


def test_horn_mount_teardrop():
    from kerf import iface

    class Ctx:
        def __init__(self):
            self.sites = []

        def site(self, s):
            self.sites.append(s)
    horn = next(f"servo_horns.{k}" for k in catalog.load()["servo_horns"])
    a = iface.horn_mount(Ctx(), horn, Location(), "g", 4.0)
    b = iface.horn_mount(Ctx(), horn, Location(), "g", 4.0, teardrop=90)
    assert b.volume > a.volume


def test_render_false_items_left_out_of_views_only():
    a, b = Box(2, 2, 2), Box(2, 2, 2)
    b.location = Location((0, 0, -150))
    proj = SimpleNamespace(items={"head": SimpleNamespace(shape=a, role="printed", spec={}),
                                  "psu": SimpleNamespace(shape=b, role="purchased", spec={"render": False})})
    assert [s.label for s in export._placed_copies(proj, for_render=True)] == ["head"]
    assert [s.label for s in export._placed_copies(proj)] == ["head", "psu"]


def test_camera_board_proxy_keeps_mounting_holes_open():
    from build123d import Cylinder
    from kerf import proxies
    from kerf.ctx import Ctx
    e = catalog.get("boards.rpi_camera_module_3")
    s = proxies.build(Ctx("cam", {}), {"catalog": "boards.rpi_camera_module_3", "proxy": "board"})
    t = e["thickness"]
    lo, hi = geom.bbox(s)
    assert hi[2] >= t + e["component_height"] - 1e-6                  # the lens housing is there, full height
    for (x, y) in e["holes"]:                                         # a hex key column above every hole is free
        col = Pos(x, y, t + 0.01) * Cylinder(1.0, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
        assert (s & col).volume < 1e-6, (x, y)


def test_view_cone_frustum_and_camera_lens_joint():
    import math
    from kerf import proxies
    from kerf.ctx import Ctx
    s = proxies.build(Ctx("v", {}), {"proxy": "view_cone", "length": 30, "aperture": [6, 6], "hfov_deg": 66, "vfov_deg": 41})
    lo, hi = geom.bbox(s)
    assert abs((hi[0] - lo[0]) - (6 + 60 * math.tan(math.radians(33)))) < 0.01
    assert abs((hi[1] - lo[1]) - (6 + 60 * math.tan(math.radians(20.5)))) < 0.01
    assert abs(hi[2] - 30) < 1e-6
    # frustum, not a box: volume well under the bounding box
    assert s.volume < 0.6 * (hi[0] - lo[0]) * (hi[1] - lo[1]) * 30
    cam = proxies.build(Ctx("cam", {}), {"catalog": "boards.rpi_camera_module_3", "proxy": "board"})
    assert "lens" in cam.joints
    with pytest.raises(ValueError):
        proxies.build(Ctx("v", {}), {"proxy": "view_cone", "length": 30})


def test_servo_flex_lead_counts_for_interference_not_tool_reach():
    """SG90 lead envelope (cable_boss_flex): part of the proxy solid, but access._rigid_part drops it."""
    from kerf import access, iface, proxies
    from kerf.ctx import Ctx
    d = iface.servo_dims("servos.SG90")
    e = catalog.get("servos.SG90")
    s = proxies.build(Ctx("s", {}), {"catalog": "servos.SG90", "proxy": "servo"})
    assert len(s.kerf_flex) == 1
    s.location = Location((5, 7, 9))                       # placed in an assembly
    x = d["L"] / 2 + catalog.num(e, "cable_boss_protrusion") / 2
    z = -d["tab_z"] + catalog.num(e, "cable_boss_z0") + catalog.num(e, "cable_boss_h") / 2
    probe = Pos(5 + x, 7, 9 + z) * Box(1, 1, 1)
    assert (s & probe).volume > 0.5                         # interference sees the lead
    assert (access._rigid_part(s) & probe).volume < 1e-6    # a hex key pushes it aside
    mg = proxies.build(Ctx("m", {}), {"catalog": "servos.MG996R", "proxy": "servo"})
    assert mg.kerf_flex == [] and access._rigid_part(mg) is mg   # a moulded boss stays rigid
