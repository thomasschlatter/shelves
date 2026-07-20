"""
A 45 (7") bin whose BOTTOM is an existing 51.5 x 122 cm plywood offcut.

The board fixes the footprint: 122 cm across (bin inner width) x 51.5 cm deep.
Everything else (2 sides, back, front, dividers) is cut from a fresh sheet;
the cut map below shows only those pieces — the bottom is the board you have.
"""
import os
from collections import OrderedDict

import simple_shelf as ss
import cutsheet
import build_viewer as bv
import render
import record_storage as rs

IN = 2.54
BOARD = (51.5, 122.0)          # cm (depth, width) — the existing bottom board
INNER_W = 122.0 / IN           # 48.03"  bin inner width  (board long side)
DEPTH = 51.5 / IN              # 20.28"  bin depth        (board short side)
BAYS = 5
HEIGHT = 6.0                   # flat, front == back
REC_N = 40
BAY_W = (INNER_W - (BAYS - 1) * ss.T) / BAYS
SLUG = "board_bin"


def build(with_records=False):
    return ss.build_parts(with_records=with_records, front_h=HEIGHT, back_h=HEIGHT,
                          depth=DEPTH, rec_n=REC_N, bays=BAYS, bay_w=BAY_W)


def main():
    here = os.path.dirname(__file__)
    parts = build()
    W = ss.overall_width(BAYS, BAY_W)
    print(f"[board bin] {len(parts)} parts  "
          f"overall {W*IN:.1f} × {DEPTH*IN:.1f} × {HEIGHT*IN:.1f} cm, "
          f"{BAYS} compartments (bay {BAY_W*IN:.1f} cm), "
          f"bottom = {INNER_W*IN:.1f} × {DEPTH*IN:.1f} cm")

    rs.export(parts, os.path.join(here, "..", "models", SLUG))
    bv.write_viewer(build(with_records=True),
                    f"Board bin (bottom = 51.5×122 cm offcut) · "
                    f"{W*IN:.0f} × {DEPTH*IN:.0f} × {HEIGHT*IN:.0f} cm",
                    f"viewer_{SLUG}.html")
    render.hero(build(with_records=True), 24, -58, f"hero_{SLUG}.png")

    # cut map for the pieces still to cut — the bottom is the existing board
    to_cut = OrderedDict((k, v) for k, v in parts.items() if k != "bottom")
    cutsheet.draw(to_cut, "Board Bin — Cut These (bottom = your 51.5×122 board)",
                  f"cut_diagram_{SLUG}.png", unit="in", show_wedge=False)
    cutsheet.draw(to_cut, "Board Bin — Cut These (cm) · bottom = your 51.5×122 board",
                  f"cut_diagram_{SLUG}_cm.png", unit="cm", show_wedge=False)
    with open(os.path.join(here, "..", "plans", f"cut_list_{SLUG}.txt"),
              "w", encoding="utf-8") as f:
        f.write(cutsheet.cut_list_text(
            to_cut, "BOARD BIN — pieces to cut (bottom = existing 51.5 x 122 cm board)"))
    print("wrote viewer + cut map (excludes the bottom board)")


if __name__ == "__main__":
    main()
