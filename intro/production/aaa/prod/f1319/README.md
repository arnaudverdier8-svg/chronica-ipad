# CHRONICA keyframe f1319 (S18 'edges'): the chronicle fraying into darkness: v2 (after the three critiques)

Status: production-proof candidate, revision 2. Everything below was checked by looking at the renders (8 full-frame iterations of this pass in `iterations/`
and `iterations_contact_sheet.jpg`, nine 100 % crops of the final in `crops_100pct/`, 1.5x-2.5x zooms while iterating). Bit-exact reproducible
(re-render diff = 0.0 on the linear frame, checked twice). The first delivery is kept untouched with the `_v1` suffix (`keyframe_f1319_2560x1440_v1.png`,
`crops_100pct_v1/`, `src_v1/`, `README_v1.md`, `falloff_check_v1.json`, `iterations_v1/`, `run_all_v1.sh`, `lib_patches/shade_s18_v1.diff`,
`work/lin_final_v1.npy`, `work/strip_final_1.5_v1.npz`); `compare_v1_vs_v2.jpg` shows both (top v1, bottom v2).

## Deliverables (this directory)
| file | what |
|---|---|
| `keyframe_f1319_2560x1440.png` / `_8bit.png` | the keyframe v2, 2560x1440, 16-bit PNG (Act III grade, seeded grain) and an 8-bit review copy |
| `keyframe_f1319_alt_1.0pxmm_2560x1440.png` / `_8bit.png` | OPTIONAL alternative framing at 1.0 px/mm (window 2560 x 1440 mm, centred on strip u 2030: oath, death, empty chair, war, burn hole, start of the ruin). Closer to the storyboard camera at f1319 (still mid ease-out, ~1.4-1.7 px/mm if exponential), figures ~135 px tall, stitch rows legible; but the realm and most of the ruin are out of frame and the left end is not lost in darkness. For the client to choose, not a replacement |
| `crops_100pct/c01..c09` | 1:1 crops of the final, no resampling (windows re-laid for the new composition): c01 left end realm + fog, c02 oath table with the king, c03 death panel + border lions, c04 empty chair + war field, c05 burn-through + ruin + fog, c06 gold thread + glint, c07 top-edge bites / fringe, c08 bottom edge wefts + quilts, c09 table edge + falloff |
| `falloff_check.json` | the -2.5 EV proof (flat 18 % plane through the same light transport), re-measured for the v2 rig and pool |
| `compare_v1_vs_v2.jpg`, `iterations/`, `iterations_contact_sheet.jpg` | review material |
| `src/`, `run_all.sh`, `lib_patches/shade_s18.diff` | sources (v1 sources in `src_v1/`); the library is untouched, `src/shade_s18.py` is a COPY of `lib/chron/shade.py` with the patches listed below |
| `work/` | cached resampled panels, strip maps (`_v1` and `_v2`), thread info, the linear frames |

## What changed v1 -> v2, against every critique point

Legend: **applied** = done and checked in the render; **partly** = done to the limit the pipeline allows; **rejected** = not done, with the reason.

### P1 / P0 cloth and figures read as printed paper, not wool on linen (critics 1, 3)
* **applied: oatmeal, not mustard.** Linen chroma x0.48 (wool x0.80), grime tint grey-brown (was orange), brown dying-edge tint greyed, key colour 3300 K tint .08 (was 2500 K .32), cool fill raised (fill_ratio 2.8, was 6; 8000 K). Measured plain ground in the pool (8-bit): v1 (127, 83, 48) G/R .66, B/R .38 -> v2 (100, 75, 51) G/R .75, B/R .51 (the act grade's warm gain #FFE2C4 limits how far this can go without touching the library).
* **applied: thread-scale detail the 1.5 px/mm maps cannot carry** (`src/detail.py`): (a) stitch-row streaks following the thread tangent T by line-integral convolution (rows ~1.7 mm wide, ~10 mm long) modulate wool albedo (+-7 %) and relief (0.14 mm, so the raking light sees the rows); (b) a second long-and-short pass (2.6 x 34 mm, +-6.5 %) breaks the war stripes into rows of different tension / dye lot; (c) OKLab L is quantised into discrete wool lots (step .036, threshold wandering with the row noise), so fills are blends of discrete colours, not continuous-tone gradients; (d) linen slubs, weft barre and stepped dye-lot / washing patches on the ground (+-5-7 % L, bounded so that it reads as linen, not as a texture overlay). All bands are >= 2.7 mm across so they survive the 2:1 down to 0.75 px/mm.
* **partly:** at 0.75 px/mm a 1 mm stitch is below one pixel, so real stitches are never resolved; faces remain painterly at 100 % (see known issues). The alt framing at 1.0 px/mm shows the rows better.

### P1 light is a soft frontal pool, not raking light (critics 1, 2, 3)
* **applied:** key elevation 17 -> 10 deg (key intensity 1.30 to hold the exposure), relief of the cloth raised: soft dunes about x2 (95 mm wavelength), 64 wrinkles (was 26) with 55 % oblique shear wrinkles so that a light from below rakes them, stitch-row relief 0.14 mm, slubs; edge buckling made aperiodic. Cool, desaturated fill in the shadows (see above); plain ground about -0.5 EV lower than v1 (exposure 0.92, key 1.30 at el 10 vs 1.45 at el 17; measured on the oath-left ground); walnut albedo browner / greyer.
* **kept:** the falloff itself (critic 1: good). The pool centre moved 170 mm to the right so that the ruin end (right) sits at about -2.4 EV and the realm end (left) at -2.75 EV instead of -2.8 / -2.55 the other way round: `falloff_check.json`: edge mid-points -2.75 (left) / -2.40 (right) / -2.44 (top) / -2.43 (bottom) vs the pool peak, mean -2.51 EV (vs the frame centre -2.80 / -2.45 / -2.50 / -2.49). Corners -3.55 to -3.7. Still in the light transport, not an overlay.

### P1 torn cloth edge = uniform cream outline, no thickness, no contact shadow (critics 1, 2, 3)
* **applied:** 2-4 mm contact shadow and a wider soft occlusion band on the walnut (`ao_extra`, deeper under lifted edges), the same around the quilts; patchy edge lift (curls on ~40 % of the length, flat elsewhere) instead of a continuous lip; the output filter is no longer Lanczos (its ringing on the cloth / walnut step was a hidden source of the cream outline): Gaussian + bilinear 2:1; a comb of loose warp-yarn ends (groups of 1-5 columns, 45-90 % of the groups, up to 16 mm, grey-tan yarn) outside the cut line and a ragged ~2.4 mm inside it (weft ends of uneven length with dark gaps); cut-line bites are ragged (run-length steps scaled with the bite depth) instead of smooth scallops; the periodic edge buckling is aperiodic.
* **applied (critic 2 P3):** three deeper bites go through the border into the register at mid-strip (u 1030: 92 mm, 1575: 88 mm, 2335: 96 mm) and two bites eat half of the lions (u 2060, 2335); their coloured strands stream off.

### P2 fringe, loose wefts and loops look like vector hairs / straw (critics 1, 2, 3)
* **applied:** new thread generator (`src/threads.py`): tapered strands with per-chunk tone (slubs), undyed yarn is a grey-tan (was straw yellow) and darker, 1/3 fewer clumps, fringe about 40 % shorter, no ring-ended curls (curvature is bounded; total turning clamped), long wefts run roughly along the edge (as a pulled weft does) with gentle S-curves, key coloured strands 1.1-1.9 mm wide (>= 0.8 px), contact shadows 0.60 (was 0.45), sheen term cut from 0.05 to 0.02, 100 stray lint fibres (was 150), thinner and paler.
* **rejected (critic 2): "lengthen curls to 20-30 mm".** Curls are what read as pencil doodles for critics 1 and 3; the long strands are now low-curvature lies. Key strands reach 95 mm.
* **partly:** a few straight fringe clumps still read slightly stiff at 100 % (c08).

### P2 burn-through hole reads as an ink blot (critics 1, 2, 3)
* **applied:** ragged boundary (3 noise scales), 4-6 mm char crust with relief (bumpy, 1.2 mm), dry-carbon sheen (silk BRDF on the crust, tangent along the rim), sparse ash flecks, a 24 mm brown scorch gradient into the cloth, blackened thread stubs inside the hole (threads.py), and the walnut that was under the cloth for years is cleaner / lighter / glossier than the dusty table, with its grain visible (the S14 splice 'burns through to the dark walnut'). Reads as a hole onto wood at 100 % (c05).
* **partly:** no curled relit crust, no loose ash threads beyond the stubs.

### P2 quilts look like UI stickers (critics 1, 2, 3)
* **applied** (`src/quilts.py`, `src/layout.py`): warm drab linen tint (was grey-lilac) with soot / dust darker toward the rim and in the grooves; per-cell random padding (0.7-1.3, a quarter of the cells slumped), puckering dimples, a smooth random warp (+-1.8 mm) and skew per instance, linen slubs on the surface, per-quilt tint jitter; 22 quilts in two coherent fronts closing in from the frame ends and thinning inward as chains of smaller puffs along the bottom margin (overlapping the cloth edge) and over the left top border; no mid-strip singletons (critic 2 vs critic 3 pulled both ways; resolved as chains from the ends); gains 0.40-0.50 (v1 .52-.62) so that the edge quilts are no longer the brightest objects at the frame edge (critic 3).
* **partly:** the stitch rhythm is still the game's sprite; the variation is in the stuffing, silhouette, tone and soot, not in hand-built shapes.

### P2 gold thread and glint (critics 1, 2, 3)
* **applied** (`src/thread_gold.py`, `src/post.py`): the chronicle thread is now a visible, dull, tarnished (bronze, #6E5C3C to #E6B85E) two-ply thread (3.0 mm, ply banding at 2.8 mm, tube relief 1.25 mm) running the whole length on the border rule, with tie-down stitches (drab wool, up to 132 along the strip) where the cloth still holds it; across bites it relaxes 55 % of the way into the notch and follows the torn edge (no taut wire), smooth path (no kinks); it warms and brightens only over the last ~200 mm (the survivor) and runs out of the frame at the right edge unbroken. The glint is moved inside the action-safe area (screen (2344, 522), was (2463, 548)), tiny (~4 px core + thin streak), palette gold: core #F2CB7C (v1 #F1CA8E peach-cream; palette highlight #FCD577), still the global brightest pixel (max gray 190 vs p99.9 138) and below the palette white (#F3E8D0), headroom kept for the f1345 pulse.
* **partly:** the glint is still an authored additive spot on a thread the BRDF renders dull (a 3 mm thread's sparkle cannot be resolved at 0.75 px/mm).

### P3 walnut and table (critics 1, 3)
* **applied:** stronger cathedral figure with plank-to-plank tone variation (0.66-1.28), hand-rubbed lighter patches, dust specks and a dust veil, wax smears, a broad satin lobe in the varnish BRDF (`0.060 ndh^8`), the front edge has a larger roll-off (R 10 mm), a low-frequency wander of the edge line (+-3 mm), 14 knocks, wear on the arris; walnut gain 3.3 -> 3.9 so the table is not a black void; table grain 0.8 deg vs the strip's -3 deg (they cross); table edge moved down so the dead floor is ~14 % of the frame (was ~25 %).
* **rejected: "floor flat 11/255 with a magenta cast".** The floor value (13, 10, 13) is the library's Act III grade black point and lift (#0B0607, shadow tint #1A1620), applied to anything below ~0.003 linear. A floor gradient albedo was added (0.004 + 0.011 e^(-d/70 mm), neutral) but it sits below the grade's lift, so it does not show; neutralising the cast needs a change in `chron.grade` (read-only here) or a brighter floor, which would break the 'dead black' of the table edge.

### P3 composition / framing (critics 1, 3)
* **applied:** strip off the horizontal: tilt -3.0 deg (was -2.0), the table grain / front edge at -0.8 deg so the two cross, the glint end rises; the strip centre-line at y 0 with the diagonal reading lower-left to upper-right; floor reduced.
* **rejected: "crop tighter / lower angle on the strip".** The brief fixes the hold framing at ~0.75 px/mm so that the realm, the oath table, the war and the ruin are all recognisable in one frame, and S18's emotion is 'despair and smallness'. The tighter framing is provided as the optional alt (1.0 px/mm).
* **rejected: scale props on the table (needle, shears).** Procedural props would be the weakest element in the frame and the S19 truck needs the table free.

### P2 micro content (critic 3) and critic 2 P4-P6
* **applied:** the king-shaped void is toned down to the aged ground (v1: a pale wash), with needle holes along its outline (dark 1.3 mm pricks) and 26 loose purple / crimson / gold wool strands lying on the cloth around it; the mint-green mend is now a drab, ragged, rotated darned patch (two mends, oatmeal / grey, 2.4 mm rows); the war field's remaining riders are desaturated (-58 % chroma) and darkened so they do not look freshly stitched; the three tree dividers are now different (mirrored, re-banded) instead of clones.
* **rejected:** panel seams: they are the baked panel boundaries; hiding them needs a re-bake (they are faint at 100 %).

### P7 (critic 2) content / camera deviations, recorded for the client
See Deviations below (unchanged in substance from v1, now with the alt framing as an option).

### Ruin end legibility (critic 1 separate note)
* **applied (without a rim-light cheat):** pool centre shifted right (ruin end -2.4 EV), the grime darkening toward the ends kept but greyed; c05 shows the city, towers and flame tongues. No local light added.

## Pipeline (all frame-deterministic, numpy / cv2 / numba, no AI generation)
1. `prep_panels.py`: the 5 px/mm mip (L1) of the baked MapSets (`k1_realm`, `p1_oath`, `p1_oath_ground`, `p3_death`, `war_ground`, `p6_ruin`) area-resampled to 1.5 px/mm.
2. `build_strip.py`: strip-local canvas (4100 x 400 mm), continuous border band, register sections realm | T1 | p1 | T2 | p3 | T3 | p1' | war | p6 | T4; v2: the dividers are three different trees.
3. `finish_strip.py` (+ `detail.py`): ageing, oatmeal grade, grime, stitch-row LIC detail and wool lots, slubs / barre, riders faded, void toned + needle holes + stray-strand anchors, burn-through (crust, scorch, stubs), mends, wrinkles / dunes / buckling, patchy edge lift, comb of yarn ends, ragged cut line, bites.
4. `world.py` + `walnut.py` + `geometry.py`: strip -> world (S-bow, tilt), procedural walnut, table edge, contact shadows, clean walnut under the hole, pool, rig.
5. `thread_gold.py`, `quilts.py` + `layout.py`, `shade_s18.py` (relight), `threads.py`, `post.py` (glint, bloom), `chron.grade` act III (exposure 0.92, grain .012 seeded 1319).

Library patches (`lib_patches/shade_s18.diff`, unchanged from v1 except one line): (a) the key-pool `kmap` scales every directional light and the fill (real light-level falloff); (b) `brdf` takes a per-pixel `spec` map (walnut sheen, gold-thread tarnish); (c) shadow-march range 6.5 mm of relief with exposed penumbra; v2: (d) a broad satin lobe in the walnut branch.

Key v2 knobs (env, defaults are the delivered values): `F_EL` 10, `F_KEY` 1.30 (`world.rig_last_light`), `F_FOLD` 1.3, `F_LICREL` 0.14 (`finish_strip`), `F_THETA` -3.0 / `F_YC` 0 (`geometry.GEO`), `F_TABLE_ANGLE` -0.8, `F_EDGE` 690, `F_GLINT` 7.0, `F_GLINT_U` 3262, `F_SURV0` 3120, `F_EXPOSURE` 0.92, `F_SCREEN` 0.75, `F_UC` 1830, `F_TAG` _v2.

## Numbers
* Working density 1.5 px/mm (2.0x the 0.75 px/mm screen: supersampled shading). Strip build 14 s, finish ~55 s (peak 2.1 GB), frame ~50 s (peak RSS 3.04 GB), 2 numba threads, nice 5; alt framing 40 s. Re-render diff 0.0.
* Frame: max gray 190 (the glint), p99.9 138, p99 124, 0.0003 % above 235; 16-bit vs 8-bit mean abs diff 0.25 (8-bit levels). Plain linen at the pool centre (100, 75, 51), left end cloth (35, 25, 20), right end (30, 19, 16).

## Deviations from the brief / storyboard (please read)
1. Framing: the S18 hold framing (0.75 px/mm) as briefed. In the storyboard camera schedule f1319 is still in the ease-out (about 1.4-1.8 px/mm if exponential); the optional alt frame is at 1.0 px/mm.
2. Strip content / order: realm | T1 | oath | T2 | death | T3 | empty chair | war | ruin, SINE HEREDE left out (3.74 m, cropped about 160 mm at each end). The window is centred on the war / oath part, not on the 'four towns' section 12 that S17 pulls back from; the S19 truck to the strip's end runs over sections that are not drawn here. The three tree dividers are procedural (not the kit trees).
3. The long plate is an assembly of 5 px/mm mips resampled to 1.5 px/mm, not the planned 1.0 / 0.75 mips. For the film use 1.0-1.25 px/mm.
4. Not the R25 fibre / curve renderer: threads are an own generator (screen-space, 2x supersampled, lit with the same rig); they get a contact shadow only. The pool centre is 170 mm right of the frame centre (see above): the edge mid-points are -2.75 / -2.40 EV, the mean -2.51.
5. The walnut is procedural; the glint is an authored additive spot.
6. No ember rim anywhere (the embers died on f1292); the 'pre-dawn' lift of f1372 is not in this frame.

## Known issues / limits (honest critique of v2)
* Faces and robes are still painterly at 100 %: the stitches are sub-pixel at 0.75 px/mm; the rows / lots / relief help but this is not photographic embroidery. The alt framing shows more.
* The quilts' stitch rhythm is the game's sprite; the gain is 0.40-0.50 so they read as dead fog, which makes the left cluster close to illegible in the darkest zone.
* A few fringe clumps still read stiff / straw-like where several overlap (c08 centre); the comb of yarn ends is subtle at 0.75 px/mm.
* The floor cast (13, 10, 13) is the act grade (rejected above); the table edge is still a thin 3 px roll-off with knocks.
* The glint is authored; the thread's tie-down stitches are 1.3 mm wide and only read as ticks.
* The fray is a static model (TOP_BITES / BOT_BITES, thread density), nothing is time-parameterised.
* Realm end: the register is extended by a mirror pad (hidden by fog); the p1 / p3 / p6 panels carry flipped copies of the realm / war border bands.
* v1 `work/strip_raw_1.5.npz` was overwritten by the v2 build (new dividers); `work/strip_final_1.5_v1.npz` and `work/lin_final_v1.npy` are the v1 strip and linear frame. To rebuild v1 exactly run `src_v1/` in a copy.

## Reproduce
```
cd aaa/prod/f1319 && ./run_all.sh        # prep, build, finish, render, crops, falloff check, alt framing (~5 min)
```
