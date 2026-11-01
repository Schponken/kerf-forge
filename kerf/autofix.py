"""Auto-fix pass for the common findings, run before a design goes to the reviewer (`kerf fixes <p> [--apply]`).

From the last check's report.json it turns these findings into concrete edits of the part code:
- a pin / fastener hole that prints horizontal but was cut round  ->  `teardrop="auto"` on its iface call
  (iface works the angle out from the part's print_rot);
- a self-tapping (`tap`) hole closer than 1.5 x d to a free edge  ->  that iface call's kind `"tap"` -> `"heatset"`
  (a melted-in brass insert does not wedge the edge apart the way a thread-forming screw does; ENGINEERING.md s7).
  Its bore is larger, so it can break the 2.4 mm insert-wall rule: `--apply` writes it only with `--heatset`, and the
  check that follows must pass (else revert it and grow a boss instead);
and lists, without editing, what needs a designer: a hole with too little wall or a non-tap hole near an edge
(grow a boss: kerf.idioms.boss), a sharp inside corner in a stressed zone (fillet it).
Edits are made with the Python AST: only an iface call whose arguments name the finding's group is touched.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROUND = re.compile(r"^(\w+): (\d+) (?:pin|(\w+)) hole\(s\) of group '([\w-]+)' print horizontal and are cut round")
NEAR_EDGE = re.compile(r"^(\w+): (\d+) (M[\d.]+) (\w+) hole\(s\) of group '([\w-]+)' sit closer than 1\.5 x d")
THIN_WALL = re.compile(r"^(\w+): (M[\d.]+) (\w+) hole \(group '([\w-]+)'\) at (\[[^\]]*\]) has less than")
SHARP = re.compile(r"^(\w+): .*sharp inside corner", re.I)

IFACE_CALLS = {"bolt_pattern", "servo_mount", "horn_mount", "pin_hole"}   # the iface calls that take teardrop / kind


def _calls(src: str, group: str):
    """iface calls in a part source whose arguments include the string `group`."""
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name not in IFACE_CALLS:
                continue
            args = list(node.args) + [k.value for k in node.keywords]
            if any(isinstance(a, ast.Constant) and a.value == group for a in args):
                yield node


def _offset(src: str, line: int, col: int) -> int:
    """String index of an AST (line, col) position; AST columns count UTF-8 bytes, so a line with a non-ASCII
    character before the column (a "x" or "deg" sign in a comment) still lands right."""
    lines = src.splitlines(keepends=True)
    return sum(len(x) for x in lines[: line - 1]) + len(lines[line - 1].encode("utf-8")[:col].decode("utf-8"))


def _add_teardrop(src: str, group: str) -> tuple[str, int]:
    n = 0
    for node in sorted(_calls(src, group), key=lambda c: (c.end_lineno, c.end_col_offset), reverse=True):
        if any(k.arg == "teardrop" for k in node.keywords):
            continue
        end = _offset(src, node.end_lineno, node.end_col_offset) - 1          # the closing parenthesis
        src = src[:end] + ', teardrop="auto"' + src[end:]
        n += 1
    return src, n


def _tap_to_heatset(src: str, group: str) -> tuple[str, int]:
    n = 0
    edits = []
    for node in _calls(src, group):
        for a in list(node.args) + [k.value for k in node.keywords]:
            if isinstance(a, ast.Constant) and a.value == "tap":
                edits.append((_offset(src, a.lineno, a.col_offset), _offset(src, a.end_lineno, a.end_col_offset)))
    for s0, s1 in sorted(edits, reverse=True):
        quote = src[s0]
        src = src[:s0] + f"{quote}heatset{quote}" + src[s1:]
        n += 1
    return src, n


def _source_of(proj_dir: Path, part: str, data: dict) -> Path | None:
    spec = (data.get("parts") or {}).get(part) or {}
    f = spec.get("file") if isinstance(spec, dict) else None
    p = proj_dir / (f or f"parts/{part}.py")
    return p if p.exists() else None


def fixes(proj_dir, apply: bool = False, heatset: bool = False) -> list[dict]:
    """Findings from out/report.json with the fix for each. apply=True writes the teardrops (always safe: the same hole,
    printable roof); tap -> heat-set is written only with heatset=True as well."""
    import yaml
    proj_dir = Path(proj_dir)
    rep = json.loads((proj_dir / "out" / "report.json").read_text(encoding="utf-8"))
    data = yaml.safe_load((proj_dir / "project.yaml").read_text(encoding="utf-8")) or {}
    out = []
    for msg in (rep.get("problems") or []) + (rep.get("warnings") or []):
        m = ROUND.match(msg)
        if m:
            part, group = m.group(1), m.group(4)
            out.append({"finding": msg, "part": part, "group": group, "kind": "teardrop",
                        "fix": f'add teardrop="auto" to the iface call of group \'{group}\' in {part}'})
            continue
        m = NEAR_EDGE.match(msg)
        if m:
            part, kind, group = m.group(1), m.group(4), m.group(5)
            if kind == "tap":
                out.append({"finding": msg, "part": part, "group": group, "kind": "heatset",
                            "fix": f"group '{group}' in {part}: self-tapping hole near an edge -> heat-set insert (kind \"heatset\")"})
            else:
                out.append({"finding": msg, "part": part, "group": group, "kind": "manual",
                            "fix": f"group '{group}' in {part}: grow a boss around the hole (kerf.idioms.boss, outer d >= 3 x screw d) "
                                   "or move the hole in; or say in DESIGN.md that the purchased part's pattern forces it"})
            continue
        m = THIN_WALL.match(msg)
        if m:
            out.append({"finding": msg, "part": m.group(1), "group": m.group(4), "kind": "manual",
                        "fix": f"group '{m.group(4)}' in {m.group(1)} at {m.group(5)}: add a boss (kerf.idioms.boss) or move the hole in"})
            continue
        if SHARP.match(msg):
            part = SHARP.match(msg).group(1)
            out.append({"finding": msg, "part": part, "group": None, "kind": "manual",
                        "fix": f"{part}: fillet the sharp inside corners the check lists (kerf.features.safe_fillet, the "
                               "project's style radius), stressed ones first"})
    for f in out:
        if f["kind"] not in ("teardrop", "heatset"):
            f["applied"] = False
            continue
        src_path = _source_of(proj_dir, f["part"], data)
        f["file"] = str(src_path.relative_to(proj_dir)) if src_path else None
        if src_path is None:
            f["applied"] = False
            continue
        src = src_path.read_text(encoding="utf-8")
        new, n = (_add_teardrop if f["kind"] == "teardrop" else _tap_to_heatset)(src, f["group"])
        if n == 0 and any(True for _ in _calls(src, f["group"])):     # the call is there and already fixed
            f["applied"], f["fix"] = False, f["fix"] + " (already in the part file: rebuild to clear the finding)"
            continue
        if n == 0:                         # the group is built in a helper (layout.py) or the call is unusual
            f["applied"] = False
            f["fix"] += " (no matching iface call in the part file: edit it by hand)"
            continue
        compile(new, str(src_path), "exec")
        do = apply and (f["kind"] == "teardrop" or heatset)
        if do:
            src_path.write_text(new, encoding="utf-8")
        f["applied"] = do
        f["edits"] = n
    return out
