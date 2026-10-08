"""Gate G1: the procedural Bayeux kit beside p1 at MATCHED px/mm and IDENTICAL relight.

Both sheets are baked at 10 px/mm and shaded on their 5 px/mm mip (the 1.0-1.4x rule at F1).  One light rig (the
f91 window key: 3000 K, az 128, el 22, key:fill 3:1, rim 25 %), one key-light pool expressed in SCREEN space (so it
spans the splice continuously), the same shared fold field, the same ageing amount, the same fibres model and the
same Act I grade.  The kit's right edge (capital, large town) is butted against p1's left edge, as the frieze splices
them (S02 -> T1 tree -> S03).

Outputs (g1/):  g1_side_by_side_2560x1440.png   full frame, left = kit k1_realm, right = p1_oath, both at 4.65 px/mm
                g1_crops_100pct.png              matched 100 % crops (kit row vs p1 row)
                g1_stats.json                    linen / wool / relief / contrast statistics of both halves
"""
import os, sys, json, time, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_f91 as R                                        # noqa (sets paths)
import numpy as np, cv2                                       # noqa
from chron.maps import MapSet                                 # noqa
from chron import frontal, grade                              # noqa
from chron.color import LUMA, lin2oklab                       # noqa

OUT = os.path.join(HERE, 'g1')
os.makedirs(OUT, exist_ok=True)
S = 4.65                       # F1, the storyboard's G1 density
W, H = 2560, 1440
HALF = W // 2


def render_half(ms, x0, y0, kcx_screen, seed):
    """render a 1280x1440 half at S px/mm, top-left (x0, y0) sheet mm; the key pool centre is given in screen px of
    the FULL composite frame and converted to this sheet's mm, so both halves share one pool."""
    view = dict(x0_mm=x0, y0_mm=y0, px_per_mm=S)
    K = R.SHOT['kmap']
    cx_mm = x0 + kcx_screen[0] / S
    cy_mm = y0 + kcx_screen[1] / S
    fr = frontal.render(ms, view, R.rig(), out_wh=(HALF, H), kmap=dict(cx_mm=cx_mm, cy_mm=cy_mm, r_mm=K['r_mm'], floor=K['floor'],
                        aspect=K.get('aspect', 1.0)), fib_seed=seed, edit=R.fold_field, age=R.age_map, return_maps=True)
    return fr


def stats(fr):
    m = fr['maps']
    mat = m['mat']; alb = m['alb']; h = m['h']
    lin = fr['lin']
    Lr = (lin * LUMA).sum(-1)
    hp = Lr - cv2.GaussianBlur(Lr, (0, 0), 2.0)
    linen = mat == 0
    wool = mat == 1
    lab = lin2oklab(np.clip(alb.reshape(-1, 3), 0, 1)).reshape(alb.shape)
    C = np.hypot(lab[..., 1], lab[..., 2])
    return dict(level=int(fr['level']), map_px_per_mm=float(fr['map_px']),
                linen_fraction=round(float(linen.mean()), 3),
                linen_albedo_lin=[round(float(v), 4) for v in alb[linen].mean(0)],
                wool_albedo_L_ok_median=round(float(np.median(lab[..., 0][wool])), 3),
                wool_chroma_ok_p50=round(float(np.median(C[wool])), 3), wool_chroma_ok_p95=round(float(np.percentile(C[wool], 95)), 3),
                wool_height_mm_p50=round(float(np.median(h[wool])), 3), wool_height_mm_p95=round(float(np.percentile(h[wool], 95)), 3),
                frame_luma_p05_p50_p95=[round(float(np.percentile(Lr, q)), 4) for q in (5, 50, 95)],
                frame_hf_std=round(float(hp.std()), 5))


def main():
    t0 = time.time()
    kit = MapSet(os.path.join(R.MAPS, 'k1_realm'))
    p1 = MapSet(os.path.join(R.MAPS, 'p1_oath'))
    # composite: kit (x 325-600 mm) | p1 (from its left margin)
    y0 = 5.0
    kit_x0 = 600.0 - HALF / S                  # kit's right edge = sheet edge (600 mm)
    p1_x0 = 0.0
    p1_y0 = 30.0
    pool = (W * 0.5, H * 0.42)                 # one pool, centred on the splice
    frk = render_half(kit, kit_x0, y0, (pool[0], pool[1]), 91)
    frp = render_half(p1, p1_x0, p1_y0, (pool[0] - HALF, pool[1]), 91)
    lin = np.concatenate([frk['lin'], frp['lin']], 1)
    # the same room pool as f91, in screen space across the splice (identical for both halves)
    from chron.shade import spot
    PA = R.SHOT['pool_all']
    pa = spot((H, W), S, pool[0] / S, pool[1] / S, PA['r_mm'], PA['floor'], PA.get('aspect', 1.0), (0.0, 0.0))
    lin = lin * pa[..., None]
    img = grade.grade(lin, exposure=R.SHOT['grade']['exposure'], act='I', seed=91)
    cv2.imwrite(os.path.join(OUT, 'g1_side_by_side_2560x1440.png'), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    # matched 100 % crops: (kit window px, p1 window px) in each half's own 1280x1440 frame
    imk, imp = img[:, :HALF], img[:, HALF:]
    def at(x_mm, y_mm, x0, y0_):
        return (int((x_mm - x0) * S) - 260, int((y_mm - y0_) * S) - 260)
    crops = dict(kit=[at(362, 125, kit_x0, y0), at(480, 172, kit_x0, y0), at(430, 232, kit_x0, y0)],
                 p1=[at(112, 150, p1_x0, p1_y0), at(205, 170, p1_x0, p1_y0), at(78, 250, p1_x0, p1_y0)])
    cs = 520
    rows = []
    for nm, im in (('kit', imk), ('p1', imp)):
        tiles = []
        for (x, y) in crops[nm]:
            x = int(np.clip(x, 0, HALF - cs)); y = int(np.clip(y, 0, H - cs))
            tiles.append(im[y:y + cs, x:x + cs])
            tiles.append(np.full((cs, 8, 3), 20, np.uint8))
        row = np.hstack(tiles[:-1])
        label = 'KIT k1_realm (procedural Bayeux)' if nm == 'kit' else 'P1 p1_oath (re-embroidered panel)'
        cv2.rectangle(row, (0, 0), (330, 26), (22, 18, 14), -1)
        cv2.putText(row, label, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (235, 225, 205), 1, cv2.LINE_AA)
        rows.append(row)
        rows.append(np.full((8, rows[-1].shape[1], 3), 20, np.uint8))
    sheet = np.vstack(rows[:-1])
    cv2.imwrite(os.path.join(OUT, 'g1_crops_100pct.png'), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))
    st = dict(px_per_mm=S, light=R.SHOT['light'], kmap_pool_screen_px=pool, age=R.SHOT.get('age'), grade=R.SHOT['grade'],
              kit=stats(frk), p1=stats(frp), seconds=round(time.time() - t0, 1))
    json.dump(st, open(os.path.join(OUT, 'g1_stats.json'), 'w'), indent=1)
    print(json.dumps(st, indent=1))


if __name__ == '__main__':
    main()
