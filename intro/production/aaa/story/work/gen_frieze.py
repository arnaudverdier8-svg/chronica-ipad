# Generates draft_frieze.json + draft_frieze.md (storyboard "The Living Frieze") from one data table.
import json, os, math

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
TOTAL = 1984

def t(f):
    return f / FPS

TITLE = "CHRONICA - The Living Frieze"
LOGLINE = ("A forgotten embroidered roll-chronicle, filmed on a rostrum, reads itself left to right: "
           "stitched into being in a golden age, unpicked by a king's death and a hundred years of war, "
           "aged, burned, overgrown and frayed into darkness, mended at dawn - until its unwritten end is "
           "stitched into the living game board and the player is handed the next, blank page.")

# ---------------------------------------------------------------------------------------------
# Shots. Every frame range is inclusive; ranges are contiguous 0..1983.
# eevee = unique Eevee renders charged to the budget ("1080" = Blender 4.0.2 Eevee-legacy 1920x1080
# upscaled; "1440" = hero 2560x1440 16 TAA). comp = 2.5D numpy/OpenCV frames.
# ---------------------------------------------------------------------------------------------
SHOTS = [
 dict(id="S01", anchor="silence f0-3; drone + 'There' f4; 'world' f39", summary="Black -> candle finds the gold chronicle thread in macro; pull-back between threads out over the border", start=0, end=90, name="Incipit: the first thread",
  audio="f0-3 digital silence; f4 D drone fade-in + 'There was a time when the world knew only one...' (time f19, world f39 stressed, one f76 with drone swell f76).",
  visual=("f0-3 pure black #07070A. From f4 a single raking candle (1900 K, elev 6 deg, az 135 deg) blooms from the upper left and finds the first thing in the film: "
          "a macro of linen weave and the CHRONICLE THREAD, a pair of silver-gilt threads couched along the upper border with crimson silk tie-downs every 2-3 mm; "
          "the glint travels left to right along it as the light grows. Pulling back, we pass between threads and out over the upper border (paired lions in "
          "diagonal-bar compartments); on 'world' f39 the horizon of stitched hillocks enters frame; the light warms to 3000 K and climbs to 22 deg."),
  camera=("Rostrum, face-on. Exponential pull-back 24 -> 3.3 px/mm (7.3x, ease in/out, constant perceived speed) f8-90; starts at f/8 macro with the cloth tilted 15 deg so a ~5 mm "
          "sharp band crosses the gold thread, DOF opens as the field widens; 1-2 px/frame drift right."),
  technique="2.5D only. Procedural stitch maps (stitch_ref.py functions: albedo, height_mm, tangent, material id, coverage) at 3 LODs (24 / 12 / 6.6 px/mm) cross-faded during the zoom; per-frame relight (moving key); synthetic DOF from height + tilt plane; fibre fuzz with rim light.",
  material="Linen weave resolved at macro (pitch 16 px) and LOD-faded to average albedo below 2.5 px; couched gold pair: Kajiya-Kay exp 180-400, glint interrupted at each tie-down, travels along the thread; wool lions matte with fuzz halo; first foxing and nail holes in the top border.",
  transition="Continuous move into S02 (no cut).",
  purpose="Hush and material truth before story: this is a real, old, handmade object. Plants the gold chronicle thread as the film's through-line.",
  comp=91, comp_s=6, eevee=0, eevee_res=None),

 dict(id="S02", anchor="'realm' f91; gap f104-126", summary="F0 one-realm landscape, four-colour road, VNVM REGNVM; landscape 'breathes' in the light sweep", start=91, end=139, name="One realm",
  audio="'realm' f91; music-only gap f104-126 (Dadd9 drone, -37 dBFS); 'one [table]' f126 with drone re-swell.",
  visual=("F0, full frieze height with both borders. Titulus VNVM REGNVM finishes stitching (blue-black stem stitch, needle glint on the last letters f91-100). "
          "The one realm: multicolour hillock bands, a river in paired olive lines, a bridge, ploughed fields, four small walled towns (stitched elevations of settle_1/settle_2) "
          "each with a house-colour pennant, joined by ONE road couched in four alternating colours (gold, crimson, woad, green: Bayeux alternation as the image of unity), a crowned capital at centre. "
          "In the gap a light sweep (az 120 -> 165 deg) makes the landscape breathe: relief exaggeration 1.0 -> 1.5 -> 1.1, hills and towns rise a finger's breadth with soft shadows, then settle - a promise of awakening."),
  camera="Truck right accelerating 2 -> 10 px/frame, slight push 3.27 -> 3.5 px/mm. Key action inside the 4:3 safe zone x 320-2240.",
  technique="2.5D: height-map relight per frame during the sweep, per-layer parallax <= 6 px for the breath. Town elevations = game OBJ rendered orthographic side-on (flat colour ID pass, Eevee/workbench stills, not counted) then run through the laid-and-couched / stem-stitch synthesiser.",
  material="Narrative register: matte wool laid-and-couched fills with the couching-bar shadow grid (the Bayeux signature), stem-stitch outlines with 0-1 mm linen gaps, linen 40-55 % of frame; Act I dyes near fresh values; heraldic pennants slightly raised satin.",
  transition="Tree divider T1 (interlace tree, trunk banded in the four house colours) crosses frame centre f126-139; splice behind it into p1 via an 8-frame match dissolve on the identical tree.",
  purpose="Plenitude and unity: one land, one road, all four colours in balance.",
  comp=49, comp_s=5, eevee=0, eevee_res=None),

 dict(id="S03", anchor="'table' f140; 'oath' f173; near-silence f185-198", summary="Truck into p1: table candles light, glint along the oath sword", start=140, end=211, name="One table, one oath",
  audio="'table' f140; 'one oath' f162-184 ('oath' f173); near-silence f185-198 (-45 dBFS); +10 dB swell f198-212 into 'one crown'.",
  visual=("p1 (the king and four lords at the oath table) slides in. Anticipating 'table', the stitched candle flames on the table light one by one left to right (f134-146; laid-strand flames, 1900 K pools bloom on the linen). "
          "Anticipating 'oath' (f167-181) a glint runs along the sword lying under the five hands. In the near-silence f185-198 everything holds; only 2 px/frame drift."),
  camera="Truck decelerating 10 -> 2 px/frame while pushing F0 -> F1 (3.5 -> 4.65 px/mm); p1 fills frame width by f200.",
  technique="2.5D: p1 with structure-tensor/LIC stitch re-synthesis and ratio relight (style bible 5.2); candle flames as an animated stitched layer on twos; sword metal mask (HSV + hand cleanup).",
  material="Panel needle-painting fills with re-synthesised strand relief; sword metal glint exp 300 travelling hilt -> tip; candle-flame wool sways 1-3 Hz.",
  transition="Continuous.",
  purpose="Ceremony and bond: the litany gets light-beats instead of cuts, so the rhythm is not mechanical.",
  comp=72, comp_s=3, eevee=0, eevee_res=None),

 dict(id="S04", anchor="'crown' f230; gap f248-276", summary="Push to the king; crown gold flares; VNA CORONA stitches on", start=212, end=275, name="One crown",
  audio="'one crown.' f212-248 ('crown' f230, attack f229); music-only gap f248-276 (-32.8 dBFS), crescendo peaking f271.",
  visual=("Slow push to the king. On 'crown' (f224-236) the crown's couched gold flares and a glint circles the circlet. Titulus VNA CORONA stitches on above the royal banner (f236-262). "
          "Through the gap the light is at its warmest; purple king, four house tunics in balance."),
  camera="Exponential push-in 1.00 -> 1.12x panel-native centred on the crown (inside the 1.4x re-synthesis limit); 2 px/frame drift.",
  technique="2.5D (crown metal mask from p1; tituli = Cinzel 700 skeletons stem-stitched, baseline wobble +/-0.8 mm).",
  material="Metal thread glint on crown only (<3 % of pixels); royal purple (madder over woad) reserved for the king.",
  transition="Continuous.",
  purpose="Height of the golden age: authority, warmth, order.",
  comp=64, comp_s=3, eevee=0, eevee_res=None),

 dict(id="S05", anchor="'raised' f285; 'cups' f308", summary="Goblets lift 10-12 mm out of the cloth on thread tethers", start=276, end=338, name="They raised their cups",
  audio="'They raised their cups' f276-322 ('raised' f285, 'cups' f308 attack f307); bass blips f296, f323; gap f322-339.",
  visual=("Pull back to the whole table. First awakening, tiny: the gold goblets on the table lift out of the cloth by 10-12 mm (anticipation dip f280, rise f283-292 on twos, staggered 2 frames) - their stitches tauten into thread tethers, "
          "soft contact shadows open beneath, and the linen where they lay shows an underdrawn outline and needle holes. They hold high on 'cups' f308, glinting."),
  camera="Exponential pull-back 1.12 -> 1.00x to full p1 (F1).",
  technique="2.5D layered lift: goblet cut-outs (hand masks) with 4-8 px parallax, shadow offset from height and light vector, tether curves drawn as stitched strands; base patches inpainted to bare linen + underdrawing + hole field.",
  material="Metal goblets glint; tethers are wool strands catching a 25 % rim light; linen lips around the needle holes.",
  transition="Continuous.",
  purpose="Celebration - and the first sign the cloth is alive. Also fixes the p1 mismatch (no raised cups in the panel).",
  comp=63, comp_s=3, eevee=0, eevee_res=None),

 dict(id="S06", anchor="'swore' f349; 'end' f391; gap f402-446", summary="Goblets settle; camera follows the gold thread right; light cools; T2 splice", start=339, end=445, name="and swore it would never end",
  audio="'and swore it would never end.' f339-402 ('swore' f349, strongest early drone swell f358, 'never' f381, 'end' f391); music-only gap f402-446 (1.46 s, -33.5 dBFS) for the panel change; bass f390, f428.",
  visual=("On 'swore' the goblets settle back into the cloth on twos (f349-357). The camera releases rightward along the upper border following the gold chronicle thread, which runs on and on out of frame - 'never end'. "
          "Titulus HIC OMNES IVRAVERVNT stitches in red-brown (f360-395). In the gap the light cools and sinks (3000 K -> 1900 K, -0.7 EV, elev 22 -> 12 deg); tree divider T2, its trunk banded in dark woad, crosses frame f428-445."),
  camera="Pull back F1 -> F0 (f339-380); truck right 0 -> 12 px/frame (f350-400), hold 12 px/frame with 180-deg motion blur across the divider.",
  technique="2.5D (relit for the light change).",
  material="Gold thread glint leads the eye right; dye warmth drains as the light cools.",
  transition="T2 divider splice into p3: 8-frame match dissolve f438-445 on the identical tree.",
  purpose="Confidence curdling into foreboding: the promise outruns the frame while the light dies.",
  comp=107, comp_s=4, eevee=0, eevee_res=None),

 dict(id="S07", anchor="'king' f458; 'died' f469", summary="p3 king on bier; a candle flame is unpicked on 'died'", start=446, end=497, name="Then the king died",
  audio="'Then the king died' f446-483 ('king' f458, 'died' f469); D drone -6 dB at f480; bass swell f495.",
  visual=("p3: the king on his bier, night-blue ground, four tall candles. Act II light: one cold candle key at 12 deg, saturation 0.7, only the crown carries gold. "
          "On 'died' (f465-471) the nearest candle's stitched flame is unpicked - its threads drawn out in reverse stitch order over 6 frames, leaving needle holes and a bare underdrawn flame; the cloth drops 0.5 EV."),
  camera="F1, drift right decelerating 3 -> 2 px/frame.",
  technique="2.5D (p3 re-synthesis; unpick = stitch_id threshold run backwards on a hand-masked flame).",
  material="Unpicked strands lift and curl up to 20 mm before vanishing; holes are dark pits with raised linen lips.",
  transition="Continuous.",
  purpose="Death told by the cloth losing a stitch, not by melodrama.",
  comp=52, comp_s=3, eevee=0, eevee_res=None),

 dict(id="S08", anchor="'heir' f522; drone gone f548", summary="Bare linen with an underdrawn heir never stitched; T3 winter tree", start=498, end=560, name="and left no heir",
  audio="'and left no heir,' f498-532 ('heir' f522); D drone gone by f548 (-25 dB); music-only gap f532-561 (F6, -28.1 dBFS) - the lament chords begin.",
  visual=("The camera drifts past the foot of the bier into a narrow strip of bare linen between two blue-black couched bars: only the designer's underdrawing is here - a small crowned figure in faint brown ink that was never stitched. "
          "Titulus SINE HEREDE in red-brown. As the drone (the floor of the score) disappears, we look at the heir who never was. Then T3, a leafless winter tree in blue-black, crosses frame f548-560."),
  camera="F1 truck 3 -> 8 px/frame.",
  technique="2.5D (underdrawing = warm-brown ink line with slight bleed into the weave, no relief).",
  material="Bare linen, no wool: the absence of relief is the image.",
  transition="T3 divider splice (match dissolve f553-560) into the table scene repeated further along the frieze.",
  purpose="Vacancy: the score loses its floor exactly as the line of succession does.",
  comp=63, comp_s=2, eevee=0, eevee_res=None),

 dict(id="S09", anchor="'lord' f578; 'empty chair' f656-681", summary="The table again with the king unpicked: a needle-hole silhouette; push into the empty chair", start=561, end=716, name="Every lord looked at the empty chair",
  audio="'and every lord who had sat at that table looked at the empty chair' f561-681 ('lord' f578, 'table' f621, 'looked' f637, 'empty' f656, 'chair' f669); lament chords about -28 dBFS; gap f681-717 (fullest music 23-25.5 s).",
  visual=("The oath table again (Bayeux repeats scenes along the strip), but the king and his throne have been unpicked out of the frieze: in their place bare linen pricked with thousands of needle holes tracing his form, snipped thread ends curling, the faint underdrawing of the throne. "
          "The four lords remain in cold candlelight. On 'lord' f578 a grazing light passes over the four faces left to right; on 'looked' f637 the camera starts toward the empty chair and lands on the hole-pricked silhouette on 'chair' f669."),
  camera="F1 truck slowing 8 -> 0 px/frame (f561-600), then exponential push-in 1.00 -> 1.35x into the chair (f600-681) with re-synthesis; hold with 2 px drift through the gap.",
  technique="2.5D: p1 maps re-used; king+throne mask -> procedural linen patch + needle-hole height field along LIC streamlines (one hole per 3.5 mm stitch), 2D fibre curls. Does not use the broken p1_empty plate.",
  material="Needle holes catch grazing light; dyes on the lords pushed toward aged values; Act II grade (sat 0.7, chroma cap 0.12).",
  transition="Continuous into S10.",
  purpose="The hole where power was: covetous silence.",
  comp=156, comp_s=4, eevee=0, eevee_res=None),

 dict(id="S10", anchor="'own' f741; 'crown' f785; collapse f797", summary="Crown lifts; light swings so its shadow crosses each lord's head; candles unpicked", start=717, end=798, name="His own head beneath the crown",
  audio="'and saw his own head beneath the crown.' f717-799 ('own' f741 stressed, 'head' f753, 'crown' f785); music fullest, then collapses by 20 dB at f797.",
  visual=("Above the empty chair the crown (intro/crown, raised satin + couched gold) lifts 15 mm off the cloth and hangs - second small awakening. The key light swings right to left (az 160 -> 40 deg over 2.3 s: decline), "
          "so the crown's cast shadow slides across the linen and passes over each lord's head in turn (f735, f749, f763, f777): each sees his own head beneath the crown. "
          "f788-796 the crown drops back flat; on the collapse f797 every table candle is unpicked at once and the frame falls -2 EV."),
  camera="Exponential pull-back 1.35 -> 1.00x (f717-745) so all four lords are in frame by 'own'; then locked with 1 px drift.",
  technique="2.5D: crown layer with parallax; shadow = crown alpha offset by 15 mm / tan(elev) along the light vector, softened by distance; per-frame relight for the moving key.",
  material="Gold glint migrates over the crown as the light swings; wool sheen on the tunics follows the light; candles unpick together.",
  transition="Collapse to near-black f797-815.",
  purpose="Ambition and rivalry made visible by light alone; the seed of war.",
  comp=82, comp_s=6, eevee=0, eevee_res=None),

 dict(id="S11", anchor="near-silence f797-844", summary="Near-black hold; hidden splice; ember glow from below", start=799, end=843, name="Silence",
  audio="Near-silence f797-844 (-47 dBFS, 1.6 s, Gm(add9) whisper): the strongest internal boundary.",
  visual=("Almost black: a cool night fill (#141325 at about 10 %) shows only the weave. Nothing moves but one loose thread end settling. "
          "At f820 an invisible splice in the dark to the war strip. f836-843 a dull ember glow starts at the bottom edge (firelight from below)."),
  camera="Locked, 1 px/frame drift.",
  technique="2D grade on cached plates.",
  material="Linen only; blacks never below #07070A.",
  transition="Firelight rises into S12.",
  purpose="Dread. The film holds its breath with the music.",
  comp=45, comp_s=0.5, eevee=0, eevee_res=None),

 dict(id="S12", anchor="'wars' f850; 'hundred years' f884-899", summary="Soldiers peel up out of the cloth and clash; ageing time-lapse; a second generation", start=844, end=924, name="The wars lasted a hundred years",
  audio="'The wars lasted a hundred years' f844-918 ('wars' f850, 'lasted' f867, 'hundred' f884, 'years' f899); music at or below -45 dBFS, thin airy texture; crescendo from f896.",
  visual=("The war strip: madder dusk sky (war_bg), two armies of stitched figure cards lying flat in the cloth - the blue realm marching right to left, against the reading direction, the red realm facing it; far horse legs alternate colours (Bayeux). "
          "Main awakening #1: on 'wars' (f846-862) the soldiers rise out of the cloth - each card peels up hinged at its feet (to 35 deg), its felt thickness showing, its stitches pulled taut as thread tethers, casting shadows on the holes where it lay. "
          "On 'lasted' they clash (idle -> strike pose swap + 0.12 s lunge, game timing, on twos; red hurt flash in wool). 'a hundred years' (f884-918): a time-lapse of the cloth - dyes fade aged -> bleached, woad greens, foxing and tidelines bloom, creases form, the gold border thread tarnishes; "
          "the soldiers fall flat, are unpicked, and a new generation (gold vs green) stitches on and rises again, faster."),
  camera="Truck right 4 px/frame at F0, 3 deg dutch; 2200 K firelight from below, flicker 2-6 Hz at 15-25 %.",
  technique="Eevee E1 (Blender 4.0.2, 1920x1080, 8 TAA, on twos = 15 unique fps stop-motion): cloth plane (war_bg albedo + synthesised stitch normal) + 16-24 figure cards (tex_tinted albedo, normal maps, 1.2 mm solidify felt edge, hinge rigs) + tether curves. Rendered with 15 % overscan; truck and dutch done in 2D. Ageing, hole fields and tituli composited in 2.5D. Upscaled 1080 -> 1440.",
  material="Figure satin sheen (mask B) catches the firelight; tethers taut then slack; dyes visibly ageing: the hundred years happen to the cloth.",
  transition="Continuous into S13.",
  purpose="Violence that repeats without progress; futility made physical.",
  comp=81, comp_s=1.5, eevee=41, eevee_res="1080"),

 dict(id="S13", anchor="'nothing' f942; near-silence f952-979", summary="All figures unpicked: a field of needle holes under grazing light", start=925, end=981, name="and ended nothing",
  audio="'and ended nothing.' f918-955 ('ended' f925, 'nothing' f942); near-silent gap f952-979 (-47 dBFS).",
  visual=("The last generation falls back flat and every figure is unpicked at once (f930-945): threads withdrawn along their outlines. Nothing remains but aged linen pocked with needle holes in the shapes of men and horses, snipped ends, faint underdrawn ghosts. "
          "In the silence a grazing light (elev 6 deg) slides slowly across the field; every hole casts a tiny shadow. Titulus HIC BELLA CENTVM ANNOS DVRAVERVNT, half faded, in the border."),
  camera="Truck slowing 4 -> 1 px/frame.",
  technique="Eevee E1 tail f925-945 on twos (11 renders), then 2.5D relight of the hole height field with the moving light.",
  material="Holes as relief (0.3 mm pits, raised lips), loose fibres rim-lit; all wool gone.",
  transition="f975-981 a scorch begins browning the linen at the right edge (burn-through starts).",
  purpose="'Nothing' made visible: a hundred years leaves only holes.",
  comp=57, comp_s=4, eevee=11, eevee_res="1080"),

 dict(id="S14", anchor="'Cities' f982; 'fell' f999; 'ruin' f1015", summary="Burn-through onto p6; towers drop on twos; wool flames, stitched smoke", start=982, end=1050, name="Cities fell to ruin",
  audio="'Cities fell to ruin.' f982-1028 ('Cities' f982/987, 'fell' f999, 'ruin' f1015); soft pad returns f1017 (+5 dB); near-silence f1029-1047.",
  visual=("The scorch spreads (linen browning to soot, a char edge glowing with stitched flame) and burns through the cloth, opening onto p6, the burning city, as the camera trucks onto it. "
          "On 'fell' (f995-1010) the cracked towers' upper sections drop on twos as rigid cut-outs (3 frames per pose) while their masonry stitches unpick; flames (laid strands) lick at 2-4 Hz with outer strands lagging; smoke (stem-stitch spirals) turns 10-20 deg/s; crows flap on threes. "
          "On 'ruin' f1015 the torn banner at the gate slumps. Titulus VRBES CECIDERVNT."),
  camera="Truck right 6 px/frame onto p6 at F1, 3 deg dutch, firelight from below.",
  technique="2.5D: burn-through mask (noise-driven front, soot multiply, char rim), p6 re-synthesis, hand-cut tower segments, element animation on twos. No particles.",
  material="Fire is wool, smoke is stem stitch; soot multiply 30-70 %; scorched linen edge curls slightly.",
  transition="Smoke-spiral drift wipes the frame f1040-1050 into S15.",
  purpose="Loss of civilisation; the cloth itself is damaged.",
  comp=69, comp_s=4, eevee=0, eevee_res=None),

 dict(id="S15", anchor="'Roads' f1051; 'forest' f1101", summary="Act I road returns; interlace trees stitch over it until it is gone", start=1051, end=1137, name="Roads swallowed by the forest",
  audio="'Roads were swallowed by the forest.' f1051-1115 ('Roads' f1051, 'swallowed' f1075, 'forest' f1101); pad plateau about -40 dBFS (Dm add9); gap f1115-1138.",
  visual=("Beyond the smoke, the four-colour road from S02 returns as a visual rhyme - faded, broken, its couching loose. Interlace trees stitch themselves on over it: stem-stitch tendrils creep along the road from both borders, couched leaves bloom in olive/sage/forest alternation, banded trunks rise; "
          "the tree dividers multiply until on 'forest' f1101 the road is gone. Titulus SILVA VIAS DEVORAVIT."),
  camera="Truck 6 -> 4 px/frame at F0; firelight fades out, cool dusk fill rises.",
  technique="2.5D procedural stitch-on (vector trees -> stitch maps with stitch_id order; reveal at 20-60 mm/s physical with a leading needle glint; real order laid -> bars -> tie-downs -> outline).",
  material="Fresh green wool over faded road dyes; new stitches slightly proud and unaged against the aged ground.",
  transition="Continuous.",
  purpose="The world returning to wildness; isolation begins.",
  comp=87, comp_s=3, eevee=0, eevee_res=None),

 dict(id="S16", anchor="'forgot' f1149; 'borders' f1211", summary="Couched bars wall the strip into cells; road threads snipped", start=1138, end=1253, name="Men forgot their own borders",
  audio="'Men forgot what lay beyond their own borders,' f1138-1229 ('Men' f1138, 'forgot' f1149, 'borders' f1211); gap f1229-1254 (D7 colour, swell from f1241).",
  visual=("Out of the forest, vertical couched bars stitch themselves down across the register like walls (the Bayeux border-compartment device, alternating slant), cutting the strip into narrow cells. In each, one small walled town of one house colour (stitched elevations of settle_0/1/2), each turned away from the others. "
          "The road threads joining them are snipped at every bar, cut ends curling. On 'forgot' f1149 the far side of each cell fades back to underdrawing. The last bar lands on 'borders' f1211."),
  camera="Truck 4 px/frame slowing; pull-back begins f1240.",
  technique="2.5D stitch-on and unpick masks.",
  material="Couched bars in blue-black and red-brown alternating; snipped wool ends with fuzz.",
  transition="Continuous into the S17 pull-back.",
  purpose="Suspicion and small worlds; the strip literally partitions itself.",
  comp=116, comp_s=3, eevee=0, eevee_res=None),

 dict(id="S17", anchor="BASS ENTRY f1283; 'dark' f1292; 'edges' f1319", summary="Pull-back: the strip on a dark table, edges fraying into darkness; one gold glint left", start=1254, end=1381, name="The world grew dark at its edges",
  audio="'and the world grew dark at its edges.' f1254-1336 ('world' f1263, 'grew' f1281, BASS ENTRY f1283 = biggest musical event (+26 dB), 'dark' f1292, 'edges' f1319); gap f1336-1382 (-31.9 dBFS) with bass swell f1345 and an in-gap swell into 'Now' from f1372.",
  visual=("On the bass entry the camera pulls back: the chronicle is revealed as a long strip lying along a dark walnut table, vanishing into darkness both ways - and its edges are dying. The borders fray, weft threads pull loose and curl, border beasts unravel into fringe, "
          "darkness creeps inward (physical light falloff to -2.5 EV at the frame edges). The last candlelight dies on 'dark' f1292; on 'edges' f1319 the fraying bites into the main register. "
          "Gap: near-black hold; one gold glint survives at the far right end - the chronicle thread, unbroken. Titulus TENEBRAE IN FINIBVS dissolves into loose thread."),
  camera="Exponential pull-back 3.3 -> 0.85 px/mm (3.9x) f1283-1360 with a slight rise; then hold.",
  technique="2.5D: long plate assembled from all section plates at about 1 px/mm; animated fray masks + 2D fringe threads (curves with stitch shading). Optional Eevee E2 layer (on twos, 50 renders, 1080p) for 3D curling fringe.",
  material="Fraying weft and loose fibres rim-lit by the last light; linen darkening at the edges; aged dyes.",
  transition="Continuous; the surviving glint carries into S18.",
  purpose="Despair and smallness; the musical low point of the visual arc lands on the score's biggest event.",
  comp=128, comp_s=2, eevee=0, eevee_res=None, optional_eevee=50),

 dict(id="S18", anchor="'Now' f1382; 'ruler' f1407; 'whole' f1466; Bb gap", summary="Dawn sweep: cloth mends, dyes revive, four crests stitch on, thread re-couched", start=1382, end=1523, name="Now every ruler believes",
  audio="'Now every ruler believes the world can be made whole again.' f1382-1491 ('Now' f1382, 'ruler' f1407, 'believes' f1419, 'whole' f1466, 'again' f1477); bass pulses f1410, f1471; gap f1491-1524 (sustained Bb3 horn/choir, Bb major: the brightest, most hopeful colour).",
  visual=("On 'Now' dawn (4300 K) breaks from the left and sweeps left to right across the strip over 3 s. As it passes, the cloth mends itself: fringe threads re-weave into the edges (fray in reverse), darning in fresh thread closes holes, dyes revive from aged to fresh values (OKLab, staggered 0.2-0.4 s per region along the light). "
          "On 'every ruler' (f1395-1415) the four house crests (builders, legion, merchants, nomads: heraldic register, raised satin with gold cord) stitch on in the upper border, one every 5 frames, the last landing on the bass pulse f1410. "
          "On 'whole' f1466 the chronicle thread is re-couched end to end, a glint running the visible length. Bb gap: arrival at the end of the narrative, full dawn."),
  camera="Exponential push back in 0.85 -> 3.4 px/mm (f1382-1480) while trucking right about 1 m toward the end of the strip; then truck 8 -> 4 px/frame.",
  technique="2.5D: S17 masks run in reverse; per-region aged/fresh albedo lerp; crests relit with luminance-derived normals as padded satin.",
  material="Colour revival (aged -> fresh) is the visual metaphor for 'made whole'; heraldic satin flashes per block as the light passes; fresh darning visibly mismatched (#E2DBC6).",
  transition="Continuous.",
  purpose="Hope and ambition: the world and the cloth are mended together.",
  comp=142, comp_s=5, eevee=0, eevee_res=None),

 dict(id="S19", anchor="'banner' f1533; bass f1536", summary="One banner rises out of the unwritten linen (Eevee)", start=1524, end=1558, name="One banner",
  audio="'One banner,' f1524-1544 ('banner' f1533); bass pulse f1536; crescendo f1520-1550.",
  visual=("The narrative stitching ends; to its right lies the unwritten remainder of the roll - fresh linen with only the designer's underdrawing (a hex lattice, a coastline). In it one banner is stitched flat (couched gold pole, navy satin flag). "
          "From f1527 its stitches tauten; on the bass pulse f1536 it rises out of the cloth into 3D, hinging up on thread tethers toward the lens, the flag unfurling in dawn raking light. It rises exactly where the gold standard above Grandbois sits in the final menu (about x1560 y470)."),
  camera="Truck right 4 -> 2 px/frame at about 3.4 px/mm, perspective rostrum camera (35 mm equivalent) so risen pieces show parallax.",
  technique="Eevee E3 (1920x1080, 16 TAA, on ones for camera parallax; risen pieces stepped on twos). settle_banner model with stitch material; its unrisen state registered to its own 2D stitched footprint (same albedo/normal maps) so the swap is invisible.",
  material="Navy satin flag with anisotropic sheen; couched gold pole glint; tethers release with a small recoil.",
  transition="Continuous.",
  purpose="A single act of will - the player's first gesture, foreshadowed.",
  comp=35, comp_s=1, eevee=32, eevee_res="1080"),

 dict(id="S20", anchor="'village' f1569", summary="One village extrudes out of its stitched footprint (Eevee)", start=1559, end=1598, name="One village",
  audio="'one village,' f1559-1583 ('village' f1569); gap f1583-1599 (0.52 s, Dm add9).",
  visual=("Beneath the banner a village stitched in plan (laid madder/terracotta roof tiles in alternation, blue-black stem-stitch walls) rises: walls extrude up out of their stitched footprints, houses pop up row by row on twos, thread tethers snap free; "
          "the dawn raking key (elev 28 deg) throws lengthening cast shadows, the main depth cue under a top-down camera; the hex underdrawing around it stays unstitched."),
  camera="Drift 2 -> 1 px/frame; same perspective rostrum camera (real parallax between roofs and ground).",
  technique="Eevee E3 (same scene): settle_1 OBJ with projected stitch albedo on roofs and triplanar laid-and-couched texture on walls; contact shadows; tethers as curves. This shot is the head of the PoC look-dev.",
  material="Roofs keep exactly the 2D stitch texture they had when flat; new side walls carry synthesised stitches at the same mm scale (no stretched pixels).",
  transition="Continuous.",
  purpose="The first home: growth after ruin.",
  comp=40, comp_s=1, eevee=40, eevee_res="1080"),

 dict(id="S21", anchor="'one' f1599 bass; 'page' f1630; gap f1645-1689", summary="Gold thread frames a blank bay of linen on the menu-card rectangle", start=1599, end=1688, name="One blank page",
  audio="'one blank page.' f1599-1645 ('one' f1599 + bass pulse (+21.6 dB), 'blank' f1614, 'page' f1630); music-only gap f1645-1689 (1.46 s, Dm add9), bass swell f1664, in-gap swell f1658-1692.",
  visual=("On 'one' the gold chronicle thread leaves the restored border and couches a simple frame around an empty bay of pale linen on the left (glint racing round the rectangle f1600-1628): the blank page, placed exactly on the menu card rectangle (224,319)-(1227,1376). "
          "On 'page' f1630 the frame closes and light pools on it. Gap: stillness; the underdrawn hex lattice on the right warms as the light rises; the thread's end rests at the page corner, waiting."),
  camera="Ease to a full stop by f1640 (2 -> 0 px/frame); locked thereafter - menu registration starts here.",
  technique="2.5D comp; E3 renders only to f1610 (12 renders), then a held Eevee plate for the village/banner layer.",
  material="Fresh unaged linen in the bay (#E6D7B6 range), faint ink underdrawing, the gold cord frame raised 0.6 mm.",
  transition="Continuous (same framing) into S22.",
  purpose="Possibility and invitation: the space left for the player.",
  comp=90, comp_s=1, eevee=12, eevee_res="1080"),

 dict(id="S22", anchor="'remembered' f1726 bass", summary="Board embroidered along the hex underdrawing; page lifts; tilt begins (Eevee hero)", start=1689, end=1743, name="When this age is remembered",
  audio="'When this age is remembered,' f1689-1744 ('age' f1707, 'remembered' f1726 + bass pulse #8 f1726); building toward the climax.",
  visual=("The thread runs on: from the page corner it couches gold realm borders along the underdrawn hex lines (glint racing), satin-stitch fields fill hex by hex in a wavefront spreading right and back (greens, wheat, ochre), the sea floods in stitched denim blue (#316994) with wave marks - the board is embroidered, in 2D, before our eyes. "
          "On 'remembered' f1726 the page lifts gently off the cloth (scale 1.000 -> 1.015, soft shadow; it stays square to the lens) while the cloth behind starts to tilt back - the camera cranes 0 -> 10 deg around Grandbois - and the village grows (settle_1 -> settle_2 pieces rising on twos)."),
  camera="Locked until f1726, then a 3D crane tilt pivoting on Grandbois, converging on the game's menu camera (fov 30 deg, pitch 66.09 deg, distance 20.9).",
  technique="f1689-1711: 2.5D stitch-on of a rectified (face-on) version of the UI-free game plate, re-synthesised as stitches. f1712-1725: 14-frame cross to the zero-tilt Eevee render (identical content; the PoC's critical registration). f1712+: Eevee E4 hero (2560x1440, 16 TAA, on ones): board proxy plane + game OBJs at the menu-map positions, UVs = projection of the UI-free game plate from the menu camera, stitch-on driven by a per-hex delay map.",
  material="Satin hex fields (silk exp 40, sheen per block), couched gold borders (metal glint travelling), denim sea with stitched wave marks: the game's own embroidery language arrives.",
  transition="Continuous.",
  purpose="Lift-off and recognition: the chronicle turns into the game.",
  comp=55, comp_s=4, eevee=32, eevee_res="1440"),

 dict(id="S23", anchor="climax gap f1744-1783, peak f1760", summary="Everything rises; camera lands on the menu view; beam and valance enter", start=1744, end=1782, name="Climax: the cloth becomes the board",
  audio="Music-only climax gap f1744-1783: loudest music of the piece (-25.6 dBFS, Bbmaj7), peak f1760, bass swell f1755.",
  visual=("Everything awakens: towns, castles, farms, forests and figure groups rise out of the cloth, staggered from Grandbois outward, rigid, on twos, tethers releasing; the tilt completes to the menu angle (24 deg off face-on) by f1775; a warm 3200 K light sweep passes left to right and the couched gold borders flash in sequence. "
          "The walnut beam slides down into the top edge (f1750-1768) and the navy valance unrolls beneath it (f1760-1782) - its letters not yet stitched, only underdrawn."),
  camera="Crane completes onto the exact menu camera, ease-out by f1778.",
  technique="Eevee E4 hero (2560x1440) + 2D comp of chrome layers (bar and valance matted from a native 2560x1440 menu capture; valance letters removed/inpainted for the stitch-on in S24).",
  material="Heraldic register now dominant: raised satin, gold, game-saturated colour, against the board's matte fields.",
  transition="Continuous.",
  purpose="Triumph: the world made whole, and handed over.",
  comp=39, comp_s=2, eevee=39, eevee_res="1440"),

 dict(id="S24", anchor="'chronicles' f1801; 'you' f1846", summary="Thread stitches 'Chronica'; banners, candles, statues; page becomes the blank card", start=1783, end=1854, name="What will the chronicles say of you?",
  audio="'what will the chronicles say of you?' f1783-1855 ('chronicles' f1801, 'say' f1824, 'you' f1846); music recedes 19 dB (f1783 -> f1824), bass gone by f1824; a faint high chord remains.",
  visual=("Motion stops except thread and light. On 'chronicles' (f1787-1812) the gold thread climbs from the board's border into the valance and couches the letters C-h-r-o-n-i-c-a (3 frames per letter, glint leading), then the crown and fleurs-de-lis (f1806-1822): the identity is literally stitched from the chronicle thread. "
          "The Eevee board cross-dissolves to the real UI-free game plate (f1800-1830, identical camera). The lion banners unroll (f1798-1828), the candles' stitched flames light (f1815-1832), the lion statues rise into the light from the lower corners (f1810-1846), "
          "and the page squares into the parchment card: linen cross-fades to parchment and the couched frame thickens into the walnut frame with brass corners - still blank - complete on 'you' f1846."),
  camera="Locked on the menu camera.",
  technique="2D comp at exact menu_layout px_2560x1440 rects; logo stitch-on from the logo_title gold mask (skeleton order + travelling glint); Eevee E4 hero frames f1783-1800 for the settle (18 renders); 1 extra 32-TAA registration still.",
  material="Gold floss letters on navy damask, twisted cord and fringe exactly as logo_title; wood and brass for the card frame; parchment interior blank.",
  transition="Hold into S25.",
  purpose="The question is turned to the player; the title answers 'chronicles'.",
  comp=72, comp_s=1.5, eevee=19, eevee_res="1440"),

 dict(id="S25", anchor="ring-out f1855-1983", summary="Near-still menu match, locked from f1940; overlay dissolves to the live menu", start=1855, end=1983, name="Ring-out: the chronicle awaits",
  audio="Narration ends f1855; 4.27 s ring-out of a soft unresolved high chord (G6 / Am7-C6 colour), -44 -> -48 dBFS at about 1 dB/s, no fade to silence; micro-fade f1982.",
  visual=("Near-still menu composition: game plate board + walnut bar (0,0,2560,128) + logo_title (784,0,992x296) + lion banners L (16,64,129x346) / R (2421,64,123x346) + candles L (10,687,92x331) / R (2453,687,98x331) + lion statues L (6,1163,190x274) / R (2362,1163,192x274) + the blank parchment card (224,319)-(1227,1376). "
          "Only living things: candle flames flicker (6-12 %, 1-3 Hz + 8-12 Hz), one gold sheen sweep along 'Chronica' (f1868-1925, left to right), a +/-2 % breath of light. From f1940 the frame is locked and identical to the live menu's first frame minus the card's text and buttons. "
          "The last frame is held by the overlay until the engine is ready, then the 0.9 s CSS dissolve reveals the live menu: the blank page is written (title, subtitle, buttons) and the menu music fades in."),
  camera="Locked (menu camera).",
  technique="2D comp only. Base = native 2560x1440 capture of the menu's first frame with the card's text/buttons removed and parchment re-synthesised; flicker and sheen layers fade to exactly 0 by f1940. A 4:3 variant (base_4x3 layout) of this shot is rendered for iPad.",
  material="Static, exact game art; only flame and metal-sheen layers animate, then stop.",
  transition="Overlay dissolve (0.9 s) into the live main menu.",
  purpose="Calm resolve; the chronicle waits for the player's hand. A seamless, pixel-matched hand-off.",
  comp=129, comp_s=0.5, eevee=0, eevee_res=None),
]

KEYFRAMES = [
 dict(frame=91, shot="S02", title="'realm' - the frieze established",
      description="F0 full frieze height with both borders: the one-realm landscape in Bayeux idiom (hillock bands, paired-line river, four walled towns, ONE road couched in four alternating house colours, crowned capital), VNVM REGNVM just stitched, gold chronicle thread glinting in the upper border, 3000 K raking key at 22 deg with the couching-bar shadow grid visible."),
 dict(frame=669, shot="S09", title="'chair' - the king unpicked",
      description="Push-in on the oath table repeated along the frieze: the king and throne have been unpicked, leaving bare linen pricked with needle holes in his silhouette, snipped thread ends and the faint underdrawing of the throne; the four lords in cold 1900 K candlelight, Act II grade (sat 0.7, only gold accent)."),
 dict(frame=899, shot="S12", title="'years' - soldiers risen out of the cloth",
      description="Eevee awakening: blue and red figure cards hinged up to 35 deg out of the war strip on taut thread tethers, felt edges and soft shadows on the needle-holed linen beneath, mid-strike; the cloth around them half-aged by the hundred-year time-lapse (bleached dyes, foxing, a tideline), firelight from below, 3 deg dutch."),
 dict(frame=1319, shot="S17", title="'edges' - the frieze fraying into darkness",
      description="After the bass entry pull-back: the chronicle is a thin strip on a dark walnut table, both ends lost in darkness, borders unravelling into curling fringe, weft threads hanging, light falling to -2.5 EV at the edges; one tiny gold glint at the far right."),
 dict(frame=1760, shot="S23", title="climax peak - the cloth has become the board",
      description="Menu-camera view reached: the 3D embroidered hex board (satin fields, couched gold realm borders, denim sea with stitched waves) with towns and figure groups risen out of the cloth on releasing tethers, Grandbois under its banner at centre, warm light sweep mid-frame, the blank page floating square to camera on the left, walnut beam in and navy valance unrolling with unstitched letters."),
 dict(frame=1983, shot="S25", title="final frame - pixel-matched hand-off",
      description="The live main menu's first frame minus the card contents: game board plate, walnut bar, gold-stitched 'Chronica' valance at (784,0,992x296), lion banners, candles, lion statues and the blank parchment card at (224,319)-(1227,1376), ready for the overlay dissolve that writes the page."),
]

POC = dict(
 title="PoC: 'The Cloth Becomes the Board'",
 frames=[1689, 1830],
 duration_s=round((1830 - 1689 + 1) / FPS, 2),
 summary=("142 frames (4.73 s) of the real film window f1689-1830 with the real audio ('When this age is remembered' + the climax gap + 'what will the chronicles...'). "
          "It proves the film's hardest claim and its hand-off: a face-on, physically embroidered 2D cloth becomes a convincing dimensional 3D game board and lands pixel-exact on the game's menu view."),
 beats=[
  "f1689-1711 (0.0-0.8 s) 2D: rostrum face-on, fresh linen with hex underdrawing; stitch-on wavefront: couched gold borders run along hex lines (metal glint travelling, tie-downs every 2-3 mm), satin fields fill hex by hex with laid strands, denim sea with stitched wave marks; plan-view town icons stitched flat. All from real stitch maps relit with a moving 4300 -> 3200 K raking key.",
  "f1712-1725 (0.8-1.2 s) the swap: 14-frame cross from the 2D comp to the zero-tilt Eevee render of the same board (identical albedo + baked stitch normals). Must be invisible.",
  "f1726-1778 (1.2-3.0 s) 3D: crane tilt 0 -> 24 deg pivoting on Grandbois onto the exact menu camera (fov 30, pitch 66.09, dist 20.9); fields swell to 1-2 mm satin relief, forests rise as stitched cones, towns extrude out of their stitched footprints on twos with thread tethers and contact shadows, the banner hinges upright; light sweep L->R, gold borders flash in sequence.",
  "f1779-1830 (3.0-4.7 s) convergence: Eevee board settles, cross-dissolve to the real UI-free game plate (f1800-1830); chrome begins (walnut beam, valance, first letters of 'Chronica' couching on 'chronicles' f1801).",
 ],
 technique=("Blender 4.0.2 Eevee-legacy (or bpy 5.2.2 Eevee-next via EGL), 2560x1440, 16 TAA, on ones for the tilt, rising pieces on twos. "
            "Board proxy = subdivided plane with hex-relief displacement (normal map for satin direction per hex) + the decoded game OBJs placed at the menu map's world positions; "
            "ground and model UVs = projection of a UI-free 2560x1440 game plate from the menu camera (so the end pose reproduces the plate exactly), with a town-free inpainted plate for the ground under rising towns; "
            "stitch layer = albedo/normal/height from the stitch_ref.py synthesiser applied in plate-UV space; per-hex delay map drives the stitch-on; tethers as bevelled curves; 2D comp adds fuzz halo, grade and chrome."),
 inputs=["1 UI-free game plate at 2560x1440 from demo mode (menu camera, seed 4242 small map, first tour frame; about 20-40 s in SwiftShader) - plus, if possible, one with towns/units hidden",
         "hex size + world positions of hexes, settlements and unit groups for seed 4242 (from the game's map/camera code) - fallback: solve from the plate with the known camera",
         "native 2560x1440 capture of the live menu first frame (for chrome mattes and the final match)",
         "models/*.obj + game_palette.json, stitch_ref.py functions, palette.json acts IV-V"],
 acceptance=["swap f1712-1725: median dE_ok x100 < 2 and no edge shift > 1 px between 2D comp and zero-tilt Eevee",
             "end match f1800: Eevee vs game plate median dE_ok x100 < 3, town silhouettes within 1 px",
             "stitch scale continuity: same px/mm across the swap; no shimmer during the tilt (weave/strand periods < 2.5 px prefiltered)",
             "material: wool specular <= 0.06, no white hotspots, metal glint confined to couched gold (< 3 % of pixels)",
             "every rising piece shows tethers + contact shadow + needle-hole footprint for >= 6 frames, so it reads as coming OUT of the cloth, not appearing on it"],
 cost="89 Eevee hero frames at 2560x1440 (f1712-1800 unique; about 60-80 s each, geometry-heavy, 2 processes) = about 1.5 h wall + 23 relit 2.5D frames + comp. These are production frames of S22-S24, so the PoC spends budget the film needs anyway.",
 fallback="If the game's world positions cannot be recovered in time: plate-only 2.5D - the board plane homography is known from the camera, towns are hand-masked and 'rise' by height-from-ground displacement with synthesised side walls; less parallax but the hand-off still matches.",
)

def eevee_totals():
    e1080 = sum(s["eevee"] for s in SHOTS if s["eevee_res"] == "1080")
    e1440 = sum(s["eevee"] for s in SHOTS if s["eevee_res"] == "1440")
    opt = sum(s.get("optional_eevee", 0) for s in SHOTS)
    return e1080, e1440, opt

def cost_str(s):
    parts = []
    if s["eevee"]:
        res = "1920x1080 8-16 TAA" if s["eevee_res"] == "1080" else "2560x1440 16 TAA hero"
        per = 25 if s["eevee_res"] == "1080" else 70
        if s["id"] in ("S12", "S13"):
            per = 12
        parts.append(f"Eevee {s['eevee']} renders @ {res} (~{per} s each = ~{math.ceil(s['eevee']*per/60)} min wall)")
    if s.get("optional_eevee"):
        parts.append(f"optional Eevee {s['optional_eevee']} renders @ 1080p fringe layer (~17 min)")
    parts.append(f"2.5D comp {s['comp']} fr x ~{s['comp_s']} s = ~{math.ceil(s['comp']*s['comp_s']/60)} CPU-min")
    return "; ".join(parts)

def validate():
    assert SHOTS[0]["start"] == 0 and SHOTS[-1]["end"] == TOTAL - 1
    for a, b in zip(SHOTS, SHOTS[1:]):
        assert a["end"] + 1 == b["start"], (a["id"], b["id"])
    for s in SHOTS:
        assert s["comp"] == s["end"] - s["start"] + 1, s["id"]

def main():
    validate()
    e1080, e1440, opt = eevee_totals()
    shots_json = []
    for s in SHOTS:
        shots_json.append(dict(
            id=s["id"], name=s["name"], anchor=s["anchor"], summary=s["summary"], start_frame=s["start"], end_frame=s["end"],
            start_s=round(t(s["start"]), 3), end_s=round(t(s["end"] + 1), 3), frames=s["end"] - s["start"] + 1,
            audio_event=s["audio"], visual_action=s["visual"], camera=s["camera"], technique=s["technique"],
            material_behavior=s["material"], transition_out=s["transition"], emotional_purpose=s["purpose"],
            est_render_cost=cost_str(s), eevee_renders=s["eevee"], eevee_res=s["eevee_res"],
            optional_eevee_renders=s.get("optional_eevee", 0)))
    doc = dict(
        title=TITLE, angle="The Living Frieze", logline=LOGLINE,
        master=dict(width=2560, height=1440, fps=FPS, frames=TOTAL, duration_s=round(TOTAL / FPS, 3),
                    audio="aaa/audio/audio_master_1984f_s16.wav", frame_convention="frame = floor(t*30)"),
        eevee_budget=dict(renders_1080=e1080, renders_1440_hero=e1440, optional_1080=opt,
                          total_committed=e1080 + e1440, total_with_optional=e1080 + e1440 + opt,
                          limits="<= 600 at 1080p (upscaled) + <= 150 hero at 1440p"),
        shots=shots_json, six_keyframes=KEYFRAMES, poc=POC)
    with open(os.path.join(OUT, "draft_frieze.json"), "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    with open(os.path.join(OUT, "draft_frieze.md"), "w") as f:
        f.write(render_md(doc))
    print("ok", e1080, e1440, opt)

# ---------------------------------------------------------------------------------------------
def render_md(doc):
    e = doc["eevee_budget"]
    L = []
    w = L.append
    w(f"# {doc['title']}: storyboard draft\n")
    w(f"**Logline.** {doc['logline']}\n")
    w("Master 2560x1440, 30 fps, 1984 frames (0-1983) = 66.133 s, muxed with `aaa/audio/audio_master_1984f_s16.wav`. Frame = floor(t x 30). "
      "Every shot below is anchored to the measured narration words and music events in `aaa/audio/audio_report.md` / `words.json`. Machine-readable twin: `draft_frieze.json` (generated from the same table by `story/work/gen_frieze.py`).\n")

    w("## 1. The idea in one paragraph\n")
    w("The film is a single object: a long embroidered **roll-chronicle** lying along a dark walnut table under a rostrum camera, read left to right like the Bayeux Tapestry, with upper and lower border friezes, interlace trees as scene dividers and stitched Latin tituli. "
      "The camera mostly trucks along it. Story time is carried by **what happens to the cloth**: scenes are stitched on (golden age), stitches are unpicked leaving needle holes (the king's death, a hundred years of war), dyes fade and stains bloom (the hundred years), the cloth burns (cities fall), "
      "trees stitch over the road (the forest), couched bars wall the strip into cells (borders), the edges fray into darkness (the world grows dark), and at dawn the cloth mends and its colours revive (made whole). "
      "**3D happens only when something rises out of the cloth**: goblets and the crown (tiny 2.5D lifts), soldiers peeling up on thread tethers (Eevee), one banner and one village (Eevee), and finally the unwritten end of the roll, which is stitched into the game's hex board and rises into the live 3D menu view (Eevee hero). "
      "One **gold chronicle thread** runs through the whole film and in the end writes the word *Chronica*. The last page of the roll is left blank; it becomes the menu card, and the game fills it.\n")

    w("## 2. Frieze layout (reading order)\n")
    w("Scale anchor: panel-native 5 px/mm, so each AI panel = 550 x 307 mm = the main register. Borders are procedural and **continuous above and below every panel**, which is what binds the refined AI panels and the Bayeux-idiom procedural sections into one object. "
      "F0 = full height 440 mm in 1440 px (3.3 px/mm); F1 = panel width (4.65 px/mm); F2 = one figure (12.8 px/mm). Where the strip is long, travel is compressed with **divider splices**: a tree divider that exists on both sides of the splice is used for an 8-frame match dissolve, so the cloth never visibly jumps.\n")
    w("| # | section | width (mm) | content / assets | shots |\n|---|---|---|---|---|")
    rows = [
     ("1", "Incipit + ONE REALM", "~900", "hem, nail holes, gold chronicle thread; procedural Bayeux landscape; town elevations from settle_* OBJ; lion border beasts from vignette_red/blue; VNVM REGNVM", "S01-S02"),
     ("2", "T1 interlace tree", "~60", "trunk banded in the four house colours (splice)", "S02/S03"),
     ("3", "p1 OATH", "550", "p1_oath.png (re-synthesised); VNA CORONA; HIC OMNES IVRAVERVNT after it", "S03-S06"),
     ("4", "T2 night tree", "~60", "dark woad bands (splice)", "S06/S07"),
     ("5", "p3 DEATH", "550", "p3_death.png; candle unpick", "S07"),
     ("6", "SINE HEREDE strip", "~150", "underdrawn, never-stitched heir between two couched bars", "S08"),
     ("7", "T3 winter tree", "~60", "leafless, blue-black (splice)", "S08/S09"),
     ("8", "p1' THE EMPTY CHAIR", "550", "p1 again with king + throne unpicked (procedural hole field), colder dyes; crown.png lift", "S09-S10"),
     ("-", "(dark splice f820)", "-", "hidden in the near-silence", "S11"),
     ("9", "WAR strip -> hole field", "~1100", "war_bg extended; tex_tinted figure cards (blue/red, then gold/green); needle holes; HIC BELLA CENTVM ANNOS DVRAVERVNT", "S12-S13"),
     ("10", "burn-through -> p6 RUIN", "550", "p6_ruin.png; tower cut-outs, wool flames, stem-stitch smoke; VRBES CECIDERVNT", "S14"),
     ("11", "FOREST over the road", "~700", "procedural interlace trees over the S02 road (rhyme); SILVA VIAS DEVORAVIT", "S15"),
     ("12", "BORDERS cells", "~800", "couched bars, isolated towns (settle_0/1/2 elevations)", "S16"),
     ("13", "RENEWAL", "~600", "mended edges, aged->fresh dyes, four crests (crest_*.png) in the upper border", "S17-S18"),
     ("14", "THE BLANK PAGE + unwritten remainder", "~295 bay + broad field", "fresh linen, ink hex underdrawing; banner + village rise; the field becomes the game board", "S19-S25"),
    ]
    for r in rows:
        w("| " + " | ".join(r) + " |")
    w("")

    w("## 3. Through-lines\n")
    w("**The gold chronicle thread** (couched silver-gilt pair, metal shading, the only metal besides crown, sword, goblets and title):\n")
    w("| shot | frame | what the thread does |\n|---|---|---|")
    for r in [("S01", "f4-90", "first image of the film; glint travels along it as light rises"),
              ("S06", "f350-445", "runs on out of frame: 'never end'"),
              ("S12", "f884-918", "tarnishes (#E9BE6A -> #7A5A2A) over the hundred years"),
              ("S17", "f1336-1381", "one surviving glint at the far end of the darkened strip"),
              ("S18", "f1466", "re-couched end to end on 'whole'"),
              ("S21", "f1600-1630", "frames the blank page"),
              ("S22", "f1689-1743", "couches the realm borders of the game board"),
              ("S24", "f1787-1822", "writes C-h-r-o-n-i-c-a on the valance"),
              ("S25", "f1868-1925", "final sheen sweep along the title")]:
        w("| " + " | ".join(r) + " |")
    w("")
    w("**Direction.** Time moves right (camera trucks right, content slides left). Regression is shown without breaking the reading direction: in the war the armies march right-to-left and the key light swings right-to-left (S10, S12); the dawn sweep in S18 goes left-to-right.\n")
    w("**Light and colour script** (palette.json `acts`): Act I 3000 K key at 22 deg, candles 1900 K, all four house colours balanced (S01-S06) | Act II 1900 K at 12 deg, sat 0.7, only the crown is gold (S07-S11) | Act III 2200 K firelight from below with flicker, 3 deg dutch, soot and madder, edges to -2.5 EV by f1319 (S12-S17) | Act IV 4300 K dawn sweep, aged -> fresh dye revival (S18-S21) | Act V 3200 K, navy and gold, gold sheen on the title (S22-S25).\n")
    w("**Scale ladder.** Macro F2/F3 only at the very start (S01) and in the push-ins on the empty chair (S09, max 1.35x panel-native with stitch re-synthesis, inside the 1.4x rule). Wider than F0 only for the darkness reveal (S17). Everything else F0-F1, trucking at <= 12 px/frame (motion blur where faster).\n")

    w("## 4. Storyboard overview\n")
    w("| shot | frames | time (s) | audio anchor | picture | technique | Eevee |\n|---|---|---|---|---|---|---|")
    for s in doc["shots"]:
        anchor = s["anchor"]
        pic = s["summary"]
        tech = "Eevee + 2.5D" if s["eevee_renders"] else "2.5D"
        ev = f"{s['eevee_renders']} @{s['eevee_res']}" if s["eevee_renders"] else "-"
        if s["optional_eevee_renders"]:
            ev += f" (+{s['optional_eevee_renders']} opt.)"
        w(f"| **{s['id']}** {s['name']} | {s['start_frame']}-{s['end_frame']} | {s['start_s']:.2f}-{s['end_s']:.2f} | {anchor} | {pic} | {tech} | {ev} |")
    w("")

    w("## 5. Shot by shot\n")
    for s in doc["shots"]:
        w(f"### {s['id']} - {s['name']}  (f{s['start_frame']}-{s['end_frame']}, {s['start_s']:.3f}-{s['end_s']:.3f} s, {s['frames']} frames)\n")
        w(f"- **Audio:** {s['audio_event']}")
        w(f"- **Picture:** {s['visual_action']}")
        w(f"- **Camera:** {s['camera']}")
        w(f"- **Technique:** {s['technique']}")
        w(f"- **Embroidery / material:** {s['material_behavior']}")
        w(f"- **Transition out:** {s['transition_out']}")
        w(f"- **Purpose:** {s['emotional_purpose']}")
        w(f"- **Render cost:** {s['est_render_cost']}\n")

    w("## 6. Sync map (the hits that must be frame-exact)\n")
    w("| frame | sound | picture |\n|---|---|---|")
    for r in [("0-3", "digital silence", "black"), ("4", "drone + 'There'", "candle key blooms on the gold thread"),
              ("39", "'world'", "horizon of the realm enters the pull-back"), ("91", "'realm'", "F0 realm, VNVM REGNVM complete"),
              ("140", "'table'", "table candles lit (from f134)"), ("173", "'oath'", "glint along the oath sword (from f167)"),
              ("230", "'crown'", "crown gold flares (from f224)"), ("285 / 308", "'raised' / 'cups'", "goblets rise / hold high"),
              ("349", "'swore'", "goblets settle; camera releases right"), ("391", "'end'", "gold thread runs out of frame"),
              ("402-446", "1.46 s music gap", "light cools; T2 divider splice"), ("469", "'died'", "candle flame unpicked (from f465)"),
              ("522 / 548", "'heir' / drone gone", "underdrawn heir that was never stitched"), ("578", "'lord'", "light grazes the four lords"),
              ("669", "'chair'", "push-in lands on the hole-pricked silhouette"), ("741-785", "'own head ... crown'", "crown shadow crosses each lord's head"),
              ("797", "music collapses -20 dB", "all candles unpicked, near-black"), ("850", "'wars'", "soldiers rise out of the cloth (from f846)"),
              ("884-899", "'hundred years'", "ageing time-lapse, second generation"), ("942", "'nothing'", "every figure unpicked, needle-hole field"),
              ("982 / 999 / 1015", "'Cities' / 'fell' / 'ruin'", "burn-through to p6 / towers drop / banner slumps"),
              ("1051 / 1101", "'Roads' / 'forest'", "trees stitch over the road / road gone"), ("1211", "'borders'", "last couched bar lands"),
              ("1283", "BASS ENTRY (+26 dB)", "pull-back into darkness begins"), ("1292 / 1319", "'dark' / 'edges'", "last light dies / fray reaches the register"),
              ("1382", "'Now'", "dawn sweep starts, cloth mends"), ("1410", "bass pulse ('ruler')", "fourth crest lands"),
              ("1466", "'whole'", "chronicle thread re-couched end to end"), ("1536", "bass pulse ('banner')", "banner rises (stitches tauten from f1527)"),
              ("1569", "'village'", "village rises (from f1563)"), ("1599", "bass pulse ('one')", "thread starts framing the page"),
              ("1630", "'page'", "page frame closes on the menu-card rectangle"), ("1726", "bass pulse ('remembered')", "page lifts, board starts to tilt"),
              ("1744-1783 (peak 1760)", "climax gap, loudest music", "everything rises; menu camera reached by f1778"),
              ("1801", "'chronicles'", "Chronica letters couched from the thread (f1787-1812)"), ("1846", "'you'", "blank card complete"),
              ("1855-1983", "ring-out, no fade", "near-still menu match, locked from f1940")]:
        w("| " + " | ".join(r) + " |")
    w("")

    w("## 7. Six keyframes\n")
    for i, k in enumerate(doc["six_keyframes"], 1):
        w(f"{i}. **f{k['frame']} ({k['frame']/FPS:.2f} s, {k['shot']}) {k['title']}.** {k['description']}")
    w("")

    p = doc["poc"]
    w(f"## 8. Proof of concept: {p['title'].split(': ',1)[1]}\n")
    w(f"**Window:** f{p['frames'][0]}-{p['frames'][1]} ({p['duration_s']} s). {p['summary']}\n")
    for b in p["beats"]:
        w(f"- {b}")
    w("")
    w(f"**Technique.** {p['technique']}\n")
    w("**Inputs needed:**")
    for i in p["inputs"]:
        w(f"- {i}")
    w("")
    w("**Pass / fail:**")
    for a in p["acceptance"]:
        w(f"- {a}")
    w("")
    w(f"**Cost.** {p['cost']}\n")
    w(f"**Fallback.** {p['fallback']}\n")
    w("Why this PoC and not the village: it tests the swap from real 2D stitch maps to 3D, the believability of rising out of the cloth, the stitch-scale continuity under a moving 3D camera, and the hand-off match to the live game, all in one 4.7 s window. The banner and village (S19-S20) reuse the same registration trick at lower stakes.\n")

    w("## 9. Render budget and pipeline\n")
    w("| block | shots | frames | unique Eevee renders | resolution | est. wall time |\n|---|---|---|---|---|---|")
    w("| E1 soldiers rise | S12-S13 | f844-945 | 52 (on twos) | 1920x1080, 8 TAA, light cards | ~11 min |")
    w("| E2 fringe (optional) | S17 | f1283-1381 | 50 (on twos) | 1920x1080 | ~17 min |")
    w("| E3 banner + village | S19-S21 | f1527-1610 | 84 (on ones) | 1920x1080, 16 TAA | ~35 min |")
    w("| E4 board awakening (hero) | S22-S24 | f1712-1800 + 1 still | 90 | 2560x1440, 16 TAA (+1 at 32 TAA) | ~1.5-1.8 h on 2 processes |")
    w(f"| **total** | | | **{e['renders_1080']} @1080 + {e['renders_1440_hero']} hero @1440 = {e['total_committed']}** (+{e['optional_1080']} optional) | | ~2.3 h |")
    w("")
    w(f"Limits: <= 600 at 1080p and <= 150 hero at 1440p, so the plan uses about {round(100*(e['renders_1080']+e['optional_1080'])/600)} % and {round(100*e['renders_1440_hero']/150)} % of them, leaving room for retakes. "
      "Everything else (about 1,650 frames) is the numpy/OpenCV 2.5D compositor: cached shaded plates moved in 2D at about 0.4 s/frame, plus per-frame relight (3-6 s/frame) only in light-sweep shots (S01, S02, S06, S09, S10, S13, S18). Total 2.5D CPU about 2 h.\n")
    w("Pipeline per section: build aligned maps (albedo linear, height_mm, tangent, material id, wool coverage, stitch_id) at 2x the on-screen density (6.6 px/mm for F0/F1 sections; 13 px/mm crops for S01 and S09); panels get structure-tensor + LIC re-synthesis and ratio relight; procedural sections (realm, borders, trees, tituli, forest, cells, renewal, page, underdrawing) come from the stitch_ref.py functions; fibre fuzz and ageing on top; tone + act grade; x264 from PNG.\n")

    w("## 10. Hand-off (S24-S25, the last ~4.3 s)\n")
    w("- From f1855 the composition is the main menu (16:9 layout, `menu_layout.json > px_2560x1440`) with an empty card. From f1940 nothing moves; the final frame equals the live menu's first frame minus the card's title, subtitle, buttons and footer.")
    w("- Build the final plate from a **native 2560x1440 capture of the menu's first frame** (the existing 2560 shots are an upscale of 1920 or a later tour stop, so a fresh capture is needed). Remove the card contents and re-synthesise parchment; matte the chrome (bar, valance, banners, candles, statues) from the same capture so the entrances in S23-S24 use the exact pixels.")
    w("- The board under the chrome is the UI-free demo-mode plate from the same camera (first tour frame; the live menu holds 3 s there before panning, so the dissolve lands on a still board).")
    w("- Candle-flicker and title-sheen layers fade to exactly zero by f1940 so the static candle and logo art match. The overlay holds the last frame while the engine boots, then dissolves (0.9 s) as the Godot audio fades in.")
    w("- iPad 4:3: `object-fit: cover` crops 320 px each side, and the live 4:3 menu uses `base_4x3` (bigger side banners, the table edge visible). Render a 4:3 variant of S25 (and the S24 chrome entrances) at the 4:3 layout, chosen by aspect in the overlay script. Key action in every shot stays inside x 320-2240.\n")

    w("## 11. Risks and mitigations\n")
    for r in [
     "**p1 appears twice** (S03-S06 and S09-S10). That is diegetic (Bayeux repeats scenes), and the second copy differs: king unpicked, colder grade, aged dyes, candles out. If it still reads as reuse, frame S09 tighter (1.15x) so the composition differs.",
     "**Style seam** between the refined AI panels and the Bayeux-idiom procedural sections. Mitigation: continuous procedural borders over all sections, one linen ground, one relight model, shared fuzz and ageing; procedural elements never sit beside panel fills at the same scale (style bible 5.2).",
     "**Board world positions** for seed 4242 may be hard to recover. The PoC targets this first, and has a plate-only fallback.",
     "**Top-down rising reads weakly** without side views. Use long raking shadows (elev 28 deg), tethers, contact shadows, perspective FOV around 35 mm-equivalent and a small truck for parallax; cards hinge (35 deg) instead of standing straight up.",
     "**Busy ending** (logo, banners, candles, statues, card in 72 frames). They are staggered on the receding music (logo f1787, banners f1798, statues f1810, candles f1815, card f1846) and all are motions the menu art already implies (unrolling, lighting, rising).",
     "**Figure-card resolution** (288-640 px). In S12 cards are at most about 300 px tall on screen at F0, so no upscaling beyond 1.1x.",
     "**Speed/shimmer**: trucks capped at 12 px/frame with 180-deg blur above that; weave LOD fade below 2.5 px; the camera never orbits the cloth until the climax, where it tilts only 24 deg (the menu view itself).",
    ]:
        w(f"- {r}")
    w("")
    return "\n".join(L)

if __name__ == "__main__":
    main()
