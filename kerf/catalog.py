"""Hardware catalog: real, sourced dimensions for purchased parts. Every mating feature is generated from here."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = Path(os.environ.get("KERF_CATALOG", ROOT / "catalog" / "hardware.json"))


class CatalogError(KeyError):
    pass


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


_USED: set | None = None


def track():
    """Start recording every path passed to get() (project builds: the project's catalog dependencies)."""
    global _USED
    _USED = set()


def used() -> set:
    return set(_USED or ())


def deps_hash(paths) -> str:
    """Hash of just these catalog entries (a missing entry hashes as missing), so an edit elsewhere in the catalog
    does not change a project's fingerprint."""
    import hashlib
    h = hashlib.sha256()
    for p in sorted(paths):
        try:
            v = _get(p)
        except CatalogError:
            v = "<missing>"
        h.update(p.encode())
        h.update(json.dumps(v, sort_keys=True, default=str).encode())
    return h.hexdigest()


def get(path: str) -> dict:
    """get("servos.MG996R") -> the entry dict. Keys may contain dots ("screws.M2.5"): the longest matching key wins.
    Raises CatalogError with the options available at the failing level."""
    if _USED is not None:
        _USED.add(path)
    return _get(path)


def _get(path: str) -> dict:
    node, parts, i = load(), path.split("."), 0
    while i < len(parts):
        if not isinstance(node, dict):
            raise CatalogError(f"catalog '{'.'.join(parts[:i])}' is a value, not a section")
        for j in range(len(parts), i, -1):
            key = ".".join(parts[i:j])
            if key in node:
                node, i = node[key], j
                break
        else:
            options = sorted(k for k in node.keys() if not k.startswith("_"))
            raise CatalogError(f"catalog has no '{'.'.join(parts[:i + 1])}'. Options here: {options}")
    return node


def num(entry: dict, *keys: str, default=None) -> float:
    """First numeric field found among keys (catalog entries may nest value under {'value': x})."""
    for k in keys:
        if k in entry:
            v = entry[k]
            if isinstance(v, dict) and "value" in v:
                v = v["value"]
            if isinstance(v, (int, float)):
                return float(v)
    if default is not None:
        return float(default)
    raise CatalogError(f"none of {keys} found in catalog entry with keys {sorted(entry)}")


def fingerprint() -> str:
    import hashlib
    return hashlib.sha256(CATALOG.read_bytes()).hexdigest()[:16]


def unsourced(node=None, path="") -> list[str]:
    """Paths of catalog entries that hold numbers but no 'source'."""
    node = load() if node is None else node
    out = []
    if isinstance(node, dict):
        if "source" in node:
            return out  # an entry; nested dicts inside it (e.g. mount_pattern) are covered by its source
        if path and any(isinstance(v, (int, float)) for v in node.values()):
            out.append(path)
        for k, v in node.items():
            if not k.startswith("_") and isinstance(v, dict):
                out += unsourced(v, f"{path}.{k}" if path else k)
    return out
