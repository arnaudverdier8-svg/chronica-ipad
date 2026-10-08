# CHRONICA keyframe f1319 (S18 'edges'): the chronicle fraying into darkness

Status: production-proof candidate. Everything below was checked by looking at the renders (full frame, nine 100 % crops, 17 iterations; the
history is in `iterations/` and `iterations_contact_sheet.jpg`). Bit-exact reproducible (re-render diff = 0 on the linear frame).

## Deliverables (this directory)
| file | what |
|---|---|
| `keyframe_f1319_2560x1440.png` | the keyframe, 2560x1440, 16-bit PNG (Act III grade, grain, seeded) |
| `keyframe_f1319_2560x1440_8bit.png` | same, 8-bit review copy |
| `crops_100pct/c01..c09` | 1:1 crops, no resampling: c01 left end (realm + fog), c02 oath table with the king, c03 death panel + border lions, c04 empty chair + start of the war field, c05 war field / burn-through / ruin / fog, c06 gold thread + glint, c07 top-edge fringe, c08 bottom edge weft threads + quilts, c09 table edge + falloff |
| `falloff_check.json` | the -2.5 EV proof (flat 18 % plane through the same light transport) |
| `iterations/`, `iterations_contact_sheet.jpg` | v1, v4, v6, v9, v12, v17 and the final, side by side |
| `src/` | all sources (see below); `run_all.sh` reproduces everything |
| `lib_patches/shade_s18.diff` | the only change to library code: `src/shade_s18.py` is a COPY of `lib/chron/shade.py` with the patches below. The library itself is untouched (read-only), `/home/user/chronica-ipad` is untouched |
| `work/` | cached resampled panels (so the frame does not depend on `prod/f899/maps` staying unchanged), strip maps (raw / final), thread and fray info, the linear (pre-grade) frame `lin_final.npy` |

## What the frame shows (checked against the keyframe text)
* A long thin strip (~400 mm high, ~3.4 m in frame) on a dark walnut table, tilted 2 deg with a gentle bow (the dutch of Act III), rising to the right.
  Both ends run out of frame into the -2.5 EV zone and are partly swallowed by fog quilts.
* Recognisable earlier scenes in miniature, left to right: the realm (capital, road, fields), the oath table with the king, the death panel, the oath
  table again with the king-shaped void (empty chair, ghost of the unpicked work), the war strip as the needle-hole field (sky bands, figure
  footprints), the burn-through hole at the war|ruin join (real char rim, the walnut shows through), the ruin (p6, scorched margins).
  Realm-end and ruin-end are partly under fog and in the darkest light, as they must be at the frame edges.
* Borders unravelling: the upper border (flowers, red and blue lions, couching bars) is eaten in stair-stepped weft runs, up to 70 mm deep at the far right
  and 52 mm through the lions at x ~ +675 mm; cut warp ends splay as fringe clumps (3 855 threads); 434 peeled weft / curl threads hang off the edges and lie on the table; 1 237 coloured wool
  strands (lion red / blue, flower colours) come out of the motifs; 150 lint fibres lie on the walnut (c07, c08). 5 676 threads in all.
* Fog: the game's quilted cloud kit as 2.5D appliques (padding height from the stitch cells, grooves on the running stitch, rounded rims), clusters at both ends,
  small puffs creeping over the margins mid-strip, a cluster closing from below at the right. They take the same relight, AO and soft shadows.
  The top border and the thread stay clear on the right.
* The hearth is out: a last warm glow low from the bottom edge (az 250, el 17, 2500 K tinted .32; effective key:fill ~7:1 on a flat surface, the fill is a cool 8500 K), a faint rim from the
  upper right. No candle, no ember rim on the char (embers gone).
* Physical falloff, not an overlay: the irradiance pool `E = (1 + 2.175 d^2)^-1.5` (a point source over the table behind an anamorphic aperture, d = 1 at
  the frame-edge midpoints) scales key, rim AND fill inside the BRDF, the thread layer and the bounce. `falloff_check.json` relights a flat grey plane through
  the same rig: frame-edge midpoints -2.55 (left), -2.82 (right), -2.52 (top), -2.48 (bottom) EV vs the frame centre, mean -2.6; corners -3.6 to -3.9.
* One tiny gold glint at the far right: the chronicle thread (a continuous two-ply couched thread on the border rule, tarnished and dull along its length)
  has outlived the cloth under it; where the border has frayed away it hangs free, wanders across the dark walnut and runs out of frame unbroken. The only
  bright stretch (the survivor, u > 3250 mm) carries a single specular catch: ~4 px core elongated along the thread, thin slide streak, peak 12 linear
  (graded core ~#F4CE9F, deliberately below the palette ceiling #FFF3D6 which is kept for the f1345 pulse), at screen (2463, 548).

## Pipeline (all frame-deterministic, numpy / cv2 / numba, no AI generation)
1. `prep_panels.py`: the 5 px/mm mip (L1) of the baked MapSets `k1_realm`, `p1_oath`, `p1_oath_ground` (king unpicked, goblets/candles reduced to needle holes),
   `p3_death`, `war_ground` (aaa/prod/f899/maps, the needle-hole field: figures gone), `p6_ruin`, area-resampled to 1.5 px/mm (T by doubled angle, mat by class fraction).
2. `build_strip.py`: strip-local canvas (u along, v across; 4100 x 400 mm): continuous border band tiled from the realm / war border bands cut at
   quiet columns and flipped alternately; register sections realm | T1 | p1 | T2 | p3 | T3 | p1' | war | p6 | T4 (charred); procedural interlace-tree
   dividers (banded house colours); thread centre-line, tarnish map and tie positions (the thread is NOT painted into the strip, see 5).
3. `finish_strip.py`: Act III ageing (`chron.ageing.apply_age`, dye_k 1.55, linen_k .8, fox x1.7), large-scale grime deeper toward both frame ends, chroma -10 %,
   brown dying edges, burn-through hole + char rim + scorch, scorched p6 margins, two faded darned mends, folds / creases / edge buckling (relief for the raking
   light), edge lift, and the frayed cloth boundary `cloth` alpha (weft-pitch stair steps, authored bites in `TOP_BITES` / `BOT_BITES`).
4. `world.py` + `walnut.py` + `geometry.py`: strip -> world (gentle S-bow, -2 deg tilt) in row bands; procedural walnut (planks, ring figure with arches, latewood
   lines, pores, seams with bevel highlight, scratches, water rings; generated at 1.0 px/mm and resampled, albedo gain 3.3); the long front edge of the table
   (rounded 7 mm bevel that catches the light, then the dark floor).
5. `thread_gold.py`: the gold thread painted into the world maps along the strip's rule; where the cloth has receded from under it, it lifts off the cloth line and
   wanders on the walnut (`gap` term).
6. `quilts.py` + `layout.py`: 20 quilt appliques from `assets/tex/table_clouds` (flattened albedo, desaturated, gain .52-.62), placed in strip coordinates.
7. Relight (`shade_s18.py`, patched copy of `chron.shade`) at 1.5 px/mm with the physical pool, soft shadow penumbra 0.9 mm, one-bounce glow from the strip onto
   the walnut (computed at 1/4 resolution), Lanczos warp to 0.75 px/mm.
8. `threads.py`: fringe clumps, peeled wefts, coloured motif strands, stray lint: polylines in strip space -> table, lit per thread with the same rig and pool
   (Kajiya-Kay diffuse, rim, fibre sheen), 2x supersampled premultiplied-over AA lines, soft contact shadows, occluded by quilts.
9. `post.py`: glint, thresholded optical bloom (thr 0.9, only the bright strip and the glint); `chron.grade.grade` act III, exposure 1.0, grain .012 seeded 1319.

Library patches (`lib_patches/shade_s18.diff`): (a) the key-pool `kmap` now scales every directional light (key and rim) and the fill, so the falloff is a real
light-level falloff; (b) `brdf` takes a per-pixel `spec` map: walnut = anisotropic satin sheen across the grain + gloss lobe (chatoyance, worn varnish), and the
metal strength of the gold thread (tarnished stretches); (c) shadow-march range 6.5 mm of relief (quilts) instead of 2.2 mm; penumbra `soft` exposed.

## Numbers
* Working density 1.5 px/mm (2.0x the 0.75 px/mm screen: supersampled shading, Lanczos down); world 5170 x 2928 px. Quilts / thread / fringe at the same density or finer.
* Time: strip prep ~70 s (prep 25, build 12, finish 35), frame ~50-60 s (walnut 8, relight 12-19, threads / post ~15). Peak RSS 3.0 GB (band-wise strip->world
  remap, thread painting restricted to its row band, bounce at 1/4 res, walnut at 1.0 px/mm). Output frame is not clipped: p99 gray 135, max 212, 0 % above 235.
* At 1.0 px/mm the same frame takes ~35 s and 2.7 GB (used for iteration); the 1.5 px/mm version shows the couched fills, weave of the dark panels and stitch grooves of
  the quilts at 100 % (compare c02, c03 with `iterations/v12.jpg`).

## Deviations from the brief / storyboard (please read)
1. Framing: this is the S18 hold framing (0.75 px/mm). In the storyboard's camera schedule f1319 is still in the ease-out of the pull-back (scale ~1.4-1.6 px/mm
   if the move is exponential); the brief for this keyframe asked for the strip at ~0.75 px/mm, which is what is rendered.
2. Strip content / order: at 0.75 px/mm the 3.41 m window cannot hold the whole frieze (realm 800 + ... + towns 780 = ~5.6 m), so the strip is the frieze section
   order realm | T1 | oath | T2 | death | T3 | empty chair | war | ruin with the SINE HEREDE strip left out (3.74 m, cropped 160 mm at each end by the frame).
   The window is therefore centred on the war / oath part of the frieze, not on the 'four towns' section 12 of the layout. The production S18 must either use the
   same cut or accept that realm and oath are out of frame; the S19 truck to 'the strip's end' then runs over the ruin, forest and towns sections which are not drawn here.
   The sections are the baked ones: realm = k1 kit (its 252 mm register is extended by a reflection to the 322 mm register, hidden under the fog), oath / death /
   ruin = p1 / p3 / p6, war = war_ground. Panels p1 / p3 / p6 had no border: they carry the border band of the realm / war sheets (flipped copies).
   The T1-T4 dividers are my own simple procedural trees (not the planned kit trees), 60 mm wide, fine at this scale, not at F1.
3. The long plate is not the production 'assembled from every section plate with 1.5 / 1.0 / 0.75 mips' of the pipeline: it is an assembly of the 5 px/mm mips
   resampled to 1.5 px/mm for this frame. For the film, build the strip at 1.0 / 1.25 px/mm mips (relight 3-10 s per frame) and cache it.
4. Not the R25 fibre / curve renderer: the fringe, wefts and strands are an own thread generator (strip-space polylines, 2x supersampled, lit by the same light
   function) because the library fibres start at 4 px/mm. They do not receive shadows from the cloth relief (only a contact shadow) and are occluded only by quilts.
5. The walnut is procedural (no R25 wood module exists in `chron`); the bounce is a cheap one-bounce term; the glint is an authored additive specular spot on
   a thread that the BRDF itself renders dull (the BRDF at 0.75 px/mm cannot resolve a 2.5 mm thread's sparkle).
6. No ember rim anywhere (the embers died on 'dark' f1292); the char is black-brown and raised. The 'bass' pre-dawn cool lift of f1372 is not in this frame.

## Known issues / limits (honest critique of the final)
* The quilts read slightly like the game's UI sprites (even stitch rhythm, uniform padding); they are tonally matched (dull, desaturated) but they are the most
  'designed' element. Fine for the keyframe, may want hand-built variants for the film.
* Fringe clumps at the top edge can read as straw / hay where several overlap (c07); density and brightness are parameters (`dens_scale`, the 0.72 lit factor).
* The realm end shows the mirrored fields under the fog; the ruin (p6) sits in the darkest -2.8 EV zone and is barely legible at normal viewing, by design of the falloff.
* The burn hole is a noise-warped ellipse with a char rim and scorch (no curled relit crust, no loose ash threads).
* The two mends are small pale / grey-green rectangles with darning rows; at 0.75 px/mm they read as patches, not stitching.
* The walnut has no wear beyond scratches / water rings and a modest sheen; the table edge is a straight line (a carved apron was not attempted).
* The frame is a still: the fray is a static model (bite depth, thread density and u-range are parameters for animating it, but nothing is time-parameterised yet).

## Reproduce
```
cd aaa/prod/f1319 && ./run_all.sh        # prep, build, finish, render, crops, falloff check (~5 min)
F_EXPOSURE=1.0 F_GLINT=12 F_GLINT_U=3415 F_TABLE_EDGE=1 python3 src/render_f1319.py 1.5 final   # knobs used for the delivered frame
```
Key parameters: `geometry.GEO` (uc 1830, yc 36, theta -2 deg, S-bow 20 mm / 2700 mm), `world.POOL` (cx -50, cy 30, a 2.175), `world.TABLE_GAIN` 3.3, `rig_last_light`
(az 250, el 17, 2500 K tint .32, key_i 1.45, fill 8500 K ratio 6, rim 35 deg / 9 deg .30, k_env .75), `finish_strip.TOP_BITES / BOT_BITES`, `layout.QUILTS`.
