"""f899 v3 layout: the single source of truth for what stands where (sheet mm, x right, y down; no frame shift any more).

A readable confrontation: the legion's crimson (left, facing right) against the merchants' blue (right, facing left) across a clear central
gap (no-man's land).  Only the five FRONT slips stand (hinged ~70 deg, frozen in strike poses); everything behind them (FLAT) lies in the cloth as a
classic Bayeux frieze row (stitched, not standing, no footprints).  The focal pair, a crimson rider and a blue spearman about to meet, sits slightly
right of the frame centre inside x 320-2240 px.

Also holds the quick preview (seconds): projects the standing cards (real stand-up matrix), the flat figures and the hearth shadows with the shot camera.
    python3 layout_v3.py OUT.png [scale]
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)

RED, REDD, BLUE, BLUED = '#A3181A', '#6E2428', '#2F5F9E', '#2D4460'

# standing slips: (unit, pose, realm, x (feet centre), y (feet), card px per mm, yaw deg, tilt deg)
FRONT = [
    ('mercenary',   'strike', 'R', 158.0, 283.0, 5.3, -3.0, 70.0),     # crimson rank, rear left (axe raised)
    ('legionary',   'strike', 'R', 212.0, 298.0, 5.0, 3.0, 70.0),      # crimson rank, front
    ('knight',      'strike', 'R', 293.0, 301.0, 4.9, -2.0, 70.0),     # FOCAL: the crimson rider, lance levelled
    ('spearman',    'strike', 'B', 447.0, 299.0, 4.7, 3.0, 70.0),      # FOCAL: the blue spearman
    ('man_at_arms', 'strike', 'B', 520.0, 287.0, 5.0, -3.0, 70.0),     # blue rank
]
# flat frieze rows lying in the cloth: (unit, pose, realm, x, y (feet), scale rel. to 5 px/mm)
FLAT_A = [('spearman', 'idle', 'R', 104.0, 232.0, .64), ('man_at_arms', 'idle', 'R', 172.0, 233.0, .62), ('archer', 'idle', 'R', 238.0, 233.0, .66),
          ('legionary', 'idle', 'B', 452.0, 233.0, .64), ('archer', 'idle', 'B', 520.0, 234.0, .66)]
FLAT_B = [('knight', 'idle', 'R', 124.0, 205.0, .46),
          ('knight', 'idle', 'B', 486.0, 204.0, .46), ('horse_archer', 'strike', 'B', 574.0, 205.0, .44)]

SKY_Y0, SKY_Y1 = 84.0, 170.0


def realm_cols(realm):
    return (RED, REDD) if realm == 'R' else (BLUE, BLUED)


def slip_names():
    return [f'slip{k}' for k in range(len(FRONT))]


def pose_table():
    return {f'slip{k}': dict(tilt=f[7], yaw=f[6]) for k, f in enumerate(FRONT)}


# ---------------------------------------------------------------------------------------------------- preview
def main():
    import bkit
    import numpy as np, cv2
    import camera as CAM
    import figure as F
    import export_slips as EX
    ROOT = os.path.dirname(HERE)
    shot = json.load(open(os.path.join(ROOT, 'shot_f899.json')))
    cam = CAM.build(shot['camera'])
    out_png = sys.argv[1]
    sc = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    Wp, Hp = int(CAM.W * sc), int(CAM.H * sc)
    bg = np.zeros((Hp, Wp, 3), np.float32) + np.array([0.80, 0.68, 0.50], np.float32)

    def poly(pts, col):
        uv, _ = CAM.project(cam, CAM.sheet_to_world(pts))
        cv2.fillPoly(bg, [(uv * sc).astype(np.int32)], col)
    poly([[-50, -60], [700, -60], [700, -0.01], [-50, -0.01]], (0.1, 0.07, 0.04))
    poly([[-50, 0], [700, 0], [700, 78], [-50, 78]], (0.60, 0.56, 0.45))
    # sky bands
    cols = [(0.30, 0.38, 0.46), (0.40, 0.48, 0.56), (0.78, 0.70, 0.55), (0.50, 0.58, 0.64), (0.50, 0.28, 0.27), (0.76, 0.65, 0.48), (0.62, 0.34, 0.28), (0.80, 0.70, 0.52)]
    ys = np.linspace(SKY_Y0, SKY_Y1, len(cols) + 1)
    for k, c in enumerate(cols):
        poly([[-50, ys[k]], [700, ys[k]], [700, ys[k + 1]], [-50, ys[k + 1]]], c)
    poly([[-50, 176], [700, 176], [700, 360], [-50, 360]], (0.78, 0.67, 0.50))
    img = bg.copy()
    # light
    H_ = shot['hearth']
    a_, e_ = math.radians(H_['az']), math.radians(H_['el'])
    Lv = np.array([math.cos(a_) * math.cos(e_), math.sin(a_) * math.cos(e_), math.sin(e_)])

    def card_of(unit, pose, realm):
        t, d = realm_cols(realm)
        card = F.load_card(unit, pose, t, flip=(realm == 'B'), shield=t, deep_hex=d)
        lin = card['lin']; al = card['alpha']
        ys_, xs_ = np.nonzero(al > 0.5)
        x_ref, y_feet = 0.5 * (xs_.min() + xs_.max()), ys_.max()
        rgba = np.dstack([np.clip(lin, 0, 1) ** (1 / 2.2), al]).astype(np.float32)
        return rgba, x_ref, y_feet

    def warp_world(rgba, ppm, x_ref, y_feet, Mw, to_ground=False):
        Hh, Ww = rgba.shape[:2]
        loc = np.array([[0, 0], [Ww, 0], [Ww, Hh], [0, Hh]], np.float64)
        X = (loc[:, 0] - x_ref) / ppm; Y = (y_feet - loc[:, 1]) / ppm
        P = (np.stack([X, Y, np.zeros(4), np.ones(4)], 1) @ Mw.T)[:, :3]
        if to_ground:
            P = P - Lv[None] * (P[:, 2:3] / Lv[2])
            P[:, 2] = 0
        uv, _ = CAM.project(cam, P)
        dst = (uv * sc).astype(np.float32)
        Hm = cv2.getPerspectiveTransform(loc.astype(np.float32), dst)
        w = cv2.warpPerspective(rgba, Hm, (Wp, Hp), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        return w[..., :3], w[..., 3:4]

    labels = []
    for rank in (FLAT_B, FLAT_A):
        for (unit, pose, realm, x, y, s) in rank:
            rgba, xr, yf = card_of(unit, pose, realm)
            M0 = np.eye(4); M0[:3, 3] = (x, -y, 0.0)
            w, a = warp_world(rgba, 5.0 / s, xr, yf, M0)
            img = img * (1 - a) + w * a * 0.85
    shadows = np.zeros((Hp, Wp, 1), np.float32)
    stand = []
    for k, (unit, pose, realm, x, y, ppm, yaw, tilt) in enumerate(FRONT):
        rgba, xr, yf = card_of(unit, pose, realm)
        M = EX.slip_matrix(x, y, tilt, yaw)
        w, a = warp_world(rgba, ppm, xr, yf, M)
        ws, as_ = warp_world(rgba, ppm, xr, yf, M, to_ground=True)
        shadows = np.maximum(shadows, as_)
        stand.append((y, k, w, a))
        uv, _ = CAM.project(cam, CAM.sheet_to_world([[x, y]]))
        labels.append((f'{k}{realm}', int(uv[0, 0] * sc) - 8, int(uv[0, 1] * sc) + 14))
    img = img * (1 - 0.62 * shadows)
    for y, k, w, a in sorted(stand):
        img = img * (1 - a) + w * a
    o8 = (np.clip(img, 0, 1) * 255).astype(np.uint8)[..., ::-1].copy()
    for t, x_, y_ in labels:
        cv2.putText(o8, t, (x_, y_), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    for xx in (320, 2240, 1280):
        cv2.line(o8, (int(xx * sc), 0), (int(xx * sc), Hp), (0, 255, 255) if xx != 1280 else (255, 255, 0), 1)
    cv2.imwrite(out_png, o8)
    print('->', out_png)


if __name__ == '__main__':
    main()
