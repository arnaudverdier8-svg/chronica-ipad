"""Rebuild every piece of the main-menu chrome ('the chronicler's desk') as a full-frame, aligned,
straight-alpha RGBA layer, exactly where and how Godot draws it, and check each against a native
capture of the live menu.

Draw order (main_menu.gd _ready: _build_decor() then the card):
  bar_top < banner_side_left < banner_side_right < candle_left < candle_right
  < lion_statue_left < lion_statue_right < table_edge_bottom < logo_title (valance) < menu_card
"""
import numpy as np
from godot2d import load_rgba, draw_texture_rect, draw_ninepatch
from menu_layout import layout, draw_rects, MARGINS

S = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa'
TEXFILE = {
    'bar_top': 'table_wood/bar_top', 'logo_title': 'table_tapestry/logo_title',
    'banner_side_left': 'table_tapestry/banner_side_left', 'banner_side_right': 'table_tapestry/banner_side_right',
    'candle_left': 'table_backgrounds/candle_left', 'candle_right': 'table_backgrounds/candle_right',
    'lion_statue_left': 'table_backgrounds/lion_statue_left', 'lion_statue_right': 'table_backgrounds/lion_statue_right',
    'table_edge_bottom': 'table_backgrounds/table_edge_bottom', 'menu_card': 'table_parchment/menu_card',
}
# table assets with 'scale' 2 get mipmaps (ui_theme.gd table_tex -> _with_mipmaps); all TextureRects
# use TEXTURE_FILTER_LINEAR_WITH_MIPMAPS. bar_top and menu_card are scale-1 StyleBoxTextures.
MIPMAPPED = {'logo_title', 'banner_side_left', 'banner_side_right', 'candle_left', 'candle_right',
             'lion_statue_left', 'lion_statue_right', 'table_edge_bottom'}
# StyleBoxTexture.modulate_color (ui_theme.gd TABLE_SKIN): the walnut bar is WOOD_DARK
MODULATE = {'bar_top': (0.66, 0.56, 0.5)}
ORDER = ['bar_top', 'banner_side_left', 'banner_side_right', 'candle_left', 'candle_right',
         'lion_statue_left', 'lion_statue_right', 'table_edge_bottom', 'logo_title', 'menu_card']


def tex(name):
    return load_rgba(f'{S}/assets/tex/{TEXFILE[name]}.png')


def build_layers(W, H, card_min=(629.0, 665.0), aa_edges=False, names=None):
    """Returns (L, rects, layers): layers[name] = (H,W,4) straight RGBA of each visible element,
    drawn into Godot's actual draw rect (snapped control rect, keep-aspect sub-rect).
    card_min = the card PanelContainer's minimum size in base units (font-metric dependent:
    fit it per capture with fit_card.py)."""
    L = layout(W, H, card_min=card_min)
    rects = draw_rects(L)
    s = L['scale']
    layers = {}
    for n in ORDER:
        if n not in rects or (names is not None and n not in names):
            continue
        r = rects[n]
        if n in ('bar_top', 'menu_card'):
            lay, _ = draw_ninepatch(W, H, tex(n), r, s, MARGINS[n], aa_edges=aa_edges)
        else:
            lay = draw_texture_rect(W, H, tex(n), r, s, mipmaps=n in MIPMAPPED, aa_edges=aa_edges)
        if n in MODULATE:
            lay[..., :3] *= np.array(MODULATE[n], np.float32)
        layers[n] = lay
    return L, rects, layers


def check_against_capture(cap_rgb, layers, order=ORDER):
    """For each element, compare its own colour with the capture where it is opaque and not covered
    by a later element. Returns {name: (n_px, mean_abs_255, p99_abs_255)}."""
    res = {}
    names = [n for n in order if n in layers]
    for i, n in enumerate(names):
        a = layers[n][..., 3]
        cover = np.zeros_like(a)
        for m in names[i + 1:]:
            cover = np.maximum(cover, layers[m][..., 3])
        sel = (a > 0.999) & (cover < 0.001)
        if n == 'menu_card':
            res[n] = None
            continue
        d = np.abs(layers[n][..., :3][sel] - cap_rgb[sel]) * 255
        res[n] = (int(sel.sum()), float(d.mean()) if d.size else 0.0, float(np.percentile(d, 99)) if d.size else 0.0)
    return res
