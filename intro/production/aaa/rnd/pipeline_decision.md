# CHRONICA intro: embroidery rendering pipeline, production decision (v1)

Technical director's decision after the material bake-off (relight25d / gnthreads / hybridplane, three judges).
It binds the renderer to `story/storyboard_v1.md` (26 shots, f0-1983) and `style/style_bible.md`. If anything here conflicts with those two, the storyboard owns the content and timing, the bible owns the look, and this document owns how frames are made.

Abbreviations: **R25** = the relight25d code base (2.5D stitch maps plus a numba relight); **EV** = Blender Eevee; **COMP** = numpy/cv2 compositor; **mm** = cloth millimetres; **px/mm** = map or screen pixels per cloth millimetre.

---

## 0. Decision in one paragraph

**One asset format, three ways to render it.**

The asset format is the **R25 stitch-map set** (`MapSet`, section 3). Every stitched thing in the film is baked once into this format: AI panels, the Bayeux kit, figure slips, crests, the board, the blank leaf and the logo.

The three renderers:

1. **R25 frontal relight in texture space.** It renders every shot where the cloth faces the camera, about 1,480 of the 1,984 frames: the frieze, light sweeps, stitch-on, unpick, small frontal lifts, burn, fray and dye revival.
2. **Eevee legacy (Blender 4.0.2) on meshes built from the same maps.** It is used only where something physically leaves the plane or the camera tilts: macro shots, the war slips, the crane onto the board, and the game models. It is the hybridplane technique, fed with R25 maps instead of hybridplane's.
3. **COMP.** It assembles everything. It adds R25's fibres, halo, grain and the single shared grade to the Eevee layers too, so that the same fuzz and grade appear on both sides of every cut.

From gnthreads we take only what true thread geometry is uniquely good at:
- the hero metal thread and its tie-downs in macro;
- tethers that stretch and snap;
- the stand-up "figure card" rise;
- the per-strand birth parameter;
- the needle glint;
- the work-in-progress frontier.

R25's own oblique ray-march is **retired from production**. It had drip and stair artefacts on the side walls, void corners, and a cost similar to Eevee at 1080p. It is kept only as an emergency fallback for tilts of 10 degrees or less.

---

## 1. What we keep from each contestant

| contestant | judge score | kept for production | dropped |
|---|---|---|---|
| **relight25d (R25)** | 8.5 / 8.5 / 8.5 (winner x3) | Everything in `emb/`: segmentation, structure-tensor and Jobard-Lefer streamlines, the strand rasteriser (capsule chain, ply, taper, dye lots), laid-and-couched work, split stitch, couched metal pairs, padded satin, stem stitch, couched cord, the skeleton tracer, tituli, the linen tabby plus ageing, the wrap-Lambert + height-field shadow + AO + Kajiya-Kay relight, the 0.3 mm halo, fibres as 3D curves lit per frame, the key-light pool, the stitch RECORD replay, the ghost under slips (underdrawing, needle holes, protected linen), Frankot-Chellappa padding. | The oblique 2-slab ray-march (`oblique.py`, `obl_render.py`) as a production path; the single-Gaussian minification prefilter (replaced by LOD bands); region-by-region stitch-on ordering. |
| **hybridplane** | 6.5 / 7.3 / 5.5 | The displaced-mesh method: low-pass height (sigma 0.3 mm) as vertex Z, high-pass as a tangent normal map, numpy `foreach_set` grids, boundary vertices snapped to the alpha contour, Solidify felt edge. Also: the Poisson phase-field (phi/psi) stitch layout as a fallback field, the shared animated fold/drape field, the registered high-frequency shimmer metric, gold as metallic GGX under a warm environment, the gold-cross-on-crimson padded shield, the Legion crimson livery ramp, protected unfaded linen in the ghost. | Its own map synthesis (embossed-ribbon strands, grid linen), bpy 5.2 Eevee-Next as the primary engine (2.5-3.4 GB RSS, 96-182 s per frame at 1440p), painted-in 2D fuzz. |
| **gnthreads** | 4.5 / 5.4 / 4.5 | The elliptical tube builder with ply UV (for the single hero silver-gilt thread and its tie-downs in macro, where metal thread really is smooth); tether curves that stretch and snap one by one; the stand-up to about 70 deg as a game figure card; the per-strand `birth` parameter (strand order plus position along the strand); the needle glint at the growing tip; the irregular work-in-progress frontier with iron-gall underdrawing; mm scene units (1 BU = 1 mm, unit scale 0.001) for physical DOF; batch card preprocessing (`prep_knight.py` idea, re-implemented on R25's figure builder). | Tube geometry for any fill or panel (looks like pasta or rice, 4-5M vertices per panel), its linen, its drop shadows. |

---

## 2. Technique per shot type

Technique codes follow the storyboard: R25-F, R25-S, R25-L, EV-DM, COMP and GP (game plates). This document splits EV-DM into three variants:

- **EV-DM/G (geometry ground).** The cloth itself is a displaced Eevee mesh. Use it whenever the cloth is seen at more than 10 deg tilt, in macro, or under the crane.
- **EV-DM/P (pieces over plate).** The ground is an R25-F plate. Only the risen pieces are rendered in Eevee, over a shadow-catcher copy of the ground; their shadows are transferred to the plate as a ratio (section 7.6). Use it when the camera looks straight at the cloth (tilt of 10 deg or less) and something stands up out of it. It is cheaper, and the ground is identical to R25 by construction.
- **EV-MR (macro rig, block E0).** EV-DM/G at F3 with real 3D thread curves, a needle mesh, DOF and motion blur.

### 2.1 By shot type

| shot type | chosen technique | why | fallback |
|---|---|---|---|
| **Tapestry panels** (p1, p3, p6, the p1' re-dye, the war strip, the Bayeux kit, borders, dividers, the S18 long plate) | **R25-F.** Bake once, then relight per frame only while the light changes; otherwise warp a cached shaded plate. **R25-S** for stitch-on and unpick. **R25-L** for frontal lifts of 15 mm or less with the camera within 10 deg of the cloth normal (goblets, crown slip, the S14 tower drops). | Best look at 1:1 in the bake-off (all three judges); about 5 s per frame, or 1.3 s per frame for camera-only moves. | None needed. |
| **Figure cards rising** (S12-S13 war slips; S20 banner) | **EV-DM/G** for S12-S13 (macro and the 22-deg oblique). Slips come from R25's figure builder, exported as 1.5 mm padded cards with a felt edge and a foot hinge, standing up to about 70 deg, with gnthreads tethers snapping one by one and the ghost underneath. **EV-DM/P** for S20-S21 (zero-tilt top-down camera). | Real silhouettes, cast shadows and parallax are the point of the beat; a 2.5D slab cannot stand up. | S20-S21 can go to EV-DM/G (the storyboard default) if the ratio shadow fails test T4. |
| **3D hex world with game models** (S22 still, S23-S24 crane, S25 convergence) | **EV-DM/G, block E4, hero 2560x1440.** Board proxy plane displaced from R25 board maps, with per-hex puff shape keys; the decoded game OBJs carry a stitch-material port; chrome flats move by camera-track homographies; the board converges to the UI-free plate, then to the native capture (storyboard section 11). | It is the only true 3D move in the film and must land exactly on the menu camera. | Storyboard PoC fallback: a plate-only 2.5D lift. |
| **Logo** ("Chronica" on the valance, S25; flare 3 in S26) | **COMP over the exact game art.** The reveal is a mask grown along the gold-mask skeleton in needle-path order with a travelling needle glint. The sheen is an **art-preserving R25 relight**: an additive term of metal Kajiya-Kay plus the environment term, applied to the logo maps and returning to exactly zero at rest. | f1929-1983 must equal the live menu (gate G12); only additive layers that decay to zero can guarantee that. | None. |
| **Macro** (S01 needle and first thread; S11 crown rip) | **EV-MR.** 120x80 mm (S01) and 60x40 mm (S11) linen patches displaced from R25's linen generator. The thread is a gnthreads-style tube with a helical ply bump, swept along an animated path; the tie-downs are small tubes with pop keys; R25 fibres are added in COMP. | Real DOF, focus band and motion blur at 27-51 px/mm, where 2.5D has no data. | None. |
| **Transitions** | **COMP.** 8-frame divider match-dissolves in linear light; dark splices; registered R25 <-> Eevee swaps (S01 f66-76, S13 f940-944, S23 f1712-1725) with a look-match map (section 7.7); the Eevee -> UI-free plate -> native capture dissolve (f1756-1798); the hard cut S10->S11 matched on the crown; the overlay hold and CSS dissolve. | All transitions are diegetic and textile; none needs new renders. | None. |

### 2.2 Per shot (storyboard frames)

| shot | frames | technique |
|---|---|---|
| S01 | 0-90 | f0-3 black; EV-MR f4-75 (72 @1080); crossfade to R25-F f66-76; R25-F pull-back to f90 |
| S02 | 91-139 | R25-F on kit section 1; per-frame relight during the breath (height scale animated) |
| S03 | 140-211 | R25-F p1 + 2 candle point lights + flame layer (R25-S re-raster on twos) |
| S04 | 212-275 | R25-F + metal environment term (L3 flare at f230); plate cached except during the flare |
| S05 | 276-338 | R25-L goblet slips (PCSS shadow, contact AO, 2D tethers) |
| S06 | 339-445 | R25-F; relight only while the light cools, otherwise plate warp; divider dissolve |
| S07 | 446-497 | R25-F p3 + R25-S flame unpick + its point light removed |
| S08 | 498-560 | R25-F, camera-only (cached plate): underdrawing + SINE HEREDE |
| S09 | 561-716 | R25-F p1' re-dye + R25-S king unpick + R25-L crown slip |
| S10 | 717-784 | R25-F per-frame relight (key az 160->40) + slip shadow + R25-S ghost crowns |
| S11 | 785-843 | EV-MR f785-812 (28 @1080) + 2 light-split stills; COMP decay and hold |
| S12 | 844-924 | EV-DM/G E1 (macro on ones, oblique slips on twos); ageing re-textured in COMP via the UV AOV |
| S13 | 925-981 | EV-DM/G E1 crane f918-943 -> swap f940-944 -> R25-S mass unpick + R25-F |
| S14 | 982-1050 | R25-F p6 + burn module + R25-L tower drops on twos |
| S15 | 1051-1137 | R25-S procedural stitch-on (trees, needle-path order) |
| S16 | 1138-1253 | R25-S bars and cords + unpick snips + cloud-kit padded layers |
| S17 | 1254-1282 | R25-F + start of fray masks |
| S18 | 1283-1381 | R25-F long plate at about 1.5 px/mm (assembled from mips) + fray and fringe curves + physical falloff |
| S19 | 1382-1523 | R25-F + reversed masks + OKLab dye revival + R25-S crests + L3 flare |
| S20-S21 | 1524-1598 | EV-DM/P E3 (pieces on twos, camera on ones) over the R25-F remainder plate |
| S22 | 1599-1688 | R25-S gold frame + drypoint + one E4 zero-tilt pieces still; E3 to f1612 |
| S23 | 1689-1743 | R25-S board stitch-on f1689-1711 -> swap f1712-1725 -> EV-DM/G E4 |
| S24 | 1744-1782 | EV-DM/G E4 + COMP chrome and valance |
| S25 | 1783-1854 | COMP title reveal + E4 f1783-1798 + plate dissolve |
| S26 | 1855-1983 | COMP over the native capture + art-preserving R25 sheen (L3); every animated layer at zero from f1929 |

---

## 3. The asset contract: `MapSet`

Everything is in **mm**, with the origin at the sheet's top-left, x to the right, y down, and z out of the cloth toward the camera. All sheets live in one **frieze coordinate system** (x along the roll, in mm). Camera paths, light positions (candles, fire, dawn front) and sheet origins are all expressed in it.

| channel | dtype on disk | meaning |
|---|---|---|
| `h` | float16 | Height in mm above the linen base plane: linen 0-0.5, laid 0.4-0.5, plus 0.3-0.4 for bars, outlines 0.55-1.0, padded satin 1.5-2.5. |
| `alb` | float16 x3, linear | Dye albedo including dye-lot, per-strand and along-strand variation and the fuzz halo. **No baked lighting.** |
| `T` | float16 x2 | Unit thread tangent in texture space. |
| `mat` | uint8 | Material id. 0 linen, 1 wool, 2 silk/satin, 3 metal, 4 ink/underdrawing (no relief), 5 cord, 6 walnut, 7 parchment, 8 felt edge. |
| `cov` | uint8 | Wool coverage (drives fibres and halo). |
| `sid` | int32 | Stitch id (0 = ground). |
| `reg` | uint16 | Region id, for re-dye and revival and art-directed zones. |
| `birth` | float16 | Normalised needle-path order plus position along the strand, in [0, 1] (stitch-on in any renderer). |
| optional layers | float16 | `age_mul` (foxing, tideline, fade), `ghost_*` (protected linen, underdrawing, needle holes under a slip), `pad`, `burn`, `fray`. |
| `stitches.npz` | arrays | The full RECORD: sid, type, polyline offsets and points, radius, h0, hamp, shade index, region, order. This is the replay source for R25-S and for snapshots. |
| `manifest.json` | text | Sheet id, PX, size in mm, frieze origin, tile grid, seeds, code hash, hint-file hash, palette version. |

- **Tiles.** 2048x2048 px with a 64 px overlap (covers the 6 mm shadow march at 10 px/mm). Files are `np.savez_compressed` per tile, float16.
- **Bake densities.** 10 px/mm by default (panels and kit). 20 px/mm for patches that appear next to the macro shots (the S01 border, the S11 crown). Mips of each sheet are built at bake time (5, 2.5 and 1.25 px/mm).
- **Derived per mip level and cached.** Normals `N` with LOD bands (section 5.2), `ao`, and a fibre set per sheet (seeded per shot, not per frame).

This contract is also the **Eevee export format** (section 7.1), so a sheet looks identical in both renderers apart from the BRDF. The look-match map closes that remaining gap.

---

## 4. Map generation (bake) recipe

### 4.1 Common stitch parameters

Bible section 3 and the R25 values are the defaults:

- **Linen.** Pitch 0.67 mm, thread 0.5 mm with slubs, base `#D4BE98`.
- **Laid strands.** 0.8 mm pitch, height 0.5x width, S-ply ridges at 30 deg and 0.7 mm spacing.
- **Couching bars.** Every 4.5 mm +/-20 %, pinching the strands 30 %. Tie-downs every 4 mm +/-25 %, 1.5 mm long.
- **Stem stitch.** 3.5 mm +/-18 %, half overlap, slant 13 deg, rope width 1.2-1.5 mm.
- **Couched metal.** Pairs at 1.0 mm pitch, tie-downs every 2.4-2.6 mm in coloured silk.
- **Padded satin.** 1.5-2.5 mm, with a pad dome from the distance transform.
- **Irregularity budget.** Bible section 4.6, exactly.

### 4.2 Direction fields (fix for gate G6)

The thread direction comes from an ordered decision per region:

1. If the region's structure-tensor coherence is 0.35 or more over 70 % or more of its area, use the **structure-tensor field** (R25).
2. Otherwise, if the region is laid-and-couched work (robes, throne, horse bodies, caparisons), use a **region-axis field**: a constant angle (from the region's principal axis, or from a hint), bent by at most 15 deg over 30 mm by a smooth noise. This is Bayeux practice and removes the concentric "fingerprint" whorls.
3. Otherwise (needle painting: faces, beards, small forms), use the **phase field** (hybridplane `phase_fields`; psi runs along the strands).
4. For metal motifs (crown fleurs-de-lis, crest charges), use a **contour-parallel field**: the isolines of the distance transform, so couched gold follows the shape instead of running in horizontal rows.

Streamlines then come from R25's numba Jobard-Lefer, unchanged, followed by its gap-fill and end-overlap passes.

### 4.3 Per asset family

| family | builder (`lib/chron/motifs/`) | inputs | art direction | cost (CPU, 1 process, 2 threads) |
|---|---|---|---|---|
| AI panels p1, p3, p6 | `panel.py`. Tiled version of R25 `motif_king` with segmentation in OKLab colour families. | `intro/p*.png` at 5 px/mm, re-embroidered at 10 px/mm | `lib/hints/p1.json` etc.: zone polygons (face, beard, metal boxes, ermine, keep-out), per-zone stitch type, field mode, outline suppression, `detail_transfer` zones. About 15 min of authoring per panel. | 5-8 min per panel; at most 2 GB RSS |
| Face likeness (inside panels) | `panel.py` `detail_transfer` | Source panel luminance high-pass, 0.3-1.5 mm band | Zones only (faces, small heraldry): `alb *= 1 + 0.18 * hp(src)`. This is the bible section 5.2 ratio idea, restricted so it never brings back the AI look. | negligible |
| Busy detail (chain, collar, orphrey) | `panel.py` zone rules | | No black-hat outline extraction inside zones whose outline density exceeds 0.25; chain = one couched gold cord along the skeleton with tie-downs; orphrey = laid gold with red couching. | negligible |
| Ermine | zone rule | | Laid cream wool on a constant axis with diagonal, jittered couching (no brick lattice); spots are padded black satin tails. | negligible |
| Bayeux kit (hillocks, interlace trees, borders and beasts, towns, roads, bars, realm cords, fog quilts, underdrawing) | `kit.py` | Vector shapes (SVG/JSON) authored once; town elevations from game OBJs rendered side-on as colour-ID stills; `cloud_*` sprites for the quilts (luminance -> padded height) | Gate G1: S02 is proved beside p1 at matched px/mm under identical relight before any other section is built. | 2-5 min per sheet |
| Figure slips (11 units x idle/strike x 4 realms = 88) | `figure.py` (R25 `motif_knight`, generalised) | `assets/tex_tinted` albedo + normal + mask | Livery from the mask R channel in the realm ramp (Legion = game crimson, under the heraldic chroma cap of 0.20); shield G channel = couched gold cross over padded satin; outline A channel = 2-ply couched cord with a **cord fibre multiplier of 0.3**; slip margin 1.6 mm; ghost layers written for each. | about 20 s each, about 30 min batch |
| Crests (S19) | `crest.py` | `ui/crest_*` | Padded satin with couched gold over the padding, satin direction per block (blocks flash separately). | about 1 min each |
| Board (S22-S24) | `board.py` | UI-free plates, seed-4242 hex geometry | Satin hex fields (silk lobe, direction per hex), couched gold realm borders, denim sea `#316994` with wave marks, plan-icon towns, per-hex `birth` = wavefront delay map. Built in plate-UV "board mm". | about 15 min |
| Leaf (S22) | `leaf.py` | Parchment interior from the native capture (9-slice inpaint) | Fresh-linen micro-relief faded by LOD (only visible in raking light), drypoint title line plus one rule as embossed hairlines, gold frame cord 0.6 mm. | 1 min |
| Logo (S25-S26) | `logo.py` | `logo_title` art and its gold mask | Couched-floss height from the gold mask along the skeleton tangent; **albedo = the game art unchanged**; skeleton stroke order C-h-r-o-n-i-c-a, then crown, fleurs-de-lis and diamonds. | 2 min |
| Linen and ageing | `linen.py`, `ageing.py` | | Analytic tabby (threads addressable by index, for fray); ageing at 20-40 % of the survey density; burn as a noise-advected distance field. | |

### 4.4 Fuzz calibration (fix for gate G3)

- **Halo.** 0.3 mm sigma at 35 % on fills, 15 % on cords and stem outlines.
- **Fibre density multipliers.** Fills 1.0; stem outlines 0.5; couched cords 0.3; metal 0. Metal thread gets no fibres.
- **Fibre colour.** The parent albedo times U(0.95, 1.05) (R25 used up to 1.12, which whitened them).
- **Over dark fills.** Fibre alpha is multiplied by `smoothstep(0.03, 0.15, lum(alb_under))`, so pale fibres no longer read as scratches.
- **Self-shadow.** Fibre radiance is multiplied by `0.55 + 0.45 * vis_root`, and by `exp(-2.5 * max(0, h_surface_at_tip - z_tip))` (cheap occlusion when a fibre dips under neighbouring strands).
- **Slip edges.** Fibres whose tip leaves a slip's alpha are clipped (`clip_keep` = 0; R25 used 0.25), which removes the dark specks around the slip edge.

---

## 5. R25 shading model (production)

### 5.1 BRDF (R25 `shade.brdf` plus three additions)

Units are mm. N comes from the LOD-banded normals (5.2). Diffuse is wrap-Lambert `(N.L + 0.25) / 1.25`. Shadows come from a height-field march toward each light: 60 steps x 1.25 px, soft = 0.12 mm, blur 0.12 mm. AO is R25's two-scale AO, clamped to 0.35-1.

Kajiya-Kay lobes (exponent / intensity):

| material | lobes |
|---|---|
| linen | 24 / 0.05 |
| wool | 8 / 0.045, plus a coloured lobe 3 / 0.06 x albedo, plus grazing sheen `0.12 (1 - Nz)^2` |
| silk | 40 / 0.15, plus a band term |
| metal | 180-300 / 1.0-1.4 tinted by `#E9BE6A`, with diffuse x0.25 |

Lobes fade in with `smoothstep(-0.1, 0.25, N.L)`. The camera position is passed per frame (R25 already supports `cam`), so the spec follows the real view.

The three additions:

1. **Metal environment term (gate G2).**
   `spec_metal += F_gold * E(R) * k_env`, with `R = reflect(-V, N_strand)` and `k_env = 0.35`. E is a prefiltered warm studio environment:
   - a 3200 K softbox lobe centred on the key azimuth, 35 deg wide;
   - a broad warm dome at 8 % of the key;
   - a dark floor.

   Because `N_strand` sweeps across each thread's cylinder, every couched row returns a thin band of reflection at **any** key azimuth.

   Acceptance: crown, chronicle thread and title rendered at key az 60 / 120 / 180 deg must read as metal (judged), with metal pixels within the L1/L2/L3 caps (section 9.4).
2. **Point practicals.** Candles and the S22-S23 off-frame pools are point lights at frieze-mm positions:
   - inverse-square falloff, with the R25 `kmap` light pool for the soft edge;
   - a per-pixel light direction in the shadow-march kernel (new numba kernel `shadow_march_point`);
   - flicker = 1-3 Hz sway plus 8-12 Hz flicker at 6-12 % (candles), or 2-6 Hz at 15-25 % (fire), from seeded band-limited noise curves stored per shot so retakes reproduce.

   Each extra shadowed light costs about 1 s per frame. A practical whose shadow is invisible can run without shadows.
3. **Act tints and the physical vignette.**
   - Light colours come from `palette.json > light_kelvin_display`, used as 20-50 % tints.
   - Fill ratio and key elevation come from the act (section 6).
   - The vignette is only the key pool (`kmap`) and the Act III edge falloff (-1.5 to -2.5 EV by f1319); never an overlay.

### 5.2 LOD and anti-aliasing (fix for gate G7; replaces the single Gaussian prefilter)

- **Shading density rule.** Relight on the mip level whose density is 1.0-1.4x the screen px/mm, then warp.
  - F0 (3.3 px/mm on screen) shades the 5 px/mm mip.
  - F1 (4.65) shades the 5 px/mm mip.
  - F2 (12.8) shades the 10 px/mm level.
  - Magnifying beyond 1.4x is forbidden: re-bake at a higher density, or cut to Eevee.
- **Height bands.** At bake time `h` is split into four bands:
  - **weave**: period 0.67 mm;
  - **strand/ply**: 0.7-0.9 mm;
  - **stitch structure**: 3-5 mm (bars, tie-downs);
  - **relief**: everything above.

  Each band's normal contribution is scaled by `clamp((p_px - 2) / 1.5, 0, 1)`, where p_px is the band period in screen px for the current frame (bible section 3).

  Kajiya-Kay exponents are widened by Toksvig, using the normal-length shortening of the averaged band normals.

  The weave keeps its average albedo when it fades out.
- **Warp.** Use `cv2.remap` with Lanczos4 on the shaded mip (minification is at most 1.4x by the rule above, so no extra blur is needed).
- **Motion blur.** When frame-edge texture moves more than 12 px per frame, use a 180-deg shutter: 6-8 sub-frame warps of the same shaded plate, averaged. Fibres are splatted at mid-shutter.
- **Fibres.** Splatted only where the screen density is 4 px/mm or more (below that, the halo carries the fuzz). Anti-aliased width is `min(1, s * 1.1)` px.

### 5.3 Frame paths and measured cost (2560x1440, 2 threads; measured values from `bench_1440.json`, others estimated)

| path | when | s/frame |
|---|---|---|
| R25-F, light moving | sweeps, practicals, dawn | 5.0 measured (+1 s per extra shadowed point light) |
| R25-F, cached plate | camera-only moves under static light | 1.26 measured |
| R25-S, stitch-on/unpick | dirty-rect re-raster + local relight | 6-8 (target; full-map recompute today) |
| R25-L, frontal lift | slip as its own shaded layer + PCSS shadow + tethers | about 6 |

### 5.4 Grade (one implementation, used for R25 and Eevee layers alike)

ACES fit (Narkowicz) at exposure 0.85, then the act grade from `palette.json > acts` (sat, lift, gamma, gain, chroma cap).

The grade is keyed to storyboard frames (colour script, section 8), not to palette.json's act times. Act boundaries cross-fade over the transition frames listed in the storyboard.

Clamps: black floor `#07070A`, white ceiling `#F3E8D0`, shadow tint `#1A1620` at 10-20 %, highlights warm `#FFF0D6`. Metal is allowed to reach `#FFF3D6` only on the L3 frames (section 9.4). Film grain is 1.2 % luminance, seeded per frame and applied after the grade.

---

## 6. Lighting defaults

| act (storyboard) | key K / elevation / azimuth | key intensity | fill (cool, K 8000 tint) | rim | practicals |
|---|---|---|---|---|---|
| I Oath (f0-445) | 3000 K / 22 deg / 135 deg (upper left) | 2.3-3.0 | 1:3 | 25 % at az 30, el 8 on hero frames | candles 1900 K, 1-3 Hz + 8-12 Hz, 6-12 % |
| II Death (f446-843) | 1900 K / 12 deg / 135 deg (S10 swings 160 -> 40 deg) | 2.0 | 1:6 | off | 2-4 candles; one unpicked on 'died' |
| III War (f844-1381) | 2200 K firelight from the bottom edge (az about 270 deg) / 6-15 deg | 2.2, flicker 15-25 % | 1:5 | ember rim from below | fire 2-6 Hz; embers die on 'dark' f1292 |
| IV Renewal (f1382-1688) | 4300 K dawn, front sweeping L->R / 28 deg | ramp over 3-4 s | 1:2.5 | 20 % | candle pool relit on f1664 |
| V Question (f1689-1983) | 3200 K / 20 deg; warm sweep L->R peaking at f1760 | 2.5 | 1:4 | 25 % | 2 candles; title sheen 1.5-2.5 s |

Rules:
- The key is never flat (elevation 12-30 deg), except the deliberate grazing reveals: 6 deg in S13 and 8 deg in the S01 macro.
- A sweep moves 60-120 deg over 2-4 s; L->R for progress, R->L for decline.
- Eevee uses the same azimuth, elevation, Kelvin and ratios as R25, converted by `lib/chron/blender/lights.py`. The key and fill are Sun lights with angle 1.5-6 deg; practicals are Point lights with radius 2-4 mm.

---

## 7. Eevee recipe (EV-DM/G, EV-DM/P, EV-MR)

### 7.1 Engine and scene

| setting | value |
|---|---|
| engine | Blender 4.0.2 Eevee legacy under `xvfb-run` (750 MB RSS, measured; 2 processes give +21 % throughput). bpy 5.2.2 Eevee-Next via EGL is the fallback only (2.3-3.4 GB RSS). A compat shim lives in `lib/chron/blender/compat.py`. |
| scene units | 1 BU = 1 mm, `scale_length` 0.001 (physical DOF, mm-scale shadow numbers) |
| colour | View transform Standard, linear OpenEXR half multilayer output. ACES and the grade happen only in COMP (5.4). |
| shadows | Cascade 4096, cube 2048, high bit depth, soft shadows on. Sun: 4 cascades, `max_distance` fitted per shot to the visible depth range (frustum-fitted by `rig_*.py`). Contact shadows on for the key: distance 2 mm, thickness 0.2 mm. GTAO distance 2 mm, factor 0.8. Bloom off. SSR on only in E4 (gold borders). |
| samples | 16 TAA for macro, hero and DOF shots; 8 TAA for wide E1 frames; 32 TAA only for registration stills. Film filter 1.2 px. |
| motion blur | On (shutter 0.5) only in EV-MR and E4 crane frames. Moving pieces rendered on twos never get motion blur. |
| passes | Combined, Z, Normal, AO, Shadow; Shader AOVs `uv` (sheet UV), `matid`, `sheet_id`. Per-frame camera matrix and object matrices are exported to JSON (for COMP fibres, homographies and chrome). |

### 7.2 Meshes built from a `MapSet` (`lib/chron/blender/dm_mesh.py`, from hybridplane `grid_mesh` / `snap_contour`)

- **Vertex density.**
  - Ground: 3 vertices per mm (low-pass sigma 0.3 mm).
  - Within the focus band of macro and hero shots: 4-5 vertices per mm.
  - Outside the frustum's sharp region: 1 vertex per mm (non-uniform grid).
  - Slips: 4 vertices per mm, boundary vertices snapped to the alpha contour, Solidify 1.5 mm (felt edge). The edge colour is sampled from the outermost strands, not flat.
- **Textures.**
  - Albedo: EXR half, linear.
  - Normal: tangent-space, from the **high-pass** height, with the weave band pre-faded for the shot's minimum screen density.
  - Material map: R = roughness, G = metallic, B = sheen, A = spec level.
  - `birth` (for alpha-clip stitch-on, if a shot ever needs it in Eevee).
  - `microvis` (7.4).
- **Folds.** The shared fold/drape field `lib/chron/anim/drape.py` (in mm and seconds) is applied to vertex Z. The *same* function feeds R25's height, so folds match across cuts.

### 7.3 Materials (Principled v2; bible section 5.3 values)

| material | base | roughness | sheen (weight / roughness / tint) | spec IOR level | metallic | normal strength |
|---|---|---|---|---|---|---|
| wool | `alb x microvis_k` | 0.85 | 0.6 / 0.42 / 0.5 x albedo + 0.5 white | 0.35 | 0 | 1.0 |
| linen | same | 0.75 | 0.2 / 0.5 / white | 0.3 | 0 | 0.8 (LOD-faded) |
| silk satin | same | 0.4 | 0.3 / 0.3 | 0.5 | 0 | 1.0 |
| metal (couched gold) | `#E9BE6A` (tarnish `#7A5A2A`) | 0.28 | 0 | 0.5 | 1 | 1.3 (ply stretches the GGX highlight along the thread) |
| felt edge | darkened edge-strand colour | 0.95 | 0.3 | 0.2 | 0 | 0.5 |

- **World.** Warm studio gradient: the same environment E as R25's metal term, baked to an equirectangular map, strength 0.15.
- **Game OBJ pieces** (towns, castles, farms, forests, banner):
  - albedo from `game_palette.json` per material slot;
  - a triplanar stitch normal from an R25-baked tileable satin or laid patch at the piece's mm scale;
  - a brown inverted-hull outline (Solidify, flipped normals, emission brown, 0.6-1 mm thick), which is the game's piece idiom;
  - pieces keep their own materials until the convergence dissolve.

### 7.4 Micro-shadows Eevee cannot cast (fix for hybridplane's weakest point)

Strand-level relief (below 0.7 mm) lives only in the normal map, so Eevee casts no shadows from it. R25 therefore bakes a **`microvis`** texture per shot:

- the height-field shadow march for the shot's key direction, run on the **high-pass height only** (so it does not double the shadows Eevee casts from the low-pass geometry);
- multiplied into the base colour as `mix(1, microvis, 0.8)`.

When the key moves (the E4 sweep), `microvis` is written as an image sequence on twos. It costs about 1-2 s per unique frame for the visible footprint.

### 7.5 Rises, tethers, stand-ups (gnthreads + hybridplane + R25)

The sequence for every rising piece:

1. **Anticipation dip:** 2 frames.
2. **Relief swell.** `pad` scale 1.0 -> 1.3 over 4-6 frames; Frankot-Chellappa relief from the game normal map.
3. **Peel.** Top-first, with a bend shape key (curl of at most 8 deg).
4. **Hinge.** The piece hinges at its feet to 70 deg (war slips), or lifts by at most 12 mm (goblets and crown in R25-L).
5. **Settle bob** at the score's 2.115 s pulse (0.473 Hz), amplitude 0.6 deg or 0.3 mm, decaying.

Tethers:
- 20-40 per slip, bevelled curves of radius 0.16-0.2 mm in the parent strand colour (gnthreads `update_tethers`).
- They run from anchor points on the slip outline to needle holes in the ghost.
- Sag is analytic. Each tether snaps when its stretch passes 1.15 x rest length plus a per-tether jitter; snap times can be quantised to bass pulses or narration stresses.
- After snapping, the ends recoil and curl over 4 frames.

Every rising piece shows tethers, a contact shadow and its needle-hole footprint for at least 6 frames (storyboard rule). The ghost (protected unfaded linen, underdrawing, needle holes) is part of the ground maps beneath. The camera drifts so the ghost is visible for at least 12 frames somewhere in each rise.

### 7.6 EV-DM/P: pieces over an R25 plate (E3 and the S22 still)

Eevee renders only:
- (a) the pieces, with alpha;
- (b) a **shadow-catcher ground**: a white diffuse plane with low-pass displacement, lit by the key only, with the pieces casting shadows. Their camera visibility is off via a holdout material that keeps `shadow_method` opaque.

A static unshadowed copy of (b) is rendered once per light state.

COMP: `ground = R25_plate x (b / b_unshadowed)`, followed by the pieces composited over it with Eevee's contact AO.

Parallax of the 1 mm ground relief at the S20-S22 framing is at most 1 px at the frame edges, which is acceptable. This path is cheaper than EV-DM/G (estimated about 18 s per 1080p frame) and makes the ground identical to R25.

### 7.7 Look-match at registered swaps (gate for S01, S13, S23)

At each swap pose:
1. Render the Eevee frame and the R25 frame of the same maps and light.
2. Through the `uv` AOV, compute a **texture-space low-frequency ratio map**: `blur(R25) / blur(EV)` with sigma 3 mm, clamped to 0.8-1.25.
3. Apply it to every Eevee frame of that block via the `uv` AOV. It follows the cloth through the crane.

Acceptance (storyboard): median dE_ok x100 below 2, and no edge shifts above 1 px.

If this fails (test T1), switch the **ground** of that block to "R25 radiance as emission":
- the R25 relight is computed per frame with the Blender camera position and fed in as an emission image sequence;
- Eevee supplies only geometry, DOF and motion blur;
- piece shadows are transferred by the 7.6 ratio method.

### 7.8 Fibres on Eevee layers

R25 fibre sets of the sheets in view are projected with the exported camera and object matrices (fibres on a slip follow that slip's matrix), depth-tested against the Eevee Z pass, lit with the shot's lights and Kajiya-Kay, and splatted at 1440 *after* the upscale. This gives the same fuzz across every cut, which was hybridplane's main look gap.

---

## 8. Animation primitives (all driven by shot JSON; all in `lib/chron/anim/`)

| primitive | method | status vs bake-off | gate |
|---|---|---|---|
| **Stitch-on** | `birth`/RECORD replay. Needle-path order: greedy nearest-neighbour from the last stitch's end, within a region; region order laid -> bars -> tie-downs -> outline. Each strand grows along its length (capsule chain truncated at s in [0, 1]). Pop-in height 0 -> 1.15 -> 1.0 over 3 frames. Steel needle glint sprite at the tip for 1-3 frames, capped at L2. **Dirty rect:** re-raster, normals, AO, shadow and fibres only inside the new stitches' bounding box plus the shadow reach along the light, pasted into the cached shaded plate. | demonstrated (R25); order, growth and dirty rect are new | G8 |
| **Unpick** | **Checkpoint plus forward replay:** snapshot every N stitches (N chosen so that a replay costs 2 s or less), load the snapshot at or below k, rasterise forward to k (adding stitches is exact). Removed strands become 3D loose-end curves (fibre renderer in thick mode, Kajiya-Kay lit): kinked at couching points, curling 5-20 mm, pulled through to the hole over 4-6 frames. Reveals the ghost's needle holes (0.6 mm pits with raised lips) and underdrawing. | ghost exists; snapshots and curls are new | G9 |
| **Frontal lift (R25-L)** | The slip is its own shaded layer, offset by its parallax (4-8 px) and scaled 1.5 %. **PCSS shadow:** penumbra = 0.25 + 0.6 x lift in mm, offset `lift / tan(el)` along the light; contact AO 2 mm at the attachment edge; 2D tethers. Camera within 10 deg of the normal and lift of 15 mm or less only. | demonstrated; PCSS is new | G5 |
| **Stand-up / rise** | Eevee (7.5) | demonstrated (gnthreads, hybridplane) | G5 |
| **Dye revival / ageing** | Per-region OKLab lerp aged -> fresh, staggered 0.2-0.4 s behind the light front; `age_mul` keyed to 6 states (S12 time-lapse) | demonstrated (R25) | G11 |
| **Burn** | Noise-advected distance field: linen -> foxing `#9C7046` -> soot `#3A3330` -> char; 1-3 px ember rim (`#DE6A2C` -> `#F6B54A`, emissive, flickering); curled edge as a relit height lift; burn and soot persist as ageing layers | new | - |
| **Fray** | Analytic linen threads addressable by index; within the fray band, pulled weft threads are hidden in the linen map and rendered as thick fibre curves that lift and curl; border beasts unravel into fringe curves. Authored motion, no physics. | new (medium) | G9 |
| **Cloth sway** | Shared drape field (hybridplane folds plus R25 undulation), amplitude at most 1.2 mm, with phase locked to the 2.115 s pulse where the storyboard asks | demonstrated | - |
| **Flicker** | Band-limited seeded noise curves per practical; flames re-rastered as laid strands on twos, outer strands lagging | new (simple) | G11 |
| **Thread boil** | Only on moving stitched elements, on twos (re-seeded strand jitter); static cloth never boils | rule | - |

---

## 9. Camera, resolution, samples, caching

### 9.1 Resolution and upscale policy

| layer | render size | to master | ship |
|---|---|---|---|
| R25-F/S/L | native 2560x1440 | none | |
| EV-MR (E0), E1, E3 | 1920x1080, 16 TAA (8 for wide E1) | Lanczos3 x1.333 in COMP, then fibres, halo and grain at 1440 | 1920x1080 is the shipped resolution, so 1080 Eevee inserts lose nothing in `intro_1080.mp4`. |
| E4 hero | native 2560x1440, 16 TAA | none | |
| COMP master | 2560x1440 PNG16 (graded sRGB), global frame numbers 0000-1983 | x264 CRF 14 + the padded audio master | 1920x1080 H.264 (High, CRF 18, yuv420p, +faststart) + VP9 webm, area downscale; 4:3 master 1920x1440 (storyboard section 13) |

- Real-ESRGAN is not used: 10-117 s per 256 px tile on lavapipe, and it invents texture.
- Cycles is not used: about 135 s per 1440p frame.
- Remotion is not used in production. COMP is numpy/cv2 at about 0.4 s per frame plus ffmpeg.

### 9.2 Twos

- Camera moves are always on ones.
- Stitched animation (flames, stitch-on fronts on panel scale, rising pieces, tower drops, thread boil) is on twos: stop-motion embroidery, allowed by the bible.
- Lights are on ones, except where a 2-frame light step would read as a pop.

### 9.3 Caching and data layout

```
aaa/cache/maps/<sheet>/v<hash>/{manifest.json, stitches.npz, tile_rr_cc.npz, mip1..3/, fibres_<seed>.npz}
aaa/cache/plates/<shot>/<sheet>_<lightHash>_<mip>.exr   shaded linear plate, reused while the light is static
aaa/cache/snap/<sheet>/snap_<k>.npz                      unpick and stitch-on checkpoints (bounding-box crops)
aaa/cache/microvis/<shot>/<frame>.exr                    Eevee micro-shadow sequences
aaa/prod/shots/<Sxx>/{shot.json, r25/, ev/, comp/}/<global frame>.{exr|png}
aaa/prod/master/{frames/, intro_master_1440.mp4, intro_1080.mp4, intro_1080.webm, intro_4x3_1440.mp4, poster.jpg}
```

- **Content hashing.** Every cache key includes the code hash plus the input hashes. The farm skips frames whose output exists with a matching hash, so renders resume.
- **Memory.** At most 2 GB per R25 process (tiles plus float16). Eevee legacy uses about 0.75-1.5 GB. At most 2 heavy processes at once, each limited by `NUMBA_NUM_THREADS=2`, `cv2.setNumThreads(2)` and `nice -n 10`.
- **Process hygiene.** The farm writes PID files and only ever stops its own PIDs. It never uses `pkill -f` or `pgrep -f`.

### 9.4 Metal budget enforcement

`qa/metal.py` measures, per frame:
- pixels whose hue is in the gold window and whose value exceeds the `gold_hi` luminance;
- frames reaching `#FFF3D6`.

These must match the storyboard's level map:
- **L3:** the three flares only (f224-236, f1466-1480, f1862-1904).
- **L2:** at most 1 % of pixels, capped at `#F8D57C`.
- **L1:** everywhere else.

---

## 10. Library layout: `aaa/lib/`

```
aaa/lib/
  README.md                       contract summary, run recipes, env (sources tools/env.sh)
  chron/                          pure numpy/numba/cv2 package (python3.13, numba 0.68)
    config.py                     paths, PX ladder, frame<->time (frame = floor(t*30)), storyboard/audio event lookup
                                  ("word:crown" -> f230) from words.json, audio_timeline.json, storyboard_v1.json
    color.py                      sRGB/linear/OKLab, palette.json, ShadeSet (dye lots), chroma caps, Kelvin tints
                                  <- R25 core.py + stitch.ShadeSet
    maps.py                       MapSet, tiles, mips, LOD bands, float16 npz io, manifest, frieze placement
    linen.py                      analytic tabby, addressable threads    <- R25 linen.py
    ageing.py                     foxing, tidelines, losses, mends, fade, burn field, age states
    fields.py                     structure tensor, region-axis, phase field (<- hybridplane emb.phase_fields), contour-parallel, coherence selector
    strands.py                    numba Jobard-Lefer + raster_stitch + squeeze      <- R25 strands.py
    stitch.py                     fill (laid/split/long-short), couch, metal_couch, satin_pad, stem, cord, RECORD, birth
                                  <- R25 stitch.py
    segment.py, skel.py           colour families, hints loader; Zhang-Suen + tracer  <- R25
    lettering.py                  tituli (Cinzel skeletons) + logo skeleton paths     <- R25 titulus.py
    motifs/ panel.py kit.py figure.py crest.py board.py leaf.py logo.py
    shade.py                      normals (banded), AO, shadow_march (+point), brdf (+metal env), light rigs
                                  <- R25 shade.py
    fibres.py                     halo, fibre sets, projection-agnostic lit splat (frontal or Blender camera + Z)
                                  <- R25 fibres.py (+ calibration 4.4)
    camera.py                     rostrum view in frieze mm, exponential zoom, px/frame limiter, sub-frame blur;
                                  Blender camera JSON import and homographies
    frontal.py                    R25-F: mip select -> relight -> halo -> remap -> fibres -> linear out; plate cache
    lift.py                       R25-L slip layer, PCSS shadow, contact AO, 2D tethers
    anim/ stitchon.py unpick.py drape.py fray.py burn.py revive.py flicker.py pulse.py (2.115 s bass pulse)
    grade.py                      ACES fit, act grade keyed to storyboard frames, clamps, grain
    comp.py                       layer stack, dissolves (linear light), look-match maps, shadow-ratio transfer,
                                  upscale, chrome homographies, final PNG16
    farm.py                       shot JSON -> frame tasks, <=2 heavy procs, hashing/resume, own-PID control
    qa/ void.py shimmer.py (<- hybridplane shimmer.py, + resample baseline) swap.py (dE_ok, edge shift)
        metal.py clip.py (floor/ceiling, chroma caps) sync.py (event frames) handoff.py (G12) report.py
  chron/blender/                  runs inside Blender 4.0.2 (compat shim for bpy 5.2)
    compat.py dm_mesh.py (<- hybridplane grid_mesh/snap_contour) materials.py lights.py tethers.py (<- gnthreads)
    thread_tube.py (<- gnthreads build_tubes: hero metal thread, tie-downs) pieces.py (OBJ import, stitch port,
    inverted hull) export_maps.py (MapSet -> EXR/normal/material/microvis) passes.py camtrack.py
    rig_e0_macro.py rig_e1_war.py rig_e3_board.py rig_e4_hero.py
  hints/  p1.json p3.json p6.json kit/*.json      art-direction polygons and zone rules (versioned)
  shots/  S01.json ... S26.json                    generated from storyboard_v1.json, then hand-tuned
  bin/    bake.py  bake_figures.py  render_shot.py  comp_shot.py  qa_shot.py  assemble.py  preview.py
  tests/  test_contract.py test_lod.py test_metal_azimuths.py test_swap.py test_stitchon_dirty.py (small, 720p)
```

Porting rule:
- `rnd/*` is frozen. The library is a clean copy with hard-coded paths removed (R25 `core.A`, `motif_king.SRC`).
- Every port lands with a 720p regression still compared against the bake-off still.

---

## 11. QA gates (automated per shot unless noted)

| check | rule | tool |
|---|---|---|
| Void | No pixel outside every sheet or mesh (`BORDER_CONSTANT` sentinel in remap; alpha < 1 in Eevee) | `qa/void.py` (G4) |
| Shimmer | Registered high-frequency residual no more than 3 points above the resample-only baseline, on every moving shot. Before the trucks are committed: an F0 framing with a 12 px per frame truck at 1440p must pass. | `qa/shimmer.py` (G7) |
| Swap | Median dE_ok x100 below 2; no edge shift above 1 px at S01 f66-76, S13 f940-944, S23 f1712-1725 | `qa/swap.py` |
| Metal | Section 9.4 caps and level map | `qa/metal.py` (G2) |
| Clip and chroma | Floor and ceiling; narrative fills at or below 0.13, heraldic at or below 0.20, act caps | `qa/clip.py` (G11) |
| Sync | Event frames in shot JSON resolve to the storyboard sync map; a beat marker image is rendered for review | `qa/sync.py` |
| Hand-off | f1983 vs the live first frame: mean absolute difference below 2/255 outside text, flames and card interior; offsets of 0.5 px or less; checked at 2560 and at the shipped 1080. f1929-1983 identical. | `qa/handoff.py` (G12) |
| Look (human) | 1:1 crops at 3 points per shot plus a contact sheet against the bake-off R25 still | `qa/report.py` |

---

## 12. Known weaknesses and fixes

| # | weakness (source) | fix | where | gate / test |
|---|---|---|---|---|
| 1 | Gold reads as ochre wool away from az 118-128 (R25) | Environment term (5.1.1) plus a wider metal lobe; metallic GGX + world gradient in Eevee | `shade.py`, `materials.py` | G2, T2 |
| 2 | Chenille cords; white scratch fibres; dark specks at slip edges (R25) | Fuzz calibration 4.4 | `fibres.py` | G3 |
| 3 | Void corner; slip drip and stair artefacts (R25 oblique) | Oblique ray-march retired; Eevee for tilts above 10 deg; void QA on every frame | farm policy, `qa/void.py` | G4, G5 |
| 4 | Cardboard-cutout shadow for a 9 mm lift (R25) | PCSS penumbra growing with lift, contact AO, less grazing key during lifts (elevation 18 deg or more) | `lift.py` | G5 |
| 5 | Fingerprint whorls; brick-lattice ermine (R25) | Field decision 4.2; ermine rule | `fields.py`, hints | G6 |
| 6 | Soft frontal image; F0 untested (R25) | LOD bands + Toksvig + the mip-density rule replace the Gaussian; F0 truck test | `maps.py`, `shade.py`, `frontal.py` | G7, T3 |
| 7 | Stitch-on "confetti", whole-map recompute (R25) | Needle-path order, along-strand growth, pop curve, needle glint, dirty rect | `anim/stitchon.py` | G8 |
| 8 | Unpick not incremental (R25) | Checkpoint plus forward replay; loose-end curls | `anim/unpick.py` | G9 |
| 9 | Panels need hand hints; likeness loss; crown, chain and throne detail (R25) | Versioned hints JSON (about 15 min per panel); detail-transfer zones; contour-parallel gold; chain as a cord; outline suppression in busy zones | `motifs/panel.py`, `hints/` | G10 |
| 10 | 17 Mpx panels, 504 MB caches (R25) | Tiles, float16, compressed, at most 2 GB per process | `maps.py` | G10 |
| 11 | Hot satin red; blue caparison instead of Legion crimson (R25) | Realm ramps from the game crests; chroma caps enforced in QA; gold cross over padding | `figure.py`, `qa/clip.py` | G11 |
| 12 | No practicals or act tints (R25) | Point lights + flicker curves + act grade | `shade.py`, `anim/flicker.py`, `grade.py` | G11 |
| 13 | No strand self-shadow in Eevee (hybridplane) | `microvis` (7.4) | `export_maps.py` | T1 |
| 14 | No anisotropy in Eevee (hybridplane, gnthreads) | Gold: GGX on a ply-stretched high-pass normal plus environment. Wool: sheen. Remaining mismatch closed by the look-match map; fallback to the R25-radiance emission ground. | `materials.py`, `comp.py` | T1 |
| 15 | No 3D fuzz on Eevee layers (hybridplane) | R25 fibres projected with the Blender camera + Z (7.8) | `fibres.py`, `comp.py` | T1 |
| 16 | Eevee mm-scale shadow precision (gnthreads note) | mm units, frustum-fitted cascades, contact shadows 2 mm; check on the first E1 and E4 look-dev stills | `rig_*.py` | T1, T5 |
| 17 | Rigid stand-up with no curl (gnthreads) | Bend shape key during the peel (8 deg or less), squash on landing, tethers snapping | `rig_e1_war.py` | T5 |
| 18 | Ghost hidden behind a risen piece (hybridplane, gnthreads) | Camera drift reveals it for 12 frames or more; protected-linen tone | shot JSON | review |
| 19 | Tethers read as drips (hybridplane) | Radius 0.16-0.2 mm in the parent colour, analytic sag, Kajiya-Kay-lit fibres on them in COMP, snap and recoil | `tethers.py` | T5 |
| 20 | Pasta-looking tubes (gnthreads) | Tubes are used only for the silver-gilt thread (physically smooth metal) and silk tie-downs; never for wool | `thread_tube.py` | T6 |
| 21 | Eevee shader compile 10-20 s per process | One long-lived Blender process per block, rendering frame ranges | `farm.py` | - |
| 22 | Contention on 4 shared cores | At most 2 heavy processes, nice, test renders at 720p, resumable farm | `farm.py` | - |

---

## 13. Validation tests before committing renders (each 30 CPU-min or less, at 720p unless noted)

| test | content | pass | fallback |
|---|---|---|---|
| **T1 swap** | The bake-off scene (king + knight sheet) at zero tilt: R25-F vs EV-DM/G at 1080 with `microvis`, look-match map and projected fibres | Median dE_ok x100 below 2; edge shift of 1 px or less; judged indistinguishable in an A/B flicker | R25-radiance emission ground (7.7) |
| **T2 metal** | Crown at az 60 / 120 / 180, 1440 crops | Reads as metal at all three; within the metal caps | Raise `k_env`, narrow the softbox |
| **T3 F0 truck** | Kit S02 sheet at F0, 12 px per frame truck, 1440p, 30 frames | Shimmer within baseline + 3 points; no moire | 2x supersampled shading for F0 shots only (about 2x cost on about 150 frames) |
| **T4 shadow ratio** | S20 banner via EV-DM/P vs EV-DM/G | Shadows and contact read correctly; ground identical to R25 | EV-DM/G for E3 (storyboard default, about +10 min) |
| **T5 war slip** | One slip standing up with tethers, 1080 16 TAA, 6 frames | No shadow acne or peter-panning at mm scale; tethers read as wool | Tighter cascades; contact shadow distance 1 mm |
| **T6 macro thread** | S01 f39 still (thread taut, first tie-down) | Silver-gilt reads as metal wire on silk; linen fibres convincing at 27 px/mm | Eevee hair (40/cm2) on the patch focus band only |
| **PoC** | Storyboard section 11 (f1689-1830) | Storyboard pass/fail list | Storyboard fallbacks |

---

## 14. Time estimates

### 14.1 Engineering (agent-hours; parallel tracks)

| track | work | hours |
|---|---|---|
| A. Library core | Port `emb/` into `lib/chron` + MapSet/tiles/mips + LOD bands + metal environment + fuzz calibration + practicals + grade + QA void/shimmer/clip | 12 |
| B. Animation | Stitch-on (order, growth, dirty rect, glint) + unpick (snapshots, curls) + lift (PCSS) + burn + fray + revival | 10 |
| C. Assets | Hints and tiled bakes for p1, p3, p6 (3 x 15 min authoring + tuning) + Bayeux kit with the G1 proof (largest item) + figure batch + crests + logo + leaf | 14 |
| D. Eevee | compat, export_maps, dm_mesh, materials, lights, tethers, thread_tube, pieces, rigs E0/E1/E3/E4, look-match, T1/T4/T5/T6 | 12 |
| E. Board and hand-off | Game plates (demo mode), hex geometry, board maps, chrome mattes, PoC, 4:3 recomposite, G12 | 8 (overlaps D) |
| F. COMP and assembly | Layer stacks, dissolves, homographies, fibres-on-Eevee, encodes, QA report | 5 |
| **total** | | **about 55-60 agent-hours**; about 14-18 h of calendar time with 4 parallel agents. Critical path: A -> (C kit with G1 proof, and D with T1) -> E PoC -> full renders. |

### 14.2 CPU (measured rates where they exist; others estimated)

| item | frames | rate | process time |
|---|---|---|---|
| Bakes: panels (3 x 5-8 min), figures (88 x 20 s), kit (about 10 sheets x 2-5 min), board, crests, logo, leaf, snapshots, long plate | - | - | about 2.5 h (2 in parallel: about 1.3 h wall) |
| Game plates (SwiftShader 20-40 s per frame; 2x plates, captures) | about 8 plates | - | about 1 h |
| R25-F/S/L (about 1,480 frames incl. Eevee hand-over frames) | - | 1.3-8 s, average about 6.5 s with practicals | about 2.8 h (2 threads) |
| E0 macro | 102 @1080 | about 65 s | 111 min |
| E1 war | 77 @1080 | 28 x 65 s + 49 x 15 s | 42 min |
| E3 banner and village (EV-DM/P) | 89 @1080 | about 18 s | 27 min (37 min if the T4 fallback is used) |
| E4 hero | 89 @1440 | 90-100 s | 141 min |
| E4L 4:3 leaf layer | 87 | about 10 s | 15 min |
| `microvis` sequences, look-match, fibres-on-Eevee | about 360 | 1-2 s | 10 min |
| COMP (all frames) + encodes + QA | 1,984 | 0.5-3 s | about 45 min |
| Look-dev tests T1-T6 + PoC overhead (PoC frames are production frames) | - | - | about 2 h |
| Preview animatic (R25 at 720p 2.3 s per frame; Eevee at 960x540 4 TAA) | 1,984 | - | about 1.5 h |
| **Final pass total** | | | **about 9.5 process-hours**: Eevee 5.6 h + R25 2.8 h + COMP 0.75 h + misc |

Wall clock on 4 shared cores, with one Eevee lane (2 procs when R25 is idle) plus one R25/COMP lane:
- final render pass: **about 5-6 h**;
- with bakes, plates, tests and the animatic: **about 9-10 h**;
- plus a **25 % retake reserve** (about 1.5 h).

Budget check against the brief: Eevee uses 268 of 600 frames at 1080p and 89 of 150 hero frames at 1440p; everything else is 2.5D. Inside the limits.

### 14.3 Order of work

1. **Library core.** Port A, then T2/T3 on the bake-off sheet. In parallel: D compat/export, then T1.
2. **Kit proof (G1).** S02 beside p1. Panel hints and bakes. Figure batch. Game plates.
3. **PoC f1689-1830.** Then T4, T5, T6. Then lock the shot JSONs.
4. **Animatic.** Full film at 720p/540p, muxed, for a sync and pacing review.
5. **Finals.** Order: E4 hero and E0 (longest renders) first, in parallel with the R25 shots in film order. Then COMP, QA, encodes, and the hand-off acceptance (G12).

---

## 15. Explicit non-goals

- No orbit or tilt beyond 25 deg (except the specified macro, war and crane tilts).
- No tilt-shift, no dolly-zoom.
- No particles. Fire is wool, smoke is stem stitch.
- No Cycles, no AI upscaling.
- No new paid AI images.
- No physics simulation: tethers, fray and loose ends are authored curves.
- No modification of `/home/user/chronica-ipad`. The integration snippet stays a suggestion; the deliverables are `intro_1080.mp4`/`.webm`, a 4:3 variant and a poster.
