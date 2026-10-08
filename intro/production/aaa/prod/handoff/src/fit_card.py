"""Fit the live card rect (base units) to a native capture by matching the rebuilt nine-patch
against the captured walnut frame (content-free zones). Prints the fitted rect and residuals."""
import sys, json
import numpy as np
from scipy.optimize import minimize
from godot2d import load_rgba, draw_ninepatch, over
from menu_layout import layout, draw_rects, MARGINS
S = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa'

def fit(cap_path, W, H, card_guess=(629.0, 665.0)):
    cap = load_rgba(cap_path)[..., :3]
    L = layout(W, H, card_min=card_guess)
    s = L['scale']
    tex = load_rgba(S + '/assets/tex/table_parchment/menu_card.png')
    x, y, w, h = draw_rects(L)['menu_card']
    X0, Y0, X1, Y1 = [int(round(v)) for v in (x * s, y * s, (x + w) * s, (y + h) * s)]
    m = int(round(40 * s / 1.6))
    zones = [(X0 - 4, Y0 + 3 * m, X0 + m, Y1 - 3 * m), (X1 - m, Y0 + 3 * m, X1 + 4, Y1 - 3 * m),
             (X0 + 3 * m, Y0 - 4, X1 - 3 * m, Y0 + m), (X0 + 3 * m, Y1 - m, X1 - 3 * m, Y1 + 4)]
    def err(p):
        lay, _ = draw_ninepatch(W, H, tex, tuple(p), s, MARGINS['menu_card'])
        comp = over(cap, lay)
        d = np.abs(comp - cap) * 255
        return float(sum(d[b:e, a:c].mean() for a, b, c, e in zones))
    p0 = np.array([x, y, w, h])
    best = p0; be = err(p0)
    # coarse-to-fine coordinate search (objective is piecewise, avoid gradients)
    for step in (1.0, 0.25, 0.1, 0.04, 0.02):
        improved = True
        while improved:
            improved = False
            for i in (2, 3):  # position is snapped to whole base units; fit the min size
                for sgn in (-1, 1):
                    q = best.copy(); q[i] += sgn * step
                    e = err(q)
                    if e < be - 1e-4:
                        best, be, improved = q, e, True
    return best, be, s

if __name__ == '__main__':
    cap, W, H = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    best, be, s = fit(cap, W, H)
    print(json.dumps({'card_base': [round(v, 3) for v in best], 'card_px': [round(v * s, 2) for v in best], 'frame_err_sum': round(be, 3)}))
