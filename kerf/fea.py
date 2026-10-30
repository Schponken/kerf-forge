"""Linear-elastic static FEA for one printed part: gmsh tetrahedral mesh + scikit-fem quadratic (P2) elements.

    res = fea.static(shape, E_mpa=2000, nu=0.38,
                     fixed=lambda x, y, z: x < 0.01,                     # boundary faces clamped (mm, part frame)
                     loads=[(lambda x, y, z: x > 99.99, (0, 0, -10.0))])  # total force (N) spread over those faces
    -> {"max_vm_mpa": 99.9th percentile von Mises, "max_vm_peak_mpa", "max_disp_mm", "nodes", "elements"}

Predicates get numpy arrays of facet-centre coordinates and must be vectorised (use comparisons, & and |).
Units: mm, N, MPa. Validated against beam theory in tests/test_fea.py. The percentile stress ignores single-point singularities at sharp re-entrant corners and load
edges; judge against allowable stress = strength / safety factor (docs/ENGINEERING.md). Printed parts are not
isotropic: use the layer-direction (Z) strength when the stressed region is loaded across layers.
"""
from __future__ import annotations

import os
import tempfile

import logging

import numpy as np

logging.getLogger("skfem").setLevel(logging.ERROR)


MAX_TETS = 60000  # ~2-3 GB peak with P2 elements and the direct solver


def _mesh(shape, size: float):
    import gmsh
    from build123d import export_step
    with tempfile.TemporaryDirectory() as t:
        f = os.path.join(t, "p.step")
        export_step(shape, f)
        gmsh.initialize(["-noenv"])
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.model.add("p")
            gmsh.model.occ.importShapes(f)
            gmsh.model.occ.synchronize()
            gmsh.option.setNumber("Mesh.MeshSizeMax", size)
            gmsh.option.setNumber("Mesh.MeshSizeMin", size / 3)
            gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 24)  # ~24 elements per full circle keeps curved sections accurate
            gmsh.model.mesh.generate(3)
            ntags, coords, _ = gmsh.model.mesh.getNodes()
            etypes, _, enodes = gmsh.model.mesh.getElements(3)
        finally:
            gmsh.finalize()
    idx = np.zeros(int(ntags.max()) + 1, dtype=np.int64)
    idx[ntags.astype(np.int64)] = np.arange(len(ntags))
    k = list(etypes).index(4)  # 4-node tetrahedron
    tets = idx[np.asarray(enodes[k], dtype=np.int64)].reshape(-1, 4)
    pts = coords.reshape(-1, 3)
    used = np.unique(tets)
    remap = -np.ones(len(pts), dtype=np.int64)
    remap[used] = np.arange(len(used))
    return pts[used], remap[tets]


def static(shape, E_mpa: float, nu: float, fixed, loads, size: float | None = None) -> dict:
    from skfem import Basis, ElementTetP2, ElementVector, FacetBasis, Functional, LinearForm, MeshTet, asm, condense, solve
    from skfem.helpers import eye, sym_grad, trace
    from skfem.models.elasticity import lame_parameters, linear_elasticity

    bb = shape.bounding_box()
    size = size or max(min(bb.size.X, bb.size.Y, bb.size.Z) / 4.0, 0.6)  # coarser meshes under-represent curved sections
    pts, tets = _mesh(shape, size)
    while len(tets) > MAX_TETS:  # quadratic elements: memory grows fast; coarsen rather than run out of RAM
        size *= 1.4
        pts, tets = _mesh(shape, size)
    mesh = MeshTet(pts.T, tets.T)
    elem = ElementVector(ElementTetP2())
    basis = Basis(mesh, elem, intorder=4)
    lam, mu = lame_parameters(E_mpa, nu)
    K = asm(linear_elasticity(lam, mu), basis)
    f = np.zeros(K.shape[0])
    for pred, force in loads:
        facets = mesh.facets_satisfying(lambda x: pred(x[0], x[1], x[2]), boundaries_only=True)
        if len(facets) == 0:
            raise ValueError("a load region selects no boundary faces")
        fb = FacetBasis(mesh, elem, facets=facets, intorder=4)
        area = asm(Functional(lambda w: 1.0 + 0.0 * w.x[0]), fb)
        t = np.asarray(force, dtype=float) / area

        @LinearForm
        def traction(v, w, t=t):
            return t[0] * v[0] + t[1] * v[1] + t[2] * v[2]

        f += asm(traction, fb)
    fixed_facets = mesh.facets_satisfying(lambda x: fixed(x[0], x[1], x[2]), boundaries_only=True)
    if len(fixed_facets) == 0:
        raise ValueError("the fixed region selects no boundary faces")
    D = basis.get_dofs(fixed_facets).all()
    u = solve(*condense(K, f, D=D))
    eps = sym_grad(basis.interpolate(u))
    s = 2 * mu * eps + lam * eye(trace(eps), 3)
    vm = np.sqrt(0.5 * ((s[0, 0] - s[1, 1]) ** 2 + (s[1, 1] - s[2, 2]) ** 2 + (s[2, 2] - s[0, 0]) ** 2)
                 + 3 * (s[0, 1] ** 2 + s[1, 2] ** 2 + s[2, 0] ** 2))
    disp = np.vstack([u[basis.nodal_dofs[i]] for i in range(3)]).T
    return {"max_vm_mpa": float(np.percentile(vm, 99.9)), "max_vm_peak_mpa": float(vm.max()), "median_vm_mpa": float(np.median(vm)),
            "max_disp_mm": float(np.linalg.norm(disp, axis=1).max()),
            "nodes": int(mesh.p.shape[1]), "elements": int(mesh.t.shape[1])}
