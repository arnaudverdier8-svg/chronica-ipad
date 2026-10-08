"""Game OBJ -> flat side-on elevation stills (material-ID + island-ID + depth), the source of the kit's stitched towns.

Orthographic projection (no perspective: Bayeux idiom), optional small tilt so roofs behind a wall peek over it.
Painter's algorithm over triangles (far -> near), rasterised with cv2.fillPoly at sub-pixel precision.
Islands = connected mesh pieces (shared vertex positions), so each house / tower / roof can take its own dye
(Bayeux alternation).  Deterministic; no Blender needed.

    E = elevation('settle_1', px_per_unit=500, tilt_deg=6)
    E['mat'] (HxW int, -1 = empty), E['island'], E['depth'], E['names'] (material names), E['normal_z'] ...
"""
import os, json, math
import numpy as np, cv2

AAA = "/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa"
MODELS = os.path.join(AAA, 'assets', 'models')


def load_obj(name):
    path = name if name.endswith('.obj') else os.path.join(MODELS, name + '.obj')
    V, F, M, names = [], [], [], []
    cur = -1
    with open(path) as fh:
        for ln in fh:
            if ln.startswith('v '):
                V.append([float(x) for x in ln.split()[1:4]])
            elif ln.startswith('usemtl'):
                nm = ln.split()[1]
                if nm not in names:
                    names.append(nm)
                cur = names.index(nm)
            elif ln.startswith('f '):
                idx = [int(t.split('/')[0]) - 1 for t in ln.split()[1:]]
                for k in range(1, len(idx) - 1):
                    F.append([idx[0], idx[k], idx[k + 1]]); M.append(cur)
    return np.array(V, np.float64), np.array(F, np.int64), np.array(M, np.int32), names


def islands(V, F, tol=1e-4):
    """connected components of faces sharing (rounded) vertex positions."""
    key = np.round(V / tol).astype(np.int64)
    _, vid = np.unique(key, axis=0, return_inverse=True)
    vid = vid.ravel()
    parent = np.arange(vid.max() + 1)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for f in F:
        a, b, c = vid[f]
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra; parent[find(rc)] = ra
    roots = np.array([find(vid[f[0]]) for f in F])
    _, isl = np.unique(roots, return_inverse=True)
    return isl.astype(np.int32)


def elevation(name, px_per_unit=500.0, tilt_deg=0.0, yaw_deg=0.0, front='+z', pad_px=6, min_area_px=0, vstretch=1.0):
    """orthographic elevation.  View from +z (front='+z') or -z looking at the model; y up; tilt rotates the model
    toward the viewer about x (positive = we see a bit of the tops)."""
    V, F, M, names = load_obj(name)
    isl = islands(V, F)
    P = V.copy()
    if front == '-z':
        P[:, 0] *= -1; P[:, 2] *= -1
    a = math.radians(yaw_deg)
    x, z = P[:, 0] * math.cos(a) + P[:, 2] * math.sin(a), -P[:, 0] * math.sin(a) + P[:, 2] * math.cos(a)
    P[:, 0], P[:, 2] = x, z
    t = math.radians(tilt_deg)
    y, z = P[:, 1] * math.cos(t) - P[:, 2] * math.sin(t), P[:, 1] * math.sin(t) + P[:, 2] * math.cos(t)
    P[:, 1], P[:, 2] = y, z
    # image coords: x right, y down
    xs, ys = P[:, 0] * px_per_unit, -P[:, 1] * px_per_unit * vstretch
    x0, y0 = xs.min() - pad_px, ys.min() - pad_px
    W, H = int(math.ceil(xs.max() - x0 + pad_px)), int(math.ceil(ys.max() - y0 + pad_px))
    X = np.stack([xs - x0, ys - y0], 1)
    # face normals (for shading / roof detection) in view space
    e1 = P[F[:, 1]] - P[F[:, 0]]; e2 = P[F[:, 2]] - P[F[:, 0]]
    n = np.cross(e1, e2); n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
    depth = P[F].mean(1)[:, 2]
    order = np.argsort(depth)             # far (small z) first
    mat = np.full((H, W), -1, np.int32); il = np.full((H, W), -1, np.int32); dep = np.full((H, W), -1e9, np.float32)
    nz = np.zeros((H, W), np.float32); ny = np.zeros((H, W), np.float32); fid = np.full((H, W), -1, np.int32)
    SH = 4
    for f in order:
        if abs(n[f, 2]) < 0.02 and True:
            pass
        tri = np.round(X[F[f]] * (1 << SH)).astype(np.int32)[None]
        m1 = np.zeros((H, W), np.uint8)
        cv2.fillPoly(m1, tri, 1, cv2.LINE_8, shift=SH)
        sel = m1 > 0
        if not sel.any():
            continue
        mat[sel] = M[f]; il[sel] = isl[f]; dep[sel] = depth[f]; nz[sel] = abs(n[f, 2]); ny[sel] = n[f, 1]; fid[sel] = f
    return dict(mat=mat, island=il, depth=dep, nz=nz, ny=ny, face=fid, names=names, px_per_unit=px_per_unit,
                origin_px=(float(-x0), float(-y0)), size=(W, H), name=os.path.basename(name).replace('.obj', ''),
                ground_y_px=float(-y0))


def mtl_colours(name):
    path = name if name.endswith('.mtl') else os.path.join(MODELS, name + '.mtl')
    out, cur = {}, None
    for ln in open(path):
        if ln.startswith('newmtl'):
            cur = ln.split()[1]
        elif ln.startswith('Kd') and cur:
            out[cur] = [float(v) for v in ln.split()[1:4]]
    return out


def preview(E, path):
    cols = mtl_colours(E['name'])
    H, W = E['mat'].shape
    img = np.full((H, W, 3), 0.85, np.float32)
    for i, nm in enumerate(E['names']):
        c = np.array(cols.get(nm, [0.5, 0.5, 0.5]), np.float32) ** (1 / 2.2)
        sel = E['mat'] == i
        img[sel] = c * (0.55 + 0.45 * E['nz'][sel])[:, None]
    # island edges
    il = E['island']
    ed = np.zeros((H, W), bool)
    ed[:, 1:] |= il[:, 1:] != il[:, :-1]; ed[1:, :] |= il[1:, :] != il[:-1, :]
    img[ed] *= 0.4
    cv2.imwrite(path, cv2.cvtColor((np.clip(img, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))


if __name__ == '__main__':
    import sys
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'elev')
    os.makedirs(out, exist_ok=True)
    for nm in (sys.argv[1:] or ['settle_0', 'settle_1', 'settle_2', 'capital', 'bridge']):
        for fr in ('+z', '-z'):
            for tilt in (0, 8):
                E = elevation(nm, 400, tilt_deg=tilt, front=fr)
                preview(E, os.path.join(out, f'{nm}_{"pz" if fr == "+z" else "nz"}_t{tilt}.png'))
                print(nm, fr, tilt, E['size'], E['names'], int(E['island'].max()) + 1)
