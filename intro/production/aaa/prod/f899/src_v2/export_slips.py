"""Cut the front-rank slips out of the war sheet's record and export everything the Eevee scene needs (pipeline 7.2 / 7.5):

per slip  * albedo (linear, aged, RGBA), tangent normal map (high-pass height), material map (R rough, G metal, B sheen), AO-baked
            micro-visibility, all at 10 px/mm, from an exact replay of the slip's own stitches on an empty base (own alpha);
          * a displaced mesh (low-pass height as vertex Z, boundary vertices snapped to the alpha contour, 1.4 mm felt backing + rim);
          * the standing transform (hinge at the feet, tilt ~70 deg, small yaw) as a 4x4;
          * thread tethers: snapped stubs curling on the cloth and hanging from the slip's lower edge, built from the real strand
            ends (needle-hole positions of the ghost), as tube meshes in world coordinates.

    python3 export_slips.py [--out DIR]
"""
import os, sys, json, math, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bkit                                                           # noqa
import numpy as np, cv2                                               # noqa
from chron.maps import MapSet                                         # noqa
from chron.anim.groupanim import GroupAnim                            # noqa
from chron.record import replay                                       # noqa
from chron.shade import normals, ambient_occlusion, lod_height        # noqa
from chron.ageing import apply_age                                    # noqa
from chron import stitch as S                                         # noqa
from chron.color import hex_lin, chroma_cap, lin2oklab                # noqa
import camera as CAM                                                  # noqa

ROOT = os.path.dirname(HERE)
PX = 10.0
THICK = 1.1
CHROMA_CAP = 0.165

# per-slip standing pose: tilt from the cloth (deg), yaw about the vertical (deg, + = counter-clockwise seen from above)
POSE = {
    'slip0': dict(tilt=70.0, yaw=-4.0), 'slip1': dict(tilt=69.0, yaw=4.0), 'slip2': dict(tilt=71.0, yaw=-3.0),
    'slip3': dict(tilt=68.0, yaw=5.0), 'slip4': dict(tilt=70.0, yaw=-5.0), 'slip5': dict(tilt=72.0, yaw=3.0),
    'slip6': dict(tilt=69.0, yaw=4.0), 'slip7': dict(tilt=70.0, yaw=-4.0), 'slip8': dict(tilt=71.0, yaw=3.0),
    'slip9': dict(tilt=68.0, yaw=-5.0), 'slip10': dict(tilt=70.0, yaw=0.0), 'slip11': dict(tilt=70.0, yaw=0.0),
}


def slip_maps(G, group):
    ga = GroupAnim(G, [group])
    x0, y0, x1, y1 = ga.bbox
    H, W = y1 - y0, x1 - x0
    m = dict(h=np.full((H, W), -10.0, np.float32), alb=np.zeros((H, W, 3), np.float32), T=np.zeros((H, W, 2), np.float32),
             mat=np.zeros((H, W), np.uint8), cov=np.zeros((H, W), np.float32), sid=np.zeros((H, W), np.int32),
             sfr=np.zeros((H, W), np.float32), base=np.zeros((H, W), np.float32), stamp=np.zeros((H, W), np.int32), PX=PX)
    replay(m, ga.rec, ga.sel, x0, y0)
    return ga, m, (x0, y0)


def finish_slip_maps(m, age_amount):
    """alpha, felt filler, aged albedo, high-pass normals, AO.  Returns dict of arrays at 10 px/mm."""
    h = m['h']
    a = (h > -5).astype(np.float32)
    a = cv2.morphologyEx(a, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    # keep the biggest component (drop stray strands)
    n, cc, st, _ = cv2.connectedComponentsWithStats(a.astype(np.uint8), connectivity=8)
    keep = np.zeros_like(a, bool)
    for i in range(1, n):
        if st[i, 4] > 0.05 * st[1:, 4].max():
            keep |= cc == i
    a = np.where(keep, a, 0).astype(np.float32)
    ff = a.copy().astype(np.uint8); hh, ww = ff.shape
    m2 = np.zeros((hh + 2, ww + 2), np.uint8)
    cv2.floodFill(ff, m2, (0, 0), 1)
    a = np.maximum(a, (1 - ff).astype(np.float32))            # fill interior holes
    inside = a > 0
    gap = inside & (h <= -5)                                   # felt showing between strands
    alb = chroma_cap(m['alb'].copy(), CHROMA_CAP)
    wl = (h > -5).astype(np.float32)
    num = cv2.GaussianBlur(alb * wl[..., None], (0, 0), 0.5 * PX)
    den = cv2.GaussianBlur(wl, (0, 0), 0.5 * PX)[..., None] + 1e-4
    local = num / den
    alb = np.where(gap[..., None], local * 0.55, alb)
    alb = np.where(inside[..., None], alb, local)
    mat = np.where(inside & (h > -5), m['mat'], 8).astype(np.uint8)       # 8 = felt
    mat = np.where(inside, mat, 8).astype(np.uint8)
    hf = np.where(inside & (h > -5), np.maximum(h, 0.0), 0.0).astype(np.float32)
    # fill the height of the gaps with the neighbourhood minimum so the felt reads as a floor
    hf = np.where(inside, hf, 0.0)
    if age_amount > 0:
        alb = apply_age(alb, np.where(mat == 8, 1, mat), age_amount, None)
    hl, _ = lod_height(hf, PX, 4.65 * 1.2)
    N = normals(hl, PX, blur=0.55)
    ao = ambient_occlusion(hf, PX)
    return dict(alpha=a, alb=alb.astype(np.float32), h=hf, mat=mat, N=N, ao=ao, T=m['T'], cov=m['cov'])


MAT_PARAMS = {0: (0.75, 0.0, 0.2), 1: (0.72, 0.0, 0.70), 2: (0.36, 0.0, 0.40), 3: (0.28, 1.0, 0.0), 4: (0.80, 0.0, 0.5), 5: (0.80, 0.0, 0.4),
              7: (0.8, 0.0, 0.2), 8: (0.78, 0.0, 0.35)}


def mat_map(mat):
    out = np.zeros(mat.shape + (3,), np.float32)
    for k, (r, g, b) in MAT_PARAMS.items():
        sel = mat == k
        out[sel] = (r, g, b)
    return out


def grid_mesh(alpha, hlow, x0mm, y0mm, xf, yf, step=0.34, thick=THICK, edge_cols=None):
    """front displaced grid snapped to the alpha contour + flat felt back + rim.  Local frame: X right, Y up the card (0 at the
    feet), Z toward the viewer.  Returns dict(co, uv, quads, midx, vcol)."""
    H, W = alpha.shape
    Wmm, Hmm = W / PX, H / PX
    cov = cv2.GaussianBlur(alpha.astype(np.float32), (0, 0), 0.25 * PX)
    gy_, gx_ = np.gradient(cov)
    xs = np.arange(0.0, Wmm + 1e-6, step); ys = np.arange(0.0, Hmm + 1e-6, step)
    X, Y = np.meshgrid(xs, ys)
    ny, nx = X.shape
    cx_ = 0.5 * (xs[:-1] + xs[1:])[None, :]; cy_ = 0.5 * (ys[:-1] + ys[1:])[:, None]

    def samp(arr, x, y):
        x = np.asarray(x); y = np.asarray(y); shp = x.shape
        n = x.size; cols = 1024; rows = (n + cols - 1) // cols
        mx = np.zeros(rows * cols, np.float32); my = np.zeros(rows * cols, np.float32)
        mx[:n] = x.ravel() * PX - 0.5; my[:n] = y.ravel() * PX - 0.5
        o = cv2.remap(arr.astype(np.float32), mx.reshape(rows, cols), my.reshape(rows, cols), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return o.ravel()[:n].reshape(shp)
    covd = cv2.dilate((alpha > 0.5).astype(np.uint8), np.ones((int(0.5 * PX), int(0.5 * PX)), np.uint8))
    fm = samp(covd.astype(np.float32), np.broadcast_to(cx_, (ny - 1, nx - 1)), np.broadcast_to(cy_, (ny - 1, nx - 1))) > 0.5
    vid = np.arange(nx * ny).reshape(ny, nx)
    q = np.stack([vid[:-1, :-1], vid[:-1, 1:], vid[1:, 1:], vid[1:, :-1]], -1).reshape(-1, 4)[fm.reshape(-1)]
    e = np.sort(np.stack([q, np.roll(q, -1, 1)], -1).reshape(-1, 2), 1)
    ue, cnt = np.unique(e, axis=0, return_counts=True)
    bnd = np.zeros(nx * ny, bool); bnd[ue[cnt == 1].ravel()] = True
    xf_, yf_ = X.reshape(-1).copy(), Y.reshape(-1).copy()
    bx, by = xf_[bnd], yf_[bnd]
    for _ in range(8):
        c = samp(cov, bx, by) - 0.5
        gxx = samp(gx_, bx, by) * PX; gyy = samp(gy_, bx, by) * PX
        g2 = gxx ** 2 + gyy ** 2 + 1e-6
        bx = bx + np.clip(-c * gxx / g2, -0.3, 0.3); by = by + np.clip(-c * gyy / g2, -0.3, 0.3)
    xf_[bnd], yf_[bnd] = bx, by
    used = np.unique(q)
    remap = -np.ones(nx * ny, np.int64); remap[used] = np.arange(len(used))
    q = remap[q]
    px_, py_ = xf_[used], yf_[used]                              # image-frame mm inside the slip bbox (x right, y down)
    z = samp(hlow, px_, py_)
    nvf = len(used)
    # front verts
    co_f = np.stack([px_ + x0mm - xf, yf - (py_ + y0mm), z], 1)
    uv_f = np.stack([px_ / Wmm, 1.0 - py_ / Hmm], 1)
    # boundary loop edges (orientation from the quads)
    qe = np.stack([q, np.roll(q, -1, 1)], -1).reshape(-1, 2)
    key = np.sort(qe, 1)
    uk, inv, cn = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    inv = inv.ravel()
    bmask = cn[inv] == 1
    bedges = qe[bmask]
    bverts = np.unique(bedges)
    # back verts: copies of boundary verts only? full back surface is needed for the felt back -> duplicate all
    co_b = co_f.copy(); co_b[:, 2] = -thick
    quads_f = q
    quads_b = q[:, ::-1] + nvf
    rim = np.stack([bedges[:, 0], bedges[:, 1], bedges[:, 1] + nvf, bedges[:, 0] + nvf], 1)
    co = np.concatenate([co_f, co_b]).astype(np.float32)
    uv = np.concatenate([uv_f, uv_f]).astype(np.float32)
    quads = np.concatenate([quads_f, quads_b, rim]).astype(np.int32)
    midx = np.concatenate([np.zeros(len(quads_f)), np.ones(len(quads_b)), np.ones(len(rim))]).astype(np.int32)
    # felt colour: albedo sampled at the (inset) boundary, darkened
    vcol = np.full((len(co), 3), 0.06, np.float32)
    if edge_cols is not None:
        ex = np.clip((px_ * PX).astype(int), 0, W - 1); ey = np.clip((py_ * PX).astype(int), 0, H - 1)
        c = edge_cols[ey, ex]
        felt = np.array([0.30, 0.215, 0.12], np.float32)         # undyed wool felt backing
        vc = np.clip(c * 0.50 + felt * 0.50, 0, 1)
        vcol[:nvf] = vc; vcol[nvf:] = vc * 0.85
    return dict(co=co, uv=uv, quads=quads, midx=midx, vcol=vcol, n_front=nvf)


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]], np.float64)


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], np.float64)


def trans(x, y, z):
    M = np.eye(4); M[:3, 3] = (x, y, z); return M


def slip_matrix(xf, yf, tilt, yaw):
    """local card frame (X right, Y up the card, Z out of the card) -> world (Blender: X, -y, Z up): hinge at the feet."""
    return trans(xf, -yf, 0.05) @ rot_z(math.radians(yaw)) @ rot_x(math.radians(tilt))


def tube(path, radius, nside=6, taper=(1.0, 0.5)):
    """tube mesh along a 3D polyline: returns (verts, quads)."""
    P = np.asarray(path, np.float64)
    n = len(P)
    T = np.gradient(P, axis=0); T /= (np.linalg.norm(T, axis=1, keepdims=True) + 1e-9)
    ref = np.array([0, 0, 1.0])
    B = np.cross(T, ref); bad = np.linalg.norm(B, axis=1) < 1e-3
    B[bad] = np.cross(T[bad], np.array([1.0, 0, 0]))
    B /= np.linalg.norm(B, axis=1, keepdims=True)
    N = np.cross(B, T)
    ang = np.linspace(0, 2 * math.pi, nside, endpoint=False)
    rr = radius * np.interp(np.linspace(0, 1, n), [0, 1], taper)
    V = (P[:, None, :] + rr[:, None, None] * (np.cos(ang)[None, :, None] * N[:, None, :] + np.sin(ang)[None, :, None] * B[:, None, :]))
    V = V.reshape(-1, 3)
    idx = np.arange(n * nside).reshape(n, nside)
    quads = []
    for j in range(nside):
        j2 = (j + 1) % nside
        quads.append(np.stack([idx[:-1, j], idx[:-1, j2], idx[1:, j2], idx[1:, j]], 1))
    return V.astype(np.float32), np.concatenate(quads).astype(np.int32)


def curl_stub(p0, d0, length, turns, r0, lift, sag, rng, cloth=True, n=22):
    """a snapped thread end: leaves p0 along d0 (unit, world), then curls (growing helix) while sagging; cloth stubs never go
    under z = 0.3."""
    d0 = np.asarray(d0, np.float64); d0 /= np.linalg.norm(d0) + 1e-9
    ref = np.array([0, 0, 1.0]) if abs(d0[2]) < 0.9 else np.array([1.0, 0, 0])
    n1 = np.cross(d0, ref); n1 /= np.linalg.norm(n1)
    n2 = np.cross(d0, n1)
    ph = rng.uniform(0, 2 * math.pi)
    t = np.linspace(0, 1, n)
    R = r0 * np.sin(0.5 * math.pi * t) ** 1.2
    phi = 2 * math.pi * turns * t + ph
    P = p0[None] + d0[None] * (length * t)[:, None] \
        + R[:, None] * (np.cos(phi)[:, None] * n1[None] + np.sin(phi)[:, None] * n2[None]) - R[:, None] * (math.cos(ph) * n1 + math.sin(ph) * n2)[None]
    P[:, 2] += lift * np.sin(math.pi * t) - sag * t ** 2
    if cloth:
        P[:, 2] = np.maximum(P[:, 2], 0.3)
    return P


def make_tethers(ga, slip, M, rec_ends, img, rng, n_tethers=24, snapped_frac=0.86):
    """tethers for one slip.  rec_ends: (k, 2) strand-end positions (sheet mm) of the group.  img: dict(alb, alpha, origin_mm)."""
    xf, yf = slip['hinge_mm']
    band = rec_ends[(rec_ends[:, 1] > yf - 17.0) & (rec_ends[:, 1] < yf + 0.5)]
    if len(band) < 3:
        return [], []
    # spread: farthest-point sampling, random start
    order = [int(rng.integers(len(band)))]
    d = np.linalg.norm(band - band[order[0]], axis=1)
    while len(order) < min(n_tethers, len(band)):
        order.append(int(np.argmax(d)))
        d = np.minimum(d, np.linalg.norm(band - band[order[-1]], axis=1))
    verts, quads, cols = [], [], []
    ox, oy = img['origin_mm']
    for k, i in enumerate(order):
        hx, hy = band[i]
        Hw = np.array([hx, -hy, 0.0])
        Al = np.array([hx - xf, yf - hy, -0.5 * THICK, 1.0])
        Aw = (M @ Al)[:3]
        chord = np.linalg.norm(Aw - Hw)
        ix = int(np.clip((hx - ox) * PX, 0, img['alb'].shape[1] - 1)); iy = int(np.clip((hy - oy) * PX, 0, img['alb'].shape[0] - 1))
        r_ = int(2.0 * PX); ya, yb = max(iy - r_, 0), min(iy + r_ + 1, img['alb'].shape[0]); xa, xb = max(ix - r_, 0), min(ix + r_ + 1, img['alb'].shape[1])
        patch = img['alb'][ya:yb, xa:xb].reshape(-1, 3)
        lum = patch @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        good = patch[lum > 0.045]
        col = good[int(rng.integers(len(good)))] if len(good) else np.array([0.45, 0.36, 0.22], np.float32)
        col = np.clip(col * rng.uniform(0.9, 1.15), 0.02, 1)
        rad = rng.uniform(0.32, 0.44)
        hero = k < 3                                                    # three long, thick, clearly curling tethers per slip
        if hero:
            rad = rng.uniform(0.62, 0.82); col = np.clip(col * 1.12, 0, 1)
        paths = []
        if hero:
            dpull = (Hw - Aw); dpull[2] -= 0.55 * chord
            Ls = rng.uniform(0.8, 1.15) * max(chord, 8.0) + rng.uniform(5.0, 11.0)
            paths.append(curl_stub(Aw, dpull, Ls, rng.uniform(1.6, 2.5), rng.uniform(2.4, 3.8), 0.0, rng.uniform(1.0, 3.5), rng, cloth=False, n=40))
            dl = (Aw - Hw); dl[2] = 0.0
            if np.linalg.norm(dl) < 1e-3:
                dl = np.array([0, 1.0, 0])
            ang = rng.uniform(-1.2, 1.2); c_, s_ = math.cos(ang), math.sin(ang)
            dl = np.array([dl[0] * c_ - dl[1] * s_, dl[0] * s_ + dl[1] * c_, 0.0])
            Lc = rng.uniform(0.7, 1.1) * max(chord, 10.0) + rng.uniform(4.0, 9.0)
            paths.append(curl_stub(Hw + np.array([0, 0, 0.5]), dl, Lc, rng.uniform(1.8, 2.8), rng.uniform(2.5, 4.2), rng.uniform(0.6, 2.2), 0.0, rng, cloth=True, n=40))
        elif rng.random() < snapped_frac:
            # slip-side stub: hangs from the lower edge, curling at its tip
            dpull = (Hw - Aw); dpull[2] -= 0.4 * chord
            Ls = rng.uniform(0.28, 0.55) * max(chord, 5.0) + rng.uniform(0.5, 2.0)
            paths.append(curl_stub(Aw, dpull, Ls, rng.uniform(0.7, 1.4), rng.uniform(0.9, 1.9), 0.0, rng.uniform(0.5, 2.0), rng, cloth=False))
            # cloth-side stub: lies on the cloth around its needle hole, curling
            dl = (Aw - Hw); dl[2] = 0.0
            if np.linalg.norm(dl) < 1e-3:
                dl = np.array([0, 1.0, 0])
            ang = rng.uniform(-0.9, 0.9); c_, s_ = math.cos(ang), math.sin(ang)
            dl = np.array([dl[0] * c_ - dl[1] * s_, dl[0] * s_ + dl[1] * c_, 0.0])
            Lc = rng.uniform(0.25, 0.6) * max(chord, 6.0) + rng.uniform(1.0, 3.0)
            p0 = Hw + np.array([0, 0, 0.32])
            paths.append(curl_stub(p0, dl, Lc, rng.uniform(0.8, 1.8), rng.uniform(1.0, 2.4), rng.uniform(0.2, 1.4), 0.0, rng, cloth=True))
        else:
            # still in tension: thin taut thread with a small sag
            t = np.linspace(0, 1, 18)[:, None]
            P = Hw[None] * (1 - t) + Aw[None] * t
            P[:, 2] += 0.3 * (1 - t[:, 0]) - 0.6 * np.sin(math.pi * t[:, 0]) * 0.4
            paths.append(np.maximum(P, np.array([-1e9, -1e9, 0.3])))
        for P in paths:
            V, Q = tube(P, rad, 8 if rad > 0.7 else 6)
            Q = Q + sum(len(v) for v in verts)
            verts.append(V); quads.append(Q); cols.append(np.tile(col, (len(V), 1)))
    return verts, quads, cols


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'blend', 'slips_v2'))
    ap.add_argument('--maps', default=os.path.join(ROOT, 'maps_v2'))
    ap.add_argument('--age', type=float, default=0.28)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    meta = json.load(open(os.path.join(a.maps, 'war_slips.json')))
    G = MapSet(os.path.join(a.maps, 'war_ground'))
    out = dict(slips=[])
    t0 = time.time()
    all_v, all_q, all_c = [], [], []
    for k, sl in enumerate(meta['slips']):
        g = sl['group']
        ga, m, (bx0, by0) = slip_maps(G, g)
        d = finish_slip_maps(m, a.age)
        alpha = d['alpha']
        H, W = alpha.shape
        ys, xs = np.nonzero(alpha > 0.5)
        y_bot = (ys.max() + by0) / PX                                # sheet mm of the lowest slip pixel
        xc = sl['x_mm']
        hinge = (xc, y_bot - 0.25)
        # textures (PNG16 linear albedo with alpha; normal 8; mat 8)
        alb = d['alb'] * (0.60 + 0.40 * d['ao'][..., None])           # micro-visibility baked into the albedo
        rgba = np.dstack([np.clip(alb, 0, 1), (alpha > 0.5).astype(np.float32)])
        cv2.imwrite(os.path.join(a.out, f'{g}_alb.png'), cv2.cvtColor((rgba * 65535 + 0.5).astype(np.uint16), cv2.COLOR_RGBA2BGRA))
        Nm = d['N']
        nimg = np.stack([Nm[..., 0], -Nm[..., 1], Nm[..., 2]], -1) * 0.5 + 0.5
        cv2.imwrite(os.path.join(a.out, f'{g}_nrm.png'), cv2.cvtColor((np.clip(nimg, 0, 1) * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR))
        mm = mat_map(d['mat'])
        cv2.imwrite(os.path.join(a.out, f'{g}_mat.png'), cv2.cvtColor((np.clip(mm, 0, 1) * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR))
        np.savez_compressed(os.path.join(a.out, f'{g}_maps.npz'), alpha=alpha.astype(np.float16), h=d['h'].astype(np.float16), mat=d['mat'],
                            T=d['T'].astype(np.float16), cov=d['cov'].astype(np.float16), alb=d['alb'].astype(np.float16),
                            origin_mm=np.array([bx0 / PX, by0 / PX], np.float32))
        # mesh
        hlow = cv2.GaussianBlur(d['h'], (0, 0), 0.3 * PX)
        lum_ = (d['alb'] * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1)
        wfill = np.clip((lum_ - 0.045) / 0.10, 0, 1) * (alpha > 0.5)          # fill colour only (the dark stem outline is excluded)
        ecol = cv2.GaussianBlur(d['alb'] * wfill[..., None], (0, 0), 1.2 * PX) / (cv2.GaussianBlur(wfill, (0, 0), 1.2 * PX)[..., None] + 1e-3)
        mesh = grid_mesh(alpha, hlow, bx0 / PX, by0 / PX, hinge[0], hinge[1], edge_cols=ecol * 1.1)
        np.savez_compressed(os.path.join(a.out, f'{g}_mesh.npz'), **mesh)
        # pose and tethers
        pose = POSE[g]
        M = slip_matrix(hinge[0], hinge[1], pose['tilt'], pose['yaw'])
        R = ga.rec
        ends = []
        for e in ga.sel:
            if R['typ'][e] != 0 or R['kind'][e] not in (S.K_LAID, S.K_SPLIT, S.K_STEM):
                continue
            p = R['P'][R['off'][e]:R['off'][e + 1]]
            ends += [p[0], p[-1]]
        ends = np.array(ends, np.float32) / PX
        rng = np.random.default_rng(900 + k)
        slip_info = dict(group=g, unit=sl['unit'], realm=sl['realm'], hinge_mm=[float(hinge[0]), float(hinge[1])], tilt=pose['tilt'],
                         yaw=pose['yaw'], matrix=M.tolist(), size_mm=[W / PX, H / PX], origin_mm=[bx0 / PX, by0 / PX], n_verts=int(len(mesh['co'])))
        img = dict(alb=d['alb'], alpha=alpha, origin_mm=(bx0 / PX, by0 / PX))
        res = make_tethers(ga, dict(hinge_mm=hinge), M, ends, img, rng)
        if res and res[0]:
            V, Q, C = res
            nv0 = sum(len(v) for v in all_v)
            all_v += V; all_q += [q + nv0 for q in Q]; all_c += C
            slip_info['n_tether_paths'] = len(V)
        out['slips'].append(slip_info)
        print(f'[{g}] {sl["unit"]} {W/PX:.0f}x{H/PX:.0f} mm  verts {len(mesh["co"])}  tether paths {slip_info.get("n_tether_paths", 0)}  {time.time()-t0:.1f}s', flush=True)
    if all_v:
        V = np.concatenate(all_v); Q = np.concatenate(all_q); C = np.concatenate(all_c)
        np.savez_compressed(os.path.join(a.out, 'tethers.npz'), V=V, Q=Q, C=C.astype(np.float32))
        print('tethers', V.shape, Q.shape)
    json.dump(out, open(os.path.join(a.out, 'slips_export.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
