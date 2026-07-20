"""
Parametric 3D model of the Jen Woodhouse "8-Cubby Vinyl Record Storage".

Reference: https://jenwoodhouse.com/vinyl-record-storage/
Built to the OFFICIAL cut list & assembly (8-Cubby plan, © 2018 Jen Woodhouse).

Design: a stadium-seating record bin. Front tier records sit on the bottom and
lean against the 10 1/2" shelf divider; the back tier sits on a raised platform
and leans against the full-height back. Two rows of four cubbies = 8 total.

The ROW DEPTH is parametric: `row_depth=12` reproduces the original plan
(26 1/4" deep); a smaller value makes a shallower cabinet that protrudes less
from the wall while keeping both rows and all heights identical.

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
# Width / height parameters (depth is derived from row_depth, see below)
# --------------------------------------------------------------------------
W = 55.25          # overall width  (53 3/4 inner + 2 x 3/4 sides)
H = 18.50          # overall carcass height (top of back)
T = 0.75           # plywood thickness

FRONT_H = 7.00         # front panel height
BOTTOM_RECESS = 1.50   # bottom panel sits 1 1/2" up from the carcass bottom
SHELF_DIV_H = 10.50    # shelf divider (step wall) height, above bottom panel
SUPPORT_H = 5.00       # back shelf support height, above bottom panel
DIV_H = 4.75           # record divider height
CUBBIES_PER_TIER = 4   # -> 3 dividers per tier, 6 total, 8 cubbies

ROW_DEPTH_STD = 12.0     # original plan: each row 12" deep -> 26 1/4" overall
ROW_DEPTH_COMPACT = 8.0  # shallower: each row 8" deep -> 18 1/4" overall

TWO_BY = 1.5           # actual 2x2 dimension
LEG_HEIGHT = 28.0      # 28" hairpin legs
LEG_INSET = 3.0

# Records (12" LP + sleeve ~= 12.5" square) --------------------------------
RECORD_SIZE = 12.5     # 12" LP sleeve width & height
RECORD7_SIZE = 7.25    # 7" 45 rpm sleeve width & height
RECORD_T = 0.22        # sleeve thickness
RECORD_LEAN = 16.0     # lean-back angle from vertical (degrees)
RECORDS_PER_CUBBY = 6
SEVEN_BAY_W = 8.5      # clear width of a 7" (45 rpm) cubby
LP_BAY_W = 12.875      # clear width of a 12" LP cubby (matches the original plan)
RECORD_COLORS = [      # a few sleeve colours to vary the cubbies
    [196, 62, 55, 255], [63, 106, 148, 255], [222, 178, 74, 255],
    [86, 130, 96, 255], [150, 96, 148, 255], [70, 74, 82, 255],
    [201, 118, 66, 255], [120, 160, 168, 255],
]

# Colours (RGBA) ------------------------------------------------------------
WOOD = [181, 136, 89, 255]        # plywood faces (records/dividers/shelves)
WOOD_STRUCT = [150, 110, 68, 255] # carcass panels (slightly darker)
STEEL = [45, 45, 48, 255]         # hairpin legs
FRAME = [120, 92, 60, 255]        # 2x2 support frame

# Constant heights (z = 0 at the carcass bottom edge; legs/floor are negative)
BOT_Z0 = BOTTOM_RECESS            # bottom panel underside
BOT_Z1 = BOTTOM_RECESS + T        # bottom panel top  (front-tier floor)
SHELF_DIV_TOP = BOT_Z1 + SHELF_DIV_H
SUPPORT_TOP = BOT_Z1 + SUPPORT_H
PLATFORM_Z0 = SUPPORT_TOP         # back shelf bottom underside
PLATFORM_Z1 = SUPPORT_TOP + T     # back-tier floor

IX0, IX1 = T, W - T               # inner width span (between the sides)

AXIS_PERM = np.array([[0, 0, 1, 0],   # world_x = poly_z (thickness)
                      [1, 0, 0, 0],   # world_y = poly_x (depth)
                      [0, 1, 0, 0],   # world_z = poly_y (height)
                      [0, 0, 0, 1]], dtype=float)


def overall_depth(row_depth):
    """Front panel + front row + shelf divider + back row + back panel."""
    return 3 * T + 2 * row_depth


def plate(x0, x1, y0, y1, z0, z1, color=WOOD):
    """Axis-aligned board from two opposite corners, with a face colour."""
    b = trimesh.creation.box(extents=(x1 - x0, y1 - y0, z1 - z0))
    b.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    b.visual.face_colors = color
    return b


def side_panel(x0, D):
    """Wedge side: D deep, 18 1/2" at the back, sloping to the 7" front."""
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
    for a in (0.5, 2.6, 4.4):
        fx, fy = cx + foot * np.cos(a), cy + foot * np.sin(a)
        rods.append(trimesh.creation.cylinder(
            radius=r, segment=[[cx, cy, 0.0], [fx, fy, -LEG_HEIGHT]]))
    leg = trimesh.util.concatenate(rods)
    leg.visual.face_colors = STEEL
    return leg


def record_stack(cx, y_front, z_floor, n, color, size=RECORD_SIZE):
    """A leaning stack of n record sleeves in one cubby, merged to one mesh.
    Sleeves stand on z_floor, front edge at y_front, leaning back by RECORD_LEAN."""
    lean = np.radians(RECORD_LEAN)
    step = RECORD_T / np.cos(lean) + 0.03      # back offset per sleeve
    rot = trimesh.transformations.rotation_matrix(-lean, [1, 0, 0])
    recs = []
    for i in range(n):
        r = trimesh.creation.box(extents=(size, RECORD_T, size))
        r.apply_translation((0, RECORD_T / 2, size / 2))         # corner at origin
        r.apply_transform(rot)                                   # lean back
        r.apply_translation((cx, y_front + i * step, z_floor))
        recs.append(r)
    stack = trimesh.util.concatenate(recs)
    stack.visual.face_colors = color
    return stack


def build_parts(row_depth=ROW_DEPTH_STD, with_records=False,
                seven_inch_cols=None, layout=None):
    """OrderedDict {part_name: Trimesh} for the given per-row depth (inches).

    Column layout (left -> right) is either:
      * `layout`: an explicit list of "lp"/"7" bay kinds, e.g.
        ["lp", "7", "7", "7", "lp"] for 2 LP columns flanking 3 seven-inch bays; or
      * `seven_inch_cols`: indices into CUBBIES_PER_TIER equal columns to convert
        to 7" bays (e.g. {1, 2} for the two middle columns).
    7" bays are narrower and hold shorter sleeves that share the LP floor
    (bottom edges aligned). Overall width is derived from the bay widths.
    """
    D = overall_depth(row_depth)
    div_len = row_depth                        # dividers span the full row depth

    # width is DERIVED from the cubby widths (LP bays match the original plan;
    # 7" bays are narrower) — the overall cabinet gets narrower rather than
    # stretching the LP columns.
    if layout is None:
        layout = ["lp"] * CUBBIES_PER_TIER
        for c in (seven_inch_cols or []):
            layout[c] = "7"
    n = len(layout)
    widths = [SEVEN_BAY_W if k == "7" else LP_BAY_W for k in layout]
    inner_w = sum(widths) + (n - 1) * T
    Wloc = inner_w + 2 * T
    ix0, ix1 = T, Wloc - T

    # depth landmarks (y, front -> back)
    FRONT_FACE = 0.0
    FRONT_INNER = T                            # back face of front panel
    BACK_INNER = D - T                         # inner face of back panel
    STEPWALL_Y0 = FRONT_INNER + row_depth      # shelf divider front face
    STEPWALL_Y1 = STEPWALL_Y0 + T              # shelf divider back face
    SUPPORT_Y0 = STEPWALL_Y1                   # support just behind the divider
    SUPPORT_Y1 = SUPPORT_Y0 + T
    PLATFORM_FRONT = STEPWALL_Y1               # raised platform starts here

    p = OrderedDict()

    # --- Carcass ----------------------------------------------------------
    p["side_left"] = side_panel(0.0, D)
    p["side_right"] = side_panel(Wloc - T, D)
    p["back"] = plate(ix0, ix1, BACK_INNER, D, 0.0, H, WOOD_STRUCT)
    p["front"] = plate(ix0, ix1, FRONT_FACE, FRONT_INNER, 0.0, FRONT_H, WOOD_STRUCT)
    p["bottom"] = plate(ix0, ix1, FRONT_INNER, BACK_INNER, BOT_Z0, BOT_Z1, WOOD_STRUCT)

    # --- Back shelf (raised platform) ------------------------------------
    p["shelf_divider"] = plate(ix0, ix1, STEPWALL_Y0, STEPWALL_Y1,
                               BOT_Z1, SHELF_DIV_TOP, WOOD_STRUCT)
    p["back_shelf_support"] = plate(ix0, ix1, SUPPORT_Y0, SUPPORT_Y1,
                                    BOT_Z1, SUPPORT_TOP, WOOD_STRUCT)
    p["back_shelf_bottom"] = plate(ix0, ix1, PLATFORM_FRONT, BACK_INNER,
                                   PLATFORM_Z0, PLATFORM_Z1, WOOD_STRUCT)

    # --- Cubby layout: dividers, optional 7" sections, records -----------
    cols, divs, x = [], [], ix0
    for i, w in enumerate(widths):
        cols.append((x, x + w)); x += w
        if i < n - 1:
            divs.append(x + T / 2); x += T
    centers = [(a + b) / 2 for a, b in cols]

    # dividers — uniform height. The 7" columns are simply narrower, and the
    # 45s just shorter; they share the same floor as the LPs.
    for i, xc in enumerate(divs, start=1):
        p[f"front_divider_{i}"] = plate(xc - T / 2, xc + T / 2,
                                        FRONT_INNER, FRONT_INNER + div_len,
                                        BOT_Z1, BOT_Z1 + DIV_H)
        p[f"back_divider_{i}"] = plate(xc - T / 2, xc + T / 2,
                                       BACK_INNER - div_len, BACK_INNER,
                                       PLATFORM_Z1, PLATFORM_Z1 + DIV_H)

    # --- Records leaning in each cubby (optional) ------------------------
    # 7" 45s sit on the SAME floor as the 12" LPs (bottom edges aligned); they
    # are simply smaller, so no raised floor or extra lip is needed — the front
    # panel and shelf divider retain them exactly like the LPs.
    if with_records:
        for k, cx in enumerate(centers):
            size = RECORD7_SIZE if layout[k] == "7" else RECORD_SIZE
            p[f"records_front_{k+1}"] = record_stack(
                cx, FRONT_INNER + 0.5, BOT_Z1, RECORDS_PER_CUBBY,
                RECORD_COLORS[k % len(RECORD_COLORS)], size)
            p[f"records_back_{k+1}"] = record_stack(
                cx, PLATFORM_FRONT + 0.5, PLATFORM_Z1, RECORDS_PER_CUBBY,
                RECORD_COLORS[(k + 4) % len(RECORD_COLORS)], size)

    # --- 2x2 support frame under the bottom (fills the 1 1/2" recess) -----
    fz0, fz1 = 0.0, TWO_BY
    fx0, fx1 = ix0 + 0.5, ix1 - 0.5
    fy0, fy1 = FRONT_INNER + 0.5, BACK_INNER - 0.5
    p["frame_left"] = plate(fx0, fx0 + TWO_BY, fy0, fy1, fz0, fz1, FRAME)
    p["frame_right"] = plate(fx1 - TWO_BY, fx1, fy0, fy1, fz0, fz1, FRAME)
    p["frame_front"] = plate(fx0 + TWO_BY, fx1 - TWO_BY, fy0, fy0 + TWO_BY,
                             fz0, fz1, FRAME)
    p["frame_back"] = plate(fx0 + TWO_BY, fx1 - TWO_BY, fy1 - TWO_BY, fy1,
                            fz0, fz1, FRAME)
    ncross = max(1, int(round((fx1 - fx0) / 18)))    # a cross every ~18"
    for j, xc in enumerate(np.linspace(fx0, fx1, ncross + 2)[1:-1], 1):
        p[f"frame_cross_{j}"] = plate(xc - TWO_BY / 2, xc + TWO_BY / 2,
                                      fy0 + TWO_BY, fy1 - TWO_BY, fz0, fz1, FRAME)

    # --- Legs -------------------------------------------------------------
    for name, cx, cy in [
        ("leg_front_left",  LEG_INSET,      LEG_INSET),
        ("leg_front_right", Wloc - LEG_INSET, LEG_INSET),
        ("leg_back_left",   LEG_INSET,      D - LEG_INSET),
        ("leg_back_right",  Wloc - LEG_INSET, D - LEG_INSET),
    ]:
        p[name] = hairpin(cx, cy)

    return p


def build_scene(parts=None, row_depth=ROW_DEPTH_STD):
    parts = parts or build_parts(row_depth)
    scene = trimesh.Scene()
    for name, mesh in parts.items():
        scene.add_geometry(mesh, node_name=name, geom_name=name)
    return scene


def export(parts, out):
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


def _report(name, parts):
    combined = trimesh.util.concatenate(list(parts.values()))
    b = np.round(combined.bounds, 2)
    print(f"[{name}] {len(parts)} parts  overall(in) W×D×H = "
          f"{b[1][0]-b[0][0]:.2f} × {b[1][1]-b[0][1]:.2f} × {b[1][2]-b[0][2]:.2f}")


if __name__ == "__main__":
    here = os.path.dirname(__file__)

    std = build_parts(ROW_DEPTH_STD)
    export(std, os.path.join(here, "..", "models"))
    _report("standard  row=12", std)

    compact = build_parts(ROW_DEPTH_COMPACT)
    export(compact, os.path.join(here, "..", "models", "compact"))
    _report("compact   row=8 ", compact)

    seven = build_parts(ROW_DEPTH_STD, seven_inch_cols={1, 2})
    export(seven, os.path.join(here, "..", "models", "seven_inch"))
    _report("7-in mid  row=12", seven)

    seven_compact = build_parts(ROW_DEPTH_COMPACT, seven_inch_cols={1, 2})
    export(seven_compact, os.path.join(here, "..", "models", "compact_seven_inch"))
    _report("7-in cmpt row=8 ", seven_compact)

    three7 = build_parts(ROW_DEPTH_STD, layout=["lp", "7", "7", "7", "lp"])
    export(three7, os.path.join(here, "..", "models", "three_seven_inch"))
    _report("3x7 mid   row=12", three7)

    three7c = build_parts(ROW_DEPTH_COMPACT, layout=["lp", "7", "7", "7", "lp"])
    export(three7c, os.path.join(here, "..", "models", "compact_three_seven_inch"))
    _report("3x7 cmpt  row=8 ", three7c)
