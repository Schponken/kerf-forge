"""docs/ARCHITECTURE.md and docs/ENGINEERING.md must keep up with the engine: every module, requirement check, CLI
command and project.yaml key the code reads is documented. A new engine feature without docs fails here."""
import re
from pathlib import Path

from kerf import requirements

ROOT = Path(__file__).resolve().parent.parent
ARCH = (ROOT / "docs/ARCHITECTURE.md").read_text(encoding="utf-8")
ENG = (ROOT / "docs/ENGINEERING.md").read_text(encoding="utf-8")
SRC = {p: p.read_text(encoding="utf-8") for p in (ROOT / "kerf").glob("*.py")}


def test_every_module_in_package_map():
    missing = [p.name for p in SRC if p.name != "__init__.py" and f"`kerf/{p.name}`" not in ARCH]
    assert not missing, f"add to the ARCHITECTURE.md package map: {missing}"


def test_every_requirement_check_documented():
    rows = set(re.findall(r"^\| `(\w+)` \|", ARCH, re.M))
    missing = set(requirements.REGISTRY) - rows
    assert not missing, f"add to the ARCHITECTURE.md requirement table: {missing}"


def test_every_cli_command_documented():
    subs = set(re.findall(r'add_parser\("([\w-]+)"', SRC[ROOT / "kerf/cli.py"]))
    row = next(l for l in ARCH.splitlines() if l.startswith("| `kerf/cli.py`"))
    assert all(re.search(rf"\b{re.escape(s)}\b", row) for s in subs), (subs, row)


def test_every_yaml_key_documented():
    keys = set()
    for src in SRC.values():
        keys |= set(re.findall(r'(?:\bspec|\bdata|\["assembly"\])(?:\.get\(|\[)"([a-z_]+)"', src))
    internal = {"min_engage"}  # screw_spec dict key read as spec["min_engage"], not a yaml key
    missing = sorted(k for k in keys - internal if not re.search(rf"\b{k}\b", ARCH))
    assert not missing, f"project.yaml keys read by the engine but not in ARCHITECTURE.md: {missing}"


def test_engineering_rules_name_the_checks_that_enforce_them():
    for name in ("fea_static", "static_torque", "cantilever_stress", "channel_clear", "cg", "tip_over", "prop_clearance"):
        assert name in requirements.REGISTRY and re.search(rf"\b{name}\b", ENG), name
    assert "pin_hole" in ENG and "load_axis" in ENG
