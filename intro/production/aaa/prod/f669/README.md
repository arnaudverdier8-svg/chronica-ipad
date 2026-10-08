# KEYFRAME f669 - S09 "Every lord looked at the empty chair" ('chair') - v3 (touch-up round, composition accepted)

Production-proof keyframe for client approval. v3 is a **touch-up only** on the accepted v2 composition: camera, light, void, crown,
lords and table are the same; three local fixes. Previous versions are kept beside it: `out_v2/`, `src_v2/`, `README_v2.md`
(v2 PNG / 16-bit / crops / report / mp4 / v1-vs-v2 sheets), `out_v1/`, `src_v1/`, `README_v1.md`.

**Regression proof:** with the four v3 switches off (`F669_NOHORSE=1 F669_V2STRANDS=1 F669_NOPOOLC=1 F669_NOMETAL=1`, plus the v2 hole / ink
values listed under "Switches") the new code reproduces the v2 PNG **bit-identically** (0 differing pixels), so every difference between
`out_v2/f669_2560x1440.png` and `out/f669_2560x1440.png` comes from the changes below.

## What changed in v3

| # | note | what was wrong (measured) | what was done (file) | result |
|---|---|---|---|---|
| a | **White blob on the green lord's chest / shield** (frame x 0.89, y 0.66 of the preview) | It is the shield's own charge, a cream wool horse head (albedo 0.5-0.66) sewn on a dark green field (albedo 0.03-0.08) and lit only by the violet night fill: the brightest thing in the right third (shield-box peak luma 0.314 = 2.7x the robe beside it, 0.116), and a cream patch with ragged outline and a hole reads as a stain, not as a charge. | `touchup.tone_emblem` (called in the edit hook of `shot.render_frame`, before the ageing pass, so it works at every mip): the connected cream component inside the shield box is closed and filled, then re-dyed x(0.46, 0.35, 0.22) = undyed wool a century old (dun / smoke-brown), feathered 0.35 mm; the gold border of the shield is excluded by hue. Stitch relief, outline and the raven's feet are untouched. | shield-box peak luma **0.314 -> 0.219**, p99 0.284 -> 0.194, mean 0.169 -> 0.137; peak / robe **2.7 -> 1.9**; peak of the right third (99.95 %) 0.276 -> 0.258. The charge still reads as a horse head (the eye finds it at 100 %), but as old dun wool in the shadow, not as a light. Same toning at the L1 mip (720p test). |
| b | **Curling purple strands read like caterpillars** | v2 threads were 1.0-1.4 mm tubes (radius 0.5 +-, 12-16 px thick at 100 %), one hard halo, slubs +-20 %, the same rendering for the whole length, with a hard-edged cast-shadow ribbon, and the four strands crossed / touched. | **Yarn**: new thread kind 4 in `threads3d.py` (`_ply_rgb`): two helically wound plies (S twist, front ply hides the back ply, own dye lot and fibre streaks per ply, occluded groove between them), 2x2 supersampled; radius **0.42 x (0.88-1.12) mm** (about 0.84 mm diameter, ~5 px at 100 %). **Fuzz**: `_fuzz_v3` (16 fine 0.03-0.05 mm fibres / mm that leave the yarn sideways + 2.6 longer flyaways / mm + a frayed, splayed end) and three faint concentric sleeves instead of one halo, so there is no edge. **Lying / lifting**: `loose.stub_curve` + `STUB_DESIGN`: each strand is pressed flat on the cloth for its first 3-6 mm out of the needle hole (z = yarn radius), then rises in a designed shape: low arch + curling free end, serpentine with a standing arch, a short strand springing up with a spiral end, a long strand with one hump and a loose hook (heights 1.2-7.5 mm, wool crimp every ~3.4 mm); headings chosen by search so the four strands never touch (min. distance 9 mm). **Dye**: the robe's own aged dye, `apply_age` at exactly the amount `shot.age_amount` gives the robe's stitches (1.12 + 0.75 x purple), blended 55 / 45 with the v2 plum so it stays purple under 1900 K; lying yarn is 10 % darker (bedded in the weave), lifted yarn up to 28 % brighter where it catches the candle (`LIFT_LIGHT`). **Contact**: a continuous contact-shadow strip for yarn lying on the cloth (v2: a detached ribbon), a tight contact AO (`contact_ao`), cast-shadow density x exp(-z / 4.5 mm) for the lifted parts, so shadows fall with the candle (up-left light, shadows down-right). | `out/f669_v2_vs_v3_strands.png`. Strand colour sampled on the yarn centreline of the delivered frame (graded sRGB): lying yarn (z < 0.6 mm) luma 37, rgb (54, 32, 40); lifted yarn (z > 2 mm) luma 55, rgb (84, 46, 51); the linen next to it is luma ~74-89, rgb ~(103-127, 67-81, 54-59) - a dark plum, always darker than the linen, brighter where it lifts into the candle, no pink / neon. The same yarn is used for every wool loose end of the unpick sequence (720p test re-rendered). |
| c | **More contrast inside the candle pool** (deeper shadows in the void's needle holes and underdrawing, crown gold as metal, lords at the rim kept) | void luma p5 0.177 / p1 0.138, holes ~umber 0.27/0.19/0.14 with a shallow pit, ink `#5A2A1B` at max 0.82; crown gold: a flat cream (luma p10 0.359 .. p90 0.733). | **Holes / ink** (void only; the goblet and candle ghosts outside the pool keep the v2 values): hole interior umber 0.27/0.19/0.14 -> **0.15/0.10/0.07**, density 0.85 -> 0.96, pit depth 0.15 -> 0.22 mm, radius x1.12, ink `#5A2A1B` -> **`#46200F`**, line opacity x1.30 (cap 0.82 -> 0.94) (`voidfx.py`, `kingvoid.py`; `groundfix.py` passes `deep=False`). **Pool contrast**: `touchup.pool_contrast` on the scene-linear frame, after the crown, strands and cool lift, before the grade: Y' = Y (Y / 0.075)^(k w), k = 0.26 below the pivot (deeper shadows) / 0.08 above (a little punch), rolled off above 4x the pivot, hue-preserving, weight w = a super-gaussian over the pool (centre x 297 / y 190 mm, 62 mm half-width, 92 / 78 mm up / down) that is 0.017 at the red lord's face and ~0 at the blue, gold and green lords. **Gold**: `touchup.metal_pop` on the crown slip's metal mask (and on the four tethers): thread-scale local contrast (sigma 1.4 px), a tone curve around the lit gold's 55th percentile (x^(1+1.0) below it so the grooves between wrapped threads sink to deep bronze, floored at 0.20; 1 + 1.4 (x - 1) / knee above it for narrow glints), and chromaticity that follows the tone (dark bronze -> amber -> gold -> pale gold only in the glints, 80 % of the ramp). | void luma: mean 0.411 -> **0.398**, p1 0.138 -> **0.101**, p5 0.177 -> **0.137**, p95 0.626 -> 0.633; darkest 2 % relative to the median **0.359 -> 0.273**; fraction below 0.15 **2.0 % -> 6.7 %**; std 0.139 -> 0.155 (the average is not lifted, the dark tail is deeper). Crown gold luma (crown-metal mask): p10 0.359 -> 0.320, p50 0.645 -> 0.678, p90 0.733 -> 0.779, std 0.149 -> **0.184**, fraction of gold pixels above luma 0.7 24 % -> 45 %. **Lords at the rim unchanged**: face luma red 0.466 -> 0.466, blue 0.230 -> 0.230, gold 0.278 -> 0.277, green 0.167 -> 0.167; wall 0.281 / 0.193 identical. |

`out/f669_v2_vs_v3_*.png` are the before / after crops at 100 % (`shield_green_lord`, `strands`, `crown_gold`, `void_needle_holes_underdrawing`,
`red_lord_rim_unchanged`, `blue_lord_rim_unchanged`) and `f669_v2_vs_v3_full.jpg`; `f669_v3_iterations.jpg` shows the tries (strands: 4,
shield dun, crown gold: 3 curves); `f669_v3_measurements.json` holds the numbers above.

**Judgement calls**

* The "white blob" is a heraldic charge, not a rendering artefact; it was kept (re-dyed) rather than removed, because deleting it would leave
  the green lord as the only lord with a blank shield (the red lord has an eagle, the blue lord scales). If the client wants it gone, set
  `HORSE_GAIN` to ~0.15 in `touchup.py` (one line) - it then reads as a faint discoloured patch.
* The four strands are still *authored* shapes (no physics); the heading / curl of each was selected for composition (four distinct silhouettes, none
  touching, all inside the void), see `STUB_DESIGN` in `loose.py`. The positions of the holes they come out of are unchanged from v2.
* The gold contrast is a conservative number (std +24 %, p90 +6 %) because the crown is already the brightest object and the director wants it kept
  as "the only gold"; the metal read comes from structure (dark grooves between wrapped threads, narrow warm glints) rather than from a lighter peak.

## Deliverables (`out/`)

| file | what |
|---|---|
| `f669_2560x1440.png` | **the keyframe**, 8-bit sRGB, Act II grade (16-bit twin `f669_2560x1440_16bit.png`) |
| `f669_preview_1280.jpg` | downscaled preview |
| `f669_crop_*.png` | 100 % crops: all v2 crops (`crown_tethers`, `crown_shadow_in_void`, `void_holes_underdrawing`, `loose_purple_strands` (re-centred), `void_top_edge`, `void_lap_bottom`, `red_lord_face_rim`, `blue_lord_face_rim`, `green_lord_rim`, `goblet_candle_ghosts_tideline`, `right_edge_candles`, `left_goblet_ghost`) + the v3 ones `green_lord_shield`, `crown_gold_metal`, `void_pool_core` |
| `f669_v2_vs_v3_*.png / .jpg`, `f669_v3_iterations.jpg`, `f669_v3_measurements.json` | before / after, tries, numbers |
| `f669_report.json` | view, timings, crop rectangles, G4 void check (PASS, 0 void pixels) |
| `f669_unpick_test_f600-660_720p.mp4`, `f669_unpick_test_sheet.jpg`, `unpick_test_720p/` | the 2 s unpick test, **re-rendered with v3** (61 frames, 1280x720, 30 fps, H.264 + AAC slice of `audio_master_1984f_s16.wav`) |
| `f669_s09_check_frames_1440p.jpg` | f561 (king intact), f600, f630, f669 at 1440p with v3 (the sequence still reads) |
| `f669_iterations.jpg`, `f669_v1_vs_v2_*`, `f669_shadow_diagnostic.png` | v2 deliverables, unchanged (the crown shadow is the v2 one) |

## Everything not touched in v3 (unchanged from v2, see `README_v2.md`)

Camera / push, candle (az 121, 12 deg, 80 mm), pool, king-shaped void silhouette and ragged border, linen enrichment, record-driven needle holes
outside the pool (goblet / candle ghosts), crown slip, tethers' geometry, crown shadow (73 mm away: the client decision of v2 item 7 still
stands), tideline, Act II grade. Known issues of v2 that remain: the crown shadow is a separate shape; strands are authored curves; L1 vs L0 differ by 3-5 % in mean
luminance; the 1440p shot should force one mip level (L0).

## Re-render

```
cd aaa/prod/f669/src
nice -n 5 python3 render_keyframe.py        # ~75-90 s wall, writes out/f669_* (F669_OUT=dir to redirect), ~3 GB peak
FORCE=1 nice -n 5 python3 render_unpick_test.py    # ~10 s / frame at 720p, 61 frames ~ 11 min (+ the first-frame asset build)
python3 measure_v3.py                       # v2 vs v3 numbers -> out/f669_v3_measurements.json
python3 review_v3.py                        # before / after crops and the iteration sheet
python3 render_frames.py DIR 561 600 630    # 1440p check frames
```

Look-dev tools (v3): `devd.py` (daemon that builds the assets once and executes `work/v3/cmd_*.py`, with `R(...)` for cached-base window
renders; the caches `work/v3/cache_*.pkl` were deleted to save disk and are rebuilt on the first call with `cache=`), `ld3.py` (one 100 % window), `crown_tune.py`
(offline gold curve grid on the cached crown window), `probe` scripts in `work/v3/`.

## Switches (every v3 change can be turned off; with all of them the frame is bit-identical to v2)

| switch | v3 default | v2 behaviour |
|---|---|---|
| `F669_NOHORSE=1` | emblem re-dyed (`touchup.HORSE_GAIN`) | cream charge |
| `F669_V2STRANDS=1` | thin two-ply yarn, designed shapes | v2 tubes |
| `F669_NOPOOLC=1` | pool contrast on (`F669_KSH` 0.26, `F669_KLT` 0.08, `F669_YPIV` 0.075, `F669_PCC_*` pool shape) | off |
| `F669_NOMETAL=1` | `metal_pop` on crown + tethers (`F669_MK_*`) | off |
| `F669_UMBER` / `F669_HOLE_A` / `F669_HOLE_D` / `F669_HOLE_R` | `0.15,0.10,0.07` / 0.96 / 0.22 / 1.12 | `0.27,0.19,0.14` / 0.85 / 0.15 / 1.0 |
| `F669_INK` / `F669_INK_G` / `F669_INK_CAP` | `#46200F` / 1.30 / 0.94 | `#5A2A1B` / 1.0 / 0.82 |

## Peak memory / render cost (measured)

Keyframe 2560x1440 at L0: **~76-90 s wall** (the same as v2: the yarn / fuzz / metal passes add ~2 s), peak RSS ~3 GB (unchanged code path for the
base); the unpick-test frames take 9-13 s each at 720p (v2: 7-12 s) because of the denser fuzz.

## Sources (`src/`)

New / changed in v3: `touchup.py` (emblem, pool contrast, metal pop), `threads3d.py` (kind 4 yarn, `_ply_rgb`, `_fuzz_v3`, contact strip / AO), `loose.py`
(`STUB_DESIGN`, `stub_curve`, robe-aged dye, `yarn_r`), `voidfx.py` + `kingvoid.py` + `groundfix.py` (deep holes / ink for the void only), `crown.py` (metal mask
layer), `shot.py` (hooks, `F669_CACHE*` look-dev cache, `fuzz` argument), `render_keyframe.py` (3 new crops), `measure_v3.py`, `review_v3.py`, `devd.py`, `ld3.py`,
`crown_tune.py`. `src_v2/` holds the v2 sources. The library `aaa/lib` is untouched; the repo `/home/user/chronica-ipad` is untouched.
