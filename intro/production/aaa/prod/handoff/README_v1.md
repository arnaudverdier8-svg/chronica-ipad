# KEYFRAME f1983 (S26): the hand-off frame

This is the live CHRONICA main menu's first frame in its no-save state (5 buttons), captured natively from the real web build, with the card's contents removed. What remains is the blank parchment card in its walnut frame. Every pixel outside the card's parchment field is the live game, bit for bit.

## Deliverables

| file | what |
|---|---|
| `f1983_16x9_2560x1440.png` | **the keyframe** (16:9 master bucket B169) |
| `f1983_4x3_2048x1536.png` | 4:3 bucket B133 (iPad), with the table edge (books, scroll, chamberstick) that `_layout()` shows on 4:3 |
| `verify_diff_<bucket>.png` | the absolute difference between f1983 and the live capture, amplified x8, with the card rect outlined. Outside the card it is 0: max 0/255, 0 px changed, in both buckets |
| `report_<bucket>.json` | numbers: the fitted card size, the draw rect of every element, the parchment-field rect, matte-vs-capture errors and seam residuals |
| `review_sheet_f1983.png/.jpg` | client sheet with live, f1983 and the x8 difference for both buckets, plus 100 % crops of the card seams |
| `mattes_<bucket>/` | the desk/chrome mattes, described below |
| `capture/c169_a`, `capture/c133_a` (and `c169_b`, a second independent boot used for the reproducibility check) | the native live captures (`menu_<W>x<H>_mfNNN_r{0,1}.png`, where NNN is the menu frame; r0 and r1 are two screenshots of the same frozen frame and are bit-identical), plus `capture.log` |
| `qa/` | evidence images: the nameplate pop-in (frame 3 vs 30), the frame 30 vs 120 difference, the card-rebuild residual x16, the parchment-field rect, the candle flame/unlit split, the chrome over a dark checker |
| `src/` | every script needed to rebuild everything (see "Re-render") |

## How it was made

1. **Native capture with a deterministic clock** (`src/capture_menu.mjs`). Playwright Chromium (SwiftShader WebGL2) loads the game in a fresh profile. A fresh profile has no IDBFS save, so the menu shows the 5-button card. The viewport is set natively to the bucket size at DPR 1, so the Godot canvas is 2560x1440 (or 2048x1536) and nothing is upscaled.
   - An init script virtualises `performance.now()`. Time is frozen inside each browser frame and advances exactly 1/60 s per rAF tick. Godot therefore sees a steady 60 fps however slowly SwiftShader renders. As a side effect, FramePace keeps `scaling_3d_scale = 1.0`, as on a fast device, and the menu camera tour (3 s hold, then a 14 s pan) cannot start early.
   - Once the HTML loader starts fading (callMain is done and the menu is built), the script lets N Godot frames run and then holds every rAF callback. The canvas keeps the last presented frame, so it can be screenshotted at leisure.
2. **Which frame.** Menu frames 1 to about 20 are not settled: the city nameplates pop in larger. Compare `capture/c169_a/menu_2560x1440_mf003_r0.png` with `mf030`. From frame 30 on, only unit idle animations and water change (frames 30 and 120: chrome bit-identical, mean difference 0.79/255, all of it on units and water). The keyframe therefore uses **menu frame 30**: 0.5 s of game time after callMain, nameplates settled, camera still on its first focus (Grandbois), and well inside the tour's 3 s hold. That is the state the live game shows during the hand-off dissolve. The frame-3 capture is kept for reference.
3. **Godot's 2D placement, reproduced** (`src/menu_layout.py`, `src/godot2d.py`). The script ports `main_menu.gd _layout()` and adds two engine details measured on the capture:
   - Control **positions** are rounded to whole base units; sizes are not.
   - TextureRect `KEEP_ASPECT_CENTERED` truncates the fitted size to an int, then centres it.

   Textures are sampled with Godot's box-filter mip chain and trilinear filtering. The StyleBox nine-patches are rebuilt with canvas.glsl `map_ninepatch_axis` and the bar's `WOOD_DARK` modulate. With this model every chrome element matches the capture to **0.26-0.69/255** mean absolute error on its opaque pixels.
4. **Blank card** (`src/handoff.py`). The card's minimum size is fitted against the captured walnut frame. The fit gives **629 x 665 base units at both scales**, not the 627 x 661 in `game/menu_layout.json`. The card is then redrawn from `assets/tex/table_parchment/menu_card.png` (margins 46/47/48/56, stretch, bilinear). Only the parchment field is replaced: inside the inner dark line, 3 texels in, feathered over 2 texels, with the brass corners excluded. On content-free parchment the rebuild differs from the live card by **0.48/255** mean absolute error (0.42 on 4:3), and the feather band by 0.01/255. No seam is visible at 100 % (see the review sheet).
5. **Mattes** (`src/chrome.py`, `src/flames.py`). Each element is drawn from its own texture into its exact Godot rect as a full-frame straight-alpha RGBA layer.

## Reproducibility

`capture/c169_b` is a second, independent boot captured with the same script. Compared with `c169_a` at menu frame 30, it is bit-identical except for **334 px** (0.009 % of the frame; max 25/255; mean 0.0006/255). Those pixels sit in 5 tiny clusters of a faint randomly seeded dust puff over unit shields (`qa/repro_runA_vs_runB_clusters.png`). The chrome and the card are identical. Everything after the capture (`handoff.py` and the rest) is deterministic.

## G12 outlook (16:9, outside the card rect, with no masks applied)

| f1983 vs | mean abs | px > 16/255 |
|---|---|---|
| live menu frame 30 (its base) | 0.000/255 | 0 % |
| live menu frame 3 (nameplates still popping in) | 1.59/255 | 2.1 % |
| live menu frame 120 (2 s, unit idle animations and water moved) | 1.11/255 | 1.8 % |

Even without the unit and water masks, all three live frames measured in the 3 s hold (3, 30 and 120) are under the G12 threshold of 2/255. The final G12 check still has to be run on device (iPad Safari, the shipped encode).

## Mattes (`mattes_16x9_2560x1440/`, `mattes_4x3_2048x1536/`)

All layers are full frame and aligned to the live menu. They are straight (non-premultiplied) sRGB RGBA. Composite them with plain `over` in `draw_order` (Godot Compatibility blends 2D in sRGB space). `rects.json` gives the draw rects in base units and in px, the draw order, the card's minimum size and the parchment-field rect.

- `bar_top` (walnut beam, WOOD_DARK modulate), `logo_title` (the 'Chronica' valance), `banner_side_left/right`, `candle_left/right`, `lion_statue_left/right`, `table_edge_bottom` (4:3 only), and `menu_card` (the blank card).
- `candle_*_flame` and `candle_*_unlit` (on 4:3 also `table_edge_bottom_flame/_unlit`): the flame alone, and the candle with only its wick, for the unlit-desk and relit states (f1612-f1707). Each flame layer over its unlit layer reproduces the candle.
- `desk_all_but_card` and `chrome_all` (the whole desk in draw order); `board_visible_alpha` (1 where the 3D board shows); `card_parchment_replaced_alpha` (exactly the pixels f1983 changed).

## Numbers that matter to other shots (16:9 / 4:3, px)

| element | 16:9 2560x1440 | 4:3 2048x1536 |
|---|---|---|
| card (walnut frame) | 224, 318.4, 1006.37 x 1063.97 | 179.2, 254.72, 805.12 x 851.23 |
| **parchment field** (the light field inside the card's inner dark line; where the S24 leaf lands) | 259.2, 350.4, 935.97 x 999.97 | 207.36, 280.32, 748.8 x 800.03 |
| valance (logo_title) | 784, 0.145, 992 x 296 | 627.2, 0.116, 793.6 x 236.8 |
| bar | 0, 0, 2560 x 128 | 0, 0, 2048 x 102.4 |

The storyboard (section 13) and `menu_layout.json` give the card as 224, 318.7, 1003.2 x 1057.6. The live card is 3.2 px wider and 6.4 px taller, and starts 0.3 px higher, so use the numbers above for the leaf landing (+/-0.5 px) and for G12/G14. The other buckets follow from `menu_layout.layout(W, H, card_min=(629, 665))` and `draw_rects()`. For any new bucket, confirm against a native capture with `fit_card.py`.

## Re-render

```
cd src
./make_all.sh             # keyframes, mattes, diffs, reports and review sheet from the stored captures (~1 min)
CAPTURE=1 ./make_all.sh   # also re-captures the live menu first (needs the repo served on 127.0.0.1:8765, ~6 min per bucket)
```

Single steps:
- `W=2560 H=1440 OUT=<dir> FRAMES=30 node capture_menu.mjs`
- `python3 handoff.py <capture.png> <outdir> <tag>`
- `python3 fit_card.py <capture.png> W H`
- `python3 menu_layout.py W H`

Python 3 with numpy, scipy and Pillow (system python3). The scripts write nothing to the repo.
