# KEYFRAME f1983 (S26): the hand-off frame (v2, review polish)

This is the live CHRONICA main menu in its no-save state (5 buttons), captured natively from the real web build at **menu frame 30** (0.5 s of game time after callMain: nameplates settled, camera on its first focus), with the card's contents removed. What remains is the blank parchment card in its walnut frame. Every pixel outside the card's parchment field is the live game, bit for bit.

v2 applies the cheap, valid items of the three reviews (9 / 9 / 8.5, all "ship"). The keyframes did not change: **`f1983_*.png` are pixel-identical to the `_v1` files** (only an sRGB chunk was added). The v1 files are kept with a `_v1` suffix (`f1983_*_v1.png`, `report_*_v1.json`, `verify_diff_*_v1.png`, `review_sheet_f1983_v1.*`, `mattes_*_v1/`, `src_v1/`, `README_v1.md`).

## What changed in v2

| review item | what was done |
|---|---|
| R1-P1 candle flame/unlit layers did not recompose (v1: up to 58/255 and 25 % alpha off at the wick junction) | rebuilt: the unlit layer first, the flame layer as the exact residual in screen space. `over(flame, unlit) == candle` to **within 1/255 (premultiplied RGB and alpha) at every pixel**, asserted in `flames.py` and re-checked by `verify_flames.py`: max 1.0/255, 0 px over, for all 5 candle sprites in both buckets |
| R1-P2 grey flame-root disc, stray specks | the unlit wick is a clean charred stroke with a slight curl (no flame root); dark residue of the wick's own antialiased edge is composited into the unlit layer; the flame layers carry only flame, clean over dark and light grounds (`qa/candle_flames_v2_*.png`) |
| R3-P4 unlit wax still read as lit | the warm top-down glow is taken out of the upper ~18 % of the wax, row by row, matched to the lower body's tone, detail kept; the removed light lives in `*_waxglow` |
| R2-P2 / R3-P2 frame, field and contents layers for S22-S25 | new mattes `menu_card_frame`, `menu_card_parchment_field`, `card_contents` and `rects.json -> content_geometry` (bands, title baseline, rule centre line, button rects, per bucket) |
| R3-P5 G12 mask | `units_water_g12_mask.png` per bucket (measured, see G12) |
| R1-P4 parchment continuity target | `rects.json -> parchment_target` and `handoff_spec.json` |
| R1-P5 colour tags | every v2 PNG deliverable carries an sRGB chunk (no pixel changes) |
| R1-P3 encode guard | recommendation plus a one-still experiment (`qa/encode_guard_test.json`), see "Encode guard" |
| R2-P1 / R3-P1 hand-off timing | corrected claim, 30-frame wait recommendation, and a simulation (`qa/dissolve_ghost_sim_16x9.png`), see "Overlay timing" |
| R2-P2 / R2-P3 storyboard numbers and wording, 4:3 chamberstick cue | listed in `handoff_spec.json -> storyboard_corrections`, `desk_light_cues` (the storyboard itself is not edited here) |
| R3-P3 client presentation | review sheet v2: context strip (PoC f1760 snapshot, f1983, two illustrative "card writes itself" frames, live menu), both buckets, 100 % corner crops for both buckets |
| R3 FYI 4:3 composition | passed on in `handoff_spec.json -> game_team_notes_out_of_scope` |

**Not applied** (reasons in `handoff_spec.json -> not_applied`): capturing mid-dissolve frames through the real overlay (needs the overlay build, about 6 min per frame; replaced by a labelled simulation); inpainting the airborne fish (keeps the literal bit match; the client may prefer a calmer poster, then it is a decision, not a fix); grain on the master PNG (would break the bit match); valance inpainting (out of scope); editing the storyboard (owned elsewhere).

## Re-verified in v2

- Outside the card rect, f1983 vs the live capture: **max 0/255, 0 px changed, in both buckets** (`verify_outside_card.py`). The changed pixels sit inside the parchment field (16:9 bbox 266,357 to 1187,1343; 4:3 213,285 to 950,1074).
- Both keyframes are pixel-identical to their `_v1` files.
- Candle layers recompose within 1/255 (above). `card_contents` over f1983 reproduces the live capture inside the replaced region: max 2/255, mean 0.16/255.

## Deliverables

| file | what |
|---|---|
| `f1983_16x9_2560x1440.png` | **the keyframe** (16:9 master bucket B169) |
| `f1983_4x3_2048x1536.png` | 4:3 bucket B133 (iPad), with the table edge (books, scroll, chamberstick) that `_layout()` shows on 4:3 |
| `verify_diff_<bucket>.png` | the absolute difference between f1983 and the live capture, amplified x8, with the card rect outlined. Outside the card it is 0 |
| `report_<bucket>.json` | numbers: the fitted card size, the draw rect of every element, the parchment-field rect, matte-vs-capture errors and seam residuals |
| `handoff_spec.json` | the non-pixel spec: overlay timing, storyboard corrections, G12, encode guard, continuity targets, 4:3 cue, game-team notes, what was not applied |
| `polish_report.json` | the numbers behind the v2 mattes (geometry bands, parchment target, G12 outlook, contents recomposition) |
| `review_sheet_f1983.png/.jpg` | client sheet (v2): context strip, both buckets, 100 % corner crops for both buckets |
| `mattes_<bucket>/` | the desk/chrome/card mattes (below) |
| `capture/c169_a`, `capture/c133_a` (and `c169_b`, a second boot for the reproducibility check) | the native live captures (`menu_<W>x<H>_mfNNN_r{0,1}.png`; r0 and r1 are two screenshots of the same frozen frame, bit-identical), plus `capture.log`. Left exactly as the browser wrote them (untagged = sRGB) |
| `qa/` | evidence images (below) |
| `src/` | every script needed to rebuild everything ("Re-render") |

## How it was made

1. **Native capture with a deterministic clock** (`src/capture_menu.mjs`). Playwright Chromium (SwiftShader WebGL2) loads the game in a fresh profile. A fresh profile has no IDBFS save, so the menu shows the 5-button card. The viewport is set natively to the bucket size at DPR 1, so the Godot canvas is 2560x1440 (or 2048x1536) and nothing is upscaled.
   - An init script virtualises `performance.now()`. Time is frozen inside each browser frame and advances exactly 1/60 s per rAF tick. Godot therefore sees a steady 60 fps however slowly SwiftShader renders. As a side effect, FramePace keeps `scaling_3d_scale = 1.0`, as on a fast device, and the menu camera tour (3 s hold, then a 14 s pan) cannot start early.
   - Once the HTML loader starts fading (callMain is done and the menu is built), the script lets N Godot frames run and then holds every rAF callback. The canvas keeps the last presented frame, so it can be screenshotted at leisure.
2. **Which frame.** Menu frames 1 to about 20 are not settled: the city nameplates pop in larger (`capture/c169_a/menu_2560x1440_mf003_r0.png` vs `mf030`). From frame 30 on, only unit idle animations and water change (frames 30 and 120: chrome bit-identical, mean difference 0.79/255, all on units and water). The keyframe uses **menu frame 30**.
   **What this does and does not claim:** f1983 is the state the live game shows during the hand-off dissolve *only if the dissolve starts after the engine has presented about 30 frames*. The overlay as written starts it at about frame 1; see "Overlay timing". Wherever the storyboard says "the live menu's first frame" (S26, section 13, G12), read "menu frame 30".
3. **Godot's 2D placement, reproduced** (`src/menu_layout.py`, `src/godot2d.py`). The script ports `main_menu.gd _layout()` and adds two engine details measured on the capture: control **positions** are rounded to whole base units (sizes are not), and TextureRect `KEEP_ASPECT_CENTERED` truncates the fitted size to an int, then centres it. Textures are sampled with Godot's box-filter mip chain and trilinear filtering; nine-patches follow canvas.glsl `map_ninepatch_axis`; the bar carries the `WOOD_DARK` modulate. Every chrome element matches the capture to **0.26-0.69/255** mean absolute error on its opaque pixels.
4. **Blank card** (`src/handoff.py`). The card's minimum size is fitted against the captured walnut frame: **629 x 665 base units at both scales**, not the 627 x 661 in `game/menu_layout.json`. The card is redrawn from `assets/tex/table_parchment/menu_card.png` (margins 46/47/48/56, stretch, bilinear). Only the parchment field is replaced: inside the inner dark line, 3 texels in, feathered over 2 texels, brass corners excluded. On content-free parchment the rebuild differs from the live card by **0.48/255** mean absolute error (0.42 on 4:3), the feather band by 0.01/255. No seam is visible at 100 %.
5. **Mattes** (`src/chrome.py`, `src/flames.py`, `src/polish.py`). Each element is drawn from its own texture into its exact Godot rect as a full-frame straight-alpha RGBA layer; v2 adds the card layers, the candle states and the G12 mask.

## Mattes (`mattes_16x9_2560x1440/`, `mattes_4x3_2048x1536/`)

All layers are full frame and aligned to the live menu. Straight (non-premultiplied) sRGB RGBA. Composite with plain `over` in `draw_order` (Godot Compatibility blends 2D in sRGB space). `rects.json` has the draw rects in base units and px, the draw order, the card's minimum size, the parchment-field rect, `content_geometry`, `parchment_target`, `g12` and `colour`.

- **Desk**: `bar_top` (walnut beam, WOOD_DARK modulate), `logo_title` (the 'Chronica' valance), `banner_side_left/right`, `candle_left/right`, `lion_statue_left/right`, `table_edge_bottom` (4:3 only); composites `desk_all_but_card`, `chrome_all`; `board_visible_alpha` (1 where the 3D board shows).
- **Card**: `menu_card` (the blank card, as before); **`menu_card_frame`** = the card with the parchment field cut out (alpha 0 inside the field up to the inner dark line; walnut, dark line and brass corners opaque), **`menu_card_parchment_field`** = the field alone. They are a hard complementary split: `over(menu_card_frame, menu_card_parchment_field) == menu_card`. The S24 leaf lands **under** the frame layer ("the frame now holds the page"), so a leaf slightly larger than the field never shows a seam. **`card_contents`** = the live card contents (title and ornaments, subtitle, rule, 5 buttons, footer) as a straight-alpha layer, a difference matte of the live capture against f1983: `over(card_contents, f1983) == the live capture` inside the replaced region (max 2/255, mean 0.16/255). `card_parchment_replaced_alpha` = exactly the pixels f1983 changed.
- **Candle states** for the relight beats (f1612-f1707), for `candle_left`, `candle_right` and (4:3) `table_edge_bottom`:
  - `<name>_unlit`: flame removed; charred, slightly curled wick; the baked warm glow taken out of the upper ~18 % of the wax;
  - `<name>_flame`: the **exact residual**, `over(<name>_flame, <name>_unlit) == <name>` within 1/255 (premultiplied RGB and alpha);
  - `<name>_flame_core` (flame body, halo and the ember on the wick, above the wax) and `<name>_waxglow` (the flame's light on the wax and rim): disjoint support, they add up to `<name>_flame`. Use the two when the flame (flicker, grow-back from a dark ground) and its light on the wax need separate motion.
  - Method: `v1` split alpha with a soft mask, which cannot recompose under `over`. v2 solves `alpha_f = 1 - (1 - a_full)/(1 - a_unlit)` where the unlit layer is not opaque, the smallest alpha that keeps the straight colour in [0,1] where it is opaque, from the pixels the mattes store. The dark brown residue of the wick's own antialiased edge is moved into the unlit layer (exact). `flames_report.json` has the numbers per sprite. Residual alpha of 1/255 is dropped as noise (error at most 1/255). A few isolated warm pixels remain at the rim edge in `waxglow` and below the flame base in the chamberstick `flame_core`: invisible at 1x.
- **`units_water_g12_mask`**: 255 where the live board is not static (see G12).

## Content geometry (for the reading-order wipe and the drypoint ruling)

`rects.json -> content_geometry`, per bucket, measured from `card_contents` (alpha > 24), in px of the native capture and in base units (px / canvas scale): `title` (with `word_x_px`, `ornament_left_x_px`, `ornament_right_x_px` and the glyph **`baseline_y_px`**), `subtitle_1`, `subtitle_2`, `rule` (with **`centre_y_px`** and the boss column), `button_1..5`, `footer`.

| 16:9, px | x | y |
|---|---|---|
| title block | 299-1155 | 389-493 (baseline y 481, word x 504-956) |
| subtitle 1 / 2 | 434-1020 / 409-1044 | 549-586 / 598-637 |
| rule | 294-1160 | 656-675 (centre line y 670.0, boss x 725) |
| buttons 1-5 | 294-1160 | 694-797, 816-918, 938-1040, 1059-1162, 1181-1283 |
| footer | 489-959 | 1307-1335 |

In base units both buckets agree (baseline 300.6-300.8, rule centre 418.7), which cross-checks the layout port. The 4:3 numbers are in `rects.json`.

## Overlay timing (the hand-off motion)

The claim "the frame-30 state is what the player sees during the dissolve" had not been checked, and the overlay code says otherwise: `finish()` in `game/intro_overlay_snippet.html` starts the dissolve when `#status` fades, right after callMain, at about menu frame 1. The 0.9 s `ease` dissolve then runs across frames 1-20, while Sablon, Grandbois and Hautecouronne are still popping in larger and offset: for about 0.3 s, at roughly 40-55 % live opacity, they show ghosted doubles.

**Recommendation** (also in `handoff_spec.json`): after the engine-ready signal, `finish()` waits for **at least 30 presented canvas rAF frames** before starting the dissolve and the card wipe. Count frames, not milliseconds (the first iPad frames hitch). Budget: 30 frames (0.5 s) + 1.2 s card wipe = 1.7 s, inside the 3 s tour hold. If the wait is refused, rebuild f1983 on the frame that matches the dissolve midpoint (`make_all.sh` with `FRAMES=<n>`).

**Evidence, and its limit.** `qa/dissolve_ghost_sim_16x9.png` and `qa/dissolve_ghost_sim.json` simulate `shown = alpha f1983 + (1 - alpha) live` with the CSS `ease` curve over 0.9 s, using the stored captures (A: live = menu frame 3; B: live = menu frame 30). The crops show the doubled Grandbois and Sablon plates (and a doubled unit) in A and none in B; outside the card the mean difference to f1983 at 0.3 s (opacity 0.42) is 0.92/255 with 1.5 % of pixels over 16 in A and exactly 0 in B (it is 0 by construction, since f1983 is that frame outside the card). **This is arithmetic on captures, not the real overlay run through the clock harness.** The capture-based proof (4-5 mid-dissolve frames through the real overlay with the 30-frame wait) is still open, and G12 on device stays mandatory.

## G12 (16:9 and 4:3, outside the card rect)

| f1983 vs | no mask: mean abs | no mask: px > 16 | with `units_water_g12_mask` |
|---|---|---|---|
| live menu frame 30 (its base) | 0.000/255 | 0 % | 0.000/255, 0 % |
| 16:9 frame 3 (nameplates still popping in) | 1.59/255 | 1.9 % | 0.061/255, 0 % |
| 16:9 frame 120 (2 s: units idle, water moved) | 1.11/255 | 1.5 % | 0.215/255, 0 % |
| 16:9 second boot, frame 30 | 0.001/255 | 0 % | 0.000/255, 0 % |
| 4:3 frame 60 | 0.85/255 | 1.2 % | 0.052/255, 0 % |

The mask is the dilation (6 px) of every pixel that differs by more than 6/255 between menu frame 30 and the other stored captures of that bucket (units idling, water, random dust, nameplate pop-in): 5.5 % of the 16:9 frame, 5.0 % of the 4:3 frame. It is empirical. 4:3 has only two captures (frames 30 and 60), so a unit that moves differently in another frame is not covered: re-derive it from more captures if G12 starts flagging units. Text, flames and the card interior are excluded as in the storyboard definition. The final G12 still has to be run on device (iPad Safari, the shipped encode, decoded during the dissolve).

## Encode guard

The blank parchment field is the game's 260x340 texture stretched about 3.9x: very low-frequency (2 px high-pass std about 0.45/255 in 16:9, 37 distinct luma values across the field), so it is the area most likely to band in an 8-bit delivery, especially during the S24-S26 dissolve. It must not be altered (it has to match the live game), and **no grain is added to the master PNG**. Recommendation: encode the master 10-bit where the target decodes it, or 8-bit with `tune=grain`/`film` and a high AQ strength, and add the field to G12 **on the encoded file**, not only the PNG. Tag the stream BT.709, range matched to how the game presents on device.

`qa/encode_guard_test.json` is one still at three settings (x264 8-bit CRF 18, the same with tune=grain and AQ mode 3, x265 10-bit CRF 18): none collapsed the field's levels (37 to 36-37) or raised the largest 24 px block step (4.4 to 4.2-4.6), but every setting moved the field by a mean 1.8-2.7/255 (max 7-9), the 8-bit ones added high-pass energy (0.45 to 0.65-0.69), and the 10-bit run was not better on mean error. It neither proves banding nor clears the risk. The dissolve frames and the ~6 Mb/s cap were not tested.

## Continuity targets for S24/S25

`rects.json -> parchment_target` (and `handoff_spec.json`): mean RGB 232.2 / 208.7 / 174.0 (16:9), mean luminance 204.9, high-pass std at sigma 2 px 0.45/255, foxing specks about 95 per megapixel (16:9; 147 in 4:3, scale dependent). The tapestry leaf that lands on the card must be low-passed and graded to these before the dissolve, or the hand-off reads as a pop from sharp textile to soft bitmap. The game frame has flat, even lighting and no measurable card drop shadow (sea just right of the card vs 120-220 px out: ratio 1.03), so the cinematic's raking light must be fully graded out by the start of the dissolve.

## 4:3 notes

- The 4:3 table edge carries a third lit flame (the chamberstick) that no desk-light cue covered. Suggested: light it with the left candle at f1664 (layers `table_edge_bottom_unlit/_flame/_flame_core/_waxglow`).
- For the game team (live art, repo read-only): on 4:3 the 'Hautecouronne' nameplate is clipped at the right frame edge and partly behind the right candle, and the frozen floe and fish sprites in the lower sea read as stray paper scraps in a still. A cinematic that matches the menu pixel for pixel cannot fix either.

## Reproducibility

`capture/c169_b` is a second, independent boot captured with the same script. Compared with `c169_a` at menu frame 30, it is bit-identical except for **334 px** (0.009 % of the frame; max 25/255): a faint randomly seeded dust puff over unit shields (`qa/repro_runA_vs_runB_clusters.png`). Everything after the capture is deterministic: `make_all.sh` reproduces the keyframes bit for bit (checked against `_v1`).

## Numbers that matter to other shots (16:9 / 4:3, px)

| element | 16:9 2560x1440 | 4:3 2048x1536 |
|---|---|---|
| card (walnut frame) | 224, 318.4, 1006.37 x 1063.97 | 179.2, 254.72, 805.12 x 851.23 |
| **parchment field** (inside the inner dark line; where the S24 leaf lands, +/-0.5 px) | 259.2, 350.4, 935.97 x 999.97 | 207.36, 280.32, 748.8 x 800.03 |
| valance (logo_title) | 784, 0.145, 992 x 296 | 627.2, 0.116, 793.6 x 236.8 |
| bar | 0, 0, 2560 x 128 | 0, 0, 2048 x 102.4 |

The storyboard (section 13) and `menu_layout.json` give the card as 224, 318.7, 1003.2 x 1057.6 (16:9) and 179, 255, 803 x 846 (4:3), and the parchment interior as 272, 357.3, 910.7 x 976. All of these are superseded by the numbers above (the full list is `handoff_spec.json -> storyboard_corrections`). The other buckets follow from `menu_layout.layout(W, H, card_min=(629, 665))` and `draw_rects()`; confirm each against a native capture with `fit_card.py`.

## QA images (`qa/`)

`card_layers_16x9.png` / `_4x3.png` (frame, field, contents on a checker, contents over f1983, the live capture, and the G12 mask overlay); `candle_flames_v2_16x9.png` / `_4x3.png` (full, unlit, flame core, wax glow, recomposed, on dark and light grounds, x5; the v1 split is `candle_flame_unlit_split.png`; a v1 contact sheet at the same scale is `candle_flames_v1_169_before.png`); `dissolve_ghost_sim_16x9.png`; `encode_guard_test.json`; plus the v1 evidence (nameplate pop-in, frame 30 vs 120, card rebuild residual x16, parchment-field rect, chrome on dark, reproducibility).

## Re-render

```
cd src
./make_all.sh             # keyframes, mattes, polish layers, simulation, spec, review sheet, sRGB tags and checks, from the stored captures (~4 min, of which ~40 s the encode test: ENCODE_TEST=0 skips it)
CAPTURE=1 ./make_all.sh   # also re-captures the live menu first (needs the repo served on 127.0.0.1:8765, ~6 min per bucket)
```

Single steps: `W=2560 H=1440 OUT=<dir> FRAMES=30 node capture_menu.mjs`; `python3 handoff.py <capture.png> <outdir> <tag>`; `python3 polish.py <outdir>`; `python3 flames.py <matte_dir> W H CARD_W CARD_H`; `python3 verify_outside_card.py <outdir> --ref-suffix _v1`; `python3 verify_flames.py <matte_dir>`; `python3 png_srgb.py <files...>`; `python3 fit_card.py <capture.png> W H`; `python3 menu_layout.py W H`. Python 3 with numpy, scipy and Pillow (system python3); ffmpeg for the encode test. The scripts write nothing to the repo.

## Known issues

- Frame choice: not literally the first menu frame, by design (frame 30), and only equal to what the player sees if the 30-frame wait is adopted. The frame-3 version can be rebuilt with one command.
- The capture is software WebGL (SwiftShader) in desktop Chromium, not iPad Safari. The 2D chrome and the card are device-independent (Godot draws its own text and art), but the 3D board's sampling and precision may differ on a real iPad GPU. The on-device G12 check is still required.
- Units' idle animations, water and tiny random dust puffs are live and differ between frames and boots.
- Only the B169 and B133 buckets were captured; the others need the same scripts once the iPad Safari viewport sizes are measured.
- The valance letters and ornaments are kept as live art (inpainting for the S24-S26 stitch-on layer was not in scope).
- The G12 mask is empirical (stored captures only); the dissolve simulation is not the real overlay; the encode experiment is one still.
- The static file server this stage started (`python3 -m http.server 8765`, PID 2008) was left running for other agents. Stop it when the stage is over.
