"""Generate storyboard_final.md and storyboard_final.json from one data source and check frame coverage.
Run: python3 -I gen_storyboard_final.py  (from any directory; paths are absolute)."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sb_final_shots import SHOTS  # noqa: E402

AAA = os.path.dirname(os.path.dirname(HERE))
OUT_MD = os.path.join(AAA, "story", "storyboard_final.md")
OUT_JSON = os.path.join(AAA, "story", "storyboard_final.json")
FPS = 30
LAST = 1983

TITLE = "CHRONICA - The Living Frieze (storyboard final)"
LOGLINE = ("A forgotten embroidered roll-chronicle on a candle-lit walnut table reads itself left to right: a needle draws its "
           "first gold thread, one realm is stitched into being, a king is unpicked out of his own oath, a silent war rises "
           "and sinks in the cloth, fire, forest and four borders age it into darkness, dawn mends it, and its unwritten end "
           "is stitched into the living game board, where a blank page is left for the player.")

# ------------------------------------------------------------------ checks
TEXT_KEYS = ("audio_event", "visual_action", "camera", "technique", "material_behavior",
             "transition_out", "emotional_purpose", "est_render_cost", "summary", "anchor", "name")


def check_coverage(shots):
    shots = sorted(shots, key=lambda s: s["start"])
    assert shots[0]["start"] == 0, "must start at frame 0"
    for a, b in zip(shots, shots[1:]):
        assert b["start"] == a["end"] + 1, f"gap/overlap between {a['id']} and {b['id']}"
    assert shots[-1]["end"] == LAST, "must end at frame 1983"
    total = sum(s["end"] - s["start"] + 1 for s in shots)
    assert total == LAST + 1, total
    seen = [0] * (LAST + 1)
    for s in shots:
        for f in range(s["start"], s["end"] + 1):
            seen[f] += 1
        for k in TEXT_KEYS:
            assert "|" not in s[k], f"pipe char in {s['id']}.{k}"
    assert all(c == 1 for c in seen), "every frame must be covered exactly once"
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
assert E1080 <= 600 and E1440 <= 150, (E1080, E1440)
BLOCK_1080 = {}
for s in SHOTS:
    for blk in s["eevee"]["block"].split("+"):
        if blk:
            BLOCK_1080.setdefault(blk, [0, 0])
    b = s["eevee"]["block"]
    if b == "E3+E4":
        BLOCK_1080["E3"][0] += s["eevee"]["r1080"]
        BLOCK_1080["E4"][1] += s["eevee"]["r1440"]
    elif b:
        BLOCK_1080[b][0] += s["eevee"]["r1080"]
        BLOCK_1080[b][1] += s["eevee"]["r1440"]
assert BLOCK_1080 == {"E0": [101, 0], "E2": [42, 0], "E1": [77, 0], "E3": [143, 0], "E4": [0, 45]}, BLOCK_1080

# ------------------------------------------------------------------ static data
RULES = [
 ("Two renderers, one look", "Everything is relight25d (R25) stitch maps: albedo, height_mm, tangent, material, coverage, stitch_id. Frontal shots are relit in numpy (R25-F/S/L). Every 3D insert (macro, goblets, war slips, banner/village, board awakening) is Eevee rendering geometry built from the *same* maps (EV-MR, EV-DM/P, EV-DM/G), and each insert starts or ends on a registered static pose where it equals the R25 frame (swap budget: median dE_ok x100 < 2, no edge shift > 1 px; swaps at S01 f62-72, S13 f936-941, S23 f1720-1725; qa/swap also run at f1612/1613)."),
 ("3D only when something rises out of the cloth", "Every rising piece shows thread tethers and a contact shadow for at least 6 frames and its needle-hole footprint (the ghost) for at least 12 frames (pipeline 7.5); pieces hinge or peel from one edge, so the footprint is left open beside or in front of them."),
 ("Embroidery never emits", "All light comes from real practicals: the window (late day in Act I, dawn in Act IV), the chronicler's candles (lit for 'table', guttering on 'died', carried over the crown, dying on the collapse, relit on f1664 and f1707 in the desk) and the hearth (Act III, from below). Stitched flames are wool. The only glowing thing in the film is the real burn's ember rim in S14."),
 ("Light is the editor", "Practical light follows the score (section 7.3). Key elevation 15-30 deg by default (bible rule 5); documented exceptions: Act II at 12 deg (set by the bible's own colour script, 2.4), the S01 window shaft at 8 deg, the Act III hearth at 6-15 deg (pipeline section 6), the S13 graze at 6 deg and the S10 candle extremes at 4.8-4.9 deg. Flat light never."),
 ("Photosensitivity", "No general flash: whole-frame luminance components above 3 Hz stay under 10 % (fire <= 4 %, candles <= 3 % globally); strong flicker stays local (flames, the hearth glow, the ember rim, each well under 25 % of the screen); the hundred years is one slow light arc. Gate G13 (qa/flash.py, Harding-style) runs on the master and every bucket encode."),
 ("Scale follows the music", "The tightest framings sit on the quietest sound (S01 open, S11 collapse); the silences get locked frames (S13 gap, S17); the two decisive camera gestures sit on the two biggest musical events (the pull-back launching on the bass entry f1283, the crane landing on the climax f1744-1766). Under the near-silent war the only moves are S12's slow crane (settled before any figure stands) and S13's crane back to face-on (~0.9 deg/frame)."),
 ("Camera grammar", "Truck, don't pan; <= 12 px/frame over stitch texture, 180-deg motion blur above that; exponential zooms; the camera is rendered on ones whenever it moves; the cloth stays within 25 deg of facing the camera, apart from the listed tilts (15-deg macro focus bands, the war's 22-deg oblique, the 10-deg rostrum tilt in S20-S21, the final 24-deg crane onto the menu camera); no orbit, no tilt-shift, no dolly-zoom."),
 ("AI panels", "Panel faces at or below 1.0x panel-native unless they sit in shadow; the king stays inside frame x 0.43-0.57 whenever p1 is pushed in (the panel's own limit); symmetry is broken by light from one side and by ageing, not by impossible framings; full-p1 holds are trimmed in favour of border and thread detail."),
 ("Text budget", "One titulus (SINE HEREDE) and the title (Chronica). Nothing else is written on screen."),
 ("Metal budget", "Two full flares (crown f230, 'whole' f1466); listed L2 glints; one needle glint on the title (f1846); everything else, including the title strands, the ornaments, the leaf couching and the board borders, reads by light and shadow at L1 (section 7.2)."),
 ("Dye budget", "Narrative fills at or below OKLCH chroma .13 in every act (Act II .12), heraldic at or below .20, the real ember rim exempt; purple belongs to the king alone (the violet bands of p6 and war_bg are re-dyed)."),
 ("The desk", "The menu chrome is the chronicler's desk: locked to the frame from f1612, in near-darkness, revealed only by its own candles and finally by the board's daylight; its one physical action is the valance unroll (section 7.4)."),
 ("4:3 safe and aspect buckets", "Every composition before f1599 keeps its key action inside x 320-2240; f1599-1983 is recomposited per aspect bucket (section 13)."),
]

CRITIQUE = [
 (1, "Blocker", "Accepted", "Matched ending only in the no-save state (5 buttons, the only state where the blank leaf equals the card). The overlay probes Godot's IDBFS store ('/userfs') for the files Match.has_save() reads, with a first-run localStorage flag as fallback; a save present means no autoplay, and a plain 1.5 s dissolve if it plays. G12 applies to the 5-button state only.", "S22-S26, 13"),
 (2, "Blocker", "Accepted, modified", "_layout() ported to Python; f1599-1983 (leaf, E4L, desk, valance, COMP) built per aspect bucket. Buckets: 16:9, 16:10, measured iPad Safari landscape (~1.56), 1.52, 1.43, 4:3 (16:10 and '1.6' are the same ratio, so the sixth bucket is the Safari viewport). Because chrome scales with viewport height and the card with width, only aspects within 0.1 % of a bucket get the matched ending; phones and everything else get a plain dissolve. Board stays a keep_height crop; G12 per bucket.", "S22-S26, 13"),
 (3, "Blocker", "Accepted", "The hundred years is one slow light arc plus ageing; whole-frame modulation above 3 Hz under 10 % (fire <= 4 %, candles <= 3 %), strong flicker local; S10's carried candle compensated to +/-10 %; new gate G13 (qa/flash.py).", "S03, S10, S12-S14, S22-S26"),
 (4, "Major", "Accepted, modified", "S12 opens at F2 (~240 mm, not macro) and cranes to F1 in 34 frames (edges ~31 px/frame on average, centre <= 5), settled at f877; the stand-up starts f878 on twos with the camera locked; the camera is on ones whenever it moves. The 0.12 s lunge is dropped: the slips rise into their strike poses, which keeps the beat inside the shorter window.", "S11-S13"),
 (5, "Major", "Accepted (second option)", "The king stays inside frame x 0.43-0.57: S04 pushes 1.00-1.07x, S09 holds 1.06x and pushes to 1.25x with the throne at 0.47; asymmetry comes from the one-sided candle and Act II ageing. S10 now specifies its 1.25 -> 1.00x pull with a 13 mm leftward drift. No new panel art is authored.", "S04, S09, S10"),
 (6, "Major", "Accepted", "Crown lift 15 mm; the candle is carried right to left over the top (az 10 -> 173 deg) with elevations 4.9 / 8.4 / 8.3 / 4.8 deg at gold / red / blue / green (101-177 mm throws, a documented elevation exception); the shadow rests on the void f758-761; done as an offset slip alpha in COMP.", "S10"),
 (7, "Major", "Accepted", "S11 is the hanging slip: tethers pop f786-797, the slip is yanked out f797-798. Macro crown baked at 40 px/mm from p1's crown segmentation on a 40 px/mm linen patch (1.0x). Cut moved to f783/784.", "S09-S11"),
 (8, "Major", "Accepted, modified", "Rostrum tilt of 10 deg (not up to 15: 10 deg is EV-DM/P's limit) during S20-S21, back to zero by f1612; banner and houses hinge up from one edge like pop-ups so their footprints stay open, and the 28-deg dawn key throws ~1.9x shadows across open linen.", "S20-S22"),
 (9, "Major", "Accepted", "Dissolve ends f1798; first stroke f1799-1801; C-h-r-o-n-i-c-a f1801-1846 (~5.6 frames per letter), last stitch on 'you?'; ornaments f1855-1900.", "S25-S26"),
 (10, "Major", "Accepted", "Patch 260x150 mm (1 vertex/mm outside the focus band); untilt and DOF opening f40-62; crossfade f62-72; E0 renders f4-72. The pull now runs over 74 frames so the field is 220 mm at f72 (peak edge speed 54 px/frame).", "S01"),
 (11, "Major", "Accepted", "Topple and crane finish at f936; swap f936-941 on the static pose; the unpick from f942 is R25 only.", "S12-S13"),
 (12, "Major", "Accepted, modified", "The per-hex wavefront starts on the f1664 bass and spreads from Grandbois; it ends at f1719 rather than f1725 so the R25 -> E4 swap (f1720-1725) happens on a static board.", "S22-S23"),
 (13, "Major", "Accepted, interpreted", "The desk (beam, rolled valance, banners, candles, lions, table edge, reading frame) is locked to the frame from f1612 in near-darkness, never brighter than what it covers until its candles light it (f1664, f1707; gate G14); the only physical action is the valance unroll. A frame larger than the leaf cannot hide beneath it, so 'revealed under the leaf' is read as revealed by candlelight around and behind the leaf, which rises into it; nothing slides or closes.", "S22-S24"),
 (14, "Major", "Accepted", "S24 holds three events: pieces rise (to f1760), the crane lands (f1766, the leaf with it), the valance unrolls (f1755-1782). No sweep, no chrome entrances, no banner swings.", "S24"),
 (15, "Major", "Accepted", "S23/S24 glints deleted; S22 couching at L1 and <= 40 px/frame; one needle glint on the title (f1846); flare 3 replaced by the ornament couching; one needle frontier at a time in S15; crests no longer flash. Flare 2 is kept (it is now 27 frames clear of any other metal event).", "S15, S19, S22-S26, 7.2"),
 (16, "Major", "Accepted", "Title built from R25 couched-floss strands in the valance plane, stitched by a needle working from behind the damask; each letter dissolves to the exact art; no thread climb.", "S25-S26"),
 (17, "Major", "Accepted", "The leaf leads the crane by 4-6 deg over f1726-1750 (visibly foreshortened), is parallel by f1760 and on the parchment rect +/-0.5 px at f1766; the squareness test applies only from f1760.", "S23-S24, 11"),
 (18, "Major", "Accepted", "Embroidery never emits. Practicals: window, the chronicler's candles, the hearth; only the real burn glows. S03: a real candle is lit for 'table'; S07: it gutters on 'died'. p1's four baked glows (one left, three right) are inpainted out of its maps for every state.", "S01-S14, S22-S23"),
 (19, "Major", "Accepted", "S02 breathes by key azimuth/elevation only; S14 tower courses unpicked plus one tethered peel, on twos; smoke advances by stitch-on along its spiral; S16 road segments unpicked, then rings stitched on; fog quilts peel down from the bars in place.", "S02, S14, S16, S19"),
 (20, "Major", "Accepted (Eevee option)", "Goblets are EV-DM/P pieces (block E2: 32 renders on twos in S05 + 10 for the S06 settle, ~13 min).", "S05-S06"),
 (21, "Moderate", "Accepted", "Off-axis framings within item 5's limits; key and candle from one side; S02 capital at x ~0.62 and four unequal towns; S16 unequal towns and a late, re-stitched green ring; crests at irregular moments, heights and sizes; leaf couching wanders +/-1 mm.", "S02-S10, S16, S19, S22"),
 (22, "Moderate", "Accepted", "Narrative fills <= .13 in every act (Act II .12), heraldic <= .20, real ember rim exempt; violet bands of p6 and war_bg re-dyed madder / woad-grey through the hints; p6's gradient sky flattened into banded laid work.", "8, S12, S14"),
 (23, "Moderate", "Accepted (move option)", "Crests moved into the Bb gap (f1493-1517) at 4.0 px/mm, ~240 px per 60 mm crest.", "S19"),
 (24, "Moderate", "Accepted, modified for S12", "With S12 opening at F2 (10.7 px/mm) a 20 px/mm near-region patch keeps <= 1.4x, so the 40 px/mm patch is not needed there (S11's crown macro does get 40 px/mm). S18 gets 1.0 and 0.75 px/mm mips.", "S12, S18"),
 (25, "Moderate", "Accepted", "E4 renders only frames that move: the crane f1726-1766 (41) plus 4 stills (zero-tilt registration, two final light states, final registration) = 45 hero renders; static spans are ratio-blended stills. 105 hero renders are left for retakes.", "S23-S25, 12"),
 (26, "Moderate", "Accepted", "E3 is EV-DM/P at ~18 s; the banner sway continues as a pieces-only layer on twos to f1719; there is no renderer change at f1612/1613, and qa/swap is run there anyway.", "S20-S23"),
 (27, "Moderate", "Accepted", "Ship 1440-high files per bucket (2048x1536 for 4:3), H.264 High 5.1 yuv420p tagged bt709 / tv range, plus an HEVC variant for Safari; G12 runs on device-decoded frames in iPad Safari during the dissolve itself.", "13, G12"),
 (28, "Moderate", "Accepted", "Units' idle zones and water masked out of G12; the dissolve is verified on device to fall inside the tour's 3 s hold, which starts after callMain.", "13"),
 (29, "Moderate", "Accepted (integrator suggestion)", "The overlay opens the engine gate at currentTime >= 64.3 s (f1929); f1929-1983 are identical, so a stalled video there is invisible. The repo is not touched.", "S26, 13"),
 (30, "Moderate", "Accepted", "Poster = dim pre-bloom f4; f0-3 are that same image; the bloom happens on f4.", "S01, 13"),
 (31, "Moderate", "Accepted (integrator suggestion)", "The card is unmasked in reading order (title, subtitle, rule, buttons, ~1.2 s); the drypoint lines are aligned to the live title baseline and rule measured on each bucket's native capture.", "S22, S26, 13"),
 (32, "Minor", "Accepted", "S18 edge speed restated as ~32 px/frame; S01 peak 54; S02 blur threshold 12; E1 renders counted per shot (S12 64, S13 13); Act II 12 deg documented as an exception; ghost rule harmonised (tethers + contact shadow >= 6 frames, footprint >= 12); S13's gap called held, not tight; the dutch is rendered in-camera and the 8 % drift overscan is costed (+17 % pixels) and unwinds in the S13 crane; the figure batch is cut to 16 slips.", "S01, S02, S12, S13, S18, 2"),
 (33, "Minor", "Accepted", "Panel faces <= 1.0x native or in shadow; p6 fire in 3 dye lots of laid flame and no gradient sky; full-p1 framing ends at f357, about 30 frames earlier, handing over to the border and the thread.", "S03-S10, S14"),
]

SIX_KEYFRAMES = [
 dict(frame=91, shot="S02", title="'realm': the frieze and the one realm",
      description="The pull-back easing out over the one realm at ~F1: hillock bands, a paired-line river, four walled towns of different sizes with house-colour pennants and ONE road couched in four alternating house colours entering from the left and climbing to a crowned capital right of centre; above, the upper border with off-centre paired lions and the gold chronicle thread, its first crimson tie-down still visible at top left; 3000 K window key at 22 deg from upper left showing the couching-bar shadow grid; a trace of motion blur at the frame edges. No caption."),
 dict(frame=669, shot="S09", title="'chair': the king unpicked out of his oath",
      description="The repeated oath table at 1.25x, the throne at frame x 0.47: one guttered candle low on the left (12 deg) pools light on a king-shaped void of bare linen pricked with needle holes and red-brown underdrawing, a few purple strands still curling off the cloth; the gold crown slip hangs 15 mm above the void on four gold tethers, its soft shadow below; the red and blue lords at the rim of the pool, faces in shadow, gazes converging; Act II grade, a tideline across the cloth, goblets and stitched candles reduced to needle-hole outlines."),
 dict(frame=899, shot="S12", title="'years': soldiers risen out of the cloth, frozen while a century passes",
      description="A settled 22-deg oblique over the war strip with a 3-deg dutch: the front ranks of blue and crimson figure slips stood up to ~70 deg in strike poses, frozen; snapped tethers curling at their feet, needle-hole footprints open where they lay; long shadows thrown up-frame by the hearth light from the bottom edge, which is just sinking as the century's single pale arc begins at the left; the madder-and-woad-grey sky; the linen around them starting to bleach, fox and tarnish."),
 dict(frame=1319, shot="S18", title="'edges': the chronicle fraying into darkness",
      description="After the bass-entry pull-back: the chronicle is a thin strip on a dark walnut table, both ends lost in darkness; borders unravelling into curling fringe, weft threads hanging, quilted fog appliques creeping over it; the hearth's embers gone; light falling to -2.5 EV at the frame edges; one tiny gold glint at the far right end: the chronicle thread, unbroken."),
 dict(frame=1760, shot="S24", title="Climax peak: the cloth has become the board",
      description="The menu camera all but reached: the 3D embroidered hex board (padded satin fields, couched gold realm borders, denim sea with stitched waves) with towns, forests and figure groups risen out of the cloth, footprints open, the last tethers released, Grandbois under its banner; the leaf just parallel to the image plane inside the walnut reading frame on the left; the desk locked to the frame and lit only by its two candles (blue- and red-lion banners, carved lions, the walnut beam), the navy valance half unrolled with its letters only underdrawn, tassels swinging. No light sweep, no glints."),
 dict(frame=1983, shot="S26", title="Final frame: the pixel-matched hand-off",
      description="Identical to frames 1929-1982 in each aspect bucket: the live main menu's first frame in its no-save state minus the card's contents. 16:9 shown: real game board, walnut bar, gold-stitched 'Chronica' valance at (784,0,992x296), blue- and red-lion banners, both candles, carved lions and the blank parchment card at (224,319)-(1227,1376), ready for the overlay hold and the hand-off dissolve in which the card writes itself in reading order."),
]

POC = dict(
 title="The Cloth Becomes the Board (final)",
 frames=[1664, 1846], duration_s=round(183 / FPS, 3),
 audio_slice_s=[round(1664 / FPS, 3), round(1847 / FPS, 3)],
 summary=("183 real production frames (f1664-1846, 6.1 s) played against the real audio (the f1664 bass, 'When this age is "
          "remembered', the climax gap and 'what will the chronicles say of you?'), built in two aspect buckets (16:9 and 4:3). It "
          "proves the film's hardest claims and its hand-off in one window: a face-on, physically embroidered 2D cloth stitches itself "
          "and becomes a believable 3D game board; the menu chrome reads as the chronicler's desk revealed by its own candles, not as an "
          "overlay; a blank leaf rises with real foreshortening into its frame; the title is stitched from real strands; and everything "
          "lands pixel-exact on the live menu, in each bucket, on device."),
 beats=[
  "f1664-1719 (2D, R25-S + desk): on the bass the desk's left candle is lit and reveals the left of the desk and the reading frame by light alone; the per-hex wavefront opens from Grandbois (satin fields, denim sea with wave marks, plan-icon towns, gold borders at L1, no needles); the right candle is lit on 'age' f1707; the last hex closes f1719.",
  "f1720-1725 (the swap): registered cross on the static board from the R25 comp to the E4 zero-tilt still (light state B). Must be invisible.",
  "f1726-1766 (3D, E4 hero): the couching is pulled from the leaf's right and top edges; the leaf hinges up leading the crane by 4-6 deg, parallel by f1760, on the parchment rect at f1766; the crane 0 -> 24 deg lands on the exact menu camera (fov 30, pitch 66.09, distance 20.9); fields swell as padded coupons; pieces peel up out of their footprints on twos with tethers, settled by f1760; the valance unrolls f1755-1782 (COMP).",
  "f1767-1798 (convergence): ratio-blended light-state stills C/D, then the dissolve to the projected 2x UI-free plate and the native capture, nameplates and unit shields settling in.",
  "f1799-1846 (locked COMP): the needle pushes through the valance and couches C-h-r-o-n-i-c-a in R25 strands, ~5.6 frames per letter, each letter dissolving to the exact art; the single needle glint on 'you?'.",
 ],
 technique=("Blender 4.0.2 Eevee-legacy under xvfb (bpy 5.2.2 Eevee-Next via EGL as fallback), 2560x1440, 16 TAA, camera on ones, rising "
            "pieces on twos. Board proxy = subdivided plane with per-hex puff shape keys (dome + seam pinch) on staggered drivers + the "
            "decoded game OBJs at their seed-4242 world positions with a piece material port (palette albedo, triplanar stitch normal, "
            "brown inverted-hull outline). Ground albedo/normal = R25 board maps in plate-UV space, projected from an overscanned top-down "
            "UI-free plate (zero-tilt framing) and from the menu-camera UI-free plate (final framing); a pieces-hidden plate fills the "
            "ground under rising pieces, and rising pieces keep OBJ + stitch materials until convergence (no projection smear). Leaf = "
            "separate holdout layer + shadow catcher per bucket (E4L). Static spans are ratio-blended stills. Desk = layers matted from each "
            "bucket's native capture, locked to the frame, relit by the candle practicals. Title = R25 couched-floss strands in the "
            "valance plane. Menu rects come from a Python port of main_menu.gd _layout(). COMP adds fuzz halo, grain and grade."),
 inputs=[
  "UI-free demo-mode plate from the menu camera (seed 4242, small map, zoom 11, first tour focus) at 2560x1440 and 2x (5120x2880), plus the same plate with towns/units hidden.",
  "An overscanned top-down UI-free plate covering the zero-tilt footprint (fallback: extend the board procedurally with R25 kit hexes matched per terrain class).",
  "Native captures of the live menu's first frame in the no-save state at 2560x1440 (16:9) and 2048x1536 (4:3): desk mattes, nameplates/shields, card interior to inpaint, title baseline and rule positions, final match.",
  "Hex size/orientation and world positions of hexes, settlements and unit groups for seed 4242 (from the game's map and camera code; fallback: solve from the plate with the known camera).",
  "Decoded main_menu.gd (_layout) and ui_theme.gd (9-slice margins); models/*.obj + game_palette.json; the R25 emb/ library; palette.json acts IV-V.",
  "An iPad (11-inch or 4:3) with Safari for the on-device G12 and flash checks.",
 ],
 acceptance=[
  "Swap f1720-1725: median dE_ok x100 < 2 and no edge shift > 1 px between the R25 comp and the zero-tilt Eevee still.",
  "End match f1798: Eevee vs UI-free plate median dE_ok x100 < 3, town silhouettes within 1 px; after the dissolve, mean abs diff vs the native capture < 2/255 outside flames, units, water and card interior.",
  "Leaf: over f1726-1750 its corners show a 4-6 deg lead (visible foreshortening); from f1760 it is parallel to the image plane within 0.2 deg; at f1766 it sits on the bucket's parchment rect +/-0.5 px.",
  "Desk (G14): before its light event each desk layer's luminance differs from what it covers by < 3 %; layers sit on their bucket rects +/-0.5 px; nothing translates or scales.",
  "Title: each letter is visibly built from couched strands and tie-downs, then equals the logo_title art within 1/255 six frames after completion; exactly one L2 needle glint.",
  "Flash (G13): no general or red flash; whole-frame components above 3 Hz < 10 %.",
  "Every rising piece shows tethers + contact shadow >= 6 frames and its footprint >= 12 frames.",
  "Hand-off (G12) in both buckets on the shipped 1440 H.264 encode, decoded in iPad Safari during the dissolve; zero void pixels on every frame.",
 ],
 cost=("All 45 E4 hero renders (~75 min) are in this window, plus E4L 41 leaf-layer renders per bucket (2 buckets, ~14 min), R25 wavefront "
       "56 frames x ~8 s (~8 min), title strands 48 x ~3 s, COMP 183 frames x 2 buckets. All are production frames of S22-S25, so the PoC "
       "spends budget the film needs anyway."),
 fallback=("If world positions cannot be recovered: plate-only 2.5D lift, using the known board-plane homography, towns hand-masked "
           "and raised by height-from-ground displacement with synthesised side walls (less parallax, same hand-off). If the lectern "
           "leaf fails its tests, the leaf becomes a 2D layer that lifts off the cloth (widening soft shadow) with an explicit 4-6 deg "
           "foreshortening homography easing to zero by f1760. If the desk still reads as an overlay, it stays fully dark until the "
           "convergence dissolve and is revealed only by the board's daylight."),
 deliverables=["poc_cloth_to_board_169_1440.mp4 and poc_cloth_to_board_133_1536.mp4 muxed with audio 55.467-61.567 s",
               "contact sheet f1664/1707/1719/1726/1744/1760/1766/1798/1846",
               "A/B stills at f1720 (R25 vs Eevee) and f1798 (Eevee vs plate) with difference images",
               "on-device G12 and G13 reports; acceptance report (json)"],
)

GOLD_THREAD = [
 ("S01", "f5-39", "drawn up through the linen by the needle on 'There', taut on 'world', pinned by the first crimson tie-down", "L2"),
 ("S06", "f358-400", "runs on along the upper border, in close detail, and out of frame: 'never end'", "L1"),
 ("S12", "f899-917", "tarnishes #E9BE6A -> #7A5A2A in the hundred-year light arc", "-"),
 ("S18", "f1336-1381", "one surviving glint at the far right end of the darkened strip; pulses on bass f1345", "L2"),
 ("S19", "f1466-1480", "re-couched end to end on 'whole'", "L3 flare 2"),
 ("S22", "f1599-1645", "runs down from the border and couches the leaf's top and right edges (<= 40 px/frame), rests at its corner", "L1"),
 ("S23", "f1726-1734", "pulls its couching out of the leaf's right and top edges so the leaf can lift", "L1"),
 ("S25-S26", "f1799-1900", "echoed, not continued: a needle from behind the valance couches 'Chronica' and its ornaments in gold floss (no climb)", "L1; one L2 needle glint f1846"),
]

LIGHT_EDITOR = [
 ("f0-3", "dim ambient only: the pre-bloom f4 still, about -3 EV (= the poster)", "digital silence"),
 ("f4", "a shutter opens off-frame: a low shaft of late-day window light, 1900 K, elev 8 deg, upper left", "drone + 'There'"),
 ("f40-125", "the window widens: the key climbs to 22 deg and warms to 3000 K", "litany begins"),
 ("f134-146", "a real candle is lit on the walnut table off-frame left; its pool blooms over the left of p1", "'table'"),
 ("f198-212", "the candle flame lifts (+0.2 EV)", "in-gap swell"),
 ("f402-445", "the window light fades with the day (-0.7 EV); the candle is the only key (1900 K, 12 deg)", "gap after 'never end'"),
 ("f465-471", "the candle gutters (-0.5 EV) and recovers lower; a stitched flame on p3 is unpicked", "'died'; the drone exits after (f480-548)"),
 ("f741-778", "the candle is carried round over the crown, right to left over the top (az 10 -> 173 deg, elev 4.9 -> ~30 -> 4.8 deg); brightness held within +/-10 %", "'his own head beneath'"),
 ("f797-812", "the candle dies (-4 EV)", "-20 dB collapse f797"),
 ("f832-843", "the hearth's ember glow rises from the bottom edge", "near-silence"),
 ("f844-1050", "hearth firelight from the bottom edge (2200 K; slow swells <= 15 %, components above 3 Hz <= 4 % of the frame)", "the war; fire peak in S14"),
 ("f899-917", "the hearth sinks and one slow pale arc of daylight crosses the war strip once: the century", "'years'"),
 ("f1051-1282", "the hearth sinks to an ember glow; cool dusk fill rises", "M4 plateau"),
 ("f1292", "the embers die", "'dark'"),
 ("f1345", "the surviving gold glint pulses (the only light event of the gap)", "bass pulse #2"),
 ("f1372-1381", "pre-dawn lift from the window: cool grey-blue fill from the left +0.3 EV", "in-gap swell into 'Now'"),
 ("f1382-1470", "dawn through the window: sweep L->R (4300 K, elev 28 deg)", "'Now'"),
 ("f1612-1640", "the dawn narrows to the window's shape: one pane on the leaf, one on Grandbois, the mullion's shadow between; everything else sinks to near-black, where the desk stands unseen", "after 'blank'"),
 ("f1664", "the desk's left candle is lit: a pool across the leaf; the left of the desk revealed", "bass pulse"),
 ("f1707", "the desk's right candle is lit: the right of the desk revealed", "'age'"),
 ("f1744-1760", "both candles swell +0.25 EV into the peak, then settle", "climax"),
 ("f1772-1798", "the board takes the game plate's daylight; candle pools fade to the sprites' own glow", "recession begins"),
 ("f1846", "the leaf's drypoint ruling catches the candlelight once; the title needle's only glint", "'you?'"),
 ("f1855-1928", "flames settle to exactly the sprite art", "ring-out"),
 ("f1929-1983", "locked, identical frames", "ring-out tail"),
]

DESK = [
 ("What it is", "The menu chrome (walnut beam, valance on its rod, blue- and red-lion banners, two candles, carved lions, the table edge on iPad aspects, the walnut reading frame round the card) is the chronicler's desk, seen at the edges of the reader's view."),
 ("When it exists", "From f1612, when the camera reaches the zero-tilt pose, locked to the frame at the bucket's menu rects. It is composited only where it is not brighter than what it covers (the frame edges have sunk to near-black over f1612-1640), so it is never seen arriving (gate G14)."),
 ("How it is revealed", "Only by light: its left candle is lit on the f1664 bass and its right candle on 'age' f1707 (each an R25 point practical at the sprite's flame, flickering locally); the rest arrives with the board's daylight during the convergence f1772-1798."),
 ("What moves", "One physical action: the valance unrolls from its rod (f1755-1782). Nothing slides, swings in, rises or closes. The leaf rises from the board into the reading frame's aperture; at zero tilt it already lies just inside it (the menu geometry puts its hinge within ~6 px of the aperture's bottom edge and its size at ~0.91x; the zero-tilt pivot offset is chosen per bucket so no rim overlaps it), and the rims sit in darkness or in the mullion's shadow until a candle reaches them."),
 ("Why this is honest", "In the final menu these objects are a frame around a living world; the film lets the viewer discover that frame in the dark and see it lit by candles that have been the film's practical light since 'table'."),
]

COLOUR_SCRIPT = [
 dict(act="I Oath", frames="f0-445", seconds="0.00-14.87", shots="S01-S06",
      key="window light, 3000 K raking from upper left, elev 22 deg (a 1900 K shaft at 8 deg on f4, climbing), key:fill 3:1; practical: the table candle (1900 K) off-frame left from f134",
      dominant="linen #D4BE98, gold #E9BE6A, terracotta #B65E43",
      accents="crimson #CC3A2C, royal blue #3F72BE, green #3A8C63, builders ochre #CB7A1C (heraldic); royal purple #71508A (king only)",
      grade="sat 1.0; chroma caps: narrative fills .13, heraldic .20; lift #100C08, gain #FFF4E2",
      events="f4 bloom; f134-146 candle lit; f230 metal flare 1 (crown); f402-445 the window fades"),
 dict(act="II Death", frames="f446-843", seconds="14.87-28.13", shots="S07-S11",
      key="the single candle 1900 K, elev 12 deg (bible 2.4; documented exception to the 15-deg rule), key:fill 6:1; S10 extremes 4.8 deg",
      dominant="night #141325, royal purple #4E2F5E, linen_lo #B49C74",
      accents="gold only (the crown); ink red-brown #6E3326 for underdrawing",
      grade="sat 0.7, chroma cap .12 (crown gold as heraldic), lift #08080E, gamma .95, gain #FFE9CF",
      events="f469 candle gutters (-0.5 EV); f741-778 candle carried over the crown; f797-812 candle dies (-4 EV, floor #07070A, fill #141325 at 10 %)"),
 dict(act="III War", frames="f844-1381", seconds="28.13-46.07", shots="S12-S18",
      key="2200 K hearth light grazing from the bottom edge (slow swells <= 15 %, above 3 Hz <= 4 % of the frame), key:fill 5:1; 2-3 deg dutch in S12-S14",
      dominant="dusk sky madder-and-woad-grey #6A3A38 / #4F6F8A (no violet), crimson deep #56100E, smoke #4A4547, forest #34432F",
      accents="stitched fire in narrative lots (terracotta #B65E43, mustard #C3963F, madder_dark #7A3B2C); the real ember rim #DE6A2C -> #F6B54A (exempt); Legion crimson and realm cords (heraldic)",
      grade="sat .85; caps narrative .13, heraldic .20; lift #0B0607, gamma .92, gain #FFE2C4; edges to -2.5 EV by f1319",
      events="f899-917 the century: one light arc + ageing; f982-1050 burn and fire; f1292 embers die; f1345 glint pulse; f1372 pre-dawn lift"),
 dict(act="IV Renewal", frames="f1382-1688", seconds="46.07-56.30", shots="S19-S22",
      key="4300 K dawn through the window from the left, elev 28 deg, key:fill 2.5:1, sweep L->R f1382-1470; narrowing to two window panes f1612-1640; the desk's left candle from f1664",
      dominant="linen hi #E6D7B6, linen #D4BE98",
      accents="navy #15223A, gold #D79A33, woad #4F6F8A; crests at game chroma (heraldic register)",
      grade="sat .9; caps narrative .13, heraldic .20; lift #0E0C0A, gamma 1.05, gain #FFF8EC; dyes aged -> fresh (OKLab, 1.5-3 s, staggered)",
      events="f1466 metal flare 2 (thread re-couched); f1493-1517 crests; f1612-1640 edges sink; f1664 left candle lit"),
 dict(act="V Question", frames="f1689-1983", seconds="56.30-66.13", shots="S23-S26",
      key="the two window panes and the desk's two candles (3200 K pools, elev ~20 deg at the board), key:fill 4:1, converging by f1798 on the game plate's own daylight",
      dominant="navy #15223A / navy deep #080D17 (valance), game board colours (denim sea #316994, satin fields)",
      accents="gold #F8D57C / #D79A33, metal gold #E9BE6A",
      grade="sat 1.0; caps narrative .13, heraldic .20 (board satin at game chroma); lift #05070C, gain #FFF2DC; from f1798 no grade on the plate (must equal the live menu)",
      events="f1707 right candle lit; f1744-1760 candle swell; f1799-1846 title; f1855-1900 ornaments; f1929 lock"),
]

METAL_BUDGET = dict(
 L3_flares=["f224-236 crown ('crown' f230)", "f1466-1480 chronicle thread re-couched ('whole')"],
 L2_glints=["f5-39 thread on its twist, and the needle for 1-3 frames", "f757-762 crown glint as the carried candle passes over",
            "f784-797 the crown slip's couched gold in macro (dying with the light)", "f1345 surviving glint pulse",
            "S15 the single lead needle, 1-2 frames per pass", "f1846-1847 the title needle's one glint"],
 L1_rule="Everything else (sword, goblets, banner pole, the leaf couching, the board's gold borders, the title strands and ornaments, realm cords) reads by light pools, sheen and contact shadows: no travelling metal glint.",
 levels="L3 = metal reaches #FFF3D6 for 1-3 frames; L2 = capped at gold_hi #F8D57C, <= 1 % of pixels; L1 = wool/silk sheen only.",
)

RENDER_BUDGET = [
 dict(block="E0 macro rig (EV-MR: needle, thread, crown slip)", shots="S01, S11", frames="f4-72 + f4 ambient split; f784-812 + 2 war-pose light-split stills",
      renders_1080=101, renders_1440=0, settings="1920x1080, 16 TAA, on ones, ~1.1M-vert displaced linen (260x150 mm, 1 vertex/mm outside the focus band), 40 px/mm crown slip, real DOF + motion blur",
      wall="~65 s/frame = ~109 min single"),
 dict(block="E1 war slips (EV-DM/G)", shots="S12-S13", frames="f844-877 ones, f878-911 twos, f912-936 ones, f936 registration still",
      renders_1080=77, renders_1440=0, settings="1920x1080 (2080x1170 with the 8 % drift overscan), 16 TAA at F2 / 8 TAA wide; dutch in-camera; ageing and light arc in COMP via UV + ratio passes",
      wall="34 x ~35 s + 42 x ~18 s + 1 x ~60 s = ~33 min"),
 dict(block="E2 goblets (EV-DM/P)", shots="S05-S06", frames="f276-357 on twos",
      renders_1080=42, renders_1440=0, settings="1920x1080, 16 TAA, pieces + shadow-catcher ground, shadow ratio onto the R25 plate",
      wall="~18 s/frame = ~13 min"),
 dict(block="E3 banner + village (EV-DM/P)", shots="S20-S23", frames="f1524-1612 on ones (camera moving); banner-sway pieces layer f1613-1719 on twos",
      renders_1080=143, renders_1440=0, settings="1920x1080, 16 TAA, pieces over the R25 plate, tilt <= 10 deg",
      wall="89 x ~18 s + 54 x ~10 s = ~36 min"),
 dict(block="E4 board awakening (EV-DM/G hero)", shots="S23-S25", frames="zero-tilt still (32 TAA), crane f1726-1766 on ones, 2 final light-state stills, final registration still (32 TAA)",
      renders_1080=0, renders_1440=45, settings="2560x1440, 16 TAA (32 for registration stills), pieces on twos inside camera-on-ones frames, geometry-heavy",
      wall="41 x ~95 s + 4 stills = ~75 min single"),
 dict(block="E4L leaf layer per aspect bucket", shots="S23-S24", frames="f1726-1766 x 6 buckets",
      renders_1080=0, renders_1440=0, settings="leaf holdout + shadow catcher only, ~10 s each (246 light-layer renders, not counted against the hero budget)",
      wall="~41 min"),
]

GATES = [
 ("G1 Bayeux kit proof", "Build one reusable Bayeux kit (hillocks, interlace trees, borders with vignette beasts, towns from settle_* elevations at varied sizes, couched bars, roads, underdrawing). Prove S02 side by side with p1 at matched px/mm and identical relight before building any other procedural section; shorten sections with divider splices.", "S02, S08, S12, S15, S16, S19-S22"),
 ("G2 Metal reads as metal", "Add a prefiltered warm studio-gradient environment term and a wider anisotropic glint to R25's metal lobe; verify crown, thread and title strands at >= 3 key azimuths.", "S01, S04, S10, S11, S19, S22-S26"),
 ("G3 Fuzz calibration", "Cut halo/flyaway density on couched cords (no chenille), tint flyaways toward the parent thread and attenuate them over dark fills (no white scratches), add a cheap fibre self-shadow term.", "all R25 shots"),
 ("G4 No void pixels", "Pad every canvas beyond the frustum (S01 patch 260x150 mm); automated per-frame check fails on any void or background pixel.", "all"),
 ("G5 Lift policy", "R25-L only for frontal lifts (camera <= 10 deg off the cloth normal, lift <= 15 mm) with PCSS penumbra growing with lift and contact AO: the S09-S10 crown slip, the S14 tower peel, the S16/S19 fog quilts. Every goblet, hinged or oblique rise goes to Eevee (EV-DM/P at <= 10 deg tilt, EV-DM/G otherwise).", "S09-S10, S14, S16, S19 (R25-L); S05-S06, S12-S13, S20-S25 (Eevee)"),
 ("G6 Fill directions", "Phase-field (phi/psi) stitch layout where the structure tensor is incoherent (throne carving, ermine, horse bodies): no fingerprint whorls or brick lattices.", "p1, p3, p6, slips"),
 ("G7 LOD and shimmer", "LOD-fade weave and strand normals below 2.5 px; shade on the mip within 1.0-1.4x of the screen density (new 1.0 and 0.75 px/mm mips for S18); run the registered shimmer metric on every shot and test an F0 framing with a 12 px/frame truck at 1440p before committing the trucks.", "S02-S08, S15-S19"),
 ("G8 Stitch-on order", "Needle-path ordering by spatial adjacency, per-strand growth along its length with a pop-in height curve; a needle sprite only where a needle is staged (S01, S15 lead tendril, S22-S23 couching, S25-S26 title); per-hex wavefront delay maps for the board; dirty-rect recompute of normals/AO/fibres.", "S14-S16, S19, S22, S23, S25, S26"),
 ("G9 Unpick path", "Snapshot re-rasters every N stitches, needle-hole + underdrawing reveal, loose-end curls from the fibre/curve renderer; addressable weft at fray edges; course-by-course masonry unpick.", "S07, S09, S13, S14, S16-S18"),
 ("G10 Panel bakes", "Tiled re-embroidery of p1/p3/p6 at 10 px/mm, <= 2 GB per process, float16 caches; art-directed hints (~15 min/panel): crown contour-parallel gold, chain, collar, face zones; p1's four flame glows inpainted; p6 sky re-dyed and flattened, fire reduced to 3 laid-flame lots; war_bg violet bands re-dyed.", "S03-S14"),
 ("G11 Light and colour wiring", "Embroidery never emits; practicals (window, candles, hearth) as positioned point/area lights with intensity curves in the relight; act tints; narrative fills <= .13, heraldic <= .20 (qa/clip), the real ember rim exempt; Legion livery in game crimson with a couched-gold cross shield.", "all"),
 ("G12 Hand-off match", "Per aspect bucket, no-save (5-button) state only: f1983 vs the live menu's first frame, mean abs diff < 2/255 outside text, flames, units, water and card interior; no sprite offset > 0.5 px; verified at the master and on the shipped 1440 encode decoded in iPad Safari during the dissolve; the dissolve falls inside the tour's 3 s hold.", "S22-S26"),
 ("G13 Photosensitivity", "qa/flash.py (Harding-style) on the master and every encode: no more than 3 general flashes and no red flash in any 1 s window over > 25 % of the screen; whole-frame luminance components above 3 Hz < 10 %.", "all, esp. S03, S10, S12-S14, S22-S26"),
 ("G14 Desk revealed by light", "Before its light event each desk layer differs in luminance from what it covers by < 3 %; desk layers are locked to their bucket rects +/-0.5 px and never translate, scale or swing; only the valance unrolls.", "S22-S26"),
]

ASPECT_BUCKETS = [
 dict(id="B169", aspect="1.7778 (16:9)", file="intro_169_1440.mp4", size="2560x1440", viewports="16:9 desktop/laptop browsers in fullscreen, TVs, 16:9 tablets"),
 dict(id="B160", aspect="1.6000 (16:10)", file="intro_160_1440.mp4", size="2304x1440", viewports="16:10 laptops and desktops (1440x900, 1680x1050, 2560x1600)"),
 dict(id="B156", aspect="~1.55-1.58, measured", file="intro_156_1440.mp4", size="~2240x1440", viewports="iPad Safari landscape with its tab/address bars (exact innerWidth/innerHeight measured on the target iPads before the per-bucket renders)"),
 dict(id="B152", aspect="1.5228", file="intro_152_1440.mp4", size="2192x1440", viewports="iPad mini 6/7 (2266x1488) as a home-screen web app / fullscreen"),
 dict(id="B143", aspect="1.4390", file="intro_143_1440.mp4", size="2072x1440", viewports="11-inch iPad and iPad Air (2360x1640) as a home-screen web app / fullscreen; iPad Pro 11 (2388x1668, 1.4317) gets the plain dissolve unless added as a seventh bucket"),
 dict(id="B133", aspect="1.3333 (4:3)", file="intro_133_1536.mp4", size="2048x1536", viewports="4:3 iPads (2048x1536, 2732x2048) as a home-screen web app / fullscreen"),
]

HANDOFF = [
 ("Who gets the matched ending", "Only a tablet or desktop (not Device.phone, i.e. not touch with min(screen) < 600 CSS px) with no save (Match.has_save('autosave') and ('quicksave') both false: the 5-button card, the only state the blank leaf equals) and an aspect within 0.1 % of a bucket. With 5 buttons the card is 661 base px high, so tall = vr.y >= 891 holds at every bucket. Everyone else gets a plain 1.5 s dissolve from f1983 to whatever the menu shows. G12 is defined for the matched state only."),
 ("Save detection (integrator suggestion)", "Before playing, the overlay opens Godot's IndexedDB-backed user filesystem ('/userfs', the IDBFS store) and checks for the files Match.has_save() reads (paths to be confirmed from the decoded core/match.gd); if IndexedDB is unavailable it falls back to a localStorage first-run flag written when the intro completes. A save present means the intro is not autoplayed (straight to the game's own loading screen); if it is played anyway, it ends on the plain dissolve. With one save on 16:9 the card is 737 px > 900 - 230, so tall is false and the bar, valance and chrome all vanish: matching that is impossible by design."),
 ("Aspect buckets", "The overlay picks the file by innerWidth/innerHeight at start (bucket table below). f0-1598 is the same content in every file (a centre crop of the 2560 master; every composition is staged inside x 320-2240); f1599-1983 is rebuilt per bucket from a Python port of main_menu.gd _layout() (lib/chron/menu_layout.py: card at (140, max(logo_h+14, 96)) in base px with vr.x = 1600, vr.y = 1600/aspect; banners min(280, 0.24 vr.y) at y 40; candles min(280, 0.23 vr.y) at y 0.5 vr.y - 0.1 h; lions min(230, 0.19 vr.y) bottom-anchored; table_edge_bottom shown when vr.y - card.end.y - 16 >= 90, i.e. on every iPad bucket), checked against a native capture per bucket. The board is a keep_height centre crop of the 16:9 renders (no new hero renders); the leaf (E4L), its couching path, the desk and the valance are per bucket, because the card's position relative to the board moves the lectern hinge to a different board point. Outside the buckets: the nearest file, object-fit cover (contain below 1.30), plain dissolve."),
 ("Final rects (16:9, 2560x1440, menu_layout.json px_2560x1440)", "bar_top (0,0,2560x128); logo_title_banner (784,0,992x296.3); menu_card (224,318.7,1003.2x1057.6), parchment interior (272,357.3,910.7x976); banner_side_left (16,64,129.2x345.6); banner_side_right (2421.1,64,122.9x345.6); candle_left (9.6,686.9,92x331.2); candle_right (2452.9,686.9,97.5x331.2); lion_statue_left (6.4,1163.2,189.9x273.6); lion_statue_right (2362.1,1163.2,191.5x273.6); table_edge_bottom hidden. 4:3 (2048x1536): card (179,255,803x846), banners 280 base px, table edge visible; the other buckets come from the port."),
 ("Final plates", "Per bucket, a native capture of the live menu's first frame in the no-save state at the bucket's encode size. Only the card interior (title, subtitle, divider, buttons, footer) is inpainted from the 9-slice parchment; the valance letters and ornaments are inpainted only for the S24-S26 stitch-on layer; the candle flames are inpainted only for the unlit desk state. Nameplates, stars and unit shields stay as captured. The drypoint title line and rule on the leaf sit exactly under the live title baseline and rule measured on that capture."),
 ("Live board", "The live first frame is not static (two boots differ: mean 0.94/255, 1.2 % of pixels > 16; units idle, water moves), so units' idle zones and water are masked out of G12. The tour holds 3 s on the first focus, starting after callMain; the dissolve must fall inside that hold, verified on device."),
 ("Lock and engine gate (integrator suggestion)", "Every animated layer reaches zero by f1929; f1929-1983 are identical. The overlay opens the engine gate when currentTime >= 64.3 s (f1929) instead of on 'ended', so callMain's multi-second freeze happens while the picture is already still; the overlay then holds f1983 with its gold progress thread until the engine is ready. f1983 must be a clean poster (no blur, calm board at bottom centre)."),
 ("The card writes itself (integrator suggestion)", "Matched state: the overlay dissolves over 0.9 s except over the card rect, where a CSS mask wipes in reading order (title, subtitle, rule, buttons) over ~1.2 s, so the live card text appears line by line on the blank page instead of fading in at once."),
 ("Encode", "Per bucket: 1440-high H.264 High@5.1, yuv420p, CRF-capped ~6 Mb/s, colour tagged bt709 primaries/transfer/matrix and tv range in the stream and container, +faststart; an HEVC (hvc1) variant at ~3.5 Mb/s for Safari; VP9 webm for others; a 1920x1080 16:9 file as the low-bandwidth fallback (plain dissolve). G12 is run on frames decoded in iPad Safari during the dissolve itself (screen recording at native resolution, or a debug overlay that reads back video and canvas), not on PNGs."),
 ("Poster", "poster.jpg = the dim pre-bloom f4 still, which is also f0-3, so a tap on an iPad (unmuted autoplay is blocked) starts the film on the same image and the bloom lands on f4. The 'Touch to begin' text (#7a2a22 at top 72 %) needs a lighter colour on this dark poster (e.g. #E6D7B6). Suggestion only."),
 ("Audio tail", "The master stops at about -48 dBFS on f1983; recommend a 0.5 s gain ramp on the mix tail (f1968-1983) for the audio owner, so the hold never exposes an abrupt cut."),
]

MERGE_MUST_FIX = [
 ("S24 of the frieze draft overcrowded under the key line", "S24 carries three events only (pieces rise, crane lands, valance unrolls); the desk is locked to the frame from f1612 and revealed by its own candles (f1664, f1707); S25 carries only the title; the plate dissolve ends f1798, before the first stroke f1799."),
 ("Frieze S12 overpacked", "War over S12-S13 (138 frames): one generation; a slow crane settled by f877; the stand-up into strike poses f878-896; a century in one light arc; topple f925-936; one mass unpick on 'nothing' f942."),
 ("S17 candlelight dying on 'dark'", "Act II's candle dies at f797 (S11); in Act III the hearth sinks to embers, and the embers die on 'dark' f1292 (S18)."),
 ("Near-black hold while the music rises (f1336-1381)", "The surviving gold glint pulses on bass f1345 and a pre-dawn lift starts at f1372 (S18)."),
 ("Eight tituli", "One titulus only: SINE HEREDE (S08). The only other stitched word in the film is 'Chronica'."),
 ("Glints and sweeps on every beat", "Metal budget: two L3 flares (crown f230, 'whole' f1466); listed L2 glints; one needle glint on the title; everything else L1. No light sweeps at the climax."),
 ("Monotony of face-on trucking", "Grammar varied: macro in S01 and S11; the war's F2 oblique crane; locked frames in the silences (S11, S13, S17, S22); push-ins on emotional beats (S04, S09); border detail in S06; the bass pull-back; the 10-deg rostrum tilt (S20-S21); the crane. Trucks remain only where the strip must be read."),
 ("p1 repeated", "The second copy differs at first glance by light and age (one guttered candle low on the left, Act II re-dye, a tideline, stitched candles and goblets reduced to needle holes) and is an event: the king is unpicked live (S09)."),
 ("Page square to the lens without a reason", "The leaf is a separate parchment leaf tacked in by the gold couching and sewn along its bottom edge; on 'remembered' the couching is pulled and it hinges up, leading the crane by 4-6 deg (visibly foreshortened), parallel by f1760 and on the card's parchment rect at f1766."),
 ("f1760 vs tilt completion", "Crane within 0.3 deg of the menu camera by f1760 and exact at f1766; all pieces settled by f1760; the convergence dissolve ends f1798."),
 ("Title pacing", "First stroke f1799-1801, C-h-r-o-n-i-c-a f1801-1846 (~5.6 frames per letter), last stitch on 'you?' f1846; ornaments f1855-1900."),
 ("Pull-back before the bass (f1240)", "S16-S17 hold (1 px/frame); the exponential pull-back launches on f1283 with a 6-frame ease-in, cruising by 'dark' f1292."),
 ("Trapezoid footprint at zero tilt", "PoC input: overscanned top-down UI-free plate, or a procedural R25 board extension; S22 is framed on the exact E4 zero-tilt pose."),
 ("Projection smear under rising pieces", "Pieces-hidden plate for the ground; rising pieces keep OBJ + stitch materials until the convergence f1756-1798."),
 ("4.5 m of procedural art", "Gate G1 (one kit, S02 proved against p1 first) and divider splices; the war strip is war_bg re-embroidered, not new art."),
 ("E4 cost", "45 hero renders (~75 min) after static spans became ratio-blended stills; 105 hero renders spare."),
 ("S01 pull-back speed", "Real Eevee macro with real motion blur; centre < 8 px/frame; edges peak ~54 px/frame under blur; 8x over 74 frames."),
 ("Audio tail", "Recommend a 0.5 s gain ramp on the mix tail (f1968-1983) to hide the -48 dBFS cut-off during the hold."),
 ("Final plate missing nameplates/shields", "f1855-1983 are built per bucket from a native capture with only the card interior inpainted; nameplates and shields settle in during the f1772-1798 dissolve; verified on device."),
 ("Candles flickering to the end", "Flames settle to exactly the sprite art and every animated layer is zero from f1929; f1929-1983 identical."),
 ("Card screen-aligned vs a 66-deg camera", "Solved by the lectern: the leaf converges to the image plane by f1760 and lands at f1766."),
 ("Burn-through reveals a pristine layer", "The burn reveals the dark walnut beneath (the splice); the scorch and soot persist as ageing into S15-S18."),
 ("Hearth light through the weave", "The firelight is the hearth: a low grazing key from the bottom edge of frame."),
 ("Four goblets, not five", "Four goblets everywhere."),
 ("R25 material must-fixes", "Gates G2-G11 (metal environment term, fuzz, void, lift policy, whorls, LOD/shimmer, stitch-on order, unpick, panel bakes, colour/practicals)."),
]

MERGE_GRAFTS = [
 ("table", "Practical light as the editor, now with real practicals only: the candle lit for 'table', guttering on 'died', carried over the crown, dying on the f797 collapse; the hearth in the near-silence; dawn through the window on 'Now'; the desk's candles relit on f1664 and f1707."),
 ("table", "On 'borders' one road becomes four realm rings in the game's border idiom, with the game's quilted fog-of-war kit over the forgotten land (S16), peeled away by the dawn (S19)."),
 ("table", "The king unpicked live during 'and every lord...', crown left hanging (S09); ghost underdrawn crowns, layered with the frieze's travelling crown shadow (S10)."),
 ("table", "The real linen burning ('consumed by what it depicts', S14); capitonnage as the board's swelling mechanism (S23-S24); drypoint ruling on the blank page on 'page' and 'you?'; poster-frame advice and the f1983 difference test."),
 ("scale", "The needle drawing the gold thread up through the linen on 'There' f5 (S01) and the crown taken exactly on the f797-798 collapse (S11), on one shared Eevee macro rig."),
 ("scale", "'Scale follows the music' as a rule: macro on the quietest passages (S01, S11), held frames in the silences, the decisive gestures on the bass entry and the climax."),
 ("scale", "A blank world as well as a blank page: the hex underdrawing running unstitched to the end of the roll (S20-S22); the 0.5 s audio-tail ramp; 55 identical final frames."),
 ("table/scale", "The war opened low over the cloth in grazing hearth light, rising to reveal the war strip (S12), now from F2 rather than macro."),
 ("bake-off", "Displaced-mesh Eevee from R25 maps for every 3D insert; stand-up figure slips (~70 deg) with tethers snapping one by one; fold/drape field; metal environment term; embroidery-in-progress frontier with underdrawing; couched-gold-over-padding crests; Legion crimson livery; protected unfaded linen under lifted pieces; risen banner sway at the 2.115 s pulse."),
]

MERGE_REJECTED = [
 "Scale's eye-level miniature glide, dolly-zoom dive and tilt-shift miniature DOF (cliche risk, breaks the 25-deg rule, heaviest 3D).",
 "Scale's climax inside a Blender-to-Godot cross-match and demo-mode zoom animation (unverified).",
 "Table's menu chrome visible from frame 4 (spoils the final reveal); the desk exists only from f1612, in darkness.",
 "Table's 12-frame title stitch, its 60 px/frame hidden truck and its soldier-height tracking shot.",
 "Card dropping in from above the lens as a UI panel (literal; replaced by the leaf rising into its frame).",
 "Linen cross-fading into parchment (the leaf carries the parchment albedo from its first frame).",
]

FRIEZE_LAYOUT = [
 ("1", "Incipit + one realm", "~800", "hem, nail holes, the gold chronicle thread and its first tie-down; Bayeux landscape from the kit; four towns of different sizes from settle_* elevations; the four-colour road climbing to a capital right of centre; off-centre lion border beasts from vignette_red/blue", "S01-S02"),
 ("2", "T1 interlace tree", "~60", "trunk banded in the four house colours (splice)", "S02"),
 ("3", "p1 OATH", "550", "p1_oath re-embroidered by R25 at 10 px/mm; its four baked flame glows inpainted; faces kept at <= 1.0x native", "S03-S06"),
 ("4", "T2 night tree", "~60", "dark woad bands (splice)", "S06"),
 ("5", "p3 DEATH", "550", "p3_death re-embroidered; one stitched flame unpicked", "S07"),
 ("6", "SINE HEREDE strip", "~150", "underdrawn heir between two couched bars; the only titulus", "S08"),
 ("7", "T3 winter tree", "~60", "leafless, blue-black (splice)", "S08"),
 ("8", "p1' THE EMPTY CHAIR", "550", "the p1 maps again: Act II re-dye, tideline, stitched candles and goblets reduced to needle holes, king unpicked live, crown slip on tethers", "S09-S10"),
 ("-", "(dark splice f820)", "-", "hidden in the near-silence after the crown macro", "S11"),
 ("9", "WAR strip -> hole field", "~800", "war_bg re-embroidered (violet sky bands re-dyed madder / woad-grey) + 16 figure slips; aged by the century's light arc; needle-hole field", "S12-S13"),
 ("-", "(burnt hole, dark splice f988-997)", "-", "the real linen burns through to the walnut table", "S14"),
 ("10", "p6 RUIN", "550", "p6_ruin re-embroidered: banded madder / woad-grey / buff sky, fire in 3 laid-flame lots; scorched margins", "S14"),
 ("11", "charred tree + FOREST over the road", "~700", "kit trees over the S02 road (rhyme)", "S14-S15"),
 ("12", "FOUR TOWNS / borders", "~780", "four unequal towns, couched bars, four realm rings (the green one late), fog quilts hinged at the bars", "S16-S17"),
 ("13", "RENEWAL end", "~600", "the four crests in the upper border at irregular heights; mended edges", "S19"),
 ("14", "UNWRITTEN REMAINDER", "open", "fresh linen with ink hex underdrawing = the seed-4242 board layout; the banner and the village (Bayeux elevations that pop up); the parchment leaf", "S20-S26"),
]

SYNC_MAP = [
 ("0-3", "digital silence", "dim pre-bloom still (= poster)"),
 ("4-5", "drone + 'There' (strongest attack)", "window light blooms; the needle breaks through"),
 ("39", "'world'", "thread taut; first tie-down; pull-back begins f40"),
 ("62-72", "-", "registered E0 -> R25 crossfade on the frontal pose"),
 ("91", "'realm'", "the one realm revealed (pull-back easing out)"),
 ("104-125", "gap", "the landscape breathes by light alone"),
 ("140", "'table'", "a real candle lit off-frame left (f134-146); its pool blooms"),
 ("173", "'oath'", "pool steady on the hands on the sword"),
 ("185-198", "near-silence", "hold"),
 ("230", "'crown'", "METAL FLARE 1 of 2 (f224-236)"),
 ("285 / 308", "'raised' / 'cups'", "goblets peel up (f283-292) / hang"),
 ("349", "'swore'", "goblets settle; the camera rises to the border"),
 ("391", "'end'", "the gold thread runs on out of frame"),
 ("402-446", "1.46 s gap", "the window fades; the candle alone; T2 splice"),
 ("469", "'died'", "the real candle gutters (-0.5 EV); a stitched flame is unpicked (f465-471)"),
 ("522 / 548", "'heir' / drone gone", "underdrawn heir, SINE HEREDE"),
 ("561-640", "'and every lord ... table'", "the king unpicked live"),
 ("669", "'chair'", "push lands on the king-shaped void"),
 ("741 / 753 / 766 / 778", "'own' / 'head' / 'beneath' / -", "crown shadow on gold / red / (void f758-761) blue / green; ghost crowns"),
 ("784", "one frame before 'crown.' f785", "HARD CUT to the crown-slip macro"),
 ("786-797", "'crown.'", "tethers pop one by one"),
 ("797-798", "music collapses -20 dB", "the crown is yanked out; the candle dies"),
 ("820", "near-silence", "dark splice to the war strip"),
 ("832", "near-silence", "the hearth glow rises"),
 ("844-877", "'The wars' f844 / f850", "slow crane F2 -> F1 at the 22-deg oblique"),
 ("867", "'lasted'", "the slips' stitches tauten"),
 ("878-896", "'hundred' f884", "slips stand up into strike poses, tethers snap"),
 ("899-917", "'years'", "the century: one slow light arc + ageing"),
 ("912-936", "'and' f918 / 'ended' f925", "crane back to face-on; soldiers topple (f925-936)"),
 ("936-941", "-", "registered E1 -> R25 swap on the static pose"),
 ("942", "'nothing'", "every figure unpicked at once"),
 ("952-979", "near-silent gap", "needle-hole field, grazing light, locked"),
 ("982 / 999 / 1015", "'Cities' / 'fell' / 'ruin'", "real burn-through / courses unpicked + one tower peel / banner slumps"),
 ("1017", "pad returns", "stitched flames re-stitch taller; the real burn eats the margins"),
 ("1051 / 1101", "'Roads' / 'forest'", "one needle leads the forest over the road / road gone"),
 ("1149 / 1211 / 1220", "'forgot' / 'borders' / -", "bars wall the strip / three rings closed / the green ring closes late"),
 ("1263-1282", "'world grew'", "held breath; nothing launches"),
 ("1283", "BASS ENTRY (+26 dB)", "exponential pull-back launches"),
 ("1292 / 1319", "'dark' / 'edges'", "the hearth embers die / fraying reaches the register, -2.5 EV"),
 ("1345", "bass pulse #2", "surviving gold glint pulses"),
 ("1372", "in-gap swell", "pre-dawn lift"),
 ("1382", "'Now'", "dawn through the window, sweep L->R begins"),
 ("1410", "bass pulse ('ruler')", "the last frayed edge re-weaves"),
 ("1466 / 1471", "'whole' / bass", "METAL FLARE 2 of 2: thread re-couched end to end"),
 ("1491-1523", "Bb horn gap", "four crests stitch on at f1493, 1500, 1511, 1517"),
 ("1524-1540", "'One'", "rostrum tilts 0 -> 10 deg"),
 ("1536", "bass pulse ('banner')", "banner hinges up (stitches tauten from f1527)"),
 ("1569", "'village'", "village pops up (f1563-1577)"),
 ("1599", "bass pulse ('one')", "thread runs down to the leaf; tilt returning to zero"),
 ("1612", "-", "zero-tilt pose; the desk exists from here, unlit; qa/swap f1612/1613"),
 ("1630", "'page'", "thread half-way down the right edge; drypoint catches the light"),
 ("1645", "-", "the thread rests at the leaf's corner"),
 ("1664", "bass pulse", "left candle lit, desk revealed on the left; board wavefront starts at Grandbois"),
 ("1707", "'age'", "right candle lit"),
 ("1719", "-", "last hex closes"),
 ("1720-1725", "-", "registered R25 -> E4 swap on the static board"),
 ("1726", "bass pulse ('remembered')", "couching pulled; leaf lifts ahead of the crane; crane starts; pieces start rising"),
 ("1755", "bass swell", "valance unrolls (to f1782)"),
 ("1760", "CLIMAX PEAK", "pieces settled; crane within 0.3 deg; leaf parallel"),
 ("1766", "-", "crane exact; leaf on the parchment rect"),
 ("1772-1798", "recession", "convergence dissolve to the native capture"),
 ("1799-1801", "'the' f1797", "needle point through the valance; first stroke"),
 ("1801", "'chronicles'", "C-h-r-o-n-i-c-a couched to f1846, ~5.6 frames per letter"),
 ("1846", "'you?'", "last stitch, the title's only needle glint; ruling catches the light"),
 ("1855-1900", "ring-out", "ornaments couched; exact art by f1906"),
 ("1928", "ring-out", "flames at the exact sprite art"),
 ("1929", "ring-out tail", "lock; the overlay opens the engine gate"),
 ("1929-1983", "ring-out tail, micro-fade f1982", "identical locked frames = live no-save menu minus card text"),
]

RISKS = [
 ("Style seam between re-embroidered AI panels and procedural Bayeux sections", "One R25 renderer, one linen ground, continuous procedural borders over every section, shared fuzz/ageing; gate G1 proves S02 beside p1 first; panel faces kept at <= 1.0x native or in shadow."),
 ("Board world positions for seed 4242 not recoverable", "Solve from the plate with the known camera; fallback plate-only 2.5D lift in the PoC."),
 ("Overscanned top-down plate not possible in demo mode", "Extend the board procedurally beyond the menu footprint with R25 kit hexes matched per terrain class."),
 ("The desk reads as an overlay", "It exists only from f1612, in darkness, never brighter than what it covers until its own candles light it (G14); it never moves except the valance unroll; fallback: keep it dark until the convergence dissolve."),
 ("Leaf lectern looks unmotivated or like a UI card", "Its couching is visibly pulled, its sewn hinge stays, it leads the crane by 4-6 deg with real foreshortening and a widening contact shadow; fallback in the PoC section."),
 ("Returning players and odd aspects", "Matched ending only for no save and an aspect within 0.1 % of a bucket; plain 1.5 s dissolve elsewhere; no autoplay when a save exists."),
 ("Per-bucket workload", "The board, f0-1598 and all hero renders are shared; per bucket only the leaf layer (41 light renders), the S22-S26 R25 leaf/title layers and COMP (~1 h CPU each); the bucket list is frozen after the device measurements, before final renders."),
 ("Photosensitivity", "Rules in section 2; G13 on the master and every encode; the century is one light arc; flicker is local."),
 ("E4 overruns", "45 hero renders at ~95 s fit with 105 spare; if needed, pieces render on twos as a separate layer over a camera-on-ones board."),
 ("War slips at low resolution (288-640 px cards)", "Slips <= 1.5x native on screen; F2 opening on a 20 px/mm near patch; hearth light and DOF; normal maps for relief."),
 ("Busy climax", "S24 holds three events; no sweep, glints or chrome entrances; S25 is nearly still."),
 ("Render contention on 4 shared cores", "408 Eevee renders (363 + 45) + 246 light leaf layers, at most 2 concurrent Blender processes, test renders at 1280x720."),
]

DEPENDENCIES = [
 "Game plates (demo mode, SwiftShader ~20-40 s/frame): UI-free menu-camera plate at 2560x1440 and 2x; pieces-hidden variant; overscanned top-down plate; native first-frame captures of the menu in the no-save state for each aspect bucket.",
 "Decoded main_menu.gd (_layout), ui_theme.gd (9-slice margins) and core/match.gd (Match.has_save paths for the save probe).",
 "Measured innerWidth/innerHeight on the target iPads (Safari with and without bars, home-screen mode) to pin the bucket list.",
 "Seed-4242 hex geometry and world positions of settlements and unit groups.",
 "Exported Blender camera track (E4) for the leaf and the convergence projection.",
 "R25 batch pre-bake of 16 war slips (2 realms x 4 units x idle/strike); tiled bakes of p1/p3/p6 with the glow inpaint and re-dye hints; the 40 px/mm crown slip.",
 "An iPad with Safari for G12 and G13 on decoded frames.",
]

# ------------------------------------------------------------------ JSON
def shot_json(s):
    return dict(id=s["id"], name=s["name"], act=s["act"], start_frame=s["start"], end_frame=s["end"],
                start_s=s["start_s"], end_s=s["end_s"], frames=s["frames"], anchor=s["anchor"], summary=s["summary"],
                audio_event=s["audio_event"], visual_action=s["visual_action"], camera=s["camera"],
                technique=s["technique"], material_behavior=s["material_behavior"], transition_out=s["transition_out"],
                emotional_purpose=s["emotional_purpose"], est_render_cost=s["est_render_cost"],
                eevee=dict(block=s["eevee"]["block"], renders_1080=s["eevee"]["r1080"], renders_1440=s["eevee"]["r1440"]))


WALL = "~306 min single-process (~5.1 h), ~4.2 h with 2 concurrent processes; R25 ~2.5 CPU-h (+ ~1 h per extra aspect bucket); COMP ~15 min per bucket; game plates ~1 h"

doc = dict(
 title=TITLE, version="final",
 base="storyboard_v1 (frieze base + table/scale grafts + relight25d) with all 33 points of the adversarial review applied",
 logline=LOGLINE,
 master=dict(width=2560, height=1440, fps=FPS, frames=LAST + 1, first_frame=0, last_frame=LAST,
             duration_s=round((LAST + 1) / FPS, 3), audio="aaa/audio/audio_master_1984f_s16.wav", frame_convention="frame = floor(t*30)"),
 technique_codes={"R25-F": "relight25d frontal relight from cached stitch maps (5 s/frame with a moving light, 1.26 s camera-only)",
                  "R25-S": "relight25d stitch-on / unpick (stitch_id order, dirty-rect recompute, snapshot re-rasters)",
                  "R25-L": "relight25d frontal slip lift (<= 10 deg off normal, <= 15 mm, PCSS shadow, tethers)",
                  "EV-MR": "Eevee macro rig (block E0): displaced linen patch, thread tubes, needle, real DOF and motion blur",
                  "EV-DM/G": "Eevee render of a displaced mesh built from R25 maps (geometry ground): E1, E4",
                  "EV-DM/P": "Eevee pieces over an R25 plate with shadow-ratio transfer (tilt <= 10 deg): E2, E3",
                  "COMP": "numpy/cv2 compositor: transforms, desk layers, grade, grain, fuzz (every frame)",
                  "GP": "game demo-mode plates and native captures"},
 coverage=dict(shots=len(SHOTS), frames_covered=TOTAL, contiguous=True, first=0, last=LAST),
 shots=[shot_json(s) for s in SHOTS],
 eevee_budget=dict(renders_1080=E1080, renders_1440_hero=E1440, total=E1080 + E1440,
                   limits=dict(renders_1080=600, renders_1440_hero=150),
                   optional_light_layers="246 E4L leaf-layer renders (41 per aspect bucket x 6, ~10 s each)",
                   blocks=RENDER_BUDGET, wall_estimate=WALL),
 six_keyframes=SIX_KEYFRAMES,
 poc=POC,
 through_lines=dict(gold_thread=[dict(shot=a, frames=b, action=c, metal_level=d) for a, b, c, d in GOLD_THREAD],
                    metal_budget=METAL_BUDGET,
                    light_editor=[dict(frames=a, light=b, sound=c) for a, b, c in LIGHT_EDITOR],
                    desk=[dict(topic=a, text=b) for a, b in DESK]),
 colour_script=COLOUR_SCRIPT,
 frieze_layout=[dict(n=a, section=b, width_mm=c, content=d, shots=e) for a, b, c, d, e in FRIEZE_LAYOUT],
 sync_map=[dict(frame=a, sound=b, picture=c) for a, b, c in SYNC_MAP],
 gates=[dict(id=a, rule=b, shots=c) for a, b, c in GATES],
 handoff=[f"{a}: {b}" for a, b in HANDOFF],
 aspect_buckets=ASPECT_BUCKETS,
 risks=[dict(risk=a, mitigation=b) for a, b in RISKS],
 dependencies=DEPENDENCIES,
 rules=[dict(rule=a, text=b) for a, b in RULES],
 critique_responses=[dict(n=n, severity=sev, verdict=v, response=r, where=w) for n, sev, v, r, w in CRITIQUE],
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
A("Final storyboard: storyboard v1 (frieze base, table and scale grafts, relight25d) with every point of the adversarial review applied. "
  "Master 2560x1440, 30 fps, frames 0-1983 (1984 frames, 66.133 s), muxed with `aaa/audio/audio_master_1984f_s16.wav`. Frame = floor(t x 30). "
  "Machine-readable twin: `storyboard_final.json` (same data and the same structure as v1, plus `rules`, `aspect_buckets` and `critique_responses`), "
  "generated by `story/work/gen_storyboard_final.py` from `story/work/sb_final_shots.py`; the generator checks that frames 0-1983 are covered exactly once "
  "and that the Eevee counts fit the budget.\n")
A(f"**Logline.** {LOGLINE}\n")
A("## 1. The film in one paragraph\n")
A("The film is one object: a long embroidered roll-chronicle lying on a walnut table, read left to right like the Bayeux Tapestry, lit only by real "
  "light: a window, the chronicler's candles and a hearth. Story time is carried by what happens to the cloth and to that light. A shutter opens and a "
  "needle draws the first gold thread; the one realm and the oath are stitched; a candle is lit for 'table'. On 'died' the candle gutters as a stitched "
  "flame is unpicked; the king is unpicked out of his own oath and his crown is left hanging on its tethers; the candle, carried round over it, crowns "
  "each lord with its shadow; on 'crown.' the crown is torn away and the candle dies with the music. In near-silence a war of stitched slips stands up "
  "out of the cloth, freezes while one slow light arc ages it by a century, topples and is unpicked into a field of needle holes. The real linen burns, a "
  "forest swallows the road of unity, the road becomes the game's four realm borders under quilted fog, and on the bass entry the camera pulls back to "
  "show the whole chronicle fraying into darkness, one gold glint surviving. Dawn through the window mends it. At its unwritten end one banner and one "
  "village pop up out of the cloth and the gold thread tacks down one blank leaf; the light narrows, and in the dark at the edges stands the chronicler's "
  "desk, which its own candles reveal as the board stitches itself. On the climax the board rises into the live 3D game board seen from the menu camera, "
  "the leaf rises into its reading frame, the valance unrolls, and on 'chronicles' a needle stitches the word Chronica. The last 1.8 s are the live menu, "
  "frame for frame, with the page left blank for the player.\n")

A("## 2. Rules of this film\n")
for a, b in RULES:
    A(f"- **{a}.** {b}")
A("")

A("## 3. Critique responses\n")
A("All 33 points of the adversarial review were checked against the sources (decoded `main_menu.gd`/`device.gd`, `index.html`, the overlay snippet, "
  "p1/p3/p6/war_bg, the audio report, the pipeline decision and the bible) and found valid. None is rejected outright. Five are applied in a modified "
  "form, one is interpreted and three take one of the options the review offered; the reason is given in the row. Two are integrator suggestions only, because the repo is not touched.\n")
A(table(["#", "severity", "verdict", "response", "where"], [[n, sev, v, r, w] for n, sev, v, r, w in CRITIQUE]) + "\n")
A("### 3.1 v1 merge log, carried forward and updated\n")
A(table(["judge must-fix item (drafts)", "final answer"], MERGE_MUST_FIX) + "\n")
A("**Grafts adopted**\n")
A(table(["from", "graft"], MERGE_GRAFTS) + "\n")
A("**Deliberately not grafted**\n")
for r in MERGE_REJECTED:
    A(f"- {r}")
A("")

A("## 4. Frieze layout (reading order)\n")
A("Scale anchor: panel-native 5 px/mm (each AI panel = 550 x 307 mm), R25 bakes at 10 px/mm (2x headroom; 20 px/mm next to macro and the S12 opening; "
  "40 px/mm for the S11 crown slip). F0 = full height 440 mm in 1440 px (3.3 px/mm); F1 = panel width (4.65 px/mm); F2 = one figure (~10-13 px/mm); "
  "F3 = macro. Travel is compressed with divider splices (8-frame match dissolves on an identical tree) and two dark splices hidden in near-black (f820, f988-997).\n")
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
  f"= {E1080 + E1440} (limits 600 + 150), plus 246 light leaf-layer renders (E4L, 41 per aspect bucket). Technique codes: R25-F frontal relight, R25-S stitch-on/unpick, "
  "R25-L frontal slip lift, EV-MR Eevee macro rig, EV-DM/G Eevee on displaced R25 maps, EV-DM/P Eevee pieces over an R25 plate, COMP compositor, GP game plates.\n")

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
A("A couched pair of silver-gilt threads: the only metal besides the crown, the goblets, the needles and the title. It is never broken (only the crown is taken in S11).\n")
A(table(["shot", "frames", "what the thread does", "metal level"], GOLD_THREAD) + "\n")
A("### 7.2 Metal budget\n")
A(f"Levels: {METAL_BUDGET['levels']}\n")
A("- **L3 full flares (two only):** " + "; ".join(METAL_BUDGET["L3_flares"]) + ".")
A("- **L2 glints:** " + "; ".join(METAL_BUDGET["L2_glints"]) + ".")
A(f"- **L1:** {METAL_BUDGET['L1_rule']}\n")
A("### 7.3 Practical light as the editor\n")
A("Every source is real: the window (left), the chronicler's candles, the hearth (below). Embroidery never emits.\n")
A(table(["frames", "light", "sound"], LIGHT_EDITOR) + "\n")
A("### 7.4 The desk\n")
A(table(["", "the chronicler's desk (the menu chrome)"], DESK) + "\n")

A("## 8. Colour script\n")
A("Shot-aligned version of palette.json `acts` (bible section 2.4). Black point never below #07070A, white never above #F3E8D0 (metal glints may touch #FFF3D6 for 1-3 frames, on the two L3 flares only). "
  "Shadows cool-violet (#1A1620, 10-20 %), highlights warm (#FFF0D6). Light colours are applied as 20-50 % tints of the display values (1900 K #FF8400, 2200 K #FF9227, 3000 K #FFB16E, 4300 K #FFD5B3). "
  "Chroma caps (OKLCH) are enforced by qa/clip: narrative fills <= .13 in every act (Act II .12), heraldic <= .20, the real ember rim exempt.\n")
A(table(["act", "frames", "seconds", "shots", "key light", "dominant", "accents", "grade", "colour events"],
        [[c["act"], c["frames"], c["seconds"], c["shots"], c["key"], c["dominant"], c["accents"], c["grade"], c["events"]] for c in COLOUR_SCRIPT]) + "\n")
A("Signature colour moves: the four house colours in one road (S02) become four separate rings (S16); dyes age under one light arc (S12) and revive aged -> fresh behind the dawn (S19); "
  "purple belongs to the king alone and leaves with him (S09); the only saturated orange in the film is a real burn (S14); after f1798 nothing is graded, because the frame must equal the live menu.\n")

A("## 9. Sync map (frame-exact hits)\n")
A(table(["frame", "sound", "picture"], SYNC_MAP) + "\n")

A("## 10. Six keyframes\n")
for i, k in enumerate(SIX_KEYFRAMES):
    A(f"{i + 1}. **f{k['frame']} ({k['frame'] / FPS:.2f} s, {k['shot']}) {k['title']}.** {k['description']}")
A("")

A(f"## 11. Proof of concept: '{POC['title']}'\n")
A(f"**Window:** f{POC['frames'][0]}-{POC['frames'][1]} (183 frames, {POC['duration_s']} s), audio {POC['audio_slice_s'][0]}-{POC['audio_slice_s'][1]} s. {POC['summary']}\n")
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
A("Why this window: it tests, in 6.1 s of frames the film needs anyway, the 2D stitch-on and the 2D -> 3D swap from real stitch maps, the believability of pieces "
  "rising out of the cloth, stitch-scale continuity under a moving 3D camera, the lectern leaf with real foreshortening, the desk revealed by light, the strand-built "
  "title and the per-bucket, on-device hand-off. S12-S13 (war slips) and S20-S22 (banner, village) reuse the same registration trick at lower stakes; the S01/S11 macro "
  "rig is the second, smaller look-dev item (one still at f39 and one at f797 before committing).\n")

A("## 12. Render budget\n")
A(table(["block", "shots", "frames", "Eevee @1080", "Eevee @1440 hero", "settings", "est. wall"],
        [[b["block"], b["shots"], b["frames"], b["renders_1080"], b["renders_1440"], b["settings"], b["wall"]] for b in RENDER_BUDGET]
        + [["**total**", "", "", f"**{E1080}** / 600", f"**{E1440}** / 150", "", "~5.1 h single, ~4.2 h on 2 procs"]]) + "\n")
A(f"- Eevee covers {E1080 + E1440} renders ({round(100 * E1080 / 600)} % of the 1080p limit, {round(100 * E1440 / 150)} % of the hero limit). Static spans of E4 are ratio-blended light-state stills, which frees ~45 hero renders against v1 for retakes. "
  "1080p renders are upscaled with Lanczos and pass through COMP grain/fuzz.\n"
  "- R25 (relight25d, measured at 2560x1440 on 2 threads): ~5 s/frame with a moving light (+1 s per shadowed practical), 1.26 s camera-only from a cached plate, 6-8 s for stitch-on/unpick frames. "
  "Shot estimates sum to ~2.5 CPU-h for the 16:9 master; each extra aspect bucket adds ~1 h (S22-S26 leaf, title and COMP layers). Panel bakes p1/p3/p6: ~15 min of hints + 5-8 min tiled bake each.\n"
  "- COMP: every one of the 1984 frames, ~0.4 s/frame = ~13 min, plus ~3 min per extra bucket. x264/x265 from PNG per bucket, plus the 1080p fallback.\n"
  "- Game plates: UI-free plates and one native capture per bucket in demo mode, ~1 h total.\n"
  "- Frames containing Eevee pixels: f4-72, f784-943, f276-357 (goblets), f1524-1798 (many on twos or held stills); the rest are R25 + COMP only.\n")

A("## 13. Hand-off to the live menu\n")
for a, b in HANDOFF[:3]:
    A(f"- **{a}.** {b}")
A("")
A(table(["bucket", "design aspect", "file", "encode size", "viewports"],
        [[b["id"], b["aspect"], b["file"], b["size"], b["viewports"]] for b in ASPECT_BUCKETS]) + "\n")
A("Matched ending iff |innerWidth/innerHeight - bucket aspect| <= 0.1 % (the layout port predicts every desk edge within 0.5 px there); otherwise the nearest file and the plain dissolve.\n")
for a, b in HANDOFF[3:]:
    A(f"- **{a}.** {b}")
A("")

A("## 14. Production gates\n")
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
