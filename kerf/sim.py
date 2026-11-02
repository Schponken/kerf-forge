"""Motion simulation in MuJoCo (`kerf simulate <p>`, requirement kinds in kerf/req_motion.py).

The model is the URDF Kerf exports (kerf/urdf.py): one rigid body per link with the mass, centre of mass and inertia
of its parts (printed: the infill/perimeter estimate of `kerf check`; purchased: catalog weight), every moving joint
with its range, and geared joints (`<mimic>`) tied to the joint they follow by a MuJoCo joint equality.

Servos: a joint whose parent item is a catalog servo (or one named in `actuators:`) is driven by a hobby-servo model:
a DC motor behind a gearbox, so its torque is limited by the catalog stall torque falling linearly to zero at the
no-load speed (catalog `speed_s_per_60`): tau in [-T_s (1 + w / w0), T_s (1 - w / w0)], clipped to +-T_s. Its controller
is proportional: full stall torque at `band_deg` (default 3 deg) of position error, critically damped, and its set
point moves toward the commanded angle no faster than w0, as a hobby servo does.

Contact: the URDF meshes do not collide here (Kerf's own sweep checks prove the clearances); contacts are only the
ones a requirement declares (gripper pads and the held object; a drop's hit point on the floor).
SI units inside (m, kg, s, rad, N); poses and results for people in degrees / mm.
"""
from __future__ import annotations

import math
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import assembly as A, catalog

G = 9.80665
DT = 0.0005                    # s: 2 kHz; the servo loop and the grip contacts are resolved at this step
BAND_DEG = 3.0                 # servo proportional band: full torque at this position error


def servo_limits(entry: dict) -> tuple[float, float]:
    """(stall torque N*m, no-load speed rad/s) of a catalog servo, both at its catalog stall_voltage."""
    tau = catalog.num(entry, "stall_torque_kgcm", "stall_torque_kg_cm", "stall_torque") * G / 100.0
    w0 = (math.pi / 3.0) / catalog.num(entry, "speed_s_per_60")
    return tau, w0


@dataclass
class Model:
    """The project's URDF as a MuJoCo spec (recompiled per scenario) plus what the scenarios need."""
    urdf_xml: str
    joints: list                       # moving joint names
    kind: dict                         # joint -> "revolute" | "prismatic"
    servos: dict                       # joint -> {"item", "catalog", "stall_nm", "w0"}
    mimic: dict                        # follower joint -> (lead joint, ratio)
    link_of: dict                      # item -> link (body) name
    origin_mm: dict                    # link -> link-frame origin in the assembly frame at the zero pose (mm)
    root: str = ""
    point_mm: dict = field(default_factory=dict)   # "item.label" -> zero-pose assembly-frame point (mm), on demand
    tmp: object = None

    def spec(self, servos=None, scale: dict | None = None, band_deg: float = BAND_DEG):
        """A fresh MjSpec of the URDF with gravity, the gear ties and a position actuator on every servo joint
        (only those in `servos` when given; `scale` multiplies a joint's stall torque, e.g. a derated grip)."""
        import mujoco
        sp = mujoco.MjSpec.from_string(self.urdf_xml)
        sp.compiler.fusestatic = False                # bodies added below (payload) keep their own frame
        sp.option.gravity = [0.0, 0.0, -G]
        sp.option.timestep = DT
        sp.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
        for g in sp.geoms:                         # meshes never collide here (see module doc)
            g.contype, g.conaffinity = 0, 0
        for f, (lead, ratio) in self.mimic.items():
            sp.add_equality(type=mujoco.mjtEq.mjEQ_JOINT, name1=f, name2=lead,
                            data=[0.0, ratio, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        for j, sv in self.servos.items():
            if servos is not None and j not in servos:
                continue
            stall = sv["stall_nm"] * (scale or {}).get(j, 1.0)
            a = sp.add_actuator(name=f"servo_{j}", target=j, trntype=mujoco.mjtTrn.mjTRN_JOINT)
            a.set_to_position(kp=stall / math.radians(band_deg), dampratio=1.0)
            a.forcelimited = mujoco.mjtLimited.mjLIMITED_TRUE
            a.forcerange = [-stall, stall]
            a.ctrllimited = mujoco.mjtLimited.mjLIMITED_FALSE
        return sp

    def local(self, ref: str) -> tuple[str, np.ndarray]:
        """(body name, point in that body's frame, m) of a joint reference 'item.label'."""
        item = ref.split(".", 1)[0]
        link = self.link_of[item]
        return ("world" if link == self.root else link), (np.asarray(self.point_mm[ref]) - np.asarray(self.origin_mm[link])) / 1000.0

    def q(self, joint: str, value: float) -> float:
        return math.radians(value) if self.kind[joint] == "revolute" else value / 1000.0

    def full_pose(self, pose: dict | None) -> dict:
        """Joint values (deg / mm) for every joint: the pose's, followers from their lead, the rest 0."""
        out = {j: 0.0 for j in self.joints}
        out.update({k: float(v) for k, v in (pose or {}).items()})
        for f, (lead, ratio) in self.mimic.items():
            if f not in (pose or {}):
                out[f] = ratio * out[lead]
        return out


def load(proj, asm=None, masses: dict | None = None, actuators: dict | None = None, refs=()) -> Model:
    """Export the project's URDF (kerf/urdf.py) to a temp folder and wrap it for MuJoCo. `actuators` maps a joint to a
    servo item or a catalog key when the servo is not the joint's parent item; `refs` are joint references
    ('item.label') whose positions the scenarios need."""
    from . import urdf
    asm = asm or A.plan(proj)
    key = (id(asm), tuple(sorted((masses or {}).items())), tuple(sorted((actuators or {}).items())))
    cache = proj.__dict__.setdefault("_sim_models", {})
    if key in cache:
        m = cache[key]
    else:
        tmp = tempfile.TemporaryDirectory(prefix="kerf_sim_")
        out = Path(tmp.name)
        r = urdf.write(proj, out, asm, masses)
        if any(sev == "error" for sev, _, _ in r["findings"]):
            raise ValueError(f"URDF invalid: {r['findings']}")
        _, _, info = urdf.build(proj, asm, masses)
        xml = (out / r["path"]).read_text(encoding="utf-8")
        tag = f'<mujoco><compiler meshdir="{out}/" strippath="false" discardvisual="true" balanceinertia="false"/></mujoco>'
        xml = xml.replace(f'<robot name="{proj.dir.name}">', f'<robot name="{proj.dir.name}">{tag}', 1)
        edges = {e.name: e for e in asm.movable}
        mimic = {s["joint"]: (s["follows"], float(s.get("ratio", 1.0)))
                 for s in (proj.data["assembly"].get("sweeps") or []) if "joint" in s and "follows" in s}
        servos = {}
        for name, e in edges.items():
            src = (actuators or {}).get(name, e.parent)
            it = proj.items.get(src)
            cat = it.spec.get("catalog", "") if it is not None else src
            if str(cat).startswith("servos."):
                stall, w0 = servo_limits(catalog.get(cat))
                servos[name] = {"item": src if it is not None else None, "catalog": cat, "stall_nm": stall, "w0": w0}
        m = Model(xml, list(edges), {n: e.kind for n, e in edges.items()}, servos, mimic,
                  dict(info["link_of"]), dict(info["origin_mm"]), root=asm.root, tmp=tmp)
        cache[key] = m
    need = [r for r in refs if r not in m.point_mm]
    if need:
        A.solve(asm, {e.name: 0.0 for e in asm.movable})
        try:
            for ref in need:
                item, label = ref.split(".", 1)
                p = proj.items[item].shape.joints[label].location.position
                m.point_mm[ref] = [p.X, p.Y, p.Z]
        finally:
            A.solve(asm)
    return m


# ---------------------------------------------------------------------------------------------------------- servos

class Servos:
    """The hobby-servo model of the driven joints of a model compiled from Model.spec(): a MuJoCo position actuator
    (gain stall / band, critically damped, so the damping is integrated implicitly and a light link stays stable)
    whose set point moves toward the target at no more than the no-load speed, and whose force range follows the
    motor's torque-speed line every step."""

    def __init__(self, M: Model, mj, data):
        self.items = []
        for j, s in M.servos.items():
            try:
                aid = mj.actuator(f"servo_{j}").id
            except KeyError:
                continue
            jid = mj.joint(j).id
            self.items.append({"joint": j, "aid": aid, "qadr": mj.jnt_qposadr[jid], "dadr": mj.jnt_dofadr[jid],
                               "stall": float(mj.actuator_forcerange[aid][1]), "w0": s["w0"]})
        self.ref, self.target, self.peak = {}, {}, {}
        self.gain = 1.0                                   # torque available x gain (a grip ramps its squeeze up)

    def command(self, targets_rad: dict, data, jump: bool = False):
        for s in self.items:
            j = s["joint"]
            self.target[j] = targets_rad.get(j, self.target.get(j, float(data.qpos[s["qadr"]])))
            if jump or j not in self.ref:
                self.ref[j] = self.target[j] if jump else float(data.qpos[s["qadr"]])

    def step(self, mj, data):
        import mujoco
        for s in self.items:
            j = s["joint"]
            lim = s["w0"] * mj.opt.timestep
            self.ref[j] += float(np.clip(self.target[j] - self.ref[j], -lim, lim))
            w = float(data.qvel[s["dadr"]])
            hi = self.gain * s["stall"] * min(1.0, max(0.0, 1.0 - w / s["w0"]))       # motor torque-speed line
            lo = -self.gain * s["stall"] * min(1.0, max(0.0, 1.0 + w / s["w0"]))
            mj.actuator_forcerange[s["aid"]] = [lo, hi]
            data.ctrl[s["aid"]] = self.ref[j]
        mujoco.mj_step(mj, data)
        for s in self.items:
            self.peak[s["joint"]] = max(self.peak.get(s["joint"], 0.0), abs(float(data.actuator_force[s["aid"]])) / s["stall"])


def _set_pose(M: Model, mj, data, pose_deg: dict):
    import mujoco
    have = {mj.joint(i).name for i in range(mj.njnt)}
    for j, v in M.full_pose(pose_deg).items():
        if j in have:                                     # (joints welded by _lock are gone)
            data.qpos[mj.jnt_qposadr[mj.joint(j).id]] = M.q(j, v)
    mujoco.mj_forward(mj, data)


def _lock(sp, M: Model, keep: set, pose: dict):
    """Weld every joint not in `keep` at its pose value: the joint is removed and its body turned (or slid) to that
    value, so the locked arm is truly rigid (a joint equality is a soft constraint and lets a loaded arm flex by
    degrees). A joint geared to a kept joint stays, held by its gear tie."""
    import mujoco
    full = M.full_pose(pose)
    tied = {e.name1 for e in sp.equalities if e.name2 in keep} | {e.name2 for e in sp.equalities if e.name1 in keep}
    for e in list(sp.equalities):                 # gear ties between two locked joints go with the joints
        if e.name1 not in keep and e.name2 not in keep:
            sp.delete(e)
    owner = {jt.name: b for b in sp.bodies for jt in b.joints}
    for j in M.joints:
        if j in keep or j in tied:
            continue
        jt, b = sp.joint(j), owner[j]
        ax = np.asarray(jt.axis, float) / np.linalg.norm(jt.axis)
        if M.kind[j] == "revolute":
            r, out = np.zeros(4), np.zeros(4)
            mujoco.mju_axisAngle2Quat(r, ax, M.q(j, full[j]))
            mujoco.mju_mulQuat(out, np.asarray(b.quat, float), r)     # joint axis through the body origin (kerf/urdf.py)
            b.quat = out.tolist()
        else:
            R = np.zeros(9)
            mujoco.mju_quat2Mat(R, np.asarray(b.quat, float))
            b.pos = (np.asarray(b.pos, float) + R.reshape(3, 3) @ ax * M.q(j, full[j])).tolist()
        sp.delete(jt)


# ---------------------------------------------------------------------------------------------------------- motion

def move(M: Model, start: dict, end: dict, max_s: float, payload_g: float = 0.0, payload_at: str | None = None,
         band_deg: float = BAND_DEG, tol_deg: float | None = None) -> dict:
    """Hold `start`, then command every servo to `end`. Returns the time after which every driven joint stays within
    tol (default band_deg) of its target, the peak torque of each servo as a fraction of its stall torque, and the
    final error of each joint."""
    import mujoco
    tol = math.radians(tol_deg if tol_deg is not None else band_deg)
    sp = M.spec(band_deg=band_deg)
    if payload_g and payload_at:
        link, p = M.local(payload_at)
        b = sp.body(link).add_body(name="payload", pos=p.tolist(), ipos=[0, 0, 0], explicitinertial=True,
                                   mass=payload_g / 1000.0, inertia=[1e-7, 1e-7, 1e-7])   # ipos: MuJoCo copies pos otherwise
        b.add_geom(type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[0.005, 0, 0], contype=0, conaffinity=0, mass=0)
    mj = sp.compile()
    data = mujoco.MjData(mj)
    _set_pose(M, mj, data, start)
    sv = Servos(M, mj, data)
    a, b = M.full_pose(start), M.full_pose(end)
    sv.command({j: M.q(j, a[j]) for j in M.servos}, data, jump=True)
    for _ in range(int(0.5 / DT)):                       # settle at the start pose under gravity
        sv.step(mj, data)
    sv.peak.clear()
    goal = {j: M.q(j, b[j]) for j in M.servos}
    sv.command(goal, data)
    T = max(2.0 * max_s, max_s + 1.0)
    n = int(T / DT)
    last_out = 0.0
    for i in range(n):
        sv.step(mj, data)
        err = max(abs(float(data.qpos[s["qadr"]]) - goal[s["joint"]]) for s in sv.items)
        if err > tol:
            last_out = (i + 1) * DT
    final = {s["joint"]: round(math.degrees(float(data.qpos[s["qadr"]]) - goal[s["joint"]]), 2) for s in sv.items}
    reached = last_out < T - 0.25                    # inside tol for at least the last 0.25 s
    return {"time_s": round(last_out, 3) if reached else None, "peak_fraction": {k: round(v, 3) for k, v in sv.peak.items()},
            "final_error_deg": final, "sim_s": T}


def hold(M: Model, pose: dict | None = None, seconds: float = 1.0, payload_g=0.0, payload_at=None) -> dict:
    """Hold a pose: the sag of each joint and its servo's torque as a fraction of stall (`kerf simulate`)."""
    r = move(M, pose or {}, pose or {}, seconds / 2.0, payload_g, payload_at)
    return r


# ---------------------------------------------------------------------------------------------------------- grip

def _quat_z_to(n):
    """Quaternion (w, x, y, z) turning +Z onto unit vector n."""
    n = np.asarray(n, float) / np.linalg.norm(n)
    z = np.array([0.0, 0.0, 1.0])
    c = float(np.dot(z, n))
    if c < -0.999999:
        return [0.0, 1.0, 0.0, 0.0]
    ax = np.cross(z, n)
    q = np.array([1.0 + c, *ax])
    return (q / np.linalg.norm(q)).tolist()


def _rot_to_quat(R):
    import mujoco
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, np.asarray(R, float).reshape(9))
    return q.tolist()


def grip(M: Model, joint: str, pads: list, mass_g: float, mu: float, width_mm: float, size_mm=None,
         pad_t_mm=(6.0, 6.0), pad_mm=(8.0, 6.0), pose: dict | None = None, torque_fraction: float = 0.5,
         shake_g: float = 1.0, shake_hz: float = 2.0, cycles: float = 2.0) -> dict:
    """An object of `mass_g` and `width_mm` squeezed between two jaw pads by the servo on `joint` (at
    torque_fraction of stall), the rest of the arm locked at `pose`, then shaken at `shake_g` x g (sinusoid,
    `shake_hz`) along each of three axes (the squeeze direction and two across it), on top of gravity. A shake of
    the arm's base is the same as changing gravity for everything on it, which is how it is applied here.
    pads: [moving jaw point, fixed jaw point] as joint references (the pad is a box `pad_mm` across and `pad_t_mm`
    thick along the squeeze, centred on the point); friction mu at both pads.
    Returns the grip angle, squeeze force, the worst slip of the object on the fixed jaw across the squeeze (mm) per
    shake axis, and the hand estimate of the mass that would just slip."""
    import mujoco
    if M.kind.get(joint) != "revolute":
        raise ValueError(f"grip_hold: '{joint}' must be a revolute joint")
    if joint not in M.servos:
        raise ValueError(f"grip_hold: '{joint}' has no servo (its parent item is not a catalog servo; name one in actuators)")
    pose = dict(pose or {})
    mov, fix = pads
    (lm, pm), (lf, pf) = M.local(mov), M.local(fix)
    tm, tf = pad_t_mm[0] / 1000.0, pad_t_mm[1] / 1000.0
    w = width_mm / 1000.0
    # 1. the grip angle where the pad faces are `width` apart
    sp = M.spec()
    sp.body(lm).add_site(name="pad_m", pos=pm.tolist())
    sp.body(lf).add_site(name="pad_f", pos=pf.tolist())
    mj = sp.compile()
    data = mujoco.MjData(mj)
    jid = mj.joint(joint).id
    lo_r, hi_r = mj.jnt_range[jid]

    def gap(qv):
        _set_pose(M, mj, data, {**pose, joint: math.degrees(qv) if M.kind[joint] == "revolute" else qv * 1000})
        d = data.site("pad_m").xpos - data.site("pad_f").xpos
        return float(np.linalg.norm(d)) - (tm + tf) / 2.0, d.copy()

    ga, gb = gap(lo_r)[0], gap(hi_r)[0]
    if not (min(ga, gb) <= w <= max(ga, gb)):
        raise ValueError(f"grip_hold: the pads are {ga * 1000:.1f}..{gb * 1000:.1f} mm apart over '{joint}' range; "
                         f"a {width_mm} mm object does not fit")
    a, b = (lo_r, hi_r) if ga < gb else (hi_r, lo_r)          # a: closed end
    closed = a
    for _ in range(60):
        mid = (a + b) / 2
        if gap(mid)[0] < w:
            a = mid
        else:
            b = mid
    q_hold = (a + b) / 2
    _, d = gap(q_hold)
    n = d / np.linalg.norm(d)                                  # fixed pad -> moving pad, world
    pm_w, pf_w = data.site("pad_m").xpos.copy(), data.site("pad_f").xpos.copy()
    Rm, Rf = data.body(lm).xmat.reshape(3, 3).copy(), data.body(lf).xmat.reshape(3, 3).copy()
    centre = pf_w + n * (tf / 2 + w / 2)
    # squeeze force by hand: servo torque / the lever from the joint axis square to the squeeze line at the pad
    ax_w = data.xaxis[jid].copy()
    anchor = data.xanchor[jid].copy()
    lever = abs(float(np.dot(np.cross(pm_w - anchor, -n), ax_w)))
    tau = M.servos[joint]["stall_nm"] * torque_fraction
    squeeze = tau / lever if lever > 1e-6 else float("inf")
    # 2. the grip scene
    sx, sy, sz = [s / 1000.0 for s in (size_mm or (width_mm, 20.0, 20.0))]
    sx = w
    ma = mass_g / 1000.0
    results = {}
    t1 = np.cross(n, [0, 0, 1.0]) if abs(n[2]) < 0.9 else np.cross(n, [1.0, 0, 0])
    t1 /= np.linalg.norm(t1)
    t2 = np.cross(n, t1)
    R_obj = np.column_stack([n, t1, t2])
    for axis_name, sdir in (("squeeze", n), ("across_1", t1), ("across_2", t2)):
        sp = M.spec(servos={joint}, scale={joint: torque_fraction})
        sp.option.cone = mujoco.mjtCone.mjCONE_ELLIPTIC
        sp.option.impratio = 10.0
        sp.option.noslip_iterations = 5
        _lock(sp, M, {joint}, pose)
        for name, link, p, R, t, sgn in (("pad_m", lm, pm, Rm, tm, -1.0), ("pad_f", lf, pf, Rf, tf, 1.0)):
            nl = R.T @ (sgn * n)                               # pad face normal (toward the object) in its body frame
            sp.body(link).add_geom(name=name, type=mujoco.mjtGeom.mjGEOM_BOX,
                                   size=[pad_mm[0] / 2000, pad_mm[1] / 2000, t / 2], pos=p.tolist(),
                                   quat=_quat_z_to(nl), contype=0, conaffinity=0, mass=0, friction=[mu, 0.005, 0.0001])
        ob = sp.worldbody.add_body(name="object", pos=centre.tolist(), quat=_rot_to_quat(R_obj), mass=ma,
                                   ipos=[0, 0, 0], explicitinertial=True,
                                   inertia=[ma * (sy ** 2 + sz ** 2) / 12, ma * (sx ** 2 + sz ** 2) / 12, ma * (sx ** 2 + sy ** 2) / 12])
        ob.add_freejoint()
        ob.add_geom(name="obj", type=mujoco.mjtGeom.mjGEOM_BOX, size=[sx / 2, sy / 2, sz / 2], contype=0, conaffinity=0,
                    mass=0, friction=[mu, 0.005, 0.0001])
        for pg in ("pad_m", "pad_f"):
            sp.add_pair(geomname1=pg, geomname2="obj", condim=4, friction=[mu, mu, 0.005, 0.0001, 0.0001],
                        solref=[4 * DT, 1.0])        # stiff contact (4 steps): the pads sink in ~0.05 mm, not ~1 mm
        mj2 = sp.compile()
        d2 = mujoco.MjData(mj2)
        q_open = q_hold                     # pads just touching; the squeeze ramps up (no impact that throws it out)
        _set_pose(M, mj2, d2, {**pose, joint: math.degrees(q_open) if M.kind[joint] == "revolute" else q_open * 1000})
        sv = Servos(M, mj2, d2)
        sv.command({joint: closed}, d2, jump=True)
        g0 = np.array([0.0, 0.0, -G])
        bid = mj2.body("object").id
        fb = mj2.body(lf).id

        def rel():
            return d2.xmat[fb].reshape(3, 3).T @ (d2.xpos[bid] - d2.xpos[fb])

        n_set = int(0.25 / DT)                  # close in zero g, squeeze ramping up; then lift (gravity ramps in)
        for i in range(2 * n_set):
            sv.gain = min(1.0, (i + 1) / n_set)
            mj2.opt.gravity[:] = g0 * max(0.0, (i + 1 - n_set) / n_set)
            sv.step(mj2, d2)
        for _ in range(int(0.1 / DT)):
            sv.step(mj2, d2)
        p0 = rel()
        n_f = Rf.T @ n
        worst = 0.0
        steps = int(cycles / shake_hz / DT)
        for i in range(steps):
            t = (i + 1) * DT
            mj2.opt.gravity[:] = g0 - shake_g * G * math.sin(2 * math.pi * shake_hz * t) * sdir
            sv.step(mj2, d2)
            dp = rel() - p0
            dp -= np.dot(dp, n_f) * n_f                     # slip = motion across the squeeze, on the fixed jaw
            worst = max(worst, float(np.linalg.norm(dp)))
            if worst > 0.05:                                  # 50 mm: it fell out
                break
        results[axis_name] = round(worst * 1000.0, 3)
    # hand estimate: two friction faces hold 2 mu N against m (g + shake) in the worst case (both along the jaw faces)
    m_slip = 2.0 * mu * squeeze / ((1.0 + shake_g) * G) * 1000.0
    return {"grip_deg": round(math.degrees(q_hold), 2), "squeeze_n": round(squeeze, 2), "lever_mm": round(lever * 1000, 2),
            "slip_mm": results, "hand_slip_mass_g": round(m_slip, 1)}


# ---------------------------------------------------------------------------------------------------------- drop

def hertz_k(E_mpa: float, nu: float, radius_mm: float, floor_E_mpa: float | None = None, floor_nu: float = 0.3) -> float:
    """Hertz sphere-on-flat constant K (N / m^1.5): F = K delta^1.5, K = 4/3 E* sqrt(R). A rigid floor when
    floor_E_mpa is None (Johnson, Contact Mechanics, s4.2)."""
    inv = (1 - nu ** 2) / (E_mpa * 1e6) + ((1 - floor_nu ** 2) / (floor_E_mpa * 1e6) if floor_E_mpa else 0.0)
    return 4.0 / 3.0 * (1.0 / inv) * math.sqrt(radius_mm / 1000.0)


def hertz_peak(K: float, m: float, v: float) -> float:
    """Closed-form peak force of an elastic Hertz impact: F = K^(2/5) (5/4 m v^2)^(3/5) (Johnson s11.4)."""
    return K ** 0.4 * (1.25 * m * v * v) ** 0.6


def _contact_force(delta: float, K: float, ks: float | None) -> float:
    """Force of the Hertz contact in series with a linear structural spring ks (N/m) at total compression delta."""
    if delta <= 0:
        return 0.0
    if not ks:
        return K * delta ** 1.5
    lo, hi = 0.0, min(K * delta ** 1.5, ks * delta)
    for _ in range(60):                                       # delta = (F/K)^(2/3) + F/ks, monotone in F
        F = (lo + hi) / 2
        if (F / K) ** (2.0 / 3.0) + F / ks < delta:
            lo = F
        else:
            hi = F
    return (lo + hi) / 2


def drop_body(mass: float, inertia: np.ndarray, hit: np.ndarray, height_m: float, K: float, ks: float | None = None,
              dt: float | None = None) -> dict:
    """A rigid body (mass kg, 3x3 inertia about its centre of mass, the hit point `hit` relative to the centre of mass,
    m; world frame with the floor normal +Z) let go `height_m` above a rigid floor, landing on its hit point. MuJoCo
    integrates the body (free joint: it may rotate about the hit point); the floor pushes on the hit point with the
    Hertz law K delta^1.5 in series with the structure's own spring ks. Undamped (elastic): the highest peak.
    Returns the peak contact force (N) and the contact time (s)."""
    import mujoco
    v = math.sqrt(2.0 * G * height_m)
    w, V = np.linalg.eigh(np.asarray(inertia, float))
    if np.linalg.det(V) < 0:
        V[:, 0] *= -1
    sp = mujoco.MjSpec()
    sp.option.gravity = [0.0, 0.0, -G]
    k_lin = ks or K * 1e-3 ** 0.5                            # contact-time estimate for the step size
    t_c = math.pi * math.sqrt(mass / k_lin) if ks else 2.87 * (mass ** 2 / (K ** 2 * v)) ** 0.2
    sp.option.timestep = dt or min(1e-4, t_c / 400.0)
    b = sp.worldbody.add_body(name="b", pos=[0, 0, 0], ipos=[0, 0, 0], explicitinertial=True, mass=mass, inertia=np.maximum(w, 1e-12).tolist(),
                              iquat=_rot_to_quat(V))
    b.add_freejoint()
    b.add_site(name="hit", pos=np.asarray(hit, float).tolist())
    mj = sp.compile()
    d = mujoco.MjData(mj)
    d.qpos[2] = -float(hit[2]) + 1e-9                       # hit point just above the floor, moving at the drop speed
    d.qvel[2] = -v
    mujoco.mj_forward(mj, d)
    peak, t_in, t_out, steps = 0.0, None, None, 0
    while steps < 2_000_000:
        p = d.site("hit").xpos
        F = _contact_force(-float(p[2]), K, ks)
        d.xfrc_applied[:] = 0
        if F > 0:
            t_in = d.time if t_in is None else t_in
            arm = p - d.xipos[1]
            d.xfrc_applied[1, :3] = [0, 0, F]
            d.xfrc_applied[1, 3:] = np.cross(arm, [0, 0, F])
        elif t_in is not None:
            t_out = d.time
            break
        peak = max(peak, F)
        mujoco.mj_step(mj, d)
        steps += 1
    return {"peak_n": peak, "contact_s": (t_out or d.time) - (t_in or 0.0), "v_mps": v, "dt": mj.opt.timestep}


def subtree_inertia(M: Model, pose: dict, root_joint: str | None, payload=None):
    """(mass kg, centre of mass m, 3x3 inertia about it) of every body downstream of root_joint (the whole moving
    model + base when None) at `pose`, assembly frame. payload: (mass kg, point m) added as a point mass."""
    import mujoco
    mj = M.spec().compile()
    d = mujoco.MjData(mj)
    _set_pose(M, mj, d, pose)
    if root_joint is None:
        bodies = list(range(mj.nbody))
    else:
        top = mj.jnt_bodyid[mj.joint(root_joint).id]
        bodies = [b for b in range(mj.nbody) if _under(mj, b, top)]
    pts = [(float(mj.body_mass[b]), d.xipos[b].copy(),
            d.ximat[b].reshape(3, 3) @ np.diag(mj.body_inertia[b]) @ d.ximat[b].reshape(3, 3).T) for b in bodies]
    if payload:
        pts.append((payload[0], np.asarray(payload[1], float), np.zeros((3, 3))))
    m = sum(p[0] for p in pts)
    c = sum(p[0] * p[1] for p in pts) / m
    I = np.zeros((3, 3))
    for mi, ci, Ii in pts:
        r = ci - c
        I += Ii + mi * (np.dot(r, r) * np.eye(3) - np.outer(r, r))
    return m, c, I, (mj, d)


def _under(mj, b, top):
    while b > 0:
        if b == top:
            return True
        b = mj.body_parentid[b]
    return b == top


# ---------------------------------------------------------------------------------------------------------- CLI

SIM_CHECKS = ("grip_hold", "joint_speed", "drop_impact")


def simulate(name: str, say=print) -> int:
    """`kerf simulate <p>`: the project's URDF in MuJoCo; every link's mass, every servo's catalog limits, the home
    pose held under gravity, and every simulated requirement (grip_hold, joint_speed, drop_impact). Writes
    out/simulate.json; 0 when the home pose holds and every simulated requirement passes."""
    import json
    from . import project as P, requirements as R
    proj = P.build(P.load(name))
    asm = A.plan(proj)
    if not asm.movable:
        say(f"{name}: no moving joints, nothing to simulate")
        return 0
    M = load(proj, asm)
    mj = M.spec().compile()
    say(f"MuJoCo {__import__('mujoco').__version__}: {proj.dir.name}.urdf, {mj.nbody - 1} bodies, joints {M.joints}"
        + (f", geared {M.mimic}" if M.mimic else ""))
    for b in range(1, mj.nbody):
        if mj.body_mass[b] > 0:
            say(f"  link {mj.body(b).name}: {mj.body_mass[b] * 1000:.1f} g")
    for j, s in M.servos.items():
        say(f"  servo {j} ({s['catalog']}): stall {s['stall_nm']:.3f} N*m, no-load {math.degrees(s['w0']):.0f} deg/s")
    home = move(M, {}, {}, 0.5)
    ok = home["time_s"] is not None
    say(f"home pose held under gravity: {'yes' if ok else 'NO'}; torque / stall {home['peak_fraction']}; "
        f"sag (deg) {home['final_error_deg']}")
    out = {"model": {"joints": M.joints, "servos": M.servos, "mimic": M.mimic}, "home": home, "requirements": []}
    for req in proj.data.get("requirements") or []:
        if req.get("check") not in SIM_CHECKS:
            continue
        kw = {k: v for k, v in req.items() if k not in ("check", "why", "id")}
        try:
            r = R.REGISTRY[req["check"]](proj, asm, **kw)
        except Exception as e:  # noqa: BLE001
            r = {"ok": False, "value": None, "limit": None, "detail": f"failed to run: {type(e).__name__}: {e}"}
        unit, bound = R.UNITS.get(req["check"], ("", "limit"))
        r = {"id": req.get("id", req["check"]), "check": req["check"], "unit": unit, "bound": bound,
             **{k: v for k, v in r.items() if not k.startswith("_")}}
        out["requirements"].append(r)
        ok = ok and bool(r["ok"])
        say(f"{'PASS' if r['ok'] else 'FAIL'} {r['id']}: {R.describe(r)}\n      {r['detail']}")
    path = proj.out("simulate.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    say(("SIMULATE PASS" if ok else "SIMULATE FAIL") + f" (out/{path.name})")
    return 0 if ok else 1
