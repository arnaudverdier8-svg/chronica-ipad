"""f899 QA: numeric checks on the final linear composite and the 8-bit keyframe (no void / non-finite pixels, plate coverage of the
frame, grade clamps, chroma budget on the slips, edge-pixel sanity).  Writes qa_report.json.
    python3 qa.py KEYFRAME.png work/comp_lin_<tag>.npy OUT.json
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bkit
import numpy as np, cv2
import camera as CAM
from chron.color import srgb2lin, lin2oklab

ROOT = os.path.dirname(HERE)


def main():
    kf, linp, out = sys.argv[1:4]
    shot = json.load(open(os.path.join(ROOT, 'shot_f899.json')))
    img = cv2.cvtColor(cv2.imread(kf, cv2.IMREAD_UNCHANGED), cv2.COLOR_BGR2RGB)
    rep = {}
    rep['size'] = list(img.shape[:2][::-1])
    rep['dtype'] = str(img.dtype)
    lin = np.load(linp).astype(np.float32)
    rep['linear_finite'] = bool(np.isfinite(lin).all())
    rep['linear_min'] = float(lin.min()); rep['linear_max'] = float(lin.max())
    # grade clamps (8-bit: black >= #07070A, white <= #F3E8D0 plus grain 1.2 %)
    i8 = img if img.dtype == np.uint8 else (img / 257).astype(np.uint8)
    rep['p0.1_rgb'] = np.percentile(i8.reshape(-1, 3), 0.1, axis=0).tolist()
    rep['p99.9_rgb'] = np.percentile(i8.reshape(-1, 3), 99.9, axis=0).tolist()
    rep['clipped_white_frac'] = float((i8.min(-1) >= 250).mean())
    rep['pure_black_frac'] = float((i8.max(-1) <= 3).mean())
    # plate coverage: corners of the frame must land inside the rendered plate rectangle
    cam = CAM.build(shot['camera'])
    P = shot['plate']
    uv = np.array([[0, 0], [CAM.W, 0], [0, CAM.H], [CAM.W, CAM.H]], np.float64)
    xy, z = CAM.ground_from_pixel(cam, uv)
    inside = [((P['x0'] <= x <= P['x0'] + P['w']) and (P['y0'] <= y <= P['y0'] + P['h'])) or y < 0.0 for x, y in xy]     # corners above the cloth's top edge (y < 0) are the walnut table
    rep['frame_corners_mm'] = np.round(xy, 1).tolist()
    rep['plate_rect_mm'] = [P['x0'], P['y0'], P['x0'] + P['w'], P['y0'] + P['h']]
    rep['plate_covers_frame'] = bool(all(inside))
    top_edge = xy[1][1]
    rep['top_right_corner_y_mm'] = float(top_edge)
    rep['cloth_edge_visible'] = bool(min(xy[0][1], xy[1][1]) < 0.0)
    # OKLab chroma budget (final image): fraction of pixels above .20
    lab = lin2oklab(srgb2lin(i8.astype(np.float32) / 255))
    C = np.hypot(lab[..., 1], lab[..., 2])
    rep['chroma_p99'] = float(np.percentile(C, 99)); rep['chroma_max'] = float(C.max()); rep['frac_chroma_gt_0.20'] = float((C > 0.20).mean())
    # sharpness: Laplacian variance in a few tiles (slips vs ground)
    g = cv2.cvtColor(i8, cv2.COLOR_RGB2GRAY).astype(np.float32)
    lap = cv2.Laplacian(g, cv2.CV_32F)
    tiles = {}
    for name, (x0, y0, x1, y1) in dict(front_left=(300, 900, 1100, 1350), centre=(1000, 950, 1700, 1400), right=(1700, 880, 2500, 1350), sky=(500, 380, 1300, 700),
                                       border=(300, 80, 1000, 300)).items():
        tiles[name] = float(lap[y0:y1, x0:x1].var())
    rep['laplacian_var'] = tiles
    # composition: projected bbox (screen px) of every standing slip card, the focal pair (knight x spearman) must sit inside x 320-2240
    ex = json.load(open(os.path.join(ROOT, 'blend', 'slips', 'slips_export.json')))
    sl = {}
    for s in ex['slips']:
        M = np.array(s['matrix']); Wm, Hm = s['size_mm']; ox, oy = s['origin_mm']; xf, yf = s['hinge_mm']
        loc = np.array([[ox - xf, yf - (oy + Hm)], [ox + Wm - xf, yf - (oy + Hm)], [ox + Wm - xf, yf - oy], [ox - xf, yf - oy]])
        P = (np.concatenate([loc, np.zeros((4, 1)), np.ones((4, 1))], 1) @ M.T)[:, :3]
        uv, _ = CAM.project(cam, P)
        sl[f"{s['group']}_{s['unit']}_{s['realm']}"] = [int(uv[:, 0].min()), int(uv[:, 1].min()), int(uv[:, 0].max()), int(uv[:, 1].max())]
    rep['standing_slip_bbox_px'] = sl
    foc = [v for k, v in sl.items() if ('knight' in k or 'spearman' in k)]
    rep['focal_pair_x_range_px'] = [min(v[0] for v in foc), max(v[2] for v in foc)] if foc else None
    rep['focal_pair_inside_320_2240'] = bool(foc and min(v[0] for v in foc) >= 320 and max(v[2] for v in foc) <= 2240)
    rep['standing_count'] = len(sl)
    json.dump(rep, open(out, 'w'), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main()
