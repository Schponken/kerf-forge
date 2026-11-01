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

from dataclasses import dataclass
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
        self.features: list = []      # design-intent ledger: what each feature is and why (kerf/intent.py)

    # ---- joints (declare in the part's own frame) ----
    def rigid(self, label: str, loc: Location):
        self.joints.append(JointSpec("rigid", label, loc=loc))

    def revolute(self, label: str, axis: Axis, range=(-180.0, 180.0)):
        self.joints.append(JointSpec("revolute", label, axis=axis, range=tuple(range)))

    def linear(self, label: str, axis: Axis, range=(0.0, 100.0)):
        self.joints.append(JointSpec("linear", label, axis=axis, range=tuple(range)))

    def site(self, s: Site):
        self.sites.append(s)
        self._iface_feature("fastener", s.group, f"{s.screw} {s.kind}", "male" if s.role == "male" else "female", s.loc)

    def pin_site(self, s: PinSite):
        self.pins.append(s)
        self._iface_feature("pin", s.group, f"{s.pin.split('.')[-1]} {s.fit} fit", "", s.loc)

    # ---- design-intent ledger ----
    def add(self, shape, why: str, kind: str = "feature"):
        """Record a feature added to the body and return it: `body += ctx.add(rib, why="...", kind="rib")`."""
        return self._feature("add", shape, why, kind)

    def cut(self, shape, why: str, kind: str = "cut"):
        """Record a feature cut from the body and return the cutter: `body -= ctx.cut(slot, why="...", kind="tie slot")`."""
        return self._feature("cut", shape, why, kind)

    def _feature(self, op, shape, why, kind):
        if not why or not str(why).strip():
            raise PartError(f"{self.id}: ctx.{op}(..., kind={kind!r}) needs a why= (what load / fit / print need it serves)")
        c = shape.bounding_box().center() if shape is not None else None
        self.features.append({"op": op, "kind": kind, "why": str(why).strip(), "source": "part",
                              "at": [round(c.X, 1), round(c.Y, 1), round(c.Z, 1)] if c is not None else None,
                              "volume_mm3": round(float(shape.volume), 1) if shape is not None else None})
        return shape

    def _iface_feature(self, what, group, spec, role, loc):
        """iface features register themselves: one ledger row per interface group and hole type, with the count."""
        for f in self.features:
            if f.get("group") == group and f.get("spec") == spec and f["source"] == "iface":
                f["count"] += 1
                return
        mate = "the screw passes through here" if role == "male" else ("the screw threads in here" if role else "")
        p = loc.position
        self.features.append({"op": "cut", "kind": f"{what} hole", "source": "iface", "group": group, "spec": spec,
                              "count": 1, "at": [round(p.X, 1), round(p.Y, 1), round(p.Z, 1)],
                              "why": f"interface '{group}': {spec}; lines up with the mating part's '{group}' by "
                                     f"construction{(' - ' + mate) if mate else ''}"})

    def bom_item(self, item: str, qty: int = 1, spec: str = "", note: str = "", link: str = "", price_key: str = ""):
        """A purchased bit a feature of this part needs (e.g. the captive tripod nut): one BOM row per part copy.
        `price_key` names its catalog/prices.json entry so the BOM can price it."""
        row = {"type": "hardware", "item": item, "qty": qty, "spec": spec, "note": note, "link": link}
        if price_key:
            row["price_key"] = price_key
        self.bom.append(row)

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
        shape.kerf_features = [dict(f) for f in self.features]
        return shape
