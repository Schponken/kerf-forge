"""kerf/fwcheck.py: generated bring-up programs compiled (arduino-cli), run (simavr / stub PWM sysfs) and their servo
pulses checked against the joint table. Includes deliberately broken programs that must FAIL."""
import json
import re
from types import SimpleNamespace as NS

import pytest

pytestmark = pytest.mark.slow

from kerf import firmware as F, fwcheck as W

T = W.tools()
need_cli = pytest.mark.skipif(not (T["arduino_cli"] and T["core"]), reason="arduino-cli + arduino:avr not installed: ./setup.sh")
need_sim = pytest.mark.skipif(T["avrsim"] is None, reason=f"simavr harness unavailable: {T['avrsim_why']}")


def _row(pin, lo=-12.0, hi=8.0, centre=0.0, k=5.556, joint="j"):
    return {"joint": joint, "servo": f"sv_{pin}", "model": "SG90", "kind": "nano", "pin": pin, "lo": lo, "hi": hi,
            "centre": centre, "us_per_deg": k, "us_why": "test"}


def _sketch(tmp_path, rows, pca, edit=None):
    d = tmp_path / "firmware" / "t_bringup"
    d.mkdir(parents=True)
    src = F.sketch("t", rows, pca)
    (d / "t_bringup.ino").write_text(edit(src) if edit else src, encoding="utf-8")
    return tmp_path / "firmware"


# ---------------------------------------------------------------- pure checks (no tools)

def test_trace_check_catches_overtravel_early_pulses_and_no_stop():
    r = _row("D9")                                   # centre 0 in -12..8: sweep band +/- 8
    key = lambda x: F._num(x["pin"], "D")            # noqa: E731
    ok = [(600 + i * 20, 1500.0) for i in range(40)] + [(1600, 1500 + 8 * 5.556), (1700, 1500 - 8 * 5.556), (1800, 1500.0)]
    assert W.check_trace([r], key, {9: ok}, 500, 1500, 2000, 3, {9: True}) == []
    over = ok[:-1] + [(1750, 1500 - 9.5 * 5.556), (1800, 1500.0)]
    p = W.check_trace([r], key, {9: over}, 500, 1500, 2000, 3, {9: True})
    assert any("past the nearer end" in x for x in p)
    p = W.check_trace([r], key, {9: [(100, 1700.0)] + ok}, 500, 1500, 2000, 3, {9: True})
    assert any("before any command" in x for x in p)
    p = W.check_trace([r], key, {9: ok, 10: [(700, 1500.0)]}, 500, 1500, 2000, 3, {9: False, 10: True})
    assert any("no servo is wired" in x for x in p) and any("still pulsing" in x for x in p)
    p = W.check_trace([r], key, {9: ok[:40] + [(1600, 1520.0), (1800, 1500.0)]}, 500, 1500, 2000, 3, {9: True})
    assert any("only reached" in x for x in p)                                   # the sweep never got to its band


def test_pca_register_decode_matches_the_chip():
    # prescale 131 @ 27 MHz: 4.889 us per step; ch3 = registers 18..21; OFF_H bit 4 = full off
    w = [(1.0, 0xFE, 131, False), (2.0, 18, 0, False), (2.0, 19, 0, False), (2.0, 20, 50, False), (2.0, 21, 1, False),
         (3.0, 21, 0x10, False), (4.0, 0xFE, 3, True)]
    s, per = W.pca_series(w)
    assert s[3][0][1] == pytest.approx(306 * 132 / 27e6 * 1e6) and s[3][1][1] == 0.0
    assert per[0] == pytest.approx(20.02, abs=0.01)


def test_pi_script_runs_on_stub_pwm_and_a_broken_one_fails(tmp_path):
    rows = [dict(_row("GPIO18", -20, 20), kind="pi"), dict(_row("GPIO19", -35, 65, 15), kind="pi")]
    (tmp_path / "bringup.py").write_text(F.pi_script("t", rows), encoding="utf-8")
    res = W.check_dir(rows, tmp_path)
    assert res["status"] == "PASS", res["problems"]
    assert res["trace"][1]["centre_us"] == [1500.0, 1500.0] and res["trace"][1]["sweep_deg"][1] == pytest.approx(50, abs=0.1)
    # broken: twice the datasheet us/deg, so every joint's pulses go past its range
    (tmp_path / "bringup.py").write_text(F.pi_script("t", rows).replace('"us_per_deg": 5.556', '"us_per_deg": 11.112'))
    res = W.check_dir(rows, tmp_path)
    assert res["status"] == "FAIL" and sum("past the nearer end" in p for p in res["problems"]) == 2
    # broken: a sweep band past the jog limit never arrives (the clamp holds it back): caught as a hang, not waited on
    (tmp_path / "bringup.py").write_text(F.pi_script("t", rows).replace('"band": 50', '"band": 60'), encoding="utf-8")
    res = W.check_dir(rows, tmp_path)
    assert res["status"] == "FAIL" and "did not finish" in res["problems"][0]
    (tmp_path / "bringup.py").write_text(F.pi_script("t", rows).replace("def main(", "def main(:"), encoding="utf-8")
    res = W.check_dir(rows, tmp_path)
    assert res["status"] == "FAIL" and "byte-compile" in res["problems"][0]


def test_missing_toolchain_is_not_run_never_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(W, "arduino_cli", lambda: None)
    res = W.check_dir([_row("D9")], _sketch(tmp_path, [_row("D9")], False))
    assert res["status"] == "NOT_RUN" and "setup.sh" in res["problems"][0]


# ---------------------------------------------------------------- real toolchain: arduino-cli + simavr

@need_cli
@need_sim
def test_nano_sketch_compiles_and_simulates_within_range(tmp_path):
    rows = [_row("D9", joint="a"), _row("D3", -5, 25, 10, joint="b")]
    res = W.check_dir(rows, _sketch(tmp_path, rows, pca=False))
    assert res["status"] == "PASS", res["problems"]
    a, b = res["trace"]
    assert a["centre_us"][0] == pytest.approx(1500, abs=1) and a["centre_us"][1] == pytest.approx(1500, abs=1)
    assert a["sweep_deg"][0] == pytest.approx(-8, abs=1.1) and a["sweep_deg"][1] == pytest.approx(8, abs=1.1)
    assert b["sweep_deg"][1] == pytest.approx(15, abs=1.1)
    assert any(ln.startswith("stopped") for ln in res["serial"])


@need_cli
def test_broken_sketch_fails_to_compile(tmp_path):
    rows = [_row("D9")]
    fw = _sketch(tmp_path, rows, pca=False, edit=lambda s: s.replace("void limp() {", "void limp() { undefinedCall();"))
    res = W.check_dir(rows, fw)
    assert res["status"] == "FAIL" and "does not compile" in res["problems"][0] and "undefinedCall" in res["problems"][0]


@need_cli
@need_sim
def test_sketch_that_overdrives_a_joint_fails_in_simulation(tmp_path):
    rows = [_row("D9")]                              # band 8 deg; the edit doubles us/deg -> 16 deg of pulse
    fw = _sketch(tmp_path, rows, pca=False, edit=lambda s: re.sub(r"5\.556f", "11.112f", s))
    res = W.check_dir(rows, fw)
    assert res["status"] == "FAIL" and any("past the nearer end" in p for p in res["problems"])


@need_cli
@need_sim
def test_pca9685_sketch_decoded_from_i2c(tmp_path):
    rows = [dict(_row("ch2", -6, 6, joint="a"), kind="pca9685"), dict(_row("ch0", 0, 10, 5, joint="b"), kind="pca9685")]
    res = W.check_dir(rows, _sketch(tmp_path, rows, pca=True))
    assert res["status"] == "PASS", res["problems"]
    assert res["pca9685"]["frame_ms"][-1] == pytest.approx(20.0, abs=0.2)
    for t in res["trace"]:                          # whole PCA steps rounded toward centre: never past the band
        assert max(abs(d) for d in t["sweep_deg"]) <= t["band_deg"] + 1e-6
    # broken: the driver addressed at 0x41 (A0 jumper) while the board is wired at 0x40
    fw = _sketch(tmp_path / "bad", rows, pca=True,
                 edit=lambda s: s.replace("Adafruit_PWMServoDriver();", "Adafruit_PWMServoDriver(0x41);"))
    res = W.check_dir(rows, fw)
    assert res["status"] == "FAIL" and any("0x41" in p for p in res["problems"])


@need_cli
@need_sim
def test_build_records_the_firmware_check(tmp_path):
    """pipeline._firmware_check: runs on what kerf/firmware.py wrote and a FAIL becomes a build problem."""
    from kerf import pipeline
    items = {"nano": NS(spec={"catalog": "boards.arduino_nano"}), "sv": NS(spec={"catalog": "servos.SG90"})}
    proj = NS(items=items, name="t", data={"name": "t", "wiring": [{"id": "s", "from": "nano", "to": "sv", "kind": "signal", "pin": "D9"}]})
    asm = NS(edges=[NS(parent="sv", child="horn", kind="revolute", name="tilt", range=(-6, 6))])
    info = F.write(proj, asm, tmp_path)
    rep = {"files": {"ship": {"firmware": {"program": info["program"]}}}, "problems": [], "warnings": []}
    pipeline._firmware_check(proj, asm, rep, tmp_path)
    assert rep["firmware_check"]["status"] == "PASS" and not rep["problems"]
    assert json.loads((tmp_path / "firmware" / "FIRMWARE_CHECK.json").read_text())["status"] == "PASS"
    ino = next((tmp_path / "firmware").glob("*/*.ino"))
    ino.write_text(ino.read_text().replace("const int N", "const int N = ;\nconst int M"))
    asm2 = NS(edges=asm.edges)
    rep = {"files": {"ship": {"firmware": {"program": info["program"]}}}, "problems": [], "warnings": []}
    pipeline._firmware_check(proj, asm2, rep, tmp_path)
    assert rep["firmware_check"]["status"] == "FAIL" and rep["problems"][0].startswith("firmware: does not compile")
