"""Render preview PNGs of the model with matplotlib (headless-safe)."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import record_storage as m

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "renders")
os.makedirs(OUT, exist_ok=True)


def draw(mesh, color, ax, alpha=1.0):
    tris = mesh.vertices[mesh.faces]
    pc = Poly3DCollection(tris, alpha=alpha)
    pc.set_facecolor(color)
    pc.set_edgecolor((0, 0, 0, 0.12))
    pc.set_linewidth(0.15)
    ax.add_collection3d(pc)


def view(elev, azim, fname):
    fig = plt.figure(figsize=(9, 7))
    ax = fig.add_subplot(111, projection="3d")
    draw(m.wood_mesh, (0.59, 0.44, 0.28), ax)
    draw(m.leg_mesh, (0.15, 0.15, 0.15), ax)

    all_v = np.vstack([m.wood_mesh.vertices, m.leg_mesh.vertices])
    mins, maxs = all_v.min(0), all_v.max(0)
    center = (mins + maxs) / 2
    span = (maxs - mins).max() / 2
    ax.set_xlim(center[0] - span, center[0] + span)
    ax.set_ylim(center[1] - span, center[1] + span)
    ax.set_zlim(center[2] - span, center[2] + span)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_xlabel("width")
    ax.set_ylabel("depth")
    ax.set_zlabel("height")
    ax.set_title("Vinyl Record Storage  —  55¼ × 26¼ × 18½ in")
    fig.tight_layout()
    path = os.path.join(OUT, fname)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print("wrote", path)


def profile():
    """2D side profile sanity check."""
    fig, ax = plt.subplots(figsize=(6, 5))
    pts = np.array(m.side_profile_clean() + [m.side_profile_clean()[0]])
    ax.plot(pts[:, 0], pts[:, 1], "-o", color="#8a6f47")
    ax.fill(pts[:, 0], pts[:, 1], color="#8a6f47", alpha=0.25)
    ax.set_aspect("equal")
    ax.set_xlabel("depth (front → back)")
    ax.set_ylabel("height")
    ax.set_title("Side panel profile")
    ax.grid(True, alpha=0.3)
    path = os.path.join(OUT, "side_profile.png")
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print("wrote", path)


if __name__ == "__main__":
    profile()
    view(22, -60, "iso_front.png")
    view(18, -120, "iso_back.png")
