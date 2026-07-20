"""
TWO shelves from your existing offcut + ONE new full 122 x 244 cm board.

  Board 1 (have): 51.5 x 122 cm offcut  -> bottom of shelf #1 (the board-bin)
  Board 2 (buy):  122 x 244 cm sheet    -> everything else for BOTH shelves

  Shelf #1: deep flat board-bin (bottom = the offcut, so it's not on the sheet)
  Shelf #2: the TWO-LEVEL stepped cabinet, compact depth, 2x 12" columns
            (2 LP cubbies per tier = 4 cubbies), so it protrudes less.
"""
import os
from collections import OrderedDict

import board_bin
import record_storage as rs
import cutsheet


def plywood_only(parts, prefix):
    return OrderedDict((prefix + k, v) for k, v in parts.items()
                       if not k.startswith(("leg", "frame", "records")))


def main():
    here = os.path.dirname(__file__)

    shelf1 = OrderedDict((k, v) for k, v in board_bin.build().items()
                         if k != "bottom")                      # bottom = offcut
    shelf2 = rs.build_parts(rs.ROW_DEPTH_COMPACT, layout=["lp", "lp"])

    merged = OrderedDict()
    merged.update(plywood_only(shelf1, "bin-"))
    merged.update(plywood_only(shelf2, "cab-"))

    title = ("Two shelves, one new 4x8 sheet — deep board-bin (bottom = your "
             "51.5x122 offcut) + compact 2-level 2x12\" cabinet")
    placed = cutsheet.draw(merged, title, "cut_diagram_combined.png",
                           unit="in", show_wedge=False)
    nsheets = max(p["sheet"] for p in placed) + 1
    cutsheet.draw(merged, title + "  (cm)", "cut_diagram_combined_cm.png",
                  unit="cm", show_wedge=False)
    with open(os.path.join(here, "..", "plans", "cut_list_combined.txt"),
              "w", encoding="utf-8") as f:
        f.write(cutsheet.cut_list_text(
            merged, "board-bin (no bottom) + compact 2-level 2x12 cabinet"))
    print(f"==> fits on {nsheets} new sheet(s)")
    print("NOTE: cab- sides are wedge blanks; cut the slope (7\" front -> 18.5\" "
          "back) after cutting the rectangle.")


if __name__ == "__main__":
    main()
