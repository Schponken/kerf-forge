"""Shared robot-arm geometry for the two yoke parts (imported by yoke_l.py and yoke_r.py)."""
from kerf import idioms

FOOT_X = (-29.0, -14.0, 7.5)          # front screw 6.5 mm from the foot end (>= 1.5 d + wall, ENGINEERING.md section 7)
FOOT_T = 6.0


def yoke(p, side):
    """Cheek + foot + gussets for side +1 (+Y) or -1 (-Y), world frame (kerf.idioms.yoke_cheek).
    Returns (body, foot bolt points)."""
    xc = p.x_sh - p.sh_out_x
    body = idioms.yoke_cheek(x0=xc - p.ds_span / 2 - 6.0, x1=xc + p.ds_span / 2 + 6.0, z0=p.z_plat1,
                             z1=p.z_sh + p.ds_W / 2 + 8.0, y_in=side * p.cheek_in, side=side, t=p.plate_t, top_r=8.0,
                             foot=(-35.0, 14.0, 20.0, FOOT_T),
                             # gussets carry the cheek tipping moment; between the foot screws, behind the servo case top
                             gussets=(-21.0, -8.5), gusset=(3.0, 24.0, 5.0), root_r=2.0, end_r=4.0)
    return body, [(x, side * (p.cheek_in - 10.0)) for x in FOOT_X]
