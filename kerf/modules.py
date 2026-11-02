"""Reusable project assemblies: inspect their contracts, then make independent editable instances."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import yaml

from . import project
from .sources import inside as _inside

ROOT = Path(__file__).resolve().parent.parent


def entries() -> dict:
    return yaml.safe_load((ROOT / "catalog/modules.yaml").read_text(encoding="utf-8")) or {}


def _source(name: str) -> tuple[dict, Path, dict[str, bytes]]:
    entry = entries().get(name)
    if entry is None:
        raise ValueError(f"Unknown module '{name}'. Run `kerf modules` to see available modules.")
    source = _inside(ROOT / "projects", entry["source"])
    files = {}
    for relative in entry["files"]:
        f = _inside(source, relative)
        # Only declared design inputs belong in an instance, never old results or credentials.
        if relative not in {"project.yaml", "DESIGN.md", "REFERENCES.md"} and not (
                Path(relative).parts[0] == "parts" and f.suffix == ".py" or
                Path(relative).parts[0] == "imports" and f.suffix.lower() in {".stl", ".step", ".stp", ".3mf"} or
                Path(relative).parts[0] == "meshes" and f.suffix.lower() in {".stl", ".obj", ".glb"}):
            raise ValueError(f"Not a module design input: {relative}")
        files[relative] = f.read_bytes()
    if "project.yaml" not in files:
        raise ValueError(f"Module '{name}' must include project.yaml")
    data = yaml.safe_load(files["project.yaml"])
    needed = set()
    for pid, spec in (data.get("parts") or {}).items():
        if imported := spec.get("import"):
            _inside(source, imported)
            if Path(imported).suffix.lower() not in {".step", ".stp", ".stl", ".3mf"}:
                raise ValueError(f"Unsupported imported model: {imported}; use STEP, STL or 3MF")
            needed.add(imported)
        else:
            needed.add(spec.get("file", f"parts/{pid}.py"))
        if spec.get("source") == "meshy":
            from .meshy import mesh_path
            mesh = mesh_path(source, pid, spec)
            try:
                relative = mesh.relative_to(source).as_posix()
            except ValueError as e:
                raise ValueError(f"Module mesh must stay inside its source: {mesh}") from e
            _inside(source, relative)
            needed.add(relative)
    if data.get("layout"):
        needed.add(data["layout"])
    # Include sibling helpers too: copying only files named by parts drops shared layout/import dependencies.
    needed.update(p.relative_to(source).as_posix() for p in (source / "parts").rglob("*.py"))
    missing = needed - files.keys()
    if missing:
        raise ValueError(f"Module '{name}' is missing source files: {', '.join(sorted(missing))}")
    return entry, source, files


def describe(name: str) -> dict:
    from .cli import review_status

    entry, source, files = _source(name)
    data = yaml.safe_load(files["project.yaml"])
    return {"id": name, **entry, "params": data.get("params") or {},
            "requirements": data.get("requirements") or [],
            "source_review": review_status(str(source)),
            "instance_status": "Not checked or reviewed; source proof is not transferred."}


def _title(text: str, title: str) -> str:
    """Replace only the name scalar so engineering notes and YAML comments survive the copy."""
    node = yaml.compose(text)
    for key, value in node.value:
        if key.value == "name" and isinstance(value, yaml.ScalarNode):
            old = text[value.start_mark.index:value.end_mark.index]
            return (text[:value.start_mark.index] + json.dumps(title, ensure_ascii=False) +
                    ("\n" if old.endswith("\n") else "") + text[value.end_mark.index:])
    raise ValueError("Module project.yaml needs a scalar name")


def instantiate(module: str, name: str, title: str, *, projects_dir: Path | None = None) -> Path:
    """Copy a declared design snapshot; the new project shares no writable files or validity claims."""
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,40}", name):
        raise ValueError("Choose 2–41 lowercase letters, numbers or underscores, starting with a letter (for example desk_arm).")
    target = (projects_dir if projects_dir is not None else ROOT / "projects") / name
    if target.exists() or target.is_symlink():
        raise ValueError(f"{target} already exists; choose another project name")
    entry, source, files = _source(module)
    contract = describe(module)
    project_text = _title(files["project.yaml"].decode("utf-8"), title)
    review_file = source / "review.json"
    provenance = {"module": module, "source": entry["source"], "source_review": contract["source_review"],
                  "source_review_record": json.loads(review_file.read_text(encoding="utf-8")) if review_file.exists() else None,
                  "source_files_sha256": {p: hashlib.sha256(content).hexdigest() for p, content in files.items()},
                  "ports": entry.get("ports") or {}, "limits": entry.get("limits") or [],
                  "instance_status": contract["instance_status"]}
    note = (f"# {entry['title']} instance\n\nCreated from `{entry['source']}`. This is an independent editable copy.\n\n"
            f"Source review: {contract['source_review']['why']}. This does not approve the new project. "
            "The historical review (including its findings) and source hashes are preserved in `module.json`.\n\n"
            "The complete assembly, wiring, purchased parts and requirements remain in `project.yaml`; "
            "`DESIGN.md` and `REFERENCES.md` are inherited source documents.\n\n"
            "## Interfaces\n\n" + "\n".join(f"- {k}: `{v}`" for k, v in provenance["ports"].items()) +
            "\n\n## Limits\n\n" + "\n".join(f"- {v}" for v in provenance["limits"]) +
            f"\n\n## Before use\n\nRun `kerf check {name}`, then `kerf build {name}` and get a new independent design review. "
            "Changing an attachment, load, material or parameter requires checking the whole assembled system. "
            "No check result, independent review or printing approval was copied.\n")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.mkdir()  # Atomic refusal if another creator won the name after our initial check.
    try:
        for relative, content in files.items():
            dest = target / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
        (target / "project.yaml").write_text(project_text, encoding="utf-8")
        (target / "module.json").write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (target / "MODULE.md").write_text(note, encoding="utf-8")
        project.load(str(target))  # A broken contract must not leave a half-created project.
    except Exception:
        shutil.rmtree(target)
        raise
    return target
