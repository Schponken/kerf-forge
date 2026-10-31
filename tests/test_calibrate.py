"""Print-truth loop: synthetic fit feedback -> stored per printer+material offsets -> iface cuts the corrected sizes."""
import json
import math

import pytest
from build123d import Box, Location

from kerf import calibrate as C, catalog, geom, iface
from kerf.ctx import Ctx


@pytest.fixture(autouse=True)
def tmp_profiles(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "PRINTERS", tmp_path / "printers")
    return tmp_path


def _hole_d(cutter):
    bb = cutter.bounding_box()
    return round(bb.size.X, 3)


def test_no_profile_means_catalog_sizes():
    with C.active("Bambu Lab A2L", "PETG"):
        assert iface.screw_spec("M3")["clearance"] == catalog.num(catalog.get("fdm_holes.M3"), "clearance_hole")
        assert C.offset("bearing", "608") == 0.0


def test_feedback_steps_and_history():
    ch = C.feedback("PETG", {"hole_M3": "tight", "tap_M3": "loose", "insert_M2": "+0.15", "bearing_608": "ok"},
                    date="2026-10-31")
    assert ch == {"hole_M3": (0.0, 0.1), "tap_M3": (0.0, -0.05), "insert_M2": (0.0, 0.15)}
    C.feedback("petg", {"hole_M3": "tight"}, date="2026-11-01")          # same material, any case
    prof = json.loads(C.profile_path("Bambu Lab A2L").read_text())
    m = prof["materials"]["PETG"]
    assert m["offsets"]["hole_M3"] == pytest.approx(0.2)                # two tight reports = two 0.1 steps
    assert [h["date"] for h in m["history"]] == ["2026-10-31", "2026-11-01"]
    assert m["history"][0]["reported"]["tap_M3"] == "loose"


def test_offsets_are_per_material_and_printer():
    C.feedback("PETG", {"hole_M3": "tight"})
    with C.active("Bambu Lab A2L", "PLA"):
        assert C.offset("hole", "M3") == 0.0
    with C.active("Prusa MK4", "PETG"):
        assert C.offset("hole", "M3") == 0.0
    with C.active("Bambu Lab A2L", "PETG"):
        assert C.offset("hole", "M3") == pytest.approx(0.1)


def test_iface_applies_offsets_to_every_fit():
    base_cl = catalog.num(catalog.get("fdm_holes.M3"), "clearance_hole")
    C.feedback("PETG", {"hole_M3": "+0.2", "bearing_608": "tight", "servo_window": "tight", "pin_0.2": "tight",
                        "pin_0.3": "ok", "pin_0.4": "loose"})
    with C.active("Bambu Lab A2L", "PETG"):
        c, *_ = iface.hole("M3", "clearance", 5)
        assert _hole_d(c) == pytest.approx(base_cl + 0.2, abs=1e-3)
        # nearest calibrated size stands in for an uncalibrated one (M4 -> M3)
        assert C.offset("hole", "M4") == pytest.approx(0.2)
        seat = iface.bearing_seat(None, "bearings.608", Location(), fit="press")
        assert _hole_d(seat) == pytest.approx(22 + iface.FIT["press"] + 0.05, abs=1e-3)
        # a 623 was not calibrated: it takes the 608's offset (closest outer diameter that was)
        assert C.offset("bearing", "623") == pytest.approx(0.05)
        ctx = Ctx("t", {}, {"spec": {"material": "PETG"}})
        pin = iface.pin_hole(ctx, "motion.pin_3mm", Location(), "g", 5, fit="free")
        assert _hole_d(pin) == pytest.approx(3.3, abs=1e-3)                 # smallest clearance reported ok
    # outside the profile (another material) the textbook sizes come back
    with C.active("Bambu Lab A2L", "ABS"):
        c, *_ = iface.hole("M3", "clearance", 5)
        assert _hole_d(c) == pytest.approx(base_cl, abs=1e-3)


def test_servo_window_offset_widens_window():
    def window_volume():
        ctx = Ctx("t", {}, {"spec": {"material": "PETG"}})
        cut = iface.servo_mount(ctx, C.COUPON_SERVO, Location(), "g", plate_t=6, kind="tap", lead_in=0)
        return geom.volume(cut)
    with C.active("Bambu Lab A2L", "PETG"):
        v0 = window_volume()
    C.feedback("PETG", {"servo_window": "tight"})
    with C.active("Bambu Lab A2L", "PETG"):
        v1 = window_volume()
    d = catalog.get(C.COUPON_SERVO)
    L, W = d["body_l"] + 0.6, d["body_w"] + 0.6
    # window grows by 0.2 on both sides; plate 6 + 2 x 1 mm overshoot
    assert v1 - v0 == pytest.approx(((L + 0.2) * (W + 0.2) - L * W) * 8, rel=0.02)


def test_pin_feedback_all_tight_or_all_loose():
    C.feedback("PLA", {"pin_0.2": "tight", "pin_0.3": "tight", "pin_0.4": "tight"})
    with C.active("Bambu Lab A2L", "PLA"):
        assert C.pin_allowance("free", 0.35) == pytest.approx(0.5)
    C.feedback("PLA", {"pin_press": "loose"})
    with C.active("Bambu Lab A2L", "PLA"):
        assert C.pin_allowance("press", 0.05) == pytest.approx(0.03)


def test_bad_feedback_refused():
    with pytest.raises(ValueError, match="unknown coupon feature"):
        C.feedback("PETG", {"hole_M7": "tight"})
    with pytest.raises(ValueError, match="tight, ok, loose"):
        C.feedback("PETG", {"hole_M3": "snug"})
    with pytest.raises(ValueError, match="beyond"):
        C.feedback("PETG", {"hole_M3": "+0.9"})
    assert not C.profile_path("Bambu Lab A2L").exists()   # nothing half-saved


def test_coupon_builds_and_carries_offsets(tmp_path):
    body, rows = C.coupon("PETG")
    assert body.is_valid and len(body.solids()) == 1
    assert {k for k, *_ in rows} == set(C.feature_keys())
    v0 = geom.volume(body)
    C.feedback("PETG", {f"hole_{s}": "+0.3" for s in C.SIZES})
    body2, _ = C.coupon("PETG")
    # three clearance holes, each 8 mm deep, grew from d to d + 0.3
    grow = sum(math.pi / 4 * ((catalog.num(catalog.get(f"fdm_holes.{s}"), "clearance_hole") + 0.3) ** 2
                              - catalog.num(catalog.get(f"fdm_holes.{s}"), "clearance_hole") ** 2) * 8 for s in C.SIZES)
    assert v0 - geom.volume(body2) == pytest.approx(grow, rel=0.02)
    out = C.write_coupon("PETG", outdir=tmp_path / "cal")
    assert (out / "coupon.3mf").exists() and (out / "coupon.stl").exists()
    card = (out / "CARD.md").read_text()
    assert "kerf feedback PETG" in card and "`servo_window`" in card and "hole_M3" in card


def test_project_build_uses_its_printer_profile(tmp_path):
    import textwrap
    from kerf import project as P
    d = tmp_path / "p"
    (d / "parts").mkdir(parents=True)
    (d / "project.yaml").write_text(textwrap.dedent("""
        name: fit
        printer: Bambu Lab A2L
        parts:
          plate: {file: parts/plate.py, material: PETG}
        assembly: {root: plate}
    """))
    (d / "parts" / "plate.py").write_text(textwrap.dedent("""
        from build123d import *
        from kerf import iface
        def build(ctx):
            b = Box(20, 20, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
            b -= iface.bolt_pattern(ctx, "g", "M3", [(0, 0)], Location((0, 0, 5)), kind="clearance", depth=5)
            return ctx.finish(b)
    """))
    fp0 = P.load(str(d)).fingerprint()
    v0 = geom.volume(P.build(P.load(str(d))).items["plate"].shape)
    C.feedback("PETG", {"hole_M3": "+0.4"})
    proj = P.build(P.load(str(d)))
    cl = catalog.num(catalog.get("fdm_holes.M3"), "clearance_hole")
    assert v0 - geom.volume(proj.items["plate"].shape) == pytest.approx(math.pi / 4 * ((cl + 0.4) ** 2 - cl ** 2) * 5, rel=0.01)
    assert proj.fingerprint() != fp0          # a new measured fit makes the old review stale
