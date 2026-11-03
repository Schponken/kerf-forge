"""Box proxy joints may carry a rotation ({at, rot}) so a child can hang off an axis (a prop disc on a fuselage box)."""
from build123d import Location

from kerf import geom, proxies
from kerf.ctx import Ctx


def test_box_joint_with_rotation():
    ctx = Ctx("drone", {}, {})
    shape = proxies.build(ctx, {"proxy": "box", "size": [100, 20, 10],
                                "joints": {"plain": [50, 0, 5], "prop": {"at": [50, 0, 5], "rot": [0, 90, 0]}}})
    j = shape.joints
    assert (abs(geom.world_point(j["plain"].location, (0, 0, 0)) - geom.world_point(j["prop"].location, (0, 0, 0))) < 1e-9).all()
    z = geom.world_dir(j["prop"].location, (0, 0, 1))
    assert abs(z[0] - 1) < 1e-9 and abs(z[2]) < 1e-9          # Z turned onto +X
    assert abs(geom.world_dir(j["plain"].location, (0, 0, 1))[2] - 1) < 1e-9
