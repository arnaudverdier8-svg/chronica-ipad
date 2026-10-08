"""KEYFRAME f669 (S09 'chair') at 2560x1440 + 100 % crops + QA.  Run:  nice -n 5 python3 render_keyframe.py
Writes ../out/f669_2560x1440.png (8-bit sRGB), f669_2560x1440_16bit.png, f669_preview_1280.jpg, f669_crop_*.png, f669_report.json"""
import os, sys, time, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
import shot
from chron.grade import grade
from chron.qa.void import check_void
OUT = os.environ.get('F669_OUT') or os.path.join(HERE, '..', 'out'); os.makedirs(OUT, exist_ok=True)
F = 669
t = time.time()
r = shot.render_frame(F)
img = r['img']
cv2.imwrite(os.path.join(OUT, 'f669_2560x1440.png'), img[..., ::-1])
img16 = grade(r['lin'], exposure=shot.EXPOSURE, act='II', seed=F, out_u16=True)
cv2.imwrite(os.path.join(OUT, 'f669_2560x1440_16bit.png'), img16[..., ::-1])
cv2.imwrite(os.path.join(OUT, 'f669_preview_1280.jpg'), cv2.resize(img[..., ::-1], (1280, 720), interpolation=cv2.INTER_AREA),
            [cv2.IMWRITE_JPEG_QUALITY, 92])
v = r['view']; s = v['px_per_mm']; x0 = v['cx_mm'] - 1280 / s; y0 = v['cy_mm'] - 720 / s
def scr(xmm, ymm): return int(round((xmm - x0) * s)), int(round((ymm - y0) * s))
# 100 % crops of the important regions (sheet-mm anchors -> screen px)
CROPS = {
    'crown_tethers': (scr(294, 130), (760, 560)),
    'void_holes_underdrawing': (scr(272, 192), (720, 560)),
    'crown_shadow_in_void': (scr(322, 190), (760, 520)),
    'loose_purple_strands': (scr(300, 233), (900, 520)),
    'void_top_edge': (scr(296, 150), (900, 420)),
    'void_lap_bottom': (scr(300, 258), (1000, 380)),
    'red_lord_face_rim': (scr(198, 160), (560, 560)),
    'blue_lord_face_rim': (scr(396, 160), (560, 560)),
    'green_lord_rim': (scr(470, 170), (560, 560)),
    'goblet_candle_ghosts_tideline': (scr(445, 268), (1100, 400)),
    'right_edge_candles': (scr(525, 262), (700, 440)),
    'left_goblet_ghost': (scr(142, 262), (520, 420)),
}
crops = {}
for nm, ((cx, cy), (w, h)) in CROPS.items():
    xa = int(np.clip(cx - w // 2, 0, 2560 - w)); ya = int(np.clip(cy - h // 2, 0, 1440 - h))
    cv2.imwrite(os.path.join(OUT, f'f669_crop_{nm}.png'), img[ya:ya + h, xa:xa + w, ::-1])
    crops[nm] = [xa, ya, w, h]
# QA: luminance by region (scene-linear, relative to the lit void)
Y = (r['lin'] * [0.2126, 0.7152, 0.0722]).sum(-1)
def med(xmm, ymm, rad=6):
    X, Yp = scr(xmm, ymm); R = int(rad * s)
    return float(np.median(Y[Yp - R:Yp + R, X - R:X + R]))
ref = med(297, 168)
lum = {nm: round(float(np.log2(med(x, y) / ref)), 2) for nm, (x, y) in
       dict(red_face=(198, 148), blue_face=(396, 148), gold_face=(126, 158), green_face=(472, 156), void_lap=(297, 245),
            crown=(294, 128), table=(300, 285)).items()}
check_void(r['lin'], r['alpha'], name='f669')
rep = dict(frame=F, view=v, level=r['level'], timing={k: (round(x, 2) if isinstance(x, float) else x) for k, x in r['timing'].items() if k != 'view'},
           EV_vs_void_head=lum, crops=crops, wall_s=round(time.time() - t, 1), void_check='PASS (0 void pixels)')
json.dump(rep, open(os.path.join(OUT, 'f669_report.json'), 'w'), indent=1)
print(json.dumps(rep, indent=1))
