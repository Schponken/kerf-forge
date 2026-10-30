"""Linear-elastic static FEA for one printed part: gmsh tetrahedral mesh + scikit-fem quadratic (P2) elements.

    res = fea.static(shape, E_mpa=2000, nu=0.38,
                     fixed=lambda x, y, z: x < 0.01,                     # boundary faces clamped (mm, part frame)
                     loads=[(lambda x, y, z: x > 99.99, (0, 0, -10.0))])  # total force (N) spread over those faces
    -> {"max_vm_mpa": 99.9th percentile von Mises, "max_vm_peak_mpa", "max_disp_mm", "nodes", "elements"}

Each load is either (predicate, force) — a total force spread evenly over the selected faces — or a dict with "pred"
and one of: "force" (same), "pressure" (MPa, pushes into the surface along -normal), "torque" (N*mm about the axis
"axis_at" + "axis_dir", tangential traction proportional to the distance from the axis, the exact torsion
distribution for a round section) or "bearing" (force vector a shaft puts on a bore: cosine-distributed pressure on the
half of the selected faces facing the load, scaled so the resultant equals the force).
The result also has "applied_force_n" / "applied_moment_nmm" (about the part origin) so a load can be audited, and
"_viz" (surface triangles + von Mises per triangle) for kerf/fea_render.py.

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


MAX_TETS = 80000  # quadratic tets with the AMG solver stay well under ~2 GB


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
    for ld in loads:
        ld = ld if isinstance(ld, dict) else {"pred": ld[0], "force": ld[1]}
        pred = ld["pred"]
        facets = mesh.facets_satisfying(lambda x: pred(x[0], x[1], x[2]), boundaries_only=True)
        if len(facets) == 0:
            raise ValueError("a load region selects no boundary faces")
        fb = FacetBasis(mesh, elem, facets=facets, intorder=4)
        f += asm(_traction(ld, fb), fb)
    fixed_facets = mesh.facets_satisfying(lambda x: fixed(x[0], x[1], x[2]), boundaries_only=True)
    if len(fixed_facets) == 0:
        raise ValueError("the fixed region selects no boundary faces")
    D = basis.get_dofs(fixed_facets).all()
    # Iterative solve (algebraic multigrid + CG): a direct solver on quadratic tets needs GBs of RAM.
    import pyamg
    A, b, x0, I = condense(K, f, D=D)
    # rigid-body modes (3 translations, 3 rotations) as the near-null space: what makes AMG converge for elasticity
    N = K.shape[0]
    comp = np.zeros(N, dtype=int)
    for name in ("nodal_dofs", "edge_dofs", "facet_dofs", "interior_dofs"):
        arr = getattr(basis, name, None)
        if arr is not None and getattr(arr, "size", 0):
            for c in range(3):
                comp[arr[c]] = c
    X = basis.doflocs
    x_, y_, z_ = X[0], X[1], X[2]
    e0, e1, e2 = (comp == 0) * 1.0, (comp == 1) * 1.0, (comp == 2) * 1.0
    B = np.stack([e0, e1, e2, -z_ * e1 + y_ * e2, z_ * e0 - x_ * e2, -y_ * e0 + x_ * e1], axis=1)[I]
    ml = pyamg.smoothed_aggregation_solver(A.tocsr(), B=B, smooth="energy")
    res_hist = []
    xI = ml.solve(b, tol=1e-9, accel="cg", maxiter=600, residuals=res_hist)
    if res_hist and res_hist[-1] > 1e-6 * max(res_hist[0], 1e-30):
        raise RuntimeError(f"FEA solver did not converge (residual ratio {res_hist[-1] / res_hist[0]:.1e})")
    u = x0.copy()
    u[I] = xI
    eps = sym_grad(basis.interpolate(u))
    s = 2 * mu * eps + lam * eye(trace(eps), 3)
    vm = np.sqrt(0.5 * ((s[0, 0] - s[1, 1]) ** 2 + (s[1, 1] - s[2, 2]) ** 2 + (s[2, 2] - s[0, 0]) ** 2)
                 + 3 * (s[0, 1] ** 2 + s[1, 2] ** 2 + s[2, 0] ** 2))
    disp = np.vstack([u[basis.nodal_dofs[i]] for i in range(3)]).T
    # applied loads: the P2 basis reproduces linear fields, so sum(f) and sum(x cross f) are the exact resultants
    fx, fy, fz = (np.where(comp == c, f, 0.0) for c in range(3))
    Fapp = np.array([fx.sum(), fy.sum(), fz.sum()])
    Mapp = np.array([(y_ * fz - z_ * fy).sum(), (z_ * fx - x_ * fz).sum(), (x_ * fy - y_ * fx).sum()])
    bf = mesh.boundary_facets()
    vm_el = vm.mean(axis=1)
    viz = {"tris": mesh.p[:, mesh.facets[:, bf]].transpose(2, 1, 0), "vm": vm_el[mesh.f2t[0, bf]]}
    return {"applied_force_n": Fapp.round(4).tolist(), "applied_moment_nmm": Mapp.round(3).tolist(), "_viz": viz,
            "max_vm_mpa": float(np.percentile(vm, 99.9)), "max_vm_peak_mpa": float(vm.max()), "median_vm_mpa": float(np.median(vm)),
            "max_disp_mm": float(np.linalg.norm(disp, axis=1).max()),
            "nodes": int(mesh.p.shape[1]), "elements": int(mesh.t.shape[1])}


def _traction(ld, fb):
    """LinearForm for one load dict on its facet basis (see module docstring)."""
    from skfem import Functional, LinearForm, asm

    if "force" in ld:
        area = asm(Functional(lambda w: 1.0 + 0.0 * w.x[0]), fb)
        t = np.asarray(ld["force"], dtype=float) / area
        return LinearForm(lambda v, w: t[0] * v[0] + t[1] * v[1] + t[2] * v[2])
    if "pressure" in ld:
        p = float(ld["pressure"])
        return LinearForm(lambda v, w: -p * (w.n[0] * v[0] + w.n[1] * v[1] + w.n[2] * v[2]))
    if "torque" in ld:
        o = np.asarray(ld["axis_at"], float)
        d = np.asarray(ld["axis_dir"], float)
        d = d / np.linalg.norm(d)

        def tang(x):  # d x (x - o): tangential, magnitude = distance from the axis
            r = [x[i] - o[i] for i in range(3)]
            return [d[1] * r[2] - d[2] * r[1], d[2] * r[0] - d[0] * r[2], d[0] * r[1] - d[1] * r[0]]
        polar = asm(Functional(lambda w: sum(c ** 2 for c in tang(w.x))), fb)   # integral of r_perp^2 dA
        k = float(ld["torque"]) / polar
        return LinearForm(lambda v, w: k * sum(c * v[i] for i, c in enumerate(tang(w.x))))
    if "bearing" in ld:
        F = np.asarray(ld["bearing"], float)
        Fm = float(np.linalg.norm(F))
        e = F / Fm

        def cos_pos(w):  # how squarely each face point faces the load; the outward normal of a bore points inward
            return np.maximum(0.0, -(w.n[0] * e[0] + w.n[1] * e[1] + w.n[2] * e[2]))
        q = Fm / asm(Functional(lambda w: cos_pos(w) ** 2), fb)
        return LinearForm(lambda v, w: -q * cos_pos(w) * (w.n[0] * v[0] + w.n[1] * v[1] + w.n[2] * v[2]))
    raise ValueError(f"load needs force, pressure, torque or bearing: {sorted(ld)}")
