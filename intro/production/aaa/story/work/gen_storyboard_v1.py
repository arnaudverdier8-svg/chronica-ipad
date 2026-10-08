"""Generate storyboard_v1.md and storyboard_v1.json from one data source and check frame coverage.
Run: python3 -I gen_storyboard_v1.py  (from any directory; paths are absolute)."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sb_v1_shots import SHOTS  # noqa: E402

AAA = os.path.dirname(os.path.dirname(HERE))
OUT_MD = os.path.join(AAA, "story", "storyboard_v1.md")
OUT_JSON = os.path.join(AAA, "story", "storyboard_v1.json")
FPS = 30
LAST = 1983

TITLE = "CHRONICA - The Living Frieze (storyboard v1)"
LOGLINE = ("A forgotten embroidered roll-chronicle on a candle-lit walnut table reads itself left to right: a needle draws its "
           "first gold thread, one realm is stitched into being, a king is unpicked out of his own oath, a silent war rises "
           "and sinks in the cloth, fire, forest and four borders age it into darkness, dawn mends it, and its unwritten end "
           "is stitched into the living game board, where a blank page is left for the player.")

# ------------------------------------------------------------------ checks
def check_coverage(shots):
    shots = sorted(shots, key=lambda s: s["start"])
    assert shots[0]["start"] == 0, "must start at frame 0"
    for a, b in zip(shots, shots[1:]):
        assert b["start"] == a["end"] + 1, f"gap/overlap between {a['id']} and {b['id']}"
    assert shots[-1]["end"] == LAST, "must end at frame 1983"
    total = sum(s["end"] - s["start"] + 1 for s in shots)
    assert total == LAST + 1, total
    for s in shots:
        for k in ("audio_event", "visual_action", "camera", "technique", "material_behavior",
                  "transition_out", "emotional_purpose", "est_render_cost", "summary", "anchor", "name"):
            assert "|" not in s[k], f"pipe char in {s['id']}.{k}"
    return total

def secs(f):
    return f / FPS

for s in SHOTS:
    s["frames"] = s["end"] - s["start"] + 1
    s["start_s"] = round(secs(s["start"]), 3)
    s["end_s"] = round(secs(s["end"] + 1), 3)

TOTAL = check_coverage(SHOTS)
E1080 = sum(s["eevee"]["r1080"] for s in SHOTS)
E1440 = sum(s["eevee"]["r1440"] for s in SHOTS)

# ------------------------------------------------------------------ static data
SIX_KEYFRAMES = [
 dict(frame=91, shot="S02", title="'realm': the frieze and the one realm",
      description="The pull-back easing out over the one realm at ~F1: hillock bands, a paired-line river, four walled towns with house-colour pennants and ONE road couched in four alternating house colours running to a crowned capital; above, the upper border with paired lions and the gold chronicle thread, its first crimson tie-down still visible at top left; 3000 K raking key at 22 deg showing the couching-bar shadow grid; a trace of motion blur at the frame edges. No caption."),
 dict(frame=669, shot="S09", title="'chair': the king unpicked out of his oath",
      description="The repeated oath table framed tight, throne on the left third, one cold candle key at 12 deg, Act II grade: the king has just been unpicked, leaving a king-shaped void of bare linen pricked with needle holes and red-brown underdrawing on the still-stitched throne, a few purple strands still curling off the cloth; the gold crown hangs alone 10 mm above the void with its soft shadow; the four lords' gazes converge on it; the goblets are only needle-hole outlines."),
 dict(frame=899, shot="S12", title="'years': soldiers risen out of the cloth, frozen while a century passes",
      description="A 22-deg oblique over the war strip with a 3-deg dutch: blue and crimson figure slips stood up to ~70 deg out of the cloth on snapped thread tethers, felt edges lit, frozen mid-strike; long shadows thrown up-frame by firelight grazing from the bottom edge; the linen under and around them half-way through the hundred-year ageing (bleaching dyes, foxing, a tideline), the gold chronicle thread in the upper border tarnishing."),
 dict(frame=1319, shot="S18", title="'edges': the chronicle fraying into darkness",
      description="After the bass-entry pull-back: the chronicle is a thin strip on a dark walnut table, both ends lost in darkness; borders unravelling into curling fringe, weft threads hanging, quilted fog appliques rolling in over it; the ember glow gone; light falling to -2.5 EV at the frame edges; one tiny gold glint at the far right end: the chronicle thread, unbroken."),
 dict(frame=1760, shot="S24", title="Climax peak: the cloth has become the board",
      description="The menu camera reached: the 3D embroidered hex board (padded satin fields, couched gold realm borders, denim sea with stitched waves) with towns, forests and figure groups risen out of the cloth, the last tethers releasing, Grandbois under its banner; a warm 3200 K sweep mid-frame flashing the satin blocks; the blank lectern leaf square to camera on the left with the walnut reading frame closing round it; the walnut beam in place, the navy valance half unrolled with its letters only underdrawn; banners swinging in at the top corners, both candles burning at the sides, the carved lions rising into the lower corners."),
 dict(frame=1983, shot="S26", title="Final frame: the pixel-matched hand-off",
      description="Identical to frames 1929-1982: the live main menu's first frame minus the card's contents. Real game board, walnut bar, gold-stitched 'Chronica' valance at (784,0,992x296), blue- and red-lion banners, both candles, carved lions and the blank parchment card at (224,319)-(1227,1376), ready for the overlay hold and the 0.9 s dissolve that writes the page."),
]

POC = dict(
 title="The Cloth Becomes the Board (v1)",
 frames=[1689, 1830], duration_s=round(142 / FPS, 3),
 audio_slice_s=[round(1689 / FPS, 3), round(1831 / FPS, 3)],
 summary=("142 real production frames (f1689-1830, 4.73 s) played against the real audio ('When this age is remembered' + the "
          "climax gap + 'what will the chronicles...'). It proves the film's hardest claim and its hand-off in one window: a "
          "face-on, physically embroidered 2D cloth becomes a believable 3D game board, a blank leaf stays square to the lens for a "
          "visible physical reason, the chronicler's furniture assembles through the camera's own motion, and everything lands "
          "pixel-exact on the live menu before the title starts."),
 beats=[
  "f1689-1711 (2D, R25-S): locked zero-tilt pose; the gold thread runs from the leaf's corner and embroiders the board along the hex underdrawing: couched gold realm borders (tie-downs every 2-3 mm, needle glint at the tip), satin hex fields filling in a per-hex wavefront, denim sea with stitched wave marks, plan-icon towns; a 4300 -> 3200 K raking key moves; the right candle pool blooms on 'age' f1707.",
  "f1712-1725 (the swap): 14-frame registered cross from the R25 comp to the zero-tilt Eevee render of the same board (identical albedo + baked stitch normals). Must be invisible.",
  "f1726-1766 (3D, E4 hero): crane 0 -> 24 deg about the menu camera's target onto the exact menu camera (fov 30, pitch 66.09, distance 20.9); fields swell 1-2 mm as padded coupons with seam pinch; forests rise as stitched cones; towns and figure groups extrude out of their stitched footprints on twos with tethers, contact shadows and needle-hole footprints; the leaf hinges up on its tacked bottom edge by exactly the crane angle (lectern) with a widening contact shadow; warm sweep L->R peaking f1760; chrome flats enter by camera-track homographies; valance unrolls f1755-1782.",
  "f1767-1798 (convergence): board albedo blended into the projection of the 2x UI-free plate from f1756 (masked where pieces settle), then a cross-dissolve to the native-capture board f1772-1798 in which nameplates and unit shields settle in.",
  "f1799-1830 (locked COMP): the real board under exact chrome; 'Chronica' couching begins on 'chronicles' (C-h-r-o-n-i by f1822 at ~4 frames per letter).",
 ],
 technique=("Blender 4.0.2 Eevee-legacy under xvfb (bpy 5.2.2 Eevee-Next via EGL as fallback), 2560x1440, 16 TAA, camera on ones, rising "
            "pieces on twos. Board proxy = subdivided plane with per-hex puff shape keys (dome + seam pinch) on staggered drivers + the "
            "decoded game OBJs at their seed-4242 world positions with a piece material port (palette albedo, triplanar stitch normal, "
            "brown inverted-hull outline). Ground albedo/normal = R25 board maps in plate-UV space, projected from an overscanned top-down "
            "UI-free plate (zero-tilt framing) and from the menu-camera UI-free plate (final framing); a pieces-hidden plate fills the "
            "ground under rising pieces, and rising pieces keep OBJ + stitch materials until convergence (no projection smear). Leaf = "
            "separate holdout layer + shadow catcher, rendered at its 16:9 and 4:3 positions. Tethers = bevelled curves. Chrome = flats "
            "matted from the native capture at true depth, driven by the exported camera track. COMP adds fuzz halo, grain and grade."),
 inputs=[
  "UI-free demo-mode plate from the menu camera (seed 4242, small map, zoom 11, first tour focus) at 2560x1440 and 2x (5120x2880).",
  "The same plate with towns/units hidden (ground under rising pieces).",
  "An overscanned top-down UI-free plate covering the zero-tilt footprint (the menu footprint is a trapezoid, so the bottom corners of a face-on frame are otherwise missing). Fallback: extend the board procedurally with R25 kit hexes matched per terrain class.",
  "Native 2560x1440 capture of the live menu's first frame (chrome mattes, nameplates/shields, card interior to inpaint, final match) plus one 4:3 capture (keep_height check).",
  "Hex size/orientation and world positions of hexes, settlements and unit groups for seed 4242 (from the game's map and camera code; fallback: solve from the plate with the known camera).",
  "models/*.obj + game_palette.json, the R25 emb/ library (stitch, strands, fibres, shade), palette.json acts IV-V.",
 ],
 acceptance=[
  "Swap f1712-1725: median dE_ok x100 < 2 and no edge shift > 1 px between the R25 comp and the zero-tilt Eevee render.",
  "End match f1798: Eevee vs UI-free plate median dE_ok x100 < 3, town silhouettes within 1 px; after the dissolve, mean abs diff vs the native capture < 2/255 outside flames and card interior.",
  "Leaf: corner positions deviate <= 1 px from a pure screen-space similarity transform on every frame f1726-1766 (it stays square), and land on the card rect +/-0.5 px.",
  "Chrome flats land on their menu_layout rects +/-0.5 px; their entrance is driven only by the camera track.",
  "Stitch scale continuity: same px/mm across the swap; no shimmer during the tilt (registered high-frequency residual vs a resample-only baseline below threshold).",
  "Materials: wool specular <= 0.06, no white hotspots, metal glint only on couched gold and < 3 % of pixels.",
  "Every rising piece shows tethers + contact shadow + needle-hole footprint for >= 6 frames, so it reads as coming OUT of the cloth.",
  "Zero void/background pixels on every frame (automated check); the same tests pass on the 1920x1080 downscale that ships.",
 ],
 cost=("87 Eevee hero frames (f1712-1798) + 2 stills at 2560x1440 16 TAA, re-estimated at ~90-100 s each for the full geometry-heavy "
       "board = ~2.3 h on one process, ~1.9 h with two; + 23 R25 stitch-on frames (~3 CPU-min) + 32 COMP frames. All are production "
       "frames of S23-S25, so the PoC spends budget the film needs anyway."),
 fallback=("If world positions cannot be recovered: plate-only 2.5D lift, using the known board-plane homography, towns hand-masked "
           "and raised by height-from-ground displacement with synthesised side walls (less parallax, same hand-off). If the leaf "
           "lectern fails its squareness test, the leaf becomes a separate 2D layer that lifts off the cloth (scale 1.000 -> 1.015, "
           "widening soft shadow) and slides in the screen plane from its zero-tilt rect to the card rect while the board tilts behind it."),
 deliverables=["poc_cloth_to_board_1440.mp4 muxed with audio 56.300-61.033 s", "contact sheet f1689/1711/1726/1744/1760/1798/1830",
               "A/B stills at f1712 (R25 vs Eevee) and f1798 (Eevee vs plate) with difference images", "acceptance report (json)"],
)

GOLD_THREAD = [
 ("S01", "f5-39", "drawn up through the linen by the needle on 'There', taut on 'world', pinned by the first crimson tie-down", "L2"),
 ("S06", "f350-400", "runs on and on out of frame: 'never end'", "L1"),
 ("S12", "f899-918", "tarnishes #E9BE6A -> #7A5A2A in the hundred-year time-lapse", "-"),
 ("S18", "f1336-1381", "one surviving glint at the far right end of the darkened strip; pulses on bass f1345", "L2"),
 ("S19", "f1466-1480", "re-couched end to end on 'whole'", "L3 flare 2"),
 ("S22", "f1599-1630", "runs down from the border and couches a frame round the blank leaf", "L2"),
 ("S23", "f1689-1726", "runs on from the leaf's corner and couches the board's realm borders; pulls its couching out of the leaf so it can lift", "L2"),
 ("S24", "f1744-1772", "the realm borders it couched glint in sequence under the climax sweep", "L2"),
 ("S25", "f1787-1846", "climbs into the valance and couches C-h-r-o-n-i-c-a, then crown and fleurs-de-lis", "L2 needle glint"),
 ("S26", "f1862-1904", "one sheen along the finished title, then rest", "L3 flare 3"),
]

LIGHT_EDITOR = [
 ("f0-3", "black #07070A", "digital silence"),
 ("f4", "one 1900 K candle finds the linen (elev 8 deg)", "drone + 'There'"),
 ("f40-125", "warms to 3000 K, climbs to 22 deg", "litany begins"),
 ("f134-146", "the two stitched table candles light; warm pools bloom", "'table'"),
 ("f402-445", "key cools and sinks to 1900 K at 12 deg (-0.7 EV)", "gap after 'never end'"),
 ("f465-471", "a stitched candle on p3 is unpicked; its light leaves the cloth (-0.5 EV)", "'died'; the drone exits after (f480-548)"),
 ("f717-784", "the single candle key swings R->L; the crown's shadow travels", "'his own head beneath'"),
 ("f797-812", "the last candle dies with the music (-4 EV)", "-20 dB collapse f797"),
 ("f832-843", "an ember glow rises from the bottom edge", "near-silence"),
 ("f844-1050", "firelight grazing from the bottom edge (2200 K, 2-6 Hz)", "the war; fire peak in S14"),
 ("f1051-1282", "sinks to an ember glow; cool dusk fill rises", "M4 plateau"),
 ("f1292", "the embers die", "'dark'"),
 ("f1345", "the surviving gold glint pulses (the only light event of the gap)", "bass pulse #2"),
 ("f1372-1381", "pre-dawn lift: cool grey-blue fill from the left +0.3 EV", "in-gap swell into 'Now'"),
 ("f1382-1470", "dawn sweep L->R (4300 K, elev 28 deg)", "'Now'"),
 ("f1664", "left candle relit: a warm pool blooms from off-frame left", "bass pulse"),
 ("f1707", "right candle relit: a second pool from off-frame right", "'age'"),
 ("f1744-1772", "warm 3200 K sweep across the board, peak f1760", "climax"),
 ("f1772-1798", "the board takes the game plate's daylight; candle pools fade to the sprites' own glow", "recession begins"),
 ("f1862-1904", "title sheen (flare 3)", "ring-out"),
 ("f1929-1983", "locked, identical frames", "ring-out tail"),
]

COLOUR_SCRIPT = [
 dict(act="I Oath", frames="f0-445", seconds="0.00-14.87", shots="S01-S06",
      key="3000 K raking, elev 22 deg (8 deg at f4 rising), key:fill 3:1; practicals: stitched table candles 1900 K (pools)",
      dominant="linen #D4BE98, gold #E9BE6A, terracotta #B65E43",
      accents="crimson #CC3A2C, royal blue #3F72BE, green #3A8C63, builders ochre #CB7A1C; royal purple #71508A (king only)",
      grade="sat 1.0, chroma cap .17, lift #100C08, gain #FFF4E2",
      events="f230 metal flare 1 (crown); f402-445 cools to 1900 K"),
 dict(act="II Death", frames="f446-843", seconds="14.87-28.13", shots="S07-S11",
      key="single candle 1900 K, elev 12 deg, key:fill 6:1",
      dominant="night #141325, royal purple #4E2F5E, linen_lo #B49C74",
      accents="gold only (the crown); ink red-brown #6E3326 for underdrawing",
      grade="sat 0.7, chroma cap .12, lift #08080E, gamma .95, gain #FFE9CF",
      events="f469 flame unpicked (-0.5 EV); f797-812 candle dies (-4 EV, floor #07070A, fill #141325 at 10 %)"),
 dict(act="III War", frames="f844-1381", seconds="28.13-46.07", shots="S12-S18",
      key="2200 K firelight grazing from the bottom edge, flicker 2-6 Hz at 15-25 %, key:fill 5:1; 2-3 deg dutch in S12-S14",
      dominant="dusk sky #6A3A38, crimson deep #56100E, smoke #4A4547, forest #34432F",
      accents="fire #F6B54A / #DE6A2C, crimson hi; realm cords gold/crimson/blue/green in S16",
      grade="sat .85, chroma cap .19, lift #0B0607, gamma .92, gain #FFE2C4; edges to -2.5 EV by f1319",
      events="f899-918 hundred-year ageing; f982-1050 fire peak; f1292 embers die; f1345 glint pulse; f1372 pre-dawn lift"),
 dict(act="IV Renewal", frames="f1382-1688", seconds="46.07-56.30", shots="S19-S22",
      key="4300 K dawn from the left, elev 28 deg, key:fill 2.5:1, sweep L->R f1382-1470",
      dominant="linen hi #E6D7B6, linen #D4BE98",
      accents="navy #15223A, gold #D79A33, woad #4F6F8A; crests at game chroma (heraldic register)",
      grade="sat .9, chroma cap .15, lift #0E0C0A, gamma 1.05, gain #FFF8EC; dyes aged -> fresh (OKLab, 1.5-3 s, staggered)",
      events="f1466 metal flare 2 (thread re-couched); f1664 left candle pool"),
 dict(act="V Question", frames="f1689-1983", seconds="56.30-66.13", shots="S23-S26",
      key="3200 K raking, elev 20 deg, key:fill 4:1, converging by f1798 on the game plate's own daylight",
      dominant="navy #15223A / navy deep #080D17 (valance), game board colours (denim sea #316994, satin fields)",
      accents="gold #F8D57C / #D79A33, metal gold #E9BE6A",
      grade="sat 1.0, chroma cap .17, lift #05070C, gain #FFF2DC; from f1798 no grade on the plate (must equal the live menu)",
      events="f1707 right candle pool; f1744-1772 warm sweep; f1862-1904 metal flare 3 (title); f1929 lock"),
]

METAL_BUDGET = dict(
 L3_flares=["f224-236 crown ('crown' f230)", "f1466-1480 chronicle thread re-couched ('whole')", "f1862-1904 title sheen (peak ~f1883)"],
 L2_glints=["f5-39 thread on its twist", "f760-784 small crown glint migrating with the key", "f1345 surviving glint pulse",
            "f1600-1628 page-frame couching", "f1689-1726 board border couching", "f1744-1772 borders under the climax sweep",
            "f1787-1846 needle glint writing the title"],
 L1_rule="Everything else (sword, goblets, pole, cords) reads by light pools, sheen and contact shadows: no travelling metal glint.",
 levels="L3 = metal reaches #FFF3D6 for 1-3 frames; L2 = capped at gold_hi #F8D57C, <= 1 % of pixels; L1 = wool/silk sheen only.",
)

RENDER_BUDGET = [
 dict(block="E0 macro rig (needle, thread, crown rip)", shots="S01, S11", frames="f4-75, f785-812 + 2 stills",
      renders_1080=102, renders_1440=0, settings="1920x1080, 16 TAA, on ones, ~1M-vert displaced linen, real DOF + motion blur",
      wall="~65 s/frame = ~111 min single"),
 dict(block="E1 war slips", shots="S12-S13", frames="f844-871 ones, f872-916 twos, f918-943 ones",
      renders_1080=77, renders_1440=0, settings="1920x1080, 16 TAA macro / 8 TAA wide; ageing done in COMP via UV + ratio passes",
      wall="28 x ~65 s + 49 x ~15 s = ~42 min"),
 dict(block="E3 banner + village", shots="S20-S22", frames="f1524-1612",
      renders_1080=89, renders_1440=0, settings="1920x1080, 16 TAA, camera on ones, pieces on twos",
      wall="~25 s/frame = ~37 min"),
 dict(block="E4 board awakening (hero)", shots="S22-S25", frames="zero-tilt still + f1712-1798 + 32-TAA registration still",
      renders_1080=0, renders_1440=89, settings="2560x1440, 16 TAA, on ones (pieces on twos), geometry-heavy",
      wall="~90-100 s/frame = ~141 min single (~1.9 h on 2 procs)"),
 dict(block="E4L 4:3 leaf layer (deliverable for iPad)", shots="S23-S25", frames="f1712-1798",
      renders_1080=0, renders_1440=0, settings="leaf holdout + shadow catcher only at the base_4x3 position, ~10 s each (87 light layer renders, not counted against the hero budget)",
      wall="~15 min"),
]

GATES = [
 ("G1 Bayeux kit proof", "Build one reusable Bayeux kit (hillocks, interlace trees, borders with vignette beasts, towns from settle_* elevations, couched bars, roads, underdrawing). Prove S02 side by side with p1 at matched px/mm and identical relight before building any other procedural section; shorten sections with divider splices.", "S02, S08, S12, S15, S16, S19-S22"),
 ("G2 Metal reads as metal", "Add a prefiltered warm studio-gradient environment term and a wider anisotropic glint to R25's metal lobe; verify crown, thread and title at >= 3 key azimuths.", "S01, S04, S19, S22-S26"),
 ("G3 Fuzz calibration", "Cut halo/flyaway density on couched cords (no chenille), tint flyaways toward the parent thread and attenuate them over dark fills (no white scratches), add a cheap fibre self-shadow term.", "all R25 shots"),
 ("G4 No void pixels", "Pad every canvas beyond the frustum; automated per-frame check fails on any void or background pixel.", "all"),
 ("G5 Lift policy", "R25-L only for frontal lifts (camera <= 5-10 deg off the cloth normal, lift <= 15 mm) with PCSS penumbra growing with lift and contact AO. Every hinged or oblique rise goes to Eevee with displaced R25 maps (low-pass geometry + high-pass normal).", "S05, S09-S10 (R25-L); S12-S13, S20-S25 (Eevee)"),
 ("G6 Fill directions", "Phase-field (phi/psi) stitch layout where the structure tensor is incoherent (throne carving, ermine, horse bodies): no fingerprint whorls or brick lattices.", "p1, p3, p6, slips"),
 ("G7 LOD and shimmer", "LOD-fade weave and strand normals below 2.5 px; run the registered high-frequency shimmer metric on every shot, and test an F0 framing with a 12 px/frame truck at 1440p before committing the trucks.", "S02-S08, S15-S19"),
 ("G8 Stitch-on order", "Needle-path ordering by spatial adjacency, per-strand growth along its length with a pop-in height curve and a needle glint at the tip; dirty-rect recompute of normals/AO/fibres so panel-scale and logo builds stay fast.", "S15, S16, S22, S23, S25"),
 ("G9 Unpick path", "Snapshot re-rasters every N stitches, needle-hole + underdrawing reveal, loose-end curls from the fibre/curve renderer; addressable weft at fray edges.", "S07, S09, S13, S16-S18"),
 ("G10 Panel bakes", "Tiled re-embroidery of p1/p3/p6 at 10 px/mm, <= 2 GB per process, float16 caches; art-directed masks (~15 min/panel) for crown fleurs-de-lis, chain, collar and face likeness.", "S03-S11, S14"),
 ("G11 Light and colour wiring", "Act tints, candle/fire/dawn practicals as intensity curves in the relight; satin chroma under the act cap; Legion livery in game crimson with a couched-gold cross shield.", "all"),
 ("G12 Hand-off match", "f1983 vs the live menu's first frame: mean abs diff < 2/255 outside text, flames and card interior; no sprite offset > 0.5 px; verified at 2560x1440 and at the shipped 1920x1080.", "S24-S26"),
]

MERGE_MUST_FIX = [
 ("S24 of the frieze draft overcrowded under the key line", "All chrome now enters in S24 (climax) through the crane's own camera track; the candles are relit as light on f1664/f1707; S25 carries only the 'Chronica' couching, the leaf's last settle and decaying sway; the plate dissolve ends f1798, before 'chronicles'."),
 ("Frieze S12 overpacked", "War spread over S12-S13 (138 frames): one generation, one rise, one clash, a frozen hundred years, a slow topple and one mass unpick on 'nothing' f942. No second generation; slow, sparse action in the near-silence."),
 ("S17 candlelight dying on 'dark'", "Act II's last candle dies at f797 (S11); in Act III the firelight sinks to embers, and the embers die on 'dark' f1292 (S18)."),
 ("Near-black hold while the music rises (f1336-1381)", "The surviving gold glint pulses on bass f1345 and a pre-dawn lift starts at f1372 (S18)."),
 ("Eight tituli", "One titulus only: SINE HEREDE (S08). The only other stitched word in the film is 'Chronica'."),
 ("Glints and sweeps on every beat", "Metal budget: three L3 flares (crown f230, 'whole' f1466, title f1862-1904); L2 glints listed and capped; sword, goblets and pole read by light, not glints."),
 ("Monotony of face-on trucking", "Grammar varied: macro in S01, S11, S12; locked frames in the silences (S11, S13, S17, S22); push-ins on emotional beats (S04, S09); the war's oblique; the bass pull-back; the crane. Trucks remain only where the strip must be read (S02-S03, S06-S08, S15-S16, S19-S21)."),
 ("p1 repeated", "The second copy differs at first glance (1.15x, throne on the left third, Act II re-dye, candles dark, goblets reduced to needle holes) and is an event: the king is unpicked live (S09)."),
 ("Page square to the lens without a reason", "The leaf is a separate piece of cloth tacked in by the gold couching; on 'remembered' the couching is pulled out and it hinges up on its bottom edge by exactly the crane angle, with its own widening contact shadow, so it stays square: a reader's lectern (S23)."),
 ("f1760 vs tilt completion", "Crane within 0.3 deg of the menu camera by f1760 and exact at f1766; all pieces settled by f1760; the Eevee -> plate dissolve ends f1798."),
 ("Title pacing", "'Chronica' couched on 'chronicles' f1787-1822 at ~4 frames per letter, ornaments f1824-1846, last stitch on 'you?'."),
 ("Pull-back before the bass (f1240)", "S16-S17 hold (1 px/frame); the exponential pull-back launches on f1283 with a 6-frame ease-in, cruising by 'dark' f1292."),
 ("Trapezoid footprint at zero tilt", "PoC input: overscanned top-down UI-free plate, or a procedural R25 board extension; S20-S22 are framed on the exact E4 zero-tilt pose."),
 ("Projection smear under rising pieces", "Pieces-hidden plate for the ground; rising pieces keep OBJ + stitch materials until the convergence f1756-1798."),
 ("4.5 m of procedural art", "Gate G1 (one kit, S02 proved against p1 first) and divider splices; the war strip is war_bg re-embroidered, not new art."),
 ("E4 cost", "Re-estimated at 90-100 s/frame: 89 hero renders = ~2.3 h single, ~1.9 h on 2 processes, inside the 150-frame hero limit."),
 ("S01 pull-back speed", "Real Eevee macro with real motion blur; centre < 8 px/frame; edges blurred; total pull 8x over 70 frames."),
 ("Audio tail", "Recommend a 0.5 s gain ramp on the mix tail (f1968-1983) to hide the -48 dBFS cut-off during the poster hold."),
 ("Final plate missing nameplates/shields", "f1855-1983 are built from a native 2560x1440 full-menu capture with only the card interior inpainted; nameplates and shields settle in during the f1772-1798 dissolve; verified at 1920x1080 too."),
 ("Candles flickering to the end", "Flames settle to exactly the sprite art and every animated layer is zero from f1929; f1929-1983 identical."),
 ("Card screen-aligned vs a 66-deg camera", "Solved by the lectern: the leaf's plane is always parallel to the image plane."),
 ("Burn-through reveals a pristine layer", "The burn reveals the dark walnut beneath (the splice); the scorch and soot persist as ageing into S15-S18."),
 ("Hearth light through the weave", "Firelight is a low grazing key from the bottom edge of frame."),
 ("Four goblets, not five", "Four goblets everywhere."),
 ("R25 material must-fixes", "Gates G2-G11 (metal environment term, fuzz, void, lift artefacts, whorls, LOD/shimmer, stitch-on order and cost, unpick, panel bakes, colour/practicals)."),
]

MERGE_GRAFTS = [
 ("table", "Practical light as the editor: the light that follows the score (flame unpicked on 'died', the last candle dying on the f797 collapse, firelight in the near-silence, dawn on 'Now', candles relit on f1664 and f1707)."),
 ("table", "On 'borders' one road becomes four realm cords in the game's border idiom, with the game's quilted fog-of-war kit over the forgotten land (S16), peeled back by the dawn (S19)."),
 ("table", "The king unpicked live during 'and every lord...', crown left hanging (S09); ghost underdrawn crowns, layered with the frieze's sliding crown shadow (S10)."),
 ("table", "The stitched fire scorching the real linen ('consumed by what it depicts', S14); capitonnage as the board's swelling mechanism (S23-S24); drypoint ruling on the blank page on 'page' and 'you?'; poster-frame advice and the f1983 difference test."),
 ("scale", "The needle drawing the gold thread up through the linen on 'There' f5 (S01) and the crown's gold ripped out exactly on the f797-798 collapse (S11), on one shared Eevee macro rig."),
 ("scale", "'Scale follows the music' as a rule: macro on the quietest passages (S01, S11, S12 open, S13 gap), no fast moves under the near-silent war, the decisive gestures on the bass entry and the climax."),
 ("scale", "A blank world as well as a blank page: the hex underdrawing running unstitched to the end of the roll (S20-S22); the 0.5 s audio-tail ramp; 55 identical final frames."),
 ("table/scale", "The war opened in macro between the linen threads lit from below, rising over a thread onto the war strip (S12)."),
 ("bake-off", "Displaced-mesh Eevee from R25 maps for every 3D insert; stand-up figure slips (~70 deg) with tethers snapping one by one; fold/drape field; metal environment term; needle glint at the growing tip; embroidery-in-progress frontier with underdrawing; couched-gold-over-padding crests; Legion crimson livery; protected unfaded linen under lifted pieces; risen banner sway at the 2.115 s pulse."),
]

MERGE_REJECTED = [
 "Scale's eye-level miniature glide, dolly-zoom dive and tilt-shift miniature DOF (cliche risk, breaks the 25-deg rule, heaviest 3D).",
 "Scale's climax inside a Blender-to-Godot cross-match and demo-mode zoom animation (unverified).",
 "Table's menu chrome visible from frame 4 (spoils the final reveal).",
 "Table's 12-frame title stitch, its 60 px/frame hidden truck and its soldier-height tracking shot.",
 "Card dropping in from above the lens as a UI panel (literal; replaced by the thread-framed leaf).",
 "Linen cross-fading into parchment (the leaf carries the parchment albedo from its first frame).",
]

FRIEZE_LAYOUT = [
 ("1", "Incipit + one realm", "~800", "hem, nail holes, the gold chronicle thread and its first tie-down; Bayeux landscape from the kit; four towns from settle_* elevations; the four-colour road; lion border beasts from vignette_red/blue", "S01-S02"),
 ("2", "T1 interlace tree", "~60", "trunk banded in the four house colours (splice)", "S02"),
 ("3", "p1 OATH", "550", "p1_oath re-embroidered by R25 at 10 px/mm", "S03-S06"),
 ("4", "T2 night tree", "~60", "dark woad bands (splice)", "S06"),
 ("5", "p3 DEATH", "550", "p3_death re-embroidered; flame unpick", "S07"),
 ("6", "SINE HEREDE strip", "~150", "underdrawn heir between two couched bars; the only titulus", "S08"),
 ("7", "T3 winter tree", "~60", "leafless, blue-black (splice)", "S08"),
 ("8", "p1' THE EMPTY CHAIR", "550", "the p1 maps again: Act II re-dye, goblets reduced to needle holes, king unpicked live, crown slip", "S09-S10"),
 ("-", "(dark splice f820)", "-", "hidden in the near-silence after the crown macro", "S11"),
 ("9", "WAR strip -> hole field", "~800", "war_bg re-embroidered + figure slips; aged by the time-lapse; needle-hole field", "S12-S13"),
 ("-", "(burnt hole, dark splice f988-997)", "-", "burns through to the walnut table", "S14"),
 ("10", "p6 RUIN", "550", "p6_ruin re-embroidered; scorched margins", "S14"),
 ("11", "charred tree + FOREST over the road", "~700", "kit trees over the S02 road (rhyme)", "S14-S15"),
 ("12", "FOUR TOWNS / borders", "~780", "four towns, couched bars, four realm cords, fog quilts", "S16-S17"),
 ("13", "RENEWAL end", "~600", "the four crests in the upper border; mended edges", "S19"),
 ("14", "UNWRITTEN REMAINDER", "open", "fresh linen with ink hex underdrawing = the seed-4242 board layout; banner, village, the leaf", "S20-S26"),
]

SYNC_MAP = [
 ("0-3", "digital silence", "black"),
 ("4-5", "drone + 'There' (strongest attack)", "candle finds the linen; the needle breaks through"),
 ("39", "'world'", "thread taut; first tie-down; pull-back begins f40"),
 ("91", "'realm'", "the one realm revealed (pull-back easing out)"),
 ("104-125", "gap", "the landscape breathes"),
 ("140", "'table'", "stitched candles lit (f134-146), pools bloom"),
 ("173", "'oath'", "pools steady on the hands on the sword"),
 ("185-198", "near-silence", "hold"),
 ("230", "'crown'", "METAL FLARE 1 (f224-236)"),
 ("285 / 308", "'raised' / 'cups'", "goblets rise (f283-292) / hang high"),
 ("349", "'swore'", "goblets settle; camera releases right"),
 ("391", "'end'", "the gold thread runs on out of frame"),
 ("402-446", "1.46 s gap", "light cools; T2 splice"),
 ("469", "'died'", "stitched flame unpicked (f465-471), -0.5 EV; drone exits after"),
 ("522 / 548", "'heir' / drone gone", "underdrawn heir, SINE HEREDE"),
 ("561-640", "'and every lord ... table'", "the king unpicked live"),
 ("669", "'chair'", "push lands on the king-shaped void"),
 ("741 / 753 / 766 / 778", "'own' / 'head' / 'beneath' / -", "crown shadow and ghost crown on each lord"),
 ("785", "'crown.'", "HARD CUT to the crown macro"),
 ("797-798", "music collapses -20 dB", "the crown's gold whips out of frame; the candle dies"),
 ("832", "near-silence", "ember glow rises"),
 ("850", "'wars'", "macro glide; rise over a thread begins f856"),
 ("867-884", "'lasted' ... 'hundred'", "slips stand up, tethers snap; one clash f884"),
 ("899", "'years'", "hundred-year time-lapse on the cloth"),
 ("942", "'nothing'", "every figure unpicked at once"),
 ("952-979", "near-silent gap", "needle-hole field, grazing light, locked"),
 ("982 / 999 / 1015", "'Cities' / 'fell' / 'ruin'", "burn-through / towers drop / banner slumps"),
 ("1017", "pad returns", "flames quicken and scorch the real linen"),
 ("1051 / 1101", "'Roads' / 'forest'", "trees stitch over the road / road gone"),
 ("1149 / 1211", "'forgot' / 'borders'", "bars wall the strip / last realm cord closes"),
 ("1263-1282", "'world grew'", "held breath; nothing launches"),
 ("1283", "BASS ENTRY (+26 dB)", "exponential pull-back launches"),
 ("1292 / 1319", "'dark' / 'edges'", "embers die / fraying reaches the register, -2.5 EV"),
 ("1345", "bass pulse #2", "surviving gold glint pulses"),
 ("1372", "in-gap swell", "pre-dawn lift"),
 ("1382", "'Now'", "dawn sweep L->R begins"),
 ("1410", "bass pulse ('ruler')", "fourth crest lands"),
 ("1466 / 1471", "'whole' / bass", "METAL FLARE 2: thread re-couched end to end"),
 ("1491-1523", "Bb horn gap", "arrival at the strip's end in full dawn"),
 ("1536", "bass pulse ('banner')", "banner rises (stitches tauten from f1527)"),
 ("1569", "'village'", "village rises (f1563-1575)"),
 ("1599", "bass pulse ('one')", "the thread starts framing the leaf"),
 ("1630", "'page'", "frame closes; drypoint ruling catches the light"),
 ("1664", "bass pulse", "left candle relit (pool)"),
 ("1707", "'age'", "right candle relit (pool)"),
 ("1712-1725", "-", "registered 2D -> 3D swap"),
 ("1726", "bass pulse ('remembered')", "leaf lifts as a lectern; crane starts; pieces start rising"),
 ("1755", "bass swell", "valance starts to unroll"),
 ("1760", "CLIMAX PEAK", "board risen at the menu camera; sweep mid-frame"),
 ("1766", "-", "crane exact on the menu camera"),
 ("1798", "-", "plate dissolve complete (before 'chronicles')"),
 ("1801", "'chronicles'", "'Chronica' couched f1787-1822"),
 ("1846", "'you?'", "last stitch pulled tight; ruling catches the light; leaf settled"),
 ("1862-1904", "ring-out", "METAL FLARE 3: title sheen"),
 ("1929-1983", "ring-out tail, micro-fade f1982", "identical locked frames = live menu minus card text"),
]

HANDOFF = [
 "Final rects (2560x1440, menu_layout.json px_2560x1440): bar_top (0,0,2560x128); logo_title_banner (784,0,992x296.3); menu_card (224,318.7,1003.2x1057.6), parchment interior (272,357.3,910.7x976); banner_side_left (16,64,129.2x345.6); banner_side_right (2421.1,64,122.9x345.6); candle_left (9.6,686.9,92x331.2); candle_right (2452.9,686.9,97.5x331.2); lion_statue_left (6.4,1163.2,189.9x273.6); lion_statue_right (2362.1,1163.2,191.5x273.6).",
 "Final plate: a native 2560x1440 capture of the live menu's first frame (the existing 2560 images are an upscale or a later tour stop). Only the card interior (title, subtitle, divider, buttons, footer) is inpainted from the 9-slice parchment; the valance letters are inpainted only for the S24-S25 stitch-on layer. Nameplates, stars and unit shields stay as captured.",
 "Board: the menu tour holds 3 s on the first focus before panning, so the CSS dissolve lands on a still board identical to the plate.",
 "Lock: every animated layer (flames, sheen, sway) reaches zero by f1929; f1929-1983 are identical. The overlay holds f1983 for as long as engine.start() blocks, with its gold progress thread at the bottom 7 %, so f1983 must be a clean poster (no blur, calm board at bottom centre).",
 "Blank card: no rows are pre-ruled for buttons (their count depends on saved games); only the drypoint title line and one rule, faint enough to sit under the live title.",
 "Acceptance (gate G12): difference image of f1983 against the live menu's first frame: mean abs diff < 2/255 outside text, candle flames and card interior; no sprite offset > 0.5 px; repeated on the 1920x1080 encode that ships (intro_1080).",
 "iPad 4:3: object-fit:cover shows x 320-2240 of the 16:9 master, while the live 4:3 menu uses base_4x3 (card at 140-767 of 1600, larger banners, candles and lions, table_edge_bottom visible). Deliver a 1920x1440 4:3 master: f0-1598 is the central crop (every composition is staged inside x 320-2240); f1599-1983 is re-composited with the leaf, card frame and chrome at base_4x3 rects x1.2, using the E4L leaf layer. If Godot keeps the vertical FOV (keep_height), the 4:3 board is a central crop of the 16:9 board; verify with one 4:3 demo plate. The overlay would choose the file by aspect (integrator suggestion only; the repo is not touched).",
 "Poster: intro/poster.jpg should be an early lit frame (f91, the realm), not black frame 0; the 'Touch to begin' text (#7a2a22 at top 72 %) needs a lighter colour (e.g. #E6D7B6) or a scrim on that frame. Suggestion only.",
 "Audio tail: the master stops at about -48 dBFS on f1983; recommend a 0.5 s gain ramp on the mix tail (f1968-1983) for the audio owner, so the poster hold never exposes an abrupt cut.",
]

RISKS = [
 ("Style seam between re-embroidered AI panels and procedural Bayeux sections", "One R25 renderer, one linen ground, continuous procedural borders over every section, shared fuzz/ageing; gate G1 proves S02 beside p1 first."),
 ("Board world positions for seed 4242 not recoverable", "Solve from the plate with the known camera; fallback plate-only 2.5D lift in the PoC."),
 ("Overscanned top-down plate not possible in demo mode", "Extend the board procedurally beyond the menu footprint with R25 kit hexes matched per terrain class."),
 ("Chrome flats read as cheap parallax", "They are flats by nature (cut-outs of a proscenium/desk), placed at true depth, moved only by the real camera track, enter under motion blur within ~30 frames of the climax, and land exactly."),
 ("Leaf lectern looks unmotivated", "Its couching is visibly pulled out by the running thread, its bottom edge stays tacked, and its contact shadow widens; fallback in the PoC section."),
 ("E4 overruns", "89 hero renders at ~95 s fit; if needed, pieces render on twos as a separate layer over a camera-on-ones board."),
 ("War slips at low resolution (288-640 px cards)", "Slips <= 1.5x native on screen, macro DOF and firelight; normal maps for relief."),
 ("Busy climax", "Everything in S24 is one gesture (the camera arriving); pieces finish rising by f1760, chrome lands by f1772, valance by f1782; S25 is nearly still."),
 ("Render contention on 4 shared cores", "357 Eevee renders (268 + 89), at most 2 concurrent Blender processes, test renders at 1280x720."),
]

DEPENDENCIES = [
 "Game plates (demo mode, SwiftShader ~20-40 s/frame): UI-free menu-camera plate at 2560x1440 and 2x; pieces-hidden variant; overscanned top-down plate; native full-menu capture (2560x1440, first frame); one 4:3 plate.",
 "Seed-4242 hex geometry and world positions of settlements and unit groups.",
 "menu_card 9-slice margins (ui_theme.gd) for the parchment inpaint.",
 "Exported Blender camera track (E4) to drive the chrome homographies.",
 "R25 batch pre-bake of all 11 units x idle/strike x 4 realm tints; tiled bakes of p1/p3/p6.",
]

# ------------------------------------------------------------------ JSON
def shot_json(s):
    return dict(id=s["id"], name=s["name"], act=s["act"], start_frame=s["start"], end_frame=s["end"],
                start_s=s["start_s"], end_s=s["end_s"], frames=s["frames"], anchor=s["anchor"], summary=s["summary"],
                audio_event=s["audio_event"], visual_action=s["visual_action"], camera=s["camera"],
                technique=s["technique"], material_behavior=s["material_behavior"], transition_out=s["transition_out"],
                emotional_purpose=s["emotional_purpose"], est_render_cost=s["est_render_cost"],
                eevee=dict(block=s["eevee"]["block"], renders_1080=s["eevee"]["r1080"], renders_1440=s["eevee"]["r1440"]))

doc = dict(
 title=TITLE, version="v1", base="frieze (judges' consensus winner) + grafts from table and scale + material bake-off winner relight25d",
 logline=LOGLINE,
 master=dict(width=2560, height=1440, fps=FPS, frames=LAST + 1, first_frame=0, last_frame=LAST,
             duration_s=round((LAST + 1) / FPS, 3), audio="aaa/audio/audio_master_1984f_s16.wav", frame_convention="frame = floor(t*30)"),
 technique_codes={"R25-F": "relight25d frontal relight from cached stitch maps (5 s/frame with a moving light, 1.26 s camera-only)",
                  "R25-S": "relight25d stitch-on / unpick (stitch_id order, dirty-rect recompute, snapshot re-rasters)",
                  "R25-L": "relight25d frontal slip lift (<= 5-10 deg off normal, PCSS shadow, tethers)",
                  "EV-DM": "Blender 4.0.2 Eevee render of a displaced mesh built from R25 maps (low-pass geometry + high-pass normal), fuzz in COMP",
                  "COMP": "numpy/cv2 compositor: transforms, chrome layers, grade, grain, fuzz (every frame)",
                  "GP": "game demo-mode plates and native captures"},
 coverage=dict(shots=len(SHOTS), frames_covered=TOTAL, contiguous=True, first=0, last=LAST),
 shots=[shot_json(s) for s in SHOTS],
 eevee_budget=dict(renders_1080=E1080, renders_1440_hero=E1440, total=E1080 + E1440,
                   limits=dict(renders_1080=600, renders_1440_hero=150),
                   optional_light_layers="87 E4L 4:3 leaf-layer renders (~10 s each)",
                   blocks=RENDER_BUDGET,
                   wall_estimate="~331 min single-process (~5.5 h), ~4.6 h with 2 concurrent processes; R25 ~2.3 CPU-h; COMP ~13 min; game plates ~15 min"),
 six_keyframes=SIX_KEYFRAMES,
 poc=POC,
 through_lines=dict(gold_thread=[dict(shot=a, frames=b, action=c, metal_level=d) for a, b, c, d in GOLD_THREAD],
                    metal_budget=METAL_BUDGET,
                    light_editor=[dict(frames=a, light=b, sound=c) for a, b, c in LIGHT_EDITOR]),
 colour_script=COLOUR_SCRIPT,
 frieze_layout=[dict(n=a, section=b, width_mm=c, content=d, shots=e) for a, b, c, d, e in FRIEZE_LAYOUT],
 sync_map=[dict(frame=a, sound=b, picture=c) for a, b, c in SYNC_MAP],
 gates=[dict(id=a, rule=b, shots=c) for a, b, c in GATES],
 handoff=HANDOFF,
 risks=[dict(risk=a, mitigation=b) for a, b in RISKS],
 dependencies=DEPENDENCIES,
 merge_log=dict(must_fix=[dict(item=a, fix=b) for a, b in MERGE_MUST_FIX],
                grafts=[dict(source=a, graft=b) for a, b in MERGE_GRAFTS],
                rejected=MERGE_REJECTED),
)

with open(OUT_JSON, "w") as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)

# ------------------------------------------------------------------ Markdown
def esc(t):
    return str(t).replace("|", "/")

def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(esc(c) for c in r) + " |")
    return "\n".join(out)

md = []
A = md.append
A(f"# {TITLE}\n")
A("Merged final storyboard. Base: the **frieze** draft (judges' consensus winner), with grafts from **table** and **scale**, every judge must-fix applied, "
  "and shots designed for the material bake-off winner, **relight25d** (R25). Master 2560x1440, 30 fps, frames 0-1983 (1984 frames, 66.133 s), muxed with "
  "`aaa/audio/audio_master_1984f_s16.wav`. Frame = floor(t x 30). Machine-readable twin: `storyboard_v1.json` (same data, generated by "
  "`story/work/gen_storyboard_v1.py`, which also checks that frames 0-1983 are covered exactly once).\n")
A(f"**Logline.** {LOGLINE}\n")
A("## 1. The film in one paragraph\n")
A("The film is one object: a long embroidered roll-chronicle lying on a walnut table under a rostrum camera, read left to right like the Bayeux Tapestry. "
  "Story time is carried by what happens to the cloth and to the light that falls on it. A needle draws the first gold thread; the one realm, the oath and the crown "
  "are stitched and lit by stitched candles; a flame is unpicked on 'died' and the drone follows it out; the king is unpicked out of his own oath and his crown is left "
  "hanging; on 'crown.' the crown's gold is ripped out and the last candle dies with the music. In near-silence a war of stitched slips stands up out of the cloth, "
  "freezes while a hundred years age it, topples and is unpicked into a field of needle holes. Fire burns through the linen, a forest swallows the road of unity, the "
  "road becomes the game's four realm borders under quilted fog, and on the bass entry the camera pulls back to show the whole chronicle fraying into darkness on the "
  "table, one gold glint surviving. Dawn mends it. At its unwritten end one banner and one village rise, the gold thread frames one blank leaf, then embroiders the "
  "game board; on the climax the cloth becomes the live 3D board seen from the menu camera, the leaf stands up as a lectern, the chronicler's furniture assembles round "
  "it, and on 'chronicles' the same thread stitches the word Chronica. The last 4.3 s are the live menu, frame for frame, with the page left blank for the player.\n")

A("## 2. Rules of this film\n")
A("- **Two renderers, one look.** Everything is relight25d (R25) stitch maps: albedo, height_mm, tangent, material, coverage, stitch_id. Frontal shots are relit in numpy (R25-F/S/L). "
  "Every 3D insert (macro, war slips, banner/village, board awakening) is Eevee rendering a displaced mesh built from the *same* maps (EV-DM), and each insert starts or ends on a "
  "registered pose where it equals the R25 frame (swap budget: median dE_ok x100 < 2, no edge shift > 1 px).\n"
  "- **3D only when something rises out of the cloth**, and every rising piece shows thread tethers, a contact shadow and its needle-hole footprint for at least 6 frames.\n"
  "- **Light is the editor.** Practical light follows the score (section 7.3). Raking key 12-30 deg; flat light never.\n"
  "- **Scale follows the music.** The tightest framings sit on the quietest sound (S01 open, S11 collapse, S13 gap); the two decisive camera gestures sit on the two biggest musical events "
  "(the pull-back launching on the bass entry f1283, the crane landing on the climax f1744-1766); no fast moves under the near-silent war.\n"
  "- **Camera grammar.** Truck, don't pan; <= 12 px/frame over stitch texture, 180-deg motion blur above that; exponential zooms; the cloth stays within 25 deg of facing the camera "
  "(apart from the 15-20 deg macro tilts that give a focus band, the war's 22-deg oblique and the final 24-deg crane onto the menu camera are the only tilts); no orbit, no tilt-shift, no dolly-zoom.\n"
  "- **Text budget.** One titulus (SINE HEREDE) and the title (Chronica). Nothing else is written on screen.\n"
  "- **Metal budget.** Three full flares (crown f230, 'whole' f1466, title f1862-1904); listed small glints capped at gold_hi; all other gold reads by light and shadow (section 7.2).\n"
  "- **4:3 safe.** Every composition before f1599 keeps its key action inside x 320-2240; f1599-1983 has a re-composited 4:3 master (section 13).\n")

A("## 3. What changed from the drafts (merge log)\n")
A("### 3.1 Judge must-fix items and how v1 answers them\n")
A(table(["item", "v1 fix"], MERGE_MUST_FIX) + "\n")
A("### 3.2 Grafts adopted\n")
A(table(["from", "graft"], MERGE_GRAFTS) + "\n")
A("### 3.3 Deliberately not grafted\n")
for r in MERGE_REJECTED:
    A(f"- {r}")
A("")

A("## 4. Frieze layout (reading order)\n")
A("Scale anchor: panel-native 5 px/mm (each AI panel = 550 x 307 mm), R25 bakes at 10 px/mm (2x headroom). F0 = full height 440 mm in 1440 px (3.3 px/mm); "
  "F1 = panel width (4.65 px/mm); F2 = one figure (~12.8 px/mm); F3 = macro. Travel is compressed with divider splices (8-frame match dissolves on an identical tree) "
  "and two dark splices hidden in near-black (f820, f988-997).\n")
A(table(["#", "section", "width (mm)", "content / assets", "shots"], FRIEZE_LAYOUT) + "\n")

A("## 5. Storyboard at a glance\n")
rows = []
for s in SHOTS:
    e = s["eevee"]
    ev = "-"
    if e["block"]:
        parts = []
        if e["r1080"]:
            parts.append(f"{e['r1080']} @1080")
        if e["r1440"]:
            parts.append(f"{e['r1440']} @1440")
        ev = f"{e['block']}: " + " + ".join(parts)
    rows.append([f"**{s['id']}** {s['name']}", f"{s['start']}-{s['end']}", f"{s['start_s']:.3f}-{s['end_s']:.3f}", s["act"], s["anchor"], s["summary"], ev])
A(table(["shot", "frames", "time (s)", "act", "audio anchor", "picture", "Eevee"], rows) + "\n")
A(f"**Coverage:** {len(SHOTS)} shots, contiguous, frames 0-{LAST} covered exactly once ({TOTAL} frames). **Eevee:** {E1080} renders at 1080p + {E1440} hero renders at 1440p "
  f"= {E1080 + E1440} (limits 600 + 150). Technique codes: R25-F frontal relight, R25-S stitch-on/unpick, R25-L frontal slip lift, EV-DM Eevee on displaced R25 maps, "
  "COMP compositor, GP game plates.\n")

A("## 6. Full shot table\n")
A("Every row: shot id, start/end frame and seconds, audio event, visual action, camera, technique, material behaviour, transition, emotional purpose, render cost.\n")
rows = []
for s in SHOTS:
    rows.append([f"**{s['id']}** {s['name']}", f"{s['start']}-{s['end']} ({s['frames']} fr)", f"{s['start_s']:.3f}-{s['end_s']:.3f}",
                 s["audio_event"], s["visual_action"], s["camera"], s["technique"], s["material_behavior"], s["transition_out"],
                 s["emotional_purpose"], s["est_render_cost"]])
A(table(["shot", "frames", "seconds", "audio event", "visual action", "camera", "technique", "material behaviour", "transition", "emotional purpose", "render cost"], rows) + "\n")

A("## 7. Through-lines\n")
A("### 7.1 The gold chronicle thread\n")
A("A couched pair of silver-gilt threads: the only metal besides the crown, the goblets and the title. It is never broken (only the crown's gold is torn out in S11).\n")
A(table(["shot", "frames", "what the thread does", "metal level"], GOLD_THREAD) + "\n")
A("### 7.2 Metal budget\n")
A(f"Levels: {METAL_BUDGET['levels']}\n")
A("- **L3 full flares (three only):** " + "; ".join(METAL_BUDGET["L3_flares"]) + ".")
A("- **L2 glints:** " + "; ".join(METAL_BUDGET["L2_glints"]) + ".")
A(f"- **L1:** {METAL_BUDGET['L1_rule']}\n")
A("### 7.3 Practical light as the editor\n")
A(table(["frames", "light", "sound"], LIGHT_EDITOR) + "\n")

A("## 8. Colour script\n")
A("Shot-aligned version of palette.json `acts` (bible section 2.4). Black point never below #07070A, white never above #F3E8D0 (metal glints may touch #FFF3D6 for 1-3 frames). "
  "Shadows cool-violet (#1A1620, 10-20 %), highlights warm (#FFF0D6). Light colours are applied as 20-50 % tints of the display values (1900 K #FF8400, 2200 K #FF9227, 3000 K #FFB16E, 4300 K #FFD5B3).\n")
A(table(["act", "frames", "seconds", "shots", "key light", "dominant", "accents", "grade", "colour events"],
        [[c["act"], c["frames"], c["seconds"], c["shots"], c["key"], c["dominant"], c["accents"], c["grade"], c["events"]] for c in COLOUR_SCRIPT]) + "\n")
A("Signature colour moves: the four house colours in one road (S02) become four separate cords (S16); dyes age in a time-lapse (S12) and revive aged -> fresh behind the dawn (S19); "
  "purple belongs to the king alone and leaves with him (S09); after f1798 nothing is graded, because the frame must equal the live menu.\n")

A("## 9. Sync map (frame-exact hits)\n")
A(table(["frame", "sound", "picture"], SYNC_MAP) + "\n")

A("## 10. Six keyframes\n")
for k in SIX_KEYFRAMES:
    A(f"{SIX_KEYFRAMES.index(k) + 1}. **f{k['frame']} ({k['frame'] / FPS:.2f} s, {k['shot']}) {k['title']}.** {k['description']}")
A("")

A("## 11. Proof of concept: 'The Cloth Becomes the Board' (v1)\n")
A(f"**Window:** f{POC['frames'][0]}-{POC['frames'][1]} (142 frames, {POC['duration_s']} s), audio {POC['audio_slice_s'][0]}-{POC['audio_slice_s'][1]} s. {POC['summary']}\n")
A("**Beats**\n")
for b in POC["beats"]:
    A(f"- {b}")
A(f"\n**Technique.** {POC['technique']}\n")
A("**Inputs needed**\n")
for b in POC["inputs"]:
    A(f"- {b}")
A("\n**Pass / fail**\n")
for b in POC["acceptance"]:
    A(f"- {b}")
A(f"\n**Cost.** {POC['cost']}\n")
A(f"**Fallback.** {POC['fallback']}\n")
A("**Deliverables:** " + "; ".join(POC["deliverables"]) + ".\n")
A("Why this window: it tests the 2D -> 3D swap from real stitch maps, the believability of rising out of the cloth, stitch-scale continuity under a moving 3D camera, the "
  "lectern leaf, the camera-driven chrome and the hand-off match, all in 4.7 s of frames the film needs anyway. S12-S13 (war slips) and S20-S22 (banner, village) reuse the "
  "same registration trick at lower stakes; the S01/S11 macro rig is the second, smaller look-dev item (one still at f39 and one at f797 before committing).\n")

A("## 12. Render budget\n")
A(table(["block", "shots", "frames", "Eevee @1080", "Eevee @1440 hero", "settings", "est. wall"],
        [[b["block"], b["shots"], b["frames"], b["renders_1080"], b["renders_1440"], b["settings"], b["wall"]] for b in RENDER_BUDGET]
        + [["**total**", "", "", f"**{E1080}** / 600", f"**{E1440}** / 150", "", "~5.5 h single, ~4.6 h on 2 procs"]]) + "\n")
A("- Eevee covers 357 renders (45 % of the 1080p limit, 59 % of the hero limit), leaving room for retakes. 1080p renders are upscaled with Lanczos and pass through COMP grain/fuzz.\n"
  "- R25 (relight25d, measured at 2560x1440 on 2 threads): ~5 s/frame with a moving light, 1.26 s camera-only from a cached plate, 6-8 s for stitch-on/unpick frames. "
  "Shot estimates sum to ~2.3 CPU-h. Panel bakes p1/p3/p6: ~15 min of hints + 5-8 min tiled bake each.\n"
  "- COMP: every one of the 1984 frames, ~0.4 s/frame = ~13 min. x264 from PNG (CRF 14-16), plus the 1920x1080 and 4:3 encodes.\n"
  "- Game plates: ~6 plates/captures in demo mode, ~15 min total.\n"
  "- About 500 of the 1984 frames contain Eevee pixels (f4-75, f785-943, f1524-1798; many on twos or held stills); the other ~1480 are R25 + COMP only.\n")

A("## 13. Hand-off to the live menu\n")
for h in HANDOFF:
    A(f"- {h}")
A("")

A("## 14. Production gates (renderer and content must-fixes from the bake-off)\n")
A(table(["gate", "rule", "shots that depend on it"], GATES) + "\n")

A("## 15. Risks and fallbacks\n")
A(table(["risk", "mitigation"], RISKS) + "\n")

A("## 16. Dependencies\n")
for d in DEPENDENCIES:
    A(f"- {d}")
A("")

with open(OUT_MD, "w") as f:
    f.write("\n".join(md))

print("ok", OUT_MD, OUT_JSON, "shots", len(SHOTS), "frames", TOTAL, "eevee", E1080, E1440, E1080 + E1440)
