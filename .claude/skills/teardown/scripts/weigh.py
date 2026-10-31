#!/usr/bin/env python3
"""Weigh a repository: how much of it is real code, how much is prompt, what it delegates.

The point is to replace "this looks like a small skill" with a number. Run it on a
checkout before you write a single word of the teardown.

    python3 weigh.py <path-to-repo> [--json]

Prints a weight class, the code/prose split, what the repo calls out to, and the
files that actually carry the weight.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

CODE_EXT = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
    ".kt", ".swift", ".c", ".h", ".cc", ".cpp", ".hpp", ".rb", ".php", ".cs",
    ".sh", ".bash", ".zsh", ".lua", ".ex", ".exs", ".scala", ".dart", ".vue", ".svelte",
}
PROSE_EXT = {".md", ".mdx", ".rst", ".txt", ".adoc"}

# --- licence -------------------------------------------------------------
# Weight was the gate this script was built for. Measuring a month of a trending
# feed moved licence in front of it: GitHub's API returned NOASSERTION for 19 of
# 138 repos, and reading those files showed 8 of the 19 restrict use. One is an
# MIT header with a no-commercial clause appended, which the API reports as
# "Other" and a human reads as MIT.
LICENCE_FILES = (
    "LICENSE", "LICENCE", "COPYING", "LICENSE.md", "LICENCE.md", "COPYING.md",
    "LICENSE.txt", "LICENCE.txt", "LICENSE-MIT", "LICENSE.rst",
)
# Ordered, most specific first: the first match is the base licence.
LICENCE_BASE = (
    ("fair source license", "source-available", "Fair Source: use limits now, open later"),
    ("business source license", "source-available", "BUSL: no production use until the change date"),
    ("elastic license 2.0", "source-available", "ELv2: may not be offered as a managed service"),
    ("server side public license", "source-available", "SSPL: network use forces you to open your stack"),
    ("polyform", "source-available", "PolyForm: named use limits"),
    ("functional source license", "source-available", "FSL: use limits now, open later"),
    ("attribution-noncommercial", "source-available", "CC BY-NC: no commercial use"),
    # GPL family before any clause search: the AGPL text itself contains the
    # word "noncommercially", and a naive clause search calls AGPL a custom
    # non-commercial licence. That was a real false positive, not a hypothetical.
    ("gnu affero general public", "copyleft", "AGPL: network use forces you to publish your source"),
    ("gnu lesser general public", "copyleft", "LGPL: linking obligations"),
    ("gnu general public", "copyleft", "GPL: derivative works stay GPL"),
    ("mozilla public license", "weak-copyleft", "MPL: per-file copyleft"),
    ("apache license", "permissive", "Apache-2.0"),
    ("mit license", "permissive", "MIT"),
    ("permission is hereby granted, free of charge", "permissive", "MIT-style grant"),
    ("redistribution and use in source and binary forms", "permissive", "BSD-style"),
    ("isc license", "permissive", "ISC"),
    ("this is free and unencumbered software", "public-domain", "Unlicense"),
    ("cc0 1.0", "public-domain", "CC0"),
)
# Clauses bolted on top of an otherwise permissive header. This is the case the
# API hides best, and the one that costs you if you skim the first line.
LICENCE_ADDED = (
    ("commons clause", "Commons Clause: you may not sell it"),
    ("non-commercial use only", "non-commercial use only"),
    ("for non-commercial purposes only", "non-commercial use only"),
    ("may not be used for commercial", "no commercial use"),
    ("not for commercial use", "no commercial use"),
    ("personal, non-commercial", "personal non-commercial use only"),
    ("prior written permission", "written permission required for some uses"),
)
# Families you cannot simply take code from into a closed or differently
# licensed project. Printed with a marker so it is not missed.
LICENCE_BLOCKING = {"source-available", "copyleft", "none", "unknown"}
# A notebook is JSON holding code, prose and base64 outputs at once. Counting
# its lines lies in both directions, so it is counted in files, like an asset.
NOTEBOOK_EXT = {".ipynb"}
CONFIG_EXT = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml", ".env"}
STYLE_EXT = {".css", ".scss", ".sass", ".less"}
MARKUP_EXT = {".html", ".htm"}
ASSET_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".mp3", ".wav",
    ".ogg", ".flac", ".mp4", ".mov", ".webm", ".woff", ".woff2", ".ttf", ".otf",
    ".pdf", ".zip", ".gz", ".bin", ".onnx", ".safetensors", ".pt",
}
LOCK_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "uv.lock", "poetry.lock",
    "Cargo.lock", "Gemfile.lock", "composer.lock", "go.sum", "bun.lockb",
}
SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", ".venv", "venv", "__pycache__",
    "vendor", "target", ".cache", "site-packages", ".mypy_cache", ".pytest_cache",
}
TEST_HINT = re.compile(r"(^|/)(tests?|__tests__|spec|e2e)(/|$)|(\.|_|-)(test|spec)\.", re.I)
# Generated code is real code that nobody wrote. Counting it as authorship makes a
# thin SDK wrapper look like a platform: one repo here carried a single 136,000-line
# zz_generated.gen.go and read as 2M lines of engineering.
GENERATED_HINT = re.compile(
    r"(^|/)(generated|gen|__generated__|autogen|swagger|openapi)(/|$)"
    r"|(^|/)zz_generated|\.gen\.(go|ts|py|rs)$|\.pb\.(go|py|cc|h)$"
    r"|_pb2(_grpc)?\.py$|\.g\.dart$|\.designer\.cs$",
    re.I)

# What a repo hands off to somebody else. This is the tell that separates
# "a platform" from "a wrapper with good taste".
DELEGATION = [
    (re.compile(r"\bnpx\s+(?:-y\s+)?([@\w./-]+)"), "npx"),
    (re.compile(r"\buvx\s+([\w./-]+)"), "uvx"),
    (re.compile(r"\bdocker\s+(?:run|compose)\b"), "docker"),
    (re.compile(r"\bffmpeg\b"), "ffmpeg"),
    (re.compile(r"\bgit\s+clone\b"), "git clone"),
    (re.compile(r"\bcurl\s+-[a-zA-Z]*\s*https?://"), "curl"),
    (re.compile(r"\b(openai|anthropic|gemini|claude|ollama)\b", re.I), "llm-api"),
]

AGENT_MARKERS = {
    "SKILL.md": "Claude/Agent skill",
    "AGENTS.md": "agents.md convention",
    "CLAUDE.md": "Claude Code project instructions",
    ".claude-plugin": "Claude Code plugin marketplace",
    ".claude": "Claude Code skills dir",
    ".cursor": "Cursor rules",
    ".opencode": "opencode skills",
    ".agents": "Codex CLI skills",
    "mcp.json": "MCP server",
}


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def count_lines(path: Path) -> int:
    try:
        with path.open("rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def classify(path: Path, root: Path) -> str:
    name = path.name
    ext = path.suffix.lower()
    if name in LOCK_NAMES:
        return "lock"
    if ext in NOTEBOOK_EXT:
        return "notebook"
    if ext in ASSET_EXT:
        return "asset"
    if ext in PROSE_EXT:
        return "prose"
    if ext in CONFIG_EXT:
        return "config"
    if ext in STYLE_EXT:
        return "style"
    if ext in MARKUP_EXT:
        return "markup"
    if ext in CODE_EXT:
        rel = str(path.relative_to(root))
        if TEST_HINT.search(rel):
            return "test"
        return "generated" if GENERATED_HINT.search(rel) else "code"
    return "other"


def weight_class(code: int, prose: int, files: int) -> tuple[str, str]:
    """Return (class, one-line reason). Thresholds are deliberate and blunt.

    Prose beating code by 2x is the loudest signal there is: the repo's product
    is the instructions, and whatever code it ships is glue or a maintainer tool.
    """
    if code < 2000 and prose >= 2 * code:
        return ("prompt-class", f"prose outweighs code {prose / max(code, 1):.1f}:1, the artifact is the writing")
    if code < 400:
        return ("prompt-class", "under 400 lines of code in total")
    if code < 3000:
        return ("small tool", "a few thousand lines, readable end to end in a sitting")
    if code < 20000:
        return ("medium tool", "too big to read fully; adopt or integrate, do not rebuild")
    return ("fork-class", "a platform; forking it means owning a living codebase")


def find_delegation(root: Path) -> Counter:
    hits: Counter = Counter()
    for path in iter_files(root):
        if classify(path, root) not in {"code", "prose", "config", "markup"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern, label in DELEGATION:
            for match in pattern.finditer(text):
                target = match.group(1) if match.groups() else label
                hits[f"{label}: {target}"] += 1
    return hits


def find_markers(root: Path) -> list[str]:
    found = []
    for marker, label in AGENT_MARKERS.items():
        matches = [p for p in root.rglob(marker) if ".git" not in p.parts]
        if matches:
            found.append(f"{marker} → {label} ({len(matches)}x)")
    return found


def deps(root: Path) -> dict:
    out: dict[str, list[str]] = {}
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
            out["npm"] = sorted(data.get("dependencies", {}).keys())
        except (OSError, json.JSONDecodeError):
            pass
    req = root / "requirements.txt"
    if req.exists():
        out["pip"] = [
            line.split("==")[0].split(">=")[0].strip()
            for line in req.read_text(encoding="utf-8", errors="ignore").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        block = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.S)
        if block:
            out.setdefault("pip", []).extend(
                re.findall(r'"([A-Za-z0-9_.-]+)', block.group(1))
            )
    return out


def classify_licence(text: str) -> dict:
    """Base licence first, then clauses added on top. A restriction bolted onto a
    permissive header means the repo is not permissive, whatever its first line says."""
    low = " ".join(text.lower().split())
    family, meaning = "unknown", "no known licence text matched"
    for needle, fam, mean in LICENCE_BASE:
        if needle in low:
            family, meaning = fam, mean
            break
    added = [note for needle, note in LICENCE_ADDED if needle in low]
    if added and family in {"permissive", "public-domain", "unknown"}:
        family = "source-available"
    return {"family": family, "meaning": meaning, "added": added}


def find_licence(root: Path) -> dict:
    for name in LICENCE_FILES:
        path = root / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        out = classify_licence(text)
        out["file"] = name
        return out
    return {"file": None, "family": "none", "added": [],
            "meaning": "no licence file: the author keeps all rights by default"}


def weigh(root: Path) -> dict:
    lines: Counter = Counter()
    files: Counter = Counter()
    biggest: list[tuple[int, str]] = []
    for path in iter_files(root):
        kind = classify(path, root)
        files[kind] += 1
        if kind in {"asset", "lock", "notebook"}:
            continue
        n = count_lines(path)
        lines[kind] += n
        if kind in {"code", "prose"}:
            biggest.append((n, str(path.relative_to(root))))
    biggest.sort(reverse=True)
    cls, reason = weight_class(lines["code"], lines["prose"], sum(files.values()))
    return {
        "root": str(root),
        "licence": find_licence(root),
        "weight_class": cls,
        "weight_reason": reason,
        "lines": dict(lines),
        "files": dict(files),
        "biggest_files": [{"lines": n, "path": p} for n, p in biggest[:12]],
        "delegates_to": dict(find_delegation(root).most_common(15)),
        "agent_markers": find_markers(root),
        "declared_deps": deps(root),
    }


def render(report: dict) -> str:
    lines = report["lines"]
    files = report["files"]
    code, prose = lines.get("code", 0), lines.get("prose", 0)
    total_files = sum(files.values())
    lic = report["licence"]
    mark = "!! " if lic["family"] in LICENCE_BLOCKING else "   "
    out = [
        f"{mark}licence  : {lic['family']} — {lic['meaning']}"
        + (f" [{lic['file']}]" if lic["file"] else ""),
    ]
    for note in lic["added"]:
        out.append(f"!!           + {note}")
    out += [
        f"weight class : {report['weight_class']}  ({report['weight_reason']})",
        f"code         : {code} lines in {files.get('code', 0)} files",
        f"prose        : {prose} lines in {files.get('prose', 0)} files",
        f"tests        : {lines.get('test', 0)} lines in {files.get('test', 0)} files",
        f"generated    : {lines.get('generated', 0)} lines in {files.get('generated', 0)} files"
        " (code nobody wrote)",
        f"assets       : {files.get('asset', 0)} files (not counted in lines)",
        f"notebooks    : {files.get('notebook', 0)} files (not counted in lines)",
        f"files total  : {total_files}",
    ]
    if code:
        out.append(f"prose:code   : {prose / code:.2f}:1")
    if report["agent_markers"]:
        out.append("markers      : " + "; ".join(report["agent_markers"]))
    if report["delegates_to"]:
        out.append("delegates to : " + ", ".join(report["delegates_to"]))
    for name, items in report["declared_deps"].items():
        shown = ", ".join(items[:10]) or "none"
        out.append(f"deps ({name}) : {shown}")
    out.append("carries the weight:")
    for item in report["biggest_files"][:8]:
        out.append(f"  {item['lines']:>6}  {item['path']}")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()
    root = args.repo.expanduser().resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 1
    report = weigh(root)
    print(json.dumps(report, indent=2) if args.json else render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
