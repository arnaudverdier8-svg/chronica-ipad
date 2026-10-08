"""Python port of CHRONICA ui/main_menu.gd _layout() (decoded source: aaa/game/raw/main_menu.gd.txt)
for the no-save state (5 buttons: New Game, How to Play, Settings, Credits, Quit), non-phone.

Godot project: stretch mode canvas_items, aspect expand, base 1600x900, so for a W x H
viewport the canvas scale is s = min(W/1600, H/900) and the visible rect is vr = (W/s, H/s).
All rects below are in BASE units; multiply by s for screen pixels.
"""
import json

# texture sizes (aaa/game/raw/assets__ui__table__manifest.gd.txt; files in aaa/assets/tex/)
TEX = {
    'logo_title': (1741, 520),
    'banner_side_left': (240, 642), 'banner_side_right': (240, 675),
    'candle_left': (200, 720), 'candle_right': (212, 720),
    'lion_statue_left': (361, 520), 'lion_statue_right': (364, 520),
    'table_edge_bottom': (1336, 320),
    'bar_top': (703, 80), 'menu_card': (260, 340),
}
# StyleBoxTexture margins [left, top, right, bottom] (manifest 'margins')
MARGINS = {'bar_top': [65, 6, 44, 5], 'menu_card': [46, 47, 48, 56]}
# PanelContainer minimum size of the 5-button card (measured on the live menu; the content is
# title_mark + subtitle + rule + 5 x (470x64) buttons + footer, content margins 44/34/44/30)
CARD_MIN_5BTN = (627.0, 661.0)


def canvas_scale(W, H):
    s = min(W / 1600.0, H / 900.0)
    return s, (W / s, H / s)


def _w(name, h):
    tw, th = TEX[name]
    return h * tw / th


def _intersects(a, b):  # Rect2.intersects (strict)
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def _grow(r, d):
    return (r[0] - d, r[1] - d, r[2] + 2 * d, r[3] + 2 * d)


def _encloses(vr, r):
    return r[0] >= 0 and r[1] >= 0 and r[0] + r[2] <= vr[0] and r[1] + r[3] <= vr[1]


def layout(W, H, card_min=CARD_MIN_5BTN):
    s, vr = canvas_scale(W, H)
    ch = card_min[1]
    tall = vr[1] >= ch + 230
    out = {'viewport_px': [W, H], 'scale': s, 'vr_base': list(vr), 'tall': tall, 'base': {}, 'visible': {}}
    B = out['base']
    if not tall:
        B['menu_card'] = (70.0, max(10.0, (vr[1] - ch) * 0.5), *card_min)  # chrome hidden
        return out
    B['bar_top'] = (0.0, 0.0, vr[0], 80.0)
    lw = min(620.0, vr[0] * 0.42)
    logo_h = lw * TEX['logo_title'][1] / TEX['logo_title'][0]
    B['logo_title'] = ((vr[0] - lw) * 0.5, 0.0, lw, logo_h)
    side = 140.0
    top = max(logo_h + 14.0, 96.0)
    card = (side, top, card_min[0], card_min[1])
    B['menu_card'] = card
    vis = out['visible']
    vis['bar_top'] = vis['logo_title'] = vis['menu_card'] = True

    def put(n, r):
        B[n] = r
        vis[n] = (not _intersects(_grow(r, 8), card)) and _encloses(vr, r)

    bh = min(280.0, vr[1] * 0.24)
    put('banner_side_left', (10.0, 40.0, _w('banner_side_left', bh), bh))
    w = _w('banner_side_right', bh)
    put('banner_side_right', (vr[0] - w - 10.0, 40.0, w, bh))
    cdh = min(280.0, vr[1] * 0.23)
    for n in ('candle_left', 'candle_right'):
        w = _w(n, cdh)
        x = 6.0 if n == 'candle_left' else vr[0] - w - 6.0
        put(n, (x, vr[1] * 0.5 - cdh * 0.1, w, cdh))
    lh = min(230.0, vr[1] * 0.19)
    for n in ('lion_statue_left', 'lion_statue_right'):
        w = _w(n, lh)
        x = 4.0 if n == 'lion_statue_left' else vr[0] - w - 4.0
        put(n, (x, vr[1] - lh - 2.0, w, lh))
    th = min(150.0, vr[1] - (card[1] + card[3]) - 16.0)
    w = _w('table_edge_bottom', th) if th > 0 else 0.0
    x0 = card[0] + card[2] * 0.5 - w * 0.5
    ll = B['lion_statue_left']
    if vis.get('lion_statue_left'):
        x0 = max(x0, ll[0] + ll[2] + 6.0)
    put('table_edge_bottom', (x0, vr[1] - th, w, th))
    if th < 90:
        vis['table_edge_bottom'] = False
    return out


def _ground(v):
    """Godot Math::round (half away from zero)."""
    import math
    return math.floor(v + 0.5) if v >= 0 else -math.floor(-v + 0.5)


def snapped(r):
    """Control rect as drawn by this Godot 4.7 web build: the POSITION is rounded to whole canvas
    (base) units, the size is kept as is. (Established on the native 2560x1440 capture: this model
    fits every chrome element to 0.4-0.7/255 mean abs error; rounding the size as well, or not
    rounding the position, leaves 2.5-6/255 errors with visible sub-pixel shifts.)"""
    return (float(_ground(r[0])), float(_ground(r[1])), r[2], r[3])


def keep_aspect_centered(r, tex_wh):
    """TextureRect STRETCH_KEEP_ASPECT_CENTERED draw rect (texture_rect.cpp: the fitted size is
    truncated to int, then centred with a float offset)."""
    x, y, w, h = r
    tw, th = tex_wh
    tex_w = int(tw * h / th)
    tex_h = int(h)
    if tex_w > w:
        tex_w = int(w)
        tex_h = int(th * tex_w / tw)
    return (x + (w - tex_w) / 2.0, y + (h - tex_h) / 2.0, float(tex_w), float(tex_h))


def draw_rects(L):
    """Where Godot actually draws each visible element (base units): snapped control rects, and
    for TextureRects the keep-aspect-centred sub-rect. Styleboxes (bar, card) fill the control."""
    out = {}
    for n, r in L['base'].items():
        if not L['visible'].get(n):
            continue
        sr = snapped(r)
        out[n] = sr if n in ('bar_top', 'menu_card') else keep_aspect_centered(sr, TEX[n])
    return out


def px_rects(L):
    s = L['scale']
    return {k: [v * s for v in r] for k, r in L['base'].items()}


if __name__ == '__main__':
    import sys
    W, H = int(sys.argv[1]), int(sys.argv[2])
    L = layout(W, H)
    L['px'] = px_rects(L)
    print(json.dumps(L, indent=1))
