"""Minimal re-implementation of the parts of Godot 4's 2D canvas renderer (GL Compatibility,
which is what the web export uses) needed to rebuild the CHRONICA main-menu chrome:

* TextureRect (EXPAND_IGNORE_SIZE, STRETCH_KEEP_ASPECT_CENTERED, aspect already matched) with
  TEXTURE_FILTER_LINEAR_WITH_MIPMAPS (trilinear; Godot box-filter mip chain),
* StyleBoxTexture nine-patch, AXIS_STRETCH_MODE_STRETCH, exactly as canvas.glsl
  map_ninepatch_axis() does it (margins in local canvas units = texture texels),
* 'over' blending in sRGB-encoded space (the Compatibility renderer does 2D in sRGB space).

Coordinates: every draw takes a rect in BASE canvas units (Godot stretch mode canvas_items,
aspect expand, base 1600x900) and the viewport scale s (screen px per base unit). Pixel
centres (x+0.5, y+0.5) are mapped back to local units, as the rasteriser does.
All images are float32 arrays in [0,1], straight (non-premultiplied) RGBA.
"""
import numpy as np
from PIL import Image


def load_rgba(path):
    im = Image.open(path).convert('RGBA')
    return np.asarray(im).astype(np.float32) / 255.0


def save_rgba(path, a):
    Image.fromarray(np.clip(np.rint(a * 255.0), 0, 255).astype(np.uint8), 'RGBA' if a.shape[2] == 4 else 'RGB').save(path)


def mip_chain(t):
    """Godot Image.generate_mipmaps(): each level is floor(w/2) x floor(h/2) of the previous,
    a plain 2x2 box average (odd last row/column dropped)."""
    mips = [t]
    while min(mips[-1].shape[:2]) > 1:
        m = mips[-1]
        h, w = m.shape[0] // 2, m.shape[1] // 2
        m = m[:h * 2, :w * 2]
        mips.append(0.25 * (m[0::2, 0::2] + m[1::2, 0::2] + m[0::2, 1::2] + m[1::2, 1::2]))
    return mips


def bilinear(t, u, v):
    """Sample texture t (H,W,C) at normalised coords u,v (arrays), clamp-to-edge, GL texel centres."""
    h, w = t.shape[:2]
    x = u * w - 0.5
    y = v * h - 0.5
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx = (x - x0)[..., None].astype(np.float32)
    fy = (y - y0)[..., None].astype(np.float32)
    x0c = np.clip(x0, 0, w - 1); x1c = np.clip(x0 + 1, 0, w - 1)
    y0c = np.clip(y0, 0, h - 1); y1c = np.clip(y0 + 1, 0, h - 1)
    a = t[y0c, x0c]; b = t[y0c, x1c]; c = t[y1c, x0c]; d = t[y1c, x1c]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def trilinear(mips, u, v, lod):
    lod = max(0.0, float(lod))
    l0 = int(np.floor(lod)); f = lod - l0
    l0 = min(l0, len(mips) - 1); l1 = min(l0 + 1, len(mips) - 1)
    s0 = bilinear(mips[l0], u, v)
    if f < 1e-6 or l1 == l0:
        return s0
    return s0 * (1 - f) + bilinear(mips[l1], u, v) * f


def _grid(rect_px, W, H):
    """Integer pixel window covering rect_px=(x,y,w,h) in screen px, and pixel-centre coords."""
    x, y, w, h = rect_px
    x0 = max(0, int(np.floor(x))); y0 = max(0, int(np.floor(y)))
    x1 = min(W, int(np.ceil(x + w))); y1 = min(H, int(np.ceil(y + h)))
    xs = np.arange(x0, x1, dtype=np.float64) + 0.5
    ys = np.arange(y0, y1, dtype=np.float64) + 0.5
    return x0, y0, x1, y1, xs, ys


def coverage_1d(c, a, b):
    """Fraction of the pixel whose centre is c covered by [a,b] -- used only for the matte
    alpha at the rect edges (GL itself has no AA: a pixel is in iff its centre is inside)."""
    return np.clip(np.minimum(c + 0.5, b) - np.maximum(c - 0.5, a), 0.0, 1.0)


def draw_texture_rect(W, H, tex, rect_base, s, mipmaps=True, aa_edges=False):
    """Layer (H,W,4) straight RGBA with tex drawn into rect_base (base units) at scale s."""
    out = np.zeros((H, W, 4), np.float32)
    rx, ry, rw, rh = [v * s for v in rect_base]
    x0, y0, x1, y1, xs, ys = _grid((rx, ry, rw, rh), W, H)
    if x1 <= x0 or y1 <= y0:
        return out
    U, V = np.meshgrid((xs - rx) / rw, (ys - ry) / rh)
    th, tw = tex.shape[:2]
    if mipmaps:
        lod = np.log2(max(tw / rw, th / rh, 1e-9))
        smp = trilinear(mip_chain(tex), U, V, lod)
    else:
        smp = bilinear(tex, U, V)
    if aa_edges:
        cov = coverage_1d(xs, rx, rx + rw)[None, :] * coverage_1d(ys, ry, ry + rh)[:, None]
    else:
        inside_x = (xs >= rx) & (xs < rx + rw)
        inside_y = (ys >= ry) & (ys < ry + rh)
        cov = (inside_y[:, None] & inside_x[None, :]).astype(np.float32)
    smp[..., 3] *= cov
    out[y0:y1, x0:x1] = smp
    return out


def _np_axis(pixel, draw_size, tex_size, m0, m1):
    """canvas.glsl map_ninepatch_axis, AXIS_STRETCH_MODE_STRETCH; returns texel coordinate."""
    out = np.empty_like(pixel)
    a = pixel < m0
    b = pixel >= draw_size - m1
    c = ~(a | b)
    out[a] = pixel[a]
    out[b] = tex_size - (draw_size - pixel[b])
    ratio = (pixel[c] - m0) / (draw_size - m0 - m1)
    out[c] = m0 + ratio * (tex_size - m0 - m1)
    return out


def draw_ninepatch(W, H, tex, rect_base, s, margins, mipmaps=False, aa_edges=False):
    """StyleBoxTexture (stretch) of tex into rect_base. margins = [left, top, right, bottom] texels."""
    out = np.zeros((H, W, 4), np.float32)
    rx, ry, rw, rh = [v * s for v in rect_base]
    x0, y0, x1, y1, xs, ys = _grid((rx, ry, rw, rh), W, H)
    th, tw = tex.shape[:2]
    lx = (xs - rx) / s  # local canvas units
    ly = (ys - ry) / s
    tx = _np_axis(lx, rect_base[2], tw, margins[0], margins[2])
    ty = _np_axis(ly, rect_base[3], th, margins[1], margins[3])
    U, V = np.meshgrid(tx / tw, ty / th)
    if mipmaps:
        smp = trilinear(mip_chain(tex), U, V, np.log2(max(1.0 / s, 1e-9)))
    else:
        smp = bilinear(tex, U, V)
    if aa_edges:
        cov = coverage_1d(xs, rx, rx + rw)[None, :] * coverage_1d(ys, ry, ry + rh)[:, None]
    else:
        inside_x = (xs >= rx) & (xs < rx + rw)
        inside_y = (ys >= ry) & (ys < ry + rh)
        cov = (inside_y[:, None] & inside_x[None, :]).astype(np.float32)
    smp[..., 3] *= cov
    out[y0:y1, x0:x1] = smp
    # texel-space coordinates are useful to build masks of texture regions
    return out, (x0, y0, x1, y1, tx, ty)


def over(dst_rgb, layer):
    a = layer[..., 3:4]
    return layer[..., :3] * a + dst_rgb * (1 - a)
