"""Independent re-check of the hand-off keyframe against the live capture it was built from.
  * outside the card rect: max |diff| and number of changed px (must be 0)
  * changed bbox (must sit strictly inside the parchment field)
  * keyframe pixels identical to a reference file (e.g. the _v1 keyframe), if given
usage: python3 verify_outside_card.py HANDOFF_DIR [--ref-suffix _v1]"""
import sys, os, json, glob
import numpy as np
from PIL import Image

def main(hd, ref_suffix=None):
    out = {}
    for rep in sorted(glob.glob(os.path.join(hd, 'report_*.json'))):
        tag = os.path.basename(rep)[7:-5]
        if tag.endswith('_v1'):
            continue
        R = json.load(open(rep))
        kf = np.asarray(Image.open(os.path.join(hd, f'f1983_{tag}.png')).convert('RGB')).astype(np.int16)
        cap = np.asarray(Image.open(R['capture']).convert('RGB')).astype(np.int16)
        H, W = kf.shape[:2]
        d = np.abs(kf - cap).max(2)
        cx, cy, cw, ch = R['card_draw_rect_px']
        x0, y0, x1, y1 = int(np.floor(cx)), int(np.floor(cy)), int(np.ceil(cx + cw)), int(np.ceil(cy + ch))
        outside = np.ones((H, W), bool); outside[y0:y1, x0:x1] = False
        ys, xs = np.nonzero(d > 0)
        px, py, pw, ph = R['parchment_field_px']
        res = {'outside_card_rect': {'max_abs_diff': int(d[outside].max()), 'changed_px': int((d[outside] > 0).sum())},
               'changed_px_total': int((d > 0).sum()),
               'changed_bbox': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None,
               'parchment_field_px': [px, py, px + pw, py + ph]}
        res['bbox_inside_parchment_field'] = bool(len(xs) and xs.min() >= px and ys.min() >= py and xs.max() <= px + pw and ys.max() <= py + ph)
        if ref_suffix:
            rp = os.path.join(hd, f'f1983_{tag}{ref_suffix}.png')
            if os.path.exists(rp):
                ref = np.asarray(Image.open(rp).convert('RGB')).astype(np.int16)
                res[f'identical_to_{ref_suffix}'] = bool((ref == kf).all())
        out[tag] = res
    print(json.dumps(out, indent=1))
    return out

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == '--ref-suffix' else None)
