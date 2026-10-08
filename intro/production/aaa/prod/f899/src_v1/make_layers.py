"""Diagnostic layer sheet for the f899 keyframe: ground plate (R25 + shadow ratios), Eevee slips only, hearth shadow ratio, slip alpha.
    python3 make_layers.py EEVEE_DIR GROUND.jpg OUT.jpg"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
import exr


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def main():
    ev, ground, out = sys.argv[1:4]
    d = lambda n: exr.read(os.path.join(ev, n))
    sl = d('slips_hearth_img_0001.exr'); sc = d('slips_cool_img_0001.exr'); sf = d('slips_fill_img_0001.exr')
    p = d('plane_hearth_img_0001.exr')[..., :3].mean(-1); q = d('planeclean_hearth_img_0001.exr')[..., :3].mean(-1)
    ratio = np.clip(p / np.maximum(q, 1e-5), 0, 1)
    slips = (sl[..., :3] * 1.1 + sc[..., :3] * 1.0 + sf[..., :3]) * 0.8
    bg = np.full_like(slips, 0.12)
    comp = slips + bg * (1 - sl[..., 3:4])
    tiles = [cv2.imread(ground), (srgb(comp) * 255).astype(np.uint8)[..., ::-1], cv2.cvtColor((ratio * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR),
             cv2.cvtColor((sl[..., 3] * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)]
    names = ['R25 ground plate x shadow ratios', 'Eevee slips + tethers (hearth + cool + fill)', 'hearth shadow ratio (Eevee shadow catcher)', 'slip alpha']
    tt = []
    for t, n in zip(tiles, names):
        t = cv2.resize(t, (960, 540), interpolation=cv2.INTER_AREA)
        cv2.putText(t, n, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(t, n, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (10, 10, 10), 1, cv2.LINE_AA)
        tt.append(t)
    sheet = np.vstack([np.hstack(tt[:2]), np.hstack(tt[2:])])
    cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print('layers ->', out)


if __name__ == '__main__':
    main()
