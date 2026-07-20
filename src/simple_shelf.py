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
BACK_H = 8.0             # back panel height
FRONT_H = 4.0            # front panel height (lower, so you can flip through)
DIV_H = 4.5              # divider height
REC_N = 8                # records shown per compartment

W = BAYS * BAY_W + (BAYS - 1) * T + 2 * T     # overall width
IX0, IX1 = T, W - T

AXIS_PERM = rs.AXIS_PERM


def side(x0):
    """Wedge side panel: DEPTH deep, BACK_H at back sloping to FRONT_H at front."""
    poly = Polygon([(0, 0), (0, FRONT_H), (DEPTH, BACK_H), (DEPTH, 0)])
    m = trimesh.creation.extrude_polygon(poly, height=T)
    m.apply_transform(AXIS_PERM)
    m.apply_translation(-m.bounds[0])
    m.apply_translation((x0, 0, 0))
    m.visual.face_colors = rs.WOOD_STRUCT
    return m


def build_parts(with_records=False):
    p = OrderedDict()
    p["side_left"] = side(0.0)
    p["side_right"] = side(W - T)
    p["bottom"] = rs.plate(IX0, IX1, 0, DEPTH, 0, T, rs.WOOD_STRUCT)
    p["back"] = rs.plate(IX0, IX1, DEPTH - T, DEPTH, T, BACK_H, rs.WOOD_STRUCT)
    p["front"] = rs.plate(IX0, IX1, 0, T, T, FRONT_H, rs.WOOD_STRUCT)

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


def main():
    here = os.path.dirname(__file__)
    parts = build_parts()
    out = os.path.join(here, "..", "models", "simple_7inch")
    rs.export(parts, out)
    combined = trimesh.util.concatenate(list(parts.values()))
    b = np.round(combined.bounds, 2)
    print(f"[simple 7\"] {len(parts)} parts  "
          f"W×D×H = {b[1][0]-b[0][0]:.2f} × {b[1][1]-b[0][1]:.2f} × "
          f"{b[1][2]-b[0][2]:.2f} in  ({(b[1][0]-b[0][0])*2.54:.0f} cm wide)")

    # viewer + render + cut diagram
    bv.write_viewer(build_parts(with_records=True),
                    f"Simple 4× 7\" bin · {W:.2f} × {DEPTH} × {BACK_H} in",
                    "viewer_simple_7inch.html")
    render.hero(build_parts(with_records=True), 26, -60, "hero_simple_7inch.png")
    cutsheet.draw(parts, 'Simple 4× 7" Record Bin — Cut Diagram',
                  "cut_diagram_simple_7inch.png", unit="in")
    cutsheet.draw(parts, 'Simple 4× 7" Record Bin — Cut Diagram (cm)',
                  "cut_diagram_simple_7inch_cm.png", unit="cm")
    with open(os.path.join(here, "..", "plans", "cut_list_simple_7inch.txt"),
              "w", encoding="utf-8") as f:
        f.write(cutsheet.cut_list_text(
            parts, f'SIMPLE 4x 7" BIN  ({W:.2f}" / {W*2.54:.1f} cm wide)'))
    print("wrote viewer_simple_7inch.html + plans + hero render")


if __name__ == "__main__":
    main()
