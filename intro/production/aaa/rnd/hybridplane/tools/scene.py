"""Approach C renderer: thread-level maps -> real displaced cloth meshes in Blender (bpy 5.2, EEVEE, EGL headless).

  bpy_env $BPY_PY scene.py SHOT [W H TAA FRAME_FROM FRAME_TO STEP]
SHOT: frontal | oblique | motion | rise | rise_oblique
World units: maps are in mm (x right, y down); Blender = metres, X = x/1000, Y = -y/1000, Z up (towards camera).
Meshes: low-pass height -> vertex Z (true silhouettes, real cast shadows); high-pass height -> tangent normal map.
"""
import sys, os, json, math, time
import numpy as np, cv2
import bpy
from mathutils import Vector, Matrix, Euler

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
MAPS = os.path.join(ROOT, os.environ.get('MAPSDIR', 'maps'))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
SHOT = argv[0] if argv else 'frontal'
RW = int(argv[1]) if len(argv) > 1 else 2560
RH = int(argv[2]) if len(argv) > 2 else 1440
TAA = int(argv[3]) if len(argv) > 3 else 16
F0 = int(argv[4]) if len(argv) > 4 else 0
F1 = int(argv[5]) if len(argv) > 5 else F0
FSTEP = int(argv[6]) if len(argv) > 6 else 1
OUTDIR = os.path.join(ROOT, 'renders', SHOT + os.environ.get('OUTTAG', '')); os.makedirs(OUTDIR, exist_ok=True)
cfg = json.load(open(os.path.join(ROOT, 'scene_layout.json')))
PX = cfg['px']; DV = cfg['mesh_dv_mm']; HP = cfg['mesh_hp_sigma_mm']
S = 0.001

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
try:
    bpy.context.preferences.system.anisotropic_filter = os.environ.get('ANISO', 'FILTER_4')
except Exception as e:
    print('aniso pref', e)

# ------------------------------------------------------------------ folds / drape (mm), shared by every cloth mesh
g = cfg['ground']
crease = np.load(os.path.join(MAPS, 'ground_crease.npy'))
def sample_grid(arr, x, y, x0, y0, ppmm):
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64); shp = x.shape
    n = x.size; cols = 2048; rows = (n + cols - 1) // cols
    mx = np.zeros(rows * cols, np.float32); my = np.zeros(rows * cols, np.float32)
    mx[:n] = ((x.ravel() - x0) * ppmm - 0.5); my[:n] = ((y.ravel() - y0) * ppmm - 0.5)
    out = cv2.remap(arr.astype(np.float32), mx.reshape(rows, cols), my.reshape(rows, cols), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return out.ravel()[:n].reshape(shp)
def folds(x, y, t=0.0, amp=1.0):
    z = 1.5 * np.sin(2 * math.pi * (x * 0.85 + y * 0.25) / 210 + 0.6 + 0.35 * math.sin(2 * math.pi * t / 5.0)) * (0.7 + 0.3 * np.cos(y / 90))
    z += 0.8 * np.sin(2 * math.pi * (-0.3 * x + y) / 140 + 1.7 + 0.25 * math.sin(2 * math.pi * t / 4.0 + 1))
    z += sample_grid(crease, x, y, g['x0'], g['y0'], 2.0)
    return z * amp

# ------------------------------------------------------------------ mesh helpers
def grid_mesh(name, xs, ys, zfun, uv_sets, face_mask=None, snap=None):
    """xs (nx,), ys (ny,) in mm. zfun(X,Y)->Z mm. uv_sets: {name: f(X,Y)->(u,v)}. face_mask (ny-1,nx-1) bool.
    snap(x, y, is_boundary) -> (x, y): move boundary vertices (e.g. onto an alpha contour) before Z/UV."""
    X, Y = np.meshgrid(xs, ys)
    ny, nx = X.shape
    vid = np.arange(nx * ny).reshape(ny, nx)
    q = np.stack([vid[:-1, :-1], vid[1:, :-1], vid[1:, 1:], vid[:-1, 1:]], -1).reshape(-1, 4)   # CCW seen from +Z (y flipped)
    if face_mask is not None:
        q = q[face_mask.reshape(-1)]
    if snap is not None:
        e = np.sort(np.stack([q, np.roll(q, -1, 1)], -1).reshape(-1, 2), 1)
        ue, cnt = np.unique(e, axis=0, return_counts=True)
        bnd = np.zeros(nx * ny, bool); bnd[ue[cnt == 1].ravel()] = True
        xf, yf = X.reshape(-1).copy(), Y.reshape(-1).copy()
        xf[bnd], yf[bnd] = snap(xf[bnd], yf[bnd])
        X, Y = xf.reshape(ny, nx), yf.reshape(ny, nx)
    Z = zfun(X, Y)
    used = np.unique(q)
    remap = -np.ones(nx * ny, np.int64); remap[used] = np.arange(len(used))
    q = remap[q]
    co = np.stack([X.reshape(-1)[used] * S, -Y.reshape(-1)[used] * S, Z.reshape(-1)[used] * S], -1).astype(np.float32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(co)); me.vertices.foreach_set('co', co.ravel())
    me.loops.add(q.size); me.loops.foreach_set('vertex_index', q.ravel().astype(np.int32))
    me.polygons.add(len(q)); me.polygons.foreach_set('loop_start', (np.arange(len(q)) * 4).astype(np.int32))
    me.update(calc_edges=True)
    lv = q.ravel()
    xv, yv = X.reshape(-1)[used][lv], Y.reshape(-1)[used][lv]
    for uvn, f in uv_sets.items():
        uvl = me.uv_layers.new(name=uvn)
        u, v = f(xv, yv)
        uvl.data.foreach_set('uv', np.stack([u, v], -1).astype(np.float32).ravel())
    me.polygons.foreach_set('use_smooth', np.ones(len(q), bool))
    me.update()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    return ob, dict(x=X.reshape(-1)[used], y=Y.reshape(-1)[used], z=Z.reshape(-1)[used])

def world_uv(x, y):
    return (x - g['x0']) / (g['x1'] - g['x0']), 1 - (y - g['y0']) / (g['y1'] - g['y0'])

# ------------------------------------------------------------------ materials
def img(path, noncolor=False):
    im = bpy.data.images.load(path)
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    return im
IM = {}
def get_img(n, nc=False):
    if n not in IM: IM[n] = img(os.path.join(MAPS, n), nc)
    return IM[n]

def cloth_material(name, alb, nrm, mat, uvname='uv', alpha=False, tile=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    b = N['Principled BSDF']
    uvn = N.new('ShaderNodeUVMap'); uvn.uv_map = uvname
    wuv = N.new('ShaderNodeUVMap'); wuv.uv_map = 'world'
    ta = N.new('ShaderNodeTexImage'); ta.image = get_img(alb); ta.interpolation = 'Linear'
    tn = N.new('ShaderNodeTexImage'); tn.image = get_img(nrm, True); tn.interpolation = 'Linear'
    tm = N.new('ShaderNodeTexImage'); tm.image = get_img(mat, True); tm.interpolation = 'Closest' if False else 'Linear'
    tv = N.new('ShaderNodeTexImage'); tv.image = get_img('ground_var8.png', True); tv.extension = 'EXTEND'
    for t in (ta, tn, tm):
        t.extension = 'REPEAT' if tile else 'EXTEND'
        Lk.new(uvn.outputs['UV'], t.inputs['Vector'])
    Lk.new(wuv.outputs['UV'], tv.inputs['Vector'])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    var2 = N.new('ShaderNodeVectorMath'); var2.operation = 'SCALE'; var2.inputs['Scale'].default_value = 2.0
    Lk.new(tv.outputs['Color'], var2.inputs[0])
    Lk.new(ta.outputs['Color'], mul.inputs[6]); Lk.new(var2.outputs['Vector'], mul.inputs[7])
    Lk.new(mul.outputs[2], b.inputs['Base Color'])
    nm = N.new('ShaderNodeNormalMap'); nm.uv_map = uvname; nm.inputs['Strength'].default_value = float(os.environ.get('NSTR', 1.5))
    Lk.new(tn.outputs['Color'], nm.inputs['Color']); Lk.new(nm.outputs['Normal'], b.inputs['Normal'])
    sep = N.new('ShaderNodeSeparateColor'); Lk.new(tm.outputs['Color'], sep.inputs['Color'])
    Lk.new(sep.outputs['Red'], b.inputs['Roughness']); Lk.new(sep.outputs['Green'], b.inputs['Metallic'])
    Lk.new(sep.outputs['Blue'], b.inputs['Sheen Weight']); Lk.new(tm.outputs['Alpha'], b.inputs['Specular IOR Level'])
    b.inputs['Sheen Roughness'].default_value = 0.42
    tint = N.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.inputs['Factor'].default_value = 0.55
    tint.inputs[6].default_value = (1, 1, 1, 1); Lk.new(mul.outputs[2], tint.inputs[7]); Lk.new(tint.outputs[2], b.inputs['Sheen Tint'])
    b.inputs['IOR'].default_value = 1.5
    if alpha:
        Lk.new(ta.outputs['Alpha'], b.inputs['Alpha'])
        m.surface_render_method = 'DITHERED'
    m['nm_node'] = nm.name
    return m

# ------------------------------------------------------------------ ground (coarse, holes under the patches)
st = g['step']
gx = np.arange(g['x0'], g['x1'] + 1e-6, st); gy = np.arange(g['y0'], g['y1'] + 1e-6, st)
cx_ = 0.5 * (gx[:-1] + gx[1:])[None, :]; cy_ = 0.5 * (gy[:-1] + gy[1:])[:, None]
holes = []
for key in ('king', 'knight'):
    r = cfg[key]['mesh']; holes.append(r)
fmask = np.ones((len(gy) - 1, len(gx) - 1), bool)
for (a, b_, c, d) in holes:
    fmask &= ~((cx_ > a) & (cx_ < c) & (cy_ > b_) & (cy_ < d))
T = cfg['linen_tile_mm']
ground, _ = grid_mesh('ground', gx, gy, lambda X, Y: folds(X, Y), {'uv': lambda x, y: (x / T, -y / T), 'world': world_uv}, fmask)
ground.data.materials.append(cloth_material('linen', 'linen_albedo.png', 'linen_normal8.png', 'linen_mat.png', tile=True))

# ------------------------------------------------------------------ king patch (dense, true displacement)
km = json.load(open(os.path.join(MAPS, 'king_meta.json')))
KX0, KY0 = cfg['king']['x0'], cfg['king']['y0']
hk = np.load(os.path.join(MAPS, 'king_height.npy'))
hk_low = cv2.GaussianBlur(hk, (0, 0), HP * PX)
a, b_, c, d = cfg['king']['mesh']
kxs = np.arange(a, c + 1e-6, DV); kys = np.arange(b_, d + 1e-6, DV)
kxs[-1] = c; kys[-1] = d
def king_z(X, Y):
    return folds(X, Y) + sample_grid(hk_low, X, Y, KX0, KY0, PX) * np.clip(1, 0, 1)
king, KB = grid_mesh('king', kxs, kys, king_z, {'uv': lambda x, y: ((x - KX0) / km['w_mm'], 1 - (y - KY0) / km['h_mm']), 'world': world_uv})
king.data.materials.append(cloth_material('king', 'king_albedo.png', 'king_normal8.png', 'king_mat.png'))
# boundary verts: force exact linen-plane height so the seam with the ground is closed
print('king verts', len(king.data.vertices), flush=True)

# ------------------------------------------------------------------ knight ghost (flat linen + underdrawing + holes)
nm_ = json.load(open(os.path.join(MAPS, 'knight_meta.json')))
NX0, NY0 = cfg['knight']['x0'], cfg['knight']['y0']
a, b_, c, d = cfg['knight']['mesh']
gxs = np.arange(a, c + 1e-6, 1.0); gys = np.arange(b_, d + 1e-6, 1.0)
ghost, _ = grid_mesh('ghost', gxs, gys, lambda X, Y: folds(X, Y), {'uv': lambda x, y: ((x - NX0) / nm_['w_mm'], 1 - (y - NY0) / nm_['h_mm']), 'world': world_uv})
ghost.data.materials.append(cloth_material('ghost', 'ghost_albedo.png', 'ghost_normal8.png', 'linen_mat.png'))

# ------------------------------------------------------------------ knight figure (separable patch)
hn = np.load(os.path.join(MAPS, 'knight_height.npy'))
cov = np.load(os.path.join(MAPS, 'knight_cov.npy'))
hn_low = cv2.GaussianBlur(hn, (0, 0), HP * PX)
nxs = np.arange(NX0 + 1, NX0 + nm_['w_mm'] - 1, DV); nys = np.arange(NY0 + 1, NY0 + nm_['h_mm'] - 1, DV)
covd = cv2.dilate(cov.astype(np.uint8), np.ones((int(0.45 * PX), int(0.45 * PX)), np.uint8))
Xc, Yc = np.meshgrid(0.5 * (nxs[:-1] + nxs[1:]), 0.5 * (nys[:-1] + nys[1:]))
fm = sample_grid(covd.astype(np.float32), Xc, Yc, NX0, NY0, PX) > 0.5
KN_H = None
def knight_h(X, Y):
    return sample_grid(hn_low, X, Y, NX0, NY0, PX)
covs = cv2.GaussianBlur(cov.astype(np.float32), (0, 0), 0.25 * PX)
gyc, gxc = np.gradient(covs)
def snap_contour(x, y):
    for _ in range(6):
        c = sample_grid(covs, x, y, NX0, NY0, PX) - 0.5
        gx_ = sample_grid(gxc, x, y, NX0, NY0, PX) * PX; gy_ = sample_grid(gyc, x, y, NX0, NY0, PX) * PX
        g2 = gx_ ** 2 + gy_ ** 2 + 1e-6
        stepx, stepy = np.clip(-c * gx_ / g2, -0.3, 0.3), np.clip(-c * gy_ / g2, -0.3, 0.3)
        x, y = x + stepx, y + stepy
    return x, y
knight, KNB = grid_mesh('knight', nxs, nys, lambda X, Y: folds(X, Y) + knight_h(X, Y) + 0.06,
                        {'uv': lambda x, y: ((x - NX0) / nm_['w_mm'], 1 - (y - NY0) / nm_['h_mm']), 'world': world_uv}, fm, snap=snap_contour)
kmat = cloth_material('knightfig', 'knight_albedo.png', 'knight_normal8.png', 'knight_mat.png', alpha=True)
knight.data.materials.append(kmat)
# backing: the figure has a body (felted wool + linen backing) visible only once it lifts off
bmat = bpy.data.materials.new('backing'); bmat.use_nodes = True
bb_ = bmat.node_tree.nodes['Principled BSDF']; bb_.inputs['Base Color'].default_value = (0.09, 0.05, 0.03, 1)
bb_.inputs['Roughness'].default_value = 0.9; bb_.inputs['Sheen Weight'].default_value = 0.9; bb_.inputs['Sheen Roughness'].default_value = 0.3
knight.data.materials.append(bmat)
sol = knight.modifiers.new('body', 'SOLIDIFY'); sol.thickness = 0.0008; sol.offset = -1.0; sol.use_rim = True
sol.material_offset = 1; sol.material_offset_rim = 1; sol.use_even_offset = False
KNB['h'] = knight_h(KNB['x'], KNB['y']); KNB['f'] = folds(KNB['x'], KNB['y'])
CEN = np.array([NX0 + nm_['centroid_mm'][0], NY0 + nm_['centroid_mm'][1]])
print('knight verts', len(knight.data.vertices), flush=True)

# tethers: wool threads from the lifted figure's outline back down through their needle holes
tmat = bpy.data.materials.new('tether'); tmat.use_nodes = True
tb = tmat.node_tree.nodes['Principled BSDF']; tb.inputs['Base Color'].default_value = (0.075, 0.035, 0.018, 1)
tb.inputs['Roughness'].default_value = 0.85; tb.inputs['Sheen Weight'].default_value = 0.8; tb.inputs['Sheen Roughness'].default_value = 0.35
cu = bpy.data.curves.new('tethers', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.00016; cu.bevel_resolution = 2
ANC = np.array(nm_['anchors_mm']) + np.array([NX0, NY0])
NSEG = 10
for _ in ANC:
    sp = cu.splines.new('POLY'); sp.points.add(NSEG)
tobj = bpy.data.objects.new('tethers', cu); tobj.data.materials.append(tmat); sc.collection.objects.link(tobj)

def knight_pose(lift, hscale, rx=0.0, ry=0.0, bend=0.0, t=0.0, rigid=0.0):
    """lift mm, hscale relief multiplier, rx/ry tilt deg about the centroid, bend mm (centre up), rigid 0..1 (fold-follow -> flat)."""
    x, y = KNB['x'], KNB['y']
    f = KNB['f'] * (1 - rigid) + folds(np.array([CEN[0]]), np.array([CEN[1]]))[0] * rigid
    r2 = ((x - CEN[0]) / 80) ** 2 + ((y - CEN[1]) / 90) ** 2
    z = f + KNB['h'] * hscale + 0.06 + lift + bend * (1 - np.clip(r2, 0, 1.5))
    # rotate about the centroid (tilt), in mm
    P = np.stack([x - CEN[0], y - CEN[1], z - lift], -1)
    R = (Matrix.Rotation(math.radians(rx), 3, 'X') @ Matrix.Rotation(math.radians(ry), 3, 'Y'))
    Rn = np.array(R, np.float32)
    P = P @ Rn.T
    co = np.stack([(P[:, 0] + CEN[0]) * S, -(P[:, 1] + CEN[1]) * S, (P[:, 2] + lift) * S], -1).astype(np.float32)
    knight.data.vertices.foreach_set('co', co.ravel()); knight.data.update()
    kmat.node_tree.nodes[kmat['nm_node']].inputs['Strength'].default_value = float(os.environ.get('NSTR', 1.5)) * float(np.clip(0.6 + 0.4 * hscale, 0.6, 1.4))
    # the grazing rim's long shadow from a lifted figure reads as a stray blob: rim keeps lighting, stops shadowing
    rim_d.use_shadow = (lift < 0.1) and os.environ.get('RIMSH', '1') == '1'
    # tethers
    show = lift > 0.15
    tobj.hide_render = not show
    if show:
        ax, ay = ANC[:, 0], ANC[:, 1]
        hz = knight_h(ax, ay) * hscale
        Pz = np.stack([ax - CEN[0], ay - CEN[1], folds(ax, ay) * (1 - rigid) + rigid * folds(np.array([CEN[0]]), np.array([CEN[1]]))[0] + hz * 0.3], -1) @ Rn.T
        top = np.stack([Pz[:, 0] + CEN[0], Pz[:, 1] + CEN[1], Pz[:, 2] + lift], -1)
        bot = np.stack([ax, ay, folds(ax, ay) - 0.1], -1)
        for i, sp in enumerate(cu.splines):
            pts = []
            for k in range(NSEG + 1):
                s = k / NSEG
                p = bot[i] * (1 - s) + top[i] * s
                # slight sag/outward bow (threads are not rods)
                p = p + np.array([0, 0, -0.35 * math.sin(math.pi * s) * min(1, lift / 6)])
                pts += [p[0] * S, -p[1] * S, p[2] * S, 1.0]
            sp.points.foreach_set('co', pts)

# ------------------------------------------------------------------ lights
def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
TGT = Vector((0, 0, 0))
key_d = bpy.data.lights.new('key', 'SPOT'); key_d.energy = float(os.environ.get('KEY', 105)); key_d.shadow_soft_size = float(os.environ.get('KEYR', 0.045))
key_d.spot_size = math.radians(float(os.environ.get('SPOT', 62))); key_d.spot_blend = 1.0; key_d.color = (1.0, 0.88, 0.74)
key = bpy.data.objects.new('key', key_d); sc.collection.objects.link(key)
rim_d = bpy.data.lights.new('rim', 'SPOT'); rim_d.energy = 70; rim_d.shadow_soft_size = 0.03
rim_d.spot_size = math.radians(70); rim_d.spot_blend = 0.9; rim_d.color = (0.86, 0.9, 1.0)
rim = bpy.data.objects.new('rim', rim_d); sc.collection.objects.link(rim)
fill_d = bpy.data.lights.new('fill', 'AREA'); fill_d.energy = float(os.environ.get('FILL', 2.4)); fill_d.size = 0.8; fill_d.color = (0.78, 0.85, 1.0)
fill = bpy.data.objects.new('fill', fill_d); sc.collection.objects.link(fill)
fill_d.use_shadow = os.environ.get('FILLSH', '0') == '1'
rim_d.use_shadow = os.environ.get('RIMSH', '1') == '1'
for L_ in (key_d, rim_d, fill_d):
    for k_, v_ in (('shadow_maximum_resolution', float(os.environ.get('SHRES', 0.0002))), ('use_shadow_jitter', False), ('shadow_filter_radius', 1.0)):
        if hasattr(L_, k_): setattr(L_, k_, v_)
def set_key(az, el, dist=float(os.environ.get('KEYD', 1.1)), target=(0, 0, 0), energy=None):
    a, e = math.radians(az), math.radians(el)
    # az measured in screen space: 0 = right (+X), 90 = up (+Y)
    key.location = Vector(target) + Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))) * dist
    look_at(key, target)
    if energy: key_d.energy = energy
def set_rim(az=35, el=8, dist=1.4, target=(0, 0, 0)):
    a, e = math.radians(az), math.radians(el)
    rim.location = Vector(target) + Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))) * dist
    look_at(rim, target)
fill.location = (0.35, -0.6, 1.1); look_at(fill, (0, 0, 0))
w = bpy.data.worlds.new('w'); w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.005, 0.0055, 0.0075, 1); sc.world = w

# ------------------------------------------------------------------ camera
cd = bpy.data.cameras.new('cam'); cd.lens = 85; cd.sensor_width = 36; cd.clip_start = 0.01; cd.clip_end = 10
cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
def set_cam(pos_mm, tgt_mm, lens=85, fstop=None, focus_mm=None):
    cam.location = Vector((pos_mm[0] * S, -pos_mm[1] * S, pos_mm[2] * S))
    look_at(cam, Vector((tgt_mm[0] * S, -tgt_mm[1] * S, tgt_mm[2] * S)))
    cd.lens = lens
    if fstop:
        cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
        fm_ = focus_mm if focus_mm is not None else tgt_mm
        cd.dof.focus_distance = (Vector(fm_) - Vector(pos_mm)).length * S
    else:
        cd.dof.use_dof = False

# ------------------------------------------------------------------ render settings
sc.render.engine = 'BLENDER_EEVEE'
e = sc.eevee
e.taa_render_samples = TAA
for k_, v_ in (('use_shadows', True), ('shadow_ray_count', int(os.environ.get('SHRAYS', 1))), ('shadow_step_count', 6), ('use_fast_gi', os.environ.get('FASTGI', '1') == '1'),
               ('fast_gi_distance', 0.004), ('use_raytracing', False), ('shadow_resolution_scale', 1.0)):
    try: setattr(e, k_, v_)
    except Exception as ex: print('eevee', k_, ex)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = RW, RH, 100
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'; sc.render.image_settings.color_depth = '16'
sc.view_settings.view_transform = 'AgX'
try: sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
sc.view_settings.exposure = 0.0
sc.render.fps = 30
if os.environ.get('BORDER'):
    bx0, by0, bx1, by1 = map(float, os.environ['BORDER'].split(','))
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_min_y, sc.render.border_max_x, sc.render.border_max_y = bx0, by0, bx1, by1
print('setup done', round(time.time() - T0, 1), 's', flush=True)

# ------------------------------------------------------------------ shots
def ease(t): t = min(max(t, 0.0), 1.0); return t * t * (3 - 2 * t)
def ease3(t): t = min(max(t, 0.0), 1.0); return t * t * t * (t * (6 * t - 15) + 10)
FR = {'frontal': (0, 0), 'oblique': (0, 0)}
def shot_state(fr):
    t = fr / 30.0
    st = dict(cam=None, key=(135, float(os.environ.get('KEYEL', 21))), rim=(35, 8), knight=dict(lift=0, hscale=1.0), fold_t=0.0)
    if SHOT == 'frontal':
        st['cam'] = dict(pos=(0, 0, 944), tgt=(0, 0, 0), lens=85)
    elif SHOT == 'oblique':
        # 45 deg off the cloth normal, looking up the cloth from below; real DOF
        tgt = (10, 5, 0); dist = 640; tilt = math.radians(45); yaw = math.radians(-12)
        pos = (tgt[0] + dist * math.sin(tilt) * math.sin(yaw), tgt[1] + dist * math.sin(tilt) * math.cos(yaw), dist * math.cos(tilt))
        st['cam'] = dict(pos=pos, tgt=tgt, lens=58, fstop=4.0, focus=(10, 5, 0))
        st['key'] = (140, 20)
    elif SHOT == 'motion':
        # 2.5 s: key sweeps left->right across the top (az 165 -> 55), slow push-in + truck right
        u = ease(t / 2.5)
        st['key'] = (165 - 110 * u, 17 + 9 * math.sin(math.pi * u))
        st['cam'] = dict(pos=(-30 + 60 * u, 8, 760 - 120 * u), tgt=(-30 + 60 * u, 0, 0), lens=85)
        st['fold_t'] = t
    elif SHOT in ('rise', 'rise_oblique'):
        # 4 s: (0-0.8) cloth quiet, light starts to move; (0.8-1.8) relief swells; (1.6-3.4) lift-off, tethers draw tight; hold
        rs = ease3((t - 0.6) / 1.2)
        lf = ease3((t - 1.5) / 1.9)
        st['knight'] = dict(lift=11.0 * lf, hscale=0.55 + 0.75 * rs, rx=-4.0 * lf, ry=2.5 * lf, bend=1.6 * lf, rigid=lf)
        st['key'] = (150 - 25 * ease(t / 4.0), 21)
        if SHOT == 'rise':
            st['cam'] = dict(pos=(100, 120 + 15 * ease(t / 4), 560), tgt=(100, 4, 0), lens=70, fstop=5.6, focus=(100, 0, 6))
        else:
            tgt = (100, 0, 0); dist = 470; tilt = math.radians(42); yaw = math.radians(-18)
            pos = (tgt[0] + dist * math.sin(tilt) * math.sin(yaw), tgt[1] + dist * math.sin(tilt) * math.cos(yaw), dist * math.cos(tilt))
            st['cam'] = dict(pos=pos, tgt=tgt, lens=60, fstop=4.0, focus=(100, 0, 6))
        st['fold_t'] = t
    return st

rise_param = os.environ.get('KNIGHT_LIFT')
log = []
for fr in range(F0, F1 + 1, FSTEP):
    t1 = time.time()
    s_ = shot_state(fr)
    c_ = s_['cam']; set_cam(c_['pos'], c_['tgt'], c_['lens'], c_.get('fstop'), c_.get('focus'))
    tgt_m = (c_['tgt'][0] * S, -c_['tgt'][1] * S, 0)
    set_key(*s_['key'], target=tgt_m); set_rim(*s_['rim'], target=tgt_m)
    kp = dict(s_['knight'])
    if rise_param: kp.update(json.loads(rise_param))
    knight_pose(t=s_['fold_t'], **kp)
    sc.render.filepath = os.path.join(OUTDIR, f'{SHOT}_{fr:04d}.png')
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t1; log.append(dt)
    print(f'FRAME {fr} {dt:.1f}s', flush=True)
json.dump(dict(shot=SHOT, res=[RW, RH], taa=TAA, frames=[F0, F1, FSTEP], sec_per_frame=log, total=time.time() - T0),
          open(os.path.join(OUTDIR, f'timing_{F0}_{F1}.json'), 'w'), indent=1)
print('ALL DONE', round(time.time() - T0, 1), flush=True)
