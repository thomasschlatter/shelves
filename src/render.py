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


def hero(parts, elev, azim, fname, bg="white"):
    """Nicer single-collection render: all faces shaded by a light direction and
    globally depth-sorted, so records inside the cubbies show correctly."""
    L = np.array([0.35, -0.45, 0.82])          # light dir (x, y=depth, z=up)
    L = L / np.linalg.norm(L)
    amb = 0.45

    tris, cols = [], []
    for mesh in parts.values():
        v = mesh.vertices[mesh.faces]           # (F, 3, 3)
        base = np.asarray(mesh.visual.face_colors)[:, :3] / 255.0
        shade = amb + (1 - amb) * np.clip(mesh.face_normals @ L, 0, 1)
        tris.append(v)
        cols.append(base * shade[:, None])
    tris = np.concatenate(tris)
    cols = np.concatenate(cols)

    fig = plt.figure(figsize=(11, 8))
    ax = fig.add_subplot(111, projection="3d")
    fig.patch.set_facecolor(bg); ax.set_facecolor(bg)
    pc = Poly3DCollection(tris, linewidths=0)
    pc.set_facecolor(np.clip(cols, 0, 1))
    pc.set_sort_zpos(None)
    ax.add_collection3d(pc)

    allv = tris.reshape(-1, 3)
    c = (allv.min(0) + allv.max(0)) / 2
    s = (allv.max(0) - allv.min(0)).max() / 2
    for lim, cc in zip("xyz", c):
        getattr(ax, f"set_{lim}lim")(cc - s, cc + s)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.savefig(os.path.join(OUT, fname), dpi=150, facecolor=bg,
                bbox_inches="tight")
    plt.close(fig)
    print("wrote", os.path.join(OUT, fname))


if __name__ == "__main__":
    parts = m.build_parts()
    view(parts, 20, -60, "iso_front.png")
    view(parts, 18, -120, "iso_back.png")
    view(parts, 22, -60, "exploded.png", explode=0.6)

    vinyl = m.build_parts(m.ROW_DEPTH_STD, with_records=True)
    hero(vinyl, 26, -58, "hero_with_vinyl.png")

    seven = m.build_parts(m.ROW_DEPTH_STD, with_records=True, seven_inch_cols={1, 2})
    hero(seven, 24, -58, "hero_7inch.png")

    four = m.build_parts(m.ROW_DEPTH_STD, with_records=True,
                         layout=["lp", "7", "7", "7", "7", "lp"])
    hero(four, 22, -58, "hero_2lp_4x7.png")
