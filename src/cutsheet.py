"""
Generate a plywood CUT DIAGRAM (sheet nesting layout) for the record storage,
similar to page 2 of the official plan: rectangles laid out on 4x8 sheets of
3/4" plywood, each labelled with its part name and size.

Uses a simple first-fit-decreasing shelf packer. Not guaranteed optimal, but
produces a valid, readable layout. The wedge cut line is drawn on the sides.
"""
import os
import re
from fractions import Fraction

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

import record_storage as rs

SHEET_L = 96.0   # 8 ft
SHEET_W = 48.0   # 4 ft
KERF = 0.0       # ignore saw kerf for layout clarity
GAP = 0.25       # small visual gap between parts
IN2CM = 2.54

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
        out.append({"name": name, "long": round(dims[2], 3),
                    "short": round(dims[1], 3),
                    "wedge": name.startswith("side")})
    return out


def draw(parts, title, fname, unit="in", show_wedge=True):
    pieces = sheet_pieces(parts)
    placed, nsheets = _pack_tagged([dict(p) for p in pieces])

    fig, axes = plt.subplots(1, nsheets, figsize=(7.2 * nsheets, 4.2))
    if nsheets == 1:
        axes = [axes]
    fig.suptitle(title, fontsize=13, weight="bold")

    cmap = plt.get_cmap("Pastel1")
    color_by = {}
    thick = 0.75
    sheet_lbl = ("4' × 8' × ¾\" plywood" if unit == "in"
                 else f"{SHEET_W*IN2CM:.0f} × {SHEET_L*IN2CM:.0f} × "
                      f"{thick*IN2CM:.1f} cm plywood")

    for si, ax in enumerate(axes):
        ax.add_patch(Rectangle((0, 0), SHEET_L, SHEET_W, fill=False,
                               ec="#333", lw=2))
        ax.set_title(f"Sheet {si + 1}  ·  {sheet_lbl}", fontsize=10)
        for pc in placed:
            if pc["sheet"] != si:
                continue
            base = base_name(pc["name"])
            color_by.setdefault(base, cmap(len(color_by) % 9))
            x, y, L, Sh = pc["x"], pc["y"], pc["long"], pc["short"]
            ax.add_patch(Rectangle((x, y), L, Sh, facecolor=color_by[base],
                                   ec="#555", lw=0.8))
            if pc["wedge"] and show_wedge:  # wedge cut line on the side blanks
                ax.add_line(Line2D([x, x + L], [y, y + Sh],
                                   color="#c0392b", lw=1.1, ls="--"))
            label = pc["name"].replace("_", " ")
            ax.text(x + L / 2, y + Sh / 2,
                    f"{label}\n{fmt(pc['long'], unit)} × {fmt(pc['short'], unit)}",
                    ha="center", va="center", fontsize=7.2)
        ax.set_xlim(-2, SHEET_L + 2)
        ax.set_ylim(-2, SHEET_W + 2)
        ax.set_aspect("equal")
        ticks = [0, 24, 48, 72, 96]
        ax.set_xticks(ticks)
        ax.set_yticks([0, 24, 48])
        if unit == "cm":
            ax.set_xticklabels([f"{t * IN2CM:.0f}" for t in ticks])
            ax.set_yticklabels([f"{t * IN2CM:.0f}" for t in [0, 24, 48]])
        ax.set_xlabel("centimeters" if unit == "cm" else "inches")

    os.makedirs(OUT, exist_ok=True)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    path = os.path.join(OUT, fname)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("wrote", path, f"({nsheets} sheet(s))")
    return placed


def _pack_tagged(pieces):
    """Same shelf packer but records which sheet each piece lands on."""
    order = sorted(pieces, key=lambda p: p["short"], reverse=True)
    sheets = []
    for pc in order:
        w, h = pc["long"] + GAP, pc["short"] + GAP
        placed = False
        for si, sh in enumerate(sheets):
            for shelf in sh["shelves"]:
                if h <= shelf["h"] + 1e-6 and shelf["x"] + w <= SHEET_L + 1e-6:
                    pc["x"], pc["y"], pc["sheet"] = shelf["x"], shelf["y"], si
                    shelf["x"] += w
                    placed = True
                    break
            if placed:
                break
            if sh["used_w"] + h <= SHEET_W + 1e-6:
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
