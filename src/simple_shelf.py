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
BAY_W = 8.0              # clear width per compartment (7 1/4" sleeve + room)
DIV_H = 4.5              # divider height

# Slanted variant
BAYS = 4
DEPTH = 9.0
BACK_H = 8.0
FRONT_H = 4.0
REC_N = 8

# Flat variant — deeper (protrudes much more) and an extra compartment
FLAT_BAYS = 5
FLAT_DEPTH = 22.0
FLAT_H = 6.0             # front == back height
FLAT_REC_N = 30          # deep bin holds a lot

AXIS_PERM = rs.AXIS_PERM


def overall_width(bays):
    return bays * BAY_W + (bays - 1) * T + 2 * T


def side(x0, front_h, back_h, depth):
    """Side panel: `depth` deep. Wedge if front_h != back_h, rectangle if equal."""
    poly = Polygon([(0, 0), (0, front_h), (depth, back_h), (depth, 0)])
    m = trimesh.creation.extrude_polygon(poly, height=T)
    m.apply_transform(AXIS_PERM)
    m.apply_translation(-m.bounds[0])
    m.apply_translation((x0, 0, 0))
    m.visual.face_colors = rs.WOOD_STRUCT
    return m


def build_parts(with_records=False, front_h=FRONT_H, back_h=BACK_H,
                depth=DEPTH, rec_n=REC_N, bays=BAYS):
    W = overall_width(bays)
    ix0, ix1 = T, W - T
    p = OrderedDict()
    p["side_left"] = side(0.0, front_h, back_h, depth)
    p["side_right"] = side(W - T, front_h, back_h, depth)
    p["bottom"] = rs.plate(ix0, ix1, 0, depth, 0, T, rs.WOOD_STRUCT)
    p["back"] = rs.plate(ix0, ix1, depth - T, depth, T, back_h, rs.WOOD_STRUCT)
    p["front"] = rs.plate(ix0, ix1, 0, T, T, front_h, rs.WOOD_STRUCT)

    edges = np.linspace(ix0, ix1, bays + 1)
    for i, xc in enumerate(edges[1:-1], 1):
        p[f"divider_{i}"] = rs.plate(xc - T / 2, xc + T / 2, T, depth - T,
                                     T, T + DIV_H, rs.WOOD_STRUCT)

    # 28" steel hairpin legs (same as the original Jen Woodhouse plan)
    for name, cx, cy in [
        ("leg_front_left",  rs.LEG_INSET,      rs.LEG_INSET),
        ("leg_front_right", W - rs.LEG_INSET,  rs.LEG_INSET),
        ("leg_back_left",   rs.LEG_INSET,      depth - rs.LEG_INSET),
        ("leg_back_right",  W - rs.LEG_INSET,  depth - rs.LEG_INSET),
    ]:
        p[name] = rs.hairpin(cx, cy)

    if with_records:
        centers = (edges[:-1] + edges[1:]) / 2
        for k, cx in enumerate(centers):
            p[f"records_{k+1}"] = rs.record_stack(
                cx, T + 0.4, T, rec_n,
                rs.RECORD_COLORS[k % len(rs.RECORD_COLORS)], rs.RECORD7_SIZE)
    return p


def emit(slug, label, front_h, back_h, depth=DEPTH, rec_n=REC_N, bays=BAYS):
    here = os.path.dirname(__file__)
    W = overall_width(bays)
    top = max(front_h, back_h)
    parts = build_parts(front_h=front_h, back_h=back_h, depth=depth, bays=bays)
    rs.export(parts, os.path.join(here, "..", "models", slug))
    print(f"[{label}] {len(parts)} parts  W×D×H = {W:.2f} × {depth:.2f} × "
          f"{top:.2f} in  ({W*2.54:.0f} × {depth*2.54:.0f} × {top*2.54:.0f} cm)")

    rec = build_parts(with_records=True, front_h=front_h, back_h=back_h,
                      depth=depth, rec_n=rec_n, bays=bays)
    bv.write_viewer(rec, f"{label} · {W:.2f} × {depth} × {top:.1f} in",
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
    emit("simple_7inch", "Simple 4x 7\" bin (slanted)", FRONT_H, BACK_H,
         depth=DEPTH, rec_n=REC_N, bays=BAYS)
    emit("simple_7inch_flat", "Simple 5x 7\" bin (flat, deep)", FLAT_H, FLAT_H,
         depth=FLAT_DEPTH, rec_n=FLAT_REC_N, bays=FLAT_BAYS)


if __name__ == "__main__":
    main()
