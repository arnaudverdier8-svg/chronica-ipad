# CHRONICA intro, proof of concept v3: "The cloth becomes the board" (f1664-1782)

3.97 s (119 frames, 30 fps, 2560x1440) of storyboard shots S22 (end) to S24, muxed with the matching slice of `aaa/audio/audio_master_1984f_s16.wav`
(samples 1664*1470 to 1783*1470). v3 is the rework after the second round of three critics (6.5 / 6.5 / 6.8). The earlier files are kept with `_v1` / `_v2` suffixes
(`poc_cloth_to_board_2560x1440_v2.mp4`, `src_v2/`, `v2_frames/`, `r25_v2/`, `maps_v2/`, `data_v2/`, `README_v2.md`, `before_after_v1_vs_v2_v2.jpg`, ...). Scope is still only the board:
no desk chrome, valance or leaf.

## Deliverables (this directory)

| file | what |
|---|---|
| `poc_cloth_to_board_2560x1440.mp4` | H.264 High, yuv420p, bt709 (tagged, tv range), x264 slow CRF 14, AAC 192k; 119 frames; the muxed audio matches the WAV slice at lag 0 samples, r = 0.9996 |
| `frames/f1664.png ... f1782.png` | the graded master frames, 2560x1440 sRGB (decoded mp4 frames differ from them by 2.2 to 3.2 / 255 mean, grain included) |
| `keyframe_f1760_2560x1440.png` | storyboard keyframe 5 (climax peak), board only |
| `before_after_v1_v2_v3.jpg` | v1 | v2 | v3 side by side at eight key moments |
| `contact_sheet.jpg` | f1664 to f1782 at a glance |
| `stitch_on_detail_1to1.jpg`, `pieces_detail_1to1.jpg` | 1:1 crops: needle frontier, underdrawing ahead, Grandbois, figure cards, footprints, forest |
| `glint_band_travel.jpg` | ground-only 720p strip f1736 to f1764 showing the travelling gold glint (numbers in `data/glint_measure_v3.json`) |
| `ab_swap_f1719_vs_f1725.jpg` | R25 2D vs the Eevee zero-tilt still at the swap, plus a difference image |
| `compare_f1782_vs_menu.jpg` | v2 / v3 final pose next to the live menu's first frame, plus the v3 neutral-light palette check render |
| `qa.json` | measured numbers (swap, crane, pieces, tethers, light, per-frame luma, frame-to-frame change, gold glint, floor, voids) |
| `data/palette_report.json` | palette gate (neutral light, neutral grade at exposure 0.14), class medians in OKLab vs the menu |
| `data/palette_report_shown.json` | the same measure on the film as shown (candle falloff, Act V grade, light state 44 % toward D) |
| `src/` | every script plus `poc_scene.blend`; `src/lookdev/` the look-dev helpers (border renders, pool previews) |
| `ev/`, `r25/`, `maps/`, `data/` | raw Eevee EXRs, graded R25 frames, bake record and Eevee inputs (so a grade or comp change re-runs in minutes) |

## What the critics asked for and what was done

Accepted and done (verified by looking at renders and by numbers in `qa.json`):

| critic finding | v3 |
|---|---|
| Pieces read as CG toys: cream plaster, glossy orange roofs, razor silhouettes, white quarry, crate camps, lathe pines | Felt palette (`FELT` in `bl_scene.py`): oatmeal walls (`#C9BC9E`), dusty-madder roofs (`#A25C40`), blue slate spires on Grandbois (the menu's blue/grey spires), weathered rock quarry, matte roofs (rim 0.14). Laid-wool strand relief plus a second fibre bump, groove AO, macro dye-lot patches, per-object lot. Bevels widened (0.020 / 0.012). Fibre-halo shell (hashed alpha, grazing-angle gated) on trees. Contact-occlusion map under every risen piece. Pines: irregular tier radii, tilted off-centre tiers, scalloped drooping skirts; broadleaf = 5-7 lumpy lobes. |
| Figure cards are pasted sprites (heavy dark cel outline, no response to light) | `cards_bake.py`: each card is re-embroidered on its own canvas at 2.4x stitch density (13 OKLab clusters, contour-following laid wool), couched outline in the figure's own darkest dye (OKLab L x0.82, 0.40 mm), no die-cut ring (eroded away). In 3D: an appliqued felt card with 0.6 mm thickness (extruded outline, felt edge, cloth back), strand normal map, alpha cut-out holes, contact AO, idle sway. |
| First stitches (f1664-1672) rigid dark capsules, black shadows, orphan tubes | Padding in the coupon's own dye family (chroma x0.78, L 88 % of the dye), strands taper at the growing tip and settle to full height as they are pulled tight, R25 shadow lift 0.22 -> 0.45. The orphan capsules were the pad rows starting far from the wave (+-3 frame jitter): hex starts are now gated by the smooth ring. |
| Sea frontier is a bitmap-threshold staircase | Sea stitches are timed by a smooth low-frequency arrival (`arrival_sea`), +-1 frame per row, and grow along their length at ~6.5 mm per frame: a comb of tapered tips (see `stitch_on_detail_1to1.jpg` and the 3x crop discussed below). |
| Light pops (left candle +8 luma at f1665-1666, right +9 at f1707-1708), hard-edged diagonal pool, milky floor (corners RGB 14,14,17) | Ignition ramps of 5.5 / 5.0 frames with 17 % / 14 % flare and a settle, and the pool BLOOMS from the flame (radii x0.55 -> 1.0); everything on ones. Pools are ovals (Ru/Rv 6.0/4.3 and 5.2/4.1, exponent 1.25) centred round Grandbois. Fill floor 0.012, grade pedestal #020203 and lift x0.4: frame corners sit at luma 5 with the weave faintly readable (p1 = 5.0 to 5.8 throughout the 2D phase and the crane). |
| No true highlights; median luma falls to 36 in f1696-1719; the gold glint is not perceptible | Exposure 0.29 -> 0.38, key 4.0 / 3.5, white point only the Act V gain: max luma 239 (v2 225), the median never falls below 52 from f1668 on (v2: 36). Gold glint redesigned (below). |
| Linen is a mechanical dot grid | Hand-spun tabby: thread centres off-cell (+-0.17 cell) with slow wander, wider width and slub variation, stronger fibre streaks, weave height x0.80 (v2 x0.62), paler flax `#D9CEB4`. |
| Footprints read as torn paper | Footprint outline smoothed (close + 0.3 mm gaussian threshold), padding eases down into it over 1.8 mm (no cliff), an orderly row of 0.3 mm needle holes every ~2 mm along the old outline (5.1k holes), snipped thread ends (2.3k, proud, 1.3-3.4 mm), linen toned x0.58 plus 28 % of the hex dye, faint underdrawing. |
| Mixed frame rates (pieces and 2D phase on twos) | Everything is on ones: 56 R25 states, 58 Eevee frames, hold included. |
| Dead hold f1711-1727 | The wave ring now reaches radius 12.4 at f1711 (v2 f1704), the east is delayed, and the couched gold borders are a second pass stitched f1695-1718: changed pixels per frame stay at 0.2 to 1.4 % through f1718, with the right candle blooming from f1706 to f1712. f1720-1725 is the registered swap on the static board (storyboard: "the board holds still") and is the only still span; the first lift is now ON the f1726 bass (Grandbois starts at 64 deg and is at 30 deg by f1730; v2 started at f1728 and 78 deg). |
| Nothing on the f1755 swell / f1760 peak | Peeling continues to f1751 (banner last), tether snaps f1756-1760, the heal sweep from f1762; the pools swell +0.30 EV and widen 11 % to the f1760 crest, with a +4 % accent on f1755; the Grandbois banner is now tall (scale 0.95, v2 0.62) and unfurls (x scale 0.30 -> 1.0) as it stands up, and flutters in the hold; the gold glint band reaches the east at f1756-1760. Frame change is 25 % of pixels per frame through f1755 and falls to 0.4 % by f1764. |
| Material pop at first lift (f1727 -> f1728) | Per-piece fade: the model fades in over 3 frames as the stitched icon on the ground fades into the footprint (`FRAME` reveal softened to a 3-frame ramp). The strip f1725-1732 (see below) shows icon -> model without a replacement frame. Not a full projection of the R25 radiance onto the model's front faces (see known gaps). |
| Hold (f1767-1782) is a frozen board | Hold on ones with the S24 light-state blend (pools broaden x1.3, a floor of 0.07, the fill rises and turns neutral-warm), candle flicker, figure breathing, tree stir, banner flutter. Frame change 0.12 to 0.24 % of pixels, mean abs 0.8 to 2.0 (grain 0.5). |
| Icon repetition in 3D and on fields | Farms are 4-8 narrow crop strips / two-direction wedges / blocks with olive and wheat rows (v2: 3-4 lime plates), hills have six mound shapes, forests 5-17 trees in 1-4 clusters with species per cluster, 45 % of the forests have no hut/woodpile, huts scale 1.8-2.5 (v2 2.1-2.5). |
| Tethers nearly invisible in dark forests | Lighter (36 % dye / 64 % linen) and thicker (radius 0.0115). They are still short, thin threads: at film scale they read best on towns and on the plains, and are small on the forest hexes. |

Rejected or only partly done, with the reason:

- **Village and banner standing on the Grandbois hex from f1664 (P6, story anchor).** Not built. In the storyboard they are the E3 pieces layer of S20/S21 (rendered at 1080p over a plate, banner sway continuing to f1719) and belong to those shots; the PoC brief starts at the stitch-on and registers to f1663 only at the cloth level. Doing it here would mean 56 more Eevee frames with a pieces layer composited under the R25 wave, plus a hand-off to the rising 3D town. Left as a clean next step (the village OBJs and the Grandbois footprint are already registered).
- **Plate albedo projection of the 2x menu plate from f1756 and a full convergence to the menu (P3).** Only the light-state half is done (C -> D blend from f1767, 44 % of the way at f1782, as the storyboard's dissolve proper runs f1772-1798). The f1782 gate is therefore not "nearer the menu in every class": see the numbers below. Projecting the plate would turn the board into the game's own render and is the job of the S25 convergence dissolve, which is outside f1664-1782.
- **Projecting the R25 radiance onto the model faces during the hinge (P5).** Replaced by the 3-frame crossfade; a projection needs per-face UVs that the game OBJs do not have.
- **Matching Grandbois' height to the menu castle.** The model is the game's own `settle_3` OBJ at the layout scale 1.18; the menu's taller read comes from its camera and shields. Only the roof colour (blue slate spires) and the banner were matched.
- **"Make the pools circular".** They are ovals 1.4:1 by design: a 21 degree raking source stretches its spot along its azimuth; round pools would read as a top-lit gobo.


## Measured numbers (from `qa.json`, `data/palette_report*.json`, `data/glint_measure_v3.json`)

Palette gate (median dE_ok x 100 per terrain class, f1782 camera, neutral light, neutral grade, vs the menu; target < 4):

| class | forest | plains | farm | hills | quarry | sea | lake |
|---|---|---|---|---|---|---|---|
| class median | 2.86 | 3.23 | 0.68 | 3.27 | 3.16 | 1.66 | 2.94 |
| per-hex median | 4.64 | 5.81 | 3.68 | 4.40 | 3.16 | 2.15 | 4.25 |
| hexes | 15 | 7 | 9 | 4 | 1 | 36 | 2 |

The neutral grade needs an exposure to equalise the flat-light level; the gate uses 0.14 because the v3 pool peak is brighter (key 4.0); the film's exposure is 0.38 with the candle pools. The v2 plains per-hex median (12.5) is now 5.8.
As shown (candle falloff, Act V grade, light state 44 % toward D) the class medians at f1782 are farm 10.8, forest 11.5, hills 1.4, lake 26.5, plains 18.6, quarry 13.9, sea 1.4 (mean 12.0; v2 shown: 7.7, 5.4, 20.5, 33.0, 39.6, 1.6, 20.7, mean 18.9), i.e. closer in aggregate; the dark west (lake, plains) is still far below the menu's level because the left pool has not yet been released.

Swap: median dE_ok x100 0.99 per pixel (0.28 after a 2 px low-pass, p95 1.21), global shift 0.11 px. The swap dissolve also re-imposes the true candle flicker of each frame.

Crane (unchanged from v2): lands at f1766; 77 % done at f1750, 92 % at f1755, 98.7 % at f1760; peak speed 1.14 deg per frame at f1743.

Pieces (229 rising: 5 towns f1726 / 1733 / 1740 / 1746 / 1750, banner 1751, 21 cards f1730-1749, 2 quarries f1729, 10 lumber camps f1731-1749, 190 trees f1730-1751): 758 tethers, at least 6 frames of tether before the first snap on every piece (the first v3 pass had 4 on trees; fixed by `tether_snap_frames`, f1729-1768 re-rendered), last snap f1760, settled by f1763, footprints open 12 frames before healing.

Light: left candle gain 0.015 / 0.162 / 0.407 / 0.675 / 0.923 / 1.087 / 1.146 on f1663 to f1669 (flare to 1.16, settles by f1676); right 0.068 / 0.298 / 0.594 / 0.875 / 1.055 / 1.114 on f1707 to f1712. Whole-frame mean-luma steps: left ignition +22.8 / +25.6 / +22.0 / +11.6 per frame over f1665-1668 (a smooth S-curve from black over 5 frames; a fast flare, not a one-frame pop), right ignition +4.5 / +6.6 / +6.0 / +3.1 over f1708-1711 (v2: +9 in one frame). Flicker 3.96 % peak to peak, swell +0.30 EV at f1760.

Luma (post grade, 640x360 stats): p1 5.0 to 5.8 in the 2D phase and the crane (v2 12); corners 5 to 7 on three sides (the lit side of the left pool reaches 36); median 52 or more from f1668 to f1760 (v2 36); max 239.

Gold glint: ground-only renders with and without the glint: the luma gain is +125 to +199 on 2.5k-12k px (720p) in f1740-1760, centroid x travels 105 -> 415 -> 500 -> 618 -> 793 -> 915 px (west -> east) over f1736 to f1756, fades by f1764; peak luma stays 233-239 (no bloom, no flare).

Grandbois floor (mean luma of a fixed window, f1730-1744): median step 0.56, largest 10.4 (the town folding from front elevation to plan view, crossfaded over 3 frames; v2 16.7).

Voids: 0 to 12 near-black pixels (max channel < 4) per sampled frame, all in the darkest frame corners.

## Budget and cost (measured, 4 cores shared with another workflow)

- **Eevee 2560x1440, 16 TAA.** 58 frames (f1725, f1726-1782) per full pass, 36 to 100 s each (about 42 s on average once the box is quiet), 40 to 67 min per pass. Three full passes were made (first full set, material/stripe fix, glint + tether fix) plus a fourth partial pass of f1729-1768 (40 frames, 28 min) for the 6-frame tether minimum; the final frames are pass 3 for f1725-1728 and f1769-1782 and pass 4 for f1729-1768. Border renders (`--border`) at 1:1 and 720p tests were used for look-dev.
- **R25.** Bake about 2 min, finalize about 3.5 min, cards 15 s, 56 unique 2D states at 2560x1440 about 10 min.
- **COMP.** About 1.5 s per frame. **Encode.** x264 slow CRF 14. Disk: about 4.3 GB for the poc directory including v1/v2 archives.

## Iterations (every one judged on renders: stills, 1:1 crops, contact sheets, frames decoded from the mp4)

1. Light first: pool shape, floor and ignition were tuned numerically on a flat-linen preview (`src/lookdev/pool4.py`) until the corners fell to luma 5 and the pools kept 160 to 180 at the peak.
2. 2D phase: the first R25 test showed a long dead tail and a staircase sea; the ring schedule, the sea timing and the borders-as-last-pass were adjusted with a schedule-only analysis (`sched_only.py`).
3. 3D pieces: a material-ID render (`MATDEBUG=1`) found the roof classes; the felt palette and the blue slate spires were set from it. Speckle on the first felt renders was isolated by switching off, in turn, the shadow, bump, GTAO, soft shadows, outline hull and fibre shell on a 1:1 border render; the cause was the fibre-shell shell receiving the shadow of the mesh it clothes plus an aliased 512 px wool tile (now 128 px) and missing texture filtering in background mode. The fibre shell now only clothes trees; the buildings use bevels and the brown hull.
4. Figure cards: v2's cut-from-board cards had neighbours' strands in them; `cards_bake.py` makes each card on its own canvas.
5. Glint: v3 pass 2 had the glint everywhere at a 14 % floor; the band is now exp(-(d/2.3)^2) with a 3 % floor and sweeps west to east (measured).
6. Tethers: lightened and thickened after the dark-forest frames.

## Known gaps and choices (honest list)

- No village or banner at Grandbois before the lift, no desk chrome, valance or leaf, no shield markers or nameplates, no plate-albedo blend into the menu (see "Rejected").
- The model faces are felt-material wool, not a projection of the stitched elevation: the crossfade hides it but a frame-by-frame look at f1726-1728 shows the icon and the model overlapping with a faint ghost.
- Satin sheen on the ground is baked at face-on; only the gold glint is view dependent. Trees are felt cones with a fibre shell, no per-needle detail; cards have thickness 0.6 mm but are still billboards (no front-to-back shape).
- The Grandbois town and the five towns show the wool stripe on their courtyard roofs at 2x (the strand relief is at 65 % contrast); at 1:1 it reads as thatch, at 2x slightly like a barcode on the side towns.
- The left ignition steps +22 to +26 mean luma per frame for four frames. That is a fast but continuous bloom from black; if the director wants it slower, `CANDLE['L']['rise']` in `lightmodel.py` is the one number to change (the R25 states re-render in 10 min, nothing in Eevee depends on it before f1725).
- The hold is alive (flicker, light-state blend, idle sway) but visually calm: 0.12 to 0.24 % of pixels change per frame.
- The palette gate passes under neutral light with an exposure fitted on lightness (0.14); as shown the board is darker and warmer by design and the dark west corner is still far from the menu.
- The mp4 was checked by ffprobe, by decoding frames and comparing them to the masters, and by audio cross-correlation; I looked at stills, strips and 1:1 crops, not at the film played at speed, so judder or flicker at full motion is not verified by eye (frame-to-frame change is smooth in `qa.json`).
- Background-mode Blender has no texture filtering by default; `bl_scene.py` sets mipmaps and 16x anisotropy in the preferences. Other rigs should keep that.

## How it is built (v3 changes in bold; every script is in `src/`, everything is deterministic and frame-based)

1. **Light model** (`lightmodel.py`, the single source of truth for R25, Eevee and COMP). Two candle point sources with an oval lobe each and inverse-square falloff.
   **v3: round-ish pools (Ru/Rv 6.0/4.3 and 5.2/4.1 units, exponent 1.25) instead of the v2 diagonal gobo band, key 4.0 / 3.5, fill floor 0.012 (true near-black edges),
   an ignition ramp (5.5 / 5.0 frames, smoothstep + 17 % / 14 % flare that settles over ~8 frames) whose pool BLOOMS outward from the flame (radii 0.55 -> 1.0), two bass accents
   (+5 % on f1726, +4 % on f1755), the swell crest on f1760 (+0.30 EV, pools +11 %), and the S24 light-state blend C -> D (pools broaden, fill rises and turns neutral-warm) from f1767.**
2. **Grade** (`r25render.grade`): ACES fit at **exposure 0.38 (v2 0.29)**, Act V lift at **0.4 strength and a #020203 pedestal (v2 stacked a #07070A pedestal: flat 14,14,17 corners)**, gain #FFF2DC as the only white point (**highlights reach luma ~243**), grain 0.011.
3. **Board bake** (`board_bake.py`, `bakelib.py`, `icons2.py`, `linen2.py`, R25 `emb/` unchanged; 6 px/mm).
   **Linen: hand-spun (thread centres off-cell, thread width and slubs vary, paler flax #D9CEB4). Icons: farms are 4-8 narrow crop strips / two-direction wedges / blocks with olive and wheat rows running along each strip; hills have six mound shapes; forests have 1-4 clusters of 5-17 trees with spruce/fir/broadleaf per cluster; 45 % of the forests have no hut. Footprints: smooth clean outline, padding eases down into it over 1.8 mm (pressed padding, no cliff), an orderly row of 0.3 mm needle holes every ~2 mm, thread tufts, linen toned toward the hex dye. Padding felt in the coupon's own dye family (the first strands read as wool, not grey capsules).**
4. **Replay** (`replay.py`, `finalize.py`): needle-path schedule from Grandbois. **The ring reaches radius 12.4 at f1711 (v2 f1704); the east is delayed 4 frames so it is still being stitched when the right candle ignites; the sea is stitched in horizontal rows that grow along their length with a smooth front and +-1 frame per row (a comb of tapered tips, not a dissolve of 13 mm dashes); strands taper at the growing tip and settle to full height as they are pulled tight; the couched gold borders are a second, slower pass that finishes the film's stitching (f1695-1718); R25 shadows are lifted to 0.45 (the v2 first stitches had hard black cast shadows).**
5. **2D frames on ones** (`r25_frames.py`): 56 states, each relit per candle with that frame's gain and pool radii.
6. **Eevee scene** (`bl_scene.py`, `prep_eevee.py`, `anim.py`, `cards_bake.py`). Ground = the R25 radiance times (Eevee lit / flat reference lit), coloured-sun trick for the two candles, pieces and tethers as before. **v3: all pieces on ones;
   felt material (laid-wool strand relief with strand shade, groove AO, dye-lot patches, per-object lot, dusty-madder roofs, oatmeal walls, blue slate spires on Grandbois), fibre-halo shell on the organic pieces (hashed alpha, gated to grazing angles), irregular tiered spruces with tilted off-centre tiers and scalloped skirts, lumpy broadleaf thickets, appliqued felt figure cards (0.6 mm thick extruded outline, felt edge, cloth back, alpha cut-out holes) re-embroidered on their own canvas at 2.4x stitch density, per-piece fade so the stitched icon crossfades into the model over 3 frames, a contact-occlusion map under every risen piece, idle motion in the hold (cards breathe, trees stir, the banner flutters), the gold glint redesigned (below).**
7. **COMP** (`comp.py`): R25 frames, swap dissolve, homography camera blur, one grade for both renderers, grain; the hold is rendered on ones.
8. **Encode and QA** (`encode.sh`, `qa.py`, `deliverables.py`).

## Re-render

```sh
cd src
./run_chain_v3.sh               # pieces plan + bake (~2 min) + finalize (~3.5 min) + cards (~15 s) + eevee inputs
python3 r25_frames.py           # 56 unique 2D states at 2560x1440 (about 10 min on the shared box)
./run_final.sh                  # Eevee 2560x1440 16 TAA (f1725, f1726-1782 = 58 frames, ~60 s each), COMP, encode, QA
./run_preview.sh                # 720p preview of the whole move (R25 at half scale, Eevee 1280x720 6 TAA, COMP, QA)
python3 deliverables.py         # keyframe, contact sheet, before/after, A/B swap, f1782 vs menu, 1:1 detail sheets
CHRON_NEUTRAL=1 python3 palcheck_full.py ev_neutral/f1782.exr 0.14      # palette gate (neutral light, neutral grade)
```

Notes: Blender needs `PYTHONPATH=aaa/tools/py312` (numpy and cv2 for Python 3.12); run it under `xvfb-run -a -s "-screen 0 1920x1080x24" blender -b`.
`bl_scene.py` look-dev switches: `--border x0 y0 x1 y1` (render a crop of the film frame at full scale), `--closeup x z dist`, `--nofuzz`, `--nopieces`, `--noglint`, `MATDEBUG=1` (one flat colour per material name), `WDBG=alb|lit`.
