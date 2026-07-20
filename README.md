# Vinyl Record Storage — 3D Model

A parametric 3D model of the **Jen Woodhouse "8-Cubby Vinyl Record Storage"**,
built to the official published cut list and assembly steps.

Reference / plans: <https://jenwoodhouse.com/vinyl-record-storage/>

## Interactive viewer

Open **`viewer.html`** in a browser (double-click). It renders the model with
real lighting and lets you:

- **Explode** the assembly with a slider to pull every board apart
- **Show / hide** or **isolate** any individual part
- toggle the legs, wireframe, and auto-rotate
- orbit / zoom / pan

> The viewer loads three.js from a CDN, so it needs an internet connection the
> first time.

## Design

A "stadium-seating" record bin on hairpin legs, holding ~350 records in **8
cubbies** (two rows of four). Front-row records sit on the bottom and lean
against the 10½″ shelf divider; back-row records sit on a raised platform and
lean against the full-height back panel. The side panels are cut to a wedge —
7″ at the front, 18½″ at the back.

### Official cut list (¾″ plywood unless noted)

| Qty | Part | Size |
|----:|------|------|
| 1 | bottom | 53¾ × 24¾ |
| 1 | back | 53¾ × 18½ |
| 1 | back shelf bottom | 53¾ × 12 |
| 1 | back shelf support | 53¾ × 5 |
| 1 | shelf divider | 53¾ × 10½ |
| 6 | record dividers | 12 × 4¾ |
| 2 | sides (wedge) | 26¼ × 18½ |
| 1 | front | 53¾ × 7 |
| 3 | 2×2 × 8ft boards | support frame under the bottom |
| 4 | steel hairpin legs | 28″ |

**Overall:** 55¼″ W × 26¼″ D × 18½″ H carcass, ~46½″ tall on the legs.

## Usage

```bash
pip install numpy trimesh shapely
python src/record_storage.py     # -> models/*.stl, *.obj, *.glb + models/parts/*.stl
python src/build_viewer.py       # -> viewer.html (geometry baked in)

pip install matplotlib
python src/render.py             # -> renders/*.png static previews
```

The model is fully parametric — edit the constants at the top of
`src/record_storage.py` (e.g. `CUBBIES_PER_TIER = 3` for the 6-cubby version)
and everything rebuilds.

## Outputs

- `models/vinyl_record_storage.glb` — named-node scene (each board selectable)
- `models/vinyl_record_storage.stl` / `.obj` — whole assembly
- `models/parts/*.stl` — one file per constituent piece (24 parts)
- `viewer.html` — self-contained interactive exploded viewer

## Repository layout

```
src/         model, viewer generator, static renderer
models/      exported meshes (whole + per-part)
renders/     static preview images
reference/   source plan thumbnail (kept local, not committed)
```

> Geometry follows the published Jen Woodhouse plan dimensions. For the official
> step-by-step build instructions, hardware, and printable plans, see the source
> linked above.
