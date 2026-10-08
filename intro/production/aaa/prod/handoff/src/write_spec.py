"""handoff_spec.json: everything downstream shots and the integrator need from the hand-off frame that is not a pixel:
overlay timing, corrected numbers for the storyboard, G12 masks, encode guard, continuity targets, desk-light cue for
4:3, notes for the game team, and what was deliberately NOT applied. Measured numbers are read from the stored reports.

usage: python3 write_spec.py HANDOFF_DIR
"""
import sys, os, json
import numpy as np
from PIL import Image


def card_shadow_probe(hd):
    """Luminance of the sea just right of the card vs further out (16:9): is there a drop shadow on the board?"""
    R = json.load(open(os.path.join(hd, 'report_16x9_2560x1440.json')))
    f = np.asarray(Image.open(os.path.join(hd, 'f1983_16x9_2560x1440.png')).convert('RGB')).astype(np.float64)
    cx, cy, cw, ch = R['card_draw_rect_px']
    x1 = int(cx + cw)
    y0, y1 = int(cy + ch * 0.80), int(cy + ch * 0.95)
    lum = f.mean(2)
    near = lum[y0:y1, x1 + 6:x1 + 26]
    far = lum[y0:y1, x1 + 120:x1 + 220]
    return dict(rows=[y0, y1], near_6_26px_mean_lum=round(float(near.mean()), 2), far_120_220px_mean_lum=round(float(far.mean()), 2),
                ratio=round(float(near.mean() / far.mean()), 3))


def main(hd):
    P = json.load(open(os.path.join(hd, 'polish_report.json')))
    Rs = {t: json.load(open(os.path.join(hd, f'report_{t}.json'))) for t in P}
    sim = json.load(open(os.path.join(hd, 'qa', 'dissolve_ghost_sim.json')))
    enc = json.load(open(os.path.join(hd, 'qa', 'encode_guard_test.json'))) if os.path.exists(os.path.join(hd, 'qa', 'encode_guard_test.json')) else None
    r169, r43 = Rs['16x9_2560x1440'], Rs['4x3_2048x1536']

    def rr(v):
        return [round(x, 2) for x in v]

    c169 = r169['card_draw_rect_px']; c43 = r43['card_draw_rect_px']
    spec = {
        'about': 'KEYFRAME f1983 (S26) hand-off: non-pixel specification, v2 (review polish). Pixel deliverables are in mattes_<bucket>/ and the two keyframes.',
        'frame_choice': {
            'menu_frame': 30, 'game_time_s': 0.5,
            'wording': "Replace 'the live menu's first frame' in S26, section 13 and G12 with 'menu frame 30 (0.5 s after callMain: nameplates settled, camera on its first focus)'. "
                       'f1983 is built on that frame; G12 and the on-device check must compare against the same state.'},
        'overlay_timing': {
            'finding': ("The overlay's engine-ready signal (#status opacity '0' -> finish() in intro_overlay_snippet.html) fires at about menu frame 1. "
                        'Started there, the 0.9 s dissolve runs while the nameplates (Sablon, Grandbois, Hautecouronne) are still popping in larger and offset '
                        '(frames 1 to about 20), so for about 0.3 s, at 40-55 % live opacity, they show ghosted doubles. '
                        "The earlier README sentence 'that is the state the live game shows during the hand-off dissolve' is only true from about frame 20 on."),
            'recommendation': ('finish() waits for at least 30 PRESENTED canvas rAF frames after the engine-ready signal before it starts the 0.9 s dissolve and the 1.2 s '
                               'card wipe. Count frames, not milliseconds: the first iPad frames hitch.'),
            'budget_s': {'wait_30_frames': 0.5, 'dissolve': 0.9, 'card_wipe': 1.2, 'wait_plus_card_wipe': 1.7, 'tour_hold_before_pan': 3.0,
                         'verdict': 'wait + wipe = 1.7 s, inside the 3 s tour hold (the hold starts after callMain)'},
            'evidence': {'what': sim['model'], 'result_table': sim['table'], 'crops': 'qa/' + os.path.basename(sim['crops'].split(' ')[0]),
                         'caveat': sim['caveat'],
                         'not_done': 'The real overlay was NOT run through the deterministic-clock harness (about 6 min per frame at 1440p, and the overlay build is not in this stage). '
                                     'The proof by capture is open: run it with the 30-frame wait and capture 4-5 mid-dissolve frames, then G12 on device.'},
            'fallback_if_the_wait_is_refused': 'Rebuild f1983 on the live frame that matches the dissolve midpoint instead of frame 30 (one command: make_all.sh with FRAMES=<n>).'},
        'storyboard_corrections': {
            'owner': 'orchestrator / storyboard owner (this stage does not edit the storyboard)',
            'card_minimum_size_base_units': {'was': [627, 661], 'is': [629, 665], 'note': "holds at three scales (fitted on 2560 and 2048 captures, checked on the 1920x1080 reference: frame edges at 134.2/770.8/195.4/861.25 base units); 'card is 661 base px high' becomes 665; the 'tall' test still holds"},
            'B169_2560x1440': {
                'six_keyframes_f1983_card': {'was': '(224,319)-(1227,1376)', 'is': f'({c169[0]},{c169[1]})-({c169[0] + c169[2]:.2f},{c169[1] + c169[3]:.2f})'},
                'section_13_menu_card': {'was': '(224,318.7,1003.2x1057.6)', 'is': rr(c169)},
                'parchment_interior_S24_f1766_leaf_target': {'was': '(272,357.3,910.7x976)', 'is': rr(r169['parchment_field_px']), 'tolerance_px': 0.5,
                                                              'note': 'the visible field inside the inner dark line (what the leaf must cover); the leaf lands UNDER menu_card_frame.png'}},
            'B133_2048x1536': {
                'section_13_menu_card': {'was': '(179,255,803x846)', 'is': rr(c43)},
                'parchment_field': rr(r43['parchment_field_px'])},
            'other_buckets': 'menu_layout.layout(W, H, card_min=(629, 665)) and draw_rects(); confirm each with fit_card.py on a native capture.',
            'title_baseline_and_rule (storyboard line 390, critique #31)': {
                'B169': {'title_baseline_y_px': P['16x9_2560x1440']['geometry']['title']['baseline_y_px'], 'rule_centre_y_px': P['16x9_2560x1440']['geometry']['rule']['centre_y_px']},
                'B133': {'title_baseline_y_px': P['4x3_2048x1536']['geometry']['title']['baseline_y_px'], 'rule_centre_y_px': P['4x3_2048x1536']['geometry']['rule']['centre_y_px']},
                'note': 'in base units both buckets agree (title baseline 300.6-300.8, rule centre 418.7); every band and rect is in mattes_<bucket>/rects.json -> content_geometry'}},
        'desk_light_cues': {
            'B133_chamberstick': ('The 4:3 table edge carries a third lit flame (the chamberstick) that no desk-light cue covered (left candle f1664, right candle f1707, G14). '
                                  'Suggested: light it with the left candle at f1664 so the 4:3 desk reveal reaches f1983 without a flame popping on. '
                                  'Layers: table_edge_bottom_unlit / _flame / _flame_core / _waxglow, exact residual (see README).')},
        'g12': {'mask_png': 'mattes_<bucket>/units_water_g12_mask.png (255 = exclude)',
                'derivation': P['16x9_2560x1440']['g12']['rule'],
                'B169': {'mask_fraction_of_frame': P['16x9_2560x1440']['g12']['mask_fraction_of_frame'], 'outlook': P['16x9_2560x1440']['g12']['g12_outlook_outside_card']},
                'B133': {'mask_fraction_of_frame': P['4x3_2048x1536']['g12']['mask_fraction_of_frame'], 'outlook': P['4x3_2048x1536']['g12']['g12_outlook_outside_card']},
                'also_exclude': 'text (nameplates), flames, card interior (as in the storyboard G12 definition); the mask already covers nameplate pop-in where the 16:9 frame-3 capture shows it'},
        'encode_guard': {
            'risk': ('The blank parchment field is the game 260x340 texture stretched about 3.9x: extremely low-frequency (2 px high-pass std about 0.45/255, about 37 luma levels across the field). '
                     'It is the area most likely to band or macroblock in an 8-bit H.264 delivery, especially during the S24-S26 dissolve.'),
            'recommendation': ('Encode the master at 10-bit (HEVC Main10 / H.264 High10 where the target decodes it) or, for 8-bit H.264, tune=grain or film with high AQ strength; '
                               'add the field to the G12 check on the ENCODED file (device-decoded), not only the PNG. Do NOT add grain to the master PNG: that would break the bit match with the live game.'),
            'colour': 'Flag the shipped encode BT.709 (primaries, transfer, matrix), range matched to how the game presents on device (tv in the storyboard; verify the mapping on device).',
            'measured_once': enc,
            'reading_of_the_measurement': ('One still, three settings at CRF 18: none collapsed the field levels (37 -> 36-37) or raised the largest 24 px block step (4.4 -> 4.2-4.6), '
                                           'but every setting moved the field by a mean 1.8-2.7/255 (max 7-9) and the 8-bit settings added high-pass energy (0.45 -> 0.65-0.69); the 10-bit run was not better on mean error. '
                                           'So this test neither proves banding nor clears the risk: it shows the field is not untouched by the encode. The dissolve frames and the ~6 Mb/s cap were not tested.')},
        'downstream_continuity': {
            'parchment_target_for_S24_S25': {'B169': P['16x9_2560x1440']['parchment'], 'B133': P['4x3_2048x1536']['parchment']},
            'light_target': {'card_shadow_probe_B169': card_shadow_probe(hd),
                             'reading': 'The game frame has flat, even lighting with no raking light and no measurable card drop shadow on the board (ratio of the sea just right of the card to the sea 120-220 px out is close to 1). '
                                        "The cinematic's raking light and any card shadow must be fully graded out by the start of the dissolve."}},
        'colour_metadata': {'pngs': 'v2 deliverables carry an sRGB chunk (intent 0) inserted without recompression; pixels are unchanged (keyframe identical to the v1 file). '
                                    'The native captures in capture/ are left byte-identical to what Playwright wrote (untagged = sRGB).',
                            'matte_alpha': 'straight (non-premultiplied)', 'blend': 'sRGB-space over (Godot Compatibility)'},
        'game_team_notes_out_of_scope': [
            "4:3 (the main iPad platform): the 'Hautecouronne' nameplate is clipped at the right frame edge and partly hidden behind the right candle in the menu-camera framing.",
            'The frozen white floe and fish sprites in the lower sea read as stray paper scraps in a still; a cinematic that matches the menu pixel for pixel cannot fix either.',
            'Both are live game art / menu-camera composition (the repo is read-only here): pass them on as 4:3 composition notes.'],
        'not_applied': [
            {'item': 'Mid-dissolve captures through the real overlay (review 3, P1 proof)', 'why': 'needs the overlay build and about 6 min per frame at 1440p; replaced by the arithmetic simulation, clearly labelled'},
            {'item': 'Inpainting the airborne fish, or choosing a fish-free frame (review 2, P3, optional)', 'why': 'keeps the literal bit match with the live frame; the fish are live art; revisit if the client prefers a calmer poster'},
            {'item': 'Grain on the master PNG (review 1, P3)', 'why': 'would break the bit match; the guard is on the encode instead'},
            {'item': 'Valance letter / ornament inpainting for S24-S26', 'why': 'out of scope for this stage (unchanged from v1)'},
            {'item': 'Editing storyboard_final.md', 'why': 'owned elsewhere; corrections are listed above for the orchestrator'}],
    }
    json.dump(spec, open(os.path.join(hd, 'handoff_spec.json'), 'w'), indent=1)
    print('handoff_spec.json written;', 'card shadow ratio', spec['downstream_continuity']['light_target']['card_shadow_probe_B169']['ratio'])


if __name__ == '__main__':
    main(sys.argv[1])
