"""
TWO shelves from your existing offcut + ONE new full 122 x 244 cm board.

  Board 1 (have): 51.5 x 122 cm offcut  -> bottom of shelf #1 (the board-bin)
  Board 2 (buy):  122 x 244 cm sheet    -> everything else for BOTH shelves

  Shelf #1: deep flat board-bin (bottom = the offcut, so it's not on the sheet)
  Shelf #2: the TWO-LEVEL stepped cabinet, 2x 12" columns (4 LP cubbies),
            shallow ~26 cm depth so it protrudes little AND its pieces are
            small enough that the whole plan nests as grouped rip-strips on one
            board (fewest cuts).
"""
import os
from collections import OrderedDict

import board_bin
import record_storage as rs
import cutsheet

CAB_ROW_DEPTH = 8.0   # 8" rows -> ~46 cm deep (deepest that still fits 1 board)


def plywood_only(parts, prefix):
    return OrderedDict((prefix + k, v) for k, v in parts.items()
                       if not k.startswith(("leg", "frame", "records")))


def main():
    here = os.path.dirname(__file__)

    shelf1 = OrderedDict((k, v) for k, v in board_bin.build().items()
                         if k != "bottom")                      # bottom = offcut
    shelf2 = rs.build_parts(CAB_ROW_DEPTH, layout=["lp", "lp"])

    merged = OrderedDict()
    merged.update(plywood_only(shelf1, "bin-"))
    merged.update(plywood_only(shelf2, "cab-"))

    title = ("Two shelves, one new 122x244 board — deep board-bin (bottom = your "
             "51.5x122 offcut) + 2-level 2x12\" cabinet (~46 cm deep)")
    placed = cutsheet.draw(merged, title, "cut_diagram_combined.png", unit="in")
    nsheets = max(p["sheet"] for p in placed) + 1
    cutsheet.draw(merged, title + "  (cm)", "cut_diagram_combined_cm.png",
                  unit="cm")
    with open(os.path.join(here, "..", "plans", "cut_list_combined.txt"),
              "w", encoding="utf-8") as f:
        f.write(cutsheet.cut_list_text(
            merged, "board-bin (no bottom) + compact 2-level 2x12 cabinet"))
    print(f"==> fits on {nsheets} new sheet(s)")
    print("NOTE: cab- sides are wedge blanks; cut the slope (7\" front -> 18.5\" "
          "back) after cutting the rectangle.")


if __name__ == "__main__":
    main()
