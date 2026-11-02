"""Bring-up programs (kerf/firmware.py) and the bench sub-assembly order in ASSEMBLY.md (kerf/ship.py joins)."""
import importlib.util
import shutil
import subprocess
from types import SimpleNamespace as NS

import pytest

from kerf import firmware, ship


def test_us_per_deg_is_the_datasheet_minimum():
    assert firmware.us_per_deg("servos.SG90")[0] == pytest.approx(1000 / 180)          # 1-2 ms = +/-90 (TowerPro)
    assert firmware.us_per_deg("servos.DS3225")[0] == pytest.approx(2000 / 270)        # 500-2500 us, 270 deg version
    k, why = firmware.us_per_deg("servos.MG996R")                                       # no published table
    assert k == firmware.SAFE_US_PER_DEG and "no published pulse table" in why


def _proj(pin="D9", ctrl_cat="boards.arduino_nano"):
    items = {"nano": NS(spec={"catalog": ctrl_cat}), "sv": NS(spec={"catalog": "servos.SG90"}),
             "horn": NS(spec={"catalog": "servo_horns.aluminum_micro_21T"})}
    wire = {"id": "sig", "from": "nano", "to": "sv", "kind": "signal"}
    if pin:
        wire["pin"] = pin
    proj = NS(items=items, data={"name": "t", "wiring": [wire]}, name="t")
    asm = NS(edges=[NS(parent="sv", child="horn", kind="revolute", name="tilt", range=(-35, 65))])
    return proj, asm


def test_servo_rows_come_from_signal_wires_and_horn_joints():
    proj, asm = _proj()
    (r,) = firmware.servos(proj, asm)
    assert (r["kind"], r["pin"], r["joint"], r["lo"], r["hi"]) == ("nano", "D9", "tilt", -35, 65)
    # the horn goes on with the servo centred at the middle of the travel, so the servo turns 50 deg either way
    assert r["centre"] == 15 and firmware._band(r) == 50 and firmware._lim(r) == 50
    asm.edges[0].centre = 0.0                                     # a joint can name where its horn goes on
    (r,) = firmware.servos(proj, asm)
    assert r["centre"] == 0 and firmware._band(r) == 35 and firmware._lim(r) == 65   # sweep only where both ways are safe
    with pytest.raises(ValueError, match="needs `pin:`"):
        firmware.servos(*_proj(pin=None))


def test_sketch_is_valid_cpp(tmp_path):
    if not shutil.which("g++"):
        pytest.skip("no g++")
    stub = tmp_path / "stub"
    stub.mkdir()
    (stub / "Arduino.h").write_text(
        "#pragma once\n#include <math.h>\n#include <stdlib.h>\n#include <string>\n"
        "#define constrain(x,a,b) ((x)<(a)?(a):((x)>(b)?(b):(x)))\ninline void delay(unsigned long) {}\n"
        "struct String { std::string s; String(const char* c=\"\"):s(c){} String(std::string x):s(x){}\n"
        "  void trim(){} bool startsWith(const char* p) const { return s.rfind(p,0)==0; }\n"
        "  String substring(int a) const { return String(s.substr(a)); } long toInt() const { return atol(s.c_str()); }\n"
        "  bool operator==(const char* o) const { return s==o; } };\n"
        "struct SerialT { void begin(long){} int available(){return 0;} int peek(){return 0;} String readStringUntil(char){return String();}\n"
        "  template<class T> void print(T){} template<class T> void print(T,int){} template<class T> void println(T){} };\n"
        "extern SerialT Serial;\n")
    (stub / "Servo.h").write_text("#pragma once\nstruct Servo { bool attached(){return false;} void attach(int){} "
                                  "void writeMicroseconds(int){} void detach(){} };\n")
    (stub / "Wire.h").write_text("#pragma once\n")
    (stub / "Adafruit_PWMServoDriver.h").write_text(       # the real library's signatures (v3)
        "#pragma once\n#include <stdint.h>\nstruct Adafruit_PWMServoDriver { bool begin(uint8_t p=0){return true;} "
        "void setOscillatorFrequency(uint32_t){} void setPWMFreq(float){} uint8_t setPWM(uint8_t, uint16_t, uint16_t){return 0;} "
        "void writeMicroseconds(uint8_t, uint16_t){} };\n")
    rows = [{"joint": "a", "servo": "s1", "model": "SG90", "pin": p, "lo": -30, "hi": 60, "centre": 15, "us_per_deg": 5.556, "us_why": "x"}
            for p in ("ch0", "ch1")]
    for pca in (True, False):
        r = [dict(x, pin=x["pin"].replace("ch", "D")) for x in rows] if not pca else rows
        src = tmp_path / "t.cpp"
        src.write_text("#include <Arduino.h>\n" + firmware.sketch("t", r, pca))
        assert "45.0f" in src.read_text()                       # a C++ float literal, never "45f"
        res = subprocess.run(["g++", "-std=c++11", "-fsyntax-only", f"-I{stub}", str(src)], capture_output=True, text=True)
        assert res.returncode == 0, res.stderr


def test_pi_script_drives_sysfs_pwm(tmp_path, monkeypatch):
    for ch in (0, 1):
        (tmp_path / "pwmchip0" / f"pwm{ch}").mkdir(parents=True)
    (tmp_path / "pwmchip0" / "export").write_text("")
    rows = [{"joint": "pan", "servo": "p", "model": "SG90", "pin": "GPIO18", "lo": -2, "hi": 2, "centre": 0, "us_per_deg": 5.556, "us_why": "x"},
            {"joint": "tilt", "servo": "t", "model": "SG90", "pin": "GPIO19", "lo": -2, "hi": 3, "centre": 0.5, "us_per_deg": 5.556, "us_why": "x"}]
    f = tmp_path / "bringup.py"
    f.write_text(firmware.pi_script("t", rows))
    monkeypatch.setenv("KERF_PWM_ROOT", str(tmp_path))
    spec = importlib.util.spec_from_file_location("bringup", f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    duty = lambda ch: int((tmp_path / "pwmchip0" / f"pwm{ch}" / "duty_cycle").read_text())   # noqa: E731
    m.main(["c"])
    assert duty(0) == duty(1) == 1_500_000                                   # centre = 1500 us
    m.main(["j1", "++"])
    assert duty(1) == round(1500 + 2.5 * 5.556) * 1000                       # clamped 2.5 deg from the 0.5 deg centre
    m.main(["s", "x"])
    assert (tmp_path / "pwmchip0" / "pwm0" / "enable").read_text() == "0"    # stop = no pulses
    with pytest.raises(ValueError, match="GPIO18 / GPIO19"):
        firmware.pi_script("t", [dict(rows[0], pin="GPIO4")])


def test_bench_sub_assembly_joins_at_its_parents_step():
    """pan_tilt's case: horn + bracket are listed first (bench), the horn's servo comes later; the pivot that ties the
    bracket to the yoke must wait until the sub-assembly is on."""
    by_child = {"horn": NS(parent="servo"), "bracket": NS(parent="horn"), "yoke": NS(parent="base"), "servo": NS(parent="yoke")}
    asm = NS(by_child=by_child)
    seq = [["base"], ["horn", "bracket"], ["yoke"], ["servo"]]
    bench, attach = ship.joins(asm, seq)
    assert bench == {2: 4} and attach == {4: [(2, "horn", "servo")]}
    when = ship._connect_steps(asm, seq, attach)
    assert when(["horn", "bracket"]) == (2, 1)          # their screws: on the bench
    assert when(["bracket", "yoke"]) == (4, 2)          # the pivot: after the sub-assembly is pressed on
    assert when(["servo", "yoke"]) == (4, 1)            # the servo's tab screws: before it


def test_wing_flight_controller_counts_as_a_flight_controller():
    """A stand-alone wing FC (drone.fcs.*) drives servos like an FC stack: bring-up names its outputs, no sketch."""
    from types import SimpleNamespace as S
    proj = S(items={"fc": S(spec={"catalog": "drone.fcs.f405_wmo"}), "stack": S(spec={"catalog": "drone.stacks.fc_20"}),
                    "nano": S(spec={"catalog": "boards.arduino_nano"})})
    assert firmware._kind(proj, "fc") == "fc" and firmware._kind(proj, "stack") == "fc"
    assert firmware._kind(proj, "nano") == "nano"
