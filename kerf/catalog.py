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
    return json.loads(CATALOG.read_text())


def get(path: str) -> dict:
    """get("servos.MG996R") -> the entry dict. Raises CatalogError with suggestions if missing."""
    node = load()
    parts = path.split(".")
    for i, key in enumerate(parts):
        if not isinstance(node, dict) or key not in node:
            options = sorted(k for k in node.keys() if not k.startswith("_")) if isinstance(node, dict) else []
            raise CatalogError(f"catalog has no '{'.'.join(parts[:i + 1])}'. Options here: {options}")
        node = node[key]
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
        if path and any(isinstance(v, (int, float)) for v in node.values()) and "source" not in node:
            out.append(path)
        for k, v in node.items():
            if not k.startswith("_") and isinstance(v, dict):
                out += unsourced(v, f"{path}.{k}" if path else k)
    return out
