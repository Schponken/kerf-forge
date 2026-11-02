"""Prove the generated bring-up programs (kerf/firmware.py) do what BRINGUP.md says, before anyone plugs a servo in.

`kerf firmware-check <p>` (and `kerf build`, whenever a project has firmware):
- Arduino sketches (Nano driving servos, or Nano + PCA9685 over I2C) are compiled with arduino-cli for the real board
  (arduino:avr:nano, core and libraries at the versions pinned below, installed by setup.sh under .cache/arduino).
- The compiled Nano program then runs in simavr (an ATmega328P simulator) through kerf/assets/avrsim.c. It is sent the
  same Serial commands a person types (`c`, then `s`, then `x`) and every servo pulse is recorded: on the Nano's own pins
  directly, and for a PCA9685 by decoding the sketch's I2C register writes the way the chip applies them (simavr cannot
  model the chip itself, so avrsim answers as a PCA9685 at 0x40: register file, auto-increment, PRE_SCALE only in sleep).
- Raspberry Pi scripts are byte-compiled and run against a stub PWM sysfs tree that records every write.
Each recorded trace is checked against the joint table: pulses only on the wired outputs, all inside PULSE_LIMITS, a
servo frame near 50 Hz, exactly 1500 us after `c`, the sweep never commanding a joint past the nearer end of its range
(and actually reaching +/- that band and coming back to centre), and no pulses after `x`.

A tool that is missing is reported as NOT RUN with what to install; it is never counted as a pass.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import firmware as F

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / ".cache" / "arduino"
ARDUINO_CLI = "1.3.1"                     # downloads.arduino.cc/arduino-cli/, sha256 pinned in setup.sh
CORE = "arduino:avr@1.8.6"
LIBS = ["Servo@1.2.2", "Adafruit PWM Servo Driver Library@3.0.2", "Adafruit BusIO@1.16.2"]
FQBN = "arduino:avr:nano"
AVRSIM_SRC = Path(__file__).parent / "assets" / "avrsim.c"
PCA_OSC_HZ = F.PCA_OSC_HZ                 # what the generated sketch tells the Adafruit library (setOscillatorFrequency)

T_CENTRE_MS = 500                         # after setup() has printed its banner
T_SWEEP_MS = 1500
SETTLE_MS = 60                            # a command takes effect within a few servo frames
FRAME_MS = (18.0, 22.5)                   # 50 Hz servo frame, +/- 10 %
NANO_TOL_US = 3.0                         # Servo library: 0.5 us timer ticks + interrupt latency (measured < 0.2 us)
TOL_DEG = 0.6                             # reach check: the sweep's last 1 deg step lands on its target; rounding
OVER_TOL_US = 1.0                         # past-the-band check: integer-us rounding (0.5 us) + simulated timing jitter


def env() -> dict:
    result = {**os.environ, "ARDUINO_DIRECTORIES_DATA": str(TOOLS / "data"),
              "ARDUINO_DIRECTORIES_DOWNLOADS": str(TOOLS / "staging"), "ARDUINO_DIRECTORIES_USER": str(TOOLS / "user")}
    if "ARDUINO_NETWORK_PROXY" not in result:
        proxy = next((result[k] for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy") if result.get(k)), None)
        if proxy:
            result["ARDUINO_NETWORK_PROXY"] = proxy
    return result


def arduino_cli() -> str | None:
    p = TOOLS / "bin" / "arduino-cli"
    return str(p) if p.exists() else None


def _simavr_include() -> Path | None:
    cands = [Path("/usr/include/simavr"), Path("/usr/local/include/simavr"), Path("/opt/homebrew/include/simavr")]
    if shutil.which("brew"):
        try:
            cands.append(Path(subprocess.run(["brew", "--prefix"], capture_output=True, text=True, timeout=20).stdout.strip())
                         / "include" / "simavr")
        except (OSError, subprocess.SubprocessError):
            pass
    return next((c for c in cands if (c / "sim_avr.h").exists()), None)


def avrsim() -> tuple[str | None, str]:
    """Path to the compiled simulator harness (built on first use, rebuilt when avrsim.c changes), or None and why."""
    exe = TOOLS / "avrsim"
    if exe.exists() and exe.stat().st_mtime >= AVRSIM_SRC.stat().st_mtime:
        return str(exe), "ok"
    inc = _simavr_include()
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if inc is None or cc is None:
        return None, ("simavr headers/library not found (Linux: apt install simavr libsimavr-dev; macOS: brew tap "
                      "osx-cross/avr && brew install simavr) or no C compiler" if inc is None else "no C compiler (cc)")
    TOOLS.mkdir(parents=True, exist_ok=True)
    lib = inc.parent.parent / "lib"
    err = ""
    for extra in ([], ["-lelf"]):
        r = subprocess.run([cc, "-O2", "-o", str(exe), str(AVRSIM_SRC), f"-I{inc}", f"-L{lib}", f"-Wl,-rpath,{lib}",
                            "-lsimavr", *extra], capture_output=True, text=True)
        if r.returncode == 0:
            return str(exe), "ok"
        err = r.stderr.strip()[-400:]
    return None, f"could not build the simavr harness: {err}"


def tools() -> dict:
    sim, why = avrsim()
    cli = arduino_cli()
    core = cli is not None and (TOOLS / "data" / "packages" / "arduino" / "hardware" / "avr" / CORE.split("@")[1]).exists()
    return {"arduino_cli": cli, "core": core, "avrsim": sim, "avrsim_why": why}


# ---------------------------------------------------------------- compile + run

def compile_sketch(sketch_dir: Path, build_dir: Path) -> dict:
    cli = arduino_cli()
    build_dir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([cli, "compile", "--fqbn", FQBN, "--warnings", "default", "--output-dir", str(build_dir), str(sketch_dir)],
                       capture_output=True, text=True, env=env(), timeout=600)
    elf = next(iter(build_dir.glob("*.ino.elf")), None)
    log = (r.stdout + r.stderr).strip()
    return {"ok": r.returncode == 0 and elf is not None, "elf": str(elf) if elf else None,
            "log": log[-3000:], "size": next((ln for ln in log.splitlines() if ln.startswith("Sketch uses")), "")}


def simulate(elf: str, end_ms: float, inputs: list[tuple[float, str]]) -> dict:
    """Run the ELF in simavr; returns pulses per Arduino pin, Serial lines, PCA9685 register writes, NACKed addresses."""
    sim, why = avrsim()
    if sim is None:
        raise RuntimeError(why)
    args = [sim, elf, f"{end_ms:.0f}"] + [f"{t:.0f}:{s}" for t, s in inputs]
    r = subprocess.run(args, capture_output=True, text=True, timeout=max(120, end_ms / 1000 * 4 + 60))
    out = {"pulses": {}, "uart": [], "i2c": [], "nack": [], "end_ms": None, "state": None, "rc": r.returncode,
           "stderr": r.stderr[-500:]}
    for ln in r.stdout.splitlines():
        p = ln.split(" ", 3)
        if p[0] == "P":
            out["pulses"].setdefault(int(p[1]), []).append((float(p[2]) / 1000, float(p[3])))
        elif p[0] == "U":
            q = ln.split(" ", 2)
            out["uart"].append((float(q[1]), q[2] if len(q) > 2 else ""))
        elif p[0] == "I":
            q = ln.split()
            out["i2c"].append((float(q[1]) / 1000, int(q[2]), int(q[3]), len(q) > 4))
        elif p[0] == "N":
            out["nack"].append((float(p[1]) / 1000, int(p[2])))
        elif p[0] == "END":
            out["end_ms"], out["state"] = float(p[1]), int(p[2])
    return out


def pca_series(i2c: list, osc: float = PCA_OSC_HZ) -> tuple[dict, list]:
    """PCA9685 register writes -> {channel: [(t_ms, pulse_us or 0 = off)]} and the frame periods (ms) in force."""
    reg = [0] * 256
    reg[0xFE] = 0x1E                      # power-on PRE_SCALE (200 Hz)
    series, periods = {}, []
    for t, r, v, ignored in i2c:
        if ignored:
            continue
        reg[r] = v
        if 6 <= r < 70 and (r - 6) % 4 == 3:                   # LEDn_OFF_H: the library writes ON_L..OFF_H in one go
            ch = (r - 6) // 4
            on, off = reg[r - 3] | (reg[r - 2] & 0x0F) << 8, reg[r - 1] | (v & 0x0F) << 8
            per_count = (reg[0xFE] + 1) / osc * 1e6
            if v & 0x10:
                us = 0.0                                       # full off
            elif reg[r - 2] & 0x10:
                us = float("inf")                              # full on: a DC level, not a servo pulse
            else:
                us = ((off - on) % 4096) * per_count
            series.setdefault(ch, []).append((t, us))
            periods.append(4096 * (reg[0xFE] + 1) / osc * 1000)   # the frame in force when a pulse is set
    return series, periods


def pi_run(script: Path, limit_ms: float = 600_000) -> dict:
    """Byte-compile the Pi script, then run c / s / x against a stub PWM sysfs tree that records every write."""
    import py_compile
    try:
        py_compile.compile(str(script), doraise=True)
    except py_compile.PyCompileError as e:
        return {"ok": False, "error": f"does not byte-compile: {e.msg}"}
    runner = r'''
import importlib.util, json, os, sys
root = os.path.join(os.path.dirname(__file__), "pwm")
for ch in (0, 1):
    os.makedirs(os.path.join(root, "pwmchip0", "pwm%d" % ch))
open(os.path.join(root, "pwmchip0", "export"), "w", encoding="utf-8").close()
os.environ["KERF_PWM_ROOT"] = root
spec = importlib.util.spec_from_file_location("bringup", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
clock = [0.0]
rec = []
real_put = m.put
def put(path, value):
    rec.append((clock[0], os.path.relpath(path, root), str(value)))
    real_put(path, value)
m.put = put
def sleep(s):
    clock[0] += s * 1000
    if clock[0] > LIMIT:
        print("KERF_HANG %.0f" % clock[0])
        sys.exit(3)
m.time.sleep = sleep
marks = {}
for cmd, at in (("c", T_C), ("s", T_S), ("x", None)):
    if at is not None:
        clock[0] = max(clock[0], at)
    marks[cmd] = clock[0]
    m.main([cmd])
    clock[0] += 50
print("KERF_JSON " + json.dumps({"rec": rec, "marks": marks, "channel": {str(k): v for k, v in m.CHANNEL.items()}}))
'''.replace("T_C", str(T_CENTRE_MS)).replace("T_S", str(T_SWEEP_MS)).replace("LIMIT", str(limit_ms))
    with tempfile.TemporaryDirectory() as d:
        rf = Path(d) / "run.py"
        rf.write_text(runner, encoding="utf-8")
        r = subprocess.run([sys.executable, "-I", str(rf), str(script)], capture_output=True, text=True, timeout=300)
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("KERF_JSON ")), None)
    if "KERF_HANG" in r.stdout:
        return {"ok": False, "error": f"the sweep did not finish within {limit_ms / 1000:.0f} s of simulated time (stuck in a loop)"}
    if r.returncode != 0 or line is None:
        return {"ok": False, "error": f"run against the stub PWM failed (exit {r.returncode}): {r.stderr.strip()[-800:]}"}
    d = json.loads(line[len("KERF_JSON "):])
    gpio_of = {v: int(k) for k, v in d["channel"].items()}
    state, series, periods = {}, {}, []
    for t, path, val in d["rec"]:
        parts = path.split(os.sep)
        if len(parts) != 3 or not parts[1].startswith("pwm"):
            continue
        g = gpio_of.get(int(parts[1][3:]))
        st = state.setdefault(g, {"period": 0, "duty": 0, "enable": 0})
        st[parts[2] if parts[2] != "duty_cycle" else "duty"] = int(val)
        if parts[2] == "period":
            periods.append(int(val) / 1e6)
        if parts[2] in ("enable", "duty_cycle"):
            series.setdefault(g, []).append((t, st["duty"] / 1000 if st["enable"] else 0.0))
    return {"ok": True, "series": series, "periods": periods, "marks": d["marks"], "stdout": r.stdout[-2000:]}


# ---------------------------------------------------------------- checks

def _sweep_ms(rows: list[dict], per_step_ms: float) -> float:
    return sum(4 * F._band(r) / F.SWEEP_STEP_DEG for r in rows) * per_step_ms


def check_trace(rows: list[dict], key, series: dict, t_c: float, t_s: float, t_x: float, tol_us: float,
                stopped: dict, held: bool = False) -> list[str]:
    """Problems with one controller's recorded pulses. series: {output: [(t_ms, us, 0 = off)]}, one sample per pulse
    (Nano pins) or, held=True, one per change of a setting that holds until the next (PCA9685 registers, Pi sysfs);
    stopped: {output: no pulses after `x`}."""
    probs = []
    used = {key(r) for r in rows}
    for out_id, s in series.items():
        if out_id not in used and any(us > 0 for _, us in s):
            probs.append(f"pulses on output {out_id}, which no servo is wired to")
    for r in rows:
        o, name = key(r), f"{r['joint']} ({r['servo']} on {r['pin']})"
        s = series.get(o, [])
        if not s:
            probs.append(f"{name}: no servo pulses recorded at all")
            continue
        lo_us, hi_us = F.PULSE_LIMITS
        bad = [us for _, us in s if us and not (lo_us - tol_us <= us <= hi_us + tol_us)]
        if bad:
            probs.append(f"{name}: pulse {bad[0]:.1f} us outside PULSE_LIMITS {lo_us}-{hi_us} us")
        early = [us for t, us in s if t < t_c and us > 0]
        if early:
            probs.append(f"{name}: {early[0]:.1f} us pulses before any command: the servo would jump at power-up")
        win = [us for t, us in s if t_c + (0 if held else SETTLE_MS) <= t < t_s]
        cen = [us for us in win if us > 0]      # a held output may pass through "off" while it is being enabled
        if not cen or win[-1] == 0:
            probs.append(f"{name}: no pulses after `c` (centre)")
        elif any(abs(us - F.CENTRE_US) > tol_us for us in cen):
            probs.append(f"{name}: `c` gave {min(cen):.1f}-{max(cen):.1f} us, not {F.CENTRE_US} us")
        sw = [(t, us) for t, us in s if t_s <= t < t_x and us > 0]
        band, k = F._band(r), r["us_per_deg"]
        if not sw:
            probs.append(f"{name}: no pulses during the sweep `s`")
            continue
        deg = [(us - F.CENTRE_US) / k for _, us in sw]
        tol_deg = TOL_DEG + tol_us / k
        if max(abs(d) for d in deg) > band + OVER_TOL_US / k:
            worst = max(deg, key=abs)
            probs.append(f"{name}: sweep commands {worst:+.1f} deg from the centre ({r['centre']:g} deg), past the "
                         f"nearer end of its {r['lo']:g} to {r['hi']:g} deg range (+/- {band:g} deg allowed)")
        if band > 0 and (max(deg) < band - 1 - tol_deg or min(deg) > -band + 1 + tol_deg):
            probs.append(f"{name}: sweep only reached {min(deg):+.1f} to {max(deg):+.1f} deg, not +/- {band:g} deg")
        if abs(sw[-1][1] - F.CENTRE_US) > tol_us:
            probs.append(f"{name}: the sweep ended at {sw[-1][1]:.1f} us, not back at centre ({F.CENTRE_US} us)")
        if not stopped.get(o, False):
            probs.append(f"{name}: still pulsing after `x` (stop): the servo would not go limp")
    return probs


def check_nano(rows: list[dict], sketch_dir: Path, work: Path, pca: bool) -> dict:
    res = {"kind": "nano+pca9685" if pca else "nano", "sketch": str(sketch_dir)}
    c = compile_sketch(sketch_dir, work / "build")
    res["compile"] = {"ok": c["ok"], "size": c["size"], "log": c["log"] if not c["ok"] else ""}
    if not c["ok"]:
        res["status"] = "FAIL"
        res["problems"] = ["does not compile for Arduino Nano (arduino-cli " + FQBN + "):\n" + c["log"][-1500:]]
        return res
    sim, why = avrsim()
    if sim is None:
        res["status"], res["problems"] = "COMPILED_ONLY", [f"not simulated: {why}"]
        return res
    t_x = T_SWEEP_MS + _sweep_ms(rows, F.SWEEP_STEP_MS * 1.25) + 1000
    end = t_x + 600
    s = simulate(c["elf"], end, [(T_CENTRE_MS, "c"), (T_SWEEP_MS, "s"), (t_x, "x")])
    probs = []
    if s["state"] is None or s["rc"] != 0:
        probs.append(f"simulation did not finish (exit {s['rc']}, cpu state {s['state']}): {s['stderr']}")
    sweeps = [t for t, ln in s["uart"] if ln.startswith("sweep ")]
    if len(sweeps) != len(rows):
        probs.append(f"the sweep printed {len(sweeps)} of {len(rows)} 'sweep <joint>' lines before `x`")
    if not any(ln.startswith("stopped") and t >= t_x for t, ln in s["uart"]):
        probs.append("`x` did not print 'stopped' (command not handled)")
    nano_rows = [r for r in rows if r["kind"] == "nano"] if pca else rows
    pca_rows = [r for r in rows if r["kind"] == "pca9685"] if pca else []
    if pca:
        series, periods = pca_series(s["i2c"])
        key = lambda r: F._num(r["pin"], "ch")              # noqa: E731
        stopped = {ch: bool(v) and v[-1][1] == 0 and v[-1][0] >= t_x for ch, v in series.items()}
        pre = [v for _, reg, v, ig in s["i2c"] if reg == 0xFE and not ig]
        tol = 1 + 1e6 * ((pre[-1] if pre else 0x1E) + 1) / PCA_OSC_HZ    # one PCA9685 step (whole counts only)
        if s["nack"]:
            probs.append(f"I2C writes to address 0x{s['nack'][0][1] >> 1:02X}, where no PCA9685 answers")
        if not periods:
            probs.append("the sketch never set the PCA9685 frame rate (PRE_SCALE)")
        res["pca9685"] = {"frame_ms": [round(p, 2) for p in periods], "register_writes": len(s["i2c"]),
                          "osc_hz_assumed": PCA_OSC_HZ}
    else:
        series = {pin: [(t, us) for t, us in v] for pin, v in s["pulses"].items() if pin > 1}   # D0/D1 = Serial
        key = lambda r: F._num(r["pin"], "D")               # noqa: E731
        stopped = {pin: not any(t > t_x + SETTLE_MS for t, _ in v) for pin, v in series.items()}
        tol = NANO_TOL_US
        periods = []
        for v in series.values():
            rises = [t for t, _ in v if T_CENTRE_MS + SETTLE_MS < t < t_x]
            periods += [b - a for a, b in zip(rises, rises[1:])]
    if periods and not all(FRAME_MS[0] <= p <= FRAME_MS[1] for p in periods):
        probs.append(f"servo frame {min(periods):.1f}-{max(periods):.1f} ms, not 50 Hz ({FRAME_MS[0]}-{FRAME_MS[1]} ms)")
    active_rows = pca_rows if pca else nano_rows
    probs += check_trace(active_rows, key, series, T_CENTRE_MS, T_SWEEP_MS, t_x, tol, stopped, held=pca)
    res["simulated_ms"] = s["end_ms"]
    res["tolerance_us"] = round(tol, 2)
    res["trace"] = _summary(active_rows, key, series, T_CENTRE_MS, T_SWEEP_MS, t_x)
    if pca:
        # D0/D1 carry Serial, A4/A5 carry I2C; every other Nano output is checked separately.
        direct = {pin: v for pin, v in s["pulses"].items() if pin not in (0, 1, 18, 19)}
        direct_key = lambda r: F._num(r["pin"], "D")  # noqa: E731
        stopped = {pin: not any(t > t_x + SETTLE_MS for t, _ in v) for pin, v in direct.items()}
        probs += check_trace(nano_rows, direct_key, direct, T_CENTRE_MS, T_SWEEP_MS, t_x, NANO_TOL_US, stopped)
        rises = [[t for t, _ in v if T_CENTRE_MS + SETTLE_MS < t < t_x] for v in direct.values()]
        if any(not FRAME_MS[0] <= b - a <= FRAME_MS[1] for v in rises for a, b in zip(v, v[1:])):
            probs.append("Nano servo frame is not 50 Hz")
        res["trace"] += _summary(nano_rows, direct_key, direct, T_CENTRE_MS, T_SWEEP_MS, t_x)
        if nano_rows:
            res["nano_tolerance_us"] = NANO_TOL_US
    res["serial"] = [ln for _, ln in s["uart"]][:40]
    res["problems"] = probs
    res["status"] = "FAIL" if probs else "PASS"
    return res


def check_pi(rows: list[dict], script: Path) -> dict:
    res = {"kind": "pi", "script": str(script)}
    r = pi_run(script, T_SWEEP_MS + _sweep_ms(rows, F.SWEEP_STEP_MS) * 2 + 5000)
    if not r["ok"]:
        res["status"], res["problems"] = "FAIL", [r["error"]]
        return res
    key = lambda x: F._num(x["pin"], "GPIO")                # noqa: E731
    t_x = r["marks"]["x"]
    stopped = {g: bool(v) and v[-1][1] == 0 for g, v in r["series"].items()}
    probs = []
    if r["periods"] and not all(FRAME_MS[0] <= p <= FRAME_MS[1] for p in r["periods"]):
        probs.append(f"PWM period {min(r['periods']):.1f} ms, not 50 Hz")
    probs += check_trace(rows, key, r["series"], r["marks"]["c"], r["marks"]["s"], t_x, 0.5, stopped, held=True)
    res["trace"] = _summary(rows, key, r["series"], r["marks"]["c"], r["marks"]["s"], t_x)
    res["problems"], res["status"] = probs, "FAIL" if probs else "PASS"
    return res


def _summary(rows, key, series, t_c, t_s, t_x) -> list[dict]:
    out = []
    for r in rows:
        s = series.get(key(r), [])
        cen = [us for t, us in s if t_c <= t < t_s and us > 0]
        sw = [us for t, us in s if t_s <= t < t_x and us > 0]
        out.append({"joint": r["joint"], "output": r["pin"], "range_deg": [r["lo"], r["hi"]], "centre_deg": r["centre"],
                    "band_deg": F._band(r), "us_per_deg": r["us_per_deg"], "samples": len(s),
                    "centre_us": [round(min(cen), 2), round(max(cen), 2)] if cen else None,
                    "sweep_us": [round(min(sw), 2), round(max(sw), 2)] if sw else None,
                    "sweep_deg": [round((min(sw) - F.CENTRE_US) / r["us_per_deg"], 2),
                                  round((max(sw) - F.CENTRE_US) / r["us_per_deg"], 2)] if sw else None})
    return out


def check_dir(rows: list[dict], fwdir: Path, work: Path | None = None) -> dict:
    """Check the program kerf/firmware.py wrote into fwdir for these servo rows. status: PASS / FAIL / NOT_RUN /
    COMPILED_ONLY / NONE (no program: flight-controller only)."""
    kinds = {r["kind"] for r in rows} - {"fc"}
    rows = [r for r in rows if r["kind"] != "fc"]
    if not rows:
        return {"status": "NONE", "problems": [], "programs": []}
    if work is None:
        with tempfile.TemporaryDirectory(prefix="kerf-fw-") as d:
            return check_dir(rows, fwdir, Path(d))
    if kinds == {"pi"}:
        res = check_pi(rows, fwdir / "bringup.py")
    else:
        sk = sorted(p.parent for p in fwdir.glob("*/*.ino") if p.stem == p.parent.name)
        if not sk:
            return {"status": "FAIL", "problems": [f"no sketch under {fwdir}"], "programs": []}
        if arduino_cli() is None or not tools()["core"]:
            return {"status": "NOT_RUN", "programs": [str(p) for p in sk],
                    "problems": ["arduino-cli / the arduino:avr core is not installed under .cache/arduino: run ./setup.sh"]}
        programs = []
        for path in sk:
            try:
                program = check_nano(rows, path, work / path.name, pca="pca9685" in kinds)
            except (OSError, subprocess.SubprocessError, ValueError) as e:
                program = {"kind": "nano+pca9685" if "pca9685" in kinds else "nano", "sketch": str(path),
                           "status": "FAIL", "problems": [f"could not verify program: {type(e).__name__}: {e}"]}
            programs.append(program)
        if len(programs) == 1:
            res = programs[0]
        else:
            res = {"kind": programs[0]["kind"], "programs": programs,
                   "status": "FAIL" if any(p["status"] == "FAIL" for p in programs) else
                             "COMPILED_ONLY" if any(p["status"] == "COMPILED_ONLY" for p in programs) else "PASS",
                   "problems": [f"{Path(p['sketch']).name}: {msg}" for p in programs for msg in p["problems"]]}
    res["tools"] = {"arduino_cli": ARDUINO_CLI, "core": CORE, "libraries": LIBS, "fqbn": FQBN,
                    "simulator": "simavr (kerf/assets/avrsim.c)" if res["kind"] != "pi" else "stub PWM sysfs"}
    return res


def check_project(name: str) -> dict:
    """`kerf firmware-check <p>`: regenerate out/firmware from the current project.yaml, then check it."""
    from . import project as P, assembly as A
    proj = P.load(name)
    P.build(proj)
    bad = [k for k, it in proj.items.items() if it.error]
    if bad:
        return {"project": name, "status": "FAIL", "problems": [f"{k} failed to build: {proj.items[k].error}" for k in bad]}
    asm = A.plan(proj)
    out = proj.out("report.json").parent
    out.mkdir(parents=True, exist_ok=True)
    info = F.write(proj, asm, out)
    if info is None:
        return {"project": name, "status": "NONE", "problems": [], "why": "no controller-driven servo: no firmware"}
    res = check_dir(info["rows"], out / "firmware")
    res["project"] = name
    (out / "firmware" / "FIRMWARE_CHECK.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


def lines(res: dict) -> list[str]:
    st = res["status"]
    head = {"PASS": "PASS", "FAIL": "FAIL", "NOT_RUN": "NOT RUN", "COMPILED_ONLY": "COMPILED ONLY (not simulated)",
            "NONE": "no firmware"}[st]
    L = [f"firmware {head}  {res.get('project', '')}  {res.get('kind', '')}  {res.get('compile', {}).get('size', '')}".rstrip()]
    for t in res.get("trace", []):
        L.append(f"  {t['joint']:<12} {t['output']:<7} range {t['range_deg'][0]:g}..{t['range_deg'][1]:g} deg, "
                 f"centre {t['centre_us']} us, sweep {t['sweep_us']} us = {t['sweep_deg']} deg (allowed +/- {t['band_deg']:g})")
    L += [f"  - {p}" for p in res.get("problems", [])]
    for program in res.get("programs", []):
        if isinstance(program, dict):
            L.append(f"  {Path(program['sketch']).name}: {program['status']}")
    return L
