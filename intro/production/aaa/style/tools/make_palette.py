"""Builds style/palette.json and style/palette.png for the CHRONICA intro.
Run: python3 make_palette.py  (no args). Pure numpy/PIL."""
import json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

STYLE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES = os.path.join(STYLE, 'work', 'game_samples.json')

# ---------- colour maths (sRGB <-> OKLab) ----------
def srgb2lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def lin2srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055) * 255
def hex2rgb(h): h = h.lstrip('#'); return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
def rgb2hex(c): return '#%02X%02X%02X' % tuple(int(round(float(x))) for x in np.clip(c, 0, 255))
def lin2oklab(l):
    M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566], [0.0883024619, 0.2817188376, 0.6299787005]])
    M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099], [0.0259040371, 0.7827717662, -0.8086757660]])
    return M2 @ np.cbrt(M1 @ l)
def oklab2lin(lab):
    M2i = np.array([[1, 0.3963377774, 0.2158037573], [1, -0.1055613458, -0.0638541728], [1, -0.0894841775, -1.2914855480]])
    M1i = np.array([[4.0767416621, -3.3077115913, 0.2309699292], [-1.2684380046, 2.6097574011, -0.3413193965], [-0.0041960863, -0.7034186147, 1.7076147010]])
    return M1i @ ((M2i @ lab) ** 3)
def hex2oklch(h):
    L, a, b = lin2oklab(srgb2lin(hex2rgb(h)))
    return [round(float(L), 3), round(float(math.hypot(a, b)), 3), round(float(math.degrees(math.atan2(b, a)) % 360), 1)]
def oklch2hex(L, C, H):
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    return rgb2hex(lin2srgb(oklab2lin(np.array([L, a, b]))))
def deltaE_ok(h1, h2):
    return round(float(np.linalg.norm(lin2oklab(srgb2lin(hex2rgb(h1))) - lin2oklab(srgb2lin(hex2rgb(h2))))) * 100, 1)
def rel_lum(h):
    l = srgb2lin(hex2rgb(h)); return float(l @ [0.2126, 0.7152, 0.0722])
def contrast(h1, h2):
    a, b = sorted([rel_lum(h1), rel_lum(h2)], reverse=True); return round((a + 0.05) / (b + 0.05), 2)
def kelvin_rgb(K):  # Tanner Helland blackbody fit, sRGB-ish display colour of a light source
    t = K / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return rgb2hex([r, g, b])

def C(hexv, **kw):
    d = {'hex': hexv.upper(), 'oklch': hex2oklch(hexv)}
    d.update(kw); return d

# ---------- 1. historical Bayeux dye palette ----------
# Ten original colours per Lewis & Gameson (Durham, after Bedat & Girault-Kurtzeman 2004 and the
# Jan-2020 hyperspectral study).  'aged' = best-effort appearance today under ~3000K museum light,
# white-balanced (ESTIMATED from published photography, not instrument-measured: treat +-6 dE_ok).
# 'fresh' = plausible as-dyed appearance on wool (reconstruction for an 'awakening' beat).
historical = {
  'madder_light_terracotta': C('#B65E43', dye='madder (Rubia tinctorum), alum mordant', fresh='#C8492C',
      desc='Red, light, tending to pink-orange', bayeux_use='horses, garments, ship strakes, lettering (red-brown variant), borders'),
  'madder_dark_redbrown': C('#7A3B2C', dye='madder + unidentified organic brown', fresh='#8A2A1C',
      desc='Red, dark, tending to brown', bayeux_use='inscriptions (alternative to blue-black), outlines, hair, shadows of garments'),
  'weld_mustard': C('#BF9446', dye='weld (Reseda luteola) + organic brown', fresh='#D9A92E',
      desc='Yellow of a brown or mustard hue', bayeux_use='horses, garments, tree trunks, border beasts'),
  'weld_beige': C('#D2BC8A', dye='weld (light)', fresh='#E6CC6A',
      desc='Beige / buff', bayeux_use='horses, garments, fills that must read lighter than the ground'),
  'green_light': C('#9AA06A', dye='indigotin over-dyed with weld', fresh='#8FAE4E',
      desc='Green, light', bayeux_use='foliage, garments, horse legs (far side)'),
  'green_olive': C('#6C7044', dye='indigotin + weld', fresh='#5E7A2C',
      desc='Green, olive-toned', bayeux_use='water lines (paired wavy lines), hillocks, foliage'),
  'green_dark': C('#3D4A36', dye='indigotin + weld + organic brown', fresh='#2F5232',
      desc='Green, dark', bayeux_use='outlines, mail-coat hatching, tree canopies'),
  'woad_blue_mid': C('#557489', dye='indigotin from woad (Isatis tinctoria)', fresh='#2F5F9E',
      desc='Blue, mid-toned (fades most: woad dyes the fibre surface only)', bayeux_use='horses, garments, hair, ship strakes'),
  'woad_blue_dark': C('#30465E', dye='indigotin (more dips)', fresh='#1F3A6E',
      desc='Blue, dark', bayeux_use='garments, outlines, shields'),
  'woad_blue_black': C('#25293A', dye='indigotin (saturated, many dips)', fresh='#151B33',
      desc='Blue-black (near black)', bayeux_use='MOST inscriptions, main outlines, eyes, details'),
}
ground = {
  'linen_ground_lit': C('#DCCCA8', desc='bleached linen tabby, aged/yellowed, in light'),
  'linen_ground_mid': C('#CDB990', desc='typical ground under museum light'),
  'linen_ground_shadow': C('#A99470', desc='in crease / under raking shadow'),
  'linen_backing_old': C('#C7B48C', desc='19th-c. backing cloth showing through holes (numbered scenes inked on it)'),
  'restoration_19c_faded': C('#E2DBC6', desc='19th-c. repairs (synthetic dyes) faded nearly white'),
  'restoration_19c_blue_to_green': C('#8FA08C', desc='19th-c. repair blues that have turned green'),
}

# ---------- 2. game sampled colours ----------
game = json.load(open(SAMPLES))
game = {k: {kk: (vv.upper() if isinstance(vv, str) else vv) for kk, vv in v.items()} for k, v in game.items()}

# ---------- 3. cinematic palette (reconciled) ----------
# Rule: hues come from the Bayeux dye families; heraldic/identity elements are pushed toward the
# game's saturated values (crests, banners, title); narrative fills stay within the dye gamut.
cine = {
  # ground & ink
  'linen_hi':      C('#E6D7B6', role='linen ground, lit / bare "flesh"', cap='<=60% of frame', src='between bayeux linen_lit and game menu_card parchment'),
  'linen':         C('#D4BE98', role='linen ground base (== game millefleurs ground)', src='game linen(millefleurs).mid #D4BE97'),
  'linen_lo':      C('#B49C74', role='linen in shadow / creases / stain halo'),
  'linen_deep':    C('#7E6A4C', role='deepest crease, hole edge, shadow under raised work'),
  'ink_blueblack': C('#22232F', role='outlines & Latin tituli (primary)', src='bayeux woad_blue_black, darkened'),
  'ink_redbrown':  C('#6E3326', role='secondary tituli / warm outlines', src='bayeux madder_dark ~ game red_lion.mid #723223'),
  'outline_warm':  C('#2B170D', role='halo outline around heraldic padded work (game crest style)', src='game crests shadow ring'),
  # identity colours (game)
  'navy':          C('#15223A', role='navy field (title cloth, night, Merchants/Knight)', src='game navy(logo_title).mid #101B2E lifted'),
  'navy_hi':       C('#2A3F64', role='navy highlight / damask sheen'),
  'navy_deep':     C('#080D17', role='navy shadow, near black'),
  'gold_hi':       C('#F8D57C', role='gold wool/floss highlight (spec tint)', src='game gold highlight #FCD577/#FBE690'),
  'gold':          C('#D79A33', role='gold base (title letters, crowns, borders)', src='game gold mid #C47E23..#DD9D2A'),
  'gold_lo':       C('#97591A', role='gold shadow'),
  'gold_deep':     C('#5A300C', role='gold core shadow / outline'),
  'metal_gold_f0': C('#E9BE6A', role='couched metal (silver-gilt) thread base colour, metallic=1', note='use ONLY on crown, title, oath sword hilt'),
  'crimson':       C('#A3181A', role='heraldic crimson (Legion, banners, blood-red sky)', src='game crimson mid #A10709 desaturated slightly'),
  'crimson_hi':    C('#CC3A2C', role='crimson lit'),
  'crimson_deep':  C('#56100E', role='crimson shadow'),
  'royal_blue':    C('#1F4E96', role='heraldic blue (Merchants)', src='game royal_blue mid #0B3E93'),
  'royal_blue_hi': C('#3F72BE', role='royal blue lit'),
  'heraldic_green':C('#1E6440', role='heraldic green (Nomads)', src='game green mid #13673F'),
  'heraldic_green_hi': C('#3A8C63', role='heraldic green lit'),
  'builders_ochre':C('#CB7A1C', role='heraldic orange-ochre (Builders)', src='game orange mid #CE760B'),
  'royal_purple':  C('#4E2F5E', role="king's robe / funeral (exists in panels p1/p3; NOT a Bayeux dye: justify as madder+woad over-dye)", src='panels p1/p3 #4C3858/#584362'),
  'royal_purple_hi': C('#71508A', role='purple lit'),
  # narrative (dye-gamut) colours
  'terracotta':    C('#B65E43', role='non-heraldic reds: horses, roofs, ship strakes (Bayeux madder light)'),
  'madder_dark':   C('#7A3B2C', role='hair, wood, dark reds'),
  'mustard':       C('#C3963F', role='yellows in narrative fills (Bayeux weld mustard)'),
  'buff':          C('#D6BE86', role='light fills that must separate from linen'),
  'sage':          C('#98A068', role='light foliage'),
  'olive':         C('#6E7343', role='water lines, hills, forest mid (== game archer green highlight #6F7340)'),
  'forest':        C('#34432F', role='forest dark, encroaching woods'),
  'woad':          C('#4F6F8A', role='narrative blues (horses, cloaks, distant hills)'),
  'woad_dark':     C('#2D4460', role='dark narrative blue'),
  'flesh_fill':    C('#E2C7A2', role='optional face fill (Bayeux leaves faces bare linen: prefer linen_hi + ink outline)'),
  'flesh_line':    C('#7A4632', role='face features / skin outline when not blue-black'),
  # elements
  'fire_core':     C('#F6B54A', role='flame core (laid strands, gold-adjacent)'),
  'fire':          C('#DE6A2C', role='flame body', src='panel p6 #D56436'),
  'fire_outer':    C('#A5321F', role='flame edge', src='panel p6 #A53929'),
  'ember':         C('#5E1B13', role='ember / scorched'),
  'smoke_hi':      C('#7A7370', role='smoke spiral light (stem-stitch spirals)'),
  'smoke':         C('#4A4547', role='smoke'),
  'smoke_deep':    C('#26222A', role='smoke dark'),
  'night':         C('#141325', role='night sky field (p3)', src='panel p3 #1A152A'),
  'night_deep':    C('#09090F', role='night shadow'),
  'dusk_sky':      C('#6A3A38', role='war-sky band (p6)', src='panel p6 #62403F'),
  'steel':         C('#B9BCC2', role='blades, mail (grey wool; or silver thread with metallic 0.6)'),
  'steel_lo':      C('#6D717A', role='steel shadow'),
  # ageing overlays (use as multiply/overlay tints, not opaque paint)
  'foxing':        C('#9C7046', role='foxing spots, multiply 15-35%'),
  'tideline':      C('#7C5A38', role='water-stain ring edge, multiply 20-40%'),
  'wax':           C('#EFE6CC', role='candle-wax drip (glossy, roughness 0.25)'),
  'soot':          C('#3A3330', role='scorch / soot, multiply 30-70% (ruin act)'),
}

# ---------- 4. per-beat colour script (timings from words.json narration) ----------
acts = [
  dict(id='I_oath', t=[0.0, 14.4], text='one realm, one table, one oath, one crown / raised their cups',
       dominant=['linen', 'gold', 'terracotta'], accents=['crimson', 'royal_blue', 'heraldic_green', 'builders_ochre', 'royal_purple'],
       light=dict(key_K=3000, key_elev_deg=22, fill_ratio='1:3', practicals='candles 1900K flicker 4-9 Hz, amplitude 6-12%'),
       grade=dict(sat=1.0, chroma_cap=0.17, lift='#100C08', gamma=1.0, gain='#FFF4E2'),
       note='Unity: all four house colours present and balanced; warm, generous light; gold dominant accent.'),
  dict(id='II_death', t=[14.4, 27.4], text='the king died... saw his own head beneath the crown',
       dominant=['night', 'royal_purple', 'linen_lo'], accents=['gold', 'metal_gold_f0'],
       light=dict(key_K=1900, key_elev_deg=12, fill_ratio='1:6', practicals='2-4 candles only'),
       grade=dict(sat=0.7, chroma_cap=0.12, lift='#08080E', gamma=0.95, gain='#FFE9CF'),
       note='Single gold accent (the crown) carries the eye; everything else desaturates; empty chair = bare linen hole in the composition.'),
  dict(id='III_war_ruin', t=[27.4, 45.5], text='wars lasted a hundred years / cities fell / roads swallowed by forest / world grew dark at its edges',
       dominant=['dusk_sky', 'crimson_deep', 'smoke', 'forest'], accents=['fire', 'fire_core', 'crimson_hi'],
       light=dict(key_K=2200, key_elev_deg=15, fill_ratio='1:5', practicals='firelight from below, flicker 2-6 Hz, amplitude 15-25%'),
       grade=dict(sat=0.85, chroma_cap=0.19, lift='#0B0607', gamma=0.92, gain='#FFE2C4', vignette='edges -1.5 to -2.5 EV by 44 s'),
       note='Madder + soot. 32.7-34.3 s cities fall (fire). 35-37 s forest green creeps over roads (olive/forest stitches overrun). 38-44.5 s frame edges darken, fray and unravel (literal dark edges).'),
  dict(id='IV_renewal', t=[45.5, 55.6], text='every ruler believes the world can be made whole / one banner, one village, one blank page',
       dominant=['linen_hi', 'linen'], accents=['navy', 'gold', 'woad'],
       light=dict(key_K=4300, key_elev_deg=28, fill_ratio='1:2.5', practicals='none; dawn wash'),
       grade=dict(sat=0.9, chroma_cap=0.15, lift='#0E0C0A', gamma=1.05, gain='#FFF8EC'),
       note='Restoration: colour returns from faded (historical aged) to fresh. "Blank page" = bare linen with faint underdrawing lines only.'),
  dict(id='V_question_title', t=[55.6, 66.142], text='what will the chronicles say of you? + logo',
       dominant=['navy', 'navy_deep'], accents=['gold', 'gold_hi', 'metal_gold_f0'],
       light=dict(key_K=3200, key_elev_deg=20, fill_ratio='1:4', practicals='gold sheen sweep 1.5-2.5 s across title'),
       grade=dict(sat=1.0, chroma_cap=0.17, lift='#05070C', gamma=1.0, gain='#FFF2DC'),
       note='Matches logo_title asset (navy cloth + gold letters). Final 2-3 s hold on logo, sheen sweep then fade.'),
]

lights = {f'{k}K': kelvin_rgb(k) for k in (1850, 1900, 2200, 2700, 3000, 3200, 4300, 5600, 6500, 8000)}

grading = dict(
  white_point_max='#F3E8D0', black_point_min='#07070A',
  rule='never output pure white or pure black; linen highlights clip at white_point_max; deepest shadows no lower than black_point_min',
  chroma_caps=dict(narrative_fills=0.13, heraldic=0.20, fire=0.19, global_default=0.17),
  saturation_note='Bayeux aged dyes sit at OKLCH C 0.03-0.10; game crests at 0.15-0.21. Narrative fills live at 0.06-0.13; only heraldry/title reach game chroma.',
  shadow_tint='#1A1620 (cool-violet) at 10-20% in shadows; highlights warm #FFF0D6',
)

contrast_checks = {f'{a} on {b}': contrast(cine[a]['hex'], cine[b]['hex']) for a, b in [
  ('ink_blueblack', 'linen'), ('ink_redbrown', 'linen'), ('gold', 'navy'), ('gold_hi', 'navy'),
  ('terracotta', 'linen'), ('woad', 'linen'), ('olive', 'linen'), ('buff', 'linen'), ('crimson', 'linen')]}

hist_vs_game = {
  'linen: bayeux mid vs game millefleurs': deltaE_ok(ground['linen_ground_mid']['hex'], game['linen(millefleurs)']['mid']),
  'terracotta vs game red_lion highlight': deltaE_ok(historical['madder_light_terracotta']['hex'], game['red_lion(vignette_red)']['highlight']),
  'madder dark vs game red_lion mid': deltaE_ok(historical['madder_dark_redbrown']['hex'], game['red_lion(vignette_red)']['mid']),
  'olive vs game archer green highlight': deltaE_ok(historical['green_olive']['hex'], game['archer_green(unit_archer)']['highlight']),
  'woad dark vs game navy mid': deltaE_ok(historical['woad_blue_dark']['hex'], game['navy(logo_title)']['mid']),
  'mustard vs game gold mid': deltaE_ok(historical['weld_mustard']['hex'], game['gold(logo_title)']['mid']),
  'madder light vs game crimson mid': deltaE_ok(historical['madder_light_terracotta']['hex'], game['crimson(crest_legion)']['mid']),
}

variation = dict(
  per_strand=dict(L_pct=[-5, 5], C_pct=[-8, 8], H_deg=[-3, 3]),
  along_strand_noise=dict(period_mm=[5, 15], L_pct=[-3, 3]),
  dye_lot_patches=dict(size_cm=[5, 20], L_pct=[-2, 2], H_deg=[-2, 2], note='sharp-ish boundaries where a new skein starts'),
  woad_core_effect='on worn ridges blue reads +6-10% L and -20% C (indigotin dyes the surface only)',
  fading_window_side='one side of a long frieze ~5-10% lighter/less chroma (light exposure gradient)',
)

out = dict(
  meta=dict(project='CHRONICA intro', version=1, colour_space='sRGB (display-referred), OKLCH given as [L, C, h_deg]',
            sources=['Lewis & Gameson, Palette, Pigments and Pictorial Narrative (Durham repository) - list of ten original colours',
                     'Bayeux Museum: Tapestry or embroidery? - woad/madder/weld, woad fades because it does not penetrate the fibre core; 19th-c. restorations faded to near white',
                     'Chemistry World feature on Bayeux dyes - 518 restoration patches; restoration blues turned green, some threads white',
                     'CHRONICA game textures (ex/*.webp) sampled with HSV masks: see game_sampled'],
            caveat='historical hexes are best-effort visual estimates of aged appearance (+-6 dE_ok), not spectrophotometric data'),
  historical_bayeux_dyes=historical, historical_ground_and_repairs=ground,
  game_sampled=game, cinematic=cine, acts=acts, light_kelvin_display=lights, grading=grading,
  variation=variation, contrast_ratios=contrast_checks, deltaE_ok_x100_hist_vs_game=hist_vs_game,
)
json.dump(out, open(os.path.join(STYLE, 'palette.json'), 'w'), indent=1)

# ---------- swatch sheet ----------
def sheet():
    groups = [('BAYEUX DYES (aged -> fresh)', historical, True), ('GROUND / REPAIRS', ground, False), ('CINEMATIC', cine, False)]
    W, sw, sh, pad = 1800, 140, 80, 12
    rows = []
    for title, d, two in groups:
        rows.append(('title', title))
        items = list(d.items())
        for i in range(0, len(items), 11): rows.append(('sw', items[i:i + 11], two))
    H = sum(40 if r[0] == 'title' else sh + 46 + (34 if r[2] else 0) for r in rows) + 2 * pad
    im = Image.new('RGB', (W, H), (30, 28, 32)); dr = ImageDraw.Draw(im)
    try: f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    except Exception: f = ImageFont.load_default()
    y = pad
    for r in rows:
        if r[0] == 'title':
            dr.text((pad, y + 12), r[1], fill=(230, 220, 200), font=f); y += 40; continue
        for i, (k, v) in enumerate(r[1]):
            x = pad + i * (sw + 22)
            dr.rectangle([x, y, x + sw, y + sh], fill=tuple(hex2rgb(v['hex'])))
            if r[2]:
                dr.rectangle([x, y + sh, x + sw, y + sh + 30], fill=tuple(hex2rgb(v['fresh'])))
            yy = y + sh + (34 if r[2] else 4)
            dr.text((x, yy), k[:22], fill=(220, 215, 205), font=f)
            dr.text((x, yy + 16), v['hex'] + ('>' + v['fresh'] if r[2] else ''), fill=(160, 155, 150), font=f)
        y += sh + 46 + (34 if r[2] else 0)
    im.save(os.path.join(STYLE, 'palette.png'))
sheet()
print(json.dumps(hist_vs_game, indent=1)); print(json.dumps(contrast_checks, indent=1)); print(lights)
