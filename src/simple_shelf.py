"""
A very simple 7" (45 rpm) record bin: ONE level, 4 compartments, no 12" bays,
no stepped back tier, no legs. Just an open box with three dividers.

Reuses the shared helpers/colours from record_storage. Units are INCHES.
Exports a named-node GLB, STL/OBJ, per-part STLs, a viewer, a cut diagram,
and a hero render.
"""
import os
from collections import OrderedDict

import numpy as np
import trimesh
from shapely.geometry import Polygon

import record_storage as rs
import build_viewer as bv
import render
import cutsheet

# --- Parameters (inches) --------------------------------------------------
T = rs.T                 # 3/4" plywood
BAYS = 4                 # 4 compartments
BAY_W = 8.0              # clear width per compartment (7 1/4" sleeve + room)
DEPTH = 9.0              # front-to-back
BACK_H = 8.0             # slanted: back panel height
FRONT_H = 4.0            # slanted: front panel height (lower, to flip through)
FLAT_H = 6.0             # flat version: front == back height
DIV_H = 4.5              # divider height
REC_N = 8                # records shown per compartment

W = BAYS * BAY_W + (BAYS - 1) * T + 2 * T     # overall width
IX0, IX1 = T, W - T

AXIS_PERM = rs.AXIS_PERM


def side(x0, front_h, back_h):
    """Side panel: DEPTH deep. Wedge if front_h != back_h, rectangle if equal."""
    poly = Polygon([(0, 0), (0, front_h), (DEPTH, back_h), (DEPTH, 0)])
    m = trimesh.creation.extrude_polygon(poly, height=T)
    m.apply_transform(AXIS_PERM)
    m.apply_translation(-m.bounds[0])
    m.apply_translation((x0, 0, 0))
    m.visual.face_colors = rs.WOOD_STRUCT
    return m


def build_parts(with_records=False, front_h=FRONT_H, back_h=BACK_H):
    p = OrderedDict()
    p["side_left"] = side(0.0, front_h, back_h)
    p["side_right"] = side(W - T, front_h, back_h)
    p["bottom"] = rs.plate(IX0, IX1, 0, DEPTH, 0, T, rs.WOOD_STRUCT)
    p["back"] = rs.plate(IX0, IX1, DEPTH - T, DEPTH, T, back_h, rs.WOOD_STRUCT)
    p["front"] = rs.plate(IX0, IX1, 0, T, T, front_h, rs.WOOD_STRUCT)

    edges = np.linspace(IX0, IX1, BAYS + 1)
    for i, xc in enumerate(edges[1:-1], 1):
        p[f"divider_{i}"] = rs.plate(xc - T / 2, xc + T / 2, T, DEPTH - T,
                                     T, T + DIV_H, rs.WOOD_STRUCT)

    if with_records:
        centers = (edges[:-1] + edges[1:]) / 2
        for k, cx in enumerate(centers):
            p[f"records_{k+1}"] = rs.record_stack(
                cx, T + 0.4, T, REC_N,
                rs.RECORD_COLORS[k % len(rs.RECORD_COLORS)], rs.RECORD7_SIZE)
    return p


def emit(slug, label, front_h, back_h):
    here = os.path.dirname(__file__)
    parts = build_parts(front_h=front_h, back_h=back_h)
    rs.export(parts, os.path.join(here, "..", "models", slug))
    b = np.round(trimesh.util.concatenate(list(parts.values())).bounds, 2)
    top = max(front_h, back_h)
    print(f"[{label}] {len(parts)} parts  "
          f"W×D×H = {b[1][0]-b[0][0]:.2f} × {b[1][1]-b[0][1]:.2f} × "
          f"{top:.2f} in  ({(b[1][0]-b[0][0])*2.54:.0f} cm wide)")

    rec = build_parts(with_records=True, front_h=front_h, back_h=back_h)
    bv.write_viewer(rec, f"{label} · {W:.2f} × {DEPTH} × {top:.1f} in",
                    f"viewer_{slug}.html")
    render.hero(rec, 26, -60, f"hero_{slug}.png")
    cutsheet.draw(parts, f'{label} — Cut Diagram', f"cut_diagram_{slug}.png", unit="in")
    cutsheet.draw(parts, f'{label} — Cut Diagram (cm)',
                  f"cut_diagram_{slug}_cm.png", unit="cm")
    with open(os.path.join(here, "..", "plans", f"cut_list_{slug}.txt"),
              "w", encoding="utf-8") as f:
        f.write(cutsheet.cut_list_text(
            parts, f'{label.upper()}  ({W:.2f}" / {W*2.54:.1f} cm wide)'))


def main():
    emit("simple_7inch", "Simple 4x 7\" bin (slanted)", FRONT_H, BACK_H)
    emit("simple_7inch_flat", "Simple 4x 7\" bin (flat)", FLAT_H, FLAT_H)


if __name__ == "__main__":
    main()
