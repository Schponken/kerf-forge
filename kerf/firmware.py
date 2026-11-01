"""Bring-up and sweep-test programs for every project whose servos are driven by a controller Kerf knows.

`kerf build` writes out/firmware/: an Arduino sketch (Nano driving servos directly, or a Nano driving a PCA9685 over
I2C) or a Raspberry Pi Python script, plus BRINGUP.md. ASSEMBLY.md's "Step 0b" uses it to centre every servo before
its horn goes on, and the sweep test after assembly.

What the program knows comes from project.yaml: signal wires (`wiring:` rows with `kind: signal` from a controller to
a servo) carry `pin:` (Nano `D9`, Pi `GPIO18`, PCA9685 `ch3`, flight controller `M4`); each servo's travel is the range
of the revolute joint it drives (its horn joint). Degrees become pulse widths with the SMALLEST microseconds-per-degree
the servo's datasheet allows (servos.<x>.pulse_us / pulse_travel_deg), else SAFE_US_PER_DEG: the program can only
move a joint LESS than commanded, never more. Direction is not known (a servo's +pulse may be the joint's -), so the
automatic sweep stays inside +/- the smaller end of the range; the jog mode is manual.

Flight-controller projects get BRINGUP.md only (their firmware is Betaflight or the owner's own controller).
"""
from __future__ import annotations

import re
from pathlib import Path

from . import catalog

CENTRE_US = 1500                 # neutral pulse of every standard hobby servo (DSSERVO tables: "neutral 1500 usec")
SAFE_US_PER_DEG = 1000 / 180     # 1000-2000 us over 180 deg (TowerPro SG90 datasheet): the least us per degree a
                                 # standard positional servo uses, so an unknown servo moves at most as commanded
PULSE_LIMITS = (500, 2500)       # widest standard pulse range (DSSERVO DS3218/DS3225 tables)
SWEEP_STEP_DEG = 1.0
SWEEP_STEP_MS = 30

KINDS = {"boards.arduino_nano": "nano", "boards.pca9685_adafruit": "pca9685"}
PI_PREFIX = "boards.rpi_"
FC_PREFIX = ("drone.stacks.", "drone.fcs.")      # FC + ESC stacks, and stand-alone (wing) flight controllers
PI_HEADER = {"GPIO18": 12, "GPIO19": 35}   # pwm-2chan's default hardware-PWM pins -> physical header pin


def _kind(proj, iid) -> str | None:
    cat = proj.items[iid].spec.get("catalog", "") if iid in proj.items else ""
    if cat in KINDS:
        return KINDS[cat]
    if cat.startswith(PI_PREFIX):
        return "pi"
    if cat.startswith(FC_PREFIX):
        return "fc"
    return None


def us_per_deg(servo_cat: str) -> tuple[float, str]:
    """Least microseconds per degree the servo can have (so commanded degrees are an upper bound), and why."""
    e = catalog.get(servo_cat)
    p, t = e.get("pulse_us"), e.get("pulse_travel_deg")
    if p and t:
        travel = max(t) if isinstance(t, (list, tuple)) else t
        return (p[1] - p[0]) / travel, f"{p[0]}-{p[1]} us = {travel} deg ({e.get('source_pulse', 'catalog')})"
    return SAFE_US_PER_DEG, "no published pulse table: assumed 1000-2000 us = 180 deg, the least us/deg in use"


def servos(proj, asm) -> list[dict]:
    """One row per servo driven by a signal wire: controller, pin, driven joint and its range."""
    out = []
    for w in proj.data.get("wiring") or []:
        if w.get("kind") != "signal" or w.get("to") not in proj.items:
            continue
        sv = w["to"]
        cat = proj.items[sv].spec.get("catalog", "")
        if not cat.startswith("servos."):
            continue
        ctrl, kind = w["from"], _kind(proj, w["from"])
        if kind is None:
            continue
        if not w.get("pin"):
            raise ValueError(f"wiring '{w['id']}': a servo signal wire from {ctrl} needs `pin:` (e.g. D9, GPIO18, ch3, M4)")
        joint = next((e for e in asm.edges if e.parent == sv and e.kind == "revolute"), None)
        lo, hi = (joint.range if joint is not None else proj.items[sv].spec.get("range", (-45, 45)))
        k, why = us_per_deg(cat)
        out.append({"servo": sv, "model": cat.split(".", 1)[1], "controller": ctrl, "kind": kind, "pin": str(w["pin"]),
                    "joint": joint.name if joint is not None else sv, "lo": float(lo), "hi": float(hi),
                    "us_per_deg": round(k, 3), "us_why": why})
    return out


def host_of(proj, ctrl: str) -> str | None:
    """The board that talks to a PCA9685 over I2C (a signal wire from it to the driver)."""
    for w in proj.data.get("wiring") or []:
        if w.get("to") == ctrl and w.get("kind") == "signal" and _kind(proj, w.get("from")) == "nano":
            return w["from"]
    return None


def _band(s) -> float:
    return min(abs(s["lo"]), abs(s["hi"]))


def _lim(s) -> float:
    return max(abs(s["lo"]), abs(s["hi"]))


def _num(pin: str, prefix: str) -> int:
    m = re.fullmatch(prefix + r"(\d+)", pin.strip(), re.I)
    if not m:
        raise ValueError(f"pin '{pin}' is not {prefix}<number>")
    return int(m.group(1))


# ---------------------------------------------------------------- Arduino (Nano, direct or through a PCA9685)

def sketch(name: str, rows: list[dict], pca: bool) -> str:
    joints = ",\n".join(
        f'  {{"{r["joint"]} ({r["servo"]}, {r["model"]})", {_num(r["pin"], "ch" if pca else "D")}, {r["us_per_deg"]:.3f}f, '
        f'{_band(r):.1f}f, {_lim(r):.1f}f}}' for r in rows)
    why = "\n".join(f'//   {r["joint"]}: {r["us_why"]}; joint range {r["lo"]:g} to {r["hi"]:g} deg' for r in rows)
    if pca:
        hw = ("#include <Wire.h>\n#include <Adafruit_PWMServoDriver.h>   // Library Manager: \"Adafruit PWM Servo Driver Library\"\n"
              "Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();   // I2C address 0x40 (no address jumpers)\n\n"
              "void writeUs(int i, int us) { pwm.writeMicroseconds(J[i].out, us); }\n"
              "void off(int i) { pwm.setPWM(J[i].out, 0, 4096); }   // full off: no pulses, the servo goes limp\n")
        begin = "  pwm.begin();\n  pwm.setOscillatorFrequency(27000000);\n  pwm.setPWMFreq(50);\n"
    else:
        hw = ("#include <Servo.h>\nServo servo[N];\n\n"
              "void writeUs(int i, int us) { if (!servo[i].attached()) servo[i].attach(J[i].out); servo[i].writeMicroseconds(us); }\n"
              "void off(int i) { servo[i].detach(); }   // no pulses: the servo goes limp\n")
        begin = ""
    return f"""// {name}: bring-up and sweep test. Generated by `kerf build` (kerf/firmware.py) from project.yaml.
// Open the Serial Monitor at 115200 baud, line ending "Newline", and type a command:
//   c        centre every servo (1500 us). Do this BEFORE fitting any horn (ASSEMBLY.md Step 0b).
//   s        sweep test: each joint in turn, slowly, to +band, -band and back to centre
//   j<n>     select joint n for jogging (j0, j1, ...);  + / -  move it 1 deg;  ++ / --  5 deg
//   x        stop: no pulses, every servo goes limp
// Degrees are converted with the SMALLEST us/deg the servo's datasheet allows, so a joint moves at most as far as
// shown (often less). The sweep stays inside +/- the smaller end of each joint's range because which way a servo
// turns for "+" depends on how the horn went on. Jog to check the rest of the range by eye and stop before anything
// touches.
{why}

const int N = {len(rows)};
struct Joint {{ const char* name; int out; float usPerDeg; float band; float lim; }};
const Joint J[N] = {{
{joints}
}};
{hw}
float pos[N];
int sel = 0;

int toUs(int i, float deg) {{
  return constrain((int)({CENTRE_US} + deg * J[i].usPerDeg + 0.5), {PULSE_LIMITS[0]}, {PULSE_LIMITS[1]});
}}

void moveTo(int i, float deg) {{
  deg = constrain(deg, -J[i].lim, J[i].lim);
  int us = toUs(i, deg);
  writeUs(i, us);
  pos[i] = deg;
  Serial.print(J[i].name); Serial.print(": "); Serial.print(deg, 1); Serial.print(" deg = "); Serial.print(us); Serial.println(" us");
}}

void glide(int i, float to) {{
  float step = to > pos[i] ? {SWEEP_STEP_DEG:g} : -{SWEEP_STEP_DEG:g};
  while (fabs(to - pos[i]) > {SWEEP_STEP_DEG:g}) {{
    if (Serial.available() && Serial.peek() == 'x') return;
    float d = pos[i] + step;
    writeUs(i, toUs(i, d));
    pos[i] = d;
    delay({SWEEP_STEP_MS});
  }}
  moveTo(i, to);
}}

void limp() {{
  for (int i = 0; i < N; i++) off(i);
  Serial.println("stopped: servos limp");
}}

void setup() {{
  Serial.begin(115200);
{begin}  Serial.println("{name} bring-up: c = centre, s = sweep, j<n> = jog joint n, x = stop");
  for (int i = 0; i < N; i++) {{ Serial.print("  j"); Serial.print(i); Serial.print(" "); Serial.println(J[i].name); }}
}}

void loop() {{
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\\n');
  cmd.trim();
  if (cmd == "c") {{ for (int i = 0; i < N; i++) moveTo(i, 0); }}
  else if (cmd == "s") {{
    for (int i = 0; i < N; i++) {{ moveTo(i, 0); }}
    for (int i = 0; i < N; i++) {{
      Serial.print("sweep "); Serial.println(J[i].name);
      glide(i, J[i].band); glide(i, -J[i].band); glide(i, 0);
      if (Serial.available() && Serial.peek() == 'x') break;
    }}
  }}
  else if (cmd.startsWith("j")) {{ int n = cmd.substring(1).toInt(); if (n >= 0 && n < N) {{ sel = n; moveTo(sel, pos[sel]); }} }}
  else if (cmd == "+") moveTo(sel, pos[sel] + 1);
  else if (cmd == "-") moveTo(sel, pos[sel] - 1);
  else if (cmd == "++") moveTo(sel, pos[sel] + 5);
  else if (cmd == "--") moveTo(sel, pos[sel] - 5);
  else if (cmd == "x") limp();
}}
"""


# ---------------------------------------------------------------- Raspberry Pi (hardware PWM through sysfs)

def pi_script(name: str, rows: list[dict]) -> str:
    for r in rows:
        if r["pin"].upper() not in PI_HEADER:
            raise ValueError(f"{r['servo']}: Pi servo signals use hardware PWM on GPIO18 / GPIO19 (pwm-2chan), not {r['pin']}")
    joints = ",\n".join(
        f'    {{"name": "{r["joint"]} ({r["servo"]}, {r["model"]})", "gpio": {_num(r["pin"], "GPIO")}, '
        f'"us_per_deg": {r["us_per_deg"]}, "band": {_band(r):g}, "lim": {_lim(r):g}}}' for r in rows)
    why = "\n".join(f'#   {r["joint"]}: {r["us_why"]}; joint range {r["lo"]:g} to {r["hi"]:g} deg' for r in rows)
    return f'''#!/usr/bin/env python3
"""{name}: bring-up and sweep test. Generated by `kerf build` (kerf/firmware.py) from project.yaml.

Hardware PWM on GPIO18 (PWM0, header pin 12) and GPIO19 (PWM1, header pin 35): add the line
    dtoverlay=pwm-2chan
to /boot/firmware/config.txt (older Raspberry Pi OS: /boot/config.txt), reboot, then run
    sudo python3 bringup.py
Commands: c = centre every servo (1500 us; do this BEFORE fitting any horn, ASSEMBLY.md Step 0b),
          s = sweep test, j<n> = select joint n, + / - = 1 deg, ++ / -- = 5 deg, x = stop (servos limp), q = quit.
Degrees use the SMALLEST us/deg the servo's datasheet allows, so a joint moves at most as far as shown. The sweep stays
inside +/- the smaller end of each joint's range (which way "+" turns depends on how the horn went on); jog by eye to
check the rest and stop before anything touches.
"""
{why.replace("#   ", "# ")}
import os
import sys
import time

PWM_ROOT = os.environ.get("KERF_PWM_ROOT", "/sys/class/pwm")      # tests point this at a fake sysfs tree
CHANNEL = {{18: 0, 19: 1}}                                        # pwm-2chan defaults: PWM0 / PWM1 (Pi Zero 2 W .. Pi 4)
PERIOD_NS = 20_000_000                                            # 50 Hz
JOINTS = [
{joints}
]
pos = [0.0] * len(JOINTS)


def chip():
    for name in sorted(os.listdir(PWM_ROOT)):
        if name.startswith("pwmchip"):
            return os.path.join(PWM_ROOT, name)
    sys.exit("no PWM chip under " + PWM_ROOT + ": add dtoverlay=pwm-2chan to config.txt and reboot")


def put(path, value):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(str(value))


def channel(i):
    c = os.path.join(chip(), "pwm%d" % CHANNEL[JOINTS[i]["gpio"]])
    if not os.path.exists(c):
        put(os.path.join(chip(), "export"), CHANNEL[JOINTS[i]["gpio"]])
        time.sleep(0.2)
    return c


def write_us(i, us):
    c = channel(i)
    put(os.path.join(c, "period"), PERIOD_NS)
    put(os.path.join(c, "duty_cycle"), int(us * 1000))
    put(os.path.join(c, "enable"), 1)


def to_us(i, deg):
    return max({PULSE_LIMITS[0]}, min({PULSE_LIMITS[1]}, round({CENTRE_US} + deg * JOINTS[i]["us_per_deg"])))


def move(i, deg, quiet=False):
    j = JOINTS[i]
    deg = max(-j["lim"], min(j["lim"], deg))
    write_us(i, to_us(i, deg))
    pos[i] = deg
    if not quiet:
        print("%s: %.1f deg = %d us" % (j["name"], deg, to_us(i, deg)))


def glide(i, to):
    step = {SWEEP_STEP_DEG:g} if to > pos[i] else -{SWEEP_STEP_DEG:g}
    while abs(to - pos[i]) > {SWEEP_STEP_DEG:g}:
        move(i, pos[i] + step, quiet=True)
        time.sleep({SWEEP_STEP_MS / 1000:g})
    move(i, to)


def limp():
    for i in range(len(JOINTS)):
        put(os.path.join(channel(i), "enable"), 0)
    print("stopped: servos limp")


def main(lines=None):
    sel = 0
    print("{name} bring-up: c = centre, s = sweep, j<n> = jog joint n, x = stop, q = quit")
    for n, j in enumerate(JOINTS):
        print("  j%d %s" % (n, j["name"]))
    src = iter(lines) if lines is not None else iter(lambda: input("> "), None)
    for cmd in src:
        cmd = cmd.strip()
        if cmd == "q":
            break
        if cmd == "c":
            for i in range(len(JOINTS)):
                move(i, 0)
        elif cmd == "s":
            for i in range(len(JOINTS)):
                move(i, 0)
            for i, j in enumerate(JOINTS):
                print("sweep " + j["name"])
                glide(i, j["band"])
                glide(i, -j["band"])
                glide(i, 0)
        elif cmd.startswith("j") and cmd[1:].isdigit() and int(cmd[1:]) < len(JOINTS):
            sel = int(cmd[1:])
            move(sel, pos[sel])
        elif cmd in ("+", "-", "++", "--"):
            move(sel, pos[sel] + {{"+": 1, "-": -1, "++": 5, "--": -5}}[cmd])
        elif cmd == "x":
            limp()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        limp()
'''


# ---------------------------------------------------------------- files + the text ASSEMBLY.md uses

def _pin_words(r) -> str:
    if r["kind"] == "pi":
        return f"{r['pin']} (header pin {PI_HEADER[r['pin'].upper()]})" if r["pin"].upper() in PI_HEADER else r["pin"]
    if r["kind"] == "pca9685":
        return f"PCA9685 channel {_num(r['pin'], 'ch')}"
    if r["kind"] == "fc":
        return f"flight-controller output {r['pin']}"
    return f"Nano pin {r['pin']}"


def write(proj, asm, outdir: Path) -> dict | None:
    """out/firmware/: the program + BRINGUP.md. Returns what ASSEMBLY.md needs, or None when there is no controller."""
    rows = servos(proj, asm)
    fc = [i for i, it in proj.items.items() if str(it.spec.get("catalog", "")).startswith(FC_PREFIX)]
    if not rows and not fc:
        return None
    fw = outdir / "firmware"
    fw.mkdir(exist_ok=True)
    name = proj.data.get("name", proj.name)
    kinds = {r["kind"] for r in rows}
    prog, run = None, None
    if len(kinds - {"fc"}) and not (kinds <= {"pi"} or kinds <= {"nano", "pca9685"}):
        raise ValueError(f"servos on {sorted(kinds)}: one bring-up program per project (a Pi, or a Nano with or without a PCA9685)")
    if rows and kinds == {"pi"}:
        prog = "firmware/bringup.py"
        (fw / "bringup.py").write_text(pi_script(name, rows), encoding="utf-8")
        run = ("copy `firmware/bringup.py` to the Pi, add `dtoverlay=pwm-2chan` to /boot/firmware/config.txt, reboot, "
               "run `sudo python3 bringup.py`")
    elif rows and kinds <= {"nano", "pca9685"}:
        pca = "pca9685" in kinds
        sk = f"{re.sub(r'[^A-Za-z0-9_]', '_', proj.name)}_bringup"
        (fw / sk).mkdir(exist_ok=True)
        (fw / sk / f"{sk}.ino").write_text(sketch(name, rows, pca), encoding="utf-8")
        prog = f"firmware/{sk}/{sk}.ino"
        run = (f"open `{prog}` in the Arduino IDE" + (" (install \"Adafruit PWM Servo Driver Library\" from the Library "
               "Manager first)" if pca else "") + ", board Arduino Nano, upload, open the Serial Monitor at 115200 baud")
    lines = [f"# Bring-up — {name}", "",
             "Generated by `kerf build` (kerf/firmware.py). Props off, hands and loose wires clear of moving parts.", ""]
    if rows:
        lines += ["| Joint | Servo | Controller output | Joint range | Automatic sweep | us per deg used |", "|---|---|---|---|---|---|"]
        lines += [f"| {r['joint']} | {r['servo']} ({r['model']}) | {_pin_words(r)} | {r['lo']:g} to {r['hi']:g} deg | "
              + ("- (no program)" if r["kind"] == "fc" else f"+/- {_band(r):g} deg" if _band(r) > 0 else "none (range starts at 0: jog it)")
              + f" | {'-' if r['kind'] == 'fc' else format(r['us_per_deg'], 'g')} |" for r in rows]
        why = dict.fromkeys((r["model"], r["us_why"]) for r in rows if r["kind"] != "fc")
        if why:
            lines += ["", "Where the us-per-degree numbers come from:", ""] + [f"- {m}: {w}" for m, w in why]
        lines.append("")
    if prog:
        lines += ["## Run it", "", f"1. {run[0].upper() + run[1:]}.", "2. `c` centres every servo (1500 us): do this before any horn goes on.",
                  "3. After assembly, `s` sweeps each joint slowly through its test band; `j<n>` and `+` / `-` jog one "
                  "joint by hand to check the rest of its range. `x` stops (servos go limp).", "",
                  "Degrees are converted with the smallest microseconds-per-degree the servo's datasheet allows, so a joint "
                  "moves at most as far as shown. Which way \"+\" turns depends on how the horn went on, so the automatic "
                  "sweep stays inside +/- the smaller end of each range.", ""]
    if fc:
        lines += ["## Flight controller: first power-up", "",
                  "The flight controller runs its own firmware (Betaflight or your own controller), so there is no generated "
                  "program. With the props OFF:", "",
                  "1. Plug the battery in with the props off and check nothing gets hot; unplug at once if anything smokes.",
                  "2. In the configurator, check the receiver channels move with the sticks before anything else.",
                  "3. Spin each motor briefly from the configurator's motor test and check its order and direction against "
                  "the frame's motor layout; fix direction in the ESC settings, not by swapping props.", ""]
        if any(r["kind"] == "fc" for r in rows):
            lines += [f"Servos on the flight controller: centre them at {CENTRE_US} us (a servo tester, or the flight "
                      "controller's servo output) before their horns go on; then check each one moves its joint the right "
                      "way and stops short of the ends before the first flight.", ""]
    (fw / "BRINGUP.md").write_text("\n".join(lines), encoding="utf-8")
    return {"program": prog, "run": run, "rows": rows, "kinds": sorted(kinds)}


def centre_step(info: dict) -> list[str]:
    """ASSEMBLY.md Step 0b: centre every servo on the bench before any horn is fitted."""
    rows = info["rows"]
    L = ["## Step 0b — centre the servos (before any horn goes on)", ""]
    if info["program"]:
        L += [f"- Bring-up program: `{info['program']}` (details: `firmware/BRINGUP.md`).",
              f"  - To run it: {info['run']}."]
        L.append("- Connect each servo to the controller and the servo supply on the bench, just for this step:")
        for r in rows:
            L.append(f"  - **{r['servo']}**: signal (orange/yellow) to {_pin_words(r)}; red to the servo supply +, brown to "
                     "supply minus; controller GND to supply minus too (common ground).")
        if "pi" in info["kinds"]:
            L.append("  - A Raspberry Pi Zero comes without a header: solder the signal wires to the pads now (they are the "
                     "same wires the electrical steps at the end use), or fit a 2x20 header.")
        L.append("- Type `c`: every servo goes to its centre (1500 us). Unplug it and do not turn its shaft by hand "
                 "until its horn is on.")
    else:
        L.append(f"- Centre each servo at {CENTRE_US} us with a servo tester or the flight controller before its horn goes on "
                 "(`firmware/BRINGUP.md`). Do not turn the shafts by hand afterwards.")
    L.append("")
    return L
