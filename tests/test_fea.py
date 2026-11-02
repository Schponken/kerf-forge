"""FEA must match hand calculations before any project relies on it."""
import numpy as np
import pytest

pytestmark = pytest.mark.slow
from build123d import Align, Box, Cylinder

from kerf import fea


def test_cantilever_matches_beam_theory():
    beam = Box(100, 10, 10, align=(Align.MIN, Align.CENTER, Align.CENTER))
    r = fea.static(beam, 2000, 0.3, fixed=lambda x, y, z: x < 0.01, loads=[(lambda x, y, z: x > 99.99, (0, 0, -10.0))])
    I = 10 * 10 ** 3 / 12
    assert r["max_disp_mm"] == pytest.approx(10 * 100 ** 3 / (3 * 2000 * I), rel=0.03)      # 2.0 mm
    assert r["max_vm_peak_mpa"] == pytest.approx(10 * 100 * 5 / I, rel=0.10)               # 6.0 MPa
    assert r["max_disp_at"][0] == pytest.approx(100, abs=0.5)                              # at the free tip
    assert r["max_vm_peak_at"][0] < 20                                                     # peak bending at the root


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


def test_result_cache_hits_only_for_identical_problems(tmp_path, monkeypatch):
    from build123d import Box, Align
    monkeypatch.setenv("KERF_CACHE", str(tmp_path))
    bar = Box(60, 6, 6, align=(Align.MIN, Align.CENTER, Align.CENTER))
    fixed = lambda x, y, z: x < 0.01  # noqa: E731
    tip = lambda x, y, z: x > 59.99   # noqa: E731
    a = fea.static(bar, 2000, 0.38, fixed, [(tip, (0, 0, -5.0))])
    b = fea.static(bar, 2000, 0.38, fixed, [(tip, (0, 0, -5.0))])
    assert a["cached"] is False and b["cached"] is True
    for k in ("max_vm_mpa", "max_disp_mm", "nodes", "elements"):
        assert a[k] == b[k]
    c = fea.static(bar, 2000, 0.38, fixed, [(tip, (0, 0, -6.0))])      # different load -> new solve
    d = fea.static(bar, 2100, 0.38, fixed, [(tip, (0, 0, -5.0))])      # different material -> new solve
    e = fea.static(bar, 2000, 0.38, lambda x, y, z: x < 3, [(tip, (0, 0, -5.0))])  # different support -> new solve
    assert not c["cached"] and not d["cached"] and not e["cached"]
    assert c["max_disp_mm"] == pytest.approx(a["max_disp_mm"] * 1.2, rel=1e-6)
    monkeypatch.setenv("KERF_FEA_CACHE", "0")
    assert fea.static(bar, 2000, 0.38, fixed, [(tip, (0, 0, -5.0))])["cached"] is False


def test_stalled_solver_coarsens_and_solves_exactly(tmp_path, monkeypatch):
    """When AMG+CG stalls on a system too big for the direct solver, the mesh is coarsened until LU fits."""
    from build123d import Box, Align
    monkeypatch.setenv("KERF_CACHE", str(tmp_path))
    bar = Box(100, 10, 10, align=(Align.MIN, Align.CENTER, Align.CENTER))
    fixed = lambda x, y, z: x < 0.01      # noqa: E731
    tip = lambda x, y, z: x > 99.99       # noqa: E731
    ref = fea.static(bar, 2000, 0.38, fixed, [(tip, (0, 0, -10.0))])
    monkeypatch.setattr(fea, "AMG_MAXITER", 1)            # force a "stall"
    monkeypatch.setattr(fea, "DIRECT_MAX_DOFS", ref["nodes"] * 3 // 2)   # the first mesh is too big for LU
    monkeypatch.setenv("KERF_FEA_CACHE", "0")
    r = fea.static(bar, 2000, 0.38, fixed, [(tip, (0, 0, -10.0))])
    assert "coarser mesh" in r["solver_note"] and r["elements"] < ref["elements"]
    assert r["max_disp_mm"] == pytest.approx(2.0, rel=0.03)          # beam theory: F L^3 / 3EI = 2.0 mm


def test_stress_map_finds_idle_material_and_overbuilt_parts():
    from build123d import Box, Align
    from kerf import stressmap
    import os
    os.environ["KERF_FEA_CACHE"] = "0"
    bar = Box(100, 10, 10, align=(Align.MIN, Align.CENTER, Align.CENTER))
    r = fea.static(bar, 2000, 0.38, lambda x, y, z: x < 0.01, [(lambda x, y, z: x > 99.99, (0, 0, -10.0))])
    os.environ.pop("KERF_FEA_CACHE")
    assert r["_field"]["vol"].sum() == pytest.approx(10000, rel=1e-6)          # element volumes add up to the bar
    peak = float(np.percentile(r["_field"]["vm"], 99.9))
    tight = stressmap.summarize([{"field": r["_field"], "allow": peak * 1.1}])
    assert not tight["overbuilt"] and tight["hot_zones"][0]["at"][0] < 20       # hot spot at the clamped root
    loose = stressmap.summarize([{"field": r["_field"], "allow": peak * 20}])
    assert loose["overbuilt"] and loose["cold_zones"][0]["at"][0] > 50           # idle material toward the free end
    assert "overbuilt" in stressmap.advice("bar", loose)
    stiff = stressmap.summarize([{"field": r["_field"], "allow": peak * 20, "disp_use": 0.9}])
    assert not stiff["overbuilt"]                                                # stiffness governs: not overbuilt


def test_sliver_tets_are_dropped():
    """A flat (zero-volume) tet would make the stiffness NaN; drop_slivers removes it and keeps the good one."""
    import numpy as np
    from kerf import fea
    pts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [0.5, 0.5, 0]], float)
    tets = np.array([[0, 1, 2, 3], [0, 1, 2, 4]])            # the second lies flat in z = 0
    out = fea.drop_slivers(pts, tets, 1.0)
    assert out.tolist() == [[0, 1, 2, 3]]


@pytest.mark.parametrize('fail', ['none', 'initialize', 'mesh'])
def test_gmsh_meshing_keeps_python_broken_pipe_handling(fail):
    import subprocess
    import sys
    import textwrap
    code = '''
import os, signal
from build123d import Box
from kerf import fea
import gmsh
if FAIL == 'initialize':
    initialize = gmsh.initialize
    def broken_init(*args):
        initialize(*args)
        raise RuntimeError('expected initialization failure')
    gmsh.initialize = broken_init
elif FAIL == 'mesh':
    def broken(*args): raise RuntimeError('expected meshing failure')
    gmsh.model.mesh.generate = broken
try:
    fea._mesh(Box(5, 5, 5), 3)
except RuntimeError:
    assert FAIL != 'none'
# Native code can reset the OS handler while signal.getsignal still reports SIG_IGN.
# Actually write a broken pipe: a regression kills this child with SIGPIPE (exit -13).
r, w = os.pipe()
os.close(r)
try:
    os.write(w, b'x')
except BrokenPipeError:
    pass
else:
    raise AssertionError('broken pipe was not reported')
os.close(w)
'''.replace('FAIL',repr(fail))
    r = subprocess.run([sys.executable,'-c',textwrap.dedent(code)],capture_output=True,text=True,timeout=30)
    assert r.returncode==0,r.stderr


def test_von_mises_chunks_match_one_basis():
    """fea._von_mises builds the intorder-4 sampling basis per chunk of elements (memory): identical to one basis
    over the whole mesh."""
    import numpy as np
    from build123d import Box
    from skfem import Basis, ElementTetP2, ElementVector, MeshTet
    from skfem.models.elasticity import lame_parameters
    from kerf import fea
    pts, tets = fea._mesh(Box(20, 6, 4), 2.0)
    mesh = MeshTet(pts.T, tets.T)
    elem = ElementVector(ElementTetP2())
    u = np.random.default_rng(0).normal(size=Basis(mesh, elem, intorder=1).N) * 1e-3
    lam, mu = lame_parameters(2000.0, 0.35)
    one = fea._von_mises(mesh, elem, u, lam, mu, chunk=10**9)
    assert one.shape[0] == mesh.t.shape[1] and np.array_equal(one, fea._von_mises(mesh, elem, u, lam, mu, chunk=37))
