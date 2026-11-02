from evals.common import base_checks, need_req


def accept(rep, proj_dir):
    fails = []
    base_checks(rep, fails)
    if rep.get("mode") != "check":
        fails.append(f"run it in Check it mode (`kerf run check_shelf_bracket --mode check`), not {rep.get('mode')!r}")
    part = rep.get("parts", {}).get("bracket")
    if not part or not (proj_dir / "imports" / "shelf_bracket.step").exists():
        fails.append("the bracket must be the imported model imports/shelf_bracket.step")
    elif part.get("solids") != 1 or not part.get("watertight", True):
        fails.append("the imported bracket must be one closed solid")
    need_req(rep, "shelf_load", "fea_static", fails)
    need_req(rep, "mass", "mass_max", fails)
    return fails
