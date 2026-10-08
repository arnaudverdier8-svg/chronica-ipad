"""CHRONICA PoC - Eevee legacy (Blender 4.0.2) part of 'the cloth becomes the board' (zero-tilt swap still + f1726-1766).
Ground = displaced board mesh whose emission is the R25 radiance (A = stitched icons, B = lifted footprints, switched per
piece at its rise frame), modulated by Eevee's own diffuse lighting of the swollen geometry relative to the flat cloth
(ratio via Shader-to-RGB), so the zero-tilt frame equals the R25 frame by construction and piece shadows / coupon swell
come from Eevee. Pieces = the game's OBJs with a stitch material port (palette albedo, laid-wool bump, brown
inverted-hull outline), procedural pines, figure cards; pop-up hinge on twos; thread tethers that snap.
xvfb-run -a -s "-screen 0 1920x1080x24" blender -b --factory-startup -P bl_scene.py -- --res 2560 1440 --taa 16 --frames 1725,1726-1766 [--calib] [--save scene.blend]
"""
import bpy, sys, os, json, math, time
from mathutils import Vector, Matrix, Euler, Quaternion
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import numpy as np
import anim

def arg(name, n=1, default=None):
    if name in argv:
        i = argv.index(name)
        return argv[i + 1:i + 1 + n] if n > 1 else argv[i + 1]
    return default
RW, RH = [int(v) for v in arg('--res', 2, ['1280', '720'])]
TAA = int(arg('--taa', 1, '8'))
OUTD = arg('--out', 1, f'{POC}/ev')
CALIB = '--calib' in argv
NOPIECES = '--nopieces' in argv
fr = arg('--frames', 1, '1725')
FRAMES = []
for part in fr.split(','):
    if '-' in part:
        a, b = part.split('-'); FRAMES += list(range(int(a), int(b) + 1))
    else:
        FRAMES.append(int(part))
os.makedirs(OUTD, exist_ok=True)
T0 = time.time()
def log(*a): print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)
E = f'{POC}/data/eevee'; D = f'{POC}/maps'
LT = json.load(open(f'{E}/lights.json'))
AN = json.load(open(f'{E}/anim.json'))
PIECES = json.load(open(f'{POC}/data/pieces.json'))
LAYOUT = json.load(open(f'{POC}/data/layout.json'))
REF = json.load(open(f'{E}/ref.json'))['ref'] if os.path.exists(f'{E}/ref.json') and not CALIB else [1.0, 1.0, 1.0]
MOD = f'{A}/assets/models'
from piece_palette import col as pcol, OUTLINE

def srgb_lin(hexs):
    h = hexs.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
ee = sc.eevee
ee.taa_render_samples = TAA
ee.use_gtao = True; ee.gtao_distance = 0.09; ee.gtao_factor = 0.9
ee.use_soft_shadows = True; ee.shadow_cascade_size = '4096'; ee.shadow_cube_size = '1024'; ee.use_shadow_high_bitdepth = True
ee.use_ssr = False; ee.use_bloom = False
# camera-only motion blur on the crane (180 deg shutter); pieces move on twos via python, so they get none (pipeline 7.1)
ee.use_motion_blur = False;  # (Eevee legacy MB had no effect with python-driven frames; camera blur is done in comp.py)
_unused = '--nomb' not in argv; ee.motion_blur_shutter = 0.5; ee.motion_blur_steps = 1; ee.motion_blur_max = 48
ee.light_threshold = 0.001
sc.render.resolution_x, sc.render.resolution_y = RW, RH
sc.render.resolution_percentage = 100
sc.render.filter_size = 1.2
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
sc.view_settings.exposure = 0.0; sc.view_settings.gamma = 1.0
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '16'
sc.render.image_settings.exr_codec = 'ZIP'; sc.render.image_settings.color_mode = 'RGBA'
sc.render.use_persistent_data = True

# ------------------------------------------------------------------ world (cool fill) and lights (Act V rig, same as R25)
world = bpy.data.worlds.new('fill'); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes['Background']
fc = [c * LT['fill_i'] for c in LT['fill']]
bg.inputs['Color'].default_value = (fc[0], fc[1], fc[2], 1); bg.inputs['Strength'].default_value = 1.0

def bl_dir(Lb):            # board (x right, y down, z up) -> Blender (x, -y, z)
    return Vector((Lb[0], -Lb[1], Lb[2])).normalized()

def sun(name, Lb, color, strength, angle_deg, shadow=True):
    ld = bpy.data.lights.new(name, 'SUN'); ld.color = color; ld.energy = strength
    ld.angle = math.radians(angle_deg); ld.use_shadow = shadow
    if shadow:
        ld.use_contact_shadow = True; ld.contact_shadow_distance = 0.08; ld.contact_shadow_thickness = 0.012
        ld.contact_shadow_bias = 0.01
        ld.shadow_cascade_count = 4; ld.shadow_cascade_max_distance = 36.0; ld.shadow_cascade_exponent = 0.75
        ld.shadow_cascade_fade = 0.1; ld.shadow_buffer_bias = 0.3
    ob = bpy.data.objects.new(name, ld); sc.collection.objects.link(ob)
    ob.rotation_euler = bl_dir(Lb).to_track_quat('Z', 'Y').to_euler()
    return ob
sinel = math.sin(math.radians(LT['el']))
S_KEY = math.pi * LT['key_i'] * (sinel + 0.25) / (1.25 * sinel)
key = sun('key', LT['L_board'], tuple(LT['key']), S_KEY, 3.0, True)
rim = sun('rim', LT['rim_board'], tuple(LT['key']), math.pi * LT['rim_i'] * LT['key_i'] * 0.8, 6.0, False)

# ------------------------------------------------------------------ camera
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.sensor_fit = 'VERTICAL'; cam.data.lens_unit = 'FOV'; cam.data.angle_y = math.radians(FOV_V)
cam.data.clip_start = 2.0; cam.data.clip_end = 80.0

CLOSE = arg('--closeup', 3, None)
def set_camera(f):
    pose = camera_pose(f)
    if CLOSE:
        pose = dict(pitch=60.0, target=(float(CLOSE[0]), 0, float(CLOSE[1])), dist=float(CLOSE[2]))
    p = math.radians(pose['pitch']); d = pose['dist']; T = pose['target']
    cam.location = (T[0], -(T[2] + math.cos(p) * d), math.sin(p) * d)
    cam.rotation_euler = (math.pi / 2 - p, 0, 0)

# keyframe the camera on every frame (motion vectors for the blur are evaluated on sub-frames)
for _f in range(F_SWAP0, F1 + 2):
    set_camera(_f)
    cam.keyframe_insert('location', frame=_f); cam.keyframe_insert('rotation_euler', frame=_f)
for fc_ in cam.animation_data.action.fcurves:
    for kp in fc_.keyframe_points: kp.interpolation = 'LINEAR'

# ------------------------------------------------------------------ images
def img(path, noncolor=False, closest=False):
    im = bpy.data.images.load(path, check_existing=True)
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    else:
        try: im.colorspace_settings.name = 'Linear Rec.709' if path.endswith('.exr') else 'sRGB'
        except Exception: im.colorspace_settings.name = 'Linear'
    return im

# ------------------------------------------------------------------ shared node helpers
def kmap_factor(nt, N, Lk):
    """(0.2 + 0.8 * key pool) at the shading point (world position -> board uv)"""
    geo = N.new('ShaderNodeNewGeometry')
    sep = N.new('ShaderNodeSeparateXYZ'); Lk.new(geo.outputs['Position'], sep.inputs[0])
    mu = N.new('ShaderNodeMath'); mu.operation = 'MULTIPLY_ADD'; mu.inputs[1].default_value = 1 / (BX1 - BX0); mu.inputs[2].default_value = -BX0 / (BX1 - BX0)
    Lk.new(sep.outputs['X'], mu.inputs[0])
    mv = N.new('ShaderNodeMath'); mv.operation = 'MULTIPLY_ADD'; mv.inputs[1].default_value = 1 / (BZ1 - BZ0); mv.inputs[2].default_value = 1 + BZ0 / (BZ1 - BZ0)
    Lk.new(sep.outputs['Y'], mv.inputs[0])
    cmb = N.new('ShaderNodeCombineXYZ'); Lk.new(mu.outputs[0], cmb.inputs[0]); Lk.new(mv.outputs[0], cmb.inputs[1])
    tk = N.new('ShaderNodeTexImage'); tk.image = KMAP; tk.extension = 'EXTEND'; tk.interpolation = 'Linear'
    Lk.new(cmb.outputs[0], tk.inputs['Vector'])
    ma = N.new('ShaderNodeMath'); ma.operation = 'MULTIPLY_ADD'; ma.inputs[1].default_value = 0.8; ma.inputs[2].default_value = 0.2
    Lk.new(tk.outputs['Color'], ma.inputs[0])
    return ma.outputs[0]

def lit_emission(m, shader_out, N, Lk, out_node, alpha=None):
    """Shader-to-RGB of the lit BSDF x key pool -> emission (keeps one light rig with R25, incl. the pool)."""
    s2r = N.new('ShaderNodeShaderToRGB'); Lk.new(shader_out, s2r.inputs[0])
    kf = kmap_factor(m.node_tree, N, Lk)
    mul = N.new('ShaderNodeVectorMath'); mul.operation = 'SCALE'
    Lk.new(s2r.outputs['Color'], mul.inputs[0]); Lk.new(kf, mul.inputs['Scale'])
    em = N.new('ShaderNodeEmission'); Lk.new(mul.outputs[0], em.inputs['Color'])
    if alpha is None:
        Lk.new(em.outputs[0], out_node.inputs['Surface'])
    else:
        tr = N.new('ShaderNodeBsdfTransparent'); mx = N.new('ShaderNodeMixShader')
        Lk.new(alpha, mx.inputs[0]); Lk.new(tr.outputs[0], mx.inputs[1]); Lk.new(em.outputs[0], mx.inputs[2])
        Lk.new(mx.outputs[0], out_node.inputs['Surface'])

KMAP = img(f'{E}/kmap.exr', noncolor=True)
BUMP = img(f'{E}/stitch_bump.png', noncolor=True)

def wool_material(name, rgb_lin, bump_scale=2.3, bump_strength=0.55, rough=0.85, sheen=0.6):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    out = N['Material Output']; N.remove(N['Principled BSDF'])
    b = N.new('ShaderNodeBsdfPrincipled')
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (bump_scale,) * 3
    Lk.new(tc.outputs['Object'], mp.inputs['Vector'])
    tb = N.new('ShaderNodeTexImage'); tb.image = BUMP; tb.projection = 'BOX'; tb.projection_blend = 0.25; tb.interpolation = 'Linear'
    Lk.new(mp.outputs['Vector'], tb.inputs['Vector'])
    bu = N.new('ShaderNodeBump'); bu.inputs['Strength'].default_value = bump_strength; bu.inputs['Distance'].default_value = 0.004
    Lk.new(tb.outputs['Color'], bu.inputs['Height']); Lk.new(bu.outputs['Normal'], b.inputs['Normal'])
    # per-strand colour variation from the same tile (dye irregularity)
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 0.35
    mx.inputs[6].default_value = (*rgb_lin, 1)
    ramp = N.new('ShaderNodeMapRange'); ramp.inputs['To Min'].default_value = 0.72; ramp.inputs['To Max'].default_value = 1.12
    Lk.new(tb.outputs['Color'], ramp.inputs['Value'])
    Lk.new(ramp.outputs['Result'], mx.inputs[7])
    Lk.new(mx.outputs[2], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    b.inputs['Sheen Weight'].default_value = sheen; b.inputs['Sheen Roughness'].default_value = 0.42
    b.inputs['Specular IOR Level'].default_value = 0.3
    lit_emission(m, b.outputs[0], N, Lk, out)
    return m

def outline_material():
    m = bpy.data.materials.new('outline'); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    N.remove(N['Principled BSDF'])
    em = N.new('ShaderNodeEmission'); c = srgb_lin(OUTLINE)
    kf = kmap_factor(nt, N, Lk)
    mul = N.new('ShaderNodeVectorMath'); mul.operation = 'SCALE'; mul.inputs[0].default_value = (c[0] * 0.55, c[1] * 0.55, c[2] * 0.55)
    Lk.new(kf, mul.inputs['Scale']); Lk.new(mul.outputs[0], em.inputs['Color'])
    Lk.new(em.outputs[0], N['Material Output'].inputs['Surface'])
    m.use_backface_culling = True
    return m
OUTLINE_MAT = outline_material()

# ------------------------------------------------------------------ ground: displaced board mesh with the R25 emission
hlow = np.load(f'{D}/hlow.npy').astype(np.float32)          # mm, board px grid
hm = np.load(f'{D}/hexmap.npz'); HID = hm['hid'].astype(np.int32); DEDGE = hm['dedge'].astype(np.float32)
STEP_MM = 1.0
nx = int((BX1 - BX0) * MMU / STEP_MM) + 1; nz = int((BZ1 - BZ0) * MMU / STEP_MM) + 1
gxs = np.linspace(BX0, BX1, nx); gzs = np.linspace(BZ0, BZ1, nz)
GXv, GZv = np.meshgrid(gxs, gzs)
pu = np.clip(((GXv - BX0) * PPU).astype(int), 0, W - 1); pv = np.clip(((GZv - BZ0) * PPU).astype(int), 0, H - 1)
V_H = hlow[pv, pu].ravel()                                  # mm
V_HID = HID[pv, pu].ravel(); V_DE = DEDGE[pv, pu].ravel()
ter = np.array([h['t'] for h in LAYOUT['hexes']]); land = ~np.isin(ter, ['sea', 'lake'])
V_LAND = land[V_HID]
V_DOME = np.where(V_LAND, np.sqrt(np.clip(1 - (1 - np.clip((V_DE - 0.6) / 7.0, 0, 1)) ** 2, 0, 1)), 0).astype(np.float32)
HEX_SW = np.array([anim.hex_swell_start(h['q'], h['r']) for h in LAYOUT['hexes']])
V_SW = HEX_SW[V_HID]
co = np.stack([GXv.ravel(), -GZv.ravel(), np.zeros(nx * nz)], -1).astype(np.float32)
vid = np.arange(nx * nz).reshape(nz, nx)
q = np.stack([vid[:-1, :-1], vid[:-1, 1:], vid[1:, 1:], vid[1:, :-1]], -1).reshape(-1, 4)   # CCW seen from +Z (y flipped)
me = bpy.data.meshes.new('board')
me.vertices.add(len(co)); me.vertices.foreach_set('co', co.ravel())
me.loops.add(q.size); me.loops.foreach_set('vertex_index', q.ravel().astype(np.int32))
me.polygons.add(len(q)); me.polygons.foreach_set('loop_start', (np.arange(len(q)) * 4).astype(np.int32))
me.update(calc_edges=True)
uvl = me.uv_layers.new(name='uv')
lv = q.ravel()
uu = (GXv.ravel()[lv] - BX0) / (BX1 - BX0); vv = 1 - (GZv.ravel()[lv] - BZ0) / (BZ1 - BZ0)
uvl.data.foreach_set('uv', np.stack([uu, vv], -1).astype(np.float32).ravel())
me.polygons.foreach_set('use_smooth', np.ones(len(q), bool))
me.update()
board = bpy.data.objects.new('board', me); sc.collection.objects.link(board)
log('board mesh', len(co))

gm = bpy.data.materials.new('board'); gm.use_nodes = True
nt = gm.node_tree; N = nt.nodes; Lk = nt.links
N.remove(N['Principled BSDF']); out = N['Material Output']
uvn = N.new('ShaderNodeUVMap'); uvn.uv_map = 'uv'
tA = N.new('ShaderNodeTexImage'); tA.image = img(f'{D}/radA.exr'); tA.interpolation = 'Linear'; tA.extension = 'EXTEND'
tB = N.new('ShaderNodeTexImage'); tB.image = img(f'{D}/radB.exr'); tB.interpolation = 'Linear'; tB.extension = 'EXTEND'
tR = N.new('ShaderNodeTexImage'); tR.image = img(f'{E}/reveal.exr', noncolor=True); tR.interpolation = 'Closest'; tR.extension = 'EXTEND'
for t in (tA, tB, tR): Lk.new(uvn.outputs['UV'], t.inputs['Vector'])
fval = N.new('ShaderNodeValue'); fval.name = 'FRAME'; fval.outputs[0].default_value = 0.0
gt = N.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'
Lk.new(fval.outputs[0], gt.inputs[0]); Lk.new(tR.outputs['Color'], gt.inputs[1])     # frame > reveal - 0.5 (reveal stored -0.5 below)
mixAB = N.new('ShaderNodeMix'); mixAB.data_type = 'RGBA'
Lk.new(gt.outputs[0], mixAB.inputs['Factor']); Lk.new(tA.outputs['Color'], mixAB.inputs[6]); Lk.new(tB.outputs['Color'], mixAB.inputs[7])
dif = N.new('ShaderNodeBsdfDiffuse'); dif.inputs['Color'].default_value = (1, 1, 1, 1)
s2r = N.new('ShaderNodeShaderToRGB'); Lk.new(dif.outputs[0], s2r.inputs[0])
div = N.new('ShaderNodeVectorMath'); div.operation = 'DIVIDE'; div.inputs[1].default_value = tuple(REF)
Lk.new(s2r.outputs['Color'], div.inputs[0])
kval = N.new('ShaderNodeValue'); kval.name = 'RATIO_K'; kval.outputs[0].default_value = 0.85
mixr = N.new('ShaderNodeMix'); mixr.data_type = 'VECTOR'; mixr.inputs[4].default_value = (1, 1, 1)
Lk.new(kval.outputs[0], mixr.inputs['Factor']); Lk.new(div.outputs[0], mixr.inputs[5])
mulc = N.new('ShaderNodeVectorMath'); mulc.operation = 'MULTIPLY'
Lk.new(mixAB.outputs[2], mulc.inputs[0]); Lk.new(mixr.outputs[1], mulc.inputs[1])
em = N.new('ShaderNodeEmission')
if CALIB:
    Lk.new(s2r.outputs['Color'], em.inputs['Color'])
else:
    Lk.new(mulc.outputs[0], em.inputs['Color'])
Lk.new(em.outputs[0], out.inputs['Surface'])
board.data.materials.append(gm)
FRAME_NODE = fval

# towns and quarries press the padding flat under their base once they stand (they sit on the coupon, not in it)
PRESS = []
for _i, _p in enumerate(PIECES):
    if _p.get('skip') or AN['starts'][_i] is None or _p['kind'] not in ('town', 'site'): continue
    bx0, bz0, bx1, bz1 = _p['base']
    j0, j1 = int((bx0 - BX0) * MMU / STEP_MM) - 3, int((bx1 - BX0) * MMU / STEP_MM) + 4
    i0, i1 = int((bz0 - BZ0) * MMU / STEP_MM) - 3, int((bz1 - BZ0) * MMU / STEP_MM) + 4
    ii, jj = np.mgrid[max(i0, 0):min(i1, nz), max(j0, 0):min(j1, nx)]
    xg = BX0 + jj * STEP_MM / MMU; zg = BZ0 + ii * STEP_MM / MMU
    dx = np.maximum(np.maximum(bx0 - xg, xg - bx1), 0) * MMU; dz = np.maximum(np.maximum(bz0 - zg, zg - bz1), 0) * MMU
    wgt = np.clip(1 - np.hypot(dx, dz) / 2.5, 0, 1)
    PRESS.append(((ii * nx + jj).ravel(), wgt.ravel().astype(np.float32), AN['starts'][_i]))

def update_ground(f):
    g = anim.growth(f)
    sw = np.array([anim.swell(f, s) for s in HEX_SW], np.float32)[V_HID]
    z_mm = g * V_H + 1.1 * sw * V_DOME * V_LAND
    for idx, wgt, st in PRESS:
        if anim.twos(f) >= st:
            k = min(1.0, (anim.twos(f) - st + 2) / 6.0)
            base_h = np.percentile(z_mm[idx][wgt > 0.99], 15) if (wgt > 0.99).any() else 0.0
            z_mm[idx] = z_mm[idx] * (1 - wgt * k) + np.minimum(z_mm[idx], base_h) * wgt * k
    co[:, 2] = z_mm / MMU
    me.vertices.foreach_set('co', co.ravel()); me.update()
    return z_mm

def ground_height(x, zg, z_mm):
    """board height (BU) at game (x, z) from the current vertex heights"""
    i = int(round((zg - BZ0) * MMU / STEP_MM)); j = int(round((x - BX0) * MMU / STEP_MM))
    i = min(max(i, 0), nz - 1); j = min(max(j, 0), nx - 1)
    return float(z_mm[i * nx + j]) / MMU

# ------------------------------------------------------------------ pieces
MODELS = {m_['name']: m_ for m_ in json.load(open(f'{MOD}/models.json'))}
MESH = {}
MATS = {}

def piece_mat(nm, realm):
    k = (nm, realm)
    if k not in MATS:
        hexc = pcol(nm, realm)
        rough = 0.6 if nm in ('gold', 'metal') else 0.85
        MATS[k] = wool_material(f'pm_{nm}_{realm}', srgb_lin(hexc), rough=rough, sheen=0.25 if nm.startswith('roof') or nm == 'slate' else 0.6)
    return MATS[k]

def load_model(name, realm):
    k = (name, realm)
    if k in MESH: return MESH[k]
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=f'{MOD}/{name}.obj', forward_axis='NEGATIVE_Z', up_axis='Y')
    obs = [o for o in bpy.data.objects if o not in before]
    for o in obs:
        o.select_set(True); bpy.context.view_layer.objects.active = o
    if len(obs) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mesh = o.data
    for i, s_ in enumerate(o.material_slots):
        base = s_.material.name.split('.')[0] if s_.material else 'stone'
        mesh.materials[i] = piece_mat(base, realm)
    n0 = len(mesh.materials)
    mesh.materials.append(OUTLINE_MAT)
    bpy.data.objects.remove(o)
    MESH[k] = (mesh, n0)
    return MESH[k]

def tree_mesh():
    if 'tree' in MESH: return MESH['tree']
    bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=1.0, radius2=0.0, depth=0.86, location=(0, 0, 0.14 + 0.43))
    crown = bpy.context.active_object
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.16, depth=0.16, location=(0, 0, 0.08))
    trunk = bpy.context.active_object
    crown.data.materials.append(wool_material('pine', srgb_lin('#1C3B22'), bump_scale=3.0, sheen=0.5))
    trunk.data.materials.append(wool_material('trunk', srgb_lin('#46301C')))
    crown.select_set(True); trunk.select_set(True); bpy.context.view_layer.objects.active = crown
    bpy.ops.object.join()
    o = bpy.context.active_object
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    o.data.materials.append(OUTLINE_MAT)
    mesh = o.data; bpy.data.objects.remove(o)
    MESH['tree'] = (mesh, 2)
    return MESH['tree']

def card_mesh(unit, realm, w, h):
    k = ('card', unit, realm)
    if k in MESH: return MESH[k]
    me_ = bpy.data.meshes.new(f'card_{unit}_{realm}')
    me_.from_pydata([(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, h), (-w / 2, 0, h)], [], [(0, 1, 2, 3)])
    uv = me_.uv_layers.new(name='uv'); uv.data.foreach_set('uv', [0, 0, 1, 0, 1, 1, 0, 1])
    m = bpy.data.materials.new(f'card_{unit}_{realm}'); m.use_nodes = True
    nt_ = m.node_tree; N_ = nt_.nodes; L_ = nt_.links
    out_ = N_['Material Output']; N_.remove(N_['Principled BSDF'])
    b = N_.new('ShaderNodeBsdfPrincipled')
    ta = N_.new('ShaderNodeTexImage'); ta.image = img(f'{E}/cards/{unit}_{realm}_alb.png'); ta.interpolation = 'Linear'; ta.extension = 'CLIP'
    tn = N_.new('ShaderNodeTexImage'); tn.image = img(f'{E}/cards/{unit}_{realm}_nrm.png', noncolor=True); tn.extension = 'CLIP'
    nm = N_.new('ShaderNodeNormalMap'); nm.uv_map = 'uv'; nm.inputs['Strength'].default_value = 0.9
    L_.new(tn.outputs['Color'], nm.inputs['Color']); L_.new(nm.outputs['Normal'], b.inputs['Normal'])
    # back of the slip = linen backing
    geo = N_.new('ShaderNodeNewGeometry')
    mx = N_.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    L_.new(geo.outputs['Backfacing'], mx.inputs['Factor']); L_.new(ta.outputs['Color'], mx.inputs[6]); mx.inputs[7].default_value = (*srgb_lin('#C9B58E'), 1)
    L_.new(mx.outputs[2], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.82; b.inputs['Sheen Weight'].default_value = 0.5; b.inputs['Specular IOR Level'].default_value = 0.3
    gtc = N_.new('ShaderNodeMath'); gtc.operation = 'GREATER_THAN'; gtc.inputs[1].default_value = 0.5
    L_.new(ta.outputs['Alpha'], gtc.inputs[0])
    lit_emission(m, b.outputs[0], N_, L_, out_, alpha=gtc.outputs[0])
    m.blend_method = 'CLIP'; m.shadow_method = 'CLIP'; m.alpha_threshold = 0.5
    me_.materials.append(m)
    MESH[k] = (me_, 1)
    return MESH[k]

TETHER_MATS = {}
def tether_mat(kind):
    if kind not in TETHER_MATS:
        c = {'tree': '#2E4A2C', 'card': '#7A4E2A', 'town': '#B9A27E', 'site': '#A08060', 'banner': '#C8962E'}.get(kind, '#6B4A2E')
        TETHER_MATS[kind] = wool_material(f'tether_{kind}', srgb_lin(c), bump_strength=0.0)
    return TETHER_MATS[kind]

PCS = []
starts = AN['starts']
for i, p in enumerate(PIECES):
    if NOPIECES or p.get('skip') or starts[i] is None: continue
    piv = bpy.data.objects.new(f'piv_{p["id"]}', None); sc.collection.objects.link(piv)
    scl = bpy.data.objects.new(f'scl_{p["id"]}', None); sc.collection.objects.link(scl); scl.parent = piv
    yb = -p['z_back']
    piv.location = (p['x'], yb, 0.0)
    if p['kind'] in ('town', 'site', 'lumber', 'banner'):
        mesh, n0 = load_model(p['model'], p.get('realm') or 'gold')
        ob = bpy.data.objects.new(p['id'], mesh); sc.collection.objects.link(ob); ob.parent = scl
        s = p['scale']; ob.scale = (s, s, s)
        ob.location = (0, -(p['z'] - p['z_back']), 0)          # model origin is depth-in-front of the back plane
        th = 0.0045 if p['kind'] == 'town' else 0.003
    elif p['kind'] == 'tree':
        mesh, n0 = tree_mesh()
        ob = bpy.data.objects.new(p['id'], mesh); sc.collection.objects.link(ob); ob.parent = scl
        ob.scale = (p['rad'], p['rad'], p['height'] / 1.0)
        ob.location = (0, -p['rad'], 0)
        th = 0.0035
    else:
        mesh, n0 = card_mesh(p['unit'], p['realm'], p['w'], p['height'])
        ob = bpy.data.objects.new(p['id'], mesh); sc.collection.objects.link(ob); ob.parent = scl
        th = None
    if th:
        mod = ob.modifiers.new('outline', 'SOLIDIFY'); mod.thickness = th; mod.offset = 1.0
        mod.use_flip_normals = True; mod.material_offset = n0; mod.use_rim = False
    # tethers (one curve object per piece)
    cu = bpy.data.curves.new(f'teth_{p["id"]}', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.0085; cu.bevel_resolution = 1
    cu.materials.append(tether_mat(p['kind']))
    tob = bpy.data.objects.new(f'teth_{p["id"]}', cu); sc.collection.objects.link(tob)
    PCS.append(dict(p=p, i=i, piv=piv, scl=scl, ob=ob, teth=tob, cu=cu, start=starts[i], T=AN['tethers'].get(p['id'])))
log('pieces', len(PCS))

def face_point(pc, xl, yl, ang, sy):
    """world (BU) of a point on the piece's front face (face-local x, height y) for hinge angle ang (deg from upright)"""
    p = pc['p']
    depth = (p['base'][3] - p['base'][1]) * sy if p['kind'] != 'card' else 0.0
    if p['kind'] == 'tree': depth = 2 * p['rad'] * sy
    a = -math.radians(ang)
    y0, z0 = -depth, yl
    y1 = y0 * math.cos(a) - z0 * math.sin(a); z1 = y0 * math.sin(a) + z0 * math.cos(a)
    P0 = pc['piv'].location
    return Vector((P0.x + xl, P0.y + y1, P0.z + z1))

def update_pieces(f, z_mm):
    for pc in PCS:
        p = pc['p']; st = pc['start']
        ang = anim.hinge_angle(p, st, f)
        vis = ang is not None
        for o in (pc['ob'],):
            o.hide_render = not vis
        bx0, bz0, bx1, bz1 = p['base']
        hs = [ground_height(bx0 + (bx1 - bx0) * u_, bz0 + (bz1 - bz0) * v_, z_mm) for u_ in (0.1, 0.3, 0.5, 0.7, 0.9) for v_ in (0.1, 0.5, 0.9)]
        pc['piv'].location.z = float(np.percentile(hs, 80)) - 0.001
        cu = pc['cu']; cu.splines.clear()
        if not vis:
            pc['teth'].hide_render = True
            continue
        sy = anim.depth_scale(ang) if p['kind'] != 'card' else 1.0
        pc['scl'].scale = (1, max(sy, 0.02), 1)
        pc['piv'].rotation_euler = (-math.radians(ang), 0, 0)
        # tethers: needle hole (lying position) -> point on the rising face; snap one by one, then recoil
        T = pc['T']; pc['teth'].hide_render = T is None
        if T is None: continue
        ft = anim.twos(f)
        for k, ((xl, yl), sf) in enumerate(zip(T['pts'], T['snap'])):
            hole = face_point(pc, xl, yl, 90.0, 0.0); hole.z = ground_height(hole.x, -hole.y, z_mm) + 0.003
            anc = face_point(pc, xl, yl, ang, sy)
            rr = np.random.default_rng(pc['i'] * 100 + k)
            if ft < sf:
                pts = []
                d = anc - hole; L_ = d.length
                for t in np.linspace(0, 1, 6):
                    sag = 0.05 * L_ * math.sin(math.pi * t) * (1 - min(1.0, (ft - st) / max(1, sf - st)))
                    pts.append(hole + d * t + Vector((0, 0, -sag)))
            else:
                # snapped: a short loose end curling at the hole, and a stub hanging from the piece
                age = ft - sf
                l1 = 0.035 + 0.02 * rr.random()
                ang0 = rr.uniform(0, 2 * math.pi)
                curl = min(1.0, age / 4.0)
                pts = []
                for t in np.linspace(0, 1, 5):
                    a_ = ang0 + curl * 2.2 * t
                    pts.append(hole + Vector((math.cos(a_) * l1 * t, math.sin(a_) * l1 * t, 0.004 + (1 - curl) * 0.02 * t)))
                sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
                for j_, v in enumerate(pts): sp.points[j_].co = (v.x, v.y, v.z, 1)
                l2 = 0.03 + 0.02 * rr.random()
                swing = math.sin(age * 1.3 + k) * math.exp(-age / 6.0) * 0.6
                pts = [anc, anc + Vector((math.sin(swing) * l2 * 0.4, -l2 * 0.3, -l2 * math.cos(swing)))]
                pts = [pts[0], pts[0] * 0.5 + pts[1] * 0.5 + Vector((0, 0, 0.003)), pts[1]]
            sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
            for j_, v in enumerate(pts): sp.points[j_].co = (v.x, v.y, v.z, 1)

# ------------------------------------------------------------------ render loop
if arg('--save'):
    bpy.ops.wm.save_as_mainfile(filepath=arg('--save'))
for f in FRAMES:
    t = time.time()
    set_camera(f)
    z_mm = update_ground(f)
    FRAME_NODE.outputs[0].default_value = float(anim.twos(f)) + 0.5
    update_pieces(f, z_mm)
    sc.frame_set(f)
    sc.render.filepath = f'{OUTD}/f{f:04d}.exr'
    bpy.ops.render.render(write_still=True)
    log('frame', f, '%.1fs' % (time.time() - t))
log('done')
