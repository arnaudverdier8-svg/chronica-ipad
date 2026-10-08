# KEYFRAME f669 - S09 "Every lord looked at the empty chair" ('chair') - v2 (fix round after the three critiques)

Production-proof keyframe for client approval, plus a 2 s, 720p proof that the king's unpick reads as physical.
v1 is kept beside it: `out_v1/`, `src_v1/`, `README_v1.md` (the v1 test frames are in `out_v1/unpick_test_720p/`).

## What changed in v2 (director's notes + the three critiques)

| # | note / critique item | verdict | what was done (file) | measured |
|---|---|---|---|---|
| 1 | **Void too bright and flat; a cream column** | accepted | no more "protected / fresher linen" (the ghost channel is not read at all); the void is the same aged linen as the cloth around it (`shot.age_amount`, linen gain) and sits in the candle pool as a gradient, pool re-centred up-left (`shot.POOL`, `GAMMA_PHYS` 0.45); a cool night lift in the deepest shadows | graded luma of the void: mean 0.574 -> **0.411**, p95 0.748 -> **0.626**; the red lord's face (0.466) is now brighter than the void, the neighbouring wall linen is 0.28 / 0.19 (was 0.14 / 0.15) |
| 2 | **Periodic sieve weave, stamped slubs** | accepted | `voidfx.linen_enrich`: every thread wanders on its own (+-0.17 mm, slow along its length), per-thread thickness and tone with long correlation along the thread, longer rarer slubs, 1.2x weave relief, soft hoop creases. Deterministic in sheet mm | FFT peak/mean of a 512 px void window **108.6 -> 59.1** (neighbouring linen 167 -> 68; the same enrichment is on all bare linen so void and surround match) |
| 3 | **Needle holes: uniform black stipple, perforated paper** | accepted | `voidfx.holes_from_record`: holes only at the real strand ends of the unpicked stitches (entry / exit pairs along the stitch rows, thinned to 0.46 mm), elongated along the stitch (1.45 : 0.78), 0.12-0.36 mm, dark umber 0.27/0.19/0.14 (not black), shallow pit (AO cannot crush it), one-sided displaced-thread rim and a soil halo (`voidfx.apply_holes`) | see crops |
| 4 | **Underdrawing: flat, even, a ruler line** | accepted | `silhouette.draw_underdrawing` / `voidfx.ink_alpha`: wobbling broken pen strokes (0.55-1.0 pressure, 22-80 sample runs), pen-pressure map and lifts, ink `#5A2A1B`; the bake's polygon-edge lines are subtracted (they traced the straight hint polygon); ghosted compression imprint of the dense stitching (`kingvoid`, height -0.05 and tone -6 % under the old stitch coverage) | - |
| 5 | **Lap rectangle with a hard border** | accepted | the lap rectangle was the bake polygon's bottom edge (a ruler-straight stop of holes + ink). The polygon-edge ink and a 0.8 mm band of holes along it are suppressed; the unpicked border is ragged (silhouette test with +-2.2 mm noise and +-0.9 mm per-strand jitter, `silhouette.inside_ragged`), a few stitches beyond the line are cut too (decaying with distance), holes bleed out over 7.5 mm through a noise-displaced mask (`voidfx.bleed_holes`) | - |
| 6 | **Crown shadow: hard grey dome, no silhouette, straight edges, no tether shadows** | accepted | `crown.CrownSlip.layers`: the shadow is the real crown alpha (incl. the side prongs the bake clipped, see 11) projected from an **extended candle** (40 low-discrepancy samples over an ellipsoid r 3.7 mm x +-2.2 mm); the penumbra grows with the throw. Applied as a 50 % density on the lit linen **before the grade**, cool-tinted (1.0/0.94/0.80), so weave and holes stay visible inside it, and it runs over the throne's wool instead of being cut at a mask. Four tether shadows (same projection, tether from z = 0 to the crown) | `out/f669_shadow_diagnostic.png` shows the crown alpha, the projected shadow, the four tether shadows and the result side by side |
| 7 | **Crown shadow detached ~400 px from the crown** | **NOT fixed (client decision)** | the throw follows from the storyboard's 12 deg candle and 15 mm lift: analytic offset of the crown's shadow is 71 mm in v1 and **73 mm in v2** (44 mm right, 58 mm down; az 121 / candle 80 mm high), so the shadow is still a separate shape below-right of the crown. I did **not** change the 12 deg / 15 mm values (storyboard G5 / pipeline 6; S10 and S11 depend on them). What v2 adds so the shadow belongs to the crown: its real silhouette (finial, prongs, band), four tether shadows running from the crown toward it, and the soft contact occlusion under the band (item 12). | to client: if they want the shadow to touch the crown, raise the candle to 22-25 deg or drop the lift to 6-8 mm for this frame (documented deviation) |
| 8 | **Purple strands: neon pink, chenille beads, pipe cleaners; long dark parallel streaks** | accepted | colour = the robe's dye as the cloth ages (`apply_age(age=1)`), chroma capped at 0.078, rotated -22 deg toward the blue-purple, 0.93 x L (the banner and robe are aged harder too: `shot.age_amount`, purple leaves with the king); `threads3d` wool: long irregular 2-ply pitch, two ply dye lots, deep ply grooves, slubs (thick-thin +-14-20 %), fraying tapered ends (6 splayed fibres on the dressing strands), 9 fibres/mm, 1.9x radius halo, specular almost gone (matte), tip dips into a needle hole (radius / opacity ramp). Shadows: contact shadows only, density x exp(-z / 3.4 mm), 6 mm flame radius for the penumbra, so no long streaks. **Four** strands (was five), different lengths, unmirrored, all inside the void | strand luma 0.17-0.28 vs surrounding linen ~0.45 (v1 strands were lighter than the linen next to them) |
| 9 | **Rectangular pale patches around the goblets / candles** | accepted | root cause: the bake protected (flattened + un-yellowed) the linen over each hint rectangle. Not read any more, so there is no protected patch. The hint rectangles of candle_1 / candle_2 also swallowed the green lord's robe, belt and hand; goblet_0's cup was never in its group (it merged into the gold lord's torso region) and its hint polygon cut the tan strap running down-left from the sword; goblet_1 lost the loaf end and plate rim. Those entries are put back in the ground (`groundfix._rules`, `_cup_entries`), the cup is unpicked as a closed loop | no straight-edged clearings left in the crops |
| 10 | **Void edges: razor-straight top under the crown, grey-blue cape remnants, pink ridge, hollow squares in the crown** | accepted | ragged border (5); the grey padding blocks beside the head that the polygon missed (C < 0.065, hue 190-320) are unpicked 92 %; the crown slip maps are now filled (normalised convolution), not just its alpha, so no hollow squares; the crown's pin-holes are gone | - |
| 11 | **Crown: tethers smooth pale sticks, stop short of the corners, no shadow, glued to the arch** | accepted | tethers are couched gold cord (`threads3d` kind 3: two plies of Japan gold round a silk core, visible wrap, 0.5 mm radius, sag 4.2 mm, lateral wobble), anchors on the real silhouette (band corners and prong tips, `crown._anchors`), feet snapped onto bare linen (`snap_holes_to_linen`), the tip dips into the hole with a puckered ring; the crown also includes the 133 prong-stub entries the bake left in the ground (they were stitched brown thorns beside the lifted crown) | - |
| 12 | contact: thin dark gap under the crown rim | accepted | soft contact occlusion under the rim (offset 1.8 mm, sigma 2 mm, 36 %) | - |
| 13 | **Light state: candle low on the LEFT, right in shadow; shadows fall straight down** | accepted | candle az 108 -> 121 deg (the storyboard's nominal 135 would put the crown's shadow on the throne's right pillar; 121 still lands it in the void), pool asymmetric (rx 105 mm left / 88 mm right, centre moved left to x 277) | graded luma red 0.47 / gold 0.28 vs blue 0.23 / green 0.17: the left lords are ~1 stop above the right; wall 0.28 left / 0.19 right |
| 14 | **Colour Act II: warm sepia, not night violet; strands + shadow compete with the crown** | accepted | night fill (#141325) lifted 0.085 -> 0.05 relative and a cool lift in the deepest shadows (`COOL_LIFT`), linen darker / browner than the library's Act II (a century of light), banner purple aged harder, wool dyes aged an extra 12 % (sat toward 0.7); the crown is the only gold, the strands are dark plum, the shadow is cool | - |
| 15 | **Tideline: only the background one reads; make a proper stained edge across the table / lap** | accepted | `shot.tide_layer`: 3 mm dried darker edge, lighter inner ring, stained interior (0.34), bleached margin just outside; the upper-left wall one is quieter (weight 0.22 from 0.6) | tideline visible across the lap and the table in the full frame |
| 16 | **Lord at the green edge nearly lost, magenta / blue noise cast** | partly | the green lord's face is lifted by the left-biased, flatter pool floor and the cool shadow lift; the colour cast itself was not measured separately | green face luma 0.167 (was 0.125 in the v1 preview) |
| 17 | **720p test vs keyframe grade mismatch; weave vanishes at 720p; unpick front busy** | accepted | one function (`shot.render_frame`) with one grade; L1 weave enrichment attenuated with the screen scale; L0/L1 luminance measured at 0.96 (`src/calib_l1.py`) | `out/f669_unpick_test_*` |
| 18 | **S09 test: outer-left goblet still stitched at 1.06x; outer candles partly unpicked; erect pink-tipped stalks at 720p; f561 intact?** | accepted | outer-left goblet (goblet_0's cup) and the strap are fixed (9); candles are unpicked as whole groups; the loose ends are the new wool (matte, plum, recumbent); f561 rendered at 1440p: the king is intact | `out/f669_s09_check_frames_1440p.jpg` (1440p frames f561, f600, f618, f630, f648, f669; full-res frames were not kept) |

**Rejected / deviated, with reasons**

* Crown shadow touching the crown by raising the elevation to 22-25 deg or lowering the lift to 6-8 mm (item 7): the storyboard fixes the 12 deg candle and the 15 mm lift (G5 maximum); changing them changes S10 and S11 as well. Offered to the client as a decision, kept at 12 deg and 15 mm.
* az 135 (the colour script's nominal key): the crown's shadow would fall on the throne's right pillar; az 121 is the nearest value that keeps it in the void.
* "Void centre should be 100-120 luminance of 255": measured luma of the void is 0.41 (about 105 of 255 in sRGB), matching the critic's target range; p95 0.626 is a little above the critic's 0.60 because of local highlights on holes' rims and the area next to the crown.
* "Hair-line underdrawing so a seated king reads at 1280": the underdrawing now has pen pressure and broken strokes, but at 1280 it still reads as a faint head-and-shoulders only along the flanks; it is deliberately faint ("underdrawing has no relief and no sheen", storyboard S09).

## Deliverables (`out/`)

| file | what |
|---|---|
| `f669_2560x1440.png` | **the keyframe**, 8-bit sRGB, Act II grade (16-bit twin: `f669_2560x1440_16bit.png`) |
| `f669_preview_1280.jpg` | downscaled preview |
| `f669_crop_*.png` | 100 % crops: `crown_tethers`, `crown_shadow_in_void`, `void_holes_underdrawing`, `loose_purple_strands`, `void_top_edge`, `void_lap_bottom`, `red_lord_face_rim`, `blue_lord_face_rim`, `green_lord_rim`, `goblet_candle_ghosts_tideline`, `right_edge_candles`, `left_goblet_ghost` |
| `f669_report.json` | view, mip level, timings, measured scene-linear EV of faces/crown/table vs the lit void, crop rectangles, G4 void check |
| `f669_unpick_test_f600-660_720p.mp4` | 61 frames (f600-660) at 1280x720, 30 fps, H.264 + AAC slice of `audio_master_1984f_s16.wav` (sample = f * 1470) |
| `f669_unpick_test_sheet.jpg`, `unpick_test_720p/f*.png` | contact sheet and the frames of the test |
| `f669_iterations.jpg` | the v2 visual iterations (v1 -> final), for the review |
| `f669_v1_vs_v2_*.png`, `f669_v1_vs_v2_full.jpg` | before / after at 100 % (void, strands, crown, shadow, table ghosts) and full frame |
| `f669_shadow_diagnostic.png` | crown alpha, projected shadow, tether shadows and the result, side by side |

## What is in the frame and how it is made (v2)

| storyboard element | implementation |
|---|---|
| p1' at 1.25x, throne at frame x 0.47 | `shot.view_of`: 5.8125 px/mm (F1 4.65 x 1.25), throne axis x = 294.5 mm at 0.47 x 2560; camera path for the whole shot (locked 1.06x, 1 px/frame drift, smoothstep-eased exponential push f637-669, 2 px/frame drift after) |
| one guttered 1900 K candle low on the left, 12 deg | a shadowed point practical (`candle_relight.py`): 80 mm high, 376 mm from the void, az 121 at the void (upper left, beyond the panel's top edge), 12 deg at the throne; guttering = slow 1-2 Hz breathing <= 2.2 %, 7.7 Hz <= 0.6 % (G13-safe), 1 mm flame sway |
| pool on the throne, right of the scene in shadow | key-light pool shaping the CANDLE (not a directional key): an asymmetric elliptical pool centred at x 277 / y 170 mm (rx 105 mm toward the candle, 88 mm away), amplitude 0.62, floor 0.04; 45 % of the physical inverse-square falloff kept; cool night fill (#141325) at 0.05 x I0. Measured graded luma (Rec.709, 0-1): red face 0.47, gold face 0.28, void 0.41 (p95 0.63), blue face 0.23, green face 0.17, wall 0.28 left / 0.19 right |
| KING-SHAPED void, needle holes, red-brown underdrawing | `kingvoid.py` + `silhouette.py` + `voidfx.py`: hand-traced silhouette with a ragged cut line; same aged, enriched linen as the surrounding cloth (not protected); record-driven needle holes (anisotropic, umber, with rim and halo); pen-pressure underdrawing with breaks; ghosted compression imprint of the dense stitching; the throne's backrest and wood stay |
| a few purple strands still curling off the cloth | `loose.py`: 4 'stubborn' purple laid threads of the lap (not mirrored), pulled slowly through their holes (mid-pull at f669); `threads3d.py` wool in the robe's aged dye (chroma <= 0.078), 2-ply with irregular pitch, slubs, fuzz, fray, matte, contact shadows only. Plus wisps of wool left in ~7 % of the needle holes |
| gold crown slip ~15 mm above the void, four gold tethers, soft shadow below | `crown.py`: baked 'crown' group plus its 133 prong-stub entries, filled slip maps, lit by the candle at its own height, perspective parallax, 2.4 deg turn; shadow = slip alpha projected from an extended candle (40 samples), 50 % density, cool, before the grade; four tether shadows; contact occlusion; four couched-gold cords (`threads3d` kind 3) from the real silhouette to needle holes snapped onto bare linen |
| Act II grade, aged / desaturated | `render(age=age_amount)` (dyed wool 1.12, the banner / robe purple up to 1.87 = aged hard) + linen gain 0.84/0.80/0.72 + cool shadow lift + `grade(act='II')` |
| a tideline across the cloth | `shot.tide_layer` (3 mm dried edge, lighter inner ring, stained interior, bleached margin) across the lap and the table; the upper-left one is quiet |
| goblets and stitched candles reduced to needle-hole outlines | `groundfix.py`: all cups, candles and holders (plus goblet_0's cup, goblet_1's bowl) as needle-hole pairs + underdrawing, no protected patches; neighbouring embroidery that the bake's hint rectangles had swallowed is restored |

## Patches to the bake made in my own scripts (no library file was edited)

`kingvoid.py`: record re-partition by a ragged silhouette, + grey padding blocks, + a ragged nibble of stitches just outside it; ground patch rebuilt (analytic linen + replay; bit-exact reconstruction proof in `work/a4_recon.py` still holds for the replay part). `groundfix.py`: ghost patches rebuilt, group entries restored to the ground, bowl / cup / prong-stub removal. `voidfx.py`: linen enrichment, holes, ink, imprint, bleed. `threads3d.py`, `crown.py`, `loose.py`, `shot.py`: as above. `candle_relight.py` unchanged. The library `aaa/lib` is untouched.

## Re-render

```
cd aaa/prod/f669/src
nice -n 5 python3 render_keyframe.py        # ~60-70 s wall, writes out/f669_* (F669_OUT=dir to redirect)
nice -n 5 python3 render_unpick_test.py     # ~10 s/frame at 720p (61 frames ~ 10 min), writes the mp4 + sheet
python3 review_sheets.py; python3 shadow_diag.py     # v1-vs-v2 crops, crown-shadow diagnostic
python3 lookdev.py full|void|crown|strands|lords|lgob|gob0 [tag]    # fast look-dev windows (work/)
python3 measure.py image.png; python3 fftcheck.py a.png b.png; python3 calib_l1.py 669      # QA numbers used above
```

Look-dev parameters can be overridden by environment (`F669_AZ`, `F669_CZ`, `F669_AMP`, `F669_PCX`..., `F669_SHD`, `F669_COOL`, `F669_LGR/G/B`); the defaults in `shot.py` are the delivered values.

## Peak memory / render cost (measured)

Keyframe 2560x1440 at L0 (10 px/mm), re-run from scratch in a clean process (`work/rss_run.py`, `ru_maxrss` of the child): **81 s wall, 2.94 GB peak RSS** (the earlier background run measured 61.6 s for the frame alone; asset build ~18 s once per process; v1 was 55 s / 2.70 GB). The extra ~0.25 GB is the enriched linen window and the 40-sample shadow accumulation. The re-run is **bit-identical** to the delivered PNG. Unpick test: 61 frames at 720p (L1), 7-12 s/frame (first frame 31 s with the asset build), ~10 min total.

## Known issues / limits (v2)

* The crown's shadow is still a separate shape 73 mm away (item 7): client decision.
* The needle holes are now small, umber and sparse; at 1280 the void reads mostly through weave, ink and the shadow, and the holes read at 100 % crops. If the client wants them stronger at 1280, raise `holes_from_record` radius or the `apply_holes` alpha (one line each).
* The purple strands read as thick wool at 100 % but are still the strongest dark mark in the void; four rather than five and not mirrored.
* The face pools: the red lord (0.47) is now brighter than the void (0.41) by the critics' brief; the storyboard's "-1.5 EV rim" is therefore met for the blue (-1.9 EV) and green lords (-2.7 EV) and not for the red one. The `EV_vs_void_head` numbers in `f669_report.json` are relative to the void's head (now darker), so they are not comparable with the v1 report.
* L1 (720p test) vs L0 (keyframe) differ by 3-5 % in mean luminance (`calib_l1.py`: L0/L1 = 0.96) and in weave detail; the grade is the same.
* The loose wool is an authored curve model (no physics).
* The 1440p shot should force one mip level (L0) for f561-716.

## Sources (`src/`)

`shot.py` (camera, light, pool, tideline, age map, compositing order, `render_frame`), `candle_relight.py`, `kingvoid.py`, `silhouette.py`, `voidfx.py` (new), `groundfix.py`, `loose.py`, `threads3d.py`, `crown.py`, `render_keyframe.py`, `render_unpick_test.py`, `render_frames.py`, `review_sheets.py`, `shadow_diag.py`, `lookdev.py`, `measure.py`, `fftcheck.py`, `fftcheck2.py`, `calib_l1.py`, `test_threads.py`, `dbg_shadow.py`. `src_v1/` holds the v1 sources. `work/` holds analysis scripts and iteration previews (`b*`, `c*`, `t*`, `kf*`, `chk/`).
