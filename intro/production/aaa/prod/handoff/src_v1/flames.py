"""Split each candle matte into FLAME and UNLIT (wax + wick, flame removed) layers, drawn exactly
like the candle itself (same Godot rect, same trilinear sampling), for the storyboard's desk states:
desk unlit before f1664/f1707, candles relit, flames settling to the exact sprite by f1928.
flame + unlit composited 'over' reproduce the candle layer (up to filtering of the alpha split).

usage: python3 flames.py MATTE_DIR W H CARD_W CARD_H
"""
import sys, os
import numpy as np
from scipy import ndimage
from godot2d import save_rgba, draw_texture_rect
from chrome import tex
from menu_layout import layout, draw_rects


def flame_mask(t, wide=40):
    """Texture-space flame mask: everything drawn above the wax rim inside the flame's column band
    (flame, its soft halo and dark rim), except the wick; soft-edged."""
    a = t[..., 3]
    lum = t[..., :3].mean(2) * 255
    width = (a > 0.5).sum(1)
    wax_top = int(np.argmax(width > wide))         # first row where the candle body is wide
    upper = a[:max(1, wax_top - 15)] > 0.05        # well above the rim: flame only
    cols = np.nonzero(upper.any(0))[0]
    c0, c1 = max(0, cols.min() - 3), cols.max() + 4
    rows = np.arange(a.shape[0])[:, None]
    band = np.zeros_like(a, bool)
    band[:, c0:c1] = True
    # wick: the dark stroke just above the rim, near the darkest column there
    near = (rows >= wax_top - 22) & (rows < wax_top + 4) & band
    dark = (lum < 95) & (a > 0.4) & near
    wc = int(np.median(np.nonzero(dark)[1])) if dark.any() else (c0 + c1) // 2
    wick = dark & (np.abs(np.arange(a.shape[1])[None, :] - wc) <= 4)
    wick = ndimage.binary_dilation(wick, iterations=1) & (a > 0.2) & (lum < 130)
    m = (band & (rows < wax_top - 1) & ~wick).astype(np.float32)
    # just at the rim: only clearly bright flame pixels (the flame base sits in the cup)
    rim = band & (rows >= wax_top - 1) & (rows < wax_top + 3) & ~wick
    nearw = np.broadcast_to(np.abs(np.arange(a.shape[1])[None, :] - wc) <= 8, a.shape)
    m[rim] = np.clip((lum[rim] - 200.0) / 40.0, 0, 1) * nearw[rim]
    m = ndimage.gaussian_filter(m, 0.5)
    m[wick] = 0
    return np.clip(m, 0, 1), wax_top


def run(mdir, W, H, card_min):
    L = layout(W, H, card_min=card_min)
    rects = draw_rects(L)
    s = L['scale']
    for n in ('candle_left', 'candle_right'):
        if n not in rects:
            continue
        t = tex(n)
        fm, wax_top = flame_mask(t)
        tf = t.copy(); tf[..., 3] *= fm
        tu = t.copy(); tu[..., 3] *= (1 - fm)
        save_rgba(os.path.join(mdir, f'{n}_flame.png'), draw_texture_rect(W, H, tf, rects[n], s, mipmaps=True))
        save_rgba(os.path.join(mdir, f'{n}_unlit.png'), draw_texture_rect(W, H, tu, rects[n], s, mipmaps=True))
        print(n, 'wax rim row', wax_top, 'flame texels', int((fm > 0.5).sum()))
    # the chamberstick on the table edge (iPad aspects only): its flame sits at texels x 95-175, y 0-120
    n = 'table_edge_bottom'
    if n in rects:
        t = tex(n)
        fm = np.zeros(t.shape[:2], np.float32)
        sub, wax_top = flame_mask(t[0:120, 95:175], wide=30)
        fm[0:120, 95:175] = sub
        tf = t.copy(); tf[..., 3] *= fm
        tu = t.copy(); tu[..., 3] *= (1 - fm)
        save_rgba(os.path.join(mdir, f'{n}_flame.png'), draw_texture_rect(W, H, tf, rects[n], s, mipmaps=True))
        save_rgba(os.path.join(mdir, f'{n}_unlit.png'), draw_texture_rect(W, H, tu, rects[n], s, mipmaps=True))
        print(n, 'chamberstick wax rim row', wax_top, 'flame texels', int((fm > 0.5).sum()))


if __name__ == '__main__':
    run(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), (float(sys.argv[4]), float(sys.argv[5])))
