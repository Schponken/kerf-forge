"""The kerf skill is the workflow a fresh session follows from a one-paragraph description. Keep it true to the
engine: every requirement check is listed, every helper and command it names exists, every file it points to exists,
and the workflow stages appear in order."""
import inspect
import re
from pathlib import Path

from kerf import drives, features, iface, requirements

ROOT = Path(__file__).resolve().parent.parent
SKILL = (ROOT / ".claude/skills/kerf/SKILL.md").read_text(encoding="utf-8")


def _section(title):
    return SKILL.split(title, 1)[1].split("\n\n", 1)[0]


def test_every_requirement_check_listed():
    listed = set(re.findall(r"^\| `(\w+)` \|", SKILL, re.M))
    assert set(requirements.REGISTRY) <= listed, f"missing from the skill toolbox: {set(requirements.REGISTRY) - listed}"
    assert listed <= set(requirements.REGISTRY), f"skill lists checks that don't exist: {listed - set(requirements.REGISTRY)}"


def test_named_helpers_exist():
    for title, mod in (("Interfaces (`kerf/iface.py`", iface), ("Drives (`kerf/drives.py`)", drives),
                       ("Features (`kerf/features.py`)", features)):
        names = set(re.findall(r"`(\w+)`", _section(title)))
        public = {n for n, _ in inspect.getmembers(mod, inspect.isfunction)}
        kinds = set(iface.KINDS_MALE + iface.KINDS_FEMALE + iface.PIN_FITS) | {"lengths"}  # option words, not functions
        missing = names - public - kinds
        assert not missing, f"{mod.__name__} has no {missing}"
    for mod_name, fn in re.findall(r"`(features|iface|drives)\.(\w+)", SKILL):
        assert hasattr({"features": features, "iface": iface, "drives": drives}[mod_name], fn), f"{mod_name}.{fn}"


def test_commands_and_files_exist():
    cli = (ROOT / "kerf/cli.py").read_text(encoding="utf-8")
    subs = set(re.findall(r'add_parser\("([\w-]+)"', cli))
    for cmd in re.findall(r"`(?:\.venv/bin/)?kerf ([\w-]+)", SKILL):
        assert cmd in subs, f"kerf {cmd} is not a command"
    for agent in ("design-researcher", "part-designer", "design-reviewer"):
        assert agent in SKILL and (ROOT / f".claude/agents/{agent}.md").exists()
    for f in re.findall(r"`((?:docs|references|catalog|kerf)/[\w./-]+\.(?:md|json|py))`", SKILL):
        assert (ROOT / f).exists(), f


def test_workflow_in_order():
    steps = ["## 0. Research", "## 1. Understand and size", "## 2. Contract", "## 3. Parts in parallel",
             "## 4. Integrate", "## 5. Strength, then detail", "## 6. Build and look", "## 7. Independent review",
             "## 8. Deliver"]
    pos = [SKILL.index(s) for s in steps]
    assert pos == sorted(pos)
    for must in ("REFERENCES.md", "DESIGN.md", "project.yaml", "fea_static", "kerf build", "review.json", "bom.md"):
        assert must in SKILL, must
