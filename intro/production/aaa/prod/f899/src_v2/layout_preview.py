"""Quick layout preview (seconds): the standing slip cards (textured quads at the real stand-up matrix) + their flat footprints, projected with the
shot camera, over a neutral plate.  Used to place the front-rank cluster before the 4-minute bake.
    python3 layout_preview.py OUT.png [scale]
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bkit
import numpy as np, cv2
import camera as CAM
import figure as F
import scene_war as SW
import export_slips as EX

ROOT = os.path.dirname(HERE)
shot = json.load(open(os.path.join(ROOT, 'shot_f899_v2.json')))
cam = CAM.build(shot['camera'])


def quad_warp(img_rgba, ppm, x_ref, y_feet, M, sc, out):
    H, W = img_rgba.shape[:2]
    loc = np.array([[0, 0], [W, 0], [W, H], [0, H]], np.float64)
    X = (loc[:, 0] - x_ref) / ppm; Y = (y_feet - loc[:, 1]) / ppm
    P = np.stack([X, Y, np.zeros(4), np.ones(4)], 1) @ M.T
    uv, _ = CAM.project(cam, P[:, :3])
    dst = (uv * sc).astype(np.float32)
    Hm = cv2.getPerspectiveTransform(loc.astype(np.float32), dst)
    w = cv2.warpPerspective(img_rgba, Hm, (out.shape[1], out.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    a = w[..., 3:4]
    return w[..., :3], a


def main():
    out_png = sys.argv[1]
    sc = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    Wp, Hp = int(CAM.W * sc), int(CAM.H * sc)
    # background: sheet regions (sky / hills / field) by projecting rects
    bg = np.zeros((Hp, Wp, 3), np.float32) + np.array([0.80, 0.68, 0.50], np.float32)
    def poly(x0, y0, x1, y1, col):
        uv, _ = CAM.project(cam, CAM.sheet_to_world([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]))
        cv2.fillPoly(bg, [(uv * sc).astype(np.int32)], col)
    poly(-50, -40, 700, 78, (0.55, 0.50, 0.40)); poly(-50, 84, 700, 194, (0.45, 0.30, 0.30)); poly(-50, 205, 700, 250, (0.40, 0.45, 0.35))
    poly(-50, -60, 700, -0.01, (0.1, 0.07, 0.04))
    img = bg.copy()
    # figures
    items = []
    for k, f in enumerate(SW.FRONT):
        unit, pose, realm, x, y, ppm_ = f[:6]; x = x + SW.DX
        items.append((y, k, unit, pose, realm, x, y, ppm_))
    items.sort()
    labels = []
    tcol = {'R': '#A3181A', 'B': '#2F5F9E'}
    for _, k, unit, pose, realm, x, y, ppm in items:
        card = F.load_card(unit, pose, tcol[realm], flip=(realm == 'B'), shield=tcol[realm])
        lin = card['lin']; al = card['alpha']
        ys, xs = np.nonzero(al > 0.5)
        x_ref, y_feet = 0.5 * (xs.min() + xs.max()), ys.max()
        rgba = np.dstack([np.clip(lin, 0, 1) ** (1 / 2.2), al]).astype(np.float32)
        # footprint (flat): faint
        M0 = np.eye(4); M0[:3, 3] = (x, -y, 0.0)
        w, a = quad_warp(rgba, ppm, x_ref, y_feet, M0, sc, img)
        img = img * (1 - 0.30 * a) + 0.30 * a * np.array([0.9, 0.85, 0.7], np.float32)
        pose_ = EX.POSE.get(f'slip{k}', dict(tilt=70.0, yaw=0.0))
        M = EX.slip_matrix(x, y, pose_['tilt'], pose_['yaw'])
        w, a = quad_warp(rgba, ppm, x_ref, y_feet, M, sc, img)
        # long shadow (hearth az 240 el 24): project the card onto the cloth along the light
        L = np.array([math.cos(math.radians(240)) * math.cos(math.radians(24)), math.sin(math.radians(240)) * math.cos(math.radians(24)), math.sin(math.radians(24))])
        loc = None
        img = img * (1 - a) + w * a
        labels.append((f'{k}{realm}', int(cam_uv(x, y)[0] * sc) - 10, int(cam_uv(x, y)[1] * sc) + 16))
    o8 = (np.clip(img, 0, 1) * 255).astype(np.uint8)[..., ::-1].copy()
    for t, x_, y_ in labels:
        cv2.putText(o8, t, (x_, y_), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(out_png, o8)
    print('->', out_png)


def cam_uv(x, y):
    uv, _ = CAM.project(cam, CAM.sheet_to_world([[x, y]]))
    return uv[0]


if __name__ == '__main__':
    main()
