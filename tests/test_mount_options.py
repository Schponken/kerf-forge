"""motor_mount counterbore depth and the stack proxy's board size (engine additions made for the fpv_5in eval)."""
import pytest
from build123d import Location

from kerf import catalog, iface, proxies
from kerf.ctx import Ctx


def test_motor_mount_counterbore_sets_grip():
    ctx = Ctx("arm", {})
    iface.motor_mount(ctx, "drone.motors.2207_1855kv_6s", Location((0, 0, -11), (180, 0, 0)), "m", plate_t=11,
                      kind="counterbore", counterbore_depth=4.0)
    assert len(ctx.sites) == 4 and all(s.grip == pytest.approx(7.0) for s in ctx.sites)
    # site sits on the counterbore floor, 4 mm above the bottom face
    assert all(abs(s.loc.position.Z - (-7.0)) < 1e-6 for s in ctx.sites)


def test_stack_proxy_uses_largest_board():
    e = catalog.get("drone.stacks.fc_30_5")
    big = max(max(v[0], v[1]) for v in e["board_size"].values())
    s = proxies.build(Ctx("stack", {}), {"catalog": "drone.stacks.fc_30_5", "proxy": "stack"})
    bb = s.bounding_box()
    assert bb.size.X == pytest.approx(big) and bb.size.Z == pytest.approx(e["height"])
