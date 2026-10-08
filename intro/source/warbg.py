"""Stitch-rendered battlefield backdrop (2752x1536): dusk sky bands, hills, ground."""
import os, numpy as np, cv2, math
W, H = 2752, 1536
D = os.path.dirname(os.path.abspath(__file__)) + '/'
rng = np.random.default_rng(5)
img = np.zeros((H, W, 3), np.float32)
# sky bands (BGR), top -> horizon
bands = [(60, 30, 60), (80, 40, 110), (60, 40, 150), (90, 60, 170), (70, 70, 190), (80, 100, 215)]
bh = 1000 / len(bands)
for i, c in enumerate(bands):
    y0, y1 = int(i * bh), int((i + 1) * bh)
    img[y0:y1] = c
for _ in range(60000):
    y = rng.uniform(0, 1000); i = min(len(bands) - 1, int(y / bh + rng.normal(0, 0.18)))
    c = np.array(bands[i], np.float32) * rng.uniform(0.82, 1.18)
    x = rng.uniform(-40, W); L = rng.uniform(50, 110)
    p0 = (int(x), int(y)); p1 = (int(x + L), int(y + rng.normal(0, 1.5)))
    cv2.line(img, p0, p1, (c * 0.65).tolist(), 11, cv2.LINE_AA)
    cv2.line(img, p0, p1, c.tolist(), 6, cv2.LINE_AA)
    cv2.line(img, (p0[0], p0[1] - 2), (p1[0], p1[1] - 2), np.minimum(c * 1.3, 255).tolist(), 2, cv2.LINE_AA)
# distant hills
xs = np.arange(W)
hill = 930 - 70 * np.sin(xs / 300.0) - 40 * np.sin(xs / 113.0 + 1.3)
for x in range(0, W, 2):
    pass
mask = (np.arange(H)[:, None] > hill[None, :])
hc = np.array((70, 40, 60), np.float32)
for _ in range(30000):
    x = rng.uniform(0, W); y = rng.uniform(hill[int(min(W - 1, x))], 1080)
    c = hc * rng.uniform(0.8, 1.2); a = rng.normal(-0.2, 0.3); L = rng.uniform(30, 60)
    cv2.line(img, (int(x), int(y)), (int(x + L * math.cos(a)), int(y + L * math.sin(a))), (c * 0.6).tolist(), 9, cv2.LINE_AA)
    cv2.line(img, (int(x), int(y)), (int(x + L * math.cos(a)), int(y + L * math.sin(a))), c.tolist(), 4, cv2.LINE_AA)
pts = np.stack([xs, hill], 1).astype(np.int32)
cv2.polylines(img, [pts], False, (60, 140, 200), 5, cv2.LINE_AA)
# ground
gy = 1060 - 25 * np.sin(xs / 400.0)
for _ in range(70000):
    x = rng.uniform(0, W); y = rng.uniform(gy[int(min(W - 1, x))], H)
    t = (y - 1060) / 480
    c = np.array((40, 90, 95), np.float32) * (1 - t) + np.array((30, 60, 85), np.float32) * t
    c *= rng.uniform(0.8, 1.25); a = rng.normal(-1.2, 0.5); L = rng.uniform(30, 55)
    p1 = (int(x + L * math.cos(a)), int(y + L * math.sin(a)))
    cv2.line(img, (int(x), int(y)), p1, (c * 0.6).tolist(), 9, cv2.LINE_AA)
    cv2.line(img, (int(x), int(y)), p1, c.tolist(), 4, cv2.LINE_AA)
gpts = np.stack([xs, gy], 1).astype(np.int32)
cv2.polylines(img, [gpts], False, (60, 140, 200), 6, cv2.LINE_AA)
# broken spears & fallen shields scattered on ground
for _ in range(26):
    x = rng.uniform(80, W - 80); y = rng.uniform(1180, 1480); a = rng.uniform(-0.6, 0.6); L = rng.uniform(80, 180)
    p1 = (int(x + L * math.cos(a)), int(y + L * math.sin(a) * 0.3))
    cv2.line(img, (int(x), int(y)), p1, (20, 40, 70), 9, cv2.LINE_AA); cv2.line(img, (int(x), int(y)), p1, (40, 80, 120), 4, cv2.LINE_AA)
# linen weave + edge of the tapestry
yy, xx = np.mgrid[0:H, 0:W]
img += (np.sin(xx * 1.7) * np.sin(yy * 1.7) * 4)[..., None]
cv2.imwrite(D + 'war_bg.png', np.clip(img, 0, 255).astype(np.uint8))
print('ok')
