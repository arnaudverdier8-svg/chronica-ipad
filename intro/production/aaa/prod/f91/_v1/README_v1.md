# CHRONICA keyframe f91 (S02 'realm') and gate G1 (procedural Bayeux kit vs p1)

Status: production-proof candidate (v20 kit + render). Everything here was looked at (full frame, 100 % crops, G1 side-by-side).

## Deliverables (this directory)
| file | what |
|---|---|
| `keyframe_f91_2560x1440.png` | the keyframe, 2560x1440, 16-bit PNG (graded Act I, grain, zoom blur) |
| `keyframe_f91_2560x1440_8bit.png` | the same, 8-bit (review copy) |
| `crops_100pct/c01..c10` | 1:1 crops: thread + crimson tie-down (+3x), border lions, capital + crown, large town + pennant, river / bridge / hamlet, road colours, ploughed + meadow, hill town + tree, top-left corner (blur) |
| `g1/g1_side_by_side_2560x1440.png` | G1: kit (left, butted at its right edge) | p1 (right), both 4.65 px/mm, one rig, one pool, one fold field, one ageing map, one grade |
| `g1/g1_crops_100pct.png`, `g1/g1_stats.json` | matched 100 % crops (kit row / p1 row) and linen / wool / relief statistics |
| `blur_compare/` | top-left corner at the storyboard-implied blur (0.036/frame) vs the chosen 0.012/frame |
| `scene_f91.py`, `render_f91.py`, `shot_f91.json`, `g1_proof.py` | sources (`../kit/bkit/*` = the kit: `motifs.py`, `canvas.py`, `elevation.py`, `geom.py`, `beasts.py`) |
| `closeup.py`, `crop.py`, `hamlet_test.py`, `thread_test.py` | helpers used in the iterations |
| `_hist/`, `../kit/_hist/`, `_hist_renders/` | v12 sources and render (the state inherited from the stopped agent) |

Baked sheets (not copied; 161 MB each): `aaa/cache/maps/k1_realm` and `k1_realm_ground` (6000x3300 @ 10 px/mm = 600x330 mm, MapSet contract of aaa/lib; the `_ground` sheet is the same without the road group, with its ghost). S02 f92-139 should relight `k1_realm` with `render_f91.render_frame` (only key az/el change in the breath).

## Reproduce
```
cd aaa/prod/f91
nice -n 5 python3 scene_f91.py          # kit bake -> cache/maps/k1_realm(+_ground): ~4.2 min, peak RSS 2.8 GB
nice -n 5 python3 render_f91.py --tag x # frame: ~20-25 s, RSS 1.7 GB  (F91_KEY_I, F91_FILL_RATIO, F91_EL, F91_AZ, F91_ZOOM_RATE override the rig / blur)
nice -n 5 python3 g1_proof.py           # G1 proof: ~35 s
```
Light (shot_f91.json): 3000 K key, az 128 deg (upper left), el 22 deg, key_i 3.0, key:fill 3.6, 25 % rim at az 30 / el 8, k_env 0.35; window pool = screen-space `pool_all` (centre 240,118 mm, r 262, floor .36) x library kmap; shared cloth fold field (frieze mm, unchanged); ageing base 0.20 + hem boost + side boost (metal pixels keep 12 %); Act I grade, exposure 1.0, grain .012. Camera: 5.0 px/mm, top-left (40, 5) mm, zoom about the frame centre, 180-deg shutter, rate 0.012/frame, shaded on the 5 px/mm mip (level 1).

## What the frame contains (checked against the storyboard text)
* ONE road in the four house colours, repeating gold / crimson / woad / green with slanted colour joins, entering at the left edge, climbing the capital rise to the gate of the crowned capital at frame x ~0.63, then on to the large town and out right. It is the only saturated multicolour path: the hillock bands are muted olive / moss / sand / stone (the back ridge has no blue so the only blue line in the land is the river).
* Four towns of different sizes with house-colour pennants: hamlet (green, 4 cottages round a tower), river town (woad, settle_1), hill town (crimson, settle_1_2 on its own hill), large town (gold, settle_2); capital = `capital` keep + `walls_2`, crown (couched gold, crimson ties, padded satin jewels) floating 4 mm above the spires.
* Paired-line river (olive pairs + woad / olive wavy pairs) under an arch bridge, ploughed strips (two fields), tufted meadow mound, interlace trees with trunks banded in the house colours.
* Upper border: confronted red / blue lions (game vignettes, off-centre left), diagonal-bar compartments, millefleurs, blue-black + red-brown rules; two nail holes in the hem.
* Gold chronicle thread (two-ply silver-gilt pair, 2.4 mm wide, twisted plies) rising from a needle hole at top left with its first crimson silk tie-down; beyond the tie it is untied and wanders off along the underdrawn rule toward the needle (right, off frame).
* Linen 58.7 % of the frame (measured on the baked map in the f91 window; storyboard asks 40-55 %): the open sky between the border and the hills is the cause. A far ridge that fills it (`_hist/scene_f91_v21_farridge_rejected.py`) only reached 57 % and tangled with the tree / hill-town spire, so it was rejected. Couching-bar shadow grid visible in every laid fill.

## Gate G1 (kit beside p1, matched px/mm, identical relight): PASS with one noted difference
Same linen (albedo 0.623 / 0.480 / 0.284 vs 0.633 / 0.488 / 0.290), same strand, couching, outline and fuzz craft, same light and pool: the seam reads as a change of subject / hand, not of material. Wool chroma median .068 vs .069 (p95 .111 vs .116), wool height p50 0.47 vs 0.46 mm (p95 0.99 vs 1.06). Noted difference: kit wool is lighter (OKLab L median .553 vs .442: pale stone walls, no needle-painted browns) and has more high-frequency energy (hf std .107 vs .086). The kit is laid-and-couched flat colour, p1 is painterly; the storyboard asks for exactly that register split.

## Changes since v12 (iterations v13-v20, each baked and looked at)
1. Palette: buff / linen_hi are the same value as the linen (palette contrast 1.0), so walls and bands vanished: new neutrals (`stone`, `stone_dk`, `stone_warm`, `sand`, `clay`, `moss`...), deeper olive / mustard / terracotta / woad; hill bands muted so the road pops; ageing base .32 -> .20 (Act I = near fresh dyes).
2. Hamlet: the settle_0 palisade read as hay bales; replaced by hand-drawn cottages + tower (`M.cottage`, `M.watch_tower`).
3. Capital: finial rings (gold class) skipped; crown re-seated.
4. Thread: 0.4 -> 0.55 mm ply radius, 1.0 mm twist lay (readable at 5 px/mm), deeper gold albedo, metal exempt from dye ageing (it had faded to straw), bolder crimson tie, thread extended to the frame edge with a loose, wandering tail.
5. Stitch craft: couching-bar angle jitter (1-1.3 deg), hill / town wobble up, tufts on the meadow, band `model` lowered (less tube-like), tonal modelling on big fills.
6. Light: key 2.8 -> 3.0, fill ratio 3 -> 3.6, tighter pool; nail holes moved into the hem (y 7.4 / 7.9 mm).
7. Blur rate 0.005 -> 0.012 (see below).

## Findings for the orchestrator
* **Camera inconsistency (needs a decision):** the S01 pull-back is smoothstep over f40-114 (96 -> 776 mm). That curve gives d(ln s)/df = -0.036 at f91 (s ~ 5.3 px/mm), i.e. ~46 px/frame at the frame edge and 23 px streaks with a 180-deg shutter: the tie-down at top left is smeared (`blur_compare/`), contradicting the keyframe text ("a trace of motion blur at the frame edges", tie-down visible). Any 5 -> 3.3 px/mm ease-out over f91-114 needs at least ~0.018-0.036/frame. I rendered 0.012/frame (~8 px at the corners). To make the film match this keyframe, either ease S01's end harder (s(f91) nearer 3.8) or use a smaller shutter angle on f85-100.
* Storyboard says hamlet = settle_0 elevation; I used hand-drawn cottages (same stitch language) because the stitched palisade did not read.
* S01's border bake must carry the same nail holes / thread tie position: tie at sheet x = 77.5 mm, thread start (needle hole) x = 70 mm, rule y = 17.5 mm, nail holes (156, 7.4) and (404, 7.9) mm; these are parameters in `scene_f91.py`.
* The `k1_realm` sheet is 600 mm wide, the F0 field (776 mm) exceeds it: S02 frames f105+ need the neighbouring frieze section or analytic linen (the library pads with linen; for the truck-right f126-139 the T1 tree divider section must supply x > 600 mm).

## Known issues
* Linen fraction 58.7 % is above the storyboard's 40-55 % band (see above); the realm could be raised / enlarged ~6 % in the S02 camera (F0 framing covers more) instead.
* Kit values are lighter than p1 (above); hamlet and capital finials are simple; the bridge is small and mostly hidden by the road (reads, but weakly); tiny spike notches remain at the capital spire tips; crown floats by design.
* Light is "flat-lit" at the realm scale: relief is carried by the couching grid, outlines and fuzz, not by large-scale shadows (the key at 22 deg shows hills as bands, not as cast shadows; the S02 breath of the key will be visible mostly on the grid and cord relief).

Reproducibility: the baked sheet and the render are deterministic; re-baking `scene_f91.py` and re-rendering reproduced `keyframe_f91_2560x1440.png` bit-exactly (max abs diff 0 on the 16-bit PNG).
