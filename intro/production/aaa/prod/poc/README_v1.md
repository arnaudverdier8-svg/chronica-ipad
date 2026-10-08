# CHRONICA intro: proof of concept "The cloth becomes the board" (f1664-1782)

3.97 s (119 frames, 30 fps, 2560x1440) of storyboard shots S22 (end) to S24, muxed with the matching slice of
`aaa/audio/audio_master_1984f_s16.wav` (samples 1664*1470 to 1783*1470).

Scope was narrowed by the director: no desk chrome, valance, leaf or aspect buckets. Only the board.

## Deliverables (this directory)

| file | what |
|---|---|
| `poc_cloth_to_board_2560x1440.mp4` | H.264 High, yuv420p, bt709 (tagged, tv range), CRF 14, AAC 192k; frames f1664-1782 |
| `frames/f1664.png ... f1782.png` | the graded master frames, 2560x1440 sRGB |
| `keyframe_f1760_2560x1440.png` | storyboard keyframe 5 (climax peak), PoC version (board only) |
| `contact_sheet.jpg` | f1664 to f1782 at a glance |
| `ab_swap_f1719_vs_f1725.jpg` | the R25 2D render vs the Eevee zero-tilt still at the swap, plus a difference image |
| `compare_f1782_vs_menu.jpg` | the final pose next to the live menu's first frame (same camera) |
| `qa.json` | measured acceptance numbers (swap, crane landing, tethers, footprints, voids) |
| `src/` | every script, plus `poc_scene.blend` (the Eevee scene as built for the last rendered frame) |
| `data/` | the recovered layout, piece plan, demo-mode plates, and Eevee inputs |
| `maps/` | the R25 board MapSet and the stitch RECORD (needed to re-render; it can be rebuilt by `run_prep_chain.sh`) |

## What happens, frame by frame

- **f1664-1719, 2D (R25-S).** The camera is locked face-on at pitch 90 over the menu camera's target.
  - The board embroiders itself as a wavefront from Grandbois. Hex start frames follow the hex's distance from Grandbois; each hex takes 13 frames. The last tie-down lands at f1718.9, so the last hex closes on f1719.
  - In each hex the padding felt goes down first. Then the satin strands sweep across the coupon, each strand growing along its own length (partial capsule chains). The crop plots, mounds and peaks, wave marks, seams and coast outline follow. The couched gold realm borders go last, then the icons.
  - Ahead of the wave the linen is bare, showing the iron-gall underdrawing of every hex edge, icon outline, crop plot and the river.
  - Unique states are on twos (stop-motion embroidery). No needle sprites.
- **f1720-1725, swap.** A linear-light cross-dissolve on the static board from the R25 render of the final state to the Eevee zero-tilt still.
  - The Eevee ground's emission *is* the R25 radiance texture of that same state. On a flat mesh at pitch 90, Eevee reproduces the R25 frame by construction.
  - Measured (`qa.json`): median dE_ok x100 = 0.66 per pixel and 0.14 after a 2 px low-pass; global shift 0.08 px. The gate is dE < 2 and shift < 1 px.
- **f1726-1766, 3D (Eevee legacy, Blender 4.0.2).** The camera cranes about the menu target from pitch 90 to the game's menu camera: vertical fov 30, pitch 66.087, distance 20.9, focus Grandbois + (-2.2, 0, 0.5), all decoded from `view/camera_rig.gd` and `view/main.gd`. It is 0.008 deg from the menu pose at f1760 and exact at f1766.
  - The camera moves on ones. Every piece moves on twos.
  - The board's baked relief grows in, and each land coupon swells about 1.1 mm as a padded coupon, outward from Grandbois, on twos.
  - **Pieces** (89 in all: 5 towns, 2 quarries, lumber camps, pines, 21 figure cards) peel up out of their stitched icons. They are staggered outward from Grandbois, the first at f1728 and the last at f1748, and all are settled by f1760.
  - **How a piece peels up.** It is a pop-up: each icon is a Bayeux-style *elevation* of the game's own model, lying flat with its top toward the far side. It hinges up about its back ground line while its depth unfolds. It overshoots 7 deg, then settles. Figure cards stand to 62 deg from the cloth.
  - **Footprint.** On the frame a piece starts to rise, the ground under its icon switches to the "lifted" state: the coupon's padding felt with the icon's underdrawing and the needle holes of its couching. That footprint stays visible behind the piece until the end (at least 34 frames).
  - **Tethers.** Each piece pulls 3 to 11 wool tethers from its needle holes to its outline. They snap one by one between 6 and 10 frames into the rise, then the loose ends curl and the stubs swing.
  - **Shadows.** Contact shadows and soft sun shadows come from Eevee. They reach the R25 radiance on the ground through a lighting ratio (below).
  - **Motion blur.** Camera-only, 180 deg, applied in COMP by ground-plane homographies to the sub-frame camera poses.
- **f1767-1782.** Hold on the menu camera. The light swell of the climax (+0.25 EV into f1760, storyboard S24) settles back.

## How it is built

1. **Layout of the menu world (seed 4242).** `capture_plates.mjs` grabbed UI-free demo-mode plates of the live game (`index.html?args=demo,reveal,seed=4242,size=small,play=16,zoom=11|30,phase=day,hideunits`).
   - `rectify2.py` / `gamecam.py` back-project them through the decoded camera rig onto the ground plane (y = 0.25 for land tiles). The hex grid (`core/hex.gd`, pointy-top, size 1) then registers to the plates within a few pixels.
   - `layout_build.py` holds the hand-checked terrain of every hex from q -10..8, r -6..2, plus realm ownership, settlements and unit groups. Sablon (-6,-1), Grandbois (0,0) and Hautecouronne (2,1) match the menu's first frame. Vaugrise (-2,-2) and Brumecourt (-4,1), which sit under the menu card, come from the demo plates. The sea fills the right third.
   - The menu world differs slightly from the demo world in development state. Exact pixel registration was not a goal of this proof.
2. **Pieces** (`pieces_plan.py`). Towns use the decoded OBJs `settle_3` (Grandbois, with `settle_banner`), `settle_1_1`, `settle_2`, `settle_1` and `settle_1_2`. The rest are `quarry`, `lumber`, procedural pines, and figure cards from `assets/tex_tinted` (engineers and spearmen in the realm colours).
   - Their icons are front elevations rendered from the OBJs as material-ID images (`bl_elevations.py`, workbench) and re-embroidered by R25.
3. **R25 board bake** (`board_bake.py`, the R25 `emb/` code unchanged, 6 px/mm, 1 game unit = 27.5 mm).
   - The base is linen tabby with light foxing and the iron-gall underdrawing.
   - Land hexes are padded satin coupons, using split satin in silk with dye lots and a per-hex direction of 30/90/150 deg.
   - The sea and lakes are laid denim wool, couched, with cream stem-stitch wave marks and a pale-blue running-stitch hex grid.
   - Hex seams are cream running stitch. The coast is outlined in brown stem stitch. Realm borders are couched gold pairs, with tie-downs in the realm colour.
   - The river is a couched cord. Crop plots are laid and couched. Hill mounds and mountain peaks are stitched icons. The game-model elevations are laid wool with stem outlines. Figure slips are the game's own embroidered card art, appliqued and padded.
   - Every stitch is recorded with a tag (hex, kind) for replay.
4. **Wavefront replay** (`replay.py`, `finalize.py`, `r25_frames.py`). This produces the per-frame 2D states.
   - It also produces the final state A, plus the ghost state B (padding felt, underdrawing, needle holes under every icon).
   - It builds a global fibre set, where every fibre belongs to a strand and appears only once that strand exists.
   - Finally it renders the R25 linear radiance of A and B for the whole board (`maps/radA.exr`, `radB.exr`).
5. **Eevee scene** (`bl_scene.py`, Blender 4.0.2 legacy Eevee under xvfb, 2560x1440, 16 TAA).
   - **Board mesh.** 342k vertices at 1 per mm. The vertex z is the low-pass R25 height times a growth factor, plus the per-hex swell.
   - **Ground material.** The emission is `mix(radA, radB, frame > reveal(uv))`, multiplied by `mix(1, ShaderToRGB(Diffuse(white)) / REF, 0.85)`. REF is the flat-ground value, calibrated by `run_prep_chain.sh`. So the swollen domes, the piece shadows and the contact AO all come from Eevee, while the stitch micro-shading stays R25's.
   - **Pieces.** The game OBJs carry a stitch material port: the game palette (MILLEFLEURS merged over TAPISSERIE, from `view/palettes.gd`), a box-projected laid-wool bump, and the brown inverted-hull outline used by the game's pieces. They are lit by the same rig and multiplied by the same key pool.
   - **Light rig.** One rig is shared with R25 (`data/eevee/lights.json`): a 3200 K-ish key from the left-front at 24 deg elevation (raking on the cloth, three-quarter on the pieces), a cool fill at 1:4, a rim, and a soft key pool. All of it is graded once in COMP.
6. **COMP** (`comp.py`). Steps:
   - the R25 frames;
   - the linear dissolve at the swap;
   - the homography motion blur;
   - one shared grade for both renderers: ACES fit, the act V lift/gain, the bible's black/white clamps and shadow tint;
   - grain per frame;
   - the light swell.

## Re-render

```sh
cd src
./run_prep_chain.sh            # bake (~2 min) + replay/radiance (~2 min) + Eevee inputs + lighting calibration
NUMBA_NUM_THREADS=2 python3 r25_frames.py     # 28 unique 2D states at 2560x1440 (~6-9 s each)
./run_final.sh                 # Eevee 42 frames 2560x1440 16 TAA (48-100 s each on the shared box), COMP, encode, QA
                               #   (FRAMES=1728-1766 ./run_final.sh re-renders a sub-range)
python3 deliverables.py        # keyframe, contact sheet, A/B, comparison with the live menu
./run_all.sh preview           # whole chain at 1280x720 / 8 TAA for review (Eevee ~12-16 s per frame)
```

Environment notes:
- Blender needs `PYTHONPATH=aaa/tools/py312` (numpy for Python 3.12). The scripts set it.
- The game plates need the static server on 127.0.0.1:8765. The plates are already in `data/plates/`.
- Everything is a function of the global frame number: `anim.py` (hinge, swell, growth, tether snaps), `replay.py` (wavefront) and `common.camera_pose`. Re-running the scripts reproduces the frames.
- To view the scene, open `src/poc_scene.blend` in Blender 4.0.2. It holds the board, lights, camera keys and pieces as built. Pieces, tethers and the ground swell are posed per frame by `bl_scene.py`, so the .blend alone does not animate them.

## Budget and cost (measured)

- **Eevee at 2560x1440, 16 TAA.** 42 renders are in the film: the swap still f1725 and f1726-1766. The hold reuses f1766.
  - The final pass took 48-100 s per frame, about 60 s on average, on the 4 cores shared with other agents.
  - 1440p renders spent in total: 54. That is 42 kept, 11 discarded when the padding was made to press flat under towns, and 1 look-dev frame. The budget was about 60.
  - The 720p previews (8 TAA, two full passes of 42 frames) took 11-17 s per frame.
- **R25.**
  - Bake: about 100 s, about 84k stitches.
  - Wavefront replay, final states and radiance textures: about 100 s.
  - 2D frames: 28 unique states at 6-8 s each on 2 threads (about 4 min).
- **COMP.** About 1.5 s per frame at 1440p, including the 9-sample homography motion blur.
- **Encode.** x264 slow at CRF 14 gives a 19 MB file.

## Iterations (looked at every time: stills, crops at 1:1, contact sheets, frames decoded from the mp4)

1. **R25 look-dev crop around Grandbois.**
   - Colours were washed out, and streamline gaps showed as pale linen lines.
   - Fixes: a padding-felt underlay laid first, then richer dyes.
2. **First full-board bake.**
   - A crease added to the linen height was overriding the sea strands, leaving a pale band. It was removed.
   - The sea couching bars read as stripes; they were softened.
   - The gold borders were made bolder.
3. **First Eevee renders.**
   - With the key from the upper left, the pieces were back-lit and dark. The key moved to the left-front, raking on the cloth and three-quarter on the pieces.
   - The pines sat half under the cloth (missing transform_apply).
   - The footprints were glaring white bare linen. They became the coupon's padding felt with underdrawing and needle holes.
   - Towns and figure cards were enlarged.
   - Tethers were shortened and made thinner, and now come from the lower outline.
4. **Comparison against the menu frame.**
   - Our sea was teal and the whole board 25 % too bright. The fixes were a deep denim dye with a blue underlay, exposure 0.63, and a less orange key.
   - Fibres rooted just outside strands appeared on bare linen before stitching. Ownership was fixed.
5. **720p preview of the whole move.**
   - Eevee legacy motion blur did nothing on the python-driven frames, so it was replaced by COMP homography blur.
   - Towns sank into the swollen coupons. The padding is now pressed flat under them.
   - The underdrawing was too faint ahead of the wave and was boosted, only on linen that the final state covers.

## Known gaps and choices (honest list)

- **Elevation icons instead of plan icons.** Towns, trees and figures are stitched as Bayeux-style elevations lying flat, rather than plan views. This is what makes the pop-up hinge work and keeps the needle-hole footprint visible behind each risen piece. A plan icon would be hidden under its own model.
- **Unit markers are missing.** The game's shield-on-a-pole markers above unit groups and the in-world nameplates are not built.
- **Two towns are taken from the demo world.** Vaugrise and Brumecourt (under the menu card) and the realm extents come from the demo-mode world, which is played to turn 16 with 4 players. Its development state may differ slightly from the menu world.
- **The board is sparser and lighter than the game's.** The game shows denser pine forests, houses on every forest hex, bigger 3D crop rows and darker satin; see `compare_f1782_vs_menu.jpg`. Hex positions, settlements, realm borders and the sea align with the menu frame. Some pines read pale grey-green on their lit side.
- **The game OBJs read as painted low-poly pieces.** The stitch port is a bump-level laid-wool texture and an outline, not re-embroidered geometry. The figure cards are the game's own embroidered art.
- **View-dependent sheen is baked.** The ground's sheen and highlights are baked for the face-on view. Under the 24 deg crane the satin sheen does not re-orient; only Eevee's diffuse lighting ratio responds to the swell.
- **The swap still has residual texture-filter differences.** At the swap, R25 uses Gaussian prefilter plus bilinear while Eevee uses GPU mip/anisotropic filtering with TAA. The 6-frame dissolve hides it (see `qa.json` and `ab_swap_f1719_vs_f1725.jpg`).
- **Motion blur is camera-only and approximate.** It is done in COMP via ground-plane homographies, because Eevee legacy's own motion blur had no effect on these python-driven frames. Parallax of tall pieces is not blurred separately.
