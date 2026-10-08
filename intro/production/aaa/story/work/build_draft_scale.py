#!/usr/bin/env python3
"""Builds draft_scale.json + draft_scale.md (CHRONICA intro, angle "Scale Journey").
Single source of truth for the shot list; validates frame coverage 0..1983."""
import json, os

ROOT = "/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa"
OUT_JSON = f"{ROOT}/story/draft_scale.json"
OUT_MD = f"{ROOT}/story/draft_scale.md"
FPS = 30
LAST = 1983

TITLE = "CHRONICA - The Thread of the Chronicle (Scale Journey)"
LOGLINE = ("A single gold thread, drawn through linen in extreme macro, pulls back to reveal the realm it binds; "
           "when the oath breaks the same thread is torn out and the world unravels into a flat, forgotten map; "
           "on the bass entry the camera dives between its threads into a miniature stumpwork world where one banner, "
           "one village and one blank page begin again, then climbs out on the climax to find that world lying on the "
           "chronicler's table: the CHRONICA main menu, its gold title stitched by the same thread and its page left blank for you.")

# ---------------------------------------------------------------------------------------------
# Shots. eevee1080 / hero1440 = frames rendered in Blender for that shot (unique renders).
# field = approx width of cloth visible across the 2560 frame (the scale curve of this angle).
# ---------------------------------------------------------------------------------------------
SHOTS = [
 dict(id="S01", name="The Gold Thread", start=0, end=75,
  act="I Oath", field="24 mm (F3+ macro)",
  audio_event="M0 digital silence f0-3; D drone fades in with narration P01 'There was a time when the world knew only...' (attack 'There' f5, strongest of the file); 'world' f39.",
  visual_action="Black for f0-3. From f4 a raking candle line (1900K warming to 3000K) finds bare linen weave: slubs, fuzz. On 'There' (f5) the bright point of a plunging needle breaks up through the weave from behind, its eye dragging a two-ply silver-gilt cord. f5-39: the cord slides up through the hole, a glint running along its S-twist. On 'world' (f39) it draws taut and the needle leaves frame top-right. f39-75: the cord lies along a faint brown underdrawing line and a few linen fibres spring back around the hole.",
  camera="Locked macro at about 1:1 magnification (24 mm field, f/8, about 1.6 mm DOF). The cloth is tilted 18 deg so a sharp band crosses the frame. Focus racks from needle tip (f5) to cord (f30). Drift 1.5 px/frame. The pull-out starts with an ease-in at f40 (24 to 32 mm by f75).",
  technique="3D. Blender 4.0.2 Eevee-legacy 1920x1080, 16 TAA, upscaled to 2560 (bpy 5.2 Eevee-next as fallback). A 40x40 mm hero patch: subdivided plane displaced by procedural weave height (0.67 mm pitch, slubs), hair-strand fuzz 40/cm2. The cord is a curve with real 2-ply twist geometry. Steel needle mesh. Area key at 22 deg plus warm grazing rim. Real DOF.",
  material_behavior="Linen matte with a faint thread sheen. Silver-gilt cord: thin anisotropic glint travelling along the twist (faked with stretched bump in Eevee), one tarnished stretch. Back-lit wool fuzz halo. Steel needle with one hard highlight for 1-3 frames.",
  transition_out="Continuous: the same Eevee render keeps pulling out into S02.",
  emotional_purpose="Wonder and intimacy. The chronicle begins with one thread, and the audience believes in the material before any story starts.",
  est_render_cost="Eevee 1080p x 76 frames at ~50 s = ~63 min (~52 min with 2 procs). Prep: hero linen/cord rig ~0.5 day (reused in S09).",
  eevee1080=76, hero1440=0, comp=76,
  assets=["procedural linen/cord (style/tools/stitch_ref.py parameters)", "palette.json metal_gold_f0, linen"]),

 dict(id="S02", name="One Realm (powers of ten)", start=76, end=247,
  act="I Oath", field="32 mm -> 200 mm (f104) -> 330 (f140) -> 420 (f173) -> 512 mm (f230, panel 1.0x)",
  audio_event="Drone swell +9 dB at f76 on 'one'; 'realm' f91; 'one table' f126-151 (table f140, drone re-swell f126); 'one oath' f162-184 (oath f173); near-silence f185-198, then a +10 dB swell f195-215; 'one crown' f212-248 (attack f229-230).",
  visual_action="The pull-out shows the cord hangs the realm's purple banner (gold crown, two gold lions). 'realm' (f91): a sheen sweep crosses the banner's gold lions and crown. The king's crowned head enters below. 'table' (f140): the long table enters and candle pools bloom on the tablecloth. 'oath' (f173): a glint runs along the sword under the four lords' hands. f185-198: stillness. 'crown' (f230): the full oath tableau settles, the key reaches 22 deg, and a travelling glint circles the king's crown.",
  camera="Exponential pull-out with ease-out: field 32 mm (f76) to 200 mm (f104) to 512 mm (f230, p1 at 1.0x). Frame centre drifts from the right banner cord down to panel centre. Hold and drift 2 px/frame f230-247. No cuts: the litany is lit, not edited.",
  technique="Hybrid. Eevee keeps rendering f76-110: beyond the hero patch, the 3D plane carries a 2.5x LIC-resynthesised p1 texture plus a procedural linen extension above the panel for the cord. Crossfade f100-110 to the numpy/cv2 2.5D compositor: p1 ratio-relit with LIC-synth normals (bible 5.2), cord redrawn as a 2.5D height field with the same twist parameters. Each litany accent is a relight pass (key azimuth or practicals), not a cut.",
  material_behavior="Narrative wool stays matte. Banner = heraldic satin plus gold: blocks flash separately as the light passes. Sword and crown = metal glint travelling along the thread. Candles are 1900K practicals flickering 6-12 %.",
  transition_out="Continuous into S03.",
  emotional_purpose="From one thread to one realm. Unity reads as one unbroken gesture, so it hurts more when it breaks.",
  est_render_cost="Eevee 1080p x 35 frames (f76-110) ~30 min. Comp 148 frames with relight ~4 s/frame ~10 min. Prep: 2.5x LIC resynth of p1 (~10 min), linen extension + cord path (~2 h).",
  eevee1080=35, hero1440=0, comp=172,
  assets=["intro/p1_oath.png", "procedural linen extension", "style/tools/stitch_ref.py shading"]),

 dict(id="S03", name="The Oath", start=248, end=401,
  act="I Oath", field="512 -> 492 mm (1.00 -> 1.04x)",
  audio_event="Gap f248-276 (D drone). P05 'They raised their cups' f276-322 (raised f285, cups attack f307, bass swell f296). Gap f322-339. P06 'and swore it would never end.' f339-402 (swore f349, strongest early drone swell f358, never f381, end f391).",
  visual_action="'raised' (f283-295): the four goblets lift about 8 mm off the cloth as stumpwork appliques, rippling left to right on twos, their soft shadows sliding down-right. 'cups' (f307): candle flames surge. 'swore' (f349-358): the key sweeps 70 deg left to right over 2.5 s. Every couched stitch catches light in turn, the banner cord glints and the sword flashes. 'never end' (f381-402): the goblets settle back into the cloth and warm stillness holds.",
  camera="Slow truck right 2-3 px/frame with push 1.00 -> 1.04x (cubic ease).",
  technique="2.5D comp. Goblets are cut out by mask; a z-lift seen frontally is only a shadow shift plus 1.5 % scale, so no inpainting is needed. Ratio relight every frame from cached LIC normals during the sweep. Flames warp as laid strands.",
  material_behavior="Matte wool with soft sheen. Gold goblet rims glint. Laid-strand flames shift phase at 2-4 Hz. The wool fuzz halo lights up as the sweep passes.",
  transition_out="Continuous into S04.",
  emotional_purpose="The warmth of the golden age. The oath feels sincere, so its failure will hurt.",
  est_render_cost="Comp 154 frames x ~4.5 s (relight) ~12 min. Prep: goblet masks (~1 h).",
  eevee1080=0, hero1440=0, comp=154,
  assets=["intro/p1_oath.png"]),

 dict(id="S04", name="The Candles Gutter", start=402, end=467,
  act="I -> II", field="492 -> 410 mm (1.04 -> 1.25x)",
  audio_event="Music-only gap f402-446 (Dmaj7 drone, bass swell f428). 'Then the king' f446-468.",
  visual_action="A draft: the candle flames bend right and shrink. The key drops from 3000K to 1900K and from 22 to 12 deg; fill falls from 1:3 to 1:6. The feast sinks into shadow until only the king's face and crown sit in one candle pool. The cord's glint dies.",
  camera="Push-in toward the king's crown, 1.04 -> 1.25x (LIC re-synthesis past 1.075x).",
  technique="2.5D comp: animated relight (temperature, elevation, fill) and flame warps.",
  material_behavior="Wool loses its sheen as the light lowers. Long raking shadows from the couching bars appear. The gold crown keeps the last highlight.",
  transition_out="Hard cut at f468 (one frame before 'died', f469) to S05, matched on crown position and scale.",
  emotional_purpose="Foreboding. The 'never end' oath begins to fail.",
  est_render_cost="Comp 66 frames x 4.5 s ~5 min.",
  eevee1080=0, hero1440=0, comp=66,
  assets=["intro/p1_oath.png"]),

 dict(id="S05", name="The King Died", start=468, end=531,
  act="II Death", field="512 -> 445 mm (p3 1.0 -> 1.15x)",
  audio_event="'died' f469. The D drone exits (-6 dB f480, -15 dB f534, gone f548). P08 'and left no heir,' f498-532 (heir f522).",
  visual_action="p3: the king lies in state, crowned, hands on the sword, on a purple bier between tall candles. On 'no heir' (f516-522) the two outer flames gutter out as their laid strands retract into the wicks (an unpick). Two flames remain, and the crown's gold holds the last light.",
  camera="Slow push toward the crowned head, 1.0 -> 1.15x, with a 1 px/frame drift right to left.",
  technique="2.5D comp on p3: LIC re-synthesis up to 1.4x, flame masks with strand-retraction animation (small navy-field inpaint behind the flames), relight at 1900K, 12 deg.",
  material_behavior="Purple velvet wool is matte. The navy field is deep. The crown is the act's single gold accent (colour script II). Flames are laid strands.",
  transition_out="Match-dissolve anchored on the crown (S06).",
  emotional_purpose="Grief and void. The drone, the floor of the score, leaves with the king.",
  est_render_cost="Comp 64 frames ~4 min. Prep: flame masks + inpaint (~1 h).",
  eevee1080=0, hero1440=0, comp=64,
  assets=["intro/p3_death.png"]),

 dict(id="S06", name="The Crown Remains", start=532, end=560,
  act="II Death", field="~445 -> 395 mm",
  audio_event="Music-only gap f532-561 (F6). The drone is gone by f548 and the lament chords take over at about -28 dBFS.",
  visual_action="Match-dissolve on the crown. p3's crown on the dead king dissolves into the same crown, cut from p1_oath, floating alone above the empty throne of p1_empty at identical screen position and scale. The king's body melts away beneath it.",
  camera="Locked on the crown. The push continues 1.15 -> 1.3x, mapped across the two plates.",
  technique="2.5D comp: aligned crossfade using a 'thread dissolve' (strands fade in stitch-path order via an LIC streamline mask).",
  material_behavior="The crown floats about 30 mm proud of the cloth (heraldic padded satin and gold) and casts a soft shadow on the empty seat.",
  transition_out="Continuous into S07.",
  emotional_purpose="The crown outlives the king and becomes an object of desire.",
  est_render_cost="Comp 29 frames ~1 min. Prerequisite: p1_empty repair (re-stitch the throne back, clean the smear), ~0.5 day.",
  eevee1080=0, hero1440=0, comp=29,
  assets=["intro/p3_death.png", "intro/p1_empty.png (repaired)", "crown sprite cut from intro/p1_oath.png"]),

 dict(id="S07", name="The Empty Chair", start=561, end=716,
  act="II Death", field="395 -> 512 mm (1.3 -> 1.0x) -> 474 mm (1.08x)",
  audio_event="P09 'and every lord who had sat at that table looked at the empty chair' f561-681 (lord f578, table f621, looked f637, empty f656, chair f669). Lament chords at their fullest. Gap f681-717.",
  visual_action="Pulling back from the floating crown reveals the four lords leaning toward the empty throne. 'looked at the empty chair' (f637-681): the candle light narrows to a pool on the empty seat, the lords fall into half-shadow (linen faces, outlines) and the crown's shadow lies on the seat. Gap f681-717: the crown turns very slightly (a 2D shear, as if hanging on a thread). Stillness.",
  camera="Pull-back 1.3 -> 1.0x (f561-640), then push 1.0 -> 1.08x toward the throne (f640-716).",
  technique="2.5D comp on the repaired p1_empty. Crown sprite with lift shadow. Relight at 1900K, 12 deg, fill 1:6.",
  material_behavior="Desaturated wool (sat 0.7, chroma cap .12). Only the crown's gold is lit.",
  transition_out="Continuous into S08.",
  emotional_purpose="Covetous tension: every eye is on the vacancy.",
  est_render_cost="Comp 156 frames ~8 min.",
  eevee1080=0, hero1440=0, comp=156,
  assets=["intro/p1_empty.png (repaired)", "crown sprite"]),

 dict(id="S08", name="His Own Head Beneath the Crown", start=717, end=784,
  act="II Death", field="474 -> 457 mm",
  audio_event="P10 'and saw his own head beneath the crown.' f717-799 (own f741, head f753, beneath f766, crown f785). Music-side bass swell f750.",
  visual_action="The candle is carried round the table: the key swings 120 deg at 12 deg elevation. The floating crown's long shadow slides across the cloth and crowns each lord in turn: gold tunic on 'own' (f741), red on 'head' (f753), across the empty seat (~f760), blue on 'beneath' (f766), green at f778. Each lord's crest catches a gleam as the shadow-crown lands on his head.",
  camera="Locked, very slow push 1.08 -> 1.12x.",
  technique="2.5D comp. The shadow sprite is projected per light azimuth (offset = 30-35 mm lift / tan 12 deg; blur grows with distance). Ratio relight every frame.",
  material_behavior="Raking light rakes the couching bars, so the bar-shadow grid (the Bayeux signature) is visible on the tunics as the light passes.",
  transition_out="Hard cut on 'crown' (f785) to S09.",
  emotional_purpose="Ambition and inevitability. Each lord imagines himself king, and the war is already decided.",
  est_render_cost="Comp 68 frames x ~5 s ~6 min.",
  eevee1080=0, hero1440=0, comp=68,
  assets=["intro/p1_empty.png (repaired)", "crown sprite", "crest_* only as reference for gleam masks"]),

 dict(id="S09", name="The Unpicking", start=785, end=849,
  act="II -> III", field="18 mm (macro)",
  audio_event="'crown.' f785-799. The music collapses by about 20 dB at f797-798 (the strongest internal boundary). Near-silence f797-844 at -47 dBFS.",
  visual_action="Extreme macro on the crown's couched gold. At f786 a hooked needle catches the gold thread and yanks. Tie-down stitches pop one after another (f786-797), and the thread rips out through the linen and slithers out of frame exactly as the music collapses (f798). What remains: empty needle holes, crushed fibres, a curl of gold. The candle dies, and the light decays to a cold dim graze (-4 EV) by f830. Stillness, then black by f846.",
  camera="Macro, 18 mm field, f/8. Whip-follow of the escaping thread f790-798 with motion blur, then locked with 1 px/frame drift.",
  technique="3D Eevee 1080p f785-812, reusing the S01 rig (padded satin gold over linen; thread as an animated curve sliding along its path). f813-849: 2.5D hold on the last render with light decay and grain.",
  material_behavior="Heraldic padded gold tears free. Wool fibres spring up where the tie-downs snap. Linen shows holes with the thread's dent still in it.",
  transition_out="Fade to black (f840-849), then fade up into S10.",
  emotional_purpose="The oath breaks, and the silence is the shock.",
  est_render_cost="Eevee 1080p x 28 frames at ~50 s ~23 min. Comp 37 frames.",
  eevee1080=28, hero1440=0, comp=65,
  assets=["S01 macro rig"]),

 dict(id="S10", name="A Hundred Years", start=850, end=954,
  act="III War", field="512 mm (p1_empty 1.0x) -> 1000 mm (F0 frieze, f899) then lateral",
  audio_event="P11 'The wars lasted a hundred years and ended nothing.' f844-955 over near-silence (music <= -45 dBFS): wars f850, hundred f884, years f899, ended f925, nothing f942.",
  visual_action="On 'wars' the image fades up in firelight from below (2200K flicker): the crownless p1_empty, loose gold curls on the table. The frame widens and drifts left, and the tapestry continues as a long war frieze in Bayeux format (upper and lower borders, ground line, hillocks). Ranks of the four realms' stitched soldiers clash: spearmen, knights, archers, horse archers, a catapult. Arrows fly in stem stitch past burning houses, and the fallen spill into the lower border. 'years' (f899): the frieze fills the frame. 'ended nothing' (f918-955): a truck left along the endless fighting, strikes popping on twos and threes like stop-motion. On 'nothing' (f942) colour drains from the soldiers ahead.",
  camera="Fade-up at 1.0x, pull-back to 0.5x (F0) by f899 drifting left, then truck right-to-left at 12-14 px/frame (regression direction) with cubic ease-in.",
  technique="2.5D comp. Tinted figure cards (tex_tinted, 4 realms) relit with their normal maps, 5-10 mm lift shadows, idle/strike swaps using the game's strike timing. Procedural frieze ground, borders and hillocks from stitch_ref maps. Tree-divider between p1_empty and the frieze. Desaturation ramp.",
  material_behavior="Figure cards: satin cards with brown cord (two registers coexist because the frieze ground is Bayeux laid-and-couched wool). Fire flicker from below at 15-25 %. Thread boil (re-seeded jitter on twos) on animated soldiers only.",
  transition_out="Continuous into S11.",
  emotional_purpose="The hollowness of endless war: silent, distant, repetitive.",
  est_render_cost="Comp 105 frames x ~1.5 s ~3 min. Prep: frieze layout and borders ~0.5 day.",
  eevee1080=0, hero1440=0, comp=105,
  assets=["intro/p1_empty.png", "assets/tex_tinted/*_idle_* / *_strike_*", "assets/tex/figures/*_normal", "ui_embroidery_v2/vignette_red|blue (border beasts)", "icons building_* (burning houses)"]),

 dict(id="S11", name="Ended Nothing", start=955, end=981,
  act="III War", field="1000 mm",
  audio_event="Near-silent gap f952-979 (-47 dBFS).",
  visual_action="The frieze runs out into bare linen: no stitches, only needle holes and the faint brown underdrawing of soldiers never finished. A few loose red and blue threads hang from the last figures and sway.",
  camera="Truck decelerates to a stop (ease-out), then drifts at 2 px/frame.",
  technique="2.5D comp. Loose threads are 2D curve sprites with pendulum sway on twos.",
  material_behavior="Bare linen with holes and underdrawing (the 'unwritten' look that returns at the blank page).",
  transition_out="Burn-through into S12.",
  emotional_purpose="Emptiness: the war ended nothing.",
  est_render_cost="Comp 27 frames.",
  eevee1080=0, hero1440=0, comp=27,
  assets=["procedural linen + underdrawing"]),

 dict(id="S12", name="Cities Fell to Ruin", start=982, end=1028,
  act="III War", field="1000 -> 512 mm (into p6 1.0x)",
  audio_event="P12 'Cities fell to ruin.' f982-1028 (Cities attack f987, fell f999, ruin f1015). The soft pad returns f1017-1020 (+5 dB).",
  visual_action="On 'Cities' a scorch blooms in the bare linen: soot browning, a glowing ember rim, laid-strand flames licking its edge. By 'fell' it has burned through, opening a ragged hole onto the panel behind: a walled city in flames (p6). The camera pushes through the hole. On 'ruin' the flames flare, the stem-stitch smoke spirals turn and cut-out crows wheel on threes.",
  camera="Push-in through the burn hole, field 1000 -> 512 mm, cubic ease. p6 reaches 1.0x by f1015.",
  technique="2.5D comp: procedural burn front (noise-advected distance field), soot multiply, ember emission rim. p6 relit at 2200K from below with flicker. Flame and smoke warps; crow sprites.",
  material_behavior="Linen browns and chars at the rim (soot #3A3330). Fire is stitched, not particles. Smoke is stem-stitch spirals rotating 10-20 deg/s.",
  transition_out="Smoke wipe into S13.",
  emotional_purpose="Destruction made tactile: the cloth itself burns.",
  est_render_cost="Comp 47 frames ~3 min.",
  eevee1080=0, hero1440=0, comp=47,
  assets=["intro/p6_ruin.png"]),

 dict(id="S13", name="Rising Through Smoke", start=1029, end=1050,
  act="III War", field="p6 -> whole world map",
  audio_event="Gap f1028-1051 (Dm(add9)); near-silence f1029-1047 at -42.9 dBFS.",
  visual_action="p6's black stem-stitch smoke spirals rise and swell past the lens until they fill the frame. When they part, we are high above the whole world, laid out flat below as an embroidered hex map.",
  camera="Tilt-up and rise following the smoke (2D). Smoke layers scale 1 -> 4x past the lens as foreground parallax, then the map is revealed from the top of frame.",
  technique="2.5D comp: smoke layers cut from p6 plus procedural stem spirals over the S14 map plate.",
  material_behavior="Smoke = dark stem-stitch rope (#26222A) with fuzz halo, never volumetric.",
  transition_out="Reveal into S14.",
  emotional_purpose="Elevation: from the burning city to the whole ravaged world.",
  est_render_cost="Comp 22 frames.",
  eevee1080=0, hero1440=0, comp=22,
  assets=["intro/p6_ruin.png", "S14 map plate"]),

 dict(id="S14", name="Roads Swallowed", start=1051, end=1137,
  act="III War", field="World map 1.0 -> 1.15x (about 1.4 m of board cloth)",
  audio_event="P13 'Roads were swallowed by the forest.' f1051-1115 (Roads f1051, swallowed f1075, forest f1101). Pad plateau at about -40 dBFS. Gap f1115-1138.",
  visual_action="The flat embroidered world: the game board seen straight down with everything stitched flat. Satin hexes, running-stitch roads, couched light-blue river, denim sea with wave marks, flat stitched towns and ruins, gold couched realm borders. On 'Roads' the dashed roads glint. On 'swallowed' green stem-stitch tendrils and couched leaves creep out of the forest hexes over the roads (stitch-on on twos, about 30 mm/s). By 'forest' the roads are gone.",
  camera="Top-down with 5 deg tilt. Slow push 1.0 -> 1.15x and a 2 px/frame right-to-left drift.",
  technique="2.5D comp over an orthographic Blender render of the reconstructed seed-4242 board at relief = 0 (8K still with albedo, height, tangent, material and stitch_id AOVs), relit with the numpy shader. Tendrils follow precomputed growth curves rendered as stem-stitch height strokes.",
  material_behavior="Game terrain idiom: laid satin hex fills, running stitch on seams, gold couched borders (metal glint), matte wool.",
  transition_out="Continuous into S15.",
  emotional_purpose="Nature reclaims, and the world forgets its paths.",
  est_render_cost="Blender 8K ortho still (Cycles 64 spp + pyoidn, ~25 min; counted as 8 hero frames). Comp 87 frames x 2 s ~3 min.",
  eevee1080=0, hero1440=8, comp=87,
  assets=["Blender board (models/*.obj + stitched terrain)", "work/shaders/terrain|water|border.gdshader as reference"]),

 dict(id="S15", name="Beyond Their Own Borders", start=1138, end=1228,
  act="III War", field="World map 1.15 -> 1.3x",
  audio_event="P14 'Men forgot what lay beyond their own borders,' f1138-1229 (Men f1139, forgot f1149, beyond f1182, own f1201, borders f1211). The -40 dBFS plateau creeps up.",
  visual_action="Outside each realm's gold border the land is forgotten: its stitches unpick. The couching bars release first, then the laid strands slacken and pull out, leaving bare linen with needle holes and the faint brown underdrawing of hexes. Quilted cloud appliques (the game's fog-of-war kit) slide in over the forgotten lands from the margins. The light sweeps right to left (decline). On 'borders' the gold cords tighten and each realm sits alone inside its ring.",
  camera="Push 1.15 -> 1.3x toward the gold realm, top-down.",
  technique="2.5D comp. The unpick is per-strand reveal masks played in reverse (from the stitch_id AOV). Cloud-kit textures become height-mapped layers with soft shadows. Relight sweep.",
  material_behavior="Unpick order follows real practice (bars, then laid strands). Quilted clouds are padded satin with running-stitch spirals (game look).",
  transition_out="Continuous into S16.",
  emotional_purpose="Isolation: the world shrinks to what each lord can see.",
  est_render_cost="Comp 91 frames x 4 s ~6 min.",
  eevee1080=0, hero1440=0, comp=91,
  assets=["tex/table_clouds/cloud_edge_*, cloud_corner_*, cloud_puff_*", "S14 map plate + AOVs"]),

 dict(id="S16", name="Dark at Its Edges", start=1229, end=1282,
  act="III War", field="World map 1.3 -> 2.6x (accelerating)",
  audio_event="Gap f1229-1254 (Dm7 with D7 colour; in-gap swell f1241-1257). 'and the world grew' f1254-1282 (world f1263, 'grew' starts f1281).",
  visual_action="The edges of the map-cloth darken and fray: weft threads unravel and curl loose at the frame borders. The clouds thicken and the light shrinks to the gold realm at the centre. The camera accelerates toward the gold border cord beside the empty site of the future village. (PoC part 1.)",
  camera="Exponential push, top-down, 1.3 -> 2.6x, accelerating into the bass entry.",
  technique="2.5D comp: frayed edges are procedural thread sprites plus edge darkening. In the PoC, this is the Blender scene itself at relief = 0, which guarantees an exact match into S17.",
  material_behavior="Unravelled weft yarns curl in 3D (at most 20 mm) and catch a grazing rim light. The vignette is physical light falloff on the cloth, not an overlay.",
  transition_out="Continuous dive into S17. The cut is invisible because the plate IS the Blender scene at relief 0.",
  emotional_purpose="Dread contracting to a single point.",
  est_render_cost="Comp 54 frames ~3 min (or Blender at relief 0 in the PoC).",
  eevee1080=0, hero1440=0, comp=54,
  assets=["S14 map plate", "Blender board"]),

 dict(id="S17", name="Into the Weave (great scale move #1)", start=1283, end=1335,
  act="III -> IV", field="2.6x map -> ~15 mm (between threads, f1292) -> miniature eye-level",
  audio_event="BASS ENTRY f1283 on 'grew' (+26 dB in 22-120 Hz; the biggest musical event). 'dark' f1292. 'at its edges.' f1308-1336.",
  visual_action="The camera dives into the map, and as it falls the flat embroidery gains depth. Hex patches quilt up, satin strands stand proud, the gold border swells into a thick twisted rope, stumpwork trees rise from flat discs and a ruined town lifts from its flat icon. On 'dark' (f1292) the lens slips between the giant gold rope and a satin ridge: the frame fills with dark fibre silhouettes rimmed by warm back-light. Then it levels out above a miniature world at dusk, whose horizon is walled by dark quilted clouds ('at its edges').",
  camera="Exponential dive 2.6x -> about 40x with pitch 90 -> 14 deg (f1283-1305). Lens 135 -> 24 mm equivalent (dolly-zoom that amplifies depth). Passes 3 mm above the cloth at f1290-1298, then levels out gliding forward at about 10 mm height. Motion blur on the dive.",
  technique="3D. Blender Eevee 2560x1440 hero, 16 TAA (Cycles 32 spp + pyoidn optional for the fibre passage f1288-1300). One scene with a 'relief' driver 0 -> 1 staggered per object: hex quilting displacement, strand height, cord radius, model Z-scale with slight overshoot. Real yarn-curve geometry and hair fuzz only along the camera path.",
  material_behavior="Wool satin (sheen 0.6, roughness 0.85), gold rope (metallic, stretched-bump glint), linen, quilted cloud satin. Firelight key at 2200K low from the left. Warm rim lights the fuzz.",
  transition_out="Continuous into S18.",
  emotional_purpose="Awe and vertigo: the world's darkness becomes a passage into a new world.",
  est_render_cost="Eevee 1440p x 53 hero frames at ~150 s ~2.2 h (~1.8 h with 2 procs).",
  eevee1080=0, hero1440=53, comp=53,
  assets=["Blender board", "models/ruin.obj, settle_*.obj", "procedural stumpwork trees", "cloud kit"]),

 dict(id="S18", name="The Miniature at Night", start=1336, end=1381,
  act="IV Renewal (night)", field="miniature eye-level (camera 10-15 mm above cloth)",
  audio_event="Gap f1336-1382 (F6, bass swell #2 f1345, swell into P16 f1372-1385).",
  visual_action="A low glide over the stitched miniature world at night: a ruined town whose window threads glow ember-red, stumpwork forests, the couched river, the gold border rope gleaming, and the cloud wall at the horizon. (PoC tail.)",
  camera="Low forward glide 10 mm above the cloth, slow rise to 15 mm, slight right bank. Tilt-shift miniature DOF (about f/5.6 equivalent at this scale).",
  technique="3D Eevee 1080p, 8 TAA, on ones. Game models (ruin, settle_*, watchtower) get a stitched material: inverted-hull brown outline, triplanar stitch normals, wool sheen. Windows emit at night (the game's 'genre 1' windows).",
  material_behavior="Moonlit wool goes nearly monochrome. Gold rope glints. Window yarns emit #DE6A2C at low intensity.",
  transition_out="Continuous into dawn (S19).",
  emotional_purpose="Melancholy calm: the world asleep, waiting.",
  est_render_cost="Eevee 1080p x 46 frames at ~25 s ~20 min.",
  eevee1080=46, hero1440=0, comp=46,
  assets=["Blender board", "models/*.obj"]),

 dict(id="S19", name="Made Whole Again", start=1382, end=1523,
  act="IV Renewal", field="miniature, camera height 15 -> 40 mm",
  audio_event="P16 'Now every ruler believes the world can be made whole again.' f1382-1491 (Now f1382, ruler f1407 with bass pulse f1410, believes f1419, world f1436, whole f1466 with bass pulse f1471, again ends f1491). Gap f1491-1524: the sustained Bb3 horn over Bbmaj7, the brightest colour of the score.",
  visual_action="Dawn. The key rises from 5 to 28 deg and warms from 2200K to 4300K, sweeping left to right so stitches catch the light in sequence. 'every ruler': on distant hills the rulers' banners (settle_banner in gold, red, blue, green) catch the sun one after another. 'made whole': the quilted cloud wall unpins and rolls back from the horizon, revealing the forgotten lands as blank linen hexes with only faint underdrawing. Dye colours revive from aged to fresh values (OKLab, staggered behind the light front). In the Bb gap the camera glides out over the blank land toward a bare hex by the sea.",
  camera="Rising truck right (progress) at a constant 10-12 px/frame screen speed. Crane from 15 to 40 mm height, pitch 14 -> 28 deg.",
  technique="3D Eevee 1080p, 8 TAA, on ones (light and camera both move). Animated cloud planes. Dye revival is a material colour ramp keyed by a light-front mask.",
  material_behavior="Colour revival aged -> fresh (bible 2.4). Banners in the heraldic register (satin plus gold) flash as the sun reaches them. Wool sheen grows as the key rises.",
  transition_out="Continuous into S20, settling on the blank hex.",
  emotional_purpose="Hope and ambition: the world can be stitched whole.",
  est_render_cost="Eevee 1080p x 142 frames at ~25 s ~1 h.",
  eevee1080=142, hero1440=0, comp=142,
  assets=["Blender board", "models/settle_banner.obj, capital.obj, settle_3*.obj", "cloud kit"]),

 dict(id="S20", name="One Banner, One Village", start=1524, end=1598,
  act="IV Renewal", field="miniature, close on one hex (about 60 mm across)",
  audio_event="P17 'One banner,' f1524-1544 (banner f1533, bass pulse f1536). P18 'one village,' f1559-1583 (village f1569). Gap f1583-1599.",
  visual_action="On the blank hex a gold thread is drawn up out of the linen to form a pole (f1524-1533). On 'banner' (f1536) the builders' gold banner with its red hammer unfurls with a snap and sways. On 'one village' (f1559-1583) the flat stitched footprint of a camp peels up around it into a stumpwork village (palisade, tents, watchtower: settle_0), with a small overshoot and thread boil. Two gold figure cards (engineer, spearman) hinge up from lying flat to standing on their foot lines: stitched people rising from the cloth.",
  camera="Near-locked 3/4 view (pitch 28 deg, about 25 mm height). A 2D drift right at 2 px/frame on an overscanned plate.",
  technique="3D Eevee 1080p on twos (15 unique fps, stop-motion), camera locked, 12 % overscan, drift added in comp.",
  material_behavior="settle_0 in stitched material: thatch as couched straw yarn, palisade as stem-stitch logs. Banner in heraldic satin plus gold. Figure cards use their game normal maps. Linen shows its underdrawing.",
  transition_out="Continuous into S21.",
  emotional_purpose="A beginning: the player's first act.",
  est_render_cost="Eevee 1080p x 38 frames at ~30 s ~19 min.",
  eevee1080=38, hero1440=0, comp=75,
  assets=["models/settle_banner.obj, settle_0.obj", "tex_tinted/engineer_idle_gold, spearman_idle_gold", "crest_builders"]),

 dict(id="S21", name="One Blank Page", start=1599, end=1688,
  act="IV Renewal", field="miniature, camera 25 -> 40 mm high, pitch down to 10 deg (horizon in frame)",
  audio_event="P19 'one blank page.' f1599-1645 (bass pulse f1599, +21.6 dB; blank f1614; page f1630). Gap f1645-1689 (Dm(add9); bass f1664; swell f1658-1692 into P20).",
  visual_action="On the bass pulse the camera pulls back and lowers to the horizon. The little village, its banner and two figures stand alone in the foreground of a vast plain of blank hexes stretching to the horizon: bare linen with only the brown underdrawing of hex outlines and pencil guide lines. The realm's border exists only as a dotted underdrawing, with the denim sea along one side. On 'page' the raking light settles, and the blank world waits.",
  camera="Pull back and lower, f1599-1645 (exponential, ease-out). f1646-1688: slow 2D drift on a held plate.",
  technique="Eevee 1080p on ones f1599-1645 (47 frames), on twos f1646-1688 (22 frames) with 2D drift.",
  material_behavior="Bare linen: the weave reads under a 15 deg rake. The underdrawing is faint madder-brown lines. No wool yet: maximum emptiness.",
  transition_out="Continuous into S22.",
  emotional_purpose="Openness and possibility: the unwritten future.",
  est_render_cost="Eevee 1080p x 69 frames at ~25 s ~30 min.",
  eevee1080=69, hero1440=0, comp=90,
  assets=["Blender board (blank-hex state)"]),

 dict(id="S22", name="When This Age Is Remembered", start=1689, end=1725,
  act="IV -> V", field="miniature, low horizon view",
  audio_event="P20 'When this age is' f1689-1725 (age f1707). The music swells toward bass pulse #8 at f1726.",
  visual_action="The remembering. A stitch wave races away from the village toward the horizon: laid satin fills the hexes (laid strands first, then couching bars), forests pop up as stumpwork cones, roads run in stem stitch, the river couches itself in light-blue cord and the camp grows into a walled town (settle_0 -> settle_1). Far off, Grandbois rises.",
  camera="Held low view with a slow 2D push.",
  technique="Eevee 1080p on twos (19 frames) with a 2D camera. The stitch wave is an animated distance mask driving a per-hex fill reveal in the terrain material, plus object scale pops.",
  material_behavior="Stitch-on in real order: laid, couched, tied down, outlined. Thread boil on the growing parts only.",
  transition_out="Continuous into the climb-out (S23).",
  emotional_purpose="The chronicle being written: momentum.",
  est_render_cost="Eevee 1080p x 19 frames ~10 min.",
  eevee1080=19, hero1440=0, comp=37,
  assets=["Blender board", "models/settle_0|settle_1|capital.obj"]),

 dict(id="S23", name="The Climb-Out (great scale move #2)", start=1726, end=1783,
  act="V Question", field="miniature eye-level -> about 900 mm (menu framing): ~20x plus pitch 12 -> 66 deg",
  audio_event="'remembered,' f1726-1744 (bass pulse #8 f1726). CLIMAX in the gap f1744-1783: the loudest music of the piece (-25.6 dBFS), peak f1760, bass f1755, Bbmaj7/F6.",
  visual_action="On 'remembered' the gold border couches itself round the new realm and closes its loop. The camera launches up and back as the miniature world shrinks beneath us. The stitch wave now covers the whole board with every realm, town and unit as in the game. At the climax peak (f1760) the board is revealed lying on the chronicler's table. The walnut top bar, the navy valance (still blank, letters not yet stitched) swinging onto its rod, the lion banners, the lit candles, the lion statues and a blank parchment card in its walnut frame all sweep into frame from the edges with nearer-plane parallax. Each lands on its exact menu position as the music crests.",
  camera="Exponential pull-up/back: about 20x in scale, pitch 12 -> 66.09 deg (the menu camera: FOV 30, zoom 11). Ease-in from f1726, peak velocity f1760 (180-deg motion blur), ease-out landing through S24 (to about f1800).",
  technique="Hybrid. Blender Eevee 1080p on ones f1726-1762 (37 frames, motion blur) on the reconstructed board. Cross-match at f1752-1765, under peak motion blur, to frames rendered by the real game (Godot demo mode, UI-free, camera zoom 7 -> 11, on twos f1752-1800). Table dressing = 2.5D layers cut from a full 2560 menu capture, each given a nearer depth so the camera move alone produces their parallax.",
  material_behavior="Board: the game's stitch shaders (exact in the game plate). Dressing: the game's own textures (walnut, velvet, brass). Valance letters masked out (blank navy).",
  transition_out="Continuous: the camera keeps settling into S24.",
  emotional_purpose="Revelation and catharsis: the miniature world was the game all along, and it is on your table.",
  est_render_cost="Eevee 1080p x 37 frames at ~45 s (motion blur) ~28 min. Game demo-mode plates ~25 frames x 30 s ~13 min. Comp 58 frames.",
  eevee1080=37, hero1440=0, comp=58,
  assets=["Blender board", "game demo-mode UI-free renders", "game/tex/bar_top.png, logo_title.png, banner_side_*.png, candle_*.png, lion_statue_*.png, card.png", "assets/tex/table_parchment/menu_card.png"]),

 dict(id="S24", name="What Will the Chronicles Say of You?", start=1784, end=1854,
  act="V Question", field="menu framing (1.03 -> 1.00x)",
  audio_event="P21 'what will the chronicles say of you?' f1783-1855 (chronicles f1801, say f1824, of f1838, you f1846-1855). The music recedes 19 dB f1783-1824 and the bass is gone by f1823.",
  visual_action="The composition comes to rest as the music withdraws. A single gold thread (the thread of frame 0) is drawn up through the navy valance and couches the word Chronica in gold, letter by letter, with a glint riding the needle point. 'Chron' lands on 'chronicles' (f1801-1821) and 'ica' by 'say' (f1824-1838); the crown, fleurs-de-lis and diamonds follow on 'of you?' (f1838-1855). The last stitch pulls tight on 'you' with one glint on the crown. The parchment card below stays blank.",
  camera="Residual ease-out landing, 1.03 -> 1.00x by f1854, ending pixel-exact on the menu framing.",
  technique="2.5D comp. The valance has its letters inpainted out (blank). The real logo pixels are revealed along their own skeletonised letter paths (stitch-on), with an additive metal glint at the needle point. The game board plate sits underneath.",
  material_behavior="Couched gold: pairs of gold threads with tie-downs every 2-3 mm, the glint travelling along the thread (bible 4.5). Navy velvet stays matte.",
  transition_out="Continuous into the hold (S25).",
  emotional_purpose="The question turns to the player, and the identity is literally stitched by the chronicle's thread.",
  est_render_cost="Comp 71 frames ~3 min. Prep: logo letter masks + blank-valance inpaint (~2 h).",
  eevee1080=0, hero1440=0, comp=71,
  assets=["game/tex/logo_title.png", "full-menu 2560 capture"]),

 dict(id="S25", name="The Blank Page Waits (hand-off)", start=1855, end=1983,
  act="V Title", field="menu framing (locked)",
  audio_event="M7 ring-out f1855-1983: a soft, unresolved high chord (Am7/C6 colour) at -44 to -48 dBFS, no bass. It ends abruptly at f1983 (micro-fade f1982).",
  visual_action="The menu composition, near-still. The candle flames breathe faintly. One slow sheen sweep crosses the gold letters of the valance (raking light left to right, f1868-1928). Then nothing moves for the final 55 frames (f1929-1983 identical): the exact first frame of the live menu, with the parchment card blank. Hand-off: the overlay holds this last frame while the engine boots, then dissolves (0.9 s) to the live menu. Its buttons and text appear on the blank card, so the chronicle's page fills.",
  camera="Locked, pixel-exact menu framing (menu_layout.json px_2560x1440).",
  technique="2.5D comp. Game UI-free board plate plus full-menu capture layers, with the card's interior inpainted blank from the 9-slice parchment. The sheen is a relight of the logo layer (LIC normals). Candle flames are warped.",
  material_behavior="Gold glint travels once along the letters and then rests. Everything else is still: textile at rest.",
  transition_out="CSS opacity dissolve (0.9 s, intro_overlay_snippet.html) to the live Godot menu. Game audio fades in over 2.5 s.",
  emotional_purpose="Invitation: the blank page is yours.",
  est_render_cost="Comp 129 frames ~2 min. Game plates via demo mode (2-3 plates ~2 min).",
  eevee1080=0, hero1440=0, comp=129,
  assets=["game demo-mode UI-free plate", "full-menu 2560 capture", "game/02_menu_first_frame_1920x1080.png (reference)"]),
]


GLANCE = {
 "S01": ("drone fade-in; 'There' f5, 'world' f39", "needle draws the gold cord up through linen", "3D macro"),
 "S02": ("'one realm / table / oath / crown' f76-248", "pull-out: cord -> banner -> king -> table -> full oath panel", "3D -> 2.5D hybrid"),
 "S03": ("'raised' f285, 'swore' f349, swell f358", "goblets lift; light sweep; 'never end'", "2.5D relight"),
 "S04": ("gap f402-446; 'Then the king'", "candles gutter; push to the king", "2.5D relight"),
 "S05": ("'died' f469; drone exits f480-548", "king on bier; flames unpick on 'heir'", "2.5D on p3"),
 "S06": ("gap f532-561", "match-dissolve: the crown floats over the empty throne", "2.5D dissolve"),
 "S07": ("'every lord ... empty chair' f561-681", "lords revealed; light pools on the empty seat", "2.5D on p1_empty"),
 "S08": ("'his own head beneath the crown' f717-799", "the crown's shadow crowns each lord in turn", "2.5D shadow relight"),
 "S09": ("'crown.' f785; collapse f798", "macro: gold thread ripped out; light dies", "3D macro + hold"),
 "S10": ("'The wars ... nothing' over near-silence", "fade-up; pull back into a silent war frieze, truck left", "2.5D figure cards"),
 "S11": ("near-silent gap f955-981", "frieze ends in bare, unpicked linen", "2.5D"),
 "S12": ("'Cities' f982, 'fell' f999, 'ruin' f1015", "scorch burns through to the burning city (p6)", "2.5D burn"),
 "S13": ("gap f1029-1050", "smoke spirals fill frame; rise above the world", "2.5D wipe"),
 "S14": ("'Roads ... forest' f1051-1115", "flat stitched world map; forest overruns roads", "8K ortho + 2.5D"),
 "S15": ("'Men forgot ... borders' f1138-1229", "land beyond the borders unpicks; clouds close in", "2.5D unpick"),
 "S16": ("'and the world grew' f1254-1282", "edges fray and darken; push accelerates", "2.5D (PoC)"),
 "S17": ("BASS ENTRY f1283; 'dark' f1292", "DIVE between threads; the flat map gains depth", "3D hero (PoC)"),
 "S18": ("gap; bass #2 f1345", "low night glide over the stumpwork miniature", "3D (PoC tail)"),
 "S19": ("'Now every ruler ... whole again'; Bb horn", "dawn sweep; banners; clouds roll back to blank land", "3D on ones"),
 "S20": ("'One banner' f1533, 'one village' f1569", "banner unfurls; village and figures rise from the cloth", "3D on twos"),
 "S21": ("'one blank page' f1599-1645; gap", "lone village before a horizon of blank hexes", "3D ones/twos"),
 "S22": ("'When this age is' f1689-1725", "stitch wave races to the horizon", "3D on twos"),
 "S23": ("'remembered' f1726; CLIMAX f1744-1783", "CLIMB-OUT: the board is on the chronicler's table", "3D + game plates + 2.5D"),
 "S24": ("'what will the chronicles say of you?'", "gold thread stitches CHRONICA; card stays blank", "2.5D stitch-on"),
 "S25": ("ring-out f1855-1983", "near-still menu; sheen sweep; frozen last 55 frames", "2.5D hold -> live menu"),
}

KEYFRAMES = [
 dict(frame=39, description="'world' - extreme macro, 24 mm field: a steel plunging needle has just drawn the two-ply silver-gilt cord up through the linen weave. The cord is taut, a glint sits on its twist, fibres spring around the hole, and the DOF band is 1.6 mm deep. It sets the material truth of the whole film."),
 dict(frame=230, description="'crown' - landing of the first scale move (24 mm -> 512 mm): the full p1 oath tableau under a 22 deg raking key. The banner cord runs out of frame top and a travelling glint circles the king's crown. One realm, one table, one oath, one crown in one unbroken pull-out."),
 dict(frame=798, description="The music collapses: extreme macro of the crown's couched gold being ripped out. Tie-downs have popped, empty needle holes remain and the thread's tail whips out of frame into the dying light. The oath is unpicked."),
 dict(frame=1292, description="'dark', 9 frames after the bass entry: mid-dive, the lens skims between the swollen gold border rope and a satin ridge. Rim-lit fibre silhouettes frame a flat embroidered map below that is visibly rising into a miniature 3D world (quilted hexes, stumpwork trees, a ruined town)."),
 dict(frame=1760, description="Climax peak, mid climb-out: the fully stitched board drops away under motion blur. The walnut top bar, the blank navy valance swinging on its rod, the candles, the lion statues and the blank parchment card sweep in with nearer parallax, the chronicler's table revealed."),
 dict(frame=1855, description="'you?' - the hand-off frame. Chronica has just been couched in gold on the navy valance and the last glint rests on the crown. The parchment card is blank on the real seed-4242 board under the walnut bar, the composition matching menu_layout.json. From here the frame only breathes until f1983."),
]

POC = dict(
 name="Into the Weave",
 frames=[1262, 1381], seconds=[round(1262/FPS, 3), round(1382/FPS, 3)],
 summary=("A 4.0 s (120 frames, f1262-1381) proof of concept, played against the real audio (42.067-46.067 s, bass entry inside it at f1283). "
          "It starts on a flat, top-down embroidered hex map (relief 0) under a 2200K raking key, indistinguishable from the 2.5D map plate. "
          "On the bass it dives and tilts 90 -> 14 deg while one 'relief' driver raises the world: hexes quilt, satin strands stand proud, the gold border swells into a rope, "
          "stumpwork trees and a ruined town (ruin.obj) rise from their flat icons with staggered overshoot. On 'dark' (f1292) the lens skims between the rope and a satin ridge, then levels out "
          "gliding over the miniature world at dusk with a quilted cloud wall at the horizon."),
 content="A 7x5-hex patch of the reconstructed board: 2 plains, 1 forest (12 stumpwork trees), 1 hills, 1 ruin, 1 sea hex with stitched waves, 1 blank (unpicked) hex, one gold couched border run, and 3 quilted cloud pieces at the edge.",
 technique=("Blender 4.0.2 Eevee-legacy (xvfb), one .blend. (1) Terrain: hex tiles as subdivided meshes with baked maps from a numpy embroidery generator (port of stitch_ref.py: laid strands, couching bars, tie-downs, "
            "running-stitch seams, satin for gold/heraldic). Albedo, height_mm and tangent; displacement modifier strength = relief x 1.0 mm quilting + 0.5 mm strands. "
            "(2) Gold border: a curve with twisted 2-ply profile, bevel radius = mix(0.2, 1.2 mm, relief). (3) Models: game OBJs with a stitched material "
            "(MTL Kd base, triplanar stitch normal, sheen 0.6, inverted-hull brown outline), object Z-scale = mix(0.03, 1, relief_i) with a per-object stagger and 6 % overshoot. "
            "(4) Trees: padded wool cones (displaced) on flat discs. (5) Hero fibre corridor: real yarn curves plus hair fuzz only within 30 mm of the camera path at f1286-1300. "
            "(6) Camera: lens 135 -> 24 mm with a dolly (dolly-zoom), exponential descent, motion blur. (7) Lights: 2200K key at 15 deg from low left, warm rim for fuzz, "
            "an edge falloff spot for 'dark edges'. Grade in the numpy compositor (ACES fit, act III/IV grade, black #07070A, white #F3E8D0)."),
 deliverables=["poc_into_the_weave_720p.mp4 (1280x720, muxed with audio slice 42.067-46.067 s)",
               "contact sheet of f1262 / f1283 / f1292 / f1305 / f1335 / f1381",
               "A/B still: Blender relief 0 vs 2.5D map plate at f1282 (must be indistinguishable)",
               "f1300 re-rendered at 2560x1440 as the hero quality check"],
 cost="720p test: 120 frames x ~8-12 s = ~20 min. Hero check: 3 frames at 1440p ~8 min. Build: ~1.5 days (generator port + board patch + rig).",
 success_criteria=["f1262-1282 reads as flat embroidery (no visible perspective or relief)",
                   "the depth growth reads as cloth rising, not a 3D model fading in (no popping, staggered overshoot)",
                   "fibres at f1292 read as wool (fuzz, ply twist, sheen), not tubes",
                   "the miniature at f1335 reads as a real stumpwork diorama: shallow DOF, matte wool, glint only on gold",
                   "the bass entry (f1283) is felt as the start of the fall"])

SYNC = [
 (4, "sound + narration start; picture already fading up"), (39, "'world': cord taut"), (76, "'one' + drone swell: pull-out accelerates"),
 (91, "'realm': banner sheen"), (140, "'table': candle pools"), (173, "'oath': sword glint"), (230, "'crown': crown glint, panel 1.0x"),
 (285, "'raised': goblets lift"), (349, "'swore' / f358 drone swell: light sweep"), (391, "'end': goblets settle"), (468, "HARD CUT one frame before 'died' (f469)"),
 (522, "'heir': flames unpick; drone gone by f548"), (532, "match-dissolve on the crown"), (669, "'chair': light pool on the empty seat"),
 (741, "'own': shadow-crown on lord 1"), (785, "HARD CUT on 'crown' to macro"), (798, "music collapses: thread rips out"),
 (850, "'wars': fade-up in firelight"), (899, "'years': frieze at widest"), (942, "'nothing': colour drains"), (982, "'Cities': scorch"),
 (999, "'fell': burn-through"), (1015, "'ruin': p6 at 1.0x"), (1029, "smoke wipe"), (1051, "'Roads'"), (1075, "'swallowed': tendrils"),
 (1149, "'forgot': unpick"), (1211, "'borders': cords tighten"), (1254, "fray begins"), (1283, "BASS ENTRY: the dive"), (1292, "'dark': between threads"),
 (1345, "bass #2: night glide"), (1410, "bass #3 / 'ruler': banners catch sun"), (1471, "bass #4 / 'whole': clouds roll back"),
 (1536, "bass #5 / 'banner': banner unfurls"), (1569, "'village': village rises"), (1599, "bass #6 / 'one [blank page]': pull back to horizon"),
 (1630, "'page': light settles"), (1726, "bass #8 / 'remembered': border closes, climb-out launches"), (1760, "CLIMAX peak: table revealed"),
 (1783, "recession + 'what': logo thread appears"), (1801, "'chronicles': 'Chron' stitched"), (1846, "'you': last stitch + glint"),
 (1855, "narration ends: near-still hold"), (1929, "final 55 frames frozen"), (1983, "last frame = hand-off still")]


def check():
    assert SHOTS[0]["start"] == 0 and SHOTS[-1]["end"] == LAST
    for a, b in zip(SHOTS, SHOTS[1:]):
        assert b["start"] == a["end"] + 1, (a["id"], b["id"])
    for s in SHOTS:
        assert s["end"] >= s["start"]


def tc(f):
    return f"{f / FPS:6.2f}"


def build():
    check()
    e1080 = sum(s["eevee1080"] for s in SHOTS)
    h1440 = sum(s["hero1440"] for s in SHOTS)
    hero_anim = sum(s["hero1440"] for s in SHOTS if s["id"] == "S17")
    total_eevee_anim = e1080 + hero_anim
    shots_out = []
    for s in SHOTS:
        d = {k: s[k] for k in ["id", "name", "act", "start", "end"]}
        d = {"id": s["id"], "name": s["name"], "act": s["act"],
             "start_frame": s["start"], "end_frame": s["end"],
             "start_s": round(s["start"] / FPS, 3), "end_s": round((s["end"] + 1) / FPS, 3),
             "n_frames": s["end"] - s["start"] + 1,
             "field_of_view_cloth": s["field"],
             "audio_event": s["audio_event"], "visual_action": s["visual_action"], "camera": s["camera"],
             "technique": s["technique"], "material_behavior": s["material_behavior"],
             "transition_out": s["transition_out"], "emotional_purpose": s["emotional_purpose"],
             "est_render_cost": s["est_render_cost"],
             "render_frames": {"eevee_1080p": s["eevee1080"], "hero_1440p": s["hero1440"], "comp_2_5d": s["comp"]},
             "assets": s["assets"]}
        shots_out.append(d)
    data = {
        "title": TITLE, "angle": "Scale Journey", "logline": LOGLINE,
        "master": {"w": 2560, "h": 1440, "fps": 30, "frames": 1984, "last_frame": 1983, "duration_s": 66.133333,
                   "audio": f"{ROOT}/audio/audio_master_1984f_s16.wav", "frame_convention": "frame = floor(t*30)"},
        "scale_spine": [
            {"frames": [0, 247], "move": "macro thread -> scene (pull-out 21x, ease-out)", "music": "M1 drone"},
            {"frames": [248, 784], "move": "scene -> intimate push-ins (<=1.4x panel)", "music": "M1 swells, drone exit, M2 lament"},
            {"frames": [785, 849], "move": "hard cut to macro (unpick)", "music": "M3 collapse"},
            {"frames": [850, 1282], "move": "widest: frieze F0 -> whole world map", "music": "M3 hollow / M4 plateau"},
            {"frames": [1283, 1335], "move": "GREAT MOVE 1: dive between threads into the miniature", "music": "M5 bass entry"},
            {"frames": [1336, 1725], "move": "miniature eye-level, gentle rises", "music": "M5 bar pulse"},
            {"frames": [1726, 1800], "move": "GREAT MOVE 2: climb-out to the chronicler's table (menu)", "music": "climax f1744-1783, recession"},
            {"frames": [1801, 1983], "move": "human scale, still", "music": "M6 recession, M7 ring-out"}],
        "through_lines": [
            "The gold thread: stitched in (f0), lit (f230), torn out (f798), the gold realm borders (S14-S17), the new border (f1726) and the CHRONICA letters (f1783-1855).",
            "Stitched = remembered, unpicked = forgotten, bare linen with underdrawing = unwritten (f955, f1149, f1630, the blank card).",
            "Scale follows loudness: the closest views sit on the quietest moments (f0, f798) and the two great scale moves sit on the two biggest musical events (f1283, f1760)."],
        "sync_points": [{"frame": f, "what": w} for f, w in SYNC],
        "shots": shots_out,
        "six_keyframes": KEYFRAMES,
        "poc": POC,
        "budget": {
            "eevee_1080p_frames": e1080, "eevee_1440p_hero_anim_frames": hero_anim,
            "hero_1440p_equivalent_incl_stills": h1440 + 10,
            "total_eevee_anim_frames": total_eevee_anim,
            "limits": {"eevee_1080p": 600, "hero_1440p": 150},
            "game_demo_mode_frames": 28,
            "comp_frames": 1984,
            "wall_clock_estimate": "Eevee 1080p ~490 x 30 s = 4.1 h single (~3.4 h with 2 procs); hero ~2.5 h; comp ~1.4 h; game plates ~15 min. Total ~7 h on 4 shared cores, leaving ~110 1080p and ~80 hero frames for retakes."},
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    return data, e1080, hero_anim, h1440


def md_escape(s):
    return s.replace("|", "/")


def write_md(data, e1080, hero_anim, h1440):
    L = []
    A = L.append
    A(f"# {TITLE}")
    A("")
    A("Draft storyboard for the 66.133 s CHRONICA intro (2560x1440, 30 fps, frames 0-1983), creative angle **Scale Journey**.")
    A(f"Machine-readable shot list: `{OUT_JSON}`. Audio: `audio/audio_master_1984f_s16.wav`. Frame convention: `frame = floor(t x 30)`.")
    A("")
    A("## Logline")
    A("")
    A(LOGLINE)
    A("")
    A("## The idea in one paragraph")
    A("")
    A("The film is one journey through scale, and **scale follows the music**. The closest views sit on the quietest sound: the opening drone and the collapse into silence. "
      "The widest views sit on the hollow war, when the world is far away. "
      "The two great scale changes sit on the two biggest musical events. On the **bass entry (f1283, 'grew dark')** the camera dives *into* the cloth, between its threads, into a miniature stumpwork world built from the real game models. "
      "On the **climax (f1744-1783, peak f1760)** it climbs *out* and finds that world lying on the chronicler's table, which is the main menu. "
      "One object ties it together: **a gold thread**. It is stitched in at frame 0, torn out when the oath breaks, couched as the realm borders, and at the end it stitches the word CHRONICA while the narrator asks what the chronicles will say. "
      "Stitched means remembered, unpicked means forgotten, and bare linen with underdrawing means unwritten. That is why the film ends on a **blank parchment card** that the live menu then fills.")
    A("")
    A("## Scale spine (field of view across the 2560 frame)")
    A("")
    A("| frames | time (s) | scale move | music |")
    A("|---|---|---|---|")
    for sp in data["scale_spine"]:
        a, b = sp["frames"]
        A(f"| {a}-{b} | {a/30:.2f}-{(b+1)/30:.2f} | {sp['move']} | {sp['music']} |")
    A("")
    A("Ladder in practice: **24 mm** macro (f0) -> **512 mm** oath panel (f230) -> **18 mm** unpick (f798) -> **1 m** war frieze (f899) -> **whole world** map (f1051) -> **~15 mm** between threads (f1292) -> **miniature eye-level** (f1336-1725) -> **~0.9 m** chronicler's table = menu (f1800).")
    A("")
    A("## Storyboard at a glance")
    A("")
    A("| shot | frames | time (s) | audio anchor | what we see | technique | Blender frames |")
    A("|---|---|---|---|---|---|---|")
    for s in SHOTS:
        rf = []
        if s["eevee1080"]:
            rf.append(f"{s['eevee1080']} @1080p")
        if s["hero1440"]:
            rf.append(f"{s['hero1440']} @1440p")
        rf = ", ".join(rf) if rf else "-"
        ga, gv, gt = GLANCE[s["id"]]
        A(f"| **{s['id']}** {md_escape(s['name'])} | {s['start']}-{s['end']} | {s['start']/30:.2f}-{(s['end']+1)/30:.2f} | {md_escape(ga)} | {md_escape(gv)} | {md_escape(gt)} | {rf} |")
    A("")
    A("Cuts in the whole film: two hard cuts (f468 on 'died', f785 on 'crown'). Every other transition is diegetic: a continuous camera move, a match-dissolve on the crown, a fade through darkness, a burn-through, a smoke wipe, the dive and the climb-out.")
    A("")
    A("## Shots in detail")
    A("")
    for s in SHOTS:
        n = s["end"] - s["start"] + 1
        A(f"### {s['id']} - {s['name']}  (f{s['start']}-{s['end']}, {s['start']/30:.2f}-{(s['end']+1)/30:.2f} s, {n} frames, act {s['act']})")
        A("")
        A(f"- **Scale:** {s['field']}")
        A(f"- **Audio event:** {s['audio_event']}")
        A(f"- **Visual action:** {s['visual_action']}")
        A(f"- **Camera:** {s['camera']}")
        A(f"- **Technique:** {s['technique']}")
        A(f"- **Embroidery / material:** {s['material_behavior']}")
        A(f"- **Transition out:** {s['transition_out']}")
        A(f"- **Emotional purpose:** {s['emotional_purpose']}")
        A(f"- **Render cost:** {s['est_render_cost']}")
        A(f"- **Assets:** {', '.join(s['assets'])}")
        A("")
    A("## Six keyframes")
    A("")
    A("| # | frame | time (s) | description |")
    A("|---|---|---|---|")
    for i, k in enumerate(KEYFRAMES, 1):
        A(f"| {i} | {k['frame']} | {k['frame']/30:.2f} | {md_escape(k['description'])} |")
    A("")
    A("## Proof of concept: \"Into the Weave\" (f1262-1381, 4.0 s)")
    A("")
    A(POC["summary"])
    A("")
    A(f"- **Content:** {POC['content']}")
    A(f"- **Technique:** {POC['technique']}")
    A(f"- **Cost:** {POC['cost']}")
    A("- **Deliverables:** " + "; ".join(POC["deliverables"]))
    A("- **Pass criteria:** " + "; ".join(POC["success_criteria"]))
    A("")
    A("This shot is the riskiest in the film and the one the brief asks for: an embroidered 2D scene becoming a believable 3D space. If it works, S17-S23 are the same rig at different camera positions. "
      "If it fails, the fallback is a 2.5D dive (zoom stack through a macro weave render with a crossfade into a held 3D establishing plate). The angle survives, with less vertigo.")
    A("")
    A("## Render budget")
    A("")
    A("| shot | Eevee 1080p | Eevee 1440p hero | note |")
    A("|---|---|---|---|")
    for s in SHOTS:
        if s["eevee1080"] or s["hero1440"]:
            A(f"| {s['id']} | {s['eevee1080'] or ''} | {s['hero1440'] or ''} | {md_escape(s['est_render_cost'])} |")
    A(f"| **total** | **{e1080}** / 600 | **{hero_anim} anim + ~{h1440 - hero_anim + 10} still-equivalents** / 150 | |")
    A("")
    A(f"- Total Eevee animation frames: **{e1080 + hero_anim}** ({e1080} at 1080p, upscaled, plus {hero_anim} hero frames at 1440p). Stills: the 8K orthographic map (about 8 hero-equivalents) and about 10 look-dev stills.")
    A("- 3D is rendered on twos wherever the camera can be locked and moved in 2D (S20, S21 tail, S22). It is on ones only where the camera really travels in 3D (S01, S17-S19, S21 crane, S23).")
    A("- Blender covers 619 of the 1,984 frames (some of them on twos). The other 1,365 frames are numpy/cv2 2.5D compositor only, at 0.4 s/frame, or 3-6 s/frame when relighting. Every frame, Blender ones included, goes through the compositor for the grade, grain and fuzz layers.")
    A("- The game's own demo mode (SwiftShader, ~30 s/frame) renders about 28 frames: the S23 landing on twos and the S25 plates. These match the live menu exactly.")
    A("- Wall clock: about 7 h on the shared 4 cores (2 Blender processes at once for +21 %), leaving about 110 1080p frames and 80 hero frames for retakes.")
    A("")
    A("## Hand-off specification (S23-S25)")
    A("")
    A("1. **End frame = live menu first frame, with the card blank.** Capture two 2560x1440 frames from the game at the menu camera (seed 4242, zoom 11, pitch 66.09 deg, the first 3 s hold of the tour): one UI-free and one full menu. "
      "Build the end frame from the full capture, then inpaint the card's text and buttons with the parchment 9-slice (`tex/table_parchment/menu_card.png`, interior 272,357 to 1182,1334). Everything else is then pixel-identical to the live menu.")
    A("2. **Last 55 frames (f1929-1983) are identical.** The overlay holds the last frame while `engine.start` boots (measured about 20 s of main-thread block). The gold progress thread shows over it, so the still must work on its own.")
    A("3. **The dissolve fills the page.** The 0.9 s CSS opacity transition crossfades the blank card into the live card with its title, motto and buttons. The live UI does the writing.")
    A("4. **4:3 iPad.** `object-fit: cover` crops 320 px from each side of a 16:9 master, and the 4:3 menu layout differs (`base_4x3`: card 140..767 of 1600, taller banners, table_edge_bottom visible). "
      "Deliver a 4:3 variant of S23-S25 (f1726-1983) composited with `base_4x3` positions on a 2048x1536 game plate. The 2.5D layering makes this cheap. The overlay picks the source by aspect ratio.")
    A("5. **Audio.** The master stops at about -48 dBFS at f1983. Because picture is a still, this is acceptable, but a 0.5 s gain ramp on the mix tail (f1968-1983) is recommended. Game audio fades in over 2.5 s after the dissolve.")
    A("")
    A("## Prep work this angle needs (in order)")
    A("")
    A("1. **Board reconstruction (critical path).** Rebuild the seed-4242 'small' board in Blender: hex terrain types, coast, river, roads, realm borders, settlements, units. "
      "Read the layout from the game (demo-mode dump if available, otherwise sample hex centres on a top-down UI-free game plate). Match the menu area around Hautecouronne and Grandbois exactly; elsewhere approximate is fine.")
    A("2. **Embroidery map generator.** Port `style/tools/stitch_ref.py` into a tile generator producing albedo, height, tangent and stitch_id per terrain type (laid plus couching, running-stitch seams, satin, gold couching), following `work/shaders/terrain|water|border.gdshader`.")
    A("3. **Stitched model material** for the 59 OBJs: MTL Kd base, triplanar stitch normal, wool sheen and an inverted-hull brown outline (the game's `piece_outline`). Stumpwork tree generator. Quilted cloud planes from the cloud kit.")
    A("4. **Panel prep:** LIC re-synthesis of p1, p3, p1_empty and p6 (bible 5.2); p1 linen extension and the cord path above the banner; **p1_empty repair**; crown sprite cut from p1; goblet and flame masks.")
    A("5. **War frieze:** Bayeux-format strip (borders with diagonal bars and beasts, ground line, hillocks, tree divider) populated with tinted figure cards.")
    A("6. **Logo:** letter masks and skeleton paths from `logo_title`, a blank-valance inpaint, and the couched-gold stitch-on with a travelling glint.")
    A("7. **Game captures:** UI-free and full-menu 2560 plates, plus the S23 landing frames (zoom 7 -> 11) from demo mode, and 4:3 versions.")
    A("")
    A("## Risks and mitigations")
    A("")
    A("- **Blender board vs real game look at the S23 cross-match.** Mitigation: cross-match at peak motion blur (f1752-1765); calibrate colours from `models/game_palette.json` and the game plates; port the shader formulas. "
      "Best case: if demo mode accepts an arbitrary Camera3D transform, render S22-S23 (and possibly S18-S21) in Godot itself for an exact match, at about the same cost as Eevee.")
    A("- **Bridging procedural macro and the AI panel (S01-S02).** The macro sits on the banner cord over bare linen, where only linen and cord need to be procedural. The panel only takes over at 2.5x or wider, with LIC re-synthesis. The cord is drawn by the same twist model in 3D and in 2.5D.")
    A("- **Style gap between the AI panels and the game figure cards (S10).** The figure cards appear only at frieze scale (F0, about 300 px tall), on a Bayeux laid-and-couched ground, which unifies them.")
    A("- **Bible deviations, all deliberate:** (a) the crown lifts 30-35 mm (bible: 5-15 mm) so that its shadow can reach the lords. (b) A real 3D world (the bible says 'never pretend the cloth is a 3D world'). "
      "This is justified because the miniature is **stumpwork** (raised embroidery, a real historical technique) and is the game's own register: `piece.gdshader` calls its pieces 'broderie en relief (stumpwork)'. The panels themselves are never treated as 3D.")
    A("- **Climax busyness (S23).** All dressing motion comes from the camera move alone (per-layer depth parallax). Nothing animates independently except the valance sway, so the reveal reads as one gesture.")
    A("- **Budget.** 543 Eevee animation frames of 750 allowed. If time runs short: render S19 on twos with a 2D camera (-71) and shorten S18 to 30 frames (-16).")
    A("")
    A("## Sync map (frame-accurate)")
    A("")
    A("| frame | time (s) | event |")
    A("|---|---|---|")
    for f, w in SYNC:
        A(f"| {f} | {f/30:.2f} | {md_escape(w)} |")
    A("")
    with open(OUT_MD, "w") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    data, e1080, hero_anim, h1440 = build()
    write_md(data, e1080, hero_anim, h1440)
    print("ok", OUT_JSON, OUT_MD, "eevee1080", e1080, "hero_anim", hero_anim, "total", e1080 + hero_anim, "shots", len(SHOTS))
