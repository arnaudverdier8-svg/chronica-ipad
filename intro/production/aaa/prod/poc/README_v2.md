# CHRONICA intro, proof of concept v2: "The cloth becomes the board" (f1664-1782)

3.97 s (119 frames, 30 fps, 2560x1440) of storyboard shots S22 (end) to S24, muxed with the matching slice of
`aaa/audio/audio_master_1984f_s16.wav` (samples 1664*1470 to 1783*1470).

This is the rework of the v1 proof after the art-director notes (muted menu palette, candle light, needle stitch-on, varied icons, felt 3D pieces,
protected-linen footprints, crane timing, couched-gold glint). The v1 files are kept next to it with a `_v1` suffix
(`poc_cloth_to_board_2560x1440_v1.mp4`, `src_v1/`, `v1_frames/`, `README_v1.md`, `*_v1.jpg`).
Scope is still only the board: no desk chrome, valance or leaf.

## Deliverables (this directory)

| file | what |
|---|---|
| `poc_cloth_to_board_2560x1440.mp4` | H.264 High, yuv420p, bt709 (tagged, tv range), x264 slow CRF 14, AAC 192k; frames f1664-1782 |
| `frames/f1664.png ... f1782.png` | the graded master frames, 2560x1440 sRGB |
| `keyframe_f1760_2560x1440.png` | storyboard keyframe 5 (climax peak), board only |
| `before_after_v1_vs_v2.jpg` | v1 and v2 side by side at the key moments (stitch-on, swap, crane, f1760, hold) |
| `contact_sheet.jpg` | f1664 to f1782 at a glance |
| `stitch_on_detail_1to1.jpg` | the needle-path stitch-on at 1:1 (underdrawing ahead of the wave, padding under the strands, frontier) |
| `ab_swap_f1719_vs_f1725.jpg` | R25 2D render vs the Eevee zero-tilt still at the swap, plus a difference image |
| `compare_f1782_vs_menu.jpg` | the final pose next to the live menu's first frame, same camera |
| `qa.json` | measured numbers (swap, crane landing, pieces, tethers, light, voids, floor) |
| `data/palette_report.json` | palette gate, class medians in OKLab vs the menu, neutral light, neutral grade |
| `data/palette_report_shown.json` | the same measure on the board as shown (candle falloff and Act V grade included) |
| `data/menu_palette.json` | per-terrain OKLab medians sampled from the live menu |
| `src/` | every script, plus `poc_scene.blend` (the Eevee scene as built for the last rendered frame) |
| `data/` | layout, piece plan, Eevee inputs (reveal / heal / pool maps, tether anchors, light table) |
| `ev/`, `r25/` | the raw Eevee EXR frames and the graded R25 2D frames that `comp.py` assembles (kept so a grade or comp change re-runs in minutes) |
| `maps/` | the R25 board map set and the stitch RECORD (needed to re-render; rebuilt by `run_bake_chain.sh`) |

## What happens, frame by frame

- **f1664-1719, 2D (R25-S), the board is stitched on.** Camera locked face-on over the menu camera's target. Everything is a function of the frame number.
  - f1664 is the bass hit. The left candle (3200 K) ignites on this frame and its pool is centred on Grandbois, raking from the left at about 21 degrees.
    The right candle ignites on f1707 ("age"), from the right. Light falls to near black at the edges by inverse square from the candle position, not by a vignette.
  - The wave starts at Grandbois and runs outward on a ragged ring: hex start frames follow distance plus azimuth ripples plus noise (+-3 to 5 frames).
    The sea floods continuously across the hex seams, so it never looks like per-hex pads.
  - Inside a hex the padding felt (low-chroma undyed wool) grows along its length just ahead of the satin and is pressed down as the satin arrives.
    The satin rows then sweep across the coupon perpendicular to the strands in alternating directions (boustrophedon, a needle path); each row grows along its own length
    and the frontier wobbles with low-frequency noise, so it is a soft irregular line and not a wipe. Plots, mounds, peaks, trees, huts and towns are stitched region by region;
    seams, coast, borders, rings, waves and the river are run sequentially by arclength. Couching squeezes land when their bar completes.
  - Ahead of the wave the linen is bare and shows the iron-gall underdrawing of hex edges, icon outlines and plots.
  - Unique states are on twos (stop-motion embroidery). The last tie-down lands at f1718.9.
- **f1720-1725, swap.** Linear-light cross-dissolve on the static board from the last R25 state to the Eevee zero-tilt still. Both renderers use the same light table, so the pools match by construction.
- **f1726-1766, 3D crane (Eevee legacy, Blender 4.0.2).** The camera cranes from pitch 90 to the game's menu camera (vertical fov 30, pitch 66.087, distance 20.9).
  - The crane eases out and lands exactly on f1766: 12 % done at f1735, 46 % at f1743, 77 % at f1750, 92 % at f1755, 98.7 % at f1760, 100 % at f1766. Peak speed is at f1743 (1.14 deg per frame).
  - 217 pieces peel up out of their elevation icons on twos, staggered outward from Grandbois: first at f1728 (Grandbois), last at f1750. Each piece hinges about its back-bottom edge like a pop-up book.
    Its footprint (protected unfaded linen, needle holes, snipped thread ends, faint underdrawing) stays visible behind it.
  - Each piece pulls a few plied threads from its needle holes. They are the thread the piece was stitched with (terrain dye lightened toward linen), wander, sag while slack and straighten as the piece lifts.
    They snap one by one (at least 6 frames of tether before the first snap, the last snap at f1760); the cloth end whips back and curls into its hole, the piece end swings away.
    730 tethers in all.
  - From f1760 the footprints heal: the coupon's satin closes over each footprint (sweep order), 13 frames after the piece started to lift.
  - The couched gold borders carry a narrow metallic glint (Kajiya-Kay lobe, orientation selective) that travels along them as the camera cranes. Level L1, no flare.
  - Candles swell by +0.28 EV into the f1760 peak (the pools themselves widen, not an exposure ramp) and relax to +0.13 EV by f1782.
  - Camera motion blur is done in COMP (ground-plane homographies, 9 samples, 180 degree shutter).
- **f1767-1782, hold on the menu camera.** Footprints heal, the swell settles; Eevee frames on twos.

## How it is built

All scripts are in `src/`. Everything is deterministic and frame-based.

1. **Light model** (`lightmodel.py`, pure numpy, the single source of truth for R25, Eevee and COMP).
   Two candles as point sources with an anisotropic lobe around the focal pool, inverse-square falloff, ignition (f1662.8 left, f1706.8 right), flicker (3 sines, 4 % peak to peak), the f1744-1760 swell, a cool navy fill at key:fill about 4:1.
2. **Palette** (`pal2.py`, `sample_menu.py`, `palcheck.py`). Dyes were tuned in OKLab against per-terrain medians sampled from the menu at the f1782 camera. No lime, no candy orange.
3. **Board bake** (`board_bake.py`, `bakelib.py`, `icons2.py`, `linen2.py`; the R25 `emb/` code unchanged; 6 px/mm, 1 unit = 27.5 mm; about 103k recorded stitch events, about 100 s).
   Tabby linen with foxing and underdrawing, padded satin coupons per hex with dye lots, laid denim sea, couched gold borders, plots with laid and couched rows. Icons follow the in-game idiom and are varied per hex:
   forests of 2-4 clusters of 5-12 conifers / broadleaf trees (never the same cluster twice), a hut and woodpile slot and a dashed inner ring; fields of 2-3 by 1-2 crop plots with rows along or across, a pole and a stook; 3-6 lumpy two-band hill mounds; 4-8 peaks per mountain hex; sparse tufts on plains; hand-placed sea wave marks (blue-noise darts, denser toward coasts, three mark types, irregular size and tilt). Every random draw is a hash of (hex, role), so a re-bake reproduces the board.
   Every stitch carries a tag (kind, key, order, group) for the replay.
4. **Replay and finalize** (`replay.py`, `finalize.py`, `pieces_plan.py`). The needle-path schedule maps each event to (start, end, reversed) frames. `finalize.py` replays the whole record once and produces
   the final stitched state A, the lifted footprint state B (linen, needle holes, thread tufts), the healed state C, the low-pass mesh height (3 mm blur), the heal sweep map and the gold mask.
   `pieces_plan.py` picks the 217 pieces the crane can see (171 trees, 21 figure cards, 17 lumber camps, 5 towns, 2 quarry/camp sites, 1 banner) and their foreshortened elevation icons.
5. **2D frames** (`r25_frames.py`, `r25render.py`, `shade2.py`). Each unique state is relit per candle in texture space (brdf pass per candle plus fill), fibres only where their strand exists, warped to 2560x1440 and graded.
6. **Eevee scene** (`bl_scene.py`, `prep_eevee.py`, `anim.py`, `common.py`). The ground emission is the R25 radiance texture times (Eevee lit / flat reference lit), so at zero tilt the ratio is 1.
   The light uses a coloured-sun trick: left sun pure red, right sun pure green, world fill blue, so one Shader-to-RGB of a white diffuse separates the three contributions.
   Every material multiplies each by its candle's pool map, colour and gain (ignition, flicker, swell). The pieces use a felt/stitch material (triplanar laid-wool normal, per-strand shade, dye lots, fuzz rim, game palette) with
   bevelled edges and a brown outline; trees are tiered felt cones; figure cards are re-embroidered (couched outline, satin and split fill, no cream border). Tethers are two plied strands as curves.
7. **COMP** (`comp.py`). R25 frames, swap dissolve, homography camera blur, one grade for both renderers (ACES fit, Act V lift #05070C, gain #FFF2DC, shadow tint #1A1620, clamps, grain 0.011).
8. **Encode and QA** (`encode.sh`, `qa.py`, `deliverables.py`).

## Re-render

```sh
cd src
./run_bake_chain.sh            # pieces plan + board bake (~100 s) + finalize (~3 min); needs numba threads, set inside
python3 prep_eevee.py          # reveal / heal / pool-map / light / tether inputs for Eevee
NUMBA_NUM_THREADS=2 python3 r25_frames.py     # 28 unique 2D states at 2560x1440 (about 7 min on the shared box)
./run_final.sh                 # Eevee 2560x1440 16 TAA (50 frames), COMP, encode, QA
                               #   (FRAMES=1728-1766 ./run_final.sh re-renders a sub-range, then comp/encode/qa)
python3 deliverables.py        # keyframe, contact sheet, before/after, A/B, comparison with the menu
```

Notes:
- Blender needs `PYTHONPATH=aaa/tools/py312` (numpy for Python 3.12); `run_final.sh` sets it inline. Do not export it: it breaks the system python3.
- Run Blender under `xvfb-run -a -s "-screen 0 1920x1080x24" blender -b`.
- `CHRON_NEUTRAL=1` switches the light model to white light and flat pools (the palette gate); `CHRON_EXPO` overrides the grade exposure (default 0.29).
- `src/poc_scene.blend` holds the board, lights, camera and pieces as built; pieces, tethers and the ground swell are posed per frame by `bl_scene.py`, so the .blend alone does not animate them.
- `bl_scene_pre_tether.py` is the scene script before the tether polish (thread colour/plied strands), kept for reference.

## Measured numbers (from `qa.json` and `data/palette_report*.json`)

Palette gate (median dE_ok x 100 per terrain class, f1782 camera, neutral light and neutral grade, vs the menu; target < 4):

| class | forest | plains | farm | hills | mountain* | quarry | sea | lake |
|---|---|---|---|---|---|---|---|---|
| dE_ok x100 | 2.77 | 3.33 | 2.80 | 1.03 | n/a | 3.08 | 1.42 | 1.95 |
| hexes | 15 | 7 | 9 | 4 | 0 | 1 | 36 | 2 |

\* no mountain hex is inside the visible window. Per-hex medians are 1.9 to 4.0 for every class except plains (12.5); the cause (a layout difference on some plains hexes, or per-hex dye-lot variation of the menu) was not isolated.
The board as shown (candle falloff plus the warm Act V grade) is intentionally not equal to the menu: class medians in `data/palette_report_shown.json`.

Swap: median dE_ok x100 0.44 per pixel (0.14 after a 2 px low-pass, p95 0.94), global shift 0.12 px; the light state of both renderers is within 1.5 % of gain 1.0 on both candles at f1718 and f1725.

Crane: lands at f1766 (see the table above). Velocity per frame: 0.25 (f1730), 0.66 (f1734), 0.99 (f1738), 1.14 (f1742), 1.10 (f1746), 0.90 (f1750), 0.59 (f1754), 0.29 (f1758), 0.07 (f1762), 0.00 (f1766).

Pieces: first rise f1728, last rise f1750, last tether snap f1760, settled f1762, footprint open 13 frames before it heals, 6 or more tether frames before the first snap. Rise starts per twos frame: 1, 3, 23, 20, 22, 28, 17, 26, 27, 20, 24, 6 from f1728 to f1750.

Light: left candle gain 0.59, 0.81, 0.90, 0.94 on f1664 to f1667; right candle 0.00, 0.14, 0.59, 0.81, 0.90 on f1706 to f1710; flicker 3.96 % peak to peak; swell 0.09 EV (f1750), 0.22 (f1755), 0.28 (f1760), 0.25 (f1766), 0.13 (f1782).

Voids: 0 void pixels in the 17 sampled frames.

Grandbois floor (mean luma of a fixed window, f1730-1744, in `qa.json`): median frame-to-frame step 0.64; the largest step (16.7, between f1735 and f1736) is the town folding from its front elevation (bright white walls) into plan view (roof tops), not the v1 floor pop: the 1:1 crops of f1732-1744 show the courtyard floor present and continuous in every frame.

## Budget and cost (measured, 4 cores shared with another workflow)

- **Eevee 2560x1440, 16 TAA.** Final pass: 50 frames, 42 to 97 s each, about 59 s on average, about 49 min. A second pass of f1728-1766 (39 frames, about 38 min) re-rendered the tethers after the look was fixed.
  Previews: 720p and 1440p tests at 8 TAA, about 25 s per 1440p frame.
- **R25.** Bake about 100 s (about 103k events); finalize about 3 min (A, B, C radiance, fibres, height, sweep, metal); 28 unique 2D states, about 7 min in total.
- **COMP.** About 1.5 s per frame including the 9-sample homography blur. **Encode.** x264 slow CRF 14.

## Iterations (every one judged on renders: stills, 1:1 crops, contact sheets, frames decoded from the mp4)

1. Palette: first dyes were too saturated and bright; re-dyed in OKLab against the menu medians, exposure and pool normalisation fixed until every class was under 3.4.
2. Light: pools were too wide and the edges did not go near black; Ru/Rv tightened (corner relative luminance 0.02 to 0.09), ignition and flicker added.
3. Stitch-on: the sea flood showed confetti pads; replaced by a low-frequency noise frontier with row jitter and 1.8 to 3.6 frame growth. Padding rows now press under the satin.
4. 3D pieces: diamond banding on satin came from strand-scale relief in the mesh plus board self-shadowing; mesh height blur raised to 3 mm and board shadow-casting turned off.
5. Floor pop at f1736-1737 (v1 bug): the -7 degree overshoot buried the Grandbois courtyard under the cloth. Towns now overshoot only -1.5 degree, the pivot lifts with the overshoot, and the plateau is static.
6. Tethers: v1-style straight pale rods read as props holding the town up. Now two plied threads in the terrain dye lightened toward linen, with lazy wander and sag, thinner, and longer whipping ends when they snap.
7. Metal: the couched gold got a narrow orientation-selective glint instead of a flare.

## Known gaps and choices (honest list)

- No desk chrome, valance or leaf (outside the scope given). No shield markers above unit groups, no nameplates, no S24 blend into the menu plate.
- Village and banner at Grandbois from f1664 (story continuity) are not built; Grandbois appears with the stitch-on wave and rises at f1728.
- Satin sheen is baked at face-on. Only the gold glint is view dependent; under the crane the satin sheen does not re-orient.
- Trees' footprints are satin (they were small appliqued trees), not bare linen; the other footprints are linen, toned x0.88.
- Figure cards are stitched billboards with bump, no thickness.
- The 2D phase and the pieces are on twos (as allowed); the camera is on ones.
- Tethers are modest in legibility on dark forest hexes (the thread is in the terrain colour); they read best against plains and in front of the towns.
- Palette gate is measured under neutral light; the film as shown is darker and warmer by design, so the as-shown f1782 differs from the menu. Plains per-hex median 12.5 (see above).
- The glint's view vector is Eevee's Geometry `Incoming`; a one-plane test render (camera at (0,-5,5), plane at the origin) confirmed it points from the surface toward the camera, as the glint code assumes. Only the narrow lobe's strength (amp 0.80, exponent 150) is an art choice that was judged on frames, not measured against a reference.
- The pop-up elevation icons mean towns and trees are stitched as front elevations lying flat, not plan icons; that is what keeps the footprint visible behind the risen piece.
- Camera blur is homography-only; parallax of tall pieces is not blurred separately.
