"""CHRONICA PoC v2 - Eevee legacy (Blender 4.0.2) part of 'the cloth becomes the board' (zero-tilt swap still + f1726-1782).

Light: two candle pools + navy fill, shared with R25 through lightmodel.py. Two coloured suns carry the candles in separate colour channels
(left = R, right = G, the world carries the fill in B), so ONE Shader-to-RGB of a white diffuse gives the three light contributions separately;
every material then multiplies each by its candle's pool map (km texture, per frame), colour and gain (ignition, flicker, swell):
    lit = cL*gL*kL(x)*S_L + cR*gR*kR(x)*S_R + cF*kF(x)*S_F
Ground = displaced board mesh whose emission is the R25 radiance (A stitched icons / B lifted footprints / C healed satin, switched per piece)
times  lit / lit_flat  (the flat, base-state reference), so the zero-tilt frame equals the R25 frame by construction while the swell of the
coupons, contact shadows and the pieces' cast shadows come from Eevee. A metal overlay adds the travelling glint of the couched gold borders.
Pieces = the game OBJs with a felt/stitch material (triplanar R25-style laid wool normal + per-strand shade + dye lots + fuzz rim, palette
albedo) and bevelled edges, procedural tiered felt pines / broadleaf, the re-embroidered figure cards, fibre tethers.
xvfb-run -a -s "-screen 0 1920x1080x24" blender -b --factory-startup -P bl_scene.py -- --res 2560 1440 --taa 16 --frames 1725,1726-1766 [--save scene.blend]"""
import bpy, bmesh, sys, os, json, math, time
from mathutils import Vector, Matrix, Euler, Quaternion
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import numpy as np
import anim
import lightmodel as lm


def arg(name, n=1, default=None):
    if name in argv:
        i = argv.index(name)
        return argv[i + 1:i + 1 + n] if n > 1 else argv[i + 1]
    return default
RW, RH = [int(v) for v in arg('--res', 2, ['1280', '720'])]
TAA = int(arg('--taa', 1, '8'))
OUTD = arg('--out', 1, f'{POC}/ev')
NOPIECES = '--nopieces' in argv
NOGLINT = '--noglint' in argv
WHITE = '--whitepieces' in argv
CLOSE = arg('--closeup', 3, None)
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
KMDIR = f'{POC}/data/eevee/km_frames' if not NOPIECES else f'{POC}/preview/km_tmp'
os.makedirs(KMDIR, exist_ok=True)
AN = json.load(open(f'{E}/anim.json'))
PIECES = json.load(open(f'{POC}/data/pieces.json'))
LAYOUT = json.load(open(f'{POC}/data/layout.json'))
MOD = f'{A}/assets/models'
from piece_palette import col as pcol, OUTLINE


def srgb_lin(hexs):
    h = hexs.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]

# ------------------------------------------------------------------ light constants (same numbers as R25)
KEYC = np.array(lm.key_colour(), np.float64)
CL0 = KEYC * lm.CANDLE['L']['key_i']; CR0 = KEYC * lm.CANDLE['R']['key_i']
CF0 = np.array(lm.FILL_COL, np.float64) * lm.FILL_I
SIN_L = math.sin(math.radians(lm.CANDLE['L']['el'])); SIN_R = math.sin(math.radians(lm.CANDLE['R']['el']))
DL = (SIN_L + 0.25) / 1.25; DR = (SIN_R + 0.25) / 1.25            # R25 wrap diffuse of a flat cloth under each candle
GAINS = []          # (value node L, value node R) of every lit material: set per frame
KT_IMGS = []        # TexImage nodes of the per-frame pool map

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
ee = sc.eevee
ee.taa_render_samples = TAA
ee.use_gtao = True; ee.gtao_distance = 0.09; ee.gtao_factor = 0.9
ee.use_soft_shadows = True; ee.shadow_cascade_size = '4096'; ee.shadow_cube_size = '1024'; ee.use_shadow_high_bitdepth = True
ee.use_ssr = False; ee.use_bloom = False
ee.use_motion_blur = False
ee.light_threshold = 0.001
sc.render.resolution_x, sc.render.resolution_y = RW, RH
sc.render.resolution_percentage = 100
sc.render.filter_size = 1.2
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
sc.view_settings.exposure = 0.0; sc.view_settings.gamma = 1.0
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '16'
sc.render.image_settings.exr_codec = 'ZIP'; sc.render.image_settings.color_mode = 'RGBA'
sc.render.use_persistent_data = True

# ------------------------------------------------------------------ world (fill carried in the B channel) and the two coloured suns
world = bpy.data.worlds.new('fill'); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs['Color'].default_value = (0.0, 0.0, 1.0, 1); bg.inputs['Strength'].default_value = 1.0

def bl_dir(Lb):            # board (x right, y down, z up) -> Blender (x, -y, z)
    return Vector((Lb[0], -Lb[1], Lb[2])).normalized()

def sun(name, Lb, color, strength, angle_deg):
    ld = bpy.data.lights.new(name, 'SUN'); ld.color = color; ld.energy = strength
    ld.angle = math.radians(angle_deg); ld.use_shadow = True
    ld.use_contact_shadow = True; ld.contact_shadow_distance = 0.08; ld.contact_shadow_thickness = 0.012
    ld.contact_shadow_bias = 0.01
    ld.shadow_cascade_count = 4; ld.shadow_cascade_max_distance = 40.0; ld.shadow_cascade_exponent = 0.75
    ld.shadow_cascade_fade = 0.1; ld.shadow_buffer_bias = 0.3
    ob = bpy.data.objects.new(name, ld); sc.collection.objects.link(ob)
    ob.rotation_euler = bl_dir(Lb).to_track_quat('Z', 'Y').to_euler()
    return ob
LTAB = lm.light_table()
sun('candleL', LTAB['candles']['L']['L_board'], (1.0, 0.0, 0.0), math.pi * DL / SIN_L, 8.0)
sun('candleR', LTAB['candles']['R']['L_board'], (0.0, 1.0, 0.0), math.pi * DR / SIN_R, 8.0)

# ------------------------------------------------------------------ camera
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.sensor_fit = 'VERTICAL'; cam.data.lens_unit = 'FOV'; cam.data.angle_y = math.radians(FOV_V)
cam.data.clip_start = 2.0; cam.data.clip_end = 80.0

def set_camera(f):
    pose = camera_pose(f)
    if CLOSE:
        pose = dict(pitch=62.0, target=(float(CLOSE[0]), 0.3, float(CLOSE[1])), dist=float(CLOSE[2]))
    p = math.radians(pose['pitch']); d = pose['dist']; T = pose['target']
    cam.location = (T[0], -(T[2] + math.cos(p) * d), math.sin(p) * d)
    cam.rotation_euler = (math.pi / 2 - p, 0, 0)

# ------------------------------------------------------------------ images
def img(path, noncolor=False):
    im = bpy.data.images.load(path, check_existing=True)
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    else:
        try: im.colorspace_settings.name = 'Linear Rec.709' if path.endswith('.exr') else 'sRGB'
        except Exception: im.colorspace_settings.name = 'Linear'
    return im
KM0 = img(f'{E}/km0.exr', noncolor=True)
_kz = np.load(f'{E}/km0_shape.npy') if os.path.exists(f'{E}/km0_shape.npy') else np.array([H // 4, W // 4])
KT = bpy.data.images.new('KT_pool', int(_kz[1]), int(_kz[0]), alpha=True, float_buffer=True)    # per-frame pool maps (R = left, G = right, B = fill)
KT.colorspace_settings.name = 'Non-Color'
WOOL = img(f'{E}/wool_tile.png', noncolor=True)

# ------------------------------------------------------------------ node helpers
class NB:
    """tiny node-builder bound to a material's tree"""
    def __init__(self, m):
        self.m = m; self.nt = m.node_tree; self.N = self.nt.nodes; self.Lk = self.nt.links
    def node(self, typ, **kw):
        n = self.N.new(typ)
        for k, v in kw.items(): setattr(n, k, v)
        return n
    def link(self, a, b): self.Lk.new(a, b)
    def vmath(self, op, a=None, b=None, scale=None):
        n = self.N.new('ShaderNodeVectorMath'); n.operation = op
        if a is not None: self.set_in(n.inputs[0], a)
        if b is not None: self.set_in(n.inputs[1], b)
        if scale is not None: self.set_in(n.inputs['Scale'], scale)
        return n
    def math(self, op, a=None, b=None, c=None, clamp=False):
        n = self.N.new('ShaderNodeMath'); n.operation = op; n.use_clamp = bool(clamp)
        if a is not None: self.set_in(n.inputs[0], a)
        if b is not None: self.set_in(n.inputs[1], b)
        if c is not None: self.set_in(n.inputs[2], c)
        return n
    def set_in(self, sock, v):
        if hasattr(v, 'node'): self.Lk.new(v, sock)
        elif isinstance(v, (tuple, list)): sock.default_value = tuple(v) if len(v) == len(sock.default_value) else tuple(list(v) + [0] * (len(sock.default_value) - len(v)))
        else: sock.default_value = v
    def value(self, v):
        n = self.N.new('ShaderNodeValue'); n.outputs[0].default_value = v; return n
    def rgb(self, c):
        n = self.N.new('ShaderNodeRGB'); n.outputs[0].default_value = (c[0], c[1], c[2], 1); return n

def board_uv(nb):
    """world position -> board UV (as in the R25 textures)"""
    geo = nb.node('ShaderNodeNewGeometry')
    sep = nb.node('ShaderNodeSeparateXYZ'); nb.link(geo.outputs['Position'], sep.inputs[0])
    mu = nb.math('MULTIPLY_ADD'); mu.inputs[1].default_value = 1 / (BX1 - BX0); mu.inputs[2].default_value = -BX0 / (BX1 - BX0)
    nb.link(sep.outputs['X'], mu.inputs[0])
    mv = nb.math('MULTIPLY_ADD'); mv.inputs[1].default_value = 1 / (BZ1 - BZ0); mv.inputs[2].default_value = 1 + BZ0 / (BZ1 - BZ0)
    nb.link(sep.outputs['Y'], mv.inputs[0])
    cmb = nb.node('ShaderNodeCombineXYZ'); nb.link(mu.outputs[0], cmb.inputs[0]); nb.link(mv.outputs[0], cmb.inputs[1])
    return cmb.outputs[0], geo

def km_tex(nb, uv, image, per_frame=False):
    t = nb.node('ShaderNodeTexImage'); t.image = image; t.extension = 'EXTEND'; t.interpolation = 'Linear'
    nb.link(uv, t.inputs['Vector'])
    if per_frame: KT_IMGS.append(t)
    return t

SHADOW_LIFT = 0.40
GLINT_EXP = 150.0       # narrow Kajiya-Kay lobe: only strands nearly perpendicular to the half vector glint; as the crane turns H the glint travels from one border orientation to the next
GLINT_AMP = 0.80        # light level L1
LVEC = {n_: lm.lvec(lm.CANDLE[n_]['az'], lm.CANDLE[n_]['el']) for n_ in 'LR'}

def lit_terms(nb, uv, shade_rgb, normal=None):
    """lit = cL*gL*kL*S_L + cR*gR*kR*S_R + cF*kF*S_F   (RGB vector socket). shade_rgb = Shader-to-RGB colour of a white diffuse.
    The cast-shadow part of S_L / S_R is lifted by SHADOW_LIFT (bounce from the pools; R25 does the same): never black shadows."""
    kt = km_tex(nb, uv, KT, True)
    ksep = nb.node('ShaderNodeSeparateColor'); nb.link(kt.outputs['Color'], ksep.inputs[0])
    ssep = nb.node('ShaderNodeSeparateColor'); nb.link(shade_rgb, ssep.inputs[0])
    if normal is None:
        normal = nb.node('ShaderNodeNewGeometry').outputs['Normal']
    def lifted(i, name, k):
        Lb = LVEC[name]; Lbl = (float(Lb[0]), float(-Lb[1]), float(Lb[2]))
        d = nb.vmath('DOT_PRODUCT', normal, Lbl)
        mx = nb.math('MAXIMUM', d.outputs['Value'], 0.0)
        su = nb.math('MULTIPLY', mx.outputs[0], k)
        diff = nb.math('SUBTRACT', su.outputs[0], ssep.outputs[i])
        add = nb.math('MULTIPLY_ADD', diff.outputs[0], SHADOW_LIFT, ssep.outputs[i])
        return add.outputs[0]
    sL = lifted(0, 'L', DL / SIN_L); sR = lifted(1, 'R', DR / SIN_R)
    gL = nb.value(1.0); gR = nb.value(1.0); GAINS.append((gL, gR))
    def term(c_rgb, g, ksock, ssock):
        prod = nb.math('MULTIPLY', ksock, ssock)
        if g is not None: prod = nb.math('MULTIPLY', prod.outputs[0], g.outputs[0])
        return nb.vmath('SCALE', tuple(c_rgb), None, prod.outputs[0])
    tL = term(CL0, gL, ksep.outputs[0], sL)
    tR = term(CR0, gR, ksep.outputs[1], sR)
    tF = term(CF0, None, ksep.outputs[2], ssep.outputs[2])
    a = nb.vmath('ADD', tL.outputs[0], tR.outputs[0]); b = nb.vmath('ADD', a.outputs[0], tF.outputs[0])
    return b.outputs[0]

def white_shade(nb, normal=None):
    dif = nb.node('ShaderNodeBsdfDiffuse'); dif.inputs['Color'].default_value = (1, 1, 1, 1)
    if normal is not None: nb.link(normal, dif.inputs['Normal'])
    s2r = nb.node('ShaderNodeShaderToRGB'); nb.link(dif.outputs[0], s2r.inputs[0])
    return s2r.outputs['Color']

def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
    return m, NB(m), nt.nodes['Material Output']

# ------------------------------------------------------------------ felt / stitched wool material for the pieces
MATS = {}
ROT = {'roof': 35.0, 'roof_tile': 35.0, 'roof_tile_old': 35.0, 'roof_slate': 35.0, 'roof_thatch': 70.0, 'thatch': 70.0, 'slate': 35.0, 'wood': 90.0, 'wood_dark': 90.0,
       'plank': 0.0, 'window': 90.0}

AGE_TINT = np.array(srgb_lin('#8C7A5E')); 
def wool_material(name, rgb_lin, rot_deg=0.0, rough_bump=1.0, rim=0.35, nrm_strength=1.0, scale=2.1, aged=True):
    m, nb, out = new_mat(name)
    tc = nb.node('ShaderNodeTexCoord'); mp = nb.node('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale,) * 3
    mp.inputs['Rotation'].default_value = (0.0, 0.0, math.radians(rot_deg))
    nb.link(tc.outputs['Object'], mp.inputs['Vector'])
    tb = nb.node('ShaderNodeTexImage'); tb.image = WOOL; tb.projection = 'BOX'; tb.projection_blend = 0.3; tb.interpolation = 'Linear'
    nb.link(mp.outputs['Vector'], tb.inputs['Vector'])
    sepc = nb.node('ShaderNodeSeparateColor'); nb.link(tb.outputs['Color'], sepc.inputs[0])
    bu = nb.node('ShaderNodeBump'); bu.inputs['Strength'].default_value = 1.6 * nrm_strength; bu.inputs['Distance'].default_value = 0.020
    nb.link(sepc.outputs[0], bu.inputs['Height'])
    # albedo: palette x per-strand shade x groove ao x dye-lot noise x per-object lot
    shade = nb.node('ShaderNodeMapRange'); shade.inputs['To Min'].default_value = 0.78; shade.inputs['To Max'].default_value = 1.16
    nb.link(sepc.outputs[1], shade.inputs['Value'])
    aoc = nb.node('ShaderNodeMapRange'); aoc.inputs['From Min'].default_value = 0.55; aoc.inputs['To Min'].default_value = 0.62; aoc.inputs['To Max'].default_value = 1.0
    nb.link(sepc.outputs[2], aoc.inputs['Value'])
    nz = nb.node('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 9.0; nz.inputs['Detail'].default_value = 2.0
    nb.link(tc.outputs['Object'], nz.inputs['Vector'])
    nzm = nb.node('ShaderNodeMapRange'); nzm.inputs['To Min'].default_value = 0.93; nzm.inputs['To Max'].default_value = 1.07
    nb.link(nz.outputs['Fac'], nzm.inputs['Value'])
    oi = nb.node('ShaderNodeObjectInfo')
    lot = nb.node('ShaderNodeMapRange'); lot.inputs['To Min'].default_value = 0.93; lot.inputs['To Max'].default_value = 1.07
    nb.link(oi.outputs['Random'], lot.inputs['Value'])
    felt = nb.node('ShaderNodeTexNoise'); felt.inputs['Scale'].default_value = 26.0; felt.inputs['Detail'].default_value = 3.0; felt.inputs['Roughness'].default_value = 0.6
    nb.link(tc.outputs['Object'], felt.inputs['Vector'])
    feltm = nb.node('ShaderNodeMapRange'); feltm.inputs['To Min'].default_value = 0.86; feltm.inputs['To Max'].default_value = 1.10
    nb.link(felt.outputs['Fac'], feltm.inputs['Value'])
    m1 = nb.math('MULTIPLY', shade.outputs[0], aoc.outputs[0]); m2 = nb.math('MULTIPLY', m1.outputs[0], nzm.outputs[0]); m3 = nb.math('MULTIPLY', m2.outputs[0], lot.outputs[0])
    m4 = nb.math('MULTIPLY', m3.outputs[0], feltm.outputs[0])
    base_c = np.array(rgb_lin) * 0.92 * 0.88 + AGE_TINT * 0.12 * 0.88 if aged else np.array(rgb_lin)      # aged wool: a touch warmer / duller than the game's clean palette
    alb = nb.vmath('SCALE', (1.0, 1.0, 1.0) if WHITE else tuple(float(c) for c in base_c), None, m4.outputs[0])
    sh = white_shade(nb, bu.outputs['Normal'])
    uv, geo = board_uv(nb)
    lit = lit_terms(nb, uv, sh, bu.outputs['Normal'])
    col = nb.vmath('MULTIPLY', alb.outputs[0], lit)
    # fuzz: a soft lighter halo toward grazing angles (wool pile catching the candles)
    ndv = nb.vmath('DOT_PRODUCT', bu.outputs['Normal'], geo.outputs['Incoming'])
    fr_ = nb.math('SUBTRACT', 1.0, ndv.outputs['Value'], clamp=True)
    fr3 = nb.math('POWER', fr_.outputs[0], 3.0)
    rimv = nb.math('MULTIPLY', fr3.outputs[0], rim)
    rimc = nb.vmath('MULTIPLY', lit, tuple(min(1.0, c * 1.6 + 0.12) for c in rgb_lin))
    rimc = nb.vmath('SCALE', rimc.outputs[0], None, rimv.outputs[0])
    tot = nb.vmath('ADD', col.outputs[0], rimc.outputs[0])
    em = nb.node('ShaderNodeEmission'); nb.link(tot.outputs[0], em.inputs['Color'])
    nb.link(em.outputs[0], out.inputs['Surface'])
    return m

def outline_material():
    m, nb, out = new_mat('outline')
    em = nb.node('ShaderNodeEmission'); c = srgb_lin('#2B1C10')
    sh = white_shade(nb)
    uv, geo = board_uv(nb)
    lit = lit_terms(nb, uv, sh)
    col = nb.vmath('MULTIPLY', lit, tuple(c))
    nb.link(col.outputs[0], em.inputs['Color'])
    nb.link(em.outputs[0], out.inputs['Surface'])
    m.use_backface_culling = True
    return m
OUTLINE_MAT = outline_material()

# ------------------------------------------------------------------ ground: displaced board mesh with the R25 emission
hlow = np.load(f'{D}/hlow.npy').astype(np.float32)          # mm, board px grid (healed state, low-pass)
hm = np.load(f'{D}/hexmap.npz'); HID = hm['hid'].astype(np.int32); DEDGE = hm['dedge'].astype(np.float32)
STEP_MM = 2.0
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
q = np.stack([vid[:-1, :-1], vid[:-1, 1:], vid[1:, 1:], vid[1:, :-1]], -1).reshape(-1, 4)
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
board.visible_shadow = False        # the coupons' relief is already in the R25 radiance; no shadow-map self-shadowing moire on the cloth
log('board mesh', len(co))

gm, nb, out = new_mat('board')
uvn = nb.node('ShaderNodeUVMap'); uvn.uv_map = 'uv'
def tex(path, nc=False, interp='Linear'):
    t = nb.node('ShaderNodeTexImage'); t.image = img(path, nc); t.interpolation = interp; t.extension = 'EXTEND'
    nb.link(uvn.outputs['UV'], t.inputs['Vector']); return t
tA, tB, tC = tex(f'{D}/radA.exr'), tex(f'{D}/radB.exr'), tex(f'{D}/radC.exr')
tR = tex(f'{E}/reveal.exr', True, 'Closest'); tH = tex(f'{E}/heal.exr', True, 'Closest'); tM = tex(f'{D}/metal.exr', True)
fval = nb.value(0.0); fval.name = 'FRAME'
gt = nb.math('GREATER_THAN'); nb.link(fval.outputs[0], gt.inputs[0]); nb.link(tR.outputs['Color'], gt.inputs[1])        # frame > reveal -> footprint (B)
gh = nb.math('GREATER_THAN'); nb.link(fval.outputs[0], gh.inputs[0]); nb.link(tH.outputs['Color'], gh.inputs[1])         # frame > heal -> healed (C)
mixAB = nb.node('ShaderNodeMix'); mixAB.data_type = 'RGBA'
nb.link(gt.outputs[0], mixAB.inputs['Factor']); nb.link(tA.outputs['Color'], mixAB.inputs[6]); nb.link(tB.outputs['Color'], mixAB.inputs[7])
mixBC = nb.node('ShaderNodeMix'); mixBC.data_type = 'RGBA'
nb.link(gh.outputs[0], mixBC.inputs['Factor']); nb.link(mixAB.outputs[2], mixBC.inputs[6]); nb.link(tC.outputs['Color'], mixBC.inputs[7])
shg = white_shade(nb)
# numerator: the light of this frame (gains, per-frame pools, Eevee shading incl. cast shadows / AO / curvature)
numr = lit_terms(nb, uvn.outputs['UV'], shg)
# denominator: the flat cloth under the base state (both candles at gain 1, base pools): what R25 baked in
k0 = nb.node('ShaderNodeTexImage'); k0.image = KM0; k0.extension = 'EXTEND'; k0.interpolation = 'Linear'; nb.link(uvn.outputs['UV'], k0.inputs['Vector'])
k0s = nb.node('ShaderNodeSeparateColor'); nb.link(k0.outputs['Color'], k0s.inputs[0])
d1 = nb.vmath('SCALE', tuple(CL0 * DL), None, k0s.outputs[0]); d2 = nb.vmath('SCALE', tuple(CR0 * DR), None, k0s.outputs[1]); d3 = nb.vmath('SCALE', tuple(CF0), None, k0s.outputs[2])
dsum = nb.vmath('ADD', nb.vmath('ADD', d1.outputs[0], d2.outputs[0]).outputs[0], d3.outputs[0])
ratio = nb.vmath('DIVIDE', numr, dsum.outputs[0])
kval = nb.value(1.0); kval.name = 'RATIO_K'
mixr = nb.node('ShaderNodeMix'); mixr.data_type = 'VECTOR'; mixr.inputs[4].default_value = (1, 1, 1)
nb.link(kval.outputs[0], mixr.inputs['Factor']); nb.link(ratio.outputs[0], mixr.inputs[5])
mulc = nb.vmath('MULTIPLY', mixBC.outputs[2], mixr.outputs[1])
# travelling glint on the couched gold (KK lobe on the strand tangent vs the half vector of each candle and the view, per pixel)
GLINT = nb.value(0.0); GLINT.name = 'GLINT'
mask = nb.node('ShaderNodeSeparateColor'); nb.link(tM.outputs['Color'], mask.inputs[0])
tvec = nb.node('ShaderNodeCombineXYZ')
tx = nb.math('MULTIPLY_ADD'); tx.inputs[1].default_value = 2.0; tx.inputs[2].default_value = -1.0; nb.link(mask.outputs[1], tx.inputs[0])
ty = nb.math('MULTIPLY_ADD'); ty.inputs[1].default_value = -2.0; ty.inputs[2].default_value = 1.0; nb.link(mask.outputs[2], ty.inputs[0])   # board y(down) -> Blender -y
nb.link(tx.outputs[0], tvec.inputs[0]); nb.link(ty.outputs[0], tvec.inputs[1])
geo_g = nb.node('ShaderNodeNewGeometry')
glint_sum = None
ktg = km_tex(nb, uvn.outputs['UV'], KT, True)
ktgs = nb.node('ShaderNodeSeparateColor'); nb.link(ktg.outputs['Color'], ktgs.inputs[0])
GL_GAINS = []
for i, nm in enumerate('LR'):
    Pc = lm.candle_pos(nm); Pc_b = (Pc[0], -Pc[1], Pc[2])
    toL = nb.vmath('SUBTRACT', tuple(Pc_b), geo_g.outputs['Position'])
    toLn = nb.vmath('NORMALIZE', toL.outputs[0])
    hv = nb.vmath('ADD', toLn.outputs[0], geo_g.outputs['Incoming'])
    hn = nb.vmath('NORMALIZE', hv.outputs[0])
    tdh = nb.vmath('DOT_PRODUCT', tvec.outputs[0], hn.outputs[0])
    t2 = nb.math('MULTIPLY', tdh.outputs['Value'], tdh.outputs['Value'])
    s2 = nb.math('SUBTRACT', 1.0, t2.outputs[0], clamp=True)
    sth = nb.math('SQRT', s2.outputs[0])
    lobe = nb.math('POWER', sth.outputs[0], GLINT_EXP)
    g = nb.value(1.0); GL_GAINS.append(g)
    w = nb.math('MULTIPLY', lobe.outputs[0], ktgs.outputs[i]); w = nb.math('MULTIPLY', w.outputs[0], g.outputs[0])
    w = nb.math('MULTIPLY', w.outputs[0], mask.outputs[0]); w = nb.math('MULTIPLY', w.outputs[0], GLINT.outputs[0])
    gc = nb.vmath('SCALE', tuple((KEYC * (CL0 if i == 0 else CR0).max() / max(1e-6, (CL0 if i == 0 else CR0).max())) * np.array([1.0, 0.84, 0.50]) * 0.55), None, w.outputs[0])
    glint_sum = gc if glint_sum is None else nb.vmath('ADD', glint_sum.outputs[0], gc.outputs[0])
final = nb.vmath('ADD', mulc.outputs[0], glint_sum.outputs[0])
em = nb.node('ShaderNodeEmission')
nb.link(final.outputs[0], em.inputs['Color'])
nb.link(em.outputs[0], out.inputs['Surface'])
board.data.materials.append(gm)
FRAME_NODE = fval

# towns and quarries sit on a flat plateau of the coupon from the first Eevee frame (never a time-dependent 'press': no floor pop)
PLATEAU = []
for _i, _p in enumerate(PIECES):
    if _p.get('skip') or AN['starts'][_i] is None or _p['kind'] not in ('town', 'site'): continue
    bx0, bz0, bx1, bz1 = _p['base']
    j0, j1 = int((bx0 - BX0) * MMU / STEP_MM) - 3, int((bx1 - BX0) * MMU / STEP_MM) + 4
    i0, i1 = int((bz0 - BZ0) * MMU / STEP_MM) - 3, int((bz1 - BZ0) * MMU / STEP_MM) + 4
    ii, jj = np.mgrid[max(i0, 0):min(i1, nz), max(j0, 0):min(j1, nx)]
    xg = BX0 + jj * STEP_MM / MMU; zg = BZ0 + ii * STEP_MM / MMU
    dx = np.maximum(np.maximum(bx0 - xg, xg - bx1), 0) * MMU; dz = np.maximum(np.maximum(bz0 - zg, zg - bz1), 0) * MMU
    wgt = np.clip(1 - np.hypot(dx, dz) / 3.0, 0, 1).astype(np.float32)
    idx = (ii * nx + jj).ravel(); w_ = wgt.ravel()
    inner = w_ > 0.99
    zp = float(np.percentile(V_H[idx][inner], 20)) if inner.any() else 0.0        # fixed plateau level (mm, grown with the relief)
    PLATEAU.append((idx, w_, zp))
V_SW_ARR = np.array(V_SW, np.float32)

def update_ground(f):
    g = anim.growth(f)
    sw = np.array([anim.swell(f, s) for s in HEX_SW], np.float32)[V_HID]
    z_mm = g * V_H + 1.1 * sw * V_DOME * V_LAND
    for idx, w_, zp in PLATEAU:
        z_mm[idx] = z_mm[idx] * (1 - w_) + (g * zp) * w_
    co[:, 2] = z_mm / MMU
    me.vertices.foreach_set('co', co.ravel()); me.update()
    return z_mm

def ground_height(x, zg, z_mm):
    i = int(round((zg - BZ0) * MMU / STEP_MM)); j = int(round((x - BX0) * MMU / STEP_MM))
    i = min(max(i, 0), nz - 1); j = min(max(j, 0), nx - 1)
    return float(z_mm[i * nx + j]) / MMU

# ------------------------------------------------------------------ pieces
MODELS = {m_['name']: m_ for m_ in json.load(open(f'{MOD}/models.json'))}
MESH = {}

def piece_mat(nm, realm):
    k = (nm, realm)
    if k not in MATS:
        hexc = pcol(nm, realm)
        rot = ROT.get(nm, 0.0)
        MATS[k] = wool_material(f'pm_{nm}_{realm}', srgb_lin(hexc), rot_deg=rot, rim=0.18 if nm.startswith('roof') or nm in ('slate', 'metal', 'gold') else 0.38)
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

def scaled_copy(mesh, s):
    me2 = mesh.copy()
    me2.transform(Matrix.Scale(s, 4))
    me2.update()
    return me2

def tree_mesh(sp, rad, ht, seed):
    """stuffed-felt tiered conifer / rounded broadleaf, scale baked (game units), base at z=0, centre at the origin"""
    r = np.random.default_rng(seed)
    bm = bmesh.new()
    trunk_h = 0.10 * ht
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=6, radius1=rad * 0.20, radius2=rad * 0.16, depth=trunk_h * 1.4,
                          matrix=Matrix.Translation((0, 0, trunk_h * 0.7)))
    trunk_faces = [f for f in bm.faces]
    for f in trunk_faces: f.material_index = 1
    if sp in ('spruce', 'fir'):
        n = 5 if sp == 'spruce' else 3
        crown_h = ht - trunk_h
        step = crown_h / (n + 0.45)
        for k in range(n):
            y_a = trunk_h * 0.8 + k * step * 0.95
            wk = rad * (1.0 - 0.62 * k / n) * r.uniform(0.94, 1.06)
            geom = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=10, radius1=wk, radius2=wk * 0.12, depth=step * 1.55,
                                         matrix=Matrix.Translation((r.uniform(-0.01, 0.01), r.uniform(-0.01, 0.01), y_a + step * 0.78)))
            for v in geom['verts']:
                if v.co.z < y_a + step * 0.2:                 # scalloped, drooping skirt
                    ang = math.atan2(v.co.y, v.co.x)
                    v.co.z -= 0.06 * step * (0.5 + 0.5 * math.sin(ang * 3 + k))
                    v.co.x *= 1 + 0.07 * math.sin(ang * 5 + k * 2); v.co.y *= 1 + 0.07 * math.sin(ang * 5 + k * 2)
    else:
        for (ox, oy, oz, rr) in [(-0.35, 0.0, 0.58, 0.62), (0.40, 0.05, 0.54, 0.58), (0.0, -0.05, 0.70, 0.70)]:
            geom = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=rad * rr * 1.3,
                                              matrix=Matrix.Translation((ox * rad, oy * rad, trunk_h + (ht - trunk_h) * oz * 0.9)))
            for v in geom['verts']:
                v.co.z *= 0.86
                v.co += Vector((r.normal(0, 0.012), r.normal(0, 0.012), r.normal(0, 0.01)))
    bm.normal_update()
    me_ = bpy.data.meshes.new(f'tree_{seed}')
    bm.to_mesh(me_); bm.free()
    for p_ in me_.polygons: p_.use_smooth = True
    return me_

TREE_MATS = {}
def tree_mats(sp):
    if sp not in TREE_MATS:
        cd = {'spruce': '#223A2B', 'fir': '#263F2D', 'round': '#3E5530'}[sp]
        cl = {'spruce': '#2A4630', 'fir': '#2F4E34', 'round': '#4A6434'}[sp]
        mc = wool_material(f'tree_{sp}', srgb_lin(cl), rot_deg=75.0, rim=0.30, nrm_strength=1.1)
        mt = wool_material('trunk', srgb_lin('#4A3420'), rot_deg=90.0, rim=0.1)
        TREE_MATS[sp] = (mc, mt)
    return TREE_MATS[sp]

def card_mesh(p):
    nm = p['id']
    w, h = p['w'], p['height']
    me_ = bpy.data.meshes.new(f'card_{nm}')
    me_.from_pydata([(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, h), (-w / 2, 0, h)], [], [(0, 1, 2, 3)])
    uv = me_.uv_layers.new(name='uv'); uv.data.foreach_set('uv', [0, 0, 1, 0, 1, 1, 0, 1])
    m, nb_, out_ = new_mat(f'card_{nm}')
    ta = nb_.node('ShaderNodeTexImage'); ta.image = img(f'{E}/cards/{nm}_alb.png'); ta.interpolation = 'Linear'; ta.extension = 'CLIP'
    tn = nb_.node('ShaderNodeTexImage'); tn.image = img(f'{E}/cards/{nm}_nrm.png', noncolor=True); tn.interpolation = 'Linear'; tn.extension = 'EXTEND'
    nmn = nb_.node('ShaderNodeNormalMap'); nmn.uv_map = 'uv'; nmn.inputs['Strength'].default_value = 1.3
    nb_.link(tn.outputs['Color'], nmn.inputs['Color'])
    sh = white_shade(nb_, nmn.outputs['Normal'])
    uvg, geo = board_uv(nb_)
    lit = lit_terms(nb_, uvg, sh, nmn.outputs['Normal'])
    geo2 = nb_.node('ShaderNodeNewGeometry')
    lin_back = nb_.rgb(srgb_lin('#C9B58E'))
    mx = nb_.node('ShaderNodeMix'); mx.data_type = 'RGBA'
    nb_.link(geo2.outputs['Backfacing'], mx.inputs['Factor']); nb_.link(ta.outputs['Color'], mx.inputs[6]); nb_.link(lin_back.outputs[0], mx.inputs[7])
    col = nb_.vmath('MULTIPLY', mx.outputs[2], lit)
    ndv = nb_.vmath('DOT_PRODUCT', nmn.outputs['Normal'], geo2.outputs['Incoming'])
    fr_ = nb_.math('SUBTRACT', 1.0, ndv.outputs['Value'], clamp=True); fr3 = nb_.math('POWER', fr_.outputs[0], 3.0); rimv = nb_.math('MULTIPLY', fr3.outputs[0], 0.25)
    rimc = nb_.vmath('SCALE', nb_.vmath('MULTIPLY', lit, mx.outputs[2]).outputs[0], None, rimv.outputs[0])
    tot = nb_.vmath('ADD', col.outputs[0], rimc.outputs[0])
    em = nb_.node('ShaderNodeEmission'); nb_.link(tot.outputs[0], em.inputs['Color'])
    tr = nb_.node('ShaderNodeBsdfTransparent'); mxs = nb_.node('ShaderNodeMixShader')
    gtc = nb_.math('GREATER_THAN', ta.outputs['Alpha'], 0.5)
    nb_.link(gtc.outputs[0], mxs.inputs[0]); nb_.link(tr.outputs[0], mxs.inputs[1]); nb_.link(em.outputs[0], mxs.inputs[2])
    nb_.link(mxs.outputs[0], out_.inputs['Surface'])
    m.blend_method = 'CLIP'; m.shadow_method = 'CLIP'; m.alpha_threshold = 0.5
    me_.materials.append(m)
    return me_

TETHER_MATS = {}
def tether_mat(kind):
    if kind not in TETHER_MATS:
        c = {'tree': '#4F6B3A', 'card': '#8A6A40', 'town': '#CDB995', 'site': '#B8A27C', 'banner': '#C8962E', 'lumber': '#8A6A40'}.get(kind, '#6B4A2E')
        TETHER_MATS[kind] = wool_material(f'tether_{kind}', srgb_lin(c), rot_deg=0.0, rim=0.5, nrm_strength=0.6, scale=14.0)
    return TETHER_MATS[kind]

PCS = []
starts = AN['starts']
for i, p in enumerate(PIECES):
    if NOPIECES or p.get('skip') or starts[i] is None: continue
    piv = bpy.data.objects.new(f'piv_{p["id"]}', None); sc.collection.objects.link(piv)
    scl = bpy.data.objects.new(f'scl_{p["id"]}', None); sc.collection.objects.link(scl); scl.parent = piv
    piv.location = (p['x'], -p['z_back'], 0.0)
    th = None
    if p['kind'] in ('town', 'site', 'lumber', 'banner'):
        mesh, n0 = load_model(p['model'], p.get('realm') or 'gold')
        me2 = scaled_copy(mesh, p['scale'])
        ob = bpy.data.objects.new(p['id'], me2); sc.collection.objects.link(ob); ob.parent = scl
        ob.location = (0, -(p['z'] - p['z_back']), 0)
        th = 0.0045 if p['kind'] == 'town' else 0.003
        bev = ob.modifiers.new('bevel', 'BEVEL'); bev.width = 0.013 if p['kind'] == 'town' else 0.009; bev.segments = 2; bev.limit_method = 'ANGLE'
        bev.angle_limit = math.radians(40); bev.harden_normals = False
    elif p['kind'] == 'tree':
        me2 = tree_mesh(p['sp'], p['rad'], p['height'], p['seed'])
        mc, mt = tree_mats(p['sp'])
        me2.materials.append(mc); me2.materials.append(mt)
        n0 = 2
        me2.materials.append(OUTLINE_MAT)
        ob = bpy.data.objects.new(p['id'], me2); sc.collection.objects.link(ob); ob.parent = scl
        r_ = np.random.default_rng(p['seed'])
        ob.location = (0, -p['rad'], 0)
        ob.rotation_euler = (math.radians(r_.normal(0, 2.5)), math.radians(r_.normal(0, 2.5)), r_.uniform(0, 6.28))
        th = 0.0030
    else:
        me2 = card_mesh(p)
        ob = bpy.data.objects.new(p['id'], me2); sc.collection.objects.link(ob); ob.parent = scl
        n0 = 1
    if th:
        mod = ob.modifiers.new('outline', 'SOLIDIFY'); mod.thickness = th; mod.offset = 1.0
        mod.use_flip_normals = True; mod.material_offset = n0; mod.use_rim = False
    cu = bpy.data.curves.new(f'teth_{p["id"]}', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.0155; cu.bevel_resolution = 2
    cu.materials.append(tether_mat(p['kind']))
    tob = bpy.data.objects.new(f'teth_{p["id"]}', cu); sc.collection.objects.link(tob)
    PCS.append(dict(p=p, i=i, piv=piv, scl=scl, ob=ob, teth=tob, cu=cu, start=starts[i], T=AN['tethers'].get(p['id'])))
log('pieces', len(PCS))

def face_point(pc, xl, yl, ang, sy, hs):
    """world (BU) of a point on the piece's front face (face-local x, height y) for hinge angle ang (deg from upright)"""
    p = pc['p']
    depth = (p['base'][3] - p['base'][1]) * sy if p['kind'] not in ('card',) else 0.0
    if p['kind'] == 'tree': depth = 2 * p['rad'] * sy
    a = -math.radians(ang)
    y0, z0 = -depth, yl * hs
    y1 = y0 * math.cos(a) - z0 * math.sin(a); z1 = y0 * math.sin(a) + z0 * math.cos(a)
    P0 = pc['piv'].location
    return Vector((P0.x + xl, P0.y + y1, P0.z + z1))

def update_pieces(f, z_mm):
    for pc in PCS:
        p = pc['p']; st = pc['start']
        ang = anim.hinge_angle(p, st, f)
        vis = ang is not None
        pc['ob'].hide_render = not vis
        bx0, bz0, bx1, bz1 = p['base']
        hs_ = [ground_height(bx0 + (bx1 - bx0) * u_, bz0 + (bz1 - bz0) * v_, z_mm) for u_ in (0.1, 0.5, 0.9) for v_ in (0.1, 0.5, 0.9)]
        pc['piv'].location.z = float(np.percentile(hs_, 60)) + 0.002
        cu = pc['cu']; cu.splines.clear()
        if not vis:
            pc['teth'].hide_render = True
            continue
        sy = anim.depth_scale(ang) if p['kind'] != 'card' else 1.0
        hsc = anim.height_scale(ang, p['k'])
        if ang < 0 and p['kind'] not in ('card',):      # overshoot leans the piece back: lift the pivot so its front edge stays on the cloth
            depth_ = (p['base'][3] - p['base'][1]) * sy if p['kind'] != 'tree' else 2 * p['rad'] * sy
            pc['piv'].location.z += depth_ * math.sin(math.radians(-ang)) + 0.002
        pc['scl'].scale = (1, max(sy, 0.02), hsc)
        pc['piv'].rotation_euler = (-math.radians(ang), 0, 0)
        T = pc['T']; pc['teth'].hide_render = T is None
        if T is None: continue
        ft = anim.twos(f)
        for k, ((xl, yl), sf) in enumerate(zip(T['pts'], T['snap'])):
            hole = face_point(pc, xl, yl, 90.0, 0.0, p['k']); hole.z = ground_height(hole.x, -hole.y, z_mm) + 0.004
            anc = face_point(pc, xl, yl, ang, sy, hsc)
            rr = np.random.default_rng(pc['i'] * 100 + k)
            if ft < sf:
                # taut thread, catenary sag that closes as the piece lifts
                pts = []
                d = anc - hole; L_ = d.length
                slack = max(0.0, 1 - (ft - st) / max(1, sf - st))
                lat = Vector((-d.y, d.x, 0)).normalized() * (rr.normal(0, 0.02) * L_) if L_ > 1e-4 else Vector((0, 0, 0))
                for t in np.linspace(0, 1, 7):
                    sag = 0.14 * L_ * math.sin(math.pi * t) * (0.10 + 0.90 * slack)
                    pts.append(hole + d * t + lat * math.sin(math.pi * t) * (0.4 + slack) + Vector((0, 0, -sag)))
            else:
                age = ft - sf
                if age > 8: continue
                # snapped: the cloth end whips back and curls into its hole (the snipped end that stays is part of the footprint), the piece end falls away
                l1 = (0.05 + 0.03 * rr.random()) * max(0.0, 1 - age / 7.0)
                ang0 = rr.uniform(0, 2 * math.pi)
                curl = min(1.0, age / 3.0)
                pts = []
                for t in np.linspace(0, 1, 5):
                    a_ = ang0 + curl * 2.6 * t
                    pts.append(hole + Vector((math.cos(a_) * l1 * t, math.sin(a_) * l1 * t, 0.006 + (1 - curl) * 0.025 * t)))
                if l1 > 0.004:
                    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
                    for j_, v in enumerate(pts): sp.points[j_].co = (v.x, v.y, v.z, 1)
                l2 = (0.05 + 0.03 * rr.random()) * max(0.0, 1 - age / 8.0)
                swing = math.sin(age * 1.4 + k) * math.exp(-age / 5.0) * 0.7
                pts = [anc, anc + Vector((math.sin(swing) * l2 * 0.5, -l2 * 0.35, -l2 * math.cos(swing) * 0.9))]
                pts = [pts[0], pts[0] * 0.5 + pts[1] * 0.5 + Vector((0, 0, 0.003)), pts[1]]
                if l2 < 0.004: continue
            sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
            for j_, v in enumerate(pts): sp.points[j_].co = (v.x, v.y, v.z, 1)

# ------------------------------------------------------------------ per-frame light state
def set_light_state(f):
    gL = lm.gain('L', f); gR = lm.gain('R', f)
    if lm.NEUTRAL: gL = gR = 1.0
    for a_, b_ in GAINS:
        a_.outputs[0].default_value = gL; b_.outputs[0].default_value = gR
    # per-frame pool maps (pools widen slightly with the swell); the ground's flat reference keeps the base pools
    kL, kR, kF = lm.kmaps((H // 4, W // 4), 0, 0, 4, f)
    kF = lm.fill_map(kL, kR, gL, gR)
    arr = np.dstack([kL, kR, kF, np.ones_like(kL)])[::-1].astype(np.float32)           # Blender images are bottom-up
    KT.pixels.foreach_set(arr.ravel()); KT.update()
    # glint: ramps in with the crane, narrow KK lobe, per-candle gain follows the candles
    s = crane_s(f)
    ramp = float(min(1.0, max(0.0, (s - 0.03) / 0.18)))
    GLINT.outputs[0].default_value = 0.0 if NOGLINT else GLINT_AMP * ramp
    GL_GAINS[0].outputs[0].default_value = gL; GL_GAINS[1].outputs[0].default_value = gR
    return gL, gR

# ------------------------------------------------------------------ render loop
if arg('--save'):
    bpy.ops.wm.save_as_mainfile(filepath=arg('--save'))
for f in FRAMES:
    t = time.time()
    set_camera(f)
    z_mm = update_ground(f)
    FRAME_NODE.outputs[0].default_value = float(anim.twos(f)) + 0.5
    update_pieces(f, z_mm)
    gL, gR = set_light_state(f)
    sc.frame_set(f)
    sc.render.filepath = f'{OUTD}/f{f:04d}.exr'
    bpy.ops.render.render(write_still=True)
    log('frame', f, '%.1fs' % (time.time() - t), 'gL %.3f gR %.3f' % (gL, gR))
log('done')
