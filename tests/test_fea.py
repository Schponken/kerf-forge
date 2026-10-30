"""FEA must match hand calculations before any project relies on it."""
import pytest
from build123d import Align, Box, Cylinder

from kerf import fea


def test_cantilever_matches_beam_theory():
    beam = Box(100, 10, 10, align=(Align.MIN, Align.CENTER, Align.CENTER))
    r = fea.static(beam, 2000, 0.3, fixed=lambda x, y, z: x < 0.01, loads=[(lambda x, y, z: x > 99.99, (0, 0, -10.0))])
    I = 10 * 10 ** 3 / 12
    assert r["max_disp_mm"] == pytest.approx(10 * 100 ** 3 / (3 * 2000 * I), rel=0.03)      # 2.0 mm
    assert r["max_vm_peak_mpa"] == pytest.approx(10 * 100 * 5 / I, rel=0.10)               # 6.0 MPa


def test_axial_rod_stress():
    rod = Cylinder(5, 80, align=(Align.CENTER, Align.CENTER, Align.MIN))
    r = fea.static(rod, 2000, 0.3, fixed=lambda x, y, z: z < 0.01, loads=[(lambda x, y, z: z > 79.99, (0, 0, 500.0))])
    assert r["median_vm_mpa"] == pytest.approx(500 / (3.14159265 * 25), rel=0.03)           # 6.37 MPa in the bulk
    assert r["max_vm_mpa"] == pytest.approx(500 / (3.14159265 * 25), rel=0.15)              # clamp raises the local peak
    assert r["max_disp_mm"] == pytest.approx(500 * 80 / (2000 * 3.14159265 * 25), rel=0.05)  # 0.255 mm


def test_axial_square_bar_exact():
    bar = Box(10, 10, 80, align=(Align.CENTER, Align.CENTER, Align.MIN))
    r = fea.static(bar, 2000, 0.3, fixed=lambda x, y, z: z < 0.01, loads=[(lambda x, y, z: z > 79.99, (0, 0, 500.0))])
    assert r["median_vm_mpa"] == pytest.approx(5.0, rel=0.01)
    assert r["max_disp_mm"] == pytest.approx(500 * 80 / (2000 * 100), rel=0.02)


def test_fast_stiffness_equals_skfem():
    """kerf.fea.stiffness (vectorised, order-2 quadrature) builds the same matrix as skfem's generic assembly."""
    import numpy as np
    from build123d import Box
    from skfem import Basis, ElementTetP2, ElementVector, MeshTet, asm
    from skfem.models.elasticity import lame_parameters, linear_elasticity
    pts, tets = fea._mesh(Box(30, 8, 6), 2.5)
    mesh, elem = MeshTet(pts.T, tets.T), ElementVector(ElementTetP2())
    lam, mu = lame_parameters(2000, 0.38)
    ref = asm(linear_elasticity(lam, mu), Basis(mesh, elem, intorder=4))
    fast = fea.stiffness(Basis(mesh, elem, intorder=2), lam, mu, chunk=97)   # small chunks exercise the chunking
    assert abs(fast - ref).max() <= 1e-10 * abs(ref).max()     # round-off below 1e-10 x max is dropped on purpose
    assert np.allclose(fast.diagonal(), ref.diagonal())
