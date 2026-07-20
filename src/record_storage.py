"""
Parametric 3D model of the Jen Woodhouse "Vinyl Record Storage" stepped bin.

Reference: https://jenwoodhouse.com/vinyl-record-storage/
Overall box: 55 1/4" W x 26 1/4" D x 18 1/2" H, on hairpin legs.

The cabinet is a stepped ("stadium seating") record bin: the back wall is
full height and the interior descends toward the front in three tiers. Each
tier is a shelf + riser where LP records lean back so you can flip through
them. Every tier is split into compartments by vertical dividers.

Units are INCHES throughout. Exports OBJ / STL / GLB.

Requires: numpy, trimesh, shapely
"""

import numpy as np
import trimesh

# --------------------------------------------------------------------------
# Parameters (inches)
# --------------------------------------------------------------------------
W = 55.25          # overall width
D = 26.25          # overall depth (front -> back)
H = 18.50          # overall box height (top of back wall)
T = 0.75           # material thickness (3/4" plywood)

N_TIERS = 3        # number of front-to-back tiers (rows of records)
DIVIDERS_PER_TIER = 3   # vertical dividers splitting each tier's width
FRONT_LIP = 4.0    # height of the very front wall

LEG_HEIGHT = 16.0  # hairpin leg height
LEG_INSET = 2.5    # how far legs are set in from the corners

# Derived tier geometry -----------------------------------------------------
tier_depth = D / N_TIERS
# Floor height of each tier, front (lowest) -> back (highest).
# Front tier sits on the bottom; back tier floor is highest.
tier_floor = np.linspace(0.0, H - FRONT_LIP - T, N_TIERS)
# Riser top = the next tier's floor; the last riser reaches full height H.
riser_top = np.append(tier_floor[1:], H)

WOOD = [150, 111, 71, 255]     # plywood colour
STEEL = [40, 40, 40, 255]      # hairpin legs


def box(size, center):
    """Axis-aligned box (size=(dx,dy,dz)) centred at `center`."""
    b = trimesh.creation.box(extents=size)
    b.apply_translation(center)
    return b


def plate(x0, x1, y0, y1, z0, z1):
    """Box from two opposite corners."""
    return box((x1 - x0, y1 - y0, z1 - z0),
               ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


# --------------------------------------------------------------------------
# Coordinate frame:
#   x : width   0 .. W   (left -> right)
#   y : depth   0 .. D   (front -> back)
#   z : height  0 .. H   (bottom of box .. top of back wall)
# The box bottom sits at z = 0; legs live below z = 0.
# --------------------------------------------------------------------------
parts = []

# --- Side panels: a stepped ("staircase") profile extruded across thickness.
# Profile in the depth(y)-height(z) plane, going around the outline.
def side_profile():
    pts = [(0.0, 0.0)]                         # bottom-front
    pts.append((0.0, FRONT_LIP))               # up the front lip
    for i in range(N_TIERS):
        y_front = i * tier_depth
        y_back = (i + 1) * tier_depth
        pts.append((y_front, tier_floor[i] + FRONT_LIP if i == 0 else tier_floor[i]))
        pts.append((y_back, riser_top[i]))     # up-and-over each step
    pts.append((D, 0.0))                        # bottom-back
    return np.array(pts)

# Outer side-panel silhouette: a clean wedge (low front lip -> high back),
# matching the reference. Interior tiers are built separately as shelves.
def side_profile_clean():
    return [(0.0, 0.0), (0.0, FRONT_LIP), (D, H), (D, 0.0)]

from shapely.geometry import Polygon
poly = Polygon(side_profile_clean())
if not poly.is_valid:
    poly = poly.buffer(0)

# Map the polygon's own axes -> world axes:
#   poly_x (depth)     -> world_y
#   poly_y (height)    -> world_z
#   poly_z (thickness) -> world_x
AXIS_PERM = np.array([
    [0, 0, 1, 0],   # world_x = poly_z
    [1, 0, 0, 0],   # world_y = poly_x
    [0, 1, 0, 0],   # world_z = poly_y
    [0, 0, 0, 1],
], dtype=float)

for x0 in (0.0, W - T):                       # left and right side panels
    side = trimesh.creation.extrude_polygon(poly, height=T)
    side.apply_transform(AXIS_PERM)
    side.apply_translation(-side.bounds[0])   # min corner -> origin
    side.apply_translation((x0, 0, 0))
    parts.append(side)

# --- Bottom / floor of the box
parts.append(plate(T, W - T, 0.0, D, 0.0, T))

# --- Back wall (full height)
parts.append(plate(T, W - T, D - T, D, 0.0, H))

# --- Tier shelves + risers + front lip
inner_x0, inner_x1 = T, W - T

# Front lip (very front wall)
parts.append(plate(inner_x0, inner_x1, 0.0, T, 0.0, FRONT_LIP))

for i in range(N_TIERS):
    y_front = i * tier_depth
    y_back = (i + 1) * tier_depth
    zf = tier_floor[i]
    # shelf (floor of this tier)
    parts.append(plate(inner_x0, inner_x1, y_front, y_back, zf, zf + T))
    # riser at the back of this tier (front wall of the tier behind it)
    if i < N_TIERS - 1:
        parts.append(plate(inner_x0, inner_x1, y_back - T, y_back,
                           zf, riser_top[i]))
    # vertical dividers splitting this tier across the width
    xs = np.linspace(inner_x0, inner_x1, DIVIDERS_PER_TIER + 1)[1:-1]
    div_top = riser_top[i]
    for xc in xs:
        parts.append(plate(xc - T / 2, xc + T / 2, y_front, y_back,
                           zf, div_top))

# --- Hairpin legs (simplified: three splayed steel rods per corner)
def hairpin(cx, cy):
    rods = []
    r = 0.18
    foot = 4.5     # splay radius at the floor
    angles = [0.6, 2.7, 4.5]
    for a in angles:
        fx = cx + foot * np.cos(a)
        fy = cy + foot * np.sin(a)
        rod = trimesh.creation.cylinder(
            radius=r,
            segment=[[cx, cy, 0.0], [fx, fy, -LEG_HEIGHT]])
        rods.append(rod)
    return rods

legs = []
for cx in (LEG_INSET, W - LEG_INSET):
    for cy in (LEG_INSET, D - LEG_INSET):
        legs.extend(hairpin(cx, cy))

# --------------------------------------------------------------------------
# Assemble & export
# --------------------------------------------------------------------------
wood_mesh = trimesh.util.concatenate(parts)
wood_mesh.visual.face_colors = WOOD

leg_mesh = trimesh.util.concatenate(legs)
leg_mesh.visual.face_colors = STEEL

scene = trimesh.Scene()
scene.add_geometry(wood_mesh, node_name="cabinet")
scene.add_geometry(leg_mesh, node_name="legs")

if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), "..", "models")
    os.makedirs(out, exist_ok=True)

    combined = trimesh.util.concatenate([wood_mesh, leg_mesh])
    combined.export(os.path.join(out, "vinyl_record_storage.stl"))
    combined.export(os.path.join(out, "vinyl_record_storage.obj"))
    scene.export(os.path.join(out, "vinyl_record_storage.glb"))

    print("Exported STL / OBJ / GLB to models/")
    print(f"Cabinet watertight: {wood_mesh.is_watertight}")
    print(f"Overall bounds (in): {np.round(combined.bounds, 2).tolist()}")
    print(f"Wood volume (cu in): {wood_mesh.volume:.1f}")
