"""The gripper claw (projects/robotic_gripper_claw) bolts onto the desk robot arm's wrist. Its wrist numbers are copied
from projects/robot_arm, and its bench stand copies the arm forearm's wrist end so `kerf check` proves the fit; these
tests fail as soon as the arm changes and the claw does not follow."""
import importlib.util
from types import SimpleNamespace

import yaml
from build123d import Align, Box, Location, Pos

from kerf import catalog, geom, project

CLAW = project.PROJECTS / "robotic_gripper_claw"
ARM = project.PROJECTS / "robot_arm"


def _claw_layout():
    spec = importlib.util.spec_from_file_location("claw_layout", CLAW / "parts" / "layout.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_wrist_numbers_match_the_arm():
    mod = _claw_layout()
    arm_params = project.param_values(yaml.safe_load((ARM / "project.yaml").read_text(encoding="utf-8")))
    for k, v in mod.ARM.items():
        assert arm_params[k] == v, f"robot_arm param {k} is {arm_params[k]}, the claw assumes {v}"
    arm = project.load("robot_arm")
    a = project.shared_layout(arm)
    claw = project.load("robotic_gripper_claw")
    c = mod.layout(SimpleNamespace(**claw.params), catalog)
    assert abs(c["face"] - a["face_wr"]) < 1e-9 and abs(c["w_f"] - a["w_f"]) < 1e-9
    assert c["W"] == a["w_g"] and abs(c["out_x"] - a["wr_out_x"]) < 1e-9


def test_stand_contains_the_forearm_wrist_end():
    """Everything of the arm's forearm the claw can reach (from the rear web forward) is inside the stand, so a claw
    that clears the stand over the wrist sweep clears the forearm."""
    arm = project.build(project.load("robot_arm"), only=["forearm"])
    claw = project.build(project.load("robotic_gripper_claw"), only=["wrist_stand"])
    fa, st = arm.items["forearm"].shape, claw.items["wrist_stand"].shape
    assert fa is not None and st is not None, (arm.items["forearm"].error, claw.items["wrist_stand"].error)
    L2, p = arm.params["L2"], claw.params
    fa_local = fa.moved(Location((-L2, 0, 0)))                        # forearm frame -> stand frame (wrist axis at 0)
    x0 = p["fa_web_x"] - p["fa_web_t"] / 2 - 0.5
    region = Pos(x0, -50, -20) * Box(100, 100, 100, align=(Align.MIN, Align.MIN, Align.MIN))
    reach = fa_local & region
    assert geom.volume(reach) > 1000                                   # sanity: the plates and web are in the region
    outside = geom.volume(reach) - geom.volume(reach & st)
    assert outside < 5.0, f"{outside:.1f} mm3 of the forearm's wrist end is not in the stand: update wrist_stand.py"
