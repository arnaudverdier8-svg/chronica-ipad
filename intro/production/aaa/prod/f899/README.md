# CHRONICA keyframe f899 (S12 'years'), v2: ten soldiers risen out of the cloth, frozen while a century passes

Production-proof stage, client approval pending.  v2 answers the three-critic review of the first proof (scores 5.5 / 5.5 / 4).  The previous proof is kept
with a `_v1` suffix next to every v2 file (`out/keyframe_f899_2560x1440_v1.png`, `out/crops_v1/`, `out/layers_sheet_v1.jpg`, `out/iterations_v1/`, `README_v1.md`,
`shot_f899_v1.json`, `run_all_v1.sh`, `src_v1/`, `maps_v1/`, `blend/slips_v1/`, `work/plate_v1/`, EXR passes `work/ev_v14/`).

Deliverable: `out/keyframe_f899_2560x1440.png` (8-bit sRGB, TPDF-dithered, 1.2 % grain) + `out/keyframe_f899_2560x1440_16bit.png` (same grade, 16-bit, for the
video encode); 100 % crops `out/crops/` (+ `review_sheet.jpg`); layer breakdown `out/layers_sheet.jpg`; iteration history `out/iterations_sheet.jpg` and
`out/iterations/`; numeric checks `out/qa_report.json`.  The comp is deterministic: `src/comp.py work/ev_v2 ...` reproduces the keyframe bit-exactly from the kept EXR passes.

## What is in the frame (v2)
* **Camera**: pinhole, 22 deg oblique, 3 deg dutch in-camera, aim (330, 158) mm, 4.5 px/mm, f/16 focused at 850 mm.  The aim moved 26 mm up the cloth so the whole
  gold chronicle thread, the hem and a 180-px wedge of the walnut table sit in frame (the dutch makes the table wedge grow to the right); the sheet is 660 x 345 mm
  (every v1 x shifted by +30 mm so the rolled frame never leaves the cloth).
* **Composition**: one clash, not a parade.  Ten front-rank slips (5 Legion crimson facing right, 5 merchants' blue facing left) in two ranks: the hero rank at 1.0 x
  (legionary x man-at-arms, shield to shield, centre-left third; knight with lance at the left; horse archer / spearman / mercenary at the right) and a back rank at
  0.83 x.  Slips overlap on screen and in the sheet (each is stitched whole, the occlusion is reset per slip), their yaw is small (3-5 deg) so every footprint registers
  with its slip.  Behind them two flat ranks (0.58 x / 0.42 x, less relief) stand on two rolling hillock mounds.
* **Figures** are still the game's strike-pose cards re-embroidered as real strands (laid + couched fills, split-stitch faces, couched-gold crosses), but the outline is
  now a THIN, TONAL (darker tone of the adjacent fill), BROKEN stem stitch instead of a dark all-round ink line; the felt backing is 1.1 mm of undyed wool felt mixed with the
  local fill colour, hard-edged, lit by the hearth.  The soft 0.3 mm 'wool halo' of v1 (the dark halo the critics saw) is gone; the fuzz is the R25 fibre set with 4x edge boost.
* **Needle-painted dusk sky** (`scene_war.build_sky`): 76 mm of long-and-short split stitch in three zones (stitch length 15 / 10.5 / 7 mm, wavy interleaving seams), each
  stitch picks its shade from a woad-grey -> grey dusk -> madder -> terracotta -> pale-glow gradient displaced by row-correlated noise (rows ~0.85 mm differ, each wanders
  over ~14 mm), eleven lens-shaped laid cloud / glow bars lighter than their surroundings, no regular couching ticks.  Chroma <= .125, no violet.
* **Ground**: turf lines (couched earth bands) under each front figure's feet, tuft CLUSTERS (127 tufts in 30 clumps + near the feet, 2.2-6.6 mm, varied lean / blade
  count / colour; v1 had ~250 stamped glyphs), irregular foxing (domain-warped blots, darker core + yellow-brown halo, clustered along tidelines and the hem), wicked pale tea-brown tidelines.
* **Footprints** (`ghost_v2.py`): protected linen colour-matched to the surrounding aged linen (slightly fresher, no cool slab), needle holes 0.20-0.42 mm with a raised lip and
  a red-brown pigment bleed around 40 % of them, variable spacing, red-brown underdrawing of each slip's stem paths.
* **Light**: 2200 K hearth key from the bottom edge, about -29 % against v1 (Eevee key 2.1 -> 1.9 at a wider 5 deg source, then x0.78 in COMP as `hearth_gain`; pooled with irregular static
  flicker lobes and a height-dependent fall-off up every standing body; mean OKLab L .468 -> .419); warm radiosity (12 % of the hearth stays in the shadow, in the hearth's colour); shadow penumbra grows with distance from
  the caster (Eevee's area light + a distance-dependent blur) and thins out with distance; a 5200 K dusk fill.  **The century's arc**: a pale 7500 K light with a ragged,
  slightly curved leading edge sweeping the left third, a bleach front that trails it (dyes toward grey-white / pink-grey, linen toward ivory), applied identically to the plate
  (albedo, OKLab) and to the slips (screen space), the gold thread tarnishing from the left (bronze) to fresh gold at the right.
* **Grade**: Act III with sat x0.88, a split tone (woad-cool in the deep shadows, a trace of warm in the highlights), halation on the hottest warm highlights, a lens vignette,
  TPDF dither before the 8-bit quantise.
* **Tethers**: three long, thick (0.62-0.82 mm), clearly curling tethers per slip (hanging from the lower edge and lying on the cloth), plus 21 fine ones, in the parent strand's colour with sheen.

## Pipeline (all in `src/`; one command: `run_all.sh TAG [eevee_scale] [taa] [plate_scale]`, steps skippable with `SKIP="bake export plate eevee comp"`)
1. `scene_war.py`  bake `maps/war` + `maps/war_ground` (bkit Canvas -> RECORD -> needle order -> exact replay), 6600 x 3450 px at 10 px/mm, ~4 min, ~3.3 GB.
2. `export_slips.py`  slip textures, meshes, tethers, poses -> `blend/slips/` (~20 s).
3. `render_plate.py`  R25-F rectified relight of `war_ground` (hearth / cool / fill passes + the metal mask), aged inside the edit (folds -> library dye age -> irregular fox / tide / bleach / footprint match -> tarnish front), warped by the camera homography (~80 s full, 40 s half).
4. `eevee_scene.py`  9 Eevee passes (slips / plane / planeclean x hearth / cool / fill), linear EXR + Z; 2560 x 1440 at 40 TAA took 12.4 min with the machine shared.
5. `comp.py`  plate x shadow ratios (+ bounce, penumbra, fade) + pooled slips + bleach + R25 fibres + gold gleam + DOF + halation + vignette + split-tone grade (~25 s).
   `qa.py`, `make_crops.py src/crops_v2.json`, `make_layers.py` produce the checks and sheets.  `layout_preview.py` places slips in seconds (standing cards projected with the shot camera); `preview_ground.py` is the ground-only look-dev composite.
Reproducibility: `shot_f899.json` holds every shot parameter; EXR passes of the final render are kept in `work/ev_v2/`.

## Review triage (what was applied, what was not, and why)
| review point | v2 |
|---|---|
| Sky = brick wall / ticks / flat bands (all three) | rebuilt: needle-painted gradient, three stitch lengths, feathered rows, cloud bars, no ticks; hills = closed mounds with hatched interiors and jittered couching |
| Slip edges: soft dark halo, sticker outline (c1 P1, c3 P2) | halo removed, tonal broken thin outline, hard felt rim, edge fibres x4; faces NOT re-embroidered (see known issues) |
| Light on slips / hearth shape (c1 P2) | height fall-off, flicker lobes, sheen up (wool roughness .72, sheen .7), gold gleam; hearth sinks (-25 %) |
| Mechanical fills (c1 P3) | sky + hills + border bars (jitter 7-8 deg, spacing 5-6 mm); the flat far-rank figures keep the v1 stitching with 28 % less relief |
| Shadows flat olive / scissors / smears (c1 P4, c2 P5, c3 P4) | warm radiosity, distance-dependent penumbra and fade, wider source, cut-outs stay recognisable |
| Footprint slab / holes (c1 P5, c3 P8) | colour match, bigger holes with lips + bleed, yaw cut to 3-5 deg so each ghost registers with its slip |
| Ground dressing (c1 P6, c3 P6) | clustered varied tufts (-50 %), turf lines, irregular fox / tide |
| Border soft (c1 P7) vs 'more DOF falloff' (c2 P7) | the two conflict; border made crisp (f/16, focus 850: Laplacian var 24 -> 93), the oblique is carried by the table wedge + dutch + aerial haze, not by extra blur |
| Tethers invisible (c1 P8, c2 P3, c3 P3) | three hero tethers per slip, 2x thicker, strand colour, sheen |
| Grade too orange / one tint (c1 P9, c2 P4, c3 P9) | Act III sat .85 x 0.88 = .75 (v1: .85 x 1.15 = .98), gamma .92 (v1: x1.3), split tone, hearth -29 %; lower linen OKLCH measured L .41-.43, C .059-.060, h 45-49 (the review measured v1's lower linen at L .57-.66, C .104-.113, h 54-59); mean OKLab L .468 -> .419 |
| Ageing low impact (c1 P10, c2 P1, c3 P9) | arc with leading edge + bleach front + tarnish gradient (see above) |
| Gold thread missing (c2 P1) | aim moved up, whole thread in frame, gleaming at the fresh (right) end, bronze at the tarnished (left) end |
| Parade not clash (c2 P2, c3 P5) | ten slips, two ranks, hero pair shield to shield, overlaps, one focal point |
| Stand-up not legible (c2 P3, c3 P3) | thinner hard rim, tethers, contact / penumbra shadows, small yaw so the footprint reads under each slip; the 22 deg oblique still foreshortens a 70 deg slip to ~66 % |
| Cloth too clean (c3 P7) | fold amplitude 0.55 -> 0.85 mm, creases x1.3 (still subtle) |
| Border flowers cloned (c3 P10) | heights 36-49 mm, leans varied, two more sprigs; still the same sprig builder |
| Reviewer 3 'mirrored reused riders / blank faces' | partly: tint, dye lots and seeds vary per slip, but the game cards are what they are |
| 'sixteen slips / six keyed ageing states' | not done: ten slips, one ageing state (the keyframe), flagged for integration |

## Library patches / copies (the library `aaa/lib` was NOT modified)
* `src/bkit/` is a copy of `prod/kit/bkit`: absolute paths; `motifs.hill` gained `bar_jitter`, `interior_depth` (closed mound), `interior_style/L`; `diag_bar` couches at 5.2 mm with 7 deg jitter.
* `scene_war.py` replaces `chron.motifs.panel._ghost` at runtime with `ghost_v2.ghost_v2` (library file untouched).
* `figure.py` (tonal / broken outlines, `hamp_mul`), `export_slips.py`, `plate.py` (irregular ageing, bleach, ghost match, tarnish front), `arc.py`, `ghost_v2.py` are new / extended modules using only public library calls (`apply_age` is now called from `render_plate.py` before the art-directed ageing).

## Known issues (honest list)
1. The figure art is the game's cartoony card art; faces and small devices are low-detail (no re-embroidered eyes / brows) and the re-embroidery is still soft at 4.5 px/mm on a 10 px/mm bake.
2. The 70 deg stand-up is seen only 22 deg from the vertical, so slips are foreshortened to ~66 %; the lift reads through shadows, footprints, tethers and the rim, not parallax.
3. Ten slips and one ageing state, not the storyboard's sixteen slips and six keyed R25 ageing states.
4. The lower ground is still orange-brown (OKLCH L .41-.43, C .06, h 45-49) because it is hearth-lit; the right third of the frame is dim and the right-hand hearth pool reads flatter than the left.  The overall brightness only fell 10 % (mean OKLab L .468 -> .419), less than the review's 'cut the key 25 %' suggests once the fill and the cool arc are counted.
5. Turf lines read as slightly flat, grey-brown lozenges under the feet; the tuft glyph is still a 'v' stroke family, only varied.
6. The slips' hinge has no dedicated crease: contact is Eevee's AO / contact shadow only; slip-feet end in flat dark clipped soles.
7. The ratio-map shadow transfer fills the pixels under the slips from their neighbours (the diagnostic ground image in `layers_sheet.jpg` shows black blobs there; they are covered by the slip alpha in the final).
8. The wool fuzz on the slips is an R25 fibre set splatted in COMP, tethers are authored tube curves (no physics); the gold gleam is a screen-space mask x warm term, not the library's metal BRDF (which renders the thread dark at the dim right end).
9. The far-left corner stacks two knights on the same hill; the bleach on the left makes the far ranks nearly ghost-white (intended, but strong).
10. Grade and exposure (0.50, sat x0.88) are art-directed for this frame; check against f669 / f1319 in the integration pass.

## Costs
Bake 3.9-4.1 min (~3.3 GB), export 20 s, plate 80 s full (1.5 GB), Eevee 12.4 min at 2560 x 1440 / 40 TAA (0.7 GB), comp 25 s.  Three full-resolution chains (two with a re-bake), two half-resolution chains, two test bakes and a few ground-only previews were run; temporary EXRs of the intermediate renders were deleted.  The last change (hearth_gain 0.78) was a COMP-only re-run (25 s) on the kept passes.
