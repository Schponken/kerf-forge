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
