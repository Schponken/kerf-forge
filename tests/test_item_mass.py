"""Purchased-item mass: catalog weight, or density x tube cross-section x length (hand-checked)."""
import math
import types

import pytest

from kerf.checks import item_mass_g


def item(**spec):
    return types.SimpleNamespace(role="purchased", spec=spec)


def test_tube_mass_from_density():
    # 5 x 3 mm carbon tube, 228 mm, 1.5 g/cm3: pi/4 x (25 - 9) x 228 / 1000 x 1.5 = 4.30 g
    assert item_mass_g(item(catalog="rods.cf_tube_5x3", length=228)) == pytest.approx(math.pi / 4 * 16 * 228e-3 * 1.5, rel=1e-6)


def test_catalog_weight_and_override():
    assert item_mass_g(item(catalog="servos.MG90S")) > 0
    assert item_mass_g(item(catalog="rods.cf_tube_5x3", length=228, mass_g=7.0)) == 7.0


def test_printed_mass_is_cached_per_geometry_and_spec():
    """checks.item_mass_g keeps a printed part's mass on its shape (every mass / CG requirement asks again): moving the
    part keeps the cached value, changing the spec (infill) or the geometry recomputes it, and it always equals a
    fresh computation."""
    from types import SimpleNamespace
    from build123d import Box, Pos
    from kerf import checks
    s = Box(40, 30, 20)
    it = SimpleNamespace(role="printed", shape=s, spec={"material": "PETG", "infill": 0.2})
    m = checks.item_mass_g(it)
    assert m == checks._printed_mass_g(it)
    it.shape.location = Pos(100, 0, 0) * it.shape.location             # moved: same part, same mass
    assert checks.item_mass_g(it) == m
    it.spec = {"material": "PETG", "infill": 0.6}
    assert checks.item_mass_g(it) > m and checks.item_mass_g(it) == checks._printed_mass_g(it)
    it.shape = Box(40, 30, 40)                                          # new geometry
    assert checks.item_mass_g(it) == checks._printed_mass_g(it) > m
