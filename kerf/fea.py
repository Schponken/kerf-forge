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


# Result cache: a solve is fully determined by the mesh, the boundary faces each region selects, the load values,
# the material and this file's code. Hashing exactly those (after meshing, before solving) makes a cache hit
# provably the same answer; any change to geometry, loads, material or the solver is a miss. KERF_FEA_CACHE=0 disables.
_SRC_HASH = __import__("hashlib").sha256(__import__("pathlib").Path(__file__).read_bytes()).hexdigest()[:16]


def _cache_dir():
    if os.environ.get("KERF_FEA_CACHE", "1") == "0":
        return None
    d = os.environ.get("KERF_CACHE") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")
    d = os.path.join(d, "fea")
    os.makedirs(d, exist_ok=True)
    return d


def _key(E, nu, pts, tets, fixed_facets, loads):
    import hashlib
    h = hashlib.sha256()
    import pyamg, scipy, skfem
    h.update(f"{_SRC_HASH}|{skfem.__version__}|{pyamg.__version__}|{scipy.__version__}|{float(E)!r}|{float(nu)!r}|".encode())
    for a in (np.round(pts, 6), np.ascontiguousarray(tets), np.sort(fixed_facets)):
        h.update(str(a.shape).encode() + np.ascontiguousarray(a).tobytes())
    for ld, facets in loads:
        vals = {k: np.round(np.asarray(v, dtype=float), 9).tolist() for k, v in sorted(ld.items()) if k != "pred"}
        h.update(repr(vals).encode() + np.sort(facets).tobytes())
    return h.hexdigest()


DIRECT_MAX_DOFS = 120000  # sparse LU fallback stays under ~2 GB up to here (P2 tets)
MAX_TETS = 80000  # quadratic tets with the AMG solver stay well under ~2 GB


def _mesh(shape, size: float):
    import gmsh
    import signal
    from build123d import export_step
    with tempfile.TemporaryDirectory() as t:
        f = os.path.join(t, "p.step")
        export_step(shape, f)
        pipe = getattr(signal, "SIGPIPE", None)
        pipe_handler = signal.getsignal(pipe) if pipe is not None else None
        try:
            gmsh.initialize(["-noenv"])
            # Gmsh changes the native SIGPIPE handler behind Python's back. Keep a disconnected
            # HTTP/worker pipe as BrokenPipeError instead of terminating the entire process.
            if pipe is not None:
                signal.signal(pipe, pipe_handler)
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
            try:
                if gmsh.isInitialized():
                    gmsh.finalize()
            finally:
                if pipe is not None:
                    signal.signal(pipe, pipe_handler)
    idx = np.zeros(int(ntags.max()) + 1, dtype=np.int64)
    idx[ntags.astype(np.int64)] = np.arange(len(ntags))
    k = list(etypes).index(4)  # 4-node tetrahedron
    tets = idx[np.asarray(enodes[k], dtype=np.int64)].reshape(-1, 4)
    pts = coords.reshape(-1, 3)
    tets = drop_slivers(pts, tets, size)
    used = np.unique(tets)
    remap = -np.ones(len(pts), dtype=np.int64)
    remap[used] = np.arange(len(used))
    return pts[used], remap[tets]


SLIVER_REL = 1e-6     # a tet below this fraction of size^3 counts as a sliver


def drop_slivers(pts, tets, size: float):
    """Near-flat sliver tets (a thin skin meshed coarse) make the element mapping singular: NaN stiffness, and the
    solver dies (fpv_wing pod). They hold no volume to speak of (< SLIVER_REL x size^3 each), so drop them; a mesh
    without slivers comes back unchanged."""
    a, b, c, d = (pts[tets[:, i]] for i in range(4))
    vol = np.abs(np.einsum("ij,ij->i", np.cross(b - a, c - a), d - a)) / 6
    return tets[vol >= SLIVER_REL * size ** 3]


def stiffness(basis, lam: float, mu: float, chunk: int = 8000):
    """Isotropic linear-elastic stiffness matrix, vectorised over elements (same matrix as skfem's
    asm(linear_elasticity(lam, mu), basis), ~8x faster; tests/test_fea.py compares them). Chunked to bound memory."""
    from scipy.sparse import coo_matrix
    nd, nel = basis.Nbfun, basis.element_dofs.shape[1]
    rows, cols, vals = [], [], []
    for e0 in range(0, nel, chunk):
        sl = slice(e0, min(e0 + chunk, nel))
        G = np.stack([basis.basis[i][0].grad[:, :, sl] for i in range(nd)])   # (dof, comp, dir, elem, qp)
        dx = basis.dx[sl]
        eps = 0.5 * (G + G.transpose(0, 2, 1, 3, 4))
        div = np.einsum("iaaeq->ieq", G)
        Ke = (2 * mu * np.einsum("iabeq,jabeq,eq->ije", eps, eps, dx, optimize=True)
              + lam * np.einsum("ieq,jeq,eq->ije", div, div, dx, optimize=True))
        ed = basis.element_dofs[:, sl]
        rows.append(np.broadcast_to(ed[:, None, :], Ke.shape).ravel())
        cols.append(np.broadcast_to(ed[None, :, :], Ke.shape).ravel())
        vals.append(Ke.ravel())
    K = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(basis.N, basis.N)).tocsr()
    K.sum_duplicates()
    # couplings that cancel exactly in exact arithmetic come out as +-1e-13 round-off here; leaving them in changes the
    # sparsity pattern pyamg aggregates on (and broke convergence on servo_link's arm), so drop them
    K.data[np.abs(K.data) < 1e-10 * np.abs(K.data).max()] = 0.0
    K.eliminate_zeros()
    K.sort_indices()
    return K


AMG_MAXITER = 600


def static(shape, E_mpa: float, nu: float, fixed, loads, size: float | None = None, _depth: int = 0) -> dict:
    from skfem import Basis, ElementTetP2, ElementVector, FacetBasis, MeshTet, asm, condense
    from skfem.helpers import eye, sym_grad, trace
    from skfem.models.elasticity import lame_parameters

    bb = shape.bounding_box()
    size = size or max(min(bb.size.X, bb.size.Y, bb.size.Z) / 4.0, 0.6)  # coarser meshes under-represent curved sections
    pts, tets = _mesh(shape, size)
    while len(tets) > MAX_TETS:  # quadratic elements: memory grows fast; coarsen rather than run out of RAM
        size *= 1.4
        pts, tets = _mesh(shape, size)
    mesh = MeshTet(pts.T, tets.T)
    elem = ElementVector(ElementTetP2())
    sel = []
    for ld in loads:
        ld = ld if isinstance(ld, dict) else {"pred": ld[0], "force": ld[1]}
        pred = ld["pred"]
        facets = mesh.facets_satisfying(lambda x: pred(x[0], x[1], x[2]), boundaries_only=True)
        if len(facets) == 0:
            raise ValueError("a load region selects no boundary faces")
        sel.append((ld, facets))
    fixed_facets = mesh.facets_satisfying(lambda x: fixed(x[0], x[1], x[2]), boundaries_only=True)
    if len(fixed_facets) == 0:
        raise ValueError("the fixed region selects no boundary faces")
    cdir = _cache_dir()
    cfile = os.path.join(cdir, _key(E_mpa, nu, pts, tets, fixed_facets, sel) + ".pkl") if cdir else None
    if cfile and os.path.exists(cfile):
        import pickle
        try:
            with open(cfile, "rb") as fh:
                return dict(pickle.load(fh), cached=True)
        except Exception:  # noqa: BLE001 - a damaged cache entry is just a miss
            pass
    basis = Basis(mesh, elem, intorder=4)          # stresses are sampled at these points
    lam, mu = lame_parameters(E_mpa, nu)
    # P2 gradients are linear on a straight-sided tet, so the stiffness integrand is quadratic: order 2 is exact.
    K = stiffness(Basis(mesh, elem, intorder=2), lam, mu)
    f = np.zeros(K.shape[0])
    for ld, facets in sel:
        fb = FacetBasis(mesh, elem, facets=facets, intorder=4)
        f += asm(_traction(ld, fb), fb)
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
    xI = ml.solve(b, tol=1e-9, accel="cg", maxiter=AMG_MAXITER, residuals=res_hist)
    if res_hist and res_hist[-1] > 1e-6 * max(res_hist[0], 1e-30):
        # AMG+CG occasionally stalls on a load case (seen on slender parts loaded sideways). Small systems are
        # solved directly instead (sparse LU, exact up to round-off). A system too big for that is re-meshed 1.4x
        # coarser (P2 tets keep bending accurate at a few elements through the thickness) until it fits, and the
        # result says so; only after 6 coarsenings does it fail.
        if A.shape[0] > DIRECT_MAX_DOFS:
            ratio = res_hist[-1] / res_hist[0]
            if _depth >= 6:
                raise RuntimeError(f"FEA solver did not converge (residual ratio {ratio:.1e}) and {A.shape[0]} unknowns "
                                   "is too many for the direct fallback, even after coarsening the mesh 6 times")
            r = static(shape, E_mpa, nu, fixed, loads, size=size * 1.4, _depth=_depth + 1)
            r = dict(r, solver_note=r.get("solver_note") or (f"iterative solver stalled on a {size:.2f} mm mesh "
                                                              f"({A.shape[0]} unknowns); solved exactly on a coarser mesh"))
            if cfile:
                import pickle
                with open(cfile + ".tmp", "wb") as fh:
                    pickle.dump({k: v for k, v in r.items() if k != "cached"}, fh)
                os.replace(cfile + ".tmp", cfile)
            return dict(r, cached=False)
        from scipy.sparse.linalg import spsolve
        xI = spsolve(A.tocsc(), b)
        if np.linalg.norm(A @ xI - b) > 1e-6 * max(np.linalg.norm(b), 1e-30):
            raise RuntimeError("FEA direct fallback solve failed")
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
    # the stress FIELD, not just its peak: element centroids, volumes and mean von Mises, so callers can say where
    # material works and where it idles (requirements.stress_map)
    P = mesh.p[:, mesh.t]                                       # 3 x 4 corners x elements
    vol = np.abs(np.einsum("ij...,ij...->...", np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0], axis=0)[None],
                           (P[:, 3] - P[:, 0])[None])) / 6.0
    field = {"c": P.mean(axis=1).T.astype(np.float32), "vol": vol.astype(np.float32), "vm": vm_el.astype(np.float32)}
    res = {"applied_force_n": Fapp.round(4).tolist(), "applied_moment_nmm": Mapp.round(3).tolist(), "_viz": viz, "_field": field,
            "max_vm_mpa": float(np.percentile(vm, 99.9)), "max_vm_peak_mpa": float(vm.max()), "median_vm_mpa": float(np.median(vm)),
            "max_disp_mm": float(np.linalg.norm(disp, axis=1).max()),
            "max_disp_at": mesh.p[:, int(np.argmax(np.linalg.norm(disp, axis=1)))].round(1).tolist(),
            "max_vm_peak_at": mesh.p[:, mesh.t[:, int(np.argmax(vm.max(axis=1)))]].mean(axis=1).round(1).tolist(),
            "nodes": int(mesh.p.shape[1]), "elements": int(mesh.t.shape[1]),
            # external work f.u (N*mm) = twice the strain energy: the load set's compliance is work / |F|^2, so dynamic
            # checks (kerf/req_dynamic.py) get the part's stiffness for impacts and natural frequencies from one solve
            "work_nmm": float(f @ u)}
    if cfile:
        import pickle
        tmp = cfile + f".{os.getpid()}.tmp"
        with open(tmp, "wb") as fh:
            pickle.dump(res, fh)
        os.replace(tmp, cfile)                     # atomic: parallel runs never read a half-written entry
    return dict(res, cached=False)


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
        # a pure couple: subtract the mean tangential vector so a region off the axis (e.g. a servo's 4 tab screws,
        # centred on the case, not the output) gets no net force; the moment about the axis stays exactly `torque`
        area = asm(Functional(lambda w: 1.0 + 0.0 * w.x[0]), fb)
        tbar = [asm(Functional(lambda w, i=i: tang(w.x)[i]), fb) / area for i in range(3)]
        polar = asm(Functional(lambda w: sum(c ** 2 for c in tang(w.x))), fb)   # integral of r_perp^2 dA
        polar -= area * sum(c * c for c in tbar)
        k = float(ld["torque"]) / polar
        return LinearForm(lambda v, w: k * sum((c - tbar[i]) * v[i] for i, c in enumerate(tang(w.x))))
    if "bearing" in ld:
        F = np.asarray(ld["bearing"], float)
        Fm = float(np.linalg.norm(F))
        e = F / Fm

        def cos_pos(w):  # how squarely each face point faces the load; the outward normal of a bore points inward
            return np.maximum(0.0, -(w.n[0] * e[0] + w.n[1] * e[1] + w.n[2] * e[2]))
        q = Fm / asm(Functional(lambda w: cos_pos(w) ** 2), fb)
        return LinearForm(lambda v, w: -q * cos_pos(w) * (w.n[0] * v[0] + w.n[1] * v[1] + w.n[2] * v[2]))
    raise ValueError(f"load needs force, pressure, torque or bearing: {sorted(ld)}")
