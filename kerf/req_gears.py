"""Gear tooth bending (audit ENG-20a): the Lewis equation for a printed spur gear at the driving actuator's stall
torque, so a pair from kerf.drives.spur_pair is proven, not assumed.

    sigma = Ft / (b * m * Y),   Ft = T / r,  r = m * z / 2

Y is the Lewis form factor for 20-degree full-depth involute teeth (Shigley's Mechanical Engineering Design, Table
14-2, Y = pi * y), interpolated in z. Ft is taken at the pitch circle of the gear the torque `torque_nmm` acts on
(`z_driver`); the tooth check is done on the gear with the smaller Y (fewer teeth), which carries the same Ft.
Teeth of a gear printed flat bend in the layer plane, so the allowable is the material's xy strength / sf
(direction z when the gear prints on edge).

    - {id: yaw_teeth, check: gear_bending, module: 1.5, z_driver: 36, z_driven: 24, width: 8, torque_nmm: 922,
       material: PETG, sf: 3, direction: xy}
"""
from __future__ import annotations

import numpy as np

from .requirements import _ev, _strength, check

# Shigley Table 14-2: Lewis form factor Y, 20 deg pressure angle, full-depth teeth, diametral-pitch independent
LEWIS_Z = [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 26, 28, 30, 34, 38, 43, 50, 60, 75, 100, 150, 300, 400]
LEWIS_Y = [0.245, 0.261, 0.277, 0.290, 0.296, 0.303, 0.309, 0.314, 0.322, 0.328, 0.331, 0.337, 0.346, 0.353, 0.359,
           0.371, 0.384, 0.397, 0.409, 0.422, 0.435, 0.447, 0.460, 0.472, 0.480]


def lewis_y(z: int) -> float:
    if z < LEWIS_Z[0]:
        raise ValueError(f"Lewis form factor table starts at 12 teeth (got {z}): undercut pinion, redesign")
    return float(np.interp(z, LEWIS_Z, LEWIS_Y))


def lewis_stress(module, z_driver, z_driven, width, torque_nmm) -> float:
    ft = float(torque_nmm) / (float(module) * float(z_driver) / 2.0)
    y = min(lewis_y(int(z_driver)), lewis_y(int(z_driven)))
    return ft / (float(width) * float(module) * y)


@check("gear_bending")
def gear_bending(proj, asm, module, z_driver, z_driven, width, torque_nmm, material="PETG", sf=3.0, direction="xy"):
    """Lewis tooth-root bending stress at `torque_nmm` (an actuator's stall) vs material strength / sf."""
    p = proj.params
    m, z1, z2, b, t = (_ev(v, p) for v in (module, z_driver, z_driven, width, torque_nmm))
    s = lewis_stress(m, int(z1), int(z2), b, t)
    allow = _strength(material, direction) / float(sf)
    return {"ok": s <= allow, "value": round(s, 2), "limit": round(allow, 2),
            "detail": f"Lewis tooth bending (MPa): Ft {t / (m * z1 / 2):.1f} N at the {int(z1)} T pitch circle, "
                      f"b {b:g} mm, m {m:g}, Y {min(lewis_y(int(z1)), lewis_y(int(z2))):.3f}; {material} {direction} / SF {sf}"}
