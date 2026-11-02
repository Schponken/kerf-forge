"""Scenario checks from declared demand and modeled regions; no inferred plant demand or sensing performance."""
from __future__ import annotations

import math

from . import assembly, geom
from .requirements import UNITS, check


def _number(name, value, *, zero=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            or (value < 0 if zero else value <= 0)):
        raise ValueError(f"{name} must be a finite {'nonnegative' if zero else 'positive'} number")
    return float(value)


def _region(proj, name):
    item = proj.items.get(name)
    if item is None or item.role != "keepout":
        raise ValueError(f"'{name}' must name a keep-out region, not the material of a printed or purchased part")
    shape = item.shape
    if shape is None or item.error or not shape.is_valid or len(shape.solids()) != 1:
        raise ValueError(f"region '{name}' must build one valid solid")
    volume = _number(f"region '{name}' volume", geom.volume(shape))
    return item, volume


@check("reservoir_capacity")
def reservoir_capacity(proj, asm, volume, daily_ml, days, usable_fraction, reserve_ml=0):
    """Days supplied by a modeled internal fluid volume, after explicit usable fraction and reserve."""
    demand = _number("daily_ml", daily_ml)
    duration = _number("days", days)
    usable = _number("usable_fraction", usable_fraction)
    if usable > 1:
        raise ValueError("usable_fraction cannot exceed 1")
    reserve = _number("reserve_ml", reserve_ml, zero=True)
    _, mm3 = _region(proj, volume)
    capacity = mm3 / 1000  # 1 mL = 1 cm³ = 1000 mm³; never use the tank's outer box or plastic volume.
    required_ml = _number("total demand", demand * duration)
    needed_capacity = _number("required capacity", (required_ml + reserve) / usable)
    available = max(0.0, capacity * usable - reserve)
    lasts = _number("available days", available / demand, zero=True)
    return {"ok": lasts >= duration, "value": lasts, "limit": duration,
            "capacity_ml": capacity, "available_ml": available, "required_ml": required_ml,
            "needed_capacity_ml": needed_capacity,
            "detail": (f"{volume}: {capacity:g} mL internal volume × {usable:g} usable − {reserve:g} mL reserve "
                       f"= {available:g} mL; at declared {demand:g} mL/day lasts {lasts:g} days. "
                       "Does not prove pump delivery, leak-tightness or the plant's actual demand.")}


@check("sensor_coverage")
def sensor_coverage(proj, asm, view, target, min_fraction=1.0, pose=None):
    """Fraction of a modeled target region inside the existing view-cone frustum, at a declared assembly pose."""
    required = _number("min_fraction", min_fraction)
    if required > 1:
        raise ValueError("min_fraction cannot exceed 1")
    cone, _ = _region(proj, view)
    region, volume = _region(proj, target)
    if cone.spec.get("proxy") != "view_cone" or view == target:
        raise ValueError("view must be a view_cone keep-out distinct from the target region")
    if pose is not None and not isinstance(pose, dict):
        raise ValueError("pose must map movable joint names to values")
    movable = {edge.name: edge for edge in asm.movable}
    for name, value in (pose or {}).items():
        if (name not in movable or isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not movable[name].range[0] <= value <= movable[name].range[1]):
            raise ValueError(f"pose '{name}' must name a movable joint and a finite value inside its range")
    try:
        assembly.solve(asm, pose or {})
        inside = _number("covered volume", geom.overlap(cone.shape, region.shape), zero=True)
        fraction = max(0.0, min(1.0, inside / volume))
    finally:
        assembly.solve(asm)
    return {"ok": fraction >= required - 1e-9, "value": fraction * 100, "limit": required * 100,
            "covered_mm3": inside, "target_mm3": volume,
            "detail": (f"{fraction * 100:g}% of '{target}' lies in '{view}' at pose {pose or 'home'}. "
                       "Geometric field of view only: does not prove unobstructed visibility, resolution or detection. "
                       "Run the normal fit checks for objects intruding into the view cone.")}


UNITS.update({"reservoir_capacity": ("days", "min"), "sensor_coverage": ("%", "min")})
