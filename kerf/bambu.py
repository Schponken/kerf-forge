"""Bambu A2L handoff: `kerf print <project>` orients every printed part, packs plates, slices them with Bambu Studio
(or OrcaSlicer) into .gcode.3mf and sends a plate to the printer over its LAN Developer Mode, then polls status.

Orientation: the 24 axis-aligned rotations are scored on one tessellation per part: must fit the bed; a declared
`load_axis` must stay within 30 deg of the layer plane (checks.LAYER_WARN_NZ2); then least down-facing area steeper
than 45 deg (support), then lowest height. The yaml `print_rot` is the designer's choice and is kept unless another
rotation needs clearly less support (>= max(5 mm2, 10 %) less); every change is reported.

Slicing (Bambu Studio CLI, github.com/bambulab/BambuStudio/wiki/Command-Line-Usage):
  <slicer> --arrange 0 --load-settings "machine.json;process.json" --load-filaments "filament.json" --slice 0
           --debug 2 --export-3mf plate_N.gcode.3mf plate_N.3mf
The setting files must be FULL configs (the CLI page says partial profiles from resources/profiles don't work);
export them once from Bambu Studio with the A2L + PETG presets selected.

LAN send (Developer Mode: since 2025 firmware rejects unsigned commands in normal LAN mode, wiki.bambulab.com
third-party-integration; protocol per github.com/Doridian/OpenBambuAPI mqtt.md / ftp.md):
  FTPS implicit TLS, port 990, user bblp, password = LAN access code: upload the .gcode.3mf to the SD card root.
  MQTT TLS, port 8883, user bblp, same password: publish `print.project_file` on device/<serial>/request (url
  ftp:///<file>, param Metadata/plate_<n>.gcode), then `pushing.pushall` and read device/<serial>/report
  (gcode_state, mc_percent, mc_remaining_time, print_error).
The printer's certificate is self-signed per device, so TLS is encrypted but not verified (LAN only).

Config lives OUTSIDE the repo: ~/.kerf/bambu.json (or $KERF_BAMBU_CONFIG):
  {"printer": {"host": "192.168.1.50", "serial": "...", "access_code": "12345678"},
   "slicer": {"bin": "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio",
              "machine": ".../machine.json", "process": ".../process.json", "filaments": {"PETG": ".../petg.json"}}}
Fallback without a slicer config or LAN access: the plate 3MFs are written and opened in Bambu Studio / Bambu
Connect (`bambu-connect://import-file?path=...&name=...&version=1.0.0`) for a one-click slice and send.
"""
from __future__ import annotations

import itertools
import json
import os
import shutil
import ssl
import time
import urllib.parse
from pathlib import Path

import numpy as np
from build123d import Rot

from . import checks, geom

MIN_GAIN_MM2, MIN_GAIN_FRAC = 5.0, 0.10
SLICER_PATHS = ["/Applications/BambuStudio.app/Contents/MacOS/BambuStudio",
                "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"]
SLICER_NAMES = ["bambu-studio", "BambuStudio", "orca-slicer", "OrcaSlicer"]
MQTT_PORT, FTPS_PORT, USER = 8883, 990, "bblp"
STARTED = {"PREPARE", "RUNNING", "SLICING"}
DONE = {"FINISH", "FAILED"}


# ---------------------------------------------------------------- orientation

def rotations() -> list[tuple]:
    """The 24 distinct axis-aligned orientations as (rx, ry, rz) degrees."""
    out, seen = [], set()
    for r in itertools.product((0, 90, 180, 270), repeat=3):
        M = _R(r)
        key = tuple(np.round(M, 6).ravel())
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _R(rot) -> np.ndarray:
    t = Rot(*rot).wrapped.Transformation()
    return np.array([[t.Value(i + 1, j + 1) for j in range(3)] for i in range(3)])


def score(V, F, rot, load_axes, bed) -> dict:
    R = _R(rot)
    v = V @ R.T
    v = v - [0, 0, v[:, 2].min()]
    oh_area, oh_frac, _ = geom.overhang(v, F, 45.0, bed_z=0.0)
    size = v.max(axis=0) - v.min(axis=0)
    X, Y, Z = bed
    fits = sorted(size[:2], reverse=True)[0] <= max(X, Y) and sorted(size[:2])[0] <= min(X, Y) and size[2] <= Z
    nz2 = max([float((R @ a)[2]) ** 2 for a in load_axes] or [0.0])
    return {"rot": list(rot), "overhang_mm2": round(float(oh_area), 1), "overhang_pct": round(100 * float(oh_frac), 2),
            "height_mm": round(float(size[2]), 1), "fits": bool(fits), "load_nz2": round(nz2, 3),
            "load_ok": nz2 <= checks.LAYER_WARN_NZ2}


def orient(item, printer: str) -> dict:
    """Best print rotation for one printed part (see module docstring)."""
    from build123d import Location
    V, F = geom.mesh(item.shape.located(Location()), tol=0.1, ang=0.3)
    la = item.spec.get("load_axis")
    axes = [] if la is None else ([la] if isinstance(la, str) or (isinstance(la, (list, tuple)) and la and isinstance(la[0], (int, float))) else la)
    vecs = [np.asarray(checks._axis_vec(a), float) for a in axes]
    vecs = [v / np.linalg.norm(v) for v in vecs]
    bed = checks.PRINTERS[printer]
    yaml_rot = tuple(item.spec.get("print_rot", [0, 0, 0]))
    cur = score(V, F, yaml_rot, vecs, bed)
    cands = [score(V, F, r, vecs, bed) for r in rotations()]
    ok = [c for c in cands if c["fits"] and c["load_ok"]] or [c for c in cands if c["fits"]]
    best = min(ok, key=lambda c: (c["overhang_mm2"], c["height_mm"])) if ok else cur
    gain = cur["overhang_mm2"] - best["overhang_mm2"]
    better = (not cur["fits"] or (vecs and not cur["load_ok"] and best["load_ok"])
              or gain >= max(MIN_GAIN_MM2, MIN_GAIN_FRAC * cur["overhang_mm2"]))
    pick = best if better else cur
    why = ("keeps the designed print_rot" if pick is cur else
           f"needs {gain:.0f} mm2 less support ({cur['overhang_pct']} % -> {best['overhang_pct']} % of the surface)"
           if cur["fits"] and (not vecs or cur["load_ok"]) else "the designed print_rot does not fit / loads across layers")
    return {"part": item.id, "rot": pick["rot"], "yaml_rot": list(yaml_rot), "changed": pick is not cur,
            "why": why, "chosen": pick, "designed": cur}


def write_plates(proj, rots: dict, outdir: Path, printer: str) -> list:
    """Plate 3MFs (export.plates packing) with the chosen rotations."""
    from . import export
    saved = {i: proj.items[i].spec.get("print_rot") for i in rots}
    try:
        for i, r in rots.items():
            proj.items[i].spec["print_rot"] = list(r)
        return export.plates(proj, outdir, printer)
    finally:
        for i, r in saved.items():
            if r is None:
                proj.items[i].spec.pop("print_rot", None)
            else:
                proj.items[i].spec["print_rot"] = r


# ---------------------------------------------------------------- slicing

def load_config(path: str | None = None) -> dict:
    p = Path(path or os.environ.get("KERF_BAMBU_CONFIG") or Path.home() / ".kerf" / "bambu.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def find_slicer(cfg: dict) -> str | None:
    b = (cfg.get("slicer") or {}).get("bin") or os.environ.get("KERF_SLICER")
    if b and Path(b).exists():
        return b
    for p in SLICER_PATHS:
        if Path(p).exists():
            return p
    for n in SLICER_NAMES:
        w = shutil.which(n)
        if w:
            return w
    return None


def slice_cmd(binary: str, plate: Path, out: Path, sl: dict, materials: list[str]) -> list[str]:
    """Bambu Studio CLI line for one plate. sl = cfg['slicer'] with machine/process/filaments paths."""
    missing = [k for k in ("machine", "process") if not sl.get(k)]
    fil = [(sl.get("filaments") or {}).get(m) for m in materials]
    if missing or not all(fil):
        need = missing + [f"filaments.{m}" for m, f in zip(materials, fil) if not f]
        raise ValueError(f"slicer config needs full exported settings: {', '.join(need)} (see kerf/bambu.py)")
    return [binary, "--arrange", "0", "--load-settings", f"{sl['machine']};{sl['process']}",
            "--load-filaments", ";".join(dict.fromkeys(fil)), "--slice", "0", "--debug", "2",
            "--export-3mf", str(out), str(plate)]


def import_url(path: Path, name: str) -> str:
    """Bambu Connect one-click import (wiki.bambulab.com third-party-integration)."""
    q = urllib.parse.quote
    return f"bambu-connect://import-file?path={q(str(path), safe='')}&name={q(name, safe='')}&version=1.0.0"


# ---------------------------------------------------------------- LAN send

def project_file_payload(remote_name: str, plate: int = 1, seq: int = 1, use_ams: bool = False) -> dict:
    """print.project_file as documented in OpenBambuAPI mqtt.md (local print: ids "0", bed_type auto)."""
    return {"print": {"sequence_id": str(seq), "command": "project_file", "param": f"Metadata/plate_{plate}.gcode",
                      "project_id": "0", "profile_id": "0", "task_id": "0", "subtask_id": "0",
                      "subtask_name": Path(remote_name).name.split(".")[0], "url": f"ftp:///{remote_name}", "md5": "",
                      "timelapse": False, "bed_type": "auto", "bed_levelling": True, "flow_cali": True,
                      "vibration_cali": True, "layer_inspect": False, "ams_mapping": "", "use_ams": use_ams}}


def pushall_payload(seq: int = 1) -> dict:
    return {"pushing": {"sequence_id": str(seq), "command": "pushall", "version": 1, "push_target": 1}}


def _tls() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE        # per-printer self-signed certificate; LAN only
    return ctx


class FTPS:
    """Implicit-TLS FTPS (port 990) upload to the printer's SD card root."""

    def __init__(self, host, access_code, port=FTPS_PORT):
        self.host, self.code, self.port = host, access_code, port

    def upload(self, local: Path, remote: str):
        import ftplib

        class Implicit(ftplib.FTP_TLS):
            def __init__(s, *a, **k):
                super().__init__(*a, **k)
                s._sock = None

            @property
            def sock(s):
                return s._sock

            @sock.setter
            def sock(s, value):
                if value is not None and not isinstance(value, ssl.SSLSocket):
                    value = s.context.wrap_socket(value)
                s._sock = value

            def ntransfercmd(s, cmd, rest=None):   # data channel reuses the control channel's TLS session
                conn, size = ftplib.FTP.ntransfercmd(s, cmd, rest)
                conn = s.context.wrap_socket(conn, server_hostname=s.host, session=s.sock.session)
                return conn, size

        f = Implicit(context=_tls())
        f.connect(self.host, self.port, timeout=30)
        f.login(USER, self.code)
        f.prot_p()
        with open(local, "rb") as fh:
            f.storbinary(f"STOR {remote}", fh)
        f.quit()


class MQTT:
    """TLS MQTT link to one printer: publish requests, collect reports."""

    def __init__(self, host, serial, access_code, port=MQTT_PORT):
        import paho.mqtt.client as mqtt
        self.serial, self.reports = serial, []
        self.c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"kerf-{os.getpid()}")
        self.c.username_pw_set(USER, access_code)
        self.c.tls_set_context(_tls())
        self.c.on_message = lambda c, u, m: self.reports.append(json.loads(m.payload or b"{}"))
        self.c.connect(host, port, keepalive=30)
        self.c.subscribe(f"device/{serial}/report")
        self.c.loop_start()

    def publish(self, payload: dict):
        self.c.publish(f"device/{self.serial}/request", json.dumps(payload)).wait_for_publish(10)

    def close(self):
        self.c.loop_stop()
        self.c.disconnect()


def state(reports: list) -> dict:
    """Latest print status merged from report messages (P-series send only changed fields)."""
    s = {}
    for r in reports:
        s.update({k: v for k, v in (r.get("print") or {}).items()
                  if k in ("gcode_state", "mc_percent", "mc_remaining_time", "print_error", "layer_num", "total_layer_num")})
    return s


def send(cfg: dict, sliced: Path, plate: int = 1, ftps=None, mqtt=None, wait_s: float = 60, poll_s: float = 2,
         sleep=time.sleep) -> dict:
    """Upload a sliced .gcode.3mf and start it; poll until the printer reports it started (or failed)."""
    p = cfg.get("printer") or {}
    missing = [k for k in ("host", "serial", "access_code") if not p.get(k)]
    if missing:
        raise ValueError(f"printer config missing {missing} (~/.kerf/bambu.json; enable LAN Developer Mode on the printer)")
    ftps = ftps or FTPS(p["host"], p["access_code"])
    ftps.upload(sliced, sliced.name)
    link = mqtt or MQTT(p["host"], p["serial"], p["access_code"])
    try:
        link.publish(project_file_payload(sliced.name, plate, seq=1))
        t, seq, st = 0.0, 2, {}
        while t <= wait_s:
            link.publish(pushall_payload(seq))
            seq += 1
            sleep(poll_s)
            t += poll_s
            st = state(link.reports)
            if st.get("gcode_state") in STARTED | DONE or st.get("print_error"):
                break
        return {"uploaded": sliced.name, "status": st,
                "started": st.get("gcode_state") in STARTED and not st.get("print_error")}
    finally:
        if mqtt is None:
            link.close()


def mask(cfg: dict) -> dict:
    c = json.loads(json.dumps(cfg))
    if (c.get("printer") or {}).get("access_code"):
        c["printer"]["access_code"] = "********"
    return c


# ---------------------------------------------------------------- the command

def run(name: str, *, dry_run=False, send_plate: int | None = None, open_ui=False, cfg: dict | None = None,
        say=print, runner=None) -> dict:
    """kerf print: orient -> plates -> slice -> (send). dry_run prints commands/payloads without running them."""
    import subprocess
    from . import project as P
    cfg = load_config() if cfg is None else cfg
    proj = P.build(P.load(name))
    bad = [f"{i}: {it.error}" for i, it in proj.printed.items() if it.error]
    if bad:
        raise ValueError("parts failed to build: " + "; ".join(bad))
    printer = proj.data.get("printer", "Bambu Lab A2L")
    out = proj.out("print")
    out.mkdir(parents=True, exist_ok=True)
    orients = {i: orient(it, printer) for i, it in proj.printed.items()}
    for o in orients.values():
        say(f"orient {o['part']:14s} {o['rot']}  overhang {o['chosen']['overhang_pct']} %  h {o['chosen']['height_mm']} mm"
            + (f"  (CHANGED from {o['yaml_rot']}: {o['why']})" if o["changed"] else ""))
    plates = write_plates(proj, {i: o["rot"] for i, o in orients.items()}, out, printer)
    res = {"orient": orients, "plates": plates, "sliced": [], "fallback": None, "sent": None}
    binary = find_slicer(cfg)
    sl = cfg.get("slicer") or {}
    mats = sorted({it.spec.get("material", "PETG") for it in proj.printed.values()})
    try:
        cmds = [slice_cmd(binary, out / p["file"], out / p["file"].replace(".3mf", ".gcode.3mf"), sl, mats)
                for p in plates] if binary else None
    except ValueError as e:
        say(f"slicer: {e}")
        cmds = None
    if cmds is None:
        urls = [import_url(out / p["file"], f"{proj.dir.name} {p['file']}") for p in plates]
        res["fallback"] = {"plates": [str(out / p["file"]) for p in plates], "bambu_connect": urls,
                           "why": "no slicer found" if not binary else "slicer settings not configured"}
        say(f"fallback: open {', '.join(p['file'] for p in plates)} in Bambu Studio (or Bambu Connect) to slice and send")
        if open_ui and not dry_run:
            (runner or subprocess.run)(["open", "-a", "Bambu Studio", *res["fallback"]["plates"]], check=False)
        return res
    for c in cmds:
        say(("would run: " if dry_run else "slicing: ") + " ".join(f'"{x}"' if " " in x or ";" in x else x for x in c))
        if not dry_run:
            r = (runner or subprocess.run)(c, capture_output=True, text=True, timeout=900)
            if getattr(r, "returncode", 0) != 0 or not Path(c[-2]).exists():
                raise RuntimeError(f"slicer failed on {c[-1]}: {getattr(r, 'stderr', '')[-600:]}")
        res["sliced"].append(c[-2])
    if send_plate is not None:
        target = Path(res["sliced"][send_plate - 1])
        if dry_run:
            say(f"would upload {target.name} over FTPS {(cfg.get('printer') or {}).get('host', '<host>')}:{FTPS_PORT} and publish "
                f"{json.dumps(project_file_payload(target.name))} on device/<serial>/request")
        else:
            res["sent"] = send(cfg, target)
            say(f"sent {target.name}: {res['sent']['status']}")
    return res
