"""
Generate a self-contained, printable build-plan page (plan.html) for the
one-board project: two shelves (deep 45 board-bin + 2-level 2x12" cabinet)
from a single 122 x 244 cm sheet plus a 51.5 x 122 cm offcut.

Images are embedded as base64 so the page is fully self-contained (host it
anywhere, or Print / Save-as-PDF). Run after combined_board.py / renders.
"""
import base64
import os

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")


def data_uri(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{b64}"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def img(rel):
    p = os.path.join(ROOT, rel)
    return data_uri(p) if os.path.exists(p) else ""


CUT_LIST = read(os.path.join(ROOT, "plans", "cut_list_combined.txt")) \
    if os.path.exists(os.path.join(ROOT, "plans", "cut_list_combined.txt")) else ""

HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vinyl Record Storage — One-Board Build Plan</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    color: #1c2128; background: #eceff3; line-height: 1.5; }}
  .page {{ max-width: 920px; margin: 0 auto; background: #fff; padding: 40px 48px;
    box-shadow: 0 2px 20px rgba(0,0,0,.08); }}
  h1 {{ font-size: 26px; margin: 0 0 4px; }}
  .sub {{ color: #5a6472; margin-bottom: 24px; }}
  h2 {{ font-size: 17px; border-bottom: 2px solid #e2e6ec; padding-bottom: 5px;
    margin: 30px 0 12px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  .card {{ border: 1px solid #e2e6ec; border-radius: 10px; padding: 14px; }}
  .card h3 {{ margin: 0 0 6px; font-size: 15px; }}
  .card img {{ width: 100%; border-radius: 6px; background: #f4f6f9; }}
  .card .dim {{ color: #5a6472; font-size: 13px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  td, th {{ border: 1px solid #e2e6ec; padding: 5px 9px; text-align: left; }}
  th {{ background: #f4f6f9; }}
  pre {{ background: #f4f6f9; border: 1px solid #e2e6ec; border-radius: 8px;
    padding: 12px; font-size: 11.5px; overflow-x: auto; white-space: pre; }}
  .cutimg {{ width: 100%; border: 1px solid #e2e6ec; border-radius: 8px; }}
  ul {{ padding-left: 20px; }}
  .btn {{ position: fixed; top: 16px; right: 16px; background: #d9a066; color: #201a12;
    border: 0; border-radius: 8px; padding: 10px 16px; font-size: 14px; font-weight: 600;
    cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,.2); }}
  .note {{ color: #5a6472; font-size: 13px; }}
  @media print {{
    body {{ background: #fff; }} .page {{ box-shadow: none; max-width: none; padding: 0; }}
    .btn {{ display: none; }} h2 {{ break-after: avoid; }} .card, tr, pre {{ break-inside: avoid; }}
  }}
</style></head>
<body>
<button class="btn" onclick="window.print()">🖨 Print / Save PDF</button>
<div class="page">
  <h1>Vinyl Record Storage — One-Board Build Plan</h1>
  <div class="sub">Two shelves from a single 122 × 244 cm sheet of 22 mm plywood,
     plus a 51.5 × 122 cm offcut. On 28″ steel hairpin legs.</div>

  <h2>The two shelves</h2>
  <div class="grid">
    <div class="card">
      <h3>Shelf 1 — Deep 45 board-bin</h3>
      <img src="{img('renders/hero_board_bin.png')}" alt="board bin">
      <div class="dim">≈ 126 × 51.5 × 15 cm · 5 compartments for 7″ singles.<br>
        <b>Bottom = your existing 51.5 × 122 cm offcut.</b></div>
    </div>
    <div class="card">
      <h3>Shelf 2 — 2-level LP cabinet</h3>
      <img src="{img('renders/hero_shelf2.png')}" alt="cabinet">
      <div class="dim">72 × 36 × 47 cm · 4 cubbies (2 columns × 2 tiers) for 12″ LPs.</div>
    </div>
  </div>

  <h2>Materials &amp; hardware</h2>
  <ul>
    <li><b>1 ×</b> new 122 × 244 cm sheet of 22 mm plywood (all pieces below)</li>
    <li><b>1 ×</b> existing 51.5 × 122 cm offcut → board-bin bottom</li>
    <li><b>8 ×</b> 28″ steel hairpin legs (4 per shelf) + mounting screws</li>
    <li>Wood glue · 30 mm screws / brad nails · wood filler · finish</li>
  </ul>

  <h2>Cut diagram — one sheet, ~24 guillotine cuts</h2>
  <div class="note">Blue = board-bin pieces · orange = cabinet pieces. The
    board-bin bottom is your offcut and is not on this sheet.</div>
  <img class="cutimg" src="{img('plans/cut_diagram_combined_cm.png')}" alt="cut diagram">

  <h2>Cut list</h2>
  <pre>{CUT_LIST}</pre>

  <h2>Assembly (both shelves)</h2>
  <ol>
    <li>Cut all pieces per the diagram; cut the wedge slope on the cabinet sides.</li>
    <li><b>Board-bin:</b> glue/screw the 5 dividers between front &amp; back onto the
       offcut bottom, add the two sides, then the hairpin legs.</li>
    <li><b>Cabinet:</b> attach bottom to back (raised for the 2×2 style base if used),
       add the shelf divider + back-shelf, the LP dividers, then the wedge sides and front.</li>
    <li>Fill, sand, finish; screw on the hairpin legs.</li>
  </ol>
  <div class="note">Interactive 3D models &amp; all variants: see the model gallery
     (index.html).</div>
</div>
</body></html>
"""


def main():
    out = os.path.join(ROOT, "plan.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(HTML)
    print("wrote", out, f"({os.path.getsize(out)//1024} KB)")


if __name__ == "__main__":
    main()
