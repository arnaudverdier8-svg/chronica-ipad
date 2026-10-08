"""Paint an embroidered map texture from individual thread strokes.
Outputs map_albedo.png and map_height.png (same size) plus map_layout.json
(coordinates of rivers, roads, forests, realms) for the Blender scene."""
import os, json, math
import numpy as np, cv2

W, H = 4096, 2304
rng = np.random.default_rng(7)
OUT = os.path.dirname(os.path.abspath(__file__)) + '/'

def P(u, v):
    return (u * W, v * H)

def catmull(pts, n=40):
    pts = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = map(np.array, pts[i - 1:i + 3])
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(np.array(pts[-2]))
    return np.array(out)

# ---------------- layout (u,v in 0..1, v down) ----------------
river = [(0.86, 0.04), (0.74, 0.18), (0.57, 0.26), (0.42, 0.34), (0.34, 0.52), (0.27, 0.70), (0.16, 0.86)]
coast = [(0.0, 0.64), (0.10, 0.70), (0.17, 0.80), (0.22, 0.90), (0.26, 1.0)]
road_e = [(0.53, 0.51), (0.62, 0.53), (0.70, 0.56), (0.78, 0.55), (0.86, 0.58), (0.99, 0.60)]
road_n = [(0.50, 0.46), (0.52, 0.36), (0.60, 0.26), (0.66, 0.14)]
road_w = [(0.47, 0.50), (0.40, 0.49), (0.33, 0.47), (0.22, 0.42), (0.08, 0.40)]
road_s = [(0.50, 0.54), (0.48, 0.66), (0.52, 0.80), (0.50, 0.98)]
forests = [(0.78, 0.66, 0.11, 0.11), (0.15, 0.20, 0.10, 0.12), (0.62, 0.85, 0.09, 0.07), (0.35, 0.78, 0.06, 0.06)]
fields = [(0.43, 0.60, 0.07, 0.05, 0.6), (0.58, 0.40, 0.06, 0.05, -0.5), (0.36, 0.40, 0.05, 0.04, 0.2), (0.60, 0.66, 0.05, 0.04, 1.1)]
mountains = (0.84, 0.20, 0.15, 0.17)
# realm borders radiate from a central clearing
borders = {
    'n': [(0.50, 0.40), (0.49, 0.28), (0.53, 0.14), (0.50, 0.0)],
    's': [(0.50, 0.60), (0.52, 0.72), (0.47, 0.86), (0.49, 1.0)],
    'w': [(0.42, 0.50), (0.30, 0.52), (0.16, 0.49), (0.0, 0.51)],
    'e': [(0.58, 0.50), (0.70, 0.47), (0.84, 0.50), (1.0, 0.48)],
}

# ---------------- region colour + direction fields ----------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
u, v = xx / W, yy / H

def noise(scale, seed):
    r = np.random.default_rng(seed)
    small = r.random((int(H / scale) + 2, int(W / scale) + 2)).astype(np.float32)
    return cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC)

n1, n2, n3 = noise(260, 1), noise(90, 2), noise(30, 3)
# meadow: several greens
g = np.clip(0.55 * n1 + 0.3 * n2 + 0.15 * n3, 0, 1)
meadow_a = np.array([74, 112, 52], np.float32)   # deep green
meadow_b = np.array([128, 152, 70], np.float32)  # spring green
meadow_c = np.array([160, 160, 88], np.float32)  # olive
col = (meadow_a * (1 - g[..., None]) + meadow_b * g[..., None])
col = col * (1 - 0.25 * n3[..., None]) + meadow_c * 0.25 * n3[..., None]
ang = (n1 * 2.2 + n2 * 0.8) * math.pi  # flowing grass direction
kind = np.zeros((H, W), np.uint8)  # 0 meadow,1 water,2 sea,3 field,4 forest,5 sand,6 clearing

def poly_mask(pts_uv, closed=True, thick=0):
    m = np.zeros((H, W), np.uint8)
    pts = np.array([P(*p) for p in pts_uv], np.int32)
    if thick:
        cv2.polylines(m, [pts], closed, 255, thick, cv2.LINE_AA)
    else:
        cv2.fillPoly(m, [pts], 255)
    return m > 127

# sea (bottom-left)
cs = catmull([P(*p) for p in coast], 30)
sea_poly = np.vstack([cs, [[0, H]], [[0, cs[0][1]]]]).astype(np.int32)
sea = np.zeros((H, W), np.uint8); cv2.fillPoly(sea, [sea_poly], 255); sea = sea > 0
sand = np.zeros((H, W), np.uint8); cv2.polylines(sand, [cs.astype(np.int32)], False, 255, 70); sand = (sand > 0) & ~sea
kind[sand] = 5
kind[sea] = 2

# river
rv = catmull([P(*p) for p in river], 40)
rmask = np.zeros((H, W), np.uint8)
for i in range(len(rv) - 1):
    t = i / len(rv)
    cv2.line(rmask, tuple(rv[i].astype(int)), tuple(rv[i + 1].astype(int)), 255, int(26 + 46 * t), cv2.LINE_AA)
river_m = rmask > 127
kind[river_m & ~sea] = 1

# fields
for (fu, fv, fw, fh, fa) in fields:
    c, s = math.cos(fa), math.sin(fa)
    du, dv = (u - fu) * W, (v - fv) * H
    ru, rvv = du * c + dv * s, -du * s + dv * c
    m = (np.abs(ru) < fw * W) & (np.abs(rvv) < fh * H) & (kind == 0)
    kind[m] = 3
    ang[m] = fa + 0.8 + 0.6 * (np.floor(ru[m] / 70) % 2)  # furrows alternate direction

# forests (ground under 3D trees)
for (fu, fv, fw, fh) in forests:
    d = ((u - fu) / fw) ** 2 + ((v - fv) / fh) ** 2 + (n2 - 0.5) * 0.6
    kind[(d < 1) & (kind == 0)] = 4

# central clearing
dc = ((u - 0.5) * 16 / 9) ** 2 + (v - 0.5) ** 2
kind[(dc < 0.0042) & (kind == 0)] = 6

# colours per kind
water = np.array([46, 78, 140], np.float32); water2 = np.array([78, 120, 178], np.float32)
seac = np.array([24, 42, 92], np.float32); sea2 = np.array([44, 74, 132], np.float32)
fieldc = np.array([204, 156, 58], np.float32); field2 = np.array([226, 190, 96], np.float32)
forestc = np.array([40, 74, 40], np.float32)
sandc = np.array([214, 190, 140], np.float32)
clear = np.array([150, 160, 92], np.float32)
for k, a, b in [(1, water, water2), (2, seac, sea2), (3, fieldc, field2)]:
    m = kind == k
    col[m] = a * (1 - n3[m, None]) + b * n3[m, None]
col[kind == 4] = forestc * (0.8 + 0.4 * n3[kind == 4, None])
col[kind == 5] = sandc * (0.9 + 0.2 * n3[kind == 5, None])
col[kind == 6] = clear * (0.92 + 0.16 * n3[kind == 6, None])

# directions: river flows along its path, sea in horizontal waves
dist, lab = None, None
rv_pts = rv
rdir = np.zeros(len(rv)); rdir[:-1] = np.arctan2(np.diff(rv[:, 1]), np.diff(rv[:, 0])); rdir[-1] = rdir[-2]
ys, xs = np.nonzero(kind == 1)
if len(xs):
    # nearest river sample via coarse search
    idx = np.argmin((xs[:, None] - rv[None, :, 0]) ** 2 + (ys[:, None] - rv[None, :, 1]) ** 2, axis=1) if len(xs) < 400000 else None
    ang[ys, xs] = rdir[idx]
ang[kind == 2] = 0.08 * np.sin(u[kind == 2] * 40)
ang[kind == 5] = 0.3

# ---------------- stitch rendering ----------------
img = np.zeros((H, W, 3), np.float32) + col.mean(axis=(0, 1))
hgt = np.zeros((H, W), np.float32)

def stitches(mask, length, width, count, jitter=0.25, shade=1.0, seed=0):
    r = np.random.default_rng(seed)
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return
    pick = r.integers(0, len(xs), count)
    for i in pick:
        x, y = int(xs[i]), int(ys[i])
        a = ang[y, x] + r.normal(0, jitter)
        L = length * r.uniform(0.75, 1.25)
        dx, dy = math.cos(a) * L / 2, math.sin(a) * L / 2
        p0 = (int(x - dx), int(y - dy)); p1 = (int(x + dx), int(y + dy))
        c = col[y, x] * r.uniform(0.9, 1.1) * shade
        cv2.line(img, p0, p1, (c * 0.62).tolist(), width, cv2.LINE_AA)
        cv2.line(hgt, p0, p1, 0.45, width, cv2.LINE_AA)
        cv2.line(img, p0, p1, c.tolist(), max(1, int(width * 0.62)), cv2.LINE_AA)
        cv2.line(hgt, p0, p1, 0.8, max(1, int(width * 0.62)), cv2.LINE_AA)
        hx, hy = int(-math.sin(a) * width * 0.15), int(math.cos(a) * width * 0.15)
        cv2.line(img, (p0[0] - hx, p0[1] - hy), (p1[0] - hx, p1[1] - hy), np.minimum(c * 1.32 + 12, 255).tolist(), max(1, int(width * 0.22)), cv2.LINE_AA)
        cv2.line(hgt, (p0[0] - hx, p0[1] - hy), (p1[0] - hx, p1[1] - hy), 1.0, max(1, int(width * 0.22)), cv2.LINE_AA)

area = lambda k: int((kind == k).sum())
stitches(kind == 0, 46, 9, area(0) // 150, 0.22, seed=1)
stitches(kind == 6, 40, 9, area(6) // 140, 0.5, seed=2)
stitches(kind == 3, 40, 8, area(3) // 120, 0.06, seed=3)
stitches(kind == 4, 18, 9, area(4) // 60, 3.0, seed=4)
stitches(kind == 5, 26, 7, area(5) // 90, 0.6, seed=5)
stitches(kind == 1, 54, 8, area(1) // 110, 0.08, seed=6)
stitches(kind == 2, 70, 9, area(2) // 170, 0.05, seed=7)

def couched(pts_px, color, width=7, seg=11, dash=None, seed=0):
    """Couched thread: a thick cord with small diagonal tie stitches."""
    pts = pts_px.astype(np.int32)
    c = np.array(color, np.float32)
    if dash is None:
        cv2.polylines(img, [pts], False, (c * 0.55).tolist(), width + 4, cv2.LINE_AA)
        cv2.polylines(hgt, [pts], False, 0.6, width + 4, cv2.LINE_AA)
        cv2.polylines(img, [pts], False, c.tolist(), width, cv2.LINE_AA)
        cv2.polylines(hgt, [pts], False, 0.95, width, cv2.LINE_AA)
    # twist highlights / ties along the path
    acc = 0.0
    for i in range(len(pts) - 1):
        p, q = pts[i].astype(float), pts[i + 1].astype(float)
        d = np.linalg.norm(q - p)
        if d == 0:
            continue
        t = (q - p) / d
        nrm = np.array([-t[1], t[0]])
        s = 0.0
        while s < d:
            pos = p + t * s
            k = int((acc + s) // seg)
            if dash is not None:
                on = (k % (dash[0] + dash[1])) < dash[0]
                if on:
                    a = pos - t * seg * 0.45; b = pos + t * seg * 0.45
                    cv2.line(img, tuple(a.astype(int)), tuple(b.astype(int)), (c * 0.55).tolist(), width + 3, cv2.LINE_AA)
                    cv2.line(img, tuple(a.astype(int)), tuple(b.astype(int)), c.tolist(), width, cv2.LINE_AA)
                    cv2.line(hgt, tuple(a.astype(int)), tuple(b.astype(int)), 1.0, width, cv2.LINE_AA)
            else:
                a = pos + (t * 0.6 + nrm) * width * 0.6; b = pos - (t * 0.6 + nrm) * width * 0.6
                cv2.line(img, tuple(a.astype(int)), tuple(b.astype(int)), np.minimum(c * 1.35 + 20, 255).tolist(), 2, cv2.LINE_AA)
            s += seg
        acc += d

GOLD = (212, 168, 72)
# coast + river banks in couched gold
couched(cs, GOLD, 7, 12)
offs = []
for side in (-1, 1):
    bank = []
    for i in range(len(rv) - 1):
        t = rv[i + 1] - rv[i]; t = t / (np.linalg.norm(t) + 1e-6)
        w = (26 + 46 * i / len(rv)) / 2 + 4
        bank.append(rv[i] + np.array([-t[1], t[0]]) * w * side)
    couched(np.array(bank), GOLD, 5, 10)
# sea ripples
r = np.random.default_rng(11)
for _ in range(90):
    x = r.uniform(0, 0.24) * W; y = r.uniform(0.74, 1.0) * H
    if not sea[int(min(y, H - 1)), int(x)]:
        continue
    pts = np.array([[x + k * 14, y + 6 * math.sin(k * 0.9)] for k in range(8)])
    couched(pts, (150, 176, 214), 3, 9)
# roads: running stitch in cream with dark edge
roads = {}
for name, rp in [('e', road_e), ('n', road_n), ('w', road_w), ('s', road_s)]:
    pts = catmull([P(*p) for p in rp], 30)
    roads[name] = (pts / [W, H]).tolist()
    cv2.polylines(img, [pts.astype(np.int32)], False, (118, 92, 64), 30, cv2.LINE_AA)
    cv2.polylines(hgt, [pts.astype(np.int32)], False, 0.35, 30, cv2.LINE_AA)
    couched(pts, (226, 206, 160), 10, 22, dash=(1, 1))
# realm borders: dashed couched threads in realm colours
REALM = {'n': (170, 40, 36), 'e': (40, 88, 170), 's': (36, 120, 70), 'w': (200, 146, 40)}
for k, bp in borders.items():
    pts = catmull([P(*p) for p in bp], 30)
    couched(pts, (60, 40, 30), 4, 16, dash=(2, 1))
    couched(pts + 6, (226, 196, 120), 3, 16, dash=(2, 1))
# clearing ring
cpts = np.array([[W * 0.5 + math.cos(a) * 0.065 * H * 1.0 * 1.0, H * 0.5 + math.sin(a) * 0.065 * H] for a in np.linspace(0, 2 * math.pi, 120)])
couched(cpts, GOLD, 6, 12)

# linen showing through very slightly + fabric weave
weave = (np.sin(xx * 1.6) * np.sin(yy * 1.6)) * 4
img += weave[..., None]
img = np.clip(img, 0, 255)
hgt = cv2.GaussianBlur(hgt, (0, 0), 0.8)

# outer border band: linen with a dark wool frame (map edge)
edge = 46
frame = np.zeros((H, W), bool); frame[:edge] = frame[-edge:] = True; frame[:, :edge] = frame[:, -edge:] = True
img[frame] = np.array([60, 34, 30]) * (0.85 + 0.3 * n3[frame, None])
inner = np.zeros((H, W), np.uint8)
cv2.rectangle(inner, (edge, edge), (W - edge, H - edge), 255, 8)
img[inner > 0] = GOLD
hgt[inner > 0] = 1

cv2.imwrite(OUT + 'map_albedo.png', cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2BGR))
cv2.imwrite(OUT + 'map_height.png', (np.clip(hgt, 0, 1) * 65535).astype(np.uint16))

layout = {
    'roads': roads,
    'river': (rv / [W, H]).tolist(),
    'forests': forests,
    'mountains': mountains,
    'fields': fields,
    'borders': {k: (catmull([P(*p) for p in bp], 30) / [W, H]).tolist() for k, bp in borders.items()},
    'kind_small': cv2.resize(kind, (512, 288), interpolation=cv2.INTER_NEAREST).tolist(),
}
json.dump(layout, open(OUT + 'map_layout.json', 'w'))
print('ok')
