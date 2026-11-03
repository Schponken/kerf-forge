"""Declared project inputs for downloads, review fingerprints and explicit build-cache dependencies."""
from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath

import yaml

SKIP_DIRS = {"out", "__pycache__", "node_modules", "feedback", "verify"}
PRIVATE_NAMES = {"review.json", "catalog_deps.json", "credentials", "credential", "secrets", "secret",
                 "password", "passwords", "tokens", "token", "id_rsa", "id_ed25519"}


def inside(base: Path, relative: str) -> Path:
    """A project-relative path with no escaping or symlink components; shared with assembly modules."""
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("Source paths must be nonempty relative strings")
    p = Path(relative)
    if p.is_absolute() or not p.parts or ".." in p.parts or "\\" in relative or PureWindowsPath(relative).drive:
        raise ValueError(f"Source path must stay inside {base.name}: {relative}")
    target = base / p
    if any((base / Path(*p.parts[:i])).is_symlink() for i in range(1, len(p.parts) + 1)):
        raise ValueError(f"Source files cannot be symbolic links: {relative}")
    return target


def _design_file(root: Path, relative: str) -> Path:
    f = inside(root, relative)
    parts = Path(relative).parts
    if any(p.startswith(".") or p in SKIP_DIRS for p in parts) or f.name.lower() in PRIVATE_NAMES or \
            f.stem.lower() in PRIVATE_NAMES or f.suffix.lower() in {".pyc", ".pyo", ".pem", ".key", ".p12", ".pfx"}:
        raise ValueError(f"Not a design source (cache, output, review or private file): {relative}")
    if not f.is_file():
        raise ValueError(f"Missing design source: {relative}")
    return f


def extra_files(root: Path, data: dict) -> dict[str, Path]:
    """Explicit geometry dependencies outside the normal part/layout/import declarations."""
    extra = data.get("source_files", [])
    if not isinstance(extra, list) or any(not isinstance(p, str) for p in extra):
        raise ValueError("source_files must be a list of project-relative file paths")
    return {Path(p).as_posix(): _design_file(root, p) for p in sorted(extra)}


def input_files(root: Path) -> dict[str, Path]:
    """Contract, recursive Python helpers and declared geometry inputs; never infer arbitrary file reads."""
    contract = _design_file(root, "project.yaml")
    try:
        data = yaml.safe_load(contract.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeError) as e:
        raise ValueError(f"Invalid project.yaml: {e}") from e
    if not isinstance(data, dict) or not isinstance(data.get("parts") or {}, dict):
        raise ValueError("project.yaml must contain a mapping of parts")
    needed = {"project.yaml", *extra_files(root, data)}
    for pid, spec in (data.get("parts") or {}).items():
        if not isinstance(spec or {}, dict):
            raise ValueError(f"Part {pid} must be a mapping")
        spec = spec or {}
        if imported := spec.get("import"):
            inside(root, imported)
            if Path(imported).suffix.lower() not in {".step", ".stp", ".stl", ".3mf"}:
                raise ValueError(f"Unsupported imported model: {imported}; use STEP, STL or 3MF")
            needed.add(imported)
        else:
            part_file = spec.get("file", f"parts/{pid}.py")
            inside(root, part_file)
            needed.add(part_file)
        if spec.get("source") == "meshy":
            from .meshy import mesh_path
            if spec.get("mesh"):
                inside(root, spec["mesh"])
            mesh = mesh_path(root, str(pid), spec)
            try:
                needed.add(mesh.relative_to(root).as_posix())
            except ValueError as e:
                raise ValueError(f"Mesh source must stay inside the project: {mesh}") from e
    if data.get("layout"):
        inside(root, data["layout"])
        needed.add(data["layout"])
    helpers = inside(root, "parts")
    def unreadable(error):
        raise error
    for directory, dirs, files in os.walk(helpers, followlinks=False, onerror=unreadable) if helpers.exists() else []:
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
        for child in dirs:
            inside(root, (Path(directory) / child).relative_to(root).as_posix())
        for child in files:
            if child.endswith(".py") and not child.startswith("."):
                needed.add((Path(directory) / child).relative_to(root).as_posix())
    if any(not isinstance(p, str) for p in needed):
        raise ValueError("Design source paths must be strings")
    return {Path(p).as_posix(): _design_file(root, p) for p in sorted(needed)}


def design_files(root: Path) -> dict[str, Path]:
    """The editable geometry inputs plus optional human-readable design/research notes for downloads."""
    files = input_files(root)
    for doc in ("DESIGN.md", "REFERENCES.md"):
        if (root / doc).exists() or (root / doc).is_symlink():
            files[doc] = _design_file(root, doc)
    return dict(sorted(files.items()))
