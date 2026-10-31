"""The context a part module receives in build(ctx): parameters, catalog, joints and fastener sites.

A part module looks like:

    from build123d import *
    from kerf import iface

    def build(ctx):
        p = ctx.p
        body = Box(p.w, p.d, p.t, align=(Align.CENTER, Align.CENTER, Align.MIN))
        body -= iface.bolt_pattern(ctx, "base_bracket", "M3", iface.rect(30, 20), Location((0, 0, p.t)),
                                   kind="heatset", depth=p.t)
        ctx.rigid("bracket_mount", Location((0, 0, p.t)))
        return ctx.finish(body)

Coordinates are millimetres, Z up, in the part's own frame. The part's print orientation is set in project.yaml.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from build123d import Axis, Location, RevoluteJoint, RigidJoint, LinearJoint, Color

from . import catalog


@dataclass
class Site:
    """One fastener hole end. Local frame: origin on the entry surface, +Z pointing out of the part
    toward where the screw head (male) or the mating part (female) is."""
    group: str
    role: str          # "male" (screw passes through, head side) or "female" (screw threads in)
    screw: str         # "M3"
    kind: str          # clearance | counterbore | countersink | heatset | tap | nut_trap | threaded
    loc: Location
    grip: float = 0.0  # male: clamped thickness this part contributes (mm)
    engage: float = 0.0  # female: deepest the screw tip may go past the entry surface (mm)
    min_engage: float = 0.0  # female: shortest thread engagement that holds (mm); 0 = default for the screw size
    teardrop: bool | None = None  # cut with a teardrop roof (iface); None = not known (proxies, hand-cut holes)


@dataclass
class PinSite:
    """One hole of a pin (hinge pin, dowel, or screw used as a pivot). Local frame: origin on the hole's entry surface,
    +Z along the pin axis pointing out of the material; the hole runs `depth` mm into -Z."""
    group: str
    pin: str           # catalog path ("motion.pin_3mm") or screw size ("M3") for a screw used as a pivot
    fit: str           # free (pin turns in it) | press (dowel held by interference) | heatset | tap (screw pivot thread)
    loc: Location
    depth: float
    d: float           # pin / screw nominal diameter (mm)
    teardrop: bool | None = None  # cut with a teardrop roof (iface.pin_hole); None = not known


@dataclass
class JointSpec:
    kind: str
    label: str
    loc: Location | None = None
    axis: Axis | None = None
    range: tuple = (-180.0, 180.0)


class PartError(ValueError):
    pass


class Ctx:
    def __init__(self, part_id: str, params: dict, project_meta: dict | None = None):
        self.id = part_id
        self.p = SimpleNamespace(**params)
        self.params = dict(params)
        self.cat = catalog
        self.meta = project_meta or {}
        self.sites: list[Site] = []
        self.joints: list[JointSpec] = []
        self.notes: list[str] = []
        self.pins: list[PinSite] = []
        self.mesh_cuts: list = []
        self.bom: list = []

    # ---- joints (declare in the part's own frame) ----
    def rigid(self, label: str, loc: Location):
        self.joints.append(JointSpec("rigid", label, loc=loc))

    def revolute(self, label: str, axis: Axis, range=(-180.0, 180.0)):
        self.joints.append(JointSpec("revolute", label, axis=axis, range=tuple(range)))

    def linear(self, label: str, axis: Axis, range=(0.0, 100.0)):
        self.joints.append(JointSpec("linear", label, axis=axis, range=tuple(range)))

    def site(self, s: Site):
        self.sites.append(s)

    def pin_site(self, s: PinSite):
        self.pins.append(s)

    def bom_item(self, item: str, qty: int = 1, spec: str = "", note: str = "", link: str = ""):
        """A purchased bit a feature of this part needs (e.g. the captive tripod nut): one BOM row per part copy."""
        self.bom.append({"type": "hardware", "item": item, "qty": qty, "spec": spec, "note": note, "link": link})

    def mesh_cut(self, solid):
        """`source: meshy` parts: a solid (part frame) cut through the generated shell too - holes, pockets, keep-outs.
        Subtract it from your own features as usual; kerf/meshy.py also cuts it from the fused shell."""
        self.mesh_cuts.append(solid)
        return solid

    def finish(self, shape, color=None):
        """Attach label, joints and sites to the final solid and return it."""
        if shape is None:
            raise PartError(f"{self.id}: build() produced nothing")
        shape.label = self.id
        if color is not None:
            shape.color = Color(color) if not isinstance(color, Color) else color
        labels = [j.label for j in self.joints]
        dup = {l for l in labels if labels.count(l) > 1}
        if dup:
            raise PartError(f"{self.id}: duplicate joint labels {sorted(dup)}")
        for j in self.joints:
            if j.kind == "rigid":
                RigidJoint(j.label, to_part=shape, joint_location=j.loc)
            elif j.kind == "revolute":
                RevoluteJoint(j.label, to_part=shape, axis=j.axis, angular_range=j.range)
            elif j.kind == "linear":
                LinearJoint(j.label, to_part=shape, axis=j.axis, linear_range=j.range)
        shape.kerf_sites = list(self.sites)
        shape.kerf_joints = list(self.joints)
        shape.kerf_notes = list(self.notes)
        shape.kerf_pins = list(self.pins)
        shape.kerf_mesh_cuts = list(self.mesh_cuts)
        shape.kerf_bom = list(self.bom)
        return shape
