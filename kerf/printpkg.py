"""Print package: per plate grams and print time, and the slicer settings each part needs, in out/plates/PRINT_SETTINGS.md
and in the plate 3MFs' per-object settings.

Settings come from Bambu Studio's own profiles (bambulab/BambuStudio, resources/profiles/BBL, read 2026-11-01):
filament temperatures and max volumetric speed from the filament profiles, layer height / support type / brim width
from fdm_process_common.json. Print time: when `kerf print` is set up to slice (kerf/bambu.py: slicer binary plus the
full exported machine / process / filament settings in ~/.kerf/bambu.json) each plate is sliced with that same
command line and the slicer's own prediction and weight are read back from the sliced 3MF (Metadata/slice_info.config). Without a slicer the time is a documented lower bound: the plate's plastic volume
extruded at the filament's max volumetric speed (no slicer prints faster), so the real print is longer.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

FIL_SRC = "https://github.com/bambulab/BambuStudio/tree/master/resources/profiles/BBL/filament"
PROC_SRC = "https://github.com/bambulab/BambuStudio/blob/master/resources/profiles/BBL/process/fdm_process_common.json"

# material -> Bambu filament profile values (the @base profile and what it inherits)
PROFILES = {
    "PETG": {"profile": "Bambu PETG Basic", "nozzle_c": 255, "nozzle_range": (230, 270), "bed_c": 70,
             "plates": "Textured PEI, Engineering or High Temp plate at 70 C (not the Cool plate)", "max_flow": 8.0,
             "fan_pct": (10, 40)},
    "CF-PETG": {"profile": "Bambu PETG-CF", "nozzle_c": 255, "nozzle_range": (240, 270), "bed_c": 70,
                "plates": "Textured PEI, Engineering or High Temp plate at 70 C (not the Cool plate)", "max_flow": 14.0,
                "fan_pct": (0, 30), "note": "abrasive: hardened steel nozzle"},
    "PLA": {"profile": "Bambu PLA Basic", "nozzle_c": 220, "nozzle_range": (190, 240), "bed_c": 55,
            "plates": "Textured PEI or High Temp plate at 55 C (Cool plate 35 C)", "max_flow": 21.0, "fan_pct": (100, 100)},
    "TPU": {"profile": "Bambu TPU 95A", "nozzle_c": 230, "nozzle_range": (200, 250), "bed_c": 35,
            "plates": "Textured PEI at 35 C", "max_flow": 15.0, "fan_pct": (100, 100),
            "note": "flexible: print slowly; the base profile's 15 mm3/s is a ceiling, printer profiles set less"},
}
LAYER_MM, FIRST_LAYER_MM, SUPPORT_TYPE, BRIM_MM = 0.2, 0.2, "tree(auto)", 5     # fdm_process_common.json
SUPPORT_ON = ("needed", "on", True)   # a part's `supports:` that turns slicer supports on
SUPPORT_AUTO_PCT = 5.0         # Kerf's rule: over 5 % of the surface steeper than 45 deg is more than bridges and hole tops
BRIM_SLENDER = 3.0             # height over the smaller footprint side above which a part gets a brim (Kerf's rule)

# Z is up in every part's design frame, so bottom/top are safe words; which side is a part's "front" differs between
# projects (servo_link's bracket calls its -Y face the back), so X / Y faces are named by axis only
FACES = {(0, 0, -1): "bottom (-Z) face", (0, 0, 1): "top (+Z) face", (0, -1, 0): "-Y face",
         (0, 1, 0): "+Y face", (-1, 0, 0): "-X face", (1, 0, 0): "+X face"}


def profile(material: str) -> dict:
    return PROFILES.get(str(material).upper(), PROFILES["PETG"]) | {"material": material}


def orientation_words(print_rot) -> str:
    """Which face of the part (its own design frame) sits on the bed, from print_rot - rotated with the same
    build123d Rot that kerf/checks.oriented uses, so the words always match the plate."""
    from build123d import Location, Rot
    R = Rot(*[float(v) for v in (print_rot or [0, 0, 0])])
    best = None
    for axis, words in FACES.items():
        w = (R * Location(axis)).position                  # where this part-frame direction points after rotating
        down = -float(w.Z)
        if best is None or down > best[0]:
            best = (down, words)
    return "on its " + best[1] + ("" if best[0] > 0.995 else " (tilted)")


def part_settings(rep_part: dict, spec: dict, supports: str = "allowed") -> dict:
    size = rep_part.get("size_mm") or [0, 0, 0]
    oh = float(rep_part.get("overhang_pct") or 0)
    # Kerf's overhang figure counts every face steeper than 45 deg, bridges and hole tops included, which print fine
    # without supports; supports go on only where the design says so (a part's `supports: needed`)
    sup = spec.get("supports") in SUPPORT_ON or (spec.get("supports", supports) != "avoid" and oh > SUPPORT_AUTO_PCT)
    slender = size[2] / max(1e-6, min(size[0], size[1])) if size and min(size[0], size[1]) > 0 else 0
    return {"layer_mm": LAYER_MM, "supports": sup, "support_type": SUPPORT_TYPE if sup else None,
            "brim": "outer_only" if slender > BRIM_SLENDER else "auto_brim", "brim_mm": BRIM_MM if slender > BRIM_SLENDER else None,
            "overhang_pct": oh, "slender": round(slender, 2)}


def slicer() -> tuple[str, dict] | None:
    """The slicer command line and its settings, when `kerf print` is set up for it (kerf/bambu.py: ~/.kerf/bambu.json
    names the Bambu Studio / OrcaSlicer binary and the FULL machine / process / filament settings exported from it;
    the CLI does not slice with partial profiles)."""
    from . import bambu
    cfg = bambu.load_config()
    exe = bambu.find_slicer(cfg)
    sl = cfg.get("slicer") or {}
    if not exe or not sl.get("machine") or not sl.get("process") or not sl.get("filaments"):
        return None
    return exe, sl


def read_slice_info(sliced_3mf: Path) -> dict | None:
    """Prediction (s) and weight (g) the slicer wrote into a sliced 3MF (Metadata/slice_info.config, one <plate>)."""
    try:
        with zipfile.ZipFile(sliced_3mf) as z:
            txt = z.read("Metadata/slice_info.config").decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return None
    pred = re.search(r'key="prediction"\s+value="([\d.]+)"', txt)
    wt = re.search(r'key="weight"\s+value="([\d.]+)"', txt)
    if not pred:
        return None
    return {"seconds": float(pred.group(1)), "grams": float(wt.group(1)) if wt else None}


def slice_plate(sl: tuple[str, dict], plate: Path, materials: list[str], timeout: int = 900) -> dict | None:
    """Slice one plate with the same command line `kerf print` uses; None when it cannot (the estimate is used)."""
    from . import bambu
    exe, settings = sl
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "sliced.gcode.3mf"
        try:
            cmd = bambu.slice_cmd(exe, plate, out, settings, materials)
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except Exception:  # noqa: BLE001 - a missing filament setting or a slicer crash: fall back to the estimate
            return None
        if r.returncode != 0 or not out.exists():
            return None
        return read_slice_info(out)


def plate_numbers(plate: dict, proj, rep: dict) -> dict:
    """Grams (the build's mass estimate, at its infill and walls) and the extrusion-time lower bound of one plate."""
    from .checks import FALLBACK_DENSITY
    from . import catalog
    grams, seconds, mats = 0.0, 0.0, set()
    for name in plate["parts"]:
        iid = name.split(" #")[0]
        it, rp = proj.items[iid], (rep.get("parts") or {}).get(iid) or {}
        mat = it.spec.get("material", "PETG")
        mats.add(mat)
        g = float(rp.get("mass_est_g") or 0)
        try:
            dens = float(catalog.get(f"materials.{mat}")["density"])
        except Exception:  # noqa: BLE001
            dens = FALLBACK_DENSITY.get(mat, 1.25)
        grams += g
        seconds += g / dens * 1000.0 / profile(mat)["max_flow"]      # g -> mm3 at the profile's max mm3/s
    return {"grams": round(grams, 1), "min_seconds": round(seconds), "materials": sorted(mats)}


def write(proj, rep: dict, plates: list, outdir: Path, use_slicer: bool = True) -> dict:
    """Rewrite out/plates/PRINT_SETTINGS.md with per plate grams + time and per part settings; put layer height,
    supports and brim into each plate 3MF's per-object settings. Returns {plates: [...], slicer: path|None}."""
    from .export import part_print_settings, _write_part_settings
    supports = proj.data.get("supports", "allowed")
    sl = slicer() if use_slicer else None
    rows = []
    for pl in plates:
        nums = plate_numbers(pl, proj, rep)
        sliced = slice_plate(sl, outdir / pl["file"], nums["materials"]) if sl else None
        rows.append({**pl, **nums, "sliced": sliced})
        specs = {}
        for name in pl["parts"]:
            iid, n = name.split(" #")
            st = part_settings((rep.get("parts") or {}).get(iid) or {}, proj.items[iid].spec, supports)
            specs[f"{iid}_{n}"] = {**proj.items[iid].spec, "_print": st}
        _write_part_settings(outdir / pl["file"], specs)
    L = [f"# Print package — {proj.data.get('name', proj.name)}", "",
         f"Printer: {rep.get('printer') or 'Bambu Lab A2L'}, 0.4 mm nozzle. Settings from Bambu Studio's own profiles "
         f"([filament]({FIL_SRC}), [process]({PROC_SRC})); the plate files already carry each part's layer height, "
         "supports, brim, infill and wall loops (Bambu Studio / OrcaSlicer per-object settings).", "",
         "## Plates", "", "| Plate | Parts | Filament | Print time |", "|---|---|---|---|"]
    for r in rows:
        if r["sliced"]:
            t = f"{r['sliced']['seconds'] / 3600:.1f} h (sliced)"
            g = f"{r['sliced']['grams']:.0f} g (sliced)" if r["sliced"].get("grams") else f"~{r['grams']:.0f} g"
        else:
            t = f"at least {max(1, round(r['min_seconds'] / 60))} min (see below)"
            g = f"~{r['grams']:.0f} g"
        L.append(f"| {r['file']} | {', '.join(r['parts'])} | {g} {'/'.join(r['materials'])} | {t} |")
    total_g = sum(r["grams"] for r in rows)
    L += ["", f"Filament for everything: about {total_g:.0f} g (the build's mass estimate at each part's infill and walls)."]
    if not any(r["sliced"] for r in rows):
        L += ["", "Print time without a slicer: the lower bound is the plastic volume pushed at the filament's maximum "
              "volumetric speed (Bambu profile value), which no slicer exceeds; walls, travel, the first layer and "
              "cooling make the real print several times longer. Open the plate in Bambu Studio and Slice for the "
              "real time (Kerf slices automatically once `kerf print` is set up with your exported Bambu Studio settings, see kerf/bambu.py)."]
    L += ["", "## Material settings", "", "| Material | Bambu profile | Nozzle | Bed / plate | Part fan | Note |", "|---|---|---|---|---|---|"]
    for mat in sorted({it.spec.get("material", "PETG") for it in proj.printed.values()}):
        p = profile(mat)
        L.append(f"| {mat} | {p['profile']} | {p['nozzle_c']} C (range {p['nozzle_range'][0]}-{p['nozzle_range'][1]}) | "
                 f"{p['plates']} | {p['fan_pct'][0]}-{p['fan_pct'][1]} % | {p.get('note', '')} |")
    L += ["", "## Per part", "", "| Part | Material | Orientation | Layer | Supports | Brim | Infill | Wall loops |",
          "|---|---|---|---|---|---|---|---|"]
    for iid, it in proj.printed.items():
        ps = part_print_settings(it.spec)
        st = part_settings((rep.get("parts") or {}).get(iid) or {}, it.spec, supports)
        sup = (f"on, {st['support_type']}" + (f" ({st['overhang_pct']:g} % of the surface is steeper than 45 deg)"
                                                if it.spec.get("supports") not in SUPPORT_ON else " (the design calls for it)")
               if st["supports"] else
               "off" + (f" ({st['overhang_pct']:g} % of the surface is steeper than 45 deg: bridges and hole tops; check "
                        "the slicer preview)" if st["overhang_pct"] > 0.5 else ""))
        brim = f"{st['brim_mm']} mm outer brim (tall and narrow on the bed)" if st["brim"] == "outer_only" else "auto"
        L.append(f"| {iid} | {ps['material']} | {orientation_words(ps['print_rot'])} | {st['layer_mm']} mm | {sup} | {brim} | "
                 f"{ps['infill_pct']} % | {ps['walls']} |")
    L += ["", "The mass estimate and the strength checks assume these infill and wall settings: keep them."]
    (outdir / "PRINT_SETTINGS.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return {"plates": [{k: r[k] for k in ("file", "parts", "grams", "min_seconds", "materials", "sliced")} for r in rows],
            "slicer": sl[0] if sl else None, "filament_g": round(total_g, 1)}
