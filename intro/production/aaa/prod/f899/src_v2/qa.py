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
    shot = json.load(open(os.path.join(ROOT, 'shot_f899_v2.json')))
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
    for name, (x0, y0, x1, y1) in dict(front_left=(20, 900, 700, 1300), centre=(1000, 980, 1700, 1420), right=(1750, 900, 2450, 1350), sky=(900, 420, 1600, 780),
                                       border=(300, 140, 900, 340)).items():
        tiles[name] = float(lap[y0:y1, x0:x1].var())
    rep['laplacian_var'] = tiles
    json.dump(rep, open(out, 'w'), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main()
