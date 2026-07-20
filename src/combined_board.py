"""
Nest the board-bin's remaining pieces (everything except its bottom, which is
your existing 51.5 x 122 cm offcut) TOGETHER with a whole second shelf, onto a
single full 122 x 244 cm sheet — so you buy just one complete board.

Companion = the slanted "easy" 4-compartment 7" bin.
"""
import os
from collections import OrderedDict

import board_bin
import simple_shelf as ss
import cutsheet


def plywood_only(parts, prefix):
    """Keep only plywood parts (drop steel legs / frame / records), prefixed."""
    return OrderedDict((prefix + k, v) for k, v in parts.items()
                       if not k.startswith(("leg", "frame", "records")))


def main():
    here = os.path.dirname(__file__)

    # Board bin: everything except the bottom (bottom = the existing offcut)
    board = OrderedDict((k, v) for k, v in board_bin.build().items() if k != "bottom")

    # Companion: the slanted easy bin (complete)
    companion = ss.build_parts(front_h=ss.FRONT_H, back_h=ss.BACK_H,
                               depth=ss.DEPTH, bays=ss.BAYS)

    merged = OrderedDict()
    merged.update(plywood_only(board, "bin-"))
    merged.update(plywood_only(companion, "shelf-"))

    title = ("One Board = Deep Board-Bin (minus its offcut bottom) + Slanted 4x Bin  "
             "— cut from a single 4x8 sheet")
    cutsheet.draw(merged, title, "cut_diagram_combined.png", unit="in", show_wedge=False)
    cutsheet.draw(merged, title + "  (cm)", "cut_diagram_combined_cm.png",
                  unit="cm", show_wedge=False)
    with open(os.path.join(here, "..", "plans", "cut_list_combined.txt"),
              "w", encoding="utf-8") as f:
        f.write(cutsheet.cut_list_text(
            merged, "COMBINED — board-bin pieces (no bottom) + slanted 4x bin"))
    print("wrote combined cut map")
    print("NOTE: the slanted bin's two sides (shelf-side_*) are rectangular blanks; "
          "cut their wedge (7\" front / 8\" back) afterwards.")


if __name__ == "__main__":
    main()
