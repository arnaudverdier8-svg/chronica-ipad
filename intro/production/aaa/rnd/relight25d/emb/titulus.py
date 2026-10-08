"""Stitched Latin tituli: glyph skeletons (Cinzel 700) stem-stitched, wobbling baseline, per-letter jitter."""
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
from .core import A, hex_lin, PAL
from .skel import skeleton_paths, merge_paths
from . import stitch as S

FONT = f'{A}/style/fonts/cinzel-latin-700-normal.woff2'


def titulus(m, text, x_mm, y_mm, cap_mm, seed=0, colours=None, width=1.0, spacing=0.6, L=2.6):
    """x_mm, y_mm: left of the baseline. Words alternate colours."""
    PX = m['PX']
    r = np.random.default_rng(seed)
    cols = colours or [hex_lin(PAL['cinematic']['ink_blueblack']['hex']), hex_lin(PAL['cinematic']['ink_redbrown']['hex'])]
    fs = int(cap_mm * PX / 0.70)
    font = ImageFont.truetype(FONT, fs)
    x = x_mm * PX
    word = 0
    for ch in text:
        if ch == ' ':
            x += fs * 0.36; word += 1; continue
        if ch == '.':  # interpunct
            c = np.array([[x + fs * 0.12, y_mm * PX - cap_mm * PX * 0.45]], np.float32)
            S.put(m, np.vstack([c, c + [[0.6 * PX, 0.2 * PX]]]).astype(np.float32), cols[word % 2], width * 0.5, 0.5, 0.4)
            x += fs * 0.35; continue
        bb = font.getbbox(ch)
        w, h = bb[2] - bb[0] + 8, fs + 8
        im = Image.new('L', (w, h), 0)
        ImageDraw.Draw(im).text((4 - bb[0], 4), ch, font=font, fill=255)
        g = np.asarray(im).astype(np.float32) / 255
        g = cv2.GaussianBlur(g, (0, 0), 0.03 * cap_mm * PX) > 0.42     # round off serif tips before skeletonising
        s_ = 1 + r.uniform(-0.06, 0.06)                       # letter height +/- 6 %
        g = cv2.resize(g.astype(np.uint8), None, fx=s_, fy=s_, interpolation=cv2.INTER_NEAREST)
        paths, _ = skeleton_paths(g, 3)
        paths = merge_paths(paths, 2.5)
        ascent = font.getmetrics()[0] * s_
        oy = y_mm * PX - ascent - 4 + r.normal(0, 0.8 * PX * 0.4)   # baseline wobble +/- 0.8 mm
        rot = np.radians(r.normal(0, 1.5))
        for p in paths:
            q = p.astype(np.float32).copy()
            if np.hypot(*np.diff(q, axis=0).T).sum() < 0.20 * cap_mm * PX: continue     # drop serif spurs
            cx, cy = w / 2, h / 2
            qx = (q[:, 0] - cx) * np.cos(rot) - (q[:, 1] - cy) * np.sin(rot) + cx
            qy = (q[:, 0] - cx) * np.sin(rot) + (q[:, 1] - cy) * np.cos(rot) + cy
            q = np.stack([qx + x, qy + oy], 1).astype(np.float32)
            S.stem_path(m, S.smooth_poly(S.resample(q, 0.3 * PX), 2), cols[word % 2] * (1 + r.uniform(-0.06, 0.06)), PX,
                        L=L, width=width, h0=0.45, hamp=0.4, seed=int(r.integers(1 << 30)))
        x += (bb[2] - bb[0]) * s_ + fs * 0.10 * spacing
    return x / PX
