# CHRONICA keyframe f899 (S12 'years'): soldiers risen out of the cloth, frozen while a century passes

Production-proof stage, client approval pending. Deliverable: `out/keyframe_f899_2560x1440.png` (8-bit sRGB, Act III grade, 1.2 % grain),
100 % crops in `out/crops/` (+ `review_sheet.jpg`), layer breakdown `out/layers_sheet.jpg`, iteration history `out/iterations/` and
`out/iterations_sheet.jpg`, numeric checks `out/qa_report.json`.

## What is in the frame
* Camera: pinhole, 22 deg oblique over the war strip, 3 deg dutch (in-camera), aim (300, 184) mm on the sheet, 900 mm away, 4.65 px/mm at
  the aim point (F1 framing), f/9 with a depth-of-field falloff from the analytic cloth depth + the slips' Z pass.
* The war strip is a procedural Bayeux-kit sheet (`src/scene_war.py`): madder / dusk / woad-grey banded sky in laid + couched wool (no
  violet), two hillock ridges, two flat ranks of figures (idle / strike cards, alternating colours), grass tufts on bare linen, the upper
  border with hem, nail holes, the whole-width gold chronicle thread, the two confronted game lions and sprigs.
* Seven front-rank figures (Legion crimson facing right, merchants' blue facing left; legionary x2, knight, mercenary, man-at-arms,
  spearman, horse archer, archer) are **re-embroidered from the game figure cards** (`src/figure.py`): strike poses, realm-tinted with the
  game's own tint formula, then re-segmented and re-stitched as real strands (laid + couched fills, split-stitch faces, stem-stitch outlines
  from the card's cord mask, couched-gold cross on the Legion shields). No sprite pixels, no cream die-cut border. Purple trim is re-dyed
  to deep madder / woad (purple belongs to the king).
* Each front figure is its own record group (`slip0..6`). The `war_ground` MapSet is the same sheet WITHOUT them but with their footprints:
  protected linen, needle holes at the real strand ends (0.8 mm Poisson spacing), red-brown underdrawing of the outline (never dark silhouettes).
* The slips are exported from an exact replay of their own stitches (`src/export_slips.py`): albedo + high-pass tangent normal + material map at
  10 px/mm, displaced mesh (low-pass height as Z, boundary snapped to the alpha contour) with a 1.4 mm felt backing + rim in the edge-strand
  colour, hinged at the feet and stood up to 68-72 deg (per-slip yaw +-6..17 deg). 21 snapped tethers per slip (thread tubes, 0.36-0.5 mm
  radius, parent strand colour): stubs hanging from the lower edge and curling, cloth-side stubs curling around the needle holes, a few still
  taut. Rendered as Eevee (Blender 4.0.2, EEVEE legacy, 32 TAA) displaced meshes (pipeline 7.5).
* Light: 2200 K hearth sun from the bottom edge (az 240, el 24) casts the long up-frame shadows; a pale 7500 K daylight arc comes from the left
  (az 190, el 12) with its own pool (the century's single arc begins); dusk fill. Pools are applied per light in COMP (screen space) so
  plate and slips share them exactly.
* Ageing: R25 `apply_age` (dye fade, linen yellowing, protected ghost linen stays fresh) + art-directed foxing / tideline gain, strongest at the
  left (bleach front) and the hem; gold thread tarnished toward `#7A5A2A` (50 %).
* Table: the walnut table shows above the cloth's top edge at the right (dutch).

## Pipeline (all scripts in `src/`, one command: `run_all.sh TAG [eevee_scale] [taa]`, steps skippable with `SKIP="bake export plate eevee"`)
1. `scene_war.py`  bake `maps/war` and `maps/war_ground` (bkit Canvas -> RECORD -> needle order -> exact replay), 6000 x 3800 px at 10 px/mm, ~4 min, ~3 GB.
2. `export_slips.py`  slip textures, meshes, tethers, poses -> `blend/slips/`.
3. `render_plate.py`  R25-F rectified relight of `war_ground` for hearth / cool / fill (view-dependent terms use the real camera position), warped
   by the exact camera homography (`camera.py`, `plate.py`) -> `work/plate/*.npy`.
4. `eevee_scene.py`  9 Eevee passes: slips (transparent) / plane (white shadow catcher with slips + tethers) / planeclean, each for hearth, cool,
   fill; linear EXR + Z, ~10 min at 2560x1440 / 32 TAA.
5. `comp.py`  plate x shadow ratio (slips masked and filled, per light) + pooled slip passes + R25 fibres on the slips (`slip_fibres.py`) +
   0.3 mm wool halo + sharpen + aerial-perspective haze + bloom + vignette + DOF + one shared grade (`chron.grade`, Act III with gamma x1.3, sat x1.15,
   exposure 0.44). `qa.py`, `make_crops.py`, `make_layers.py` produce the checks and sheets.
Reproducibility: `shot_f899.json` holds every shot parameter; EXR passes of the final render are kept in `work/ev_v14/` (re-comp in ~20 s).

## Library patches / copies (the library `aaa/lib` was NOT modified)
* `src/bkit/` is a copy of `prod/kit/bkit` with the two path constants made absolute (KIT / AAA, `elevation.py` AAA).
* `scene_war.py` monkey-patches `chron.motifs.panel._ghost` at runtime to give the group footprints their underdrawing from the stem paths of
  each slip and a denser needle-hole spacing (library file untouched).
* `figure.py` and `export_slips.py` are new modules (card re-embroidery, slip export); they use only public library calls.

## Iterations (visual, 15 renders; `out/iterations_sheet.jpg`)
v1 first full chain (huge cardboard-sprite slips from 8 px/mm, flat white-hot plate) -> v2/v3 figures re-scaled to hero size, footprints with
underdrawing, hearth az/el/pool re-set, chroma cap on the figures -> v4/v5 pooling moved into COMP, haze, fill pool, shadow-ratio fix ->
v6 sky re-dyed away from violet, wider sheet -> v7/v8 ageing (foxing, tideline), table wedge, cool arc -> v9-v12 grade (gamma, saturation),
cool-arc pre-compensation for the warm grade gain, folds + creases -> v13 -v15 gold thread / table / yaw of the slips / ratio-map masking.

## Known issues (honest list)
1. The figure art is the game's cartoony card art; re-embroidery gives real strands, couching and fuzz, but faces and small devices
   (shield charges, hands) are still low-detail, and the slips at 100 % read a little soft (4.65 px/mm on 10 px/mm maps through DOF + the
   Eevee 1.0 px filter). Not yet 'AAA museum macro' at 100 %.
2. The 70 deg stand-up is seen only 22 deg from the horizon, so the slips are strongly foreshortened; the lift reads mainly through the long
   shadows and the footprints, less through parallax.
3. Sky and hills are banded laid work (Bayeux-like), but the dusk sky is a stack of near-uniform stripes; there is no needle-painted gradient.
4. The gold chronicle thread sits at the very top edge of the frame (right part only): its tarnish is present but tiny. The hem / nail holes are
   barely visible at the left because of the dutch.
5. The daylight arc at the left is subtle (cool tint on linen and slip edges); the 'bleach' of dyes there is moderate by design (restraint).
6. Tethers are authored curves (no physics), tube geometry in Eevee (not fibres); wool fuzz on the slips is the R25 fibre set splatted in COMP
   (9.8 k fibres), not Eevee geometry; the ground plate's fibres are the R25 fibres of the hearth pass drawn in the rectified plate at 5 px/mm and then warped, so they are slightly softened at the far rows.
7. Ratio-map transfer of the slips' shadows: contact regions right under the felt edge use values filled from neighbours, so the contact
   shadow is slightly softer than a true Eevee ground would give.
8. COMP ageing is a plate-level relight + art-directed layers, not the six keyed R25 ageing states of the storyboard (single state for the keyframe).
9. Peak RAM: bake ~3 GB, Eevee ~0.7 GB, plate ~1.5 GB, all `nice -n 5`; disk of this dir ~0.7 GB.
