"""Von Mises colour picture of one FEA check, for the reviewer: out/renders/fea_<id>.png.

Two views of the part surface (front-iso and back-iso, part frame), shaded, coloured from 0 (blue) to the smaller of
the peak and the allowable stress (red), so the stress pattern is visible even in a lightly loaded part; anything
above the allowable is drawn magenta so overstressed spots can't hide in the colour scale.
"""
from __future__ import annotations

import numpy as np


def render(viz: dict, path, title: str = "") -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm, colors
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    tris, vm, allow = np.asarray(viz["tris"]), np.asarray(viz["vm"]), float(viz["allow"])
    cmap = matplotlib.colormaps["jet"].with_extremes(over="magenta")
    top = min(allow, float(vm.max())) or allow
    norm = colors.Normalize(0, top)
    fc = cmap(norm(vm))
    fc[vm > allow] = colors.to_rgba("magenta")
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
    light = np.array([0.3, -0.5, 0.8]) / np.linalg.norm([0.3, -0.5, 0.8])
    fc[:, :3] *= (0.55 + 0.45 * np.abs(nrm @ light))[:, None]
    lo, hi = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
    mid, span = (lo + hi) / 2, (hi - lo).max() / 2
    fig = plt.figure(figsize=(12, 6), dpi=110)
    for k, (elev, azim) in enumerate(((25, -60), (25, 120))):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        ax.add_collection3d(Poly3DCollection(tris, facecolors=fc, edgecolors="none"))
        for set_lim, c in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), mid):
            set_lim(c - span, c + span)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev, azim)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_zlabel("z")
    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    fig.colorbar(sm, ax=fig.axes, shrink=0.6, extend="max",
                 label=f"von Mises (MPa), scale 0-{top:.2f}; magenta = over the {allow:.1f} MPa limit")
    fig.suptitle(f"{title}   peak {vm.max():.2f} MPa")
    fig.savefig(str(path))
    plt.close(fig)
    return str(path)
