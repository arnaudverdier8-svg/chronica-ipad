# Builds story/draft_table.json and story/draft_table.md (angle: "The Chronicler's Table").
# Single source of truth for both files. Run: python3 build_draft_table.py
import json, os

ROOT = "/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa"
OUT_JSON = os.path.join(ROOT, "story", "draft_table.json")
OUT_MD = os.path.join(ROOT, "story", "draft_table.md")
FPS = 30
TOTAL = 1984

TITLE = "CHRONICA: The Chronicler's Table"
LOGLINE = ("On a candle-lit walnut table, seen from the exact seat of the game's main menu, a flat embroidered map "
           "of one realm and a rolled chronicle wake up: the oath is stitched, the king is unpicked from it, the "
           "candles die, a silent war rises and sinks in the cloth, the chronicle burns through to the map below, "
           "and at dawn the map is cut, padded and raised into the game's own hex board, until a blank parchment "
           "and the Chronica banner complete the menu, frame for frame, and the question is handed to the player.")

shots = [
 dict(id="S01", name="Night at the Chronicler's Table", start_frame=0, end_frame=121,
  audio_event="f0-3 digital silence. f4 D drone fade-in + 'There' (strongest attack of the file, f5); f18 'a' onset; f39 'world' (stressed); drone/bass swell f76 under 'one'; f91 'realm'; f104-121 music-only gap (Dadd9 drone, -37 dBFS).",
  visual_action="f0-3 black #07070A. f4: the left candle wick catches at its exact menu position (candle_left rect 9.6,686.9 92x331); f18: the right one. Their 1900 K pools find the Chronicler's Table from the player's seat: the walnut top bar in silhouette with the logo rod still bare (the valance is rolled tight on it), the blue- and red-lion side banners in shadow, the two carved lions rim-lit at the near corners. On the table lies the flat embroidered map of the one realm: the same coast and land as the final game board, but stitched flat in Bayeux laid-and-couched wool in aged dyes (woad sea with paired wave lines, mustard and sage fields, olive forests, stem-stitch roads, small stitched towns), with no hex grid. It is softly creased in a 3x2 grid where it was folded for a century, and ONE continuous couched gold thread runs round its whole coastline. On the left, where the parchment card will one day lie, the rolled chronicle waits, tied with a cord. f39 'world': the light settles. f85-104 'one realm': the left flame sways and a single metal glint runs all the way round the gold border, once.",
  camera="f0-40 locked exactly on the menu camera (pitch 66.09 deg, vertical FOV 30 deg): the bookend of the last frame. f40-121 slow exponential push-in (1.0 -> 1.35x) and tilt 66 -> 78 deg toward the roll. Azimuth never changes.",
  technique="2.5D. The map is one plane, so its perspective view is an exact homography of a 4K flat map plate (albedo, height_mm, tangent and material maps built with the stitch_ref.py functions from a land/terrain mask derived from a top-down demo-mode plate of seed 4242; region borders smoothed off the hex grid). Per-frame relight with two candle point lights in table coordinates (inverse-square falloff, elevation 12-18 deg, flicker = 1-3 Hz sway + 8-12 Hz, 6-12 %) and a cool #141325 fill. Menu sprites (bar_top, banner_side_left/right, lion_statue_left/right, candle_left/right, logo rod with rolled valance) sit on cards projected by the same camera; they get luminance-derived normals and are ratio-relit to near-silhouette with a warm rim. Candle flames are inpainted to dark wicks, then regrown from the flame cut-out with a small glow halo. The border glint is Kajiya-Kay on the gold-thread tangent, so it travels on its own as the flame moves.",
  material_behavior="Linen ground #D4BE98, weave visible only where the raking light catches it; wool matte (sheen 6 % or less); only the gold border glints (metal 180/1.4, tinted #E9BE6A). Ageing at about 30 % of survey density: foxing, two tidelines, one mend; fold creases 0.5 mm high catch the light. Candles at 1900 K seen through a 3200 K white balance.",
  transition_out="Continuous: the push-in carries into S02 as the cord slips off the roll.",
  emotional_purpose="Hushed wonder and quiet foreshadowing: we sit where the game will begin, in the world before it was divided.",
  est_render_cost="2.5D ~1.5 s/frame x 122 = ~3 min. Prep ~2 h (flat map plate from the game top-down plate, sprite cards, candle inpaint).",
  eevee_frames=0, eevee_res="-", lights="L candle on f4, R candle on f18, cool fill",
  assets="demo-mode top-down plate (layout), stitch_ref.py, bar_top, banner_side_left/right, lion_statue_left/right, candle_left/right, logo_banner rod"),

 dict(id="S02", name="The chronicle unrolls: one table, one oath, one crown", start_frame=122, end_frame=275,
  audio_event="f126 'one' + drone re-swell (bass f126); f140 'table' (accent #18); f162 'one', f173 'oath'; near-silence f185-198 (-45 dBFS) then a +10 dB swell f198-212; f212 'one', f230 'crown' (attack f229, accent #7); f248-275 music-only gap (Dmaj7).",
  visual_action="f122: the cord slips off and the roll unrolls rightward across the map. Its diameter shrinks and the reverse of the embroidery (knots, thread tails, crossing floats) shows on the turning roll; a soft wave settles behind it, with a contact shadow under the roll. On 'table' (f134-140) the stitched banquet table of panel p1 slides under the camera; the cloth is flat by f160 apart from one gentle residual fold. f167-184 'one oath': the candle glint runs along the couched gold hilt and down the blade of the sword the four lords touch. f198-212: both flames lift and brighten with the music swell. f224-248 'one crown': the camera eases toward the king; the crown's metal thread flares at f230, then settles. The king is kept on the right third, to avoid p1's symmetry.",
  camera="f122-160 the tilt continues to a true rostrum (90 deg) as the push lands at F0 (full frieze height plus ~30 mm of map margin above and below, ~3.0 px/mm). f160-275 slow push F0 -> 1.4x panel-native (~3 px/frame) toward the king, drifting right 2 px/frame.",
  technique="f122-177: Eevee 1080p 8 TAA on ones (56 renders): walnut plane, map plane (S01 maps), frieze strip with a geometry-nodes roll-out (spiral curl along x), two candle point lights, contact shadows. Eevee outputs UV and shading-ratio passes, so the compositor re-applies the exact p1 albedo and the handover to the 2.5D plate at f178 is seamless. f178-275: 2.5D. p1 is ratio-relit with LIC-synthesised strand normals (bible 5.2) plus a low-frequency fold height field; metal masks on the sword, crown and goblets.",
  material_behavior="p1 needle-painted wool keeps its baked modelling (relight ratio clamped 0.6-1.5). Gold reads as metal thread, its glint travelling along the tangent. On the roll, the linen reverse shows rougher, hairier wool tails (fuzz x2).",
  transition_out="Continuous into S03 (same panel).",
  emotional_purpose="Plenitude and order: the golden age is a solid object lying on a table.",
  est_render_cost="Eevee 56 x ~12 s = ~11 min; 2.5D 98 x ~1.2 s = ~2 min.",
  eevee_frames=56, eevee_res="1920x1080 8 TAA, ones", lights="L + R candles; flare f198-212",
  assets="intro/p1_oath, S01 map plate, procedural walnut"),

 dict(id="S03", name="Cups raised, an oath sworn, a thread that never ends", start_frame=276, end_frame=445,
  audio_event="f276 'They', f285 'raised' (bass f296), f308 'cups' (accent #11); bass f323 in the gap; f339 'and', f349 'swore' + strongest early drone swell f358 (accent #4); f367-402 'it would never end' ('end' f391); f402-445 music-only gap (1.46 s, Dmaj7; swell f428).",
  visual_action="f279-308: the five gold goblets on the stitched table lift 6-10 mm off the cloth as rigid cut-outs on twos, their shadows lengthening away from the left candle; they hang at the top of the lift on 'cups'. f344-372 'swore': a single glint runs from the sword's hilt to its tip under the four lords' hands; the goblets settle back (f350-380). f362-402 'it would never end': a stem-stitched titulus, HIC OMNES IVRAVERVNT, stitches itself left to right along the lower border (blue-black wool, 3.5 mm stitches popping in on twos, led by a steel glint). After the last letter the same thread keeps running right as a single line that never stops. f402-445: the camera follows that thread across the seam between p1 and the next length of linen, where a stitched interlace tree (the Bayeux scene divider) passes through frame as a wipe.",
  camera="f276-330 pull back from 1.4x to F0 (1.0x) to hold all the goblets. From f349, truck right following the stitching head, easing up to ~15 px/frame by f402 (180 deg motion blur above 12 px/frame). The seam is crossed f420-445.",
  technique="2.5D. Goblet cut-outs with LIC-resynthesised tablecloth inpainted underneath; lift = offset + soft contact shadow. Titulus built from cinzel-latin-700 skeletons as stem-stitch rope (3.5 mm chords, baseline wobble +/-0.8 mm, letter height +/-6 %); stitch_id order drives the pop-on. Seam and tree divider are procedural laid-and-couched work.",
  material_behavior="Goblets are metal gold, glinting only at the top of their lift. Titulus wool is matte blue-black #22232F with a fuzz halo. Thread boil on twos only on the stitches that are moving.",
  transition_out="Continuous truck right into S04: the thread leads us to the death.",
  emotional_purpose="Solemn certainty, with irony: the vow's thread runs straight on into what will end it.",
  est_render_cost="2.5D 170 x ~1.5 s = ~4 min. Prep ~3 h (goblet masks, titulus generator, tree divider).",
  eevee_frames=0, eevee_res="-", lights="L + R candles",
  assets="intro/p1_oath, style/fonts cinzel-latin-700"),

 dict(id="S04", name="Then the king died, and left no heir", start_frame=446, end_frame=531,
  audio_event="f446 'Then', f458 'king', f469 'died' (stressed; a word the bible allows to cut on); the drone exits: -6 dB f480, -15 dB f534; bass f495; f498-532 'and left no heir' ('heir' f522).",
  visual_action="The truck decelerates over panel p3: the king lies in state on the purple-draped bier between four stitched candles. f463-470: off-screen right, the right candle is snuffed. Its warm pool drains from the right half of the cloth in 8 frames, and only the left candle rakes the scene (Act II: 1900 K, 12 deg, key:fill 6:1, saturation 0.7); the folds of the drape deepen. f498-531: slow drift along the body to the crowned head; on 'heir' f522 the crown's gold catches one last, dull glint.",
  camera="Truck right decelerating from ~15 to 2 px/frame by f475 (landing on 'died'), then a slow drift right and a push 1.0 -> 1.2x toward the head.",
  technique="2.5D ratio relight of p3 (LIC normals + fold field) with an animated light rig (the right key fades out).",
  material_behavior="The king's purple (madder over woad, reserved for him) loses chroma as the light drops. The crown's glint is dimmer and broader, with a tarnished stretch (#7A5A2A) on the shadow side.",
  transition_out="Candle dip (S05): the left flame bends in a draught and the frame sinks toward dark.",
  emotional_purpose="Sudden loss: the light literally leaves the room.",
  est_render_cost="2.5D 86 x ~1.2 s = ~2 min.",
  eevee_frames=0, eevee_res="-", lights="R candle snuffed f463-470; L only",
  assets="intro/p3_death"),

 dict(id="S05", name="The draught", start_frame=532, end_frame=560,
  audio_event="Music-only gap f532-560 (F6 / Dm7add9, about -28 dBFS): the lament chords take over as the drone dies (-25 dB at f548).",
  visual_action="A draught bends the left flame and the light on p3 sinks to about -3 EV (never black: the cool fill holds the linen). Under that darkness the camera travels back right-to-left along the chronicle (regression). As the flame straightens (f552-560) we are over the oath scene again.",
  camera="Fast R->L truck (~60 px/frame, 180 deg blur), hidden by the dip; lands on p1 at 0.8x panel-native by f560.",
  technique="2.5D. If the blur smears, replace the travel with a hidden cut at f546, the darkest frame.",
  material_behavior="Only the low-frequency fold relief reads in the dip; the stitches sink into the cool fill.",
  transition_out="The recovering flame reveals S06.",
  emotional_purpose="A held breath; time turning back on itself.",
  est_render_cost="2.5D 29 frames, under 1 min.",
  eevee_frames=0, eevee_res="-", lights="L candle dips to -3 EV and recovers",
  assets="intro/p3_death, intro/p1_oath"),

 dict(id="S06", name="The empty chair", start_frame=561, end_frame=716,
  audio_event="f561 'and', f567 'every', f578 'lord' (stressed), f601 'sat', f621 'table', f637 'looked', f656 'empty', f669 'chair'; lament chords (Dm9/F colour, about -28 dBFS); gap f681-716 (F6).",
  visual_action="Back at the oath, but the king is coming undone. f561-640: his stitches unpick themselves from top to bottom. The couching bars release first; the laid purple, ermine and beard strands slacken in a ripple, lift and curl 5-20 mm off the cloth, then pull out through the linen (thread boil on twos). What remains is bare linen pricked with needle holes and the faint red-brown underdrawing of his silhouette on the throne: the empty chair is a king-shaped absence. The four lords, and their wool, stay. The gold crown, couched metal from the heraldic register, is not unpicked: it stays hanging where his head was, lifted 8 mm and casting a soft shadow into the void. f637-681: the push arrives on the void on 'empty chair'.",
  camera="Exponential push-in from 0.8x to 2.2x panel-native toward the throne (scale(t) = s0*(s1/s0)^ease), arriving f664; hold with 2 px/frame drift through the gap.",
  technique="2.5D plate: p1 minus the king, with linen re-synthesised where he was and underdrawing traced from p1's edges as red-brown running lines. Plus an Eevee thread-lift layer: the king's strands as curve geometry following the LIC direction field, lifted and pulled out, rendered top-down on twos at 1080p (48 renders, f561-656) and composited with contact shadows. The push to 2.2x native needs LIC re-synthesis (allowed up to 2.5x).",
  material_behavior="Unpicked wool is crinkled, kinked where it was couched, and hairier at the cut ends. Needle holes are 0.6 mm with a slight linen halo. Underdrawing is ink-like, with no relief.",
  transition_out="Continuous into S07 (same plate).",
  emotional_purpose="Absence: every gaze in the scene converges on a hole in the cloth.",
  est_render_cost="Eevee 48 x ~8 s = ~6 min; 2.5D 156 x ~1.5 s = ~4 min. Prep ~4 h (king strand extraction, underdrawing).",
  eevee_frames=48, eevee_res="1920x1080 8 TAA, twos (layer only)", lights="L candle only (1900 K, 12 deg)",
  assets="intro/p1_oath, intro/p1_empty (as a mask reference only)"),

 dict(id="S07", name="His own head beneath the crown", start_frame=717, end_frame=796,
  audio_event="f717 'and', f724 'saw', f741 'own' (stressed), f753 'head', f766 'beneath', f785 'crown'; the fullest lament (23-25.5 s), low swell f750; the phrase ends f799.",
  visual_action="Over each lord's head in turn (gold, red, blue, green; f726, f738, f750, f762) a ghost crown is drawn in faint red-brown underdrawing, the designer's line that was never stitched: each lord imagines himself crowned. On 'crown' (f779-790) the real gold crown above the void glints once more, and its shadow slides a few centimetres as the last flame leans.",
  camera="Pull back from 2.2x to 1.4x (f717-745) to hold all four lords and the throne; drift 2 px/frame.",
  technique="2.5D. Ghost crowns: the crown silhouette (intro/crown) traced to running-line underdrawing and revealed in stitch order. The real crown's shadow is its alpha offset by the moving light vector.",
  material_behavior="Underdrawing has no relief and no sheen (ink on linen). The gold crown is the only highlight in frame.",
  transition_out="The last candle gutters (S08).",
  emotional_purpose="Ambition and suspicion: the seed of a hundred years of war.",
  est_render_cost="2.5D 80 x ~1.2 s = ~2 min.",
  eevee_frames=0, eevee_res="-", lights="L candle, leaning",
  assets="intro/p1_oath, intro/crown"),

 dict(id="S08", name="The last candle", start_frame=797, end_frame=843,
  audio_event="The music collapses about 20 dB at f797; near-silence (-47 dBFS) f797-843: the strongest internal boundary of the score.",
  visual_action="f790-806 the left flame shrinks and dies; the crown's glint is the last thing to fade (f812). Then black (#07070A floor), with only the cool fill grazing the linen weave at about -4 EV and the dull orange of the wick's ember at the left edge of frame. From f832 a low red-orange glow begins to rise from the bottom edge of the frame: a hearth, off-screen.",
  camera="Locked.",
  technique="2.5D light animation on the S07 plate.",
  material_behavior="Only the weave relief reads, under the raking cool fill; no colour.",
  transition_out="Out of the dark, S09 starts in macro inside the weave, lit from below by the hearth.",
  emotional_purpose="Void. The light that dies is the music that dies.",
  est_render_cost="2.5D 47 frames, under 1 min.",
  eevee_frames=0, eevee_res="-", lights="L candle dies f790-806; darkness; hearth glow starts f832",
  assets="S07 plate"),

 dict(id="S09", name="A hundred years, and nothing", start_frame=844, end_frame=981,
  audio_event="f844 'The', f850 'wars', f867 'lasted', f884 'hundred', f899 'years' (stressed), f918 'and', f925 'ended', f942 'nothing'. The music is near-silent throughout (-45 dBFS or less; a thin, airy, high texture) with a second silent gap f952-979.",
  visual_action="Hearth light (2200 K, from below, 2-6 Hz flicker at 15-25 %) glows up through the gaps in the linen weave. The camera is inside the cloth, gliding between ridges of warp and weft, and rises over a thread into the next length of the chronicle: a stitched dusk sky (war_bg) over hills, and ranks of soldiers lying flat as stitched slips (the game's figure cards in realm tints: red legion, blue merchants, gold builders, green nomads). From f845 ('wars' f850) they rise: each figure hinges up at the feet like a detached stumpwork slip on its wire, standing to 70-80 deg and throwing a long shadow away from the fire. 'lasted a hundred years': the lines swap idle and strike poses on twos (game key poses, 0.12 s lunge), clash and fall flat, and new ranks rise behind them: generations. 'ended nothing' (f925-955): every figure sinks back flat and its stitches pull out through the linen, leaving needle-hole outlines on bare cloth. f955-981, in silence: the camera cranes up over the empty, pricked linen.",
  camera="f844-866 macro dolly at F3 (~50 mm field, f/8, 15 deg tilt, ~1.6 mm focus band) between thread ridges. f866-955 low tracking shot ~8 mm above the cloth, travelling right-to-left (regression) at a slow constant speed. f955-981 crane up to a 45 deg view. Real 3D: the only shot where the cloth plane is far from facing the camera, on purpose.",
  technique="Eevee 1080p 8 TAA on ones (138 renders). Procedural linen weave geometry for the macro (displaced grid, ~1M verts, 23 frames); war_bg on the ground plane with LIC normals; figure cards from tex_tinted (albedo + normal + mask) as 1.5 mm padded cards (solidify + edge bevel) hinged at the feet; an area light from below for the hearth; real DOF. Poses switch on twos while the camera moves on ones. Upscale to 1440p with Lanczos plus the compositor's fuzz and grain pass.",
  material_behavior="Figure cards keep the game's padded satin (the mask's B channel drives thread glints); the ground cloth is matte. Firelight makes the fuzz haloes glow on the edges of the risen slips. Stitch boil on twos on the moving figures only.",
  transition_out="Hard cut at f981, one frame before 'Cities'.",
  emotional_purpose="Futility: a war fought in silence, at soldier height, that leaves only holes.",
  est_render_cost="Eevee 23 x ~40 s + 115 x ~18 s = ~50 min.",
  eevee_frames=138, eevee_res="1920x1080 8 TAA, ones", lights="hearth from below 2200 K, flicker",
  assets="intro/war_bg, tex_tinted figure cards (legionary, man_at_arms, spearman, knight, archer, mercenary) + normal/mask maps"),

 dict(id="S10", name="Cities fell to ruin", start_frame=982, end_frame=1050,
  audio_event="f982 'Cities' (attack f987, accent #17), f999 'fell' (accent #22), f1009 'to', f1015 'ruin'; a soft pad returns at f1017 (+5 dB; crescendo f1001-1061); near-silence f1029-1047.",
  visual_action="Panel p6: the walled city burning. Its stitched flames move (laid strands shifting phase at 2-4 Hz, outer strands lagging) and its smoke spirals turn; their light adds to the hearth. f994-1001 'fell': the tall central tower drops 6-10 mm and askew in two stop-motion steps, a crack opening in its stitched masonry. f1009-1028 'to ruin': the stitched fire scorches the real linen. Browning spreads out from the flames, chars and burns through; holes open with thin glowing ember rims and their edges curl up; through them the map cloth underneath appears, lit by the embers. On the pad's return (f1017) the burn accelerates, and by f1050 most of the chronicle in frame has burned away.",
  camera="F1 locked, with 2 px/frame drift right-to-left and a 2 deg dutch angle (Act III).",
  technique="2.5D. p6 relight; flame and smoke cut-out animation. The burn is an advancing distance field from the flame masks plus fbm noise, with a colour ramp linen -> foxing #9C7046 -> soot #3A3330 -> char, an ember rim of 1-3 px (#DE6A2C -> #F6B54A, flickering) and the curled edge as a relit height lift with shadow. The revealed layer is the S11 map plate lit by the ember light.",
  material_behavior="Wool singes faster than linen (fills blacken while outlines hold a beat longer). The ember glow is the only emissive. No flying particles.",
  transition_out="The burn-through itself reveals the map (S11).",
  emotional_purpose="Violence and loss: the chronicle is consumed by what it depicts.",
  est_render_cost="2.5D 69 x ~3 s = ~4 min. Prep ~3 h (burn simulation).",
  eevee_frames=0, eevee_res="-", lights="hearth + stitched-fire glow + embers",
  assets="intro/p6_ruin, S11 map plate"),

 dict(id="S11", name="Roads swallowed by the forest", start_frame=1051, end_frame=1137,
  audio_event="f1051 'Roads' (stressed), f1075 'swallowed', f1096 'the', f1101 'forest'; M4 soft pad plateau (-40 dBFS); gap f1115-1137 (Dm add9).",
  visual_action="Beneath the ash lies the map of the one realm, seen top-down and warmly lit by the dying embers and the hearth. Its stem-stitched roads run between the towns. Green stem-stitch tendrils and couched leaves stitch themselves over the roads from the forests (each stitch-on led by a needle glint), the olive forests spread into the fields, and a road vanishes under the camera on 'forest'. A few charred threads of the chronicle lie at the right edge.",
  camera="Rostrum (90 deg) at F1 on the map, trucking right-to-left (regression) at 6-8 px/frame along a main road.",
  technique="2.5D. The map plate (S01 maps, top-down) plus procedural stitch-on growth (L-system tendrils along road splines, stitch_id order), relit with hearth and ember light.",
  material_behavior="New growth in fresh forest green and sage. The roads (couched dashes in buff) disappear thread by thread. No boil on the static cloth.",
  transition_out="Continuous truck into S12.",
  emotional_purpose="Desolation turning quiet: nature reclaims what men abandoned.",
  est_render_cost="2.5D 87 x ~1.5 s = ~2 min. Prep ~2 h (growth generator).",
  eevee_frames=0, eevee_res="-", lights="hearth + embers, low",
  assets="S01 map plate"),

 dict(id="S12", name="Beyond their own borders", start_frame=1138, end_frame=1253,
  audio_event="f1138 'Men' (accent #24), f1149 'forgot' (accent #28), f1182 'beyond', f1201 'own', f1211 'borders' (stressed); gap f1229-1253 (D7 with F#, in-gap swell).",
  visual_action="The camera reaches the one gold border of S01. Its tie-downs pop one by one; the gold thread slackens, lifts and is drawn away, then is re-couched as four separate closed borders. Each is a thick running-stitch cord in its realm's colour (gold, crimson, royal blue, green) between brown edgings, exactly the game's border idiom (border.gdshader). They close on 'borders' (f1205-1211). Beyond each border the cloth forgets: dyes bleach toward bare linen, foxing and tidelines bloom in time-lapse, and padded quilted cloud patches (the game's fog-of-war kit) are appliqued over the unknown lands.",
  camera="The truck continues right-to-left, slowing to 2 px/frame by f1200; from f1229 an exponential pull-back starts.",
  technique="2.5D. Couched-thread simulation (a 2D spline with slack, lift height and a travelling glint), procedural ageing masks, and cloud_puff_* / cloud_edge_* sprites with luminance-derived normals, relit.",
  material_behavior="Gold metal thread (glinting) becomes four wool and silk cords (sheen 10-15 %). The fog quilts are cream cotton with brown running-stitch outlines, puffing 2-3 mm.",
  transition_out="Continuous pull-back into S13.",
  emotional_purpose="Estrangement: the one realm splits into four suspicious kingdoms.",
  est_render_cost="2.5D 116 x ~2 s = ~4 min. Prep ~3 h.",
  eevee_frames=0, eevee_res="-", lights="hearth, sinking",
  assets="S01 map plate, table_clouds/cloud_puff_1-8, cloud_edge_1-3, cloud_fill, crest colours from palette.json"),

 dict(id="S13", name="The world grew dark at its edges", start_frame=1254, end_frame=1381,
  audio_event="f1263 'world', f1281 'grew' + BASS ENTRY f1283 (+26 dB in 22-120 Hz, the biggest musical event), f1292 'dark', f1319 'edges'; gap f1336-1381 with bass pulse #2 at f1345.",
  visual_action="The pull-back reveals the whole map cloth lying on the walnut table, with the four realms and their fog. It stops on the bass entry (f1283) and the darkness surges: the quilted fog rolls in from all four edges of frame, the cloth's own edges fray (weft threads slide out, the hem unravels) and the hearth sinks. By 'edges' (f1319) the frame edges sit at -2.5 EV and only the centre of the map is still lit. f1336-1381: near-still; on the bass pulse f1345 the pool of light contracts once more, like a held breath. Only the four border cords glint faintly.",
  camera="Exponential pull-back from F1 to the whole-map framing (~2.2x -> 1.0x) f1229-1283, landing with an ease-out on the bass; then locked with 1-2 px/frame drift.",
  technique="2.5D. Fray = procedural thread pull-out at the cloth edges; the fog edge kit as padded layers sliding in, relit; a global light falloff (a physical vignette, not an overlay).",
  material_behavior="Frayed linen: loose weft threads with fuzz, lifted 1-3 mm. The fog quilts are matte; the four cords carry the only sheen.",
  transition_out="Light change (S14): dawn enters from the left on 'Now'.",
  emotional_purpose="Dread, then stillness: the lowest point before renewal.",
  est_render_cost="2.5D 128 x ~2 s = ~4 min.",
  eevee_frames=0, eevee_res="-", lights="hearth dies to embers; edges -2.5 EV",
  assets="S12 plate, cloud kit, procedural walnut"),

 dict(id="S14", name="Now: dawn", start_frame=1382, end_frame=1435,
  audio_event="f1382 'Now' (a cut-strength word), f1395 'every', f1407 'ruler' + bass pulse f1410, f1419 'believes' (stressed), f1432 'the'.",
  visual_action="A shaft of dawn light (4300 K, elevation 28 deg) slides in from the left as if a shutter had opened, and sweeps left to right across the map in about 3 s. Where it touches, the fog quilts peel back and lift away toward the edges (the game's own fog reveal), and the dyes revive from aged to fresh (OKLab interpolation, staggered 0.2-0.4 s per region). f1404-1430 'every ruler': at the four capitals the four realm crests (padded satin: builders, legion, merchants, nomads) flash one after another as the light crosses them, lifting 5 mm.",
  camera="Whole-map top-down; a slow push-in (1.0 -> 1.15x) toward the region that will become the menu view.",
  technique="2.5D relight with a moving area light; fog peel = sprite translate + lift + shadow; colour revival per region; crests ui/crest_* at 1.2x native or less with a satin anisotropic flash.",
  material_behavior="Wool moves from aged to fresh dye values. The satin crests flash according to their stitch direction (40/0.15 lobe) as the sweep passes. Fold creases flatten under the higher dawn light.",
  transition_out="Continuous into S15: the light keeps sweeping as the cloth begins to rise.",
  emotional_purpose="Hope: a new day, and new ambitions.",
  est_render_cost="2.5D 54 x ~2 s = ~2 min.",
  eevee_frames=0, eevee_res="-", lights="dawn window 4300 K from the left, sweeping L->R",
  assets="ui/crest_builders, crest_legion, crest_merchants, crest_nomads, cloud kit"),

 dict(id="S15", name="Made whole: the cloth becomes the board", start_frame=1436, end_frame=1523,
  audio_event="f1436 'world', f1458 'made', f1466 'whole' + bass pulse f1471, f1477 'again' (the phrase ends f1491); gap f1491-1523: Bbmaj7 with a sustained Bb3 horn, the brightest and most hopeful colour of the score.",
  visual_action="The flat map is remade as the game's board, following the game's own textile logic. f1436-1462: a cream running stitch races along a hex grid across the land, cutting the organic regions into hexagonal coupons, and each coupon takes its terrain's fill stitch (couched rows for plains, olive satin for forest, undulating rows for hills, diagonal satin for mountains, a light-blue couched cord for rivers). f1458-1480 ('made whole', bass f1471): capitonnage. Every coupon is padded from beneath and swells into a soft quilted tile that darkens toward its seams, in a ripple outward from the menu's focus settlement; the sea sinks a little and becomes denim couched rows with cream wavelets. f1470-1500: stumpwork. The flat stitched towns hinge up and inflate into the game's own 3D models (capital, settle_*, walls, farm, lumber, watchtower), forest hexes raise their stumpwork trees, and unit slips stand up; the four border cords settle against the hex edges with their short down-right shadow. The camera, which started top-down, tilts and glides low over the rising world (into the miniature), then begins to climb back.",
  camera="3D, no orbit (azimuth fixed): top-down 90 deg -> dolly down and tilt to ~55 deg by f1490 (a low glide with f/5.6-equivalent DOF for miniature scale) -> the start of the climb toward the menu camera.",
  technique="Eevee 1080p 8 TAA on ones (88 renders). The hex board is generated from the real map layout (hex centres projected from the top-down demo-mode plate of seed 4242); each hex has a puff shape key (dome + seam pinch) with stagger. Materials crossfade from the flat-embroidery bake to an Eevee port of the terrain.gdshader / water.gdshader / border.gdshader fills (the stitch.gdshaderinc patterns baked as normal + albedo tiles). The 59 OBJ models get a piece.gdshader port (palette colour, brown outline hull, triplanar stitch bump). Fuzz and grain are added in the compositor.",
  material_behavior="From laid wool on linen to the game's patchwork: puffed coupons with cream running-stitch seams over a dark groove, a matte wool sheen at grazing angles, couched gold only on the player's border. The dawn key from the upper left (az 135 deg, el 28 deg) matches the game's down-right shadows.",
  transition_out="Continuous camera into S16.",
  emotional_purpose="Renewal and wonder: the world becomes tangible and playable.",
  est_render_cost="Eevee 88 x ~25 s = ~37 min.",
  eevee_frames=88, eevee_res="1920x1080 8 TAA, ones", lights="dawn key 4300 K az 135 el 28 + warm fill",
  assets="demo-mode top-down plate, models/*.obj (capital, settle_0..settle_3_6, walls_1-3, farm, lumber, watchtower, settle_banner, units), shaders terrain/water/border/piece/stitch"),

 dict(id="S16", name="One banner, one village", start_frame=1524, end_frame=1598,
  audio_event="f1524 'One', f1533 'banner' + bass pulse f1536 (accent #16); f1559 'one', f1569 'village'; gap f1583-1598.",
  visual_action="The camera climbs and settles toward the player's seat. f1528-1540 'banner': at the focus settlement, the player's banner (settle_banner, the builders' gold hammer) unfurls on its pole and catches the sun. f1563-1575 'village': on a hex to the right, a village rises in two stop-motion steps (camp settle_0 -> cottages settle_1), the stitches of its plot puckering as it lifts. As the view widens, the table's frame comes back in from the edges: the walnut bar with the rolled valance on its rod from the top, the side banners, the lion statues at the near corners, and the two candles (cold wicks) at the sides. From f1540 the board's material converges onto a camera projection of the real game plate, so that by f1598 the render equals the live board.",
  camera="3D climb and tilt from 55 to 66.09 deg, ending on the menu camera at 1.04x framing at f1598 (ease-out); azimuth fixed.",
  technique="Eevee 1440p 16 TAA on ones (75 renders). Final-frame match: the board albedo blends into a projection of the 2x demo-mode plate taken from the menu camera (masked where the banner and the village are still animating). Frame sprites are composited in 2.5D through homographies driven by the exported camera track, so they are exact at the menu camera.",
  material_behavior="Stumpwork pieces with brown cord outlines; banner silk with a satin sheen. The parchment is not yet in frame.",
  transition_out="The camera arrives and stops; the swap to the real plate completes under the card drop (S17).",
  emotional_purpose="A personal foothold: your banner, your first village.",
  est_render_cost="Eevee 75 x ~60 s = ~75 min (~62 min with two processes).",
  eevee_frames=75, eevee_res="2560x1440 16 TAA, ones (hero)", lights="daylight key (game look) + cold candles",
  assets="models/settle_banner, settle_0, settle_1; demo-mode menu-camera plate at 2x; bar_top, banner_side_*, lion_statue_*, candle_*, logo rod"),

 dict(id="S17", name="One blank page", start_frame=1599, end_frame=1688,
  audio_event="f1599 'one' + bass pulse f1599 (+21.6 dB, accent #5), f1614 'blank', f1630 'page' (ends f1645); gap f1645-1688 with bass pulse f1664.",
  visual_action="The board is now the real game plate (swap f1590-1605, invisible by construction). f1593-1612: a parchment sheet in its walnut frame with brass studs (menu_card) is laid on the table at the left. It descends from above the lens (scale 1.15 -> 1.0, rotation 3 -> 0 deg), its soft shadow tightening and a 6 px air-cushion slide, landing at exactly (224,319)-(1227,1376) on 'blank' (f1614). It is blank: only a faint drypoint ruling for the title line and for the rule under the subtitle catches the light on 'page' (f1626-1640). No button rows are ruled, because their number depends on saved games. f1662: on the bass pulse the left candle's wick catches again.",
  camera="Slow zoom 1.04 -> 1.02x (a pure scale of the composite, which is exact for a fixed camera).",
  technique="2.5D. Real game plate at 2x; menu_card as a 9-slice with the game's margins (or captured from the game with its labels hidden) at the measured rect; drop shadow; the ruling as embossed hairlines in the height map; candle ignition as in S01.",
  material_behavior="Parchment: matte, slightly translucent at the edges, faint cockling. The walnut frame's brass studs glint in daylight.",
  transition_out="Continuous into S18.",
  emotional_purpose="Possibility: the page is yours to fill.",
  est_render_cost="2.5D 90 x ~1 s = ~2 min; game plate at 2x ~3 min.",
  eevee_frames=0, eevee_res="-", lights="daylight; L candle relit f1662",
  assets="table_parchment/menu_card (or game capture), demo-mode plate, candle_left"),

 dict(id="S18", name="When this age is remembered: the name", start_frame=1689, end_frame=1782,
  audio_event="f1689 'When', f1707 'age', f1726 'remembered' + bass pulse #8 f1726; CLIMAX gap f1744-1783 (the loudest music, -25.6 dBFS, F6/Bbmaj7) with a bass swell at f1755 and the peak at f1760.",
  visual_action="f1703-1710 'age': the right candle relights; both flames now burn as they do in the menu. f1722-1744 'remembered': the valance rolled on the rod at the top of the frame unrolls downward; the navy velvet unfurls flat and the gold bullion fringe and the two tassels drop and swing. f1744-1756: the gold thread of the title couches itself letter by letter, 'Chronica' racing left to right behind a travelling glint, crown and fleurs-de-lis last, finishing on the bass swell f1755. f1756-1772: the climax. A gold sheen sweeps left to right across the finished title, peaking at f1760 (the only frames in the film where metal reaches #FFF3D6).",
  camera="Zoom 1.02 -> 1.01x, effectively locked.",
  technique="2.5D. The logo_banner layer at its final rect (784,0,992x296), sourced from logo_title for 1.75x headroom. Analytic roll-unfurl (cylinder shading on the rolled part); fringe and tassel cut-outs on damped pendulums (period ~1.1 s); letter stitch-on from the skeleton of the gold-letter mask, ordered left to right; an anisotropic sheen band driven by the letters' thread-direction field.",
  material_behavior="Heraldic register: padded gold on navy velvet, raised 1.5-2.5 mm, with the metal glint travelling along the couched thread. The velvet absorbs; the gold flares.",
  transition_out="Continuous into S19 as the music recedes.",
  emotional_purpose="Triumph and identity: the chronicle has a name.",
  est_render_cost="2.5D 94 x ~1.5 s = ~3 min. Prep ~3 h (letter skeleton order, fringe rig).",
  eevee_frames=0, eevee_res="-", lights="daylight; R candle relit f1703-1710; sheen peak f1760",
  assets="table_tapestry/logo_title, logo_banner, candle_right"),

 dict(id="S19", name="What will the chronicles say of you? (hand-off)", start_frame=1783, end_frame=1983,
  audio_event="f1783 'what': the music recedes ~19 dB by f1824 (bass gone f1823); f1801 'chronicles' (stressed), f1824 'say', f1838 'of', f1846 'you?' (ends f1855); f1855-1983 ring-out of a high, unresolved chord (Am7/C6 colour), no fade, ending at about -48 dBFS.",
  visual_action="The fringe's sway decays. On 'chronicles' (f1797-1810) a last soft glint runs along the title; on 'you?' (f1846) the drypoint ruling on the blank card catches the light once. From f1855: near-still, exactly the menu composition (walnut bar, logo valance, blank parchment card, burning candles, blue- and red-lion banners, carved lions, and the real board in daylight). Only the candle flames live (sprite-local, 2-3 %), and the fringe settles below 1 px by f1880. f1983 is a clean poster: the overlay holds it while the engine starts (its gold progress thread at the bottom), then dissolves into the live menu, whose title and buttons appear on the blank page.",
  camera="Zoom 1.01 -> 1.00, easing out exactly at f1855; locked to the end.",
  technique="2.5D final composite, pixel-registered to 02_menu_first_frame (scaled to 2560): the real UI-free plate plus exact sprite rects from menu_layout.json. Acceptance: mean absolute difference under 2/255 outside the text, the candle flames and the card interior.",
  material_behavior="The daylight board plate is untouched; the sprites are not relit (as in the game).",
  transition_out="Overlay hold, then the 0.9 s CSS dissolve to the live main menu (intro_overlay_snippet.html).",
  emotional_purpose="The question handed to the player; calm readiness.",
  est_render_cost="2.5D 201 x ~0.5 s = ~2 min.",
  eevee_frames=0, eevee_res="-", lights="daylight + both candles",
  assets="all menu sprites, demo-mode plate"),
]

for s in shots:
    s["frames"] = s["end_frame"] - s["start_frame"] + 1
    s["start_s"] = round(s["start_frame"] / FPS, 3)
    s["end_s"] = round((s["end_frame"] + 1) / FPS, 3)

# integrity checks: contiguous coverage of 0..1983
prev = -1
for s in shots:
    assert s["start_frame"] == prev + 1, (s["id"], s["start_frame"], prev)
    assert s["end_frame"] >= s["start_frame"]
    prev = s["end_frame"]
assert prev == TOTAL - 1, prev
assert sum(s["frames"] for s in shots) == TOTAL

eevee_1080 = sum(s["eevee_frames"] for s in shots if s["eevee_res"].startswith("1920"))
eevee_1440 = sum(s["eevee_frames"] for s in shots if s["eevee_res"].startswith("2560"))
eevee_total = eevee_1080 + eevee_1440

six_keyframes = [
 dict(frame=91, shot="S01", description="One realm. The Chronicler's Table at night from the player's seat: two candle flames at the exact menu positions, the bare logo rod, the side banners in shadow, the carved lions rim-lit. On the table, the flat Bayeux-stitched map of the same world, creased from a century of folding, ringed by one continuous couched gold thread whose glint is racing round the coast. The bookend of the final frame."),
 dict(frame=669, shot="S06", description="The empty chair. A single left candle raking at 12 deg over the oath scene, with the king's figure unpicked: a king-shaped void of bare linen with needle holes and red-brown underdrawing on the throne, loose purple strands still curling off the cloth, the gold crown hanging alone above the void with its shadow, and the four lords' gazes converging on it."),
 dict(frame=899, shot="S09", description="A hundred years. A low tracking shot in hearth firelight from below: risen stumpwork soldiers (realm-tinted figure cards) mid-strike in silence, long shadows across the dusk-sky frieze, fuzz haloes glowing, shallow focus, fallen slips lying flat behind them."),
 dict(frame=1015, shot="S10", description="Ruin. The stitched flames of the burning city have set the real linen alight: browning, black char, thin ember rims and curled edges, and through the burnt holes the map cloth beneath, lit orange by the embers; the central tower hangs askew where it fell."),
 dict(frame=1471, shot="S15", description="Made whole (the 2D->3D moment). Dawn rakes in from the upper left. The flat map has been cut into hex coupons with cream running-stitch seams; the coupons are mid-swell, padded and darkening at their seams; towns are inflating up out of their flat stitched glyphs into the game's 3D models; the sea is sinking into denim rows. Camera low and tilted, with shallow miniature focus."),
 dict(frame=1760, shot="S18", description="The name. The full menu composition in daylight: walnut bar, the navy valance just unfurled with its fringe still swinging, the gold sheen at its peak across 'Chronica', both candles burning, the blank parchment card on the left, the real hex board. Three seconds later this becomes the hand-off frame."),
]

POC = ("'Capitonnage': a 5.0 s (150-frame) self-contained excerpt of S15 that proves a physically embroidered 2D map "
 "can become a convincing dimensional board. CONTENT: a 9x6-hex patch around the menu's focus settlement (layout from the "
 "top-down demo-mode plate; a hand-placed layout if that plate is not ready). Frames 0-30: the flat Bayeux map (organic "
 "regions, woad sea with paired wave lines, stem-stitch roads, one couched gold border, a flat stitched town glyph) seen "
 "top-down; a dawn light sweep (4300 K, az 135 deg, el 28 deg) reveals the couching-bar shadow grid. Frames 30-66: a cream "
 "running stitch races along the hex seams, cutting the cloth into coupons, and each coupon switches to its terrain fill "
 "stitch. Frames 60-100: capitonnage. The coupons swell 0 -> 4 mm in a ripple from the centre, pinching and darkening at "
 "the seams; the sea sinks 1 mm and its denim rows and cream wavelets gain relief. Frames 80-120: stumpwork. The town glyph "
 "hinges up and inflates into the settle_1 OBJ (stitch material, brown cord hull), three stumpwork trees stand up per forest "
 "hex, and the gold border becomes a running-stitch cord with its short down-right shadow. Frames 75-150: the camera tilts "
 "90 -> 66 deg with a slow dolly back, focus opening from a miniature f/5.6 to deep focus. TECHNIQUE: Blender 4.0.2 Eevee "
 "under xvfb (or bpy 5.2.2 Eevee-Next via EGL). Hex mesh generator; a per-hex 'puff' shape key (dome + seam pinch) with "
 "staggered drivers; the flat state textured with 4K maps from stitch_ref.py (albedo/height/tangent baked to normal), "
 "crossfading to baked tiles that port terrain.gdshader / water.gdshader / border.gdshader fills (stitch.gdshaderinc); "
 "models with a piece.gdshader port (palette albedo, inverted-hull outline, triplanar stitch bump); metal glint faked with "
 "stretched bump; fuzz halo and grain added in the numpy compositor. COST: 150 frames at 1280x720 8 TAA, ~8 s each = "
 "~20 min test pass, plus 6 hero stills at 2560x1440 16 TAA (~6 min), compositor ~1 min. SUCCESS CRITERIA: frame 0 "
 "is indistinguishable from the 2.5D flat-map plate (same maps); no frame reads as CG terrain (the padding must read as "
 "stuffed cloth: seam pinch, grazing sheen, fuzz); no weave shimmer during the tilt (prefiltered per bible section 3); "
 "the last frame sits within ~5 dE_ok of the game's menu plate in median colour per terrain class, shown side by side.")

budget = dict(
 eevee_1080p_renders=eevee_1080, eevee_1440p_hero_renders=eevee_1440, eevee_total_renders=eevee_total,
 limits="<= 600 Eevee frames at 1080p and <= 150 hero frames at 1440p",
 per_shot={s["id"]: f"{s['eevee_frames']} @ {s['eevee_res']}" for s in shots if s["eevee_frames"]},
 game_plates="demo mode (SwiftShader, ~20-40 s/frame at 1080p): 1 top-down plate of the menu region (layout + flat-map source), 1 menu-camera plate at 2x (5120x2880, a few minutes), optional 1 plate at 4:3 (FOV-behaviour check) and 1 at g_night=1 (night look reference for S01)",
 compositor="all 1984 frames pass through the numpy/OpenCV compositor (0.4-3 s/frame): ~1 h total",
 wall_time_estimate="Eevee ~3 h on one process (~2.5 h with two concurrent), compositor ~1 h, plus prep (~25 h of tool building, mostly reusable).",
)

light_rig = [
 ("S01-S03", "f0-445", "Left candle (1900 K, az ~150 deg, el 15-18 deg) lit f4; right candle (az ~30 deg) lit f18; cool #141325 fill. Flicker 1-3 Hz sway + 8-12 Hz, 6-12 %. Both flare with the swell f198-212."),
 ("S04", "f446-531", "Right candle snuffed f463-470 on 'died'. Left candle only: el 12 deg, key:fill 6:1, saturation 0.7."),
 ("S05", "f532-560", "Left flame bent by a draught: -3 EV dip and recovery (the edit is hidden in it)."),
 ("S06-S07", "f561-796", "Left candle only, leaning at 'crown' (f779-790): moves the crown's shadow."),
 ("S08", "f797-843", "Left candle dies f790-806. Darkness: cool fill at -4 EV, wick ember. Hearth glow rises from the bottom edge from f832."),
 ("S09-S13", "f844-1381", "Hearth (2200 K, from below/bottom edge, el ~10 deg, 2-6 Hz at 15-25 %) + stitched-fire and ember glow in S10. Sinks through S12-S13 to a central pool; edges -2.5 EV by f1319."),
 ("S14-S16", "f1382-1598", "Dawn window light from the left (4300 K, el 28 deg), sweeping L->R f1382-1470; then a daylight key from the upper left (az 135 deg) matching the game board's down-right shadows. Candles cold."),
 ("S17-S19", "f1599-1983", "Daylight (the game plate's own lighting). Left candle relit f1662 (bass), right candle f1703-1710 ('age'). After dawn the candles only light themselves (sprite glow), so no warm pools are added to the board: the frame stays identical to the live menu."),
]

beat_map = [
 ("f4", "'There' + drone", "Left candle ignites at its menu position"),
 ("f85-104", "'one realm'", "Glint runs round the single gold border"),
 ("f122-140", "'one table'", "The chronicle unrolls; p1's table slides into frame"),
 ("f167-184", "'one oath'", "Glint along the oath sword"),
 ("f224-230", "'one crown'", "The crown flares"),
 ("f279-308", "'raised their cups'", "Goblets lift 6-10 mm"),
 ("f344-372", "'swore' (drone swell f358)", "Hilt-to-tip glint on the sword"),
 ("f362-445", "'never end' + gap", "Titulus stitches on; its thread runs on and leads the truck"),
 ("f463-470", "'died'", "Right candle snuffed"),
 ("f522", "'heir'", "Last dull glint on the dead king's crown"),
 ("f532-560", "drone gone, lament enters", "Draught dip; the camera returns to the oath"),
 ("f561-640", "'every lord'", "The king is unpicked from the oath scene"),
 ("f656-669", "'empty chair'", "Push arrives on the king-shaped void"),
 ("f726-766", "'his own head'", "Ghost underdrawn crowns over the four lords"),
 ("f790-806", "music collapses f797", "The last candle dies"),
 ("f845-899", "'wars ... hundred years'", "Stitched soldiers rise and fight in silence"),
 ("f925-955", "'ended nothing'", "Soldiers sink; their stitches pull out"),
 ("f981", "'Cities' (f982)", "Hard cut to the burning city"),
 ("f994-1001", "'fell'", "The tower drops"),
 ("f1009-1050", "'ruin' + pad return f1017", "Burn-through to the map beneath"),
 ("f1051-1101", "'Roads ... forest'", "Forest stitches over the roads"),
 ("f1205-1211", "'borders'", "One gold border becomes four realm cords"),
 ("f1283", "BASS ENTRY 'grew dark'", "Pull-back lands; fog and fray surge from the edges"),
 ("f1345", "bass pulse #2", "The pool of light contracts: lowest point"),
 ("f1380-1470", "'Now'", "Dawn sweep L->R; fog peels; colours revive"),
 ("f1404-1430", "'every ruler' + bass f1410", "Four crests flash"),
 ("f1458-1480", "'made whole' + bass f1471", "Capitonnage: the hexes swell"),
 ("f1491-1523", "Bbmaj7 horn", "Low glide over the rising world"),
 ("f1528-1540", "'banner' + bass f1536", "The player's banner unfurls"),
 ("f1563-1575", "'village'", "A village rises in two steps"),
 ("f1593-1614", "'one blank page' + bass f1599", "The parchment card is laid down"),
 ("f1662", "bass f1664", "Left candle relights"),
 ("f1703-1710", "'age'", "Right candle relights"),
 ("f1722-1744", "'remembered' + bass f1726", "The logo valance unrolls from its rod"),
 ("f1744-1756", "climax swell, bass f1755", "Gold thread couches 'Chronica'"),
 ("f1760", "climax peak", "Gold sheen sweep across the title"),
 ("f1783-1855", "recession under the question", "Everything settles to the exact menu framing"),
 ("f1855-1983", "ring-out", "Near-still hand-off frame; f1983 is the poster"),
]

handoff = dict(
 final_rects_2560="bar_top (0,0,2560x128); logo_title_banner (784,0,992x296.3); menu_card (224,318.7,1003.2x1057.6), parchment interior (272,357.3,910.7x976); banner_side_left (16,64,129.2x345.6); banner_side_right (2421.1,64,122.9x345.6); candle_left (9.6,686.9,92x331.2); candle_right (2452.9,686.9,97.5x331.2); lion_statue_left (6.4,1163.2,189.9x273.6); lion_statue_right (2362.1,1163.2,191.5x273.6)",
 board="UI-free demo-mode plate from the menu camera (seed 4242, small map, zoom 11, FOV 30 deg, pitch 66.09 deg, distance 20.9, first tour focus), rendered at 2x for the S17-S19 zoom. The menu tour holds 3 s before panning, so the live board is still when the dissolve happens.",
 held_poster="The overlay holds the last video frame while engine.start() runs (seconds), showing a gold progress thread at bottom 7 %; f1983 must therefore be a clean still: no motion blur, flames mid-flicker, fringe settled, and calm board/sea at the bottom centre.",
 card="The card stays blank (drypoint ruling only for the title and the subtitle rule). The live menu writes the title and buttons, whose count depends on saved games (Continue / Load Game), so no button rows are pre-drawn.",
 aspect_4x3=("iPad: object-fit:cover crops the 16:9 master to x 320-2240, which cuts the candles, side banners, statues and the card's left edge, while the live 4:3 menu uses the base_4x3 layout (and shows table_edge_bottom: books and a sealed scroll, very much the chronicler's table). "
             "Deliver a 4:3 master (1920x1440) as well: every shot is staged 4:3-safe; S01 and S15-S19 are re-composited with the base_4x3 sprite rects x1.2. If Godot keeps the vertical FOV (keep_height), the 4:3 board and Eevee layers are exact central crops of the 16:9 ones, so no re-render is needed; verify with one 4:3 demo plate. The overlay picks the file by aspect ratio."),
 poster_and_tap=("intro/poster.jpg should be frame ~60 (candlelit table), not frame 0 (black). The 'Touch to begin' text (#7a2a22 at top 72 %) sits on a dark area of that frame, so the integrator should lighten it (e.g. #E6D7B6) or add a scrim. This is a suggestion only; the repo is not touched."),
 audio_tail="Optional, for the audio owner: a 0.5-1 s gain ramp at the end of the master would hide the -48 dBFS cut-off during the poster hold.",
 acceptance="Difference image of f1983 against the live menu's first frame (UI-free plate + sprites): mean abs diff < 2/255 outside text, candle flames and card interior; no sprite offset > 0.5 px.",
)

dependencies = [
 "Demo-mode plates of the real board (seed 4242): a top-down plate (layout, terrain classes, settlement positions, flat-map source) and a 2x menu-camera plate (final board + projection texture). The fallback, if top-down camera control is not available: derive layout from the menu plate by inverse homography of the ground plane.",
 "Hex geometry (size and orientation) from the game's Hex layout, or measured from the top-down plate.",
 "menu_card 9-slice margins from ui_theme.gd, or a game capture of the menu with labels hidden.",
 "Exported Blender camera tracks (S02, S15, S16) to drive the 2.5D sprite homographies.",
]

risks = [
 ("Board match at the swap (S16->S17)", "Projection-blend onto the 2x menu plate from f1540; the swap completes under the card drop f1590-1605. Fallback: a 20-frame dissolve hidden by the card and the bass pulse."),
 ("Unpicking the needle-painted king (S06)", "Strands come from the LIC field inside the king mask (p1 vs p1_empty difference). Fallback: couching release + strand slackening as a 2.5D height ripple, then a fade to the linen/underdrawing plate."),
 ("Panel headroom (p1/p3/p6 are only 1.075x the master)", "Rostrum framings show the cloth edges (F0) so pushes have room; LIC re-synthesis for anything past 1.4x native; hard limit 2.2x (S06)."),
 ("Eevee legacy limits (no anisotropy, no material displacement)", "Real geometry for the puff (shape keys) and stretched bump for metal glints; fuzz and grain in 2D; Cycles is not used."),
 ("Figure-card resolution in S09 (288-608 px)", "Keep figures at 1.5x native on screen or less; shallow DOF and firelight hide the upsampling; normal maps used for relief."),
 ("Menu sprites relit at night (S01)", "Keep them near silhouette with a warm rim (luminance-derived normals, ratio relight); never show their baked daylight shading at full strength."),
 ("Render contention (4 shared cores)", "Total Eevee 405 renders, well under the limits; test renders at 1280x720; at most 2 concurrent Blender processes."),
]

# ---------------------------------------------------------------- JSON
doc = dict(
 title=TITLE,
 angle="The Chronicler's Table: a physical, candle-lit tabletop framing device consistent with the game menu.",
 logline=LOGLINE,
 master=dict(resolution="2560x1440", fps=FPS, frames=TOTAL, first_frame=0, last_frame=TOTAL-1, duration_s=round(TOTAL/FPS, 3),
             audio="aaa/audio/audio_master_1984f_s16.wav", frame_convention="frame = floor(t*30)", alt_master="1920x1440 (4:3, iPad) for S01 and S15-S19 re-layout"),
 world_rules=[
  "One continuous physical place: a walnut table seen either from the player's seat (the menu camera, pitch 66.09 deg) or from a rostrum straight above. The azimuth never changes; there is no orbit.",
  "Two cloths: the flat embroidered map of the one realm (it becomes the game board) and, rolled on top of it, the chronicle frieze (p1, p3, war strip, p6). The frieze burns through to the map at 'ruin'.",
  "Light is practical and is the editor: two candles at the exact menu positions, snuffed at 'died' and at the music collapse; a hearth from below for the war; a dawn window for 'Now'; the candles relit for the hand-off.",
  "Things wake through thread: stitch-on, unpick, couching release, padding (capitonnage), stumpwork. Figures move as rigid cut-outs on twos. Nothing flies; there are no particles.",
  "The menu's frame (bar, side banners, candles, lion statues, logo rod) is on screen at the first and the last frames: the film starts and ends at the same table.",
 ],
 eevee_budget=budget,
 light_rig=[dict(shots=a, frames=b, state=c) for a, b, c in light_rig],
 beat_map=[dict(frames=a, audio=b, visual=c) for a, b, c in beat_map],
 shots=[{k: s[k] for k in ["id", "name", "start_frame", "end_frame", "start_s", "end_s", "frames", "audio_event", "visual_action",
                         "camera", "technique", "material_behavior", "transition_out", "emotional_purpose", "est_render_cost",
                         "eevee_frames", "eevee_res", "lights", "assets"]} for s in shots],
 six_keyframes=six_keyframes,
 poc=POC,
 handoff=handoff,
 dependencies=dependencies,
 risks=[dict(risk=a, mitigation=b) for a, b in risks],
)
with open(OUT_JSON, "w") as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)

# ---------------------------------------------------------------- MD
def fr(s):
    return f"{s['start_frame']}-{s['end_frame']}"

md = []
A = md.append
A(f"# {TITLE}")
A("")
A("Draft storyboard, angle **\"The Chronicler's Table\"**. Master 2560x1440, 30 fps, frames 0-1983 (66.133 s), muxed with `audio/audio_master_1984f_s16.wav`. Frame = floor(t x 30). Machine-readable version: `draft_table.json` (same data; generated by `story/work/build_draft_table.py`).")
A("")
A(f"**Logline.** {LOGLINE}")
A("")
A("## 1. The idea in one paragraph")
A("")
A("The film never leaves one table. Frame 4 is the game's main menu at night: the same walnut bar, side banners, carved lions and candles, at their exact menu pixels, but with a flat embroidered map of a single realm where the 3D board will be, and a rolled chronicle lying where the parchment card will be. The candles light it; the chronicle unrolls; the story plays out on physical cloth under practical light. Every turn of the story is a physical event on the table: a candle snuffed at 'died', the king unpicked out of the oath scene, the last candle dying with the music, a war of stumpwork soldiers rising and sinking in hearth light, the stitched fire setting the real linen alight, the map beneath ageing and splitting into four borders. At dawn the map is cut into hexagonal coupons, padded and raised (the game's own capitonnage and stumpwork, as written in `terrain.gdshader` and `piece.gdshader`) until it *is* the board. A blank parchment is laid down on 'one blank page', the candles are relit, the Chronica valance unrolls and its gold is stitched on at the musical climax, and the last 4.3 s are the live menu, frame for frame. The live menu then writes its title and buttons on the blank page.")
A("")
A("## 2. Rules of this world")
A("")
for r in doc["world_rules"]:
    A(f"- {r}")
A("- Camera grammar follows the style bible (truck, don't pan; at most 12-15 px/frame without motion blur; exponential zooms; real DOF in macro). Two deliberate 3D exceptions: the war at soldier height (S09) and the board rising (S15-S16).")
A("- Every composition is staged 4:3-safe (x 320-2240) for iPad; see section 9.")
A("")
A("## 3. Music and narration drive the picture")
A("")
A("The score has no percussion, so the picture is cut to narration words and to the few real musical events. Three ideas carry the structure:")
A("")
A("1. **The candle follows the score.** The drone's exit at 16-18 s follows the right candle being snuffed on 'died' (f469). The music's collapse at f797 *is* the last candle dying. The war plays in the near-silence by hearth light only.")
A("2. **The bass pulse is the world's heartbeat.** From the bass entry on 'grew dark' (f1283) the 2.115 s pulse first drives the darkness (fog surge f1283, the contracting light f1345), then the rebuilding: crests flash f1410, hexes swell f1471, the banner unfurls f1536, the card lands f1599, the left candle relights f1664, the valance unrolls f1726, the title's last stitch lands on the swell f1755.")
A("3. **The climax gap (f1744-1783, peak f1760) is the name.** The gold thread stitches 'Chronica', then the sheen peaks exactly at f1760. The recession under the final question is the settle into the exact menu frame.")
A("")
A("| frames | audio | visual |")
A("|---|---|---|")
for a, b, c in beat_map:
    A(f"| {a} | {b} | {c} |")
A("")
A("## 4. Storyboard table")
A("")
A("| id | frames | time (s) | audio event | visual (short) | camera | technique | transition | Eevee |")
A("|---|---|---|---|---|---|---|---|---|")
short = {
 "S01": ("Candles ignite at menu positions; the night table; flat one-realm map; glint runs round the one gold border", "menu cam locked, then push + tilt 66->78 deg"),
 "S02": ("Chronicle roll unrolls across the map; p1 table, oath sword, crown glints", "tilt to rostrum, push F0->1.4x"),
 "S03": ("Goblets lift; sword glint; titulus stitches on; its thread leads across the seam", "pull back, then truck right <=15 px/f"),
 "S04": ("p3 king on bier; right candle snuffed on 'died'; last dull crown glint", "truck decelerates, push 1.2x"),
 "S05": ("Draught dip to -3 EV; travel back to the oath under darkness", "fast R->L truck, hidden"),
 "S06": ("The king is unpicked out of the oath scene: a king-shaped void, the crown left hanging", "push 0.8x->2.2x"),
 "S07": ("Ghost underdrawn crowns over each lord; crown shadow leans", "pull back to 1.4x"),
 "S08": ("Last candle dies with the music; darkness; hearth glow rises", "locked"),
 "S09": ("Macro between threads; stumpwork soldiers rise, fight in silence, sink and are unpicked", "macro dolly, low R->L track, crane"),
 "S10": ("Burning city; tower falls; stitched fire burns through the real linen to the map", "locked F1, 2 deg dutch"),
 "S11": ("On the map: forest stitches over the roads", "rostrum truck R->L"),
 "S12": ("One gold border unpicked into four realm cords; the unknown fades under fog quilts", "truck slows, pull-back starts"),
 "S13": ("Whole map on the table; fog and fray surge on the bass entry; darkness at the edges", "exp. pull-back, lands on f1283"),
 "S14": ("Dawn sweeps L->R; fog peels; colours revive; four crests flash", "top-down, push 1.15x"),
 "S15": ("Hex coupons cut, padded (capitonnage); towns rise as stumpwork 3D models", "3D tilt 90->55 deg, low glide"),
 "S16": ("Banner unfurls; village rises; the table frame re-enters; board converges to the game plate", "3D climb to menu cam (1.04x)"),
 "S17": ("Blank parchment card laid down at its menu rect; left candle relights", "zoom 1.04->1.02"),
 "S18": ("Right candle relights; valance unrolls; gold thread stitches 'Chronica'; sheen peak f1760", "locked (1.01x)"),
 "S19": ("Settles to the exact menu frame; near-still from f1855; f1983 = poster", "zoom to 1.00 at f1855, locked"),
}
tech_short = {s["id"]: ("Eevee + 2.5D" if s["eevee_frames"] else "2.5D") for s in shots}
aud_short = {
 "S01": "silence f0-3; drone + 'There' f4; 'world' f39; 'one realm' f76-104",
 "S02": "'one table' f126/140; 'one oath' f162/173; swell f198-212; 'one crown' f212/230",
 "S03": "'raised' f285, 'cups' f308; 'swore' f349 (swell f358); 'never end' f367-402; gap f402-445",
 "S04": "'king' f458, 'died' f469; drone exits f480-548; 'no heir' f498-532",
 "S05": "music-only gap, lament chords take over (F6)",
 "S06": "'every lord' f567/578; 'table' f621; 'empty chair' f656/669; gap f681-716",
 "S07": "'his own head' f741/753; 'beneath the crown' f766/785",
 "S08": "music collapses -20 dB at f797; near-silence",
 "S09": "'wars' f850; 'hundred years' f884/899; 'ended nothing' f925/942; silent gap f952-979",
 "S10": "'Cities' f982, 'fell' f999, 'ruin' f1015; pad returns f1017",
 "S11": "'Roads' f1051, 'swallowed' f1075, 'forest' f1101; soft pad",
 "S12": "'Men forgot' f1138/1149; 'borders' f1211; gap with D7 swell",
 "S13": "'grew' f1281 + BASS ENTRY f1283; 'dark' f1292; 'edges' f1319; bass f1345",
 "S14": "'Now' f1382; 'ruler' f1407 + bass f1410; 'believes' f1419",
 "S15": "'made whole' f1458/1466 + bass f1471; Bbmaj7 horn gap f1491-1523",
 "S16": "'One banner' f1524/1533 + bass f1536; 'one village' f1559/1569",
 "S17": "'one' f1599 + bass; 'blank' f1614; 'page' f1630; bass f1664",
 "S18": "'age' f1707; 'remembered' f1726 + bass; CLIMAX gap f1744-1783 (peak f1760)",
 "S19": "'chronicles' f1801 ... 'you?' f1846; recession; ring-out f1855-1983",
}
tr_short = {
 "S01": "continuous", "S02": "continuous", "S03": "continuous truck right", "S04": "candle dip",
 "S05": "flame recovers", "S06": "continuous", "S07": "candle gutters", "S08": "dark -> macro in weave",
 "S09": "hard cut f981", "S10": "burn-through", "S11": "continuous truck", "S12": "continuous pull-back",
 "S13": "dawn light change", "S14": "continuous", "S15": "continuous 3D move", "S16": "camera stops; plate swap under card",
 "S17": "continuous", "S18": "continuous", "S19": "overlay hold + 0.9 s dissolve to live menu",
}
for s in shots:
    vis, cam = short[s["id"]]
    aud = aud_short[s["id"]]
    tr = tr_short[s["id"]]
    A(f"| {s['id']} | {fr(s)} | {s['start_s']:.2f}-{s['end_s']:.2f} | {aud} | {vis} | {cam} | {tech_short[s['id']]} | {tr} | {s['eevee_frames'] or '-'} |")
A("")
A(f"**Coverage:** 19 shots, contiguous from frame 0 to frame 1983 ({TOTAL} frames). **Eevee:** {eevee_1080} renders at 1080p + {eevee_1440} hero renders at 1440p = {eevee_total} (limits 600 + 150).")
A("")
A("## 5. Shot details")
A("")
for s in shots:
    A(f"### {s['id']} {s['name']}: frames {fr(s)} ({s['start_s']:.3f}-{s['end_s']:.3f} s, {s['frames']} frames)")
    A("")
    A(f"- **Audio:** {s['audio_event']}")
    A(f"- **Visual action:** {s['visual_action']}")
    A(f"- **Camera:** {s['camera']}")
    A(f"- **Technique:** {s['technique']}")
    A(f"- **Embroidery / material:** {s['material_behavior']}")
    A(f"- **Light state:** {s['lights']}")
    A(f"- **Assets:** {s['assets']}")
    A(f"- **Transition out:** {s['transition_out']}")
    A(f"- **Emotional purpose:** {s['emotional_purpose']}")
    A(f"- **Render cost:** {s['est_render_cost']}" + (f" Eevee renders: {s['eevee_frames']} ({s['eevee_res']})." if s['eevee_frames'] else ""))
    A("")
A("## 6. Practical light continuity")
A("")
A("| shots | frames | light state |")
A("|---|---|---|")
for a, b, c in light_rig:
    A(f"| {a} | {b} | {c} |")
A("")
A("## 7. Six keyframes")
A("")
for k in six_keyframes:
    A(f"- **f{k['frame']} ({k['shot']}).** {k['description']}")
A("")
A("## 8. Proof of concept: 'Capitonnage' (2D embroidery -> 3D board, 5 s)")
A("")
A(POC)
A("")
A("Why this one: it is the riskiest and most important transformation in the film, it is the bridge between the cinematic and the game (it must end on the game's own look), and every technique it needs (flat-map maps, hex puff, stumpwork models, board-to-plate match) is reused by S01, S11-S16.")
A("")
A("## 9. Hand-off to the live menu")
A("")
A(f"- **Final rects (2560x1440, from menu_layout.json):** {handoff['final_rects_2560']}.")
A(f"- **Board:** {handoff['board']}")
A(f"- **Held poster:** {handoff['held_poster']}")
A(f"- **Blank card:** {handoff['card']}")
A(f"- **4:3 / iPad:** {handoff['aspect_4x3']}")
A(f"- **Poster and tap prompt:** {handoff['poster_and_tap']}")
A(f"- **Audio tail:** {handoff['audio_tail']}")
A(f"- **Acceptance test:** {handoff['acceptance']}")
A("")
A("## 10. Render budget")
A("")
A("| shot | Eevee renders | settings |")
A("|---|---|---|")
for s in shots:
    if s["eevee_frames"]:
        A(f"| {s['id']} | {s['eevee_frames']} | {s['eevee_res']} |")
A(f"| **total** | **{eevee_total}** | {eevee_1080} at 1080p (limit 600) + {eevee_1440} at 1440p hero (limit 150) |")
A("")
A(f"- Game plates: {budget['game_plates']}.")
A(f"- Compositor: {budget['compositor']}.")
A(f"- Wall time: {budget['wall_time_estimate']}")
eevee_screen = sum(s["eevee_frames"] * (2 if "twos" in s["eevee_res"] else 1) for s in shots)
A(f"- Everything else ({TOTAL - eevee_screen} of {TOTAL} frames contain no Eevee render at all; S06's 48 renders on twos cover 96 frames) is the numpy/OpenCV 2.5D compositor: flat-plane homographies, ratio relighting with practical lights, stitch-on/unpick/burn simulations, sprite cards.")
A("")
A("## 11. Dependencies")
A("")
for d in dependencies:
    A(f"- {d}")
A("")
A("## 12. Risks and fallbacks")
A("")
A("| risk | mitigation |")
A("|---|---|")
for a, b in risks:
    A(f"| {a} | {b} |")
A("")
A("## 13. How this angle answers the brief")
A("")
A("- **Physical linen, visible strands, handmade imperfection:** the cloth always has edges, a reverse side, folds, creases, foxing, needle holes, fuzz; nothing is a flat texture card except the menu sprites, which are the game's own.")
A("- **2D -> 3D that is believable:** every lift has a textile mechanism: goblets and crowns lifted a few millimetres (S03, S06), detached stumpwork slips on wires (S09), capitonnage padding and stumpwork pieces (S15), which are exactly how the game itself describes its board and pieces.")
A("- **Camera between threads into a miniature world:** S09 starts inside the weave; S15 glides low over the rising board.")
A("- **Threads forming the identity:** S18 couches 'Chronica' in gold on the climax.")
A("- **Avoided:** particles (the burn has ember rims only), plastic sheen (wool <= 6 %), cheap parallax (sprites move only through true camera homographies), random moves (fixed azimuth, every move motivated by a word or a musical event), over-symmetry (p1's centred king framed on a third, the menu's asymmetric card), over-clean stitching (30 % ageing density, mends, loose threads).")
A("- **Seamless hand-off:** the first and last frames share the same table; the final 4.3 s are pixel-registered to the live menu, with a blank page left for the menu to write on.")
A("")
with open(OUT_MD, "w") as f:
    f.write("\n".join(md))

print("ok", OUT_JSON, OUT_MD, "eevee", eevee_1080, eevee_1440, eevee_total, "shots", len(shots))
