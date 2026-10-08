# scene.py - Blender 4.0.2 (Eevee legacy) scene for true-thread embroidery.
# run: PYTHONPATH=<py312> xvfb-run -a -s "-screen 0 1920x1080x24" blender -b --factory-startup -P scene.py -- cfg.json
# 1 BU = 1 mm (scene unit scale 0.001 so camera DOF is physical). Cloth in XY plane, z out of cloth.
import bpy, sys, os, json, math, time
import numpy as np
from mathutils import Vector, Euler, Matrix

T0 = time.time()
argv = sys.argv[sys.argv.index('--') + 1:]
CFG = json.load(open(argv[0]))
HERE = os.path.dirname(os.path.abspath(__file__))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 0.001

def srgb2lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

# ------------------------------------------------------------------------------------------- materials
def _n(nt, t, loc=(0, 0), **kw):
    n = nt.nodes.new(t); n.location = loc
    for k, v in kw.items():
        if k in n.inputs: n.inputs[k].default_value = v
        else: setattr(n, k, v)
    return n

def mat_thread(name, kind):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; L = nt.links
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = _n(nt, 'ShaderNodeOutputMaterial', (900, 0))
    bs = _n(nt, 'ShaderNodeBsdfPrincipled', (600, 0))
    L.new(bs.outputs[0], out.inputs[0])
    at = _n(nt, 'ShaderNodeAttribute', (-900, 200)); at.attribute_name = 'col'
    uv = _n(nt, 'ShaderNodeUVMap', (-900, -100))
    sp = _n(nt, 'ShaderNodeSeparateXYZ', (-700, -100)); L.new(uv.outputs[0], sp.inputs[0])
    def math_(op, a, b, loc):
        n = _n(nt, 'ShaderNodeMath', loc); n.operation = op
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: L.new(v, n.inputs[i])
        return n.outputs[0]
    u = sp.outputs[0]; v = sp.outputs[1]; rnd = at.outputs['Alpha']
    nply = {'wool': 2.0, 'gold': 1.0, 'tie': 2.0, 'fibre': 0.0, 'cord': 2.0}[kind]
    # twisted ply ridges: phase = u + nply*v + 7*rnd  -> |sin(pi*phase)|
    ph = math_('ADD', math_('ADD', u, math_('MULTIPLY', v, nply, (-500, -150)), (-350, -100)), math_('MULTIPLY', rnd, 7.0, (-500, 50)), (-200, -50))
    s = math_('SINE', math_('MULTIPLY', ph, math.pi, (-50, -50)), 0, (100, -50))
    ridge = math_('POWER', math_('ABSOLUTE', s, 0, (250, -50)), 0.55, (400, -50))
    # fibre streaks: noise stretched along the twisted ply
    cmb = _n(nt, 'ShaderNodeCombineXYZ', (-200, -350))
    L.new(math_('MULTIPLY', ph, 2.0, (-350, -300)), cmb.inputs[0]); L.new(math_('MULTIPLY', v, 9.0, (-350, -420)), cmb.inputs[1])
    L.new(rnd, cmb.inputs[2])
    nz = _n(nt, 'ShaderNodeTexNoise', (0, -350)); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 3.0
    L.new(cmb.outputs[0], nz.inputs['Vector'])
    if kind == 'fibre':
        hgt = nz.outputs['Fac']
    else:
        hgt = math_('ADD', math_('MULTIPLY', ridge, 0.75, (550, -100)), math_('MULTIPLY', nz.outputs['Fac'], 0.35, (200, -300)), (700, -200))
    bump = _n(nt, 'ShaderNodeBump', (350, -350))
    bump.inputs['Strength'].default_value = {'wool': 0.85, 'gold': 0.9, 'tie': 0.6, 'fibre': 0.2, 'cord': 0.9}[kind]
    bump.inputs['Distance'].default_value = {'wool': 0.06, 'gold': 0.05, 'tie': 0.03, 'fibre': 0.01, 'cord': 0.08}[kind]
    L.new(hgt, bump.inputs['Height']); L.new(bump.outputs[0], bs.inputs['Normal'])
    # albedo: cavity between plies darker, slight fibre streak variation
    shade = math_('ADD', math_('MULTIPLY', ridge, 0.30, (300, 150)), 0.70, (450, 150))
    shade2 = math_('ADD', math_('MULTIPLY', nz.outputs['Fac'], 0.16, (300, 300)), 0.92, (450, 300))
    mc = _n(nt, 'ShaderNodeMix', (500, 250)); mc.data_type = 'RGBA'; mc.blend_type = 'MULTIPLY'
    mc.inputs['Factor'].default_value = 1.0
    L.new(at.outputs['Color'], mc.inputs[6]);
    shv = math_('MULTIPLY', shade, shade2, (480, 420))
    cc = _n(nt, 'ShaderNodeCombineColor', (350, 450)); L.new(shv, cc.inputs[0]); L.new(shv, cc.inputs[1]); L.new(shv, cc.inputs[2])
    L.new(cc.outputs[0], mc.inputs[7])
    L.new(mc.outputs[2], bs.inputs['Base Color'])
    if kind in ('wool', 'tie', 'cord', 'fibre'):
        bs.inputs['Roughness'].default_value = {'wool': 0.93, 'tie': 0.6, 'cord': 0.8, 'fibre': 0.95}[kind]
        bs.inputs['Specular IOR Level'].default_value = 0.18
        bs.inputs['Sheen Weight'].default_value = {'wool': 0.55, 'tie': 0.4, 'cord': 0.6, 'fibre': 1.0}[kind]
        bs.inputs['Sheen Roughness'].default_value = 0.4
        mt = _n(nt, 'ShaderNodeMix', (450, -500)); mt.data_type = 'RGBA'; mt.inputs['Factor'].default_value = 0.5
        L.new(at.outputs['Color'], mt.inputs[6]); mt.inputs[7].default_value = (1, 1, 1, 1)
        L.new(mt.outputs[2], bs.inputs['Sheen Tint'])
    if kind == 'gold':
        bs.inputs['Metallic'].default_value = 1.0
        bs.inputs['Roughness'].default_value = 0.3
    if CFG.get('stitch_on'):
        ab = _n(nt, 'ShaderNodeAttribute', (-900, 600)); ab.attribute_name = 'birth'; ab.attribute_type = 'GEOMETRY'
        rv = _n(nt, 'ShaderNodeValue', (-900, 750)); rv.name = 'REVEAL'; rv.outputs[0].default_value = 2.0
        lt = _n(nt, 'ShaderNodeMath', (-600, 650)); lt.operation = 'LESS_THAN'
        L.new(ab.outputs['Fac'], lt.inputs[0]); L.new(rv.outputs[0], lt.inputs[1]); L.new(lt.outputs[0], bs.inputs['Alpha'])
        m.blend_method = 'CLIP'; m.shadow_method = 'CLIP'; m.alpha_threshold = 0.5
    return m

def mat_linen(cfg):
    m = bpy.data.materials.new('linen'); m.use_nodes = True
    nt = m.node_tree; L = nt.links
    bs = nt.nodes['Principled BSDF']
    ta = nt.nodes.new('ShaderNodeTexImage'); ta.image = bpy.data.images.load(cfg['albedo']); ta.location = (-600, 200)
    ta.interpolation = 'Cubic'
    th = nt.nodes.new('ShaderNodeTexImage'); th.image = bpy.data.images.load(cfg['height']); th.location = (-600, -200)
    th.image.colorspace_settings.name = 'Non-Color'; th.interpolation = 'Cubic'
    bump = nt.nodes.new('ShaderNodeBump'); bump.location = (-250, -200)
    bump.inputs['Strength'].default_value = 1.0; bump.inputs['Distance'].default_value = 0.4 * cfg.get('bump_scale', 0.6)
    L.new(th.outputs['Color'], bump.inputs['Height']); L.new(bump.outputs[0], bs.inputs['Normal'])
    col = ta.outputs['Color']
    if cfg.get('imprint'):
        ti = nt.nodes.new('ShaderNodeTexImage'); ti.image = bpy.data.images.load(cfg['imprint']); ti.location = (-600, 500)
        ti.image.colorspace_settings.name = 'Non-Color'
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.location = (-250, 300)
        L.new(ti.outputs['Color'], mx.inputs['Factor']); L.new(col, mx.inputs[6]); mx.inputs[7].default_value = (0.55, 0.47, 0.38, 1)
        col = mx.outputs[2]
    L.new(col, bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.82; bs.inputs['Specular IOR Level'].default_value = 0.3
    bs.inputs['Sheen Weight'].default_value = 0.3; bs.inputs['Sheen Roughness'].default_value = 0.5
    return m

MATS = {}
def get_mat(mid):
    kind = {0: 'wool', 1: 'gold', 2: 'wool', 3: 'cord', 4: 'fibre', 5: 'tie'}[int(mid)]
    if kind not in MATS: MATS[kind] = mat_thread('thr_' + kind, kind)
    return MATS[kind]

# ------------------------------------------------------------------------------------------- tube mesh
def build_tubes(name, D, idx, offset=(0, 0, 0), zscale=1.0):
    P, RW, RH, C, off, meta = D['P'], D['RW'], D['RH'], D['C'], D['off'], D['meta']
    Vs, Fs, UVs, Cs, Bs = [], [], [], [], []
    vb = 0
    for S in sorted(set(int(meta[i, 3]) for i in idx)):
        sel = np.array([i for i in idx if int(meta[i, 3]) == S])
        lens = off[sel + 1] - off[sel]
        pidx = np.concatenate([np.arange(off[i], off[i + 1]) for i in sel])
        p = P[pidx].astype(np.float64); n = len(p)
        rw = RW[pidx].astype(np.float64); rh = RH[pidx].astype(np.float64)
        tid = np.repeat(np.arange(len(sel)), lens)
        starts = np.r_[0, np.cumsum(lens)[:-1]]; ends = np.cumsum(lens) - 1
        is_s = np.zeros(n, bool); is_s[starts] = True; is_e = np.zeros(n, bool); is_e[ends] = True
        prv = np.arange(n) - 1; prv[is_s] = np.where(is_s)[0]
        nxt = np.arange(n) + 1; nxt[is_e] = np.where(is_e)[0]
        Tg = p[nxt] - p[prv]; Tg /= (np.linalg.norm(Tg, axis=1, keepdims=True) + 1e-12)
        B = np.cross(np.array([0, 0, 1.0]), Tg); bl = np.linalg.norm(B, axis=1)
        bad = bl < 1e-3
        if bad.any(): B[bad] = np.cross(np.array([1.0, 0, 0]), Tg[bad])
        B /= (np.linalg.norm(B, axis=1, keepdims=True) + 1e-12)
        U = np.cross(Tg, B)
        th = 2 * np.pi * np.arange(S) / S + (np.pi / S if S % 2 == 0 else np.pi / 2)
        V = p[:, None, :] + B[:, None, :] * (np.cos(th)[None, :, None] * rw[:, None, None]) + U[:, None, :] * (np.sin(th)[None, :, None] * rh[:, None, None])
        V = V.reshape(-1, 3)
        V[:, 2] *= zscale
        ii = np.where(~is_e)[0]
        j = np.arange(S); j1 = (j + 1) % S
        a = ii[:, None] * S + j[None]; b = ii[:, None] * S + j1[None]
        c = (ii[:, None] + 1) * S + j1[None]; d = (ii[:, None] + 1) * S + j[None]
        F = np.stack([a, b, c, d], -1).reshape(-1, 4) + vb
        # arclength per tube -> u
        dl = np.linalg.norm(p - p[prv], axis=1); dl[is_s] = 0
        cs = np.cumsum(dl); s = cs - cs[starts][tid]
        twist = meta[sel, 2][tid]; rnd = np.random.default_rng(len(sel) + S).random(len(sel))[tid]
        uu = s / np.maximum(twist, 1e-3) + rnd * 5.0
        ua = np.repeat(uu[ii], S); ub = np.repeat(uu[ii + 1], S)
        va = np.tile(j / S, len(ii)); vb_ = np.tile((j + 1) / S, len(ii))
        UV = np.stack([np.stack([ua, va], -1), np.stack([ua, vb_], -1), np.stack([ub, vb_], -1), np.stack([ub, va], -1)], 1).reshape(-1, 2)
        col = srgb2lin(C[pidx].astype(np.float32))
        Cv = np.repeat(np.c_[col, rnd.astype(np.float32)], S, axis=0)
        if 'birth' in D:
            Lt = np.maximum(s[ends][tid], 1e-6)
            bt = D['birth'][sel][tid] + (s / Lt) * D.get('birth_dur', 0.05)
            Bs.append(np.repeat(bt.astype(np.float32), S))
        Vs.append(V); Fs.append(F); UVs.append(UV); Cs.append(Cv); vb += len(V)
    V = np.concatenate(Vs) + np.array(offset); F = np.concatenate(Fs); UV = np.concatenate(UVs); Cv = np.concatenate(Cs)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V)); me.vertices.foreach_set('co', V.astype(np.float32).ravel())
    me.loops.add(F.size); me.loops.foreach_set('vertex_index', F.astype(np.int32).ravel())
    me.polygons.add(len(F)); me.polygons.foreach_set('loop_start', (np.arange(len(F)) * 4).astype(np.int32))
    try: me.polygons.foreach_set('loop_total', np.full(len(F), 4, np.int32))
    except Exception: pass
    me.update(calc_edges=True)
    me.polygons.foreach_set('use_smooth', np.ones(len(F), bool))
    uvl = me.uv_layers.new(name='UVMap'); uvl.data.foreach_set('uv', UV.astype(np.float32).ravel())
    ca = me.color_attributes.new('col', 'FLOAT_COLOR', 'POINT'); ca.data.foreach_set('color', Cv.astype(np.float32).ravel())
    if Bs:
        ba = me.attributes.new('birth', 'FLOAT', 'POINT'); ba.data.foreach_set('value', np.concatenate(Bs).astype(np.float32))
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    return ob, len(V)

def load_motif(mcfg):
    D = dict(np.load(mcfg['npz']))
    D['C'] = D['C'].astype(np.float32)
    meta = D['meta']
    if CFG.get('stitch_on'):
        off = D['off']; P = D['P']
        cy = np.add.reduceat(P[:, 1], off[:-1]) / np.diff(off); cx = np.add.reduceat(P[:, 0], off[:-1]) / np.diff(off)
        w = (cy - cy.min()) / (np.ptp(cy) + 1e-6)
        w = np.clip(w + 0.06 * np.sin(cx * 0.15) + np.random.default_rng(3).normal(0, 0.03, len(w)), 0, 1)
        grp = meta[:, 1].astype(int); mat = meta[:, 0].astype(int)
        b = 0.02 + 0.62 * w
        b = np.where(grp == 3, 0.10 + 0.62 * w, b)            # gold slightly after the fills around it
        b = np.where(grp == 4, 0.70 + 0.24 * w, b)            # outline cord last, sweeping upward
        b = np.where(mat == 4, 0.97, b)                       # fuzz settles at the end
        D['birth'] = b.astype(np.float32); D['birth_dur'] = 0.05
    objs = []; nv = 0
    for mid in sorted(set(meta[:, 0].astype(int))):
        if mid == 4 and not CFG.get('fibres', True): continue
        idx = np.where(meta[:, 0].astype(int) == mid)[0]
        ob, n = build_tubes(mcfg['name'] + '_m%d' % mid, D, idx, mcfg.get('offset', (0, 0, 0)), mcfg.get('zscale', 1.0))
        ob.data.materials.append(get_mat(mid)); objs.append(ob); nv += n
    print('motif', mcfg['name'], 'verts', nv, 'objs', len(objs), 't', round(time.time() - T0, 1), flush=True)
    return objs, nv

# ------------------------------------------------------------------------------------------- build scene
NV = 0
MOTIF_OBJS = {}
for mc in CFG['motifs']:
    objs, n = load_motif(mc); NV += n; MOTIF_OBJS[mc['name']] = objs
    if mc.get('parent'):
        par = bpy.data.objects.get(mc['parent'])
        if par is None:
            par = bpy.data.objects.new(mc['parent'], None); sc.collection.objects.link(par)
            par.location = mc.get('pivot', (0, 0, 0))
            bpy.context.view_layer.update()
        for o in objs:
            o.parent = par; o.matrix_parent_inverse = par.matrix_world.inverted()
lc = CFG['linen']
bpy.ops.mesh.primitive_plane_add(size=1)
linen = bpy.context.active_object; linen.name = 'linen'
linen.scale = (lc['w_mm'], lc['h_mm'], 1); linen.location = (lc.get('cx', 0), lc.get('cy', 0), 0)
LINEN_MAT = mat_linen(lc)
linen.data.materials.append(LINEN_MAT)
if lc.get('outer', True):          # surrounding cloth (same weave, repeated) so the oblique view never shows the plane edge
    lc2 = dict(lc); lc2.pop('imprint', None)
    om = mat_linen(lc2)
    me = bpy.data.meshes.new('linen_outer'); OW, OH = 4000.0, 4000.0
    me.from_pydata([(-OW / 2, -OH / 2, -0.02), (OW / 2, -OH / 2, -0.02), (OW / 2, OH / 2, -0.02), (-OW / 2, OH / 2, -0.02)], [], [[0, 1, 2, 3]])
    uvl = me.uv_layers.new(name='UVMap')
    uvl.data.foreach_set('uv', np.array([[-OW / 2 / lc['w_mm'] + 0.5, -OH / 2 / lc['h_mm'] + 0.5], [OW / 2 / lc['w_mm'] + 0.5, -OH / 2 / lc['h_mm'] + 0.5],
                                         [OW / 2 / lc['w_mm'] + 0.5, OH / 2 / lc['h_mm'] + 0.5], [-OW / 2 / lc['w_mm'] + 0.5, OH / 2 / lc['h_mm'] + 0.5]], np.float32).ravel())
    oo = bpy.data.objects.new('linen_outer', me); sc.collection.objects.link(oo); oo.data.materials.append(om)

# extra meshes (backing patch etc.): linen-textured slab with UVs from its rest position on the cloth
for ex in CFG.get('extras', []):
    d = np.load(ex['npz'])
    Fl = [[int(i) for i in f if i >= 0] for f in d['F']]
    me = bpy.data.meshes.new(ex['name']); me.from_pydata(d['V'].tolist(), [], Fl); me.update()
    uvl = me.uv_layers.new(name='UVMap')
    vi = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', vi)
    V = d['V'][vi]
    uv = np.c_[(V[:, 0] - lc.get('cx', 0)) / lc['w_mm'] + 0.5, (V[:, 1] - lc.get('cy', 0)) / lc['h_mm'] + 0.5]
    uvl.data.foreach_set('uv', uv.astype(np.float32).ravel())
    ob = bpy.data.objects.new(ex['name'], me); sc.collection.objects.link(ob)
    ob.data.materials.append(LINEN_MAT if ex.get('material', 'linen') == 'linen' else LINEN_MAT)
    if ex.get('parent'):
        bpy.context.view_layer.update()
        par = bpy.data.objects.get(ex['parent']); ob.parent = par; ob.matrix_parent_inverse = par.matrix_world.inverted()

# world: dim warm "studio ceiling" gradient (gives metal thread something to reflect, soft ambient fill)
w = bpy.data.worlds.new('w'); w.use_nodes = True
wn = w.node_tree; bg = wn.nodes['Background']
tc = wn.nodes.new('ShaderNodeTexCoord'); sx = wn.nodes.new('ShaderNodeSeparateXYZ'); wn.links.new(tc.outputs['Generated'], sx.inputs[0])
ramp = wn.nodes.new('ShaderNodeValToRGB'); wn.links.new(sx.outputs[2], ramp.inputs[0])
wc = CFG.get('world', {'low': [0.010, 0.009, 0.008], 'high': [0.16, 0.14, 0.115]})
ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = (*wc['low'], 1)
ramp.color_ramp.elements[1].position = 0.9; ramp.color_ramp.elements[1].color = (*wc['high'], 1)
wn.links.new(ramp.outputs[0], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0
sc.world = w

# lights
def sun(name, az, el, energy, color, shadow=True, angle=1.5):
    ld = bpy.data.lights.new(name, 'SUN'); ld.energy = energy; ld.color = color; ld.angle = math.radians(angle)
    ld.use_shadow = shadow
    ob = bpy.data.objects.new(name, ld); sc.collection.objects.link(ob)
    set_sun_dir(ob, az, el)
    if shadow:
        ld.shadow_cascade_count = CFG.get('cascades', 1)
        ld.shadow_cascade_max_distance = CFG['camera'].get('cascade_max', 2000)
        ld.shadow_cascade_exponent = 0.8; ld.shadow_cascade_fade = 0.1
        ld.shadow_buffer_bias = CFG.get('shadow_bias', 0.02)
        ld.use_contact_shadow = True
        ld.contact_shadow_distance = 1.5; ld.contact_shadow_bias = 0.02; ld.contact_shadow_thickness = 0.3
    return ob

def set_sun_dir(ob, az, el):
    # az: direction the light COMES FROM, degrees, 0 = +x (screen right), 90 = +y (screen up); el above cloth plane
    a = math.radians(az); e = math.radians(el)
    d = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))   # towards light
    ob.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()

LC = CFG['lights']
key = sun('key', LC['key_az'], LC['key_el'], LC['key_energy'], LC.get('key_color', (1.0, 0.92, 0.82)), True, LC.get('key_angle', 1.2))
fill = sun('fill', LC['key_az'] + 180, LC.get('fill_el', 40), LC['key_energy'] * LC.get('fill_ratio', 0.08), (0.80, 0.86, 1.0), False)
rim = sun('rim', LC.get('rim_az', 20), LC.get('rim_el', 8), LC['key_energy'] * LC.get('rim_ratio', 0.22), (1.0, 0.86, 0.66), LC.get('rim_shadow', False))

# camera
cc = CFG['camera']
cd = bpy.data.cameras.new('cam'); cd.lens = cc.get('lens', 100); cd.sensor_width = 36
cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
def place_cam(loc, target, roll=0.0):
    cam.location = Vector(loc)
    dvec = Vector(target) - Vector(loc)
    q = dvec.to_track_quat('-Z', 'Y')
    cam.rotation_euler = q.to_euler()
    if roll: cam.rotation_euler.rotate_axis('Z', math.radians(roll))
place_cam(cc['loc'], cc['target'], cc.get('roll', 0))
cd.clip_start = cc.get('clip_start', 1); cd.clip_end = cc.get('clip_end', 5000)
if cc.get('fstop'):
    cd.dof.use_dof = True; cd.dof.aperture_fstop = cc['fstop']
    cd.dof.focus_distance = cc.get('focus', (Vector(cc['target']) - Vector(cc['loc'])).length)
    if cc.get('focus_point'):
        fp = Vector(cc['focus_point']); fwd = (Vector(cc['target']) - Vector(cc['loc'])).normalized()
        cd.dof.focus_distance = (fp - Vector(cc['loc'])).dot(fwd)

# render settings
R = CFG['render']
sc.render.engine = 'BLENDER_EEVEE'
e = sc.eevee
e.taa_render_samples = R.get('taa', 16)
e.use_gtao = True; e.gtao_distance = R.get('gtao_distance', 1.2); e.gtao_factor = R.get('gtao_factor', 1.0)
e.use_soft_shadows = True
e.shadow_cascade_size = R.get('cascade_size', '4096'); e.use_shadow_high_bitdepth = True
e.shadow_cube_size = '512'
e.use_ssr = False; e.use_bloom = False
e.use_motion_blur = False
sc.render.filter_size = R.get('filter', 1.2)
sc.render.resolution_x = R['w']; sc.render.resolution_y = R['h']; sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'; sc.render.image_settings.color_depth = str(R.get('depth', 16))
sc.view_settings.view_transform = R.get('view', 'Standard')
try: sc.view_settings.look = R.get('look', 'None')
except Exception as ex: print('look', ex)
sc.view_settings.exposure = R.get('exposure', -1.5)
sc.render.fps = 30
print('scene built: verts', NV, 't', round(time.time() - T0, 1), flush=True)

# ------------------------------------------------------------------------------------------- animation hooks
def smooth(t): t = min(1, max(0, t)); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t

def kf_eval(keys, f):
    """keys: list of [frame, value...]; smoothstep interpolation"""
    if f <= keys[0][0]: return keys[0][1:]
    for k0, k1 in zip(keys[:-1], keys[1:]):
        if f <= k1[0]:
            t = smooth((f - k0[0]) / max(1e-6, k1[0] - k0[0]))
            return [lerp(a, b, t) for a, b in zip(k0[1:], k1[1:])]
    return keys[-1][1:]

ANIM = CFG.get('anim', {})
TETHER_OB = None

def update_tethers(f):
    global TETHER_OB
    td = ANIM.get('tethers')
    if not td: return
    root = bpy.data.objects[ANIM['root']]
    bpy.context.view_layer.update()
    Mw = root.matrix_world
    A = np.array(td['anchor_local'], np.float64)          # points on the figure, in root-local coords at rest
    Hh = np.array(td['holes'], np.float64)                # linen holes (world)
    cols = np.array(td['colors'], np.float32)
    snap = kf_eval(ANIM['keys'], f)[3] if len(ANIM['keys'][0]) > 4 else 0
    P_all, RW, RH, C, offs, meta = [], [], [], [], [0], []
    for k in range(len(A)):
        a = np.array(Mw @ Vector(A[k]))
        h = Hh[k]
        L = np.linalg.norm(a - h)
        if L < 0.15: continue
        if snap > td['snap_at'][k]: continue
        n = 14; t = np.linspace(0, 1, n)[:, None]
        sag = 0.25 * L * (1 - min(1, L / td.get('taut_len', 6.0)))
        mid_dir = np.array([0, 0, -1.0])
        pts = h * (1 - t) + a * t + mid_dir * sag * 4 * t * (1 - t)
        pts[0, 2] = -0.25
        P_all.append(pts); RW.append(np.full(n, 0.2)); RH.append(np.full(n, 0.2)); C.append(np.repeat(cols[k][None], n, 0))
        offs.append(offs[-1] + n); meta.append([0, 9, 0.75, 6, 9])
    if TETHER_OB is not None:
        me = TETHER_OB.data; bpy.data.objects.remove(TETHER_OB); bpy.data.meshes.remove(me); TETHER_OB = None
    if not P_all: return
    D = dict(P=np.concatenate(P_all).astype(np.float32), RW=np.concatenate(RW).astype(np.float32), RH=np.concatenate(RH).astype(np.float32),
             C=np.concatenate(C).astype(np.float32), off=np.array(offs), meta=np.array(meta, np.float32))
    ob, _ = build_tubes('tethers', D, np.arange(len(meta)))
    ob.data.materials.append(get_mat(0)); TETHER_OB = ob

def apply_frame(f):
    if 'stitch' in ANIM:
        T = kf_eval(ANIM['stitch'], f)[0]
        for m in MATS.values():
            n = m.node_tree.nodes.get('REVEAL')
            if n: n.outputs[0].default_value = T
    if 'key_az' in ANIM:
        set_sun_dir(key, *kf_eval(ANIM['key_az'], f))
    if 'cam' in ANIM:
        v = kf_eval(ANIM['cam'], f)
        place_cam(v[0:3], v[3:6], cc.get('roll', 0))
        if cc.get('fstop'): cd.dof.focus_distance = (Vector(v[3:6]) - Vector(v[0:3])).length
    if 'keys' in ANIM:
        root = bpy.data.objects[ANIM['root']]
        lift, tilt, relief = kf_eval(ANIM['keys'], f)[0:3]
        root.location = Vector(ANIM['pivot']) + Vector((0, 0, lift))
        root.rotation_euler = (math.radians(tilt), 0, 0)
        for o in root.children:
            if o.type == 'MESH' and not o.name.startswith('backing'):
                o.scale = (1, 1, relief)
        update_tethers(f)

frames = R.get('frames', [1])
out = R['out']
times = []
for f in frames:
    apply_frame(f)
    sc.frame_set(int(f))
    sc.render.filepath = out % f if '%' in out else out
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    times.append(time.time() - t1)
    print('RENDERED frame', f, 'in', round(times[-1], 1), 's ->', sc.render.filepath, flush=True)
json.dump({'verts': NV, 'frame_times': times, 'build_s': T0}, open(out.replace('%04d', 'stats').split('.png')[0] + '_stats.json', 'w'))
print('ALL DONE', round(time.time() - T0, 1), flush=True)
