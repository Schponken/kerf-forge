"""Shared geometry of the portable bungee rail launcher, computed once from params + catalog so every part agrees.

Frames
- Rail frame (rear_block, sled, cradle; every section is a box proxy centred on its own length): X up the rail toward
  the nose, Y to the left, Z up from the rail's bottom face. Section k (1..4) spans x in [(k-1) SEC, k SEC], the rail
  is RAIL_W wide (|y| <= 10) and RAIL_H tall (0 <= z <= 40). Its four upper/lower side slots are at z = 10 / 30,
  the bottom slot at y = 0.
- Block frame (hinge_2 / hinge_1 / nose_block / rear_block cheeks): origin on the joint plane (the section end face)
  at the rail's bottom centre line, axes = rail frame. hinge_2 sits on the FRONT end of a section (body at x < 0),
  hinge_1 on the REAR end of the next (body at x > 0).
- World (rear_foot, the root): ground z = 0, X forward horizontally. The rail pivots on the rear foot about a Y axis,
  raised RAIL_DEG at home.

Strands: n latex strands run from the sled's tow hooks (z = Z_TOP) forward over the rail, half round the nose pulley
(pitch radius R_P about (X_P, Z_MID)) and back under the rail (z = Z_BOT) to the anchor's hooks on section 2.
The anchor sits in notch 1..10 (NOTCH_1 nearest the nose, NOTCH_PITCH apart); a higher notch stretches every strand
more. Strand lengths (centre line) at the end of the stroke and cocked are end_len(n) / start_len(n).
"""
import math

from kerf import catalog

RAIL = "motion.vslot_2040"
WHEEL = "motion.vwheel_delrin_solid"
QR = "motion.qr_pin_6mm"
LATEX = "motion.latex_tubing"
TUBE = "rods.alu_tube_20x1_5"

N_MAX = 6                 # strand grooves / hooks (6 x commodity latex reaches 15 m/s with 2 kg, DESIGN.md)
STRAND_PITCH = 10.5       # mm between strands: tubing OD 7.94 + a 2.5 mm groove flange
LUG_T = 8.0               # fold-joint lug thickness; the QR pin runs through four lugs (aft, fwd, aft, fwd from the bottom)
LUGS_AFT = ((-9.0, -1.0), (24.6, 32.6))    # lugs of the block on the aft section's front end (rail z)
LUGS_FWD = ((-0.6, 7.4), (33.0, 41.0))     # lugs of the block on the next section's rear end; stack -9..41 = 50 = QR grip
TNUT_GRIP = 6.0           # printed wall under an M5 tee-nut screw head: 6 + 5..6.5 into the nut = a 12 mm screw


def layout(p, cat):
    r = catalog.get(RAIL)
    W, H = float(r["W"]), float(r["H"])
    wh = catalog.get(WHEEL)
    wheel_y = W / 2 + float(wh["wheel_centre_to_face"])         # 20: wheel axle 10 mm outside the side face
    wheel_z = 30.0                                              # upper side slot centre
    sec = float(p.sec_len)
    z_mid = H / 2
    R_P = float(p.pulley_r)
    x_p = 4 * sec + float(p.pulley_dx)
    z_top, z_bot = z_mid + R_P, z_mid - R_P
    ys = [(i - (N_MAX - 1) / 2) * STRAND_PITCH for i in range(N_MAX)]

    # sled: origin on the rail top centre line under the sled's middle; home = cocked
    x_s0 = float(p.sled_home_x)
    sled_half = float(p.sled_len) / 2
    tow_dx = sled_half - 5.0                                    # tow hooks 5 mm behind the bumper face
    x_t_home = x_s0 + tow_dx
    brake_x = float(p.brake_x)                               # bumper meets the brake cord here
    x_t_end = brake_x - 5.0
    stroke = x_t_end - x_t_home
    travel_max = brake_x - (x_s0 + sled_half) + float(p.brake_stop_max)

    # anchor notches on section 2 (rail x), notch 1 nearest the nose
    notch_x = [float(p.notch_1_x) - i * float(p.notch_pitch) for i in range(10)]

    def end_len(notch):
        return (x_p - x_t_end) + math.pi * R_P + (x_p - notch_x[notch - 1])

    def start_len(notch):
        return end_len(notch) + stroke

    # rail pivot on the rear foot, and the bipod legs reaching the ground
    th = math.radians(float(p.rail_deg))
    pv = (float(p.pivot_x), float(p.pivot_z))             # rail frame
    h_pv = float(p.pivot_h)                                  # world height of the pivot axis

    def world_z(x, z):
        dx, dz = x - pv[0], z - pv[1]
        return h_pv + dx * math.sin(th) + dz * math.cos(th)

    splay = math.radians(float(p.leg_splay))
    sock_y = W / 2 + float(p.sock_off)                       # socket axis |y| at the socket bottom
    sock_z = float(p.sock_z)                                 # socket bottom (rail frame z)
    foot_t = float(p.foot_t)                                 # leg end to the foot's ground face
    # leg axis (rail frame) points down-out: (0, +-sin s, -cos s); in the world its z-rate is -cos s cos th
    z0 = world_z(float(p.bipod_x), sock_z)
    leg_len = (z0 - foot_t * math.cos(splay) * math.cos(th)) / (math.cos(splay) * math.cos(th))

    return {
        "W": W, "H": H, "SEC": sec, "Z_MID": z_mid, "R_P": R_P, "X_P": x_p, "Z_TOP": z_top, "Z_BOT": z_bot,
        "STRAND_Y": ys, "N_MAX": N_MAX, "STRAND_PITCH": STRAND_PITCH,
        "WHEEL_Y": wheel_y, "WHEEL_Z": wheel_z, "WHEEL_OD": float(wh["od"]), "WHEEL_W": float(wh["width"]),
        "X_S0": x_s0, "SLED_HALF": sled_half, "TOW_DX": tow_dx, "X_T_HOME": x_t_home, "X_T_END": x_t_end,
        "STROKE": stroke, "TRAVEL_MAX": travel_max,
        "NOTCH_X": notch_x, "END_LEN": [end_len(n) for n in range(1, 11)],
        "START_LEN": [start_len(n) for n in range(1, 11)],
        "LUG_T": LUG_T, "LUGS_AFT": LUGS_AFT, "LUGS_FWD": LUGS_FWD, "LUG_STACK": LUGS_FWD[1][1] - LUGS_AFT[0][0],
        "LEG_LEN": leg_len, "SOCK_Y": sock_y, "TNUT_GRIP": TNUT_GRIP,
    }
