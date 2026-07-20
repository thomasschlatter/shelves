"""Static preview PNGs of the model (matplotlib, headless-safe).

The interactive viewer.html is the primary way to inspect / explode the model;
these are just quick thumbnails for the README.
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import record_storage as m

OUT = os.path.join(os.path.dirname(__file__), "..", "renders")
os.makedirs(OUT, exist_ok=True)


def view(parts, elev, azim, fname, explode=0.0):
    fig = plt.figure(figsize=(9, 7))
    ax = fig.add_subplot(111, projection="3d")

    allv = np.vstack([mesh.vertices for mesh in parts.values()])
    center = (allv.min(0) + allv.max(0)) / 2

    for name, mesh in parts.items():
        v = mesh.vertices.copy()
        if explode:
            pc = (mesh.bounds[0] + mesh.bounds[1]) / 2
            v = v + (pc - center) * explode
        col = np.asarray(mesh.visual.face_colors)[0][:3] / 255.0
        tris = v[mesh.faces]
        p = Poly3DCollection(tris, alpha=1.0)
        p.set_facecolor(col)
        p.set_edgecolor((0, 0, 0, 0.12))
        p.set_linewidth(0.15)
        ax.add_collection3d(p)

    span = (allv.max(0) - allv.min(0)).max() / 2 * (1 + explode * 0.9)
    for lim, c in zip("xyz", center):
        getattr(ax, f"set_{lim}lim")(c - span, c + span)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_xlabel("width"); ax.set_ylabel("depth"); ax.set_zlabel("height")
    ax.set_title("8-Cubby Vinyl Record Storage  —  55¼ × 26¼ × 18½ in")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, fname), dpi=130)
    plt.close(fig)
    print("wrote", os.path.join(OUT, fname))


if __name__ == "__main__":
    parts = m.build_parts()
    view(parts, 20, -60, "iso_front.png")
    view(parts, 18, -120, "iso_back.png")
    view(parts, 22, -60, "exploded.png", explode=0.6)
