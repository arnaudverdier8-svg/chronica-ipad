import numpy as np
from chron.ageing import apply_age
from chron.color import lin2oklab, lin2srgb
A = shot._ASSETS; lo = A['loose']
for i in lo.stubborn:
    b = lo.blocks[i]
    alb = b['alb'][None, None].astype(np.float32)
    mat = np.ones((1, 1), np.uint8)
    lab = lin2oklab(alb)[0, 0]
    hue = np.degrees(np.arctan2(lab[2], lab[1])) % 360
    C = np.hypot(lab[1], lab[2])
    pur = np.clip(1 - np.abs(((hue - 322 + 180) % 360) - 180) / 55.0, 0, 1) * np.clip((C - 0.02) / 0.04, 0, 1)
    amt = 1.12 + 0.75 * pur
    out_robe = apply_age(alb, mat, np.full((1, 1), amt, np.float32), {}, ghost=None)[0, 0]
    print(i, 'alb', b['alb'].round(3), 'hue %.0f C %.3f pur %.2f amt %.2f' % (hue, C, pur, amt), 'robe-aged', out_robe.round(4), 'v2 strand', b['alb_aged'].round(4))
    print('   srgb alb', (np.clip(lin2srgb(b['alb']), 0, 1) * 255).round(0), 'robe-aged', (np.clip(lin2srgb(out_robe), 0, 1) * 255).round(0), 'v2', (np.clip(lin2srgb(b['alb_aged']), 0, 1) * 255).round(0))
