# generate 60 2560x1440 test PNGs (noisy textured gradient + moving bar) so PNG decode cost is realistic
import numpy as np, sys
from PIL import Image, ImageDraw
out = sys.argv[1]; W, H = 2560, 1440
rng = np.random.default_rng(0)
base = np.zeros((H, W, 3), np.float32)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
base[..., 0] = 120 + 80 * xx / W; base[..., 1] = 90 + 60 * yy / H; base[..., 2] = 60
grain = rng.normal(0, 12, (H, W, 1)).astype(np.float32)
for i in range(60):
    a = np.clip(base + grain, 0, 255).astype(np.uint8)
    x0 = int(i / 59 * (W - 200)); a[:, x0:x0 + 200] = (200, 40, 30)
    im = Image.fromarray(a); d = ImageDraw.Draw(im); d.text((100, 100), f'FRAME {i:02d}', fill=(255, 255, 255))
    im.save(f'{out}/f_{i:04d}.png', compress_level=1)
