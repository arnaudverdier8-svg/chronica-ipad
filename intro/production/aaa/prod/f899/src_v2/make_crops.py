"""100 % crops of the key regions of the f899 keyframe + a review sheet.
    python3 make_crops.py KEYFRAME.png OUT_DIR [crops.json]
crops.json: {"name": [x0, y0, x1, y1], ...} in 2560x1440 px (defaults below are for the f899 composition)."""
import os, sys, json
import cv2, numpy as np

DEFAULT = {
    'crop_legion_left_slips': [20, 880, 700, 1300],
    'crop_knight_footprints_tethers': [380, 820, 1060, 1240],
    'crop_centre_clash': [900, 760, 1580, 1180],
    'crop_merchants_right': [1480, 840, 2160, 1260],
    'crop_shadows_over_sky': [1000, 300, 1680, 720],
    'crop_border_gold_thread_tarnish': [1700, 0, 2380, 330],
    'crop_left_pale_arc_bleach': [0, 420, 680, 840],
}


def main():
    kf, out = sys.argv[1], sys.argv[2]
    crops = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else DEFAULT
    os.makedirs(out, exist_ok=True)
    im = cv2.imread(kf)
    H, W = im.shape[:2]
    tiles = []
    for name, (x0, y0, x1, y1) in crops.items():
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
        c = im[y0:y1, x0:x1]
        cv2.imwrite(os.path.join(out, name + '.png'), c)
        t = cv2.resize(c, (640, int(640 * c.shape[0] / c.shape[1])), interpolation=cv2.INTER_AREA)
        cv2.putText(t, name.replace('crop_', ''), (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 3, cv2.LINE_AA)
        cv2.putText(t, name.replace('crop_', ''), (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(t)
    rows = []
    for i in range(0, len(tiles), 3):
        r = tiles[i:i + 3]
        h = max(t.shape[0] for t in r)
        r = [np.pad(t, ((0, h - t.shape[0]), (0, 0), (0, 0))) for t in r]
        while len(r) < 3:
            r.append(np.zeros_like(r[0]))
        rows.append(np.hstack(r))
    cv2.imwrite(os.path.join(out, 'review_sheet.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print('crops ->', out)


if __name__ == '__main__':
    main()
