"""Plain-words problems: turn a check's message into something anyone can read at a glance (Studio's Checks tab, the
CLI). Every card says which part, what is wrong in one sentence, why it matters and what usually fixes it; the raw
check text stays attached as `detail` for whoever fixes it.

Rules are tried in order; the first whose pattern matches wins. A message no rule knows still gets a card (its part
and first clause), so a new check never disappears from the page - add a rule for it here when it shows up.

Work status says whether anyone is on it: a Studio job running for the project (fix / edit / design / check), or a
fresh claim (tools/claims.py) whose PLAN item names the project.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STALE_MIN = 90                      # same as tools/claims.py: a claim with no heartbeat for this long is abandoned

# (pattern, title, why, fix, kind). Titles / why / fix may use the pattern's named groups as {name}.
RULES = [
    (r"^(?P<part>[\w.-]+): exported mesh is not watertight",
     "Its print file has a hole in the surface",
     "The slicer may fill it wrongly or refuse the file.",
     "Close the gap in the model (usually two shapes touching only along an edge or at a point).", "print"),
    (r"^(?P<part>[\w.-]+): walls as thin as (?P<t>[\d.]+) mm",
     "Some walls are too thin to print ({t} mm)",
     "A printer lays plastic about 0.4 mm wide; walls under 0.8 mm print weak, ragged or not at all.",
     "Thicken that area, or cut the thin sliver away.", "print"),
    (r"^(?P<part>[\w.-]+) is (?P<n>\d+) separate solids",
     "It is {n} loose pieces instead of one part",
     "A printed part has to be one connected piece.",
     "Join the pieces, or make them separate parts.", "print"),
    (r"^(?P<part>[\w.-]+) is .* does not fit the",
     "Too big for the printer",
     "It will not fit on the print bed.",
     "Split it into parts, or turn it to fit.", "print"),
    (r"^(?P<part>[\w.-]+): geometry is invalid",
     "Its 3D shape is broken",
     "Faces cross through each other, so the file cannot be printed reliably.",
     "Rebuild the feature that broke it.", "print"),
    (r"^(?P<part>[\w.-]+): .*overhangs more than 45 degrees, but this project must print without supports",
     "It needs supports, but this project prints without them",
     "Surfaces leaning past 45 degrees sag in mid-air without support material.",
     "Add chamfers or turn the part so steep faces point up.", "print"),
    (r"^(?P<part>[\w.-]+): (?P<screw>M[\d.]+) (?P<hk>\w+) hole \(group '(?P<group>[^']+)'\) at \[(?P<at>[^\]]+)\] has less than (?P<wall>[\d.]+) mm of wall",
     "A screw hole is too close to the edge",
     "With under {wall} mm of plastic round it, the {screw} hole can split open when the screw is tightened or loaded.",
     "Move the hole inward, or add material around it.", "fit"),
    (r"^(?P<part>[\w.-]+) and (?P<other>[\w.-]+) overlap by (?P<v>[\d.]+) mm3",
     "Two parts are in the same space",
     "{part} and {other} overlap ({v} mm³), so they cannot both be assembled as drawn.",
     "Cut room into one of them, or move one.", "fit"),
    (r"^moving joint '(?P<joint>[^']+)' collides: (?P<part>[\w.-]+) hits (?P<other>[\w.-]+)",
     "Parts crash into each other when it moves",
     "When '{joint}' moves through its range, {part} runs into {other}.",
     "Give it more clearance, or limit how far the joint moves.", "motion"),
    (r"^fastener group '(?P<group>[^']+)': .* hole in (?P<part>[\w.-]+) .*has no matching",
     "A screw hole has no partner hole",
     "The screw for '{group}' has nothing lined up on the other part to go into.",
     "Line the two holes up (use the same group name on both sides).", "fit"),
    (r"^fastener group '(?P<group>[^']+)': (?P<part>[\w.-]+) sits (?P<gap>[\d.]+) mm off (?P<other>[\w.-]+)",
     "Parts don't touch where they are screwed together",
     "{part} sits {gap} mm away from {other}, so the '{group}' screws would bend it instead of clamping it.",
     "Make the two faces meet.", "fit"),
    (r"^fastener group '(?P<group>[^']+)': no standard (?P<screw>M[\d.]+) length fits",
     "No standard screw length fits",
     "The '{group}' joint needs a {screw} length you can't buy.",
     "Make the clamped parts thinner or thicker, or the hole deeper.", "fit"),
    (r"^fastener group '(?P<group>[^']+)': .*hole in (?P<part>[\w.-]+) .*has no screw coming through",
     "A threaded hole gets no screw",
     "The '{group}' hole in {part} has no screw hole lined up over it.",
     "Line the parts' holes up, or remove the extra hole.", "fit"),
    (r"^fastener group '(?P<group>[^']+)'",
     "A screw joint doesn't work",
     "The '{group}' screws don't line up, fit or engage as they should.",
     "See the details: usually a hole position, depth or screw length.", "fit"),
    (r"^(?P<part>[\w.-]+?)(?: \([^)]*\))?[^:]*: no (?P<s>[\d.]+) mm (?:hex )?key can reach",
     "A screw can't be reached with a tool",
     "No {s} mm hex key can get to the screw head, so it can't be tightened.",
     "Open a channel to it, or change the assembly order.", "assembly"),
    (r"^(?P<part>[\w.+ -]+?) cannot be (?:inserted|pushed onto)",
     "A part can't be put in place",
     "During assembly it would have to pass through another part.",
     "Change the assembly order, or make a path for it.", "assembly"),
    (r"^wiring '(?P<wire>[^']+)' runs through (?P<part>[\w.-]+)",
     "A wire goes through solid plastic",
     "The '{wire}' wire's route passes through {part}.",
     "Route it round, or add a hole or channel for it.", "wiring"),
    (r"^wiring '(?P<wire>[^']+)': length_mm",
     "A wire is too short",
     "The '{wire}' wire can't reach along its route (at every joint position).",
     "Make the wire longer in project.yaml.", "wiring"),
    (r"^wiring '(?P<wire>[^']+)'",
     "A wire problem",
     "The '{wire}' wire's route or length doesn't work.",
     "See the details.", "wiring"),
    (r"^pin group '(?P<group>[^']+)'",
     "A pin joint doesn't work",
     "The '{group}' pin doesn't line up, fit or turn as it should.",
     "See the details: usually a hole position or pin length.", "fit"),
    (r"^requirement '(?P<req>[^']+)' failed: (?P<rest>.*)",
     "An engineering target is missed: {req}",
     "{rest}",
     "Change the design (or the parts) until it meets the target.", "engineering"),
    (r"^requirement '(?P<req>[^']+)'",
     "An engineering check is set up wrong: {req}",
     "The check can't judge the design as written.",
     "Fix the requirement's settings in project.yaml.", "engineering"),
    (r"^drawing of (?P<part>[\w.-]+) could not be made",
     "Its paper drawing (PDF) could not be made",
     "Only the 2D drawing is missing; the part itself and its print file are fine.",
     "Kerf's drawing layout needs a fix for this part.", "files"),
    (r"^(?P<part>[\w.-]+) failed to build",
     "The part could not be built",
     "Its code stopped with an error, so there is no shape to check or print.",
     "Fix the part's code (see the details).", "build"),
    (r"^(?P<part>[\w.-]+): nothing holds it",
     "A part isn't attached to anything",
     "No screw, pin or strap holds it, so it would fall out.",
     "Give it a mount, or say what holds it.", "assembly"),
    (r"^circuit:",
     "The wiring diagram has an error",
     "Something is connected wrongly or not at all.",
     "See the details.", "wiring"),
    (r"^bom_extra",
     "A shopping-list entry is malformed",
     "One extra item in the parts list can't be read.",
     "Fix that bom_extra line in project.yaml.", "files"),
]
_COMPILED = [(re.compile(p), t, w, f, k) for p, t, w, f, k in RULES]

KIND_LABEL = {"print": "Printing", "fit": "Fit", "motion": "Motion", "assembly": "Assembly", "wiring": "Wiring",
              "engineering": "Engineering", "files": "Files", "build": "Build", "other": "Other"}

# plain names for requirement checks (Studio's requirement table and failed-requirement cards)
CHECK_NAMES = {
    "thrust_to_weight": "Thrust vs weight", "static_margin": "Balance (centre of gravity)", "wing_loading": "Weight per wing area",
    "stall_speed": "Slowest flying speed", "spar_bending": "Wing spar strength", "flight_time": "Flight time",
    "mass_max": "Total weight", "fea_static": "Strength under load", "power_budget": "Power supply load",
    "prop_clearance": "Propeller clearance", "prop_ground": "Propeller ground clearance", "bbox_max": "Overall size",
    "servo_torque": "Servo strength", "reach": "Reach", "connector_access": "Plug can be reached",
}


class _Fmt(dict):
    def __missing__(self, k):
        return "?"


def explain(msg: str, parts=()) -> dict:
    """{title, part, why, fix, kind, kind_label, detail} for one problem message."""
    for rx, title, why, fix, kind in _COMPILED:
        m = rx.search(msg)
        if m:
            g = _Fmt({k: v for k, v in m.groupdict().items() if v is not None})
            part = g.get("part") if "part" in g else None
            if part and g.get("other"):
                part = f"{part} ↔ {g['other']}"
            return {"title": title.format_map(g), "part": part, "why": why.format_map(g), "fix": fix.format_map(g),
                    "kind": kind, "kind_label": KIND_LABEL[kind], "detail": msg}
    head = msg.split(":", 1)
    part = head[0].strip() if len(head) > 1 and head[0].strip() in set(parts) else None
    body = head[1].strip() if part else msg
    title = re.split(r"[;(]", body, 1)[0].strip()
    return {"title": (title[:1].upper() + title[1:])[:110], "part": part, "why": "", "fix": "", "kind": "other",
            "kind_label": KIND_LABEL["other"], "detail": msg}


def explain_requirement(r: dict) -> dict:
    """A failed requirement row as a card."""
    from kerf import glossary
    c = r.get("check", "")
    name = CHECK_NAMES.get(c) or (glossary.name(c) if c in glossary.CHECKS else c or r.get("id", ""))
    u = r.get("unit") or ""
    unit = u if u.startswith((":", "%", "°", "x ")) else f" {u}" if u else ""
    val, lim, bound = r.get("value"), r.get("limit"), r.get("bound") or "limit"
    def num(v):
        return f"{v:.3g}" if isinstance(v, float) else str(v)
    if isinstance(lim, list):
        target = "between " + " and ".join(num(x) for x in lim) + unit
    else:
        target = {"max": "at most ", "min": "at least "}.get(bound, "") + num(lim) + unit
    what = f"It is {num(val)}{unit}; it needs to be {target}." if val is not None and lim is not None else (r.get("detail") or "")
    return {"title": f"{name}: target missed", "part": None, "why": " ".join(x for x in (what, r.get("why") or "") if x),
            "fix": "Change the design or its parts until it meets the target.", "kind": "engineering",
            "kind_label": KIND_LABEL["engineering"], "detail": f"requirement '{r.get('id')}' ({r.get('check')}): {r.get('detail') or ''}".strip()}


def cards(rep: dict, parts=()) -> list[dict]:
    """Every blocking problem as a card, failed requirements included once (their 'requirement ... failed' problem
    line is replaced by the requirement's own card)."""
    failed = [r for r in rep.get("requirements") or [] if not r.get("ok") and not r.get("skipped") and not r.get("advisory")]
    ids = {r.get("id") for r in failed}
    out = []
    for p in rep.get("problems") or []:
        m = re.match(r"^requirement '([^']+)' failed", p)
        if m and m.group(1) in ids:
            continue
        out.append(explain(p, parts))
    out += [explain_requirement(r) for r in failed]
    return out


# ---------------------------------------------------------------- who is on it
def claims(root: Path = ROOT) -> list[dict]:
    out = []
    for f in sorted((root / "claims").glob("*.json")):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001 - a broken claim file is no claim
            pass
    return out


def work_status(project: str, jobs: list[dict], claim_list: list[dict], now: float | None = None) -> dict:
    """{"state": "fixing" | "checking" | "claimed" | "idle", "text"}: is anyone working on this project's problems.
    jobs: [{"kind", "label", "started"}] running for this project; claim_list: claims/*.json contents."""
    now = time.time() if now is None else now
    def ago(t):
        m = max(0, int((now - float(t)) / 60))
        return "just now" if m < 1 else f"{m} min ago" if m < 90 else f"{m // 60} h ago"
    for j in jobs:
        if j.get("kind") in ("fix", "edit", "design", "auto_fix"):
            return {"state": "fixing", "text": f"Being fixed now: Claude Code is working on it ({j.get('label', j['kind'])}, started {ago(j.get('started', now))})."}
    for j in jobs:
        return {"state": "checking", "text": f"Being re-checked now ({j.get('label', j.get('kind', 'check'))}, started {ago(j.get('started', now))})."}
    pat = re.compile(r"(?<![\w])`?" + re.escape(project) + r"`?(?![\w])")
    for c in claim_list:
        if now - float(c.get("heartbeat", 0)) < STALE_MIN * 60 and pat.search(c.get("item", "")):
            item = re.sub(r"\s+", " ", c.get("item", ""))
            task = re.split(r":\s|\s\u2014\s|\s-\s|;\s", item, 1)[0].strip()      # its first clause: "E7 `fpv_wing`"
            return {"state": "claimed", "text": f"A Claude session is working on this project (last active {ago(c.get('heartbeat', now))}).",
                    "task": task[:120], "item": item}
    return {"state": "idle", "text": "Nobody is working on this yet. \"Fix these\" hands it to Claude Code."}
