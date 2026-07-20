"""
Parametric 3D model of the Jen Woodhouse "8-Cubby Vinyl Record Storage".

Reference: https://jenwoodhouse.com/vinyl-record-storage/
Built to the OFFICIAL cut list & assembly (8-Cubby plan, © 2018 Jen Woodhouse):

  CUT LIST (3/4" plywood unless noted)
    (1) bottom             53 3/4 x 24 3/4
    (1) back               53 3/4 x 18 1/2
    (1) back shelf bottom  53 3/4 x 12          (raised back-tier floor)
    (1) back shelf support 53 3/4 x 5           (riser under back shelf)
    (1) shelf divider      53 3/4 x 10 1/2      (step wall, front/back tiers)
    (6) record dividers    12 x 4 3/4           (3 per tier -> 4 cubbies each)
    (2) sides              26 1/4 x 18 1/2      (cut to a wedge)
    (1) front              53 3/4 x 7
    (3) 2x2 x 8 ft boards  -> support frame under the bottom
    (4) 28" steel hairpin legs

Design: a stadium-seating record bin. Front tier records sit on the bottom and
lean against the 10 1/2" shelf divider; the back tier sits on a raised platform
and leans against the full-height back. Two rows of four cubbies = 8 total.

Every board is a SEPARATE, NAMED part so the assembly can be exploded.
Units are INCHES. Frame: x = width, y = depth (front->back), z = height.

Requires: numpy, trimesh, shapely
"""

import os
from collections import OrderedDict

import numpy as np
import trimesh
from shapely.geometry import Polygon

# --------------------------------------------------------------------------
# Parameters (inches) — from the official 8-Cubby cut list
# --------------------------------------------------------------------------
W = 55.25          # overall width  (53 3/4 inner + 2 x 3/4 sides)
D = 26.25          # overall depth  (front -> back)
H = 18.50          # overall carcass height (top of back)
T = 0.75           # plywood thickness

FRONT_H = 7.00         # front panel height
BOTTOM_RECESS = 1.50   # bottom panel sits 1 1/2" up from the carcass bottom
SHELF_DIV_H = 10.50    # shelf divider (step wall) height, above bottom panel
SUPPORT_H = 5.00       # back shelf support height, above bottom panel
BACK_SHELF_DEPTH = 12.0
TIER_DEPTH = 12.0      # both tiers are 12" deep (== record divider length)
DIV_LEN = 12.0         # record divider length (depth)
DIV_H = 4.75           # record divider height
CUBBIES_PER_TIER = 4   # -> 3 dividers per tier, 6 total, 8 cubbies

TWO_BY = 1.5           # actual 2x2 dimension
LEG_HEIGHT = 28.0      # 28" hairpin legs
LEG_INSET = 3.0

# Colours (RGBA) ------------------------------------------------------------
WOOD = [181, 136, 89, 255]        # plywood faces (records/dividers/shelves)
WOOD_STRUCT = [150, 110, 68, 255] # carcass panels (slightly darker)
STEEL = [45, 45, 48, 255]         # hairpin legs
FRAME = [120, 92, 60, 255]        # 2x2 support frame

# --------------------------------------------------------------------------
# Derived heights (z = 0 at the carcass bottom edge; legs/floor are negative)
# --------------------------------------------------------------------------
BOT_Z0 = BOTTOM_RECESS            # bottom panel underside
BOT_Z1 = BOTTOM_RECESS + T        # bottom panel top  (front-tier floor)
FRONT_TIER_Z = BOT_Z1             # front records sit here
SHELF_DIV_TOP = BOT_Z1 + SHELF_DIV_H
SUPPORT_TOP = BOT_Z1 + SUPPORT_H
PLATFORM_Z0 = SUPPORT_TOP         # back shelf bottom underside
PLATFORM_Z1 = SUPPORT_TOP + T     # back-tier floor
BACK_TIER_Z = PLATFORM_Z1

IX0, IX1 = T, W - T               # inner width span (between the sides)

# depth landmarks (y)
FRONT_FACE = 0.0
FRONT_INNER = T                   # back face of front panel
BACK_INNER = D - T                # inner face of back panel
PLATFORM_FRONT = BACK_INNER - BACK_SHELF_DEPTH        # 13.5
STEPWALL_Y1 = PLATFORM_FRONT                          # shelf divider back face
STEPWALL_Y0 = PLATFORM_FRONT - T                      # shelf divider front face
SUPPORT_Y0 = PLATFORM_FRONT
SUPPORT_Y1 = PLATFORM_FRONT + T


def plate(x0, x1, y0, y1, z0, z1, color=WOOD):
    """Axis-aligned board from two opposite corners, with a face colour."""
    b = trimesh.creation.box(extents=(x1 - x0, y1 - y0, z1 - z0))
    b.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    b.visual.face_colors = color
    return b


# Wedge side panel: 26 1/4 (deep) x 18 1/2 (back), sloping to the 7" front -----
AXIS_PERM = np.array([[0, 0, 1, 0],   # world_x = poly_z (thickness)
                      [1, 0, 0, 0],   # world_y = poly_x (depth)
                      [0, 1, 0, 0],   # world_z = poly_y (height)
                      [0, 0, 0, 1]], dtype=float)


def side_panel(x0):
    poly = Polygon([(0.0, 0.0), (0.0, FRONT_H), (D, H), (D, 0.0)])
    if not poly.is_valid:
        poly = poly.buffer(0)
    side = trimesh.creation.extrude_polygon(poly, height=T)
    side.apply_transform(AXIS_PERM)
    side.apply_translation(-side.bounds[0])
    side.apply_translation((x0, 0, 0))
    side.visual.face_colors = WOOD_STRUCT
    return side


def hairpin(cx, cy):
    """One 3-rod hairpin leg (steel), merged into a single part."""
    rods = []
    r, foot = 0.20, 4.0
    top_z, bot_z = 0.0, -LEG_HEIGHT
    for a in (0.5, 2.6, 4.4):
        fx, fy = cx + foot * np.cos(a), cy + foot * np.sin(a)
        rods.append(trimesh.creation.cylinder(
            radius=r, segment=[[cx, cy, top_z], [fx, fy, bot_z]]))
    # a small foot pad at the bottom of each rod keeps it tidy
    leg = trimesh.util.concatenate(rods)
    leg.visual.face_colors = STEEL
    return leg


def build_parts():
    """OrderedDict {part_name: Trimesh}."""
    p = OrderedDict()

    # --- Carcass ----------------------------------------------------------
    p["side_left"] = side_panel(0.0)
    p["side_right"] = side_panel(W - T)
    p["back"] = plate(IX0, IX1, BACK_INNER, D, 0.0, H, WOOD_STRUCT)
    p["front"] = plate(IX0, IX1, FRONT_FACE, FRONT_INNER, 0.0, FRONT_H, WOOD_STRUCT)
    p["bottom"] = plate(IX0, IX1, FRONT_INNER, BACK_INNER, BOT_Z0, BOT_Z1, WOOD_STRUCT)

    # --- Back shelf (raised platform) ------------------------------------
    p["shelf_divider"] = plate(IX0, IX1, STEPWALL_Y0, STEPWALL_Y1,
                               BOT_Z1, SHELF_DIV_TOP, WOOD_STRUCT)
    p["back_shelf_support"] = plate(IX0, IX1, SUPPORT_Y0, SUPPORT_Y1,
                                    BOT_Z1, SUPPORT_TOP, WOOD_STRUCT)
    p["back_shelf_bottom"] = plate(IX0, IX1, PLATFORM_FRONT, BACK_INNER,
                                   PLATFORM_Z0, PLATFORM_Z1, WOOD_STRUCT)

    # --- Record dividers: 3 per tier -> 4 cubbies each --------------------
    xs = np.linspace(IX0, IX1, CUBBIES_PER_TIER + 1)[1:-1]
    for j, xc in enumerate(xs, 1):
        p[f"front_divider_{j}"] = plate(
            xc - T / 2, xc + T / 2, FRONT_INNER, FRONT_INNER + DIV_LEN,
            FRONT_TIER_Z, FRONT_TIER_Z + DIV_H)
    for j, xc in enumerate(xs, 1):
        p[f"back_divider_{j}"] = plate(
            xc - T / 2, xc + T / 2, BACK_INNER - DIV_LEN, BACK_INNER,
            BACK_TIER_Z, BACK_TIER_Z + DIV_H)

    # --- 2x2 support frame under the bottom (fills the 1 1/2" recess) -----
    fz0, fz1 = 0.0, TWO_BY
    fx0, fx1 = IX0 + 0.5, IX1 - 0.5
    fy0, fy1 = FRONT_INNER + 0.5, BACK_INNER - 0.5
    p["frame_left"] = plate(fx0, fx0 + TWO_BY, fy0, fy1, fz0, fz1, FRAME)
    p["frame_right"] = plate(fx1 - TWO_BY, fx1, fy0, fy1, fz0, fz1, FRAME)
    p["frame_front"] = plate(fx0 + TWO_BY, fx1 - TWO_BY, fy0, fy0 + TWO_BY,
                             fz0, fz1, FRAME)
    p["frame_back"] = plate(fx0 + TWO_BY, fx1 - TWO_BY, fy1 - TWO_BY, fy1,
                            fz0, fz1, FRAME)
    for j, xc in enumerate(np.linspace(fx0, fx1, 4)[1:-1], 1):
        p[f"frame_cross_{j}"] = plate(xc - TWO_BY / 2, xc + TWO_BY / 2,
                                      fy0 + TWO_BY, fy1 - TWO_BY, fz0, fz1, FRAME)

    # --- Legs -------------------------------------------------------------
    for name, cx, cy in [
        ("leg_front_left",  LEG_INSET,     LEG_INSET),
        ("leg_front_right", W - LEG_INSET, LEG_INSET),
        ("leg_back_left",   LEG_INSET,     D - LEG_INSET),
        ("leg_back_right",  W - LEG_INSET, D - LEG_INSET),
    ]:
        p[name] = hairpin(cx, cy)

    return p


def build_scene(parts=None):
    parts = parts or build_parts()
    scene = trimesh.Scene()
    for name, mesh in parts.items():
        scene.add_geometry(mesh, node_name=name, geom_name=name)
    return scene


def _export(parts, out):
    os.makedirs(out, exist_ok=True)
    parts_dir = os.path.join(out, "parts")
    os.makedirs(parts_dir, exist_ok=True)
    build_scene(parts).export(os.path.join(out, "vinyl_record_storage.glb"))
    combined = trimesh.util.concatenate(list(parts.values()))
    combined.export(os.path.join(out, "vinyl_record_storage.stl"))
    combined.export(os.path.join(out, "vinyl_record_storage.obj"))
    for name, mesh in parts.items():
        mesh.export(os.path.join(parts_dir, f"{name}.stl"))
    return combined


if __name__ == "__main__":
    parts = build_parts()
    out = os.path.join(os.path.dirname(__file__), "..", "models")
    combined = _export(parts, out)

    print(f"Exported {len(parts)} named parts (GLB + STL + OBJ, plus models/parts/*.stl)")
    print(f"Overall bounds (in): {np.round(combined.bounds, 2).tolist()}")
    print("Parts (w x d x h):")
    for name, mesh in parts.items():
        s = np.round(mesh.bounds[1] - mesh.bounds[0], 2)
        print(f"  {name:20s} {s[0]:6.2f} x {s[1]:6.2f} x {s[2]:6.2f}")
