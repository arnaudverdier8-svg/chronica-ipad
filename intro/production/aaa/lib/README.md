# aaa/lib/chron: the shared CHRONICA embroidery library (R25 production port)

Python 3.13 + numpy / cv2 / numba (system `python3`). Pure library: **read-only for keyframe agents**. Import with

```python
import sys; sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
import os; os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import cv2; cv2.setNumThreads(2)
```

Keep one heavy process per agent, `nice -n 5`. A frontal 2560x1440 frame costs 6-25 s (5 px/mm mip: ~8-14 s;
10 px/mm level for F2 framings: ~20 s), RSS ~1-1.5 GB.

## Baked assets (MapSets, `aaa/cache/maps/`)

| sheet | content |
|---|---|
| `p1_oath` | p1 re-embroidered at 10 px/mm, everything stitched (Act I state). Candle glows inpainted out of the source before segmentation; stitched flames are matte laid wool. |
| `p1_oath_ground` | p1 WITHOUT the groups `crown, king, goblet_0..3, candle_0..3`, but WITH their ghost: protected (flattened, fresher) linen, needle holes at the real strand ends (Poisson-thinned, ~1 mm), red-brown underdrawing (`#6E3326`) of the group's outlines and silhouette. This is the S09 p1' base (goblets/candles reduced to needle-hole outlines, king-shaped void once the king is unpicked). |
| `p3_death`, `p3_death_ground` | p3; groups `flame_0..3` (the four stitched candle flames only, ~20 entries each; S07 unpicks one: `demo/out/p3_flame_unpick_sheet.png`). |
| `p6_ruin`, `p6_ruin_ground` | p6; groups `tower_top_l` (cracked tower top: peel / R25-L slip), `tower_l`, `tower_c` (upper courses, stone only, sweep order: unpick runs top-down), `banner` (torn banner: slump). Sky and flames inside the boxes stay in the ground (`demo/out/p6_groups_full_vs_ground.jpg`). |

Sheet coordinates: **mm, origin at the sheet's top-left, x right, y down**. Each panel sits at (20, 20) mm inside its
sheet (20 mm linen margin; beyond that `read()` pads with the same analytic linen, so there is never a void).
Panel source px -> sheet mm: `x_mm = x_src / 5 + 20`, `y_mm = y_src / 5 + 20`. Sheet = 590.4 x 347.2 mm.
p1 king centre ~ (297, 200) mm, crown ~ (295, 124) mm, panel centre (295.2, 173.6) mm.

Files per sheet: `manifest.json` (PX, levels, channels, groups), `L0/tile_rr_cc.npz` (2048 px tiles + 64 overlap,
float16), `L1.npz L2.npz L3.npz` (5, 2.5, 1.25 px/mm mips), `stitches.npz` (the RECORD), `groups.json` (group names,
counts, field-mode stats).

Channels: `h` (mm), `alb` (linear RGB, no lighting), `T` (thread tangent), `mat` (0 linen 1 wool 2 silk 3 metal ...),
`cov` (fuzz coverage: fills 1, stem 0.5, cords 0.3, metal/silk 0), `sid`, `reg` (region id; 65535 = outlines),
`grp` (group of the top stitch; 0 ground), `birth` (needle order + along-strand, [0,1]), layers `age_fox`, `age_tide`,
`age_fade`, `ghost` (1 under any group polygon), `ud` (underdrawing), `holes`, `gpoly` (group polygon id), `pad`.

## Modules

| module | what |
|---|---|
| `config` | paths (`MAPS`, `HINTS`, `PANELS`), `FPS`, `frame_of(t)`, `event('word:crown')`, `event('shot:S09')` |
| `color` | `srgb2lin lin2srgb hex_lin pal('crimson') kelvin(K) light_colour(K, tint) lin2oklab oklab2lin chroma_cap ShadeSet` |
| `maps` | `MapSet(path)`: `.read(x0,y0,x1,y1, level)` (sheet mm, padded, float32 working maps with `PX`, `origin_mm`, `valid`), `.read_px`, `.full(level)`, `.level_for(screen_px_per_mm)`, `.stitches()`; `MapSet.write(...)`; `downsample` |
| `shade` | `rig(az, el, K, key_i, fill_ratio, rim_i, points=[{pos_mm:(x,y,z), K, i, ref_mm, shadow}], k_env)` light rigs; `relight(maps, rig, cam, kmap)`; `lod_height`, `toksvig`, `normals`, `ambient_occlusion`, `shadow_march`, `shadow_march_point`, `spot` |
| `frontal` | `render(src, view, light, ...)` R25-F: mip select -> ageing / edits -> LOD normals -> relight -> halo -> Lanczos warp -> fibres; returns `dict(lin, alpha, level, ...)`; `render_checked` (+G4) |
| `grade` | `grade(lin, exposure=0.85, act='I'..'V', grain=0.012, seed=frame)` -> sRGB uint8 (`out_u16=True` for PNG16); `act_of_frame(f)` |
| `ageing` | `apply_age(alb, mat, amount, layers, ghost)` (amount scalar or HxW: 0 fresh/as baked, 1 aged Act II); `bake_age_layers` |
| `anim.groupanim` | `GroupAnim(ground_mapset, ['king'])`: exact stitch-on / unpick of record groups: `.edit(u, mode='on'|'unpick', rate)`, `.glint_overlay(u)`, `.loose_overlay(u, rate, light, linger=[(rank, phase)])`, `.state(k)`, `.needle_tip(u)`, `.n`, `.bbox` |
| `lift` | `Slip(GroupAnim(ground, ['crown']))`: R25-L slip layer: `.layers(view, light, lift_mm)` -> rgb / alpha / PCSS shadow, `.composite(lin, layers)`; `tethers(img, top_mm, ground_mm, lift_mm, ctx, light, col)` |
| `fibres` | calibrated `halo`, `make_fibres`, `render_fibres`, `splat_thick`, `light_curves` |
| `qa.void` | `check_void(img, alpha)` -> raises `VoidError` on any void / non-finite pixel (G4) |
| `linen` | `make_linen(H, W, PX, x0_mm, y0_mm, seed)` translation-invariant tabby (any window, seamless) |
| `stitch`, `strands`, `fields`, `segment`, `skel`, `record`, `motifs.panel` | the bake: stitch primitives + RECORD, numba kernels, G6 field decision, segmentation, skeletons, needle order + exact replay, whole-panel builder |

### view / light conventions
* `view = dict(cx_mm, cy_mm, px_per_mm)` (or `x0_mm, y0_mm, px_per_mm`) in sheet mm; output 2560x1440 by default
  (`out_wh=`). F0 = 3.3, F1 = 4.65, F2 ~ 10-13 px/mm. The renderer picks the shading level by the 1.0-1.4x rule
  (F0/F1 -> 5 px/mm mip, F2 -> 10 px/mm) and fades weave/strand normals below ~2.5 screen px (G7).
* Light azimuth: degrees, 0 = from the right (+x), 90 = from the top of the image, 135 = upper left. Point lights in
  sheet mm with z = height above the cloth in mm; `ref_mm` = distance at which the inverse-square factor is 1.
* `kmap=dict(cx_mm, cy_mm, r_mm, floor, aspect)` = key-light pool (physical vignette).
* Fibres are generated per window from a seed (`fib_seed`): for moving cameras build one fibre set for the shot
  (`fibres.make_fibres` on a shot-wide window, `frame` key absent, roots in that window's px) and pass `fib=`.

## Snippets

```python
from chron.config import MAPS
from chron.maps import MapSet
from chron import frontal, shade, grade
from chron.qa.void import check_void
P1 = MapSet(MAPS + '/p1_oath')
light = shade.rig(az=135, el=22, K=3000, key_i=2.7, rim_i=0.25)                      # Act I window key
fr = frontal.render(P1, dict(cx_mm=295.2, cy_mm=173.6, px_per_mm=4.65), light,
                    kmap=dict(cx_mm=230, cy_mm=150, r_mm=400, floor=0.55), fib_seed=3)
check_void(fr['lin'], fr['alpha'])                                                   # G4
img = grade.grade(fr['lin'], exposure=0.95, act='I', seed=140)                       # uint8 RGB
```

S09 / f669 (Act II p1', king unpicked, crown slip on tethers, guttered candle low left):

```python
from chron.anim.groupanim import GroupAnim
from chron.lift import Slip, tethers
G = MapSet(MAPS + '/p1_oath_ground')
king, crown = GroupAnim(G, ['king']), GroupAnim(G, ['crown'])
candle = dict(pos_mm=(-63, 190, 78.0), K=1900, i=2.6, ref_mm=360, tint=0.55, shadow=True)   # ~12 deg at the throne
light = shade.rig(az=150, el=12, K=1900, key_i=0.3, fill_ratio=6, tint=0.5, points=[candle])
u = king.n * (f - 561) / 80            # entries removed; unpick f561-640 (couching first, then top -> bottom)
view = dict(cx_mm=310, cy_mm=170, px_per_mm=5.81)
fr = frontal.render(G, view, light, age=1.0,                                  # Act II re-dye + tideline + foxing
                    edit=king.edit(u, mode='unpick'),
                    overlay=king.loose_overlay(u, rate=king.n / 80, light=light))   # curling loose ends
slip = Slip(crown); L = slip.layers(view, light, lift_mm=15.0)
lin = slip.composite(fr['lin'], L)                                            # crown 15 mm up, PCSS shadow
img = grade.grade(lin, exposure=1.0, act='II', seed=f)
```

Stitch-on of any group (needle order, per-strand growth, pop 0.55 -> 1.15 -> 1.0, needle glint):
`frontal.render(G, view, light, edit=ga.edit(u, mode='on', rate=r), overlay=ga.glint_overlay(u))` with `u` growing
from 0 to `ga.n`.  Ageing as a parameter: `render(..., age=0.0)` fresh (as baked), `age=1.0` aged; revival =
`age=lambda m: amount_map(m)` (HxW in the window, sheet mm from `m['origin_mm']`, `m['PX']`).

Group bboxes / centres in sheet mm: `cache/maps/<sheet>_ground/groups_mm.json` (e.g. p1 king centre (297.1, 206.2),
crown (294.2, 124.0)).  Masks for art direction: `MapSet.read(..., keys=['grp','gpoly','reg','ghost'])` - `grp`/`gpoly` ids follow
`groups.json['groups']` (index 0 = ground).

## Re-bake / demos / tests

```
cd aaa/lib
python3 bin/bake_panel.py p1_oath        # ~3.5 min, ~3.4 GB peak; writes cache/maps/p1_oath{,_ground}
python3 tests/test_contract.py p1_oath   # exact replay: ground + groups == full bake
cd demo; python3 g2_metal.py; python3 g3_fuzz.py; python3 g4_void.py; python3 g6_fields.py; python3 g7_lod.py
python3 g8_stitchon.py; python3 g8_unpick.py; python3 ageing_glow.py      # outputs in demo/out/
```
Hints (art direction, source px) live in `hints/<panel>.json`: groups (polygons + order policy + optional `families` /
`exclude_families` filter: only regions of those colour families inside the polygon join the group; outlines join a
group when they lie within 1.2 mm of its regions), glows, faces,
beards, metal boxes, ermine, zones (field mode / angle / remap / force_bg), busy zones, tidelines, outline suppression.
Everything is deterministic (seeded); re-running a bake reproduces the MapSet.

## Gate status (demo/out/, all 2560x1440 PNG + 100 % crops unless noted)

| gate | fix in the library | proof |
|---|---|---|
| G2 metal | `shade.brdf`: metal environment term `k_env * E(reflect(-V, N_strand))`, E = warm studio gradient (softbox lobe toward the key azimuth at 62 deg elevation, 35 deg wide, + 8 % dome, dark floor), wider anisotropic lobes (KK 60 / 18 + ndh terms, Toksvig-widened) | `g2_metal_azimuths.png` (crown at az 60 / 120 / 180, with and without the env term), `g2_crown_az*.png`, `g2_metal_stats.json` (metal pixels above the L2 cap #F8D57C: 0.1-0.2 % of the crop) |
| G3 fuzz | `fibres`: halo x coverage, density x cov (fills 1 / stem 0.5 / cords 0.3 / metal 0), no per-stitch edge boost, colour x U(0.95,1.05), dark-fill + contrast attenuation, self-shadow (vis_root and tip occlusion), slip clip 0 | `g3_fuzz_compare.png` (R25 fuzz vs calibrated, 3 crops), `g3_fuzz_*` full frames |
| G4 void | analytic translation-invariant linen pads every read outside a sheet; `render` returns a coverage alpha; `qa.void.check_void` raises on any void | `g4_void_padded_marked.png` (frame over the sheet corner: PASS 0 px), `g4_void_report.txt` (unpadded read caught: 2.4 M void px) |
| G6 fields | `fields.select_field`: tensor if coherence >= .35 on >= 70 %, else region-axis (straight, <= 12 deg bend over 30 mm) for laid work, blend for needle-painting, contour-parallel for metal; ermine on a constant axis with diagonal jittered couching; similar-colour regions merged so a garment is one laid region | `g6_tangent_king.png` (tangent hue map, R25 whorls vs production), `g6_robe_ermine_compare.png` |
| G7 LOD | mip select (1.0-1.4x), height split into fine / strand / structure bands faded by screen period (P0 1.2 px, ramp 1.5 px), Toksvig, Lanczos warp, AO + shadows on the mip height | `g7_lod_crops_x2.png`, `g7_F0_still.png`, `g7_truck_*.mp4` (12 px/frame truck at F0), `g7_shimmer.json` (registered HF residual 0.30 % production vs 0.26 % for 4x more expensive 10 px/mm shading; budget is +3 points) |
| G8 stitch-on / unpick / ageing | RECORD of every stitch (+ squeeze events), needle-path order (boustrophedon laid -> metal -> couching units; 'sweep' groups bottom->top so the unpick releases couching first then runs top->bottom), exact replay (`tests/test_contract.py`: ground + groups == bake, <1e-6 of pixels differ by fp16 rounding), per-strand growth + pop + needle glint, checkpoint + forward replay, loose ends (lift / curl / pull-through, lit by the dominant light incl. practicals), ghost (needle holes at the real strand ends + red-brown underdrawing + protected linen), `ageing.apply_age` | `g8_stitchon_sheet.jpg`, `g8_stitchon_crown.mp4`, `g8_stitchon_mid.png`; `g8_unpick_sheet.jpg`, `g8_unpick_seq.mp4`, `g8_f669_like.png` (+ crops); `age_compare_tablecloth.png`, `age_fresh.png`, `age_aged_p1prime.png` |
| S03 glows | `motifs.panel.inpaint_glows` (radial per-channel gain removal) before segmentation; stitched flames remapped to matte laid wool | `glow_inpaint_source.png`, `glow_candle_stitched.png` |

## Known limits
* Bake peak RSS ~3.4 GB (one bake at a time; renders ~1-1.5 GB).
* p1: a few ermine stitches at the king's right shoulder lie outside the king polygon and stay after the unpick; the
  head part of the void has the polygon's straight sides. Edit `hints/p1_oath.json` (king poly) and re-bake if needed.
* p3: some light highlight strands in the navy wall read as specks; p6 sky keeps the AI violet / red bands (re-dye in
  the shot via `apply_age` or an OKLab hue map; storyboard asks madder / woad-grey / buff).
* Loose-end curls are an authored curve model (no physics), rendered as lit capsules with a soft cast shadow.
* Dirty-rect relight is not implemented: an animated group is re-rasterised exactly inside its bbox, but the frame is
  relit in full (~8-25 s / frame at 1440p depending on the level).
* Loose ends of dark outline strands under the dim Act II key read as dark smudges at 1280x720 during the fastest
  part of the unpick (`g8_unpick_seq.mp4` ~frame 20); slow the rate or pass `alpha<1` to `loose_overlay` for those.
* Tests: `tests/test_contract.py <sheet>` (exact replay, padding) and `tests/test_readme_snippets.py` both pass for
  p1 / p3 / p6.
