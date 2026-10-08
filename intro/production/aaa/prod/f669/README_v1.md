# KEYFRAME f669 - S09 "Every lord looked at the empty chair" ('chair')

Production-proof keyframe for client approval, plus a 2 s, 720p proof that the king's unpick reads as physical.

## Deliverables (`out/`)

| file | what |
|---|---|
| `f669_2560x1440.png` | **the keyframe**, 8-bit sRGB, Act II grade (16-bit twin: `f669_2560x1440_16bit.png`) |
| `f669_preview_1280.jpg` | downscaled preview |
| `f669_crop_*.png` | 100 % crops: `crown_tethers`, `crown_shadow_in_void`, `void_holes_underdrawing`, `loose_purple_strands`, `red_lord_face_rim`, `blue_lord_face_rim`, `goblet_candle_ghosts_tideline`, `left_goblet_ghost` |
| `f669_report.json` | view, mip level, timings, measured scene-linear EV of faces/crown/table vs the lit void, crop rectangles, G4 void check |
| `f669_unpick_test_f600-660_720p.mp4` | 61 frames (f600-660) at 1280x720, 30 fps, H.264 + AAC slice of `audio_master_1984f_s16.wav` (sample = f * 1470) |
| `f669_unpick_test_sheet.jpg`, `unpick_test_720p/f*.png` | contact sheet and the frames of the test |
| `f669_iterations.jpg` | the visual iterations (library recipe -> final), for the review |

## Re-render

```
cd aaa/prod/f669/src
nice -n 5 python3 render_keyframe.py        # ~55 s wall, 2.7 GB peak RSS (measured), writes out/f669_*
nice -n 5 python3 render_unpick_test.py     # ~8 s/frame at 720p (61 frames ~ 9 min), writes the mp4 + sheet
```

Everything is a deterministic function of the frame number (`shot.render_frame(f, out_wh, level)`), so any frame of
S09 (f561-716) can be rendered with the same call: e.g. `F0=561 F1=716 python3 render_unpick_test.py` renders the
whole shot at 720p.  System python3 (3.13) + numpy / cv2 / numba / scipy; the hardened library `aaa/lib` is used
read-only (`NUMBA_NUM_THREADS=2`, `cv2.setNumThreads(2)`).

## What is in the frame and how it is made

| storyboard element | implementation |
|---|---|
| p1' at 1.25x, throne at frame x 0.47 | `shot.view_of`: 5.8125 px/mm (F1 4.65 x 1.25), throne axis x = 294.5 mm at 0.47 x 2560; camera path for the whole shot (locked 1.06x, 1 px/frame drift, smoothstep-eased exponential push f637-669, 2 px/frame drift after) |
| one guttered 1900 K candle low on the left, 12 deg | a shadowed point practical (`candle_relight.py`): 70 mm high, 337 mm from the void, az 108 at the void (upper left, beyond the panel's top edge), 12 deg at the throne; guttering = slow 1-2 Hz breathing <= 2.2 %, 7.7 Hz <= 0.6 % (G13-safe), 1 mm flame sway |
| pool on the throne, right of the scene in shadow | key-light pool shaping the CANDLE (not a directional key): elliptical pool centred on the void (taller downward), 30 % of the physical inverse-square falloff kept; cool night fill (#141325) at ~1:14 of the candle on flat linen at the void. Measured (scene linear, vs the lit void): red face -2.0 EV, blue face -2.8 EV, outer lords -4.2 / -4.9 EV |
| KING-SHAPED void, needle holes, red-brown underdrawing | `kingvoid.py` + `silhouette.py` (see below): the void follows a hand-traced silhouette of the king (hair, ermine cape, sleeves, robe, hand on the table) instead of the bake's coarse polygon; the throne backrest and wood inside the old polygon stay; ermine/cape debris outside it is unpicked too; the designer's ink line of the silhouette is added; ink inside the void slightly stronger than the bake (0.72 -> 0.95, cap 0.6 -> 0.72) |
| a few purple strands still curling off the cloth | `loose.py`: 5 'stubborn' purple laid threads of the lap, pulled slowly through their holes during the gap (mid-pull at f669); 3D wool rendered by `threads3d.py` (2-ply twist, crimp, kinks where they were couched, fuzz halo and stray fibres, Kajiya-Kay + wrap lighting from the candle, soft projected shadows); colour nearer the original dye (sheltered underside). Plus wisps of wool left in ~7 % of the needle holes |
| gold crown slip ~15 mm above the void, four gold tethers, soft shadow below | `crown.py`: the baked 'crown' group as an R25-L slip (library `Slip` for maps/alpha, pin-holes filled), lit by the candle at its own height, perspective parallax about the frame centre (camera 1200 mm), turning 2.4 deg on its tethers; shadow = slip alpha **projected from the candle** (x1.27, ~72 mm throw) with a flame-size penumbra, landing in the void; 4 couched-gold tethers (Japan gold shading) from the band corners and arch shoulders to needle holes in the cloth, with their own long shadows |
| Act II grade, aged / desaturated | `render(age=1.0)` (re-dye, fade, foxing, linen yellowing; the void's linen protected = fresher) + `grade(act='II')` |
| a tideline across the cloth | `shot.tide_layer`: a translation-invariant water-stain edge across the king's lap and the table (darker 1-2 mm dried edge, fainter inner ring, stained interior) + a second, fainter one in the upper-left background; added to the `age_tide` layer and as an edge darkening |
| goblets and stitched candles reduced to needle-hole outlines | from `p1_oath_ground`, repaired by `groundfix.py`: goblet_1's bowl (missed by the bake's hint polygon) is removed to holes + underdrawing; the protected-linen ghost of all goblets/candles follows their real stitched footprint instead of the hint rectangles |

### The rebuilt ground patches (kingvoid.py / groundfix.py)

`p1_oath_ground` is reconstructed from first principles inside the king's bbox and around each goblet/candle:
analytic linen (`make_linen`, seed 11) -> the bake's ghost recipe (flattened protected linen, stored underdrawing,
stored needle holes) -> replay of every ground record entry in needle order.  This was verified **bit-exact** against
the baked ground (max |dh| 2.4e-4 mm, max |dalbedo| 4.9e-4, sid identical = fp16 rounding; `work/a4_recon.py`).  With
that, the record can be re-partitioned: entries can leave the ground (cape debris, the goblet bowl - they get needle
holes at their strand ends with the bake's Poisson spacing) and the protected-linen mask can follow any shape.

### The unpick (test video)

* Unpick list = 5841 king entries inside the silhouette + 309 cape debris (347 throne entries of the old group kept), in the king's needle order (debris slotted
  in by height); f561-640 on twos, couching first then top -> bottom (exact checkpoint + forward replay).
* A **slackening ripple**: the next 260 entries before the front are replayed raised (height x1.0 -> 1.3), so the
  raking candle shows the strands loosening just before they come out.
* Loose ends are cut into THREADS (consecutive entries one needle walked); only ~10 % of laid threads (fewer for
  split/stem) come out as visible loose ends - the rest are drawn through from the back - so the front carries
  10-18 strands at a time, not a particle spray.  Each thread: release -> slacken (2 fr) -> fall over and curl
  (3 fr) -> pulled back through its hole (4 fr: the curve slides along itself into the hole, the ply twist travels
  toward the hole, the loops tighten).  The crown slip rises 0 -> 15 mm while the head is unpicked (f575-592).

## Library use and runtime patches (no library file was edited)

* `chron.frontal.relight` is replaced **at runtime** by `src/candle_relight.relight` (a copy of `shade.relight` whose
  row 0 is the candle point light, so `kmap` shapes the candle; same numba BRDF kernel, `shadow_march_point`, metal
  environment term).  Lights without a `candle` entry fall through to the library function unchanged.
* `chron.lift.Slip` is used for the crown maps and alpha; its `layers()` is not used (replaced by
  `CrownSlip.layers`: candle-projected shadow, rotation, perspective parallax).
* `GroupAnim` / `loose_overlay` are not used for the king (replaced by `KingVoid` + `LooseEnds`); `GroupAnim` is
  used for the crown group.
* `render_frame` reads the window itself (`MapSet.read` with only the 9 channels the relight uses, the same 8 mm
  margin) and passes the maps dict to `frontal.render`; the level-0 tile cache is then dropped before the relight.
  Output is bit-identical to `frontal.render(MapSet, ...)`; peak RSS of the 1440p keyframe fell 3.85 -> 2.70 GB.
* Mip level: L0 (10 px/mm) for the 1440p keyframe; the 720p test is forced to L1 for all frames (no mip switch
  during the push).  **Production note:** the 1440p shot should also force one level (L0) for f561-716, otherwise
  `level_for` switches L1 -> L0 at 5.0 px/mm during the push.

## Art-direction decisions to confirm with the client

1. **Candle azimuth.** The storyboard's 12 deg candle "low on the left" throws a 15 mm-high crown's shadow ~72 mm.
   From due left (az 150-180) that shadow lands on the throne and the blue lord's arm, not "below, in the void".
   The candle sits off the upper-left (az 108 at the void, 112 at the crown), still 12 deg, so the crown's shadow
   falls into the king-shaped void.  Act II's nominal key (pipeline 6) is az 135; S10 starts its carry from here.
2. **Rim exposure.** At the storyboard's -1.5 EV the faces did not read as "in shadow" after the ACES + Act II grade
   (iteration v1, `f669_iterations.jpg`); the final has the red/blue faces at -2.0/-2.8 EV scene-linear (they still
   read clearly, see the face crops) and the outer lords in near darkness.
3. **The tideline** crosses the king's lap and the table (the brightest cloth in frame) rather than only the dim
   tablecloth at the frame bottom, where it was invisible.

## Known issues / limits

* Faces of the red and blue lords are at 1.16x panel-native (as specified) and stay soft-edged R25 needle painting.
* The loose wool is an authored curve model (no physics); shadows of the high parts of a strand are long thin lines
  (correct for a 12 deg candle, but they can read as extra strands in a still).
* The tether ground holes and the crown's ghost under the lifted slip are only visible where the 2.4 deg turn uncovers
  them (1 mm slivers).
* At 720p the unpick front is still busy around f612-630 (the robe after its couching is gone + the slackening
  ripple); at 1440p it resolves into strands.  The test is rendered from the L1 mip and is softer than the 1440p frame.
* The purple banner above the throne keeps the king's (aged) purple; the colour script says purple leaves with the
  king - a further desaturation of the banner would be a one-line `age` map change if wanted.
* The candle-pool shaping is a cinematic flag (a guttered candle's own falloff cannot centre a pool on the throne);
  30 % of the physical inverse-square falloff is kept so the left/upper side stays brighter.

## Sources (`src/`)

`shot.py` (camera, light, pool, tideline, compositing order, `render_frame`), `candle_relight.py`, `kingvoid.py`,
`silhouette.py` (traced silhouette + ink line), `groundfix.py`, `loose.py` (loose threads, hole residue),
`threads3d.py` (wool / gold thread renderer), `crown.py`, `render_keyframe.py`, `render_unpick_test.py`.
`work/` holds analysis scripts (`a1`..`a6`: record classification, exact-reconstruction proof, partition and void
checks) and iteration previews.
