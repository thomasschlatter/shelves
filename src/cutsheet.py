"""
Generate a plywood CUT DIAGRAM (sheet nesting layout) for the record storage,
similar to page 2 of the official plan: rectangles laid out on 4x8 sheets of
3/4" plywood, each labelled with its part name and size.

Uses a simple first-fit-decreasing shelf packer. Not guaranteed optimal, but
produces a valid, readable layout. The wedge cut line is drawn on the sides.
"""
import os
import random
import re
from collections import Counter
from fractions import Fraction

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MplPolygon
from matplotlib.lines import Line2D

import record_storage as rs


def _convex_hull(pts):
    """Andrew's monotone chain hull of 2D points (CCW, no repeat of first)."""
    pts = sorted(set(pts))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _outline(mesh):
    """Normalised silhouette of a flat panel in (u=long, v=short) 0..1 coords."""
    ext = list(mesh.extents)
    tax = ext.index(min(ext))                 # thickness axis
    a2 = [i for i in (0, 1, 2) if i != tax]
    la, sa = (a2 if ext[a2[0]] >= ext[a2[1]] else a2[::-1])
    V = mesh.vertices
    lmin, lspan = V[:, la].min(), (V[:, la].max() - V[:, la].min()) or 1.0
    smin, sspan = V[:, sa].min(), (V[:, sa].max() - V[:, sa].min()) or 1.0
    pts = [(round(float((x - lmin) / lspan), 4), round(float((y - smin) / sspan), 4))
           for x, y in zip(V[:, la], V[:, sa])]
    return _convex_hull(pts)

IN2CM = 2.54
SHEET_L = 244.0 / IN2CM   # 96.06"  (244 cm)
SHEET_W = 122.0 / IN2CM   # 48.03"  (122 cm)
KERF = 0.0                # ignore saw kerf for layout clarity
GAP = 0.0                 # adjacent pieces share a cut line (no gap between)

OUT = os.path.join(os.path.dirname(__file__), "..", "plans")


def frac(x):
    """Inch value -> nice fraction string (e.g. 53.75 -> '53 3/4')."""
    f = Fraction(x).limit_denominator(16)
    whole, rem = divmod(f, 1)
    if rem == 0:
        return f'{int(whole)}"'
    if whole == 0:
        return f'{rem.numerator}/{rem.denominator}"'
    return f'{int(whole)} {rem.numerator}/{rem.denominator}"'


def fmt(x, unit="in"):
    """Format an inch value in the requested unit."""
    return frac(x) if unit == "in" else f"{x * IN2CM:.1f} cm"


def base_name(name):
    """Group name: strip only a trailing numeric suffix (front_divider_2 -> front_divider)."""
    return re.sub(r"_\d+$", "", name)


def sheet_pieces(parts):
    """Plywood parts only (exclude steel legs + 2x2 frame). Returns list of
    dicts with the face dims (long, short), largest first."""
    out = []
    for name, mesh in parts.items():
        if name.startswith(("leg", "frame", "records")):
            continue
        dims = sorted(mesh.extents)          # ascending; dims[0] ~= 0.75 thick
        thick, short, long = dims[0], dims[1], dims[2]
        # a panel is a wedge if its actual face area is less than its bounding
        # rectangle (an angled/trapezoid cut), detected from the mesh volume
        face_area = mesh.volume / thick if thick > 1e-6 else short * long
        is_wedge = face_area < short * long * 0.97
        out.append({"name": name, "long": round(long, 3),
                    "short": round(short, 3), "wedge": bool(is_wedge),
                    "outline": _outline(mesh)})
    return out


def _pack_guillotine(pieces, sheet_l=SHEET_L, sheet_w=SHEET_W):
    """Group pieces into full-length strips that share a common width, so the
    sheet is cut by a few rips (one per strip) followed by crosscuts. Pieces
    may rotate to match a strip's width. Returns (placed, nsheets); each piece
    gets x, y, sheet, and placed dims pl (horizontal) / ph (vertical)."""
    strips = []
    for pc in sorted(pieces, key=lambda p: -max(p["long"], p["short"])):
        a, b = pc["long"], pc["short"]
        placed = False
        for s in strips:                       # join a strip of matching width
            for h, l in ((a, b), (b, a)):
                if abs(s["h"] - h) < 1e-6 and s["used"] + l + GAP <= sheet_l + 1e-6:
                    s["items"].append((pc, l, h)); s["used"] += l + GAP
                    placed = True
                    break
            if placed:
                break
        if not placed:                          # new strip; width = piece's short
            h, l = min(a, b), max(a, b)
            if l > sheet_l + 1e-6:              # too long even alone -> won't fit
                h, l = max(a, b), min(a, b)
            strips.append({"h": h, "used": l + GAP, "items": [(pc, l, h)]})

    strips.sort(key=lambda s: -s["h"])          # tidy: widest strips first
    sheets, y = 0, 0.0
    for s in strips:
        if sheets == 0 or y + s["h"] > sheet_w + 1e-6:
            sheets += 1; y = 0.0
        s["y"], s["sheet"] = y, sheets - 1
        y += s["h"] + GAP
    for s in strips:
        x = 0.0
        for pc, l, h in s["items"]:
            pc["x"], pc["y"], pc["sheet"] = x, s["y"], s["sheet"]
            pc["pl"], pc["ph"] = l, h
            x += l + GAP
    return pieces, sheets


def _pack_common(pieces, sheet_l=SHEET_L, sheet_w=SHEET_W, rng=None, strict=False):
    """Group pieces that share a dimension into the same full-length strip, most-
    shared dimension first, so many pieces come off one rip. With `rng` set, the
    strip dimension is chosen randomly (weighted by how many pieces share it) so
    a portfolio of runs explores different groupings. Returns (placed, nsheets);
    each piece gets x, y, sheet, pl (horiz), ph (vert)."""
    def key(v):
        return round(v, 2)

    def shares(p, d):
        return abs(p["long"] - d) < 0.06 or abs(p["short"] - d) < 0.06

    remaining = list(pieces)
    strips = []
    while remaining:
        cnt = Counter()
        for p in remaining:                      # tally valid rip widths
            for d in {key(p["long"]), key(p["short"])}:
                if d <= sheet_w + 1e-6:
                    cnt[d] += 1
        if not cnt:                               # nothing rippable; take smallest
            d = min(min(p["long"], p["short"]) for p in remaining)
        elif rng is None:                         # most shared; ties -> shorter strip
            d = max(cnt, key=lambda k: (cnt[k], -k))
        else:                                     # weighted-random dimension choice
            dims = list(cnt)
            d = rng.choices(dims, weights=[cnt[k] ** 2 for k in dims])[0]

        strip = {"h": d, "used": 0.0, "items": []}
        strips.append(strip)
        # Fill the strip: pieces that SHARE d first (grouped, share the rip),
        # then any remaining piece short enough to sit in this strip's tail.
        progress = True
        while progress:
            progress = False
            cand = sorted(remaining, key=lambda p: (
                0 if shares(p, d) else 1, -max(p["long"], p["short"])))
            for p in cand:
                if shares(p, d):
                    h = d
                    l = p["long"] if abs(p["short"] - d) < 0.06 else p["short"]
                elif strict:
                    continue                      # uniform strips: no shorter fillers
                else:
                    h, l = min(p["long"], p["short"]), max(p["long"], p["short"])
                    if h > d + 1e-6:
                        continue                  # too tall for this strip
                if strip["used"] + l + GAP <= sheet_l + 1e-6:
                    strip["items"].append((p, l, h))
                    strip["used"] += l + GAP
                    remaining.remove(p)
                    progress = True
                    break

        if not strip["items"]:                  # nothing fit -> force progress
            p = remaining.pop(0)
            hh, ll = min(p["long"], p["short"]), max(p["long"], p["short"])
            strip["h"], strip["used"] = hh, ll
            strip["items"].append((p, ll, hh))

    strips.sort(key=lambda s: -s["h"])
    sheets, y = 0, 0.0
    for s in strips:
        if sheets == 0 or y + s["h"] > sheet_w + 1e-6:
            sheets += 1; y = 0.0
        s["y"], s["sheet"] = y, sheets - 1
        y += s["h"] + GAP
    for s in strips:
        x = 0.0
        for p, l, h in s["items"]:
            p["x"], p["y"], p["sheet"] = x, s["y"], s["sheet"]
            p["pl"], p["ph"] = l, h
            x += l + GAP
    return pieces, sheets


def _merge_twins(pieces, sheet_l):
    """Merge identical pieces whose lengths tile a full sheet length into one
    super-strip, so e.g. two 122 cm panels share a single 244 cm row (one rip +
    one crosscut). Super pieces carry a 'twins' list; others pass through."""
    from collections import defaultdict
    groups = defaultdict(list)
    for p in pieces:
        groups[(round(p["long"], 1), round(p["short"], 1))].append(p)
    out = []
    for (lo, _sh), grp in groups.items():
        k = int(round(sheet_l / lo)) if lo > 0 else 1
        i = 0
        while k >= 2 and len(grp) - i >= k and abs(k * lo - sheet_l) < 1.5:
            chunk = grp[i:i + k]
            out.append({"name": "+".join(c["name"] for c in chunk),
                        "long": k * lo, "short": chunk[0]["short"],
                        "wedge": False, "twins": chunk})
            i += k
        out.extend(grp[i:])
    return out


def _expand_twins(placed):
    """Replace each placed super-strip with its individual twin pieces."""
    out = []
    for pc in placed:
        if "twins" not in pc:
            out.append(pc)
            continue
        rot = abs(pc["pl"] - pc["long"]) >= 0.05     # long dim runs vertically
        off = 0.0
        for t in pc["twins"]:
            tp = dict(t)
            tp["sheet"] = pc["sheet"]
            if rot:
                tp["x"], tp["y"] = pc["x"], pc["y"] + off
                tp["pl"], tp["ph"] = pc["pl"], t["long"]
            else:
                tp["x"], tp["y"] = pc["x"] + off, pc["y"]
                tp["pl"], tp["ph"] = t["long"], pc["ph"]
            off += t["long"]
            out.append(tp)
    return out


def _count_cuts(placed, sheet_l=SHEET_L, sheet_w=SHEET_W):
    """Guillotine cut count for a strip layout: for each sheet the sheet is
    sliced into strips (horizontal rips) then each strip into pieces + tail
    waste (vertical crosscuts). #cuts = #rectangles - 1 per sheet."""
    from collections import defaultdict
    sheets = defaultdict(lambda: defaultdict(list))
    for p in placed:
        sheets[p["sheet"]][round(p["y"], 1)].append(p)
    total = 0
    for strips in sheets.values():
        band, vcuts = 0.0, 0
        for items in strips.values():
            h = max(it["ph"] for it in items)
            band += h
            tail = sum(it["pl"] for it in items) < sheet_l - 0.5
            vcuts += (len(items) - 1) + (1 if tail else 0)
            # each piece shorter than its strip leaves waste above it (+1 cut)
            vcuts += sum(1 for it in items if it["ph"] < h - 0.3)
        top_waste = band < sheet_w - 0.5
        total += (len(strips) - 1) + (1 if top_waste else 0) + vcuts
    return total


def draw(parts, title, fname, unit="in", show_wedge=True, tries=400):
    base = sheet_pieces(parts)
    rng = random.Random(20240607)
    best = [None]        # (nsheets, cuts, placed)

    def consider(placed_raw, n, sl, sw, transpose):
        for pc in placed_raw:
            pc.setdefault("pl", pc["long"])
            pc.setdefault("ph", pc["short"])
        exp = _expand_twins(placed_raw)
        cuts = _count_cuts(exp, sl, sw)
        if transpose:                              # map strip space -> real board
            for pc in exp:
                pc["x"], pc["y"] = pc["y"], pc["x"]
                pc["pl"], pc["ph"] = pc["ph"], pc["pl"]
        if best[0] is None or (n, cuts) < (best[0][0], best[0][1]):
            best[0] = (n, cuts, exp)

    # Portfolio: both orientations x {grouping packer, shelf packer, and many
    # randomized grouping runs}. Keep fewest sheets, then fewest guillotine cuts.
    for sl, sw, tr in [(SHEET_L, SHEET_W, False)]:      # row orientation only
        merged = _merge_twins([dict(p) for p in base], sl)
        consider(*_pack_common([dict(p) for p in merged], sl, sw), sl, sw, tr)
        consider(*_pack_common([dict(p) for p in merged], sl, sw, strict=True),
                 sl, sw, tr)
        consider(*_pack_tagged([dict(p) for p in merged], sl, sw), sl, sw, tr)
        for _ in range(tries):
            strict = rng.random() < 0.5           # explore both fill modes
            consider(*_pack_common([dict(p) for p in merged], sl, sw, rng, strict),
                     sl, sw, tr)
    nsheets, ncuts, placed = best[0]

    # number pieces in reading order (per sheet: top -> bottom, left -> right)
    order = sorted(placed, key=lambda p: (p["sheet"], -round(p["y"], 1),
                                          round(p["x"], 1)))
    for i, pc in enumerate(order, 1):
        pc["idx"] = i

    # colour by SHELF group (name prefix "bin-"/"cab-"); one colour if unprefixed
    GROUP_COLORS = ["#9ecae1", "#fdae6b", "#a1d99b", "#c6a5d6", "#fb9a99"]
    has_groups = any("-" in pc["name"] for pc in placed)

    def group_of(nm):
        return nm.split("-", 1)[0] if (has_groups and "-" in nm) else "all"

    color_by = {}
    for pc in sorted(placed, key=lambda p: p["idx"]):
        g = group_of(pc["name"])
        if g not in color_by:
            color_by[g] = (GROUP_COLORS[len(color_by) % len(GROUP_COLORS)]
                           if has_groups else "#cfe2f3")
    thick = 0.75
    sheet_lbl = ("4' × 8' × ¾\" plywood" if unit == "in"
                 else f"{SHEET_W*IN2CM:.0f} × {SHEET_L*IN2CM:.0f} × "
                      f"{thick*IN2CM:.1f} cm plywood")

    # legend geometry: 3 columns beneath the sheet(s)
    leg_cols = 3
    leg_rows = -(-len(order) // leg_cols)
    leg_h = 0.5 + 0.20 * leg_rows
    fig = plt.figure(figsize=(max(7.6 * nsheets, 9), 4.4 + leg_h))
    gs = fig.add_gridspec(2, 1, height_ratios=[4.4, leg_h], hspace=0.05)
    top = gs[0].subgridspec(1, nsheets, wspace=0.08)
    fig.suptitle(title, fontsize=12.5, weight="bold")
    cut_note = f"{len(order)} pieces  ·  ~{ncuts} guillotine cuts"

    ax_step = 24 if SHEET_L > 40 else 12
    for si in range(nsheets):
        ax = fig.add_subplot(top[si])
        ax.add_patch(Rectangle((0, 0), SHEET_L, SHEET_W, fill=False,
                               ec="#333", lw=2))
        extra = f"  ·  {cut_note}" if si == 0 else ""
        ax.set_title(f"Sheet {si + 1}  ·  {sheet_lbl}{extra}", fontsize=9.5)
        for pc in placed:
            if pc["sheet"] != si:
                continue
            x, y, L, Sh = pc["x"], pc["y"], pc["pl"], pc["ph"]
            col = color_by[group_of(pc["name"])]
            rotated = abs(pc["pl"] - pc["long"]) > 0.05   # long dim is vertical
            if pc["wedge"] and show_wedge:
                # show the real silhouette; the blank rectangle + offcut are dashed
                ax.add_patch(Rectangle((x, y), L, Sh, facecolor="none",
                                       ec="#c0392b", ls=(0, (4, 3)), lw=0.8))
                pts = [((x + v * L, y + u * Sh) if rotated
                        else (x + u * L, y + v * Sh)) for u, v in pc["outline"]]
                ax.add_patch(MplPolygon(pts, closed=True, facecolor=col,
                                        ec="#555", lw=0.9))
            else:
                ax.add_patch(Rectangle((x, y), L, Sh, facecolor=col,
                                       ec="#555", lw=0.8))
            fs = max(5.5, min(11, min(L, Sh) * 1.7))   # number scaled to piece
            ax.text(x + L / 2, y + Sh / 2, str(pc["idx"]),
                    ha="center", va="center", fontsize=fs, weight="bold",
                    color="#222")
        ax.set_xlim(-2, SHEET_L + 2)
        ax.set_ylim(-2, SHEET_W + 2)
        ax.set_aspect("equal")
        xt = list(range(0, int(SHEET_L) + 1, ax_step))
        yt = list(range(0, int(SHEET_W) + 1, ax_step))
        ax.set_xticks(xt); ax.set_yticks(yt)
        if unit == "cm":
            ax.set_xticklabels([f"{t * IN2CM:.0f}" for t in xt])
            ax.set_yticklabels([f"{t * IN2CM:.0f}" for t in yt])
        ax.set_xlabel("centimeters" if unit == "cm" else "inches", fontsize=8)
        ax.tick_params(labelsize=7)

    # legend
    legax = fig.add_subplot(gs[1])
    legax.axis("off")
    if has_groups:                              # shelf colour key
        keys = [g for g in color_by if g != "all"]
        for j, g in enumerate(keys):
            legax.add_patch(Rectangle((j * 0.18, 1.06), 0.02, 0.06,
                            facecolor=color_by[g], ec="#555",
                            transform=legax.transAxes, clip_on=False))
            legax.text(j * 0.18 + 0.028, 1.09, f"{g}-*", va="center",
                       fontsize=8, weight="bold", transform=legax.transAxes)
    for i, pc in enumerate(order):
        col, row = i % leg_cols, i // leg_cols
        name = pc["name"].replace("_", " ")
        txt = (f"{pc['idx']:>2}.  {name}  —  "
               f"{fmt(pc['long'], unit)} × {fmt(pc['short'], unit)}")
        legax.text(col / leg_cols, 1 - (row + 0.5) / leg_rows, txt,
                   ha="left", va="center", fontsize=6.8, family="monospace",
                   transform=legax.transAxes)

    os.makedirs(OUT, exist_ok=True)
    fig.subplots_adjust(left=0.05, right=0.98, top=0.9, bottom=0.04)
    path = os.path.join(OUT, fname)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("wrote", path, f"({nsheets} sheet(s))")
    return placed


def _pack_tagged(pieces, sheet_l=SHEET_L, sheet_w=SHEET_W):
    """Same shelf packer but records which sheet each piece lands on."""
    order = sorted(pieces, key=lambda p: p["short"], reverse=True)
    sheets = []
    for pc in order:
        w, h = pc["long"] + GAP, pc["short"] + GAP
        placed = False
        for si, sh in enumerate(sheets):
            for shelf in sh["shelves"]:
                if h <= shelf["h"] + 1e-6 and shelf["x"] + w <= sheet_l + 1e-6:
                    pc["x"], pc["y"], pc["sheet"] = shelf["x"], shelf["y"], si
                    shelf["x"] += w
                    placed = True
                    break
            if placed:
                break
            if sh["used_w"] + h <= sheet_w + 1e-6:
                shelf = {"y": sh["used_w"], "h": h, "x": 0.0}
                sh["shelves"].append(shelf)
                sh["used_w"] += h
                pc["x"], pc["y"], pc["sheet"] = 0.0, shelf["y"], si
                shelf["x"] += w
                placed = True
                break
        if not placed:
            sh = {"shelves": [], "used_w": 0.0}
            sheets.append(sh)
            shelf = {"y": 0.0, "h": h, "x": 0.0}
            sh["shelves"].append(shelf)
            sh["used_w"] += h
            pc["x"], pc["y"], pc["sheet"] = 0.0, 0.0, len(sheets) - 1
            shelf["x"] += w
    return order, len(sheets)


def cut_list_text(parts, title, unit="in"):
    """Grouped cut list as plain text, in inches and centimeters."""
    groups = {}
    for p in sheet_pieces(parts):
        key = (base_name(p["name"]), p["long"], p["short"])
        groups[key] = groups.get(key, 0) + 1
    lines = [title, "=" * len(title), "",
             "CUT LIST (3/4\" / 19 mm plywood):",
             f"  {'qty':>3}  {'part':22s} {'inches':16s} centimeters"]
    for (name, L, S), qty in sorted(groups.items(), key=lambda k: -k[0][1]):
        inch = f"{frac(L)} x {frac(S)}"
        cm = f"{L*IN2CM:.1f} x {S*IN2CM:.1f} cm"
        lines.append(f"  ({qty}) {name.replace('_',' '):22s} {inch:16s} {cm}")
    return "\n".join(lines)


if __name__ == "__main__":
    std = rs.build_parts(rs.ROW_DEPTH_STD)
    compact = rs.build_parts(rs.ROW_DEPTH_COMPACT)

    # all cm figures are computed from the inch values, never hard-coded
    for parts, name, row in [(std, "Standard", rs.ROW_DEPTH_STD),
                             (compact, "Compact", rs.ROW_DEPTH_COMPACT)]:
        depth_in = rs.overall_depth(row)
        depth_cm = depth_in * IN2CM
        base = f"8-Cubby Vinyl Record Storage — Cut Diagram ({name}, "
        draw(parts, base + f"{fmt(depth_in,'in')} / {depth_cm:.1f} cm deep)",
             f"cut_diagram_{name.lower()}.png", unit="in")
        draw(parts, base + f"{depth_cm:.1f} cm deep)",
             f"cut_diagram_{name.lower()}_cm.png", unit="cm")

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "cut_list.txt"), "w", encoding="utf-8") as f:
        for parts, name, row in [(std, "STANDARD", rs.ROW_DEPTH_STD),
                                 (compact, "COMPACT", rs.ROW_DEPTH_COMPACT)]:
            note = ("original plan" if name == "STANDARD" else "protrudes less")
            title = (f"{name}  (each row {fmt(row,'in')} / {row*IN2CM:.1f} cm "
                     f"deep — {note})")
            f.write(cut_list_text(parts, title))
            f.write("\n\n\n")
    print("wrote", os.path.join(OUT, "cut_list.txt"))

    # 2x 12" + 3x 7" variant
    v = rs.build_parts(rs.ROW_DEPTH_STD, layout=["lp", "7", "7", "7", "lp"])
    draw(v, '2×12" + 3×7" Vinyl Record Storage — Cut Diagram (55¾" wide)',
         "cut_diagram_2lp_3x7.png", unit="in")
    draw(v, "2×12\" + 3×7\" Vinyl Record Storage — Cut Diagram (141.6 cm wide)",
         "cut_diagram_2lp_3x7_cm.png", unit="cm")
    with open(os.path.join(OUT, "cut_list_2lp_3x7.txt"), "w", encoding="utf-8") as f:
        f.write(cut_list_text(v, "2x 12\" + 3x 7\"  (55 3/4\" / 141.6 cm wide)"))
    print("wrote", os.path.join(OUT, "cut_diagram_2lp_3x7.png"))

    # 2x 12" + 4x 7" variant (65" / 165.1 cm wide)
    v4 = rs.build_parts(rs.ROW_DEPTH_STD, layout=["lp", "7", "7", "7", "7", "lp"])
    draw(v4, '2×12" + 4×7" Vinyl Record Storage — Cut Diagram (65" wide)',
         "cut_diagram_2lp_4x7.png", unit="in")
    draw(v4, "2×12\" + 4×7\" Vinyl Record Storage — Cut Diagram (165.1 cm wide)",
         "cut_diagram_2lp_4x7_cm.png", unit="cm")
    with open(os.path.join(OUT, "cut_list_2lp_4x7.txt"), "w", encoding="utf-8") as f:
        f.write(cut_list_text(v4, "2x 12\" + 4x 7\"  (65\" / 165.1 cm wide)"))
    print("wrote", os.path.join(OUT, "cut_diagram_2lp_4x7.png"))
