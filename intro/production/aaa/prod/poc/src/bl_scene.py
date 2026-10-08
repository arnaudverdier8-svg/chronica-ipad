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
import bpy, bmesh, sys, os, json, math, time, zlib
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
NOFUZZ = '--nofuzz' in argv or os.environ.get('NOFUZZ') == '1'
WHITE = '--whitepieces' in argv
CLOSE = arg('--closeup', 3, None)
BORDER = arg('--border', 4, None)
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
FILL_NODES = []     # vector-SCALE nodes of the fill term of every lit material: colour x gain set per frame (S24 light state D: the fill turns neutral-warm and rises)
KT_IMGS = []        # TexImage nodes of the per-frame pool map

bpy.ops.wm.read_factory_settings(use_empty=True)
try:
    bpy.context.preferences.system.use_mipmaps = True; bpy.context.preferences.system.anisotropic_filter = 'FILTER_16'     # v3: background mode ran without texture filtering: the 512 px wool tile aliased into speckle
except Exception as _e: print('prefs', _e)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
ee = sc.eevee
ee.taa_render_samples = TAA
ee.use_gtao = True; ee.gtao_distance = 0.09; ee.gtao_factor = 0.9
ee.use_soft_shadows = os.environ.get('SOFT', '1') == '1'; ee.shadow_cascade_size = '4096'; ee.shadow_cube_size = '1024'; ee.use_shadow_high_bitdepth = True
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
if BORDER:
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_min_y, sc.render.border_max_x, sc.render.border_max_y = [float(v) for v in BORDER]
if os.environ.get('NOGTAO') == '1': ee.use_gtao = False

# ------------------------------------------------------------------ world (fill carried in the B channel) and the two coloured suns
world = bpy.data.worlds.new('fill'); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs['Color'].default_value = (0.0, 0.0, 1.0, 1); bg.inputs['Strength'].default_value = 1.0

def bl_dir(Lb):            # board (x right, y down, z up) -> Blender (x, -y, z)
    return Vector((Lb[0], -Lb[1], Lb[2])).normalized()

def sun(name, Lb, color, strength, angle_deg):
    ld = bpy.data.lights.new(name, 'SUN'); ld.color = color; ld.energy = strength
    ld.angle = math.radians(angle_deg); ld.use_shadow = os.environ.get('NOSHADOW') != '1'
    ld.use_contact_shadow = False           # v3: the screen-space contact shadow made black speckle on grazing wall faces; contact darkening comes from the AO map
    ld.contact_shadow_distance = 0.08; ld.contact_shadow_thickness = 0.012; ld.contact_shadow_bias = 0.01
    ld.shadow_cascade_count = 4; ld.shadow_cascade_max_distance = 40.0; ld.shadow_cascade_exponent = 0.75
    ld.shadow_cascade_fade = 0.1; ld.shadow_buffer_bias = float(os.environ.get('SBIAS', '1.0'))
    ob = bpy.data.objects.new(name, ld); sc.collection.objects.link(ob)
    ob.rotation_euler = bl_dir(Lb).to_track_quat('Z', 'Y').to_euler()
    return ob
LTAB = lm.light_table()
SANG = float(os.environ.get('SANG', '8.0'))
sun('candleL', LTAB['candles']['L']['L_board'], (1.0, 0.0, 0.0), math.pi * DL / SIN_L, SANG)
sun('candleR', LTAB['candles']['R']['L_board'], (0.0, 1.0, 0.0), math.pi * DR / SIN_R, SANG)

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
AOI = bpy.data.images.new('AOI_contact', int(_kz[1]), int(_kz[0]), alpha=True, float_buffer=True)   # per-frame contact occlusion under the risen pieces (R)
AOI.colorspace_settings.name = 'Non-Color'
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
GLINT_EXP = 55.0        # v3: Kajiya-Kay lobe (about +-12 deg): only strands nearly perpendicular to the half vector glint; as the crane turns H (and the candles' H varies across the board) the glint travels along the borders
GLINT_AMP = 12.0        # v3: hot enough to read (peak ~235-245 after the grade) but a narrow band, no bloom, no flare (light level L1)
GLINT_W = 3.2           # board units: width of the travelling band the glint is gated by
GLINT_DIR = (math.cos(math.radians(28)), math.sin(math.radians(28)))   # sweep direction (Blender xy): west -> east, a little toward the camera
LVEC = {n_: lm.lvec(lm.CANDLE[n_]['az'], lm.CANDLE[n_]['el']) for n_ in 'LR'}

def lit_terms(nb, uv, shade_rgb, normal=None, noshadow=False):
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
        return su.outputs[0] if noshadow else add.outputs[0]
    sL = lifted(0, 'L', DL / SIN_L); sR = lifted(1, 'R', DR / SIN_R)
    gL = nb.value(1.0); gR = nb.value(1.0); GAINS.append((gL, gR))
    def term(c_rgb, g, ksock, ssock):
        prod = nb.math('MULTIPLY', ksock, ssock)
        if g is not None: prod = nb.math('MULTIPLY', prod.outputs[0], g.outputs[0])
        return nb.vmath('SCALE', tuple(c_rgb), None, prod.outputs[0])
    tL = term(CL0, gL, ksep.outputs[0], sL)
    tR = term(CR0, gR, ksep.outputs[1], sR)
    tF = term(CF0, None, ksep.outputs[2], (nb.value(1.0).outputs[0] if noshadow else ssep.outputs[2])); FILL_NODES.append(tF)
    a = nb.vmath('ADD', tL.outputs[0], tR.outputs[0]); b = nb.vmath('ADD', a.outputs[0], tF.outputs[0])
    return b.outputs[0]

def white_shade(nb, normal=None):
    dif = nb.node('ShaderNodeBsdfDiffuse'); dif.inputs['Color'].default_value = (1, 1, 1, 1)
    if normal is not None: nb.link(normal, dif.inputs['Normal'])
    s2r = nb.node('ShaderNodeShaderToRGB'); nb.link(dif.outputs[0], s2r.inputs[0])
    return s2r.outputs['Color']

def fade_node(nb):
    """per-object 'fade' (custom property, 0..1): the piece dissolves in over its first frames (v3: no one-frame swap of the stitched icon for the felt model)"""
    at = nb.node('ShaderNodeAttribute'); at.attribute_type = 'OBJECT'; at.attribute_name = 'fade'
    return at.outputs['Fac']

def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
    return m, NB(m), nt.nodes['Material Output']

# ------------------------------------------------------------------ felt / stitched wool material for the pieces (v3)
MATS = {}
MATDEBUG = os.environ.get('MATDEBUG') == '1'        # look-dev: every material name in its own flat colour
ROT = {'roof': 35.0, 'roof_tile': 35.0, 'roof_tile_old': 35.0, 'roof_slate': 35.0, 'roof_thatch': 70.0, 'thatch': 70.0, 'slate': 35.0, 'wood': 90.0, 'wood_dark': 90.0,
       'plank': 0.0, 'window': 90.0}

AGE_TINT = np.array(srgb_lin('#8C7A5E'))
FUZZ_AMP = 0.85
FUZZ_TH = 0.014          # fibre halo shell: 0.4 mm of wool pile around every piece (soft silhouette against the satin)
def wool_material(name, rgb_lin, rot_deg=0.0, rough_bump=1.0, rim=0.22, nrm_strength=1.0, scale=float(os.environ.get('WSCALE', '1.0')), aged=True, fuzz=False, lot_amp=0.09, stripe=1.0):
    """felt / laid-wool surface lit by the shared candle rig.  v3: macro dye-lot patches (+-14 %), per-object lot, per-strand shade, groove AO, a low
    fuzz rim and (fuzz=True) the fibre-halo variant: the same colour, alpha = a fibre noise, hashed blend, used on an inflated shell."""
    m, nb, out = new_mat(name + ('_fz' if fuzz else ''))
    if MATDEBUG:
        h_ = (zlib.crc32(name.encode()) % 997) / 997.0
        em = nb.node('ShaderNodeEmission'); em.inputs['Color'].default_value = (0.2 + 0.8 * abs(math.sin(h_ * 40)), 0.2 + 0.8 * abs(math.sin(h_ * 91 + 1)), 0.2 + 0.8 * abs(math.sin(h_ * 17 + 2)), 1)
        nb.link(em.outputs[0], out.inputs['Surface'])
        return m
    tc = nb.node('ShaderNodeTexCoord'); mp = nb.node('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale,) * 3
    mp.inputs['Rotation'].default_value = (0.0, 0.0, math.radians(rot_deg))
    nb.link(tc.outputs['Object'], mp.inputs['Vector'])
    tb = nb.node('ShaderNodeTexImage'); tb.image = WOOL; tb.projection = 'BOX'; tb.projection_blend = 0.3; tb.interpolation = 'Linear'
    nb.link(mp.outputs['Vector'], tb.inputs['Vector'])
    sepc = nb.node('ShaderNodeSeparateColor'); nb.link(tb.outputs['Color'], sepc.inputs[0])
    bu = nb.node('ShaderNodeBump'); bu.inputs['Strength'].default_value = float(os.environ.get('WB_S', '2.4')) * nrm_strength; bu.inputs['Distance'].default_value = float(os.environ.get('WB_D', '0.03'))
    nb.link(sepc.outputs[0], bu.inputs['Height'])
    # felt: a second, finer lumpy bump on top (fibre mat), so the faces are never smooth CG gradients
    fb = nb.node('ShaderNodeTexNoise'); fb.inputs['Scale'].default_value = 14.0; fb.inputs['Detail'].default_value = 1.5; fb.inputs['Roughness'].default_value = 0.55
    nb.link(tc.outputs['Object'], fb.inputs['Vector'])
    bu2 = nb.node('ShaderNodeBump'); bu2.inputs['Strength'].default_value = float(os.environ.get('WB2_S', '0.22')) * nrm_strength; bu2.inputs['Distance'].default_value = 0.012
    nb.link(fb.outputs['Fac'], bu2.inputs['Height']); nb.link(bu.outputs['Normal'], bu2.inputs['Normal'])
    NRM = bu2.outputs['Normal']
    if os.environ.get('NOBUMP') == '1': NRM = nb.node('ShaderNodeNewGeometry').outputs['Normal']
    shade = nb.node('ShaderNodeMapRange'); shade.inputs['To Min'].default_value = 1.0 - 0.20 * stripe; shade.inputs['To Max'].default_value = 1.0 + 0.14 * stripe
    nb.link(sepc.outputs[1], shade.inputs['Value'])
    aoc = nb.node('ShaderNodeMapRange'); aoc.inputs['From Min'].default_value = 0.55; aoc.inputs['To Min'].default_value = 1.0 - 0.26 * stripe; aoc.inputs['To Max'].default_value = 1.0
    nb.link(sepc.outputs[2], aoc.inputs['Value'])
    nz = nb.node('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 4.2; nz.inputs['Detail'].default_value = 3.0           # dye-lot patches
    nb.link(tc.outputs['Object'], nz.inputs['Vector'])
    nzm = nb.node('ShaderNodeMapRange'); nzm.inputs['To Min'].default_value = 0.86; nzm.inputs['To Max'].default_value = 1.14
    nb.link(nz.outputs['Fac'], nzm.inputs['Value'])
    oi = nb.node('ShaderNodeObjectInfo')
    lot = nb.node('ShaderNodeMapRange'); lot.inputs['To Min'].default_value = 1 - lot_amp; lot.inputs['To Max'].default_value = 1 + lot_amp
    nb.link(oi.outputs['Random'], lot.inputs['Value'])
    felt = nb.node('ShaderNodeTexNoise'); felt.inputs['Scale'].default_value = 16.0; felt.inputs['Detail'].default_value = 1.5; felt.inputs['Roughness'].default_value = 0.55
    nb.link(tc.outputs['Object'], felt.inputs['Vector'])
    feltm = nb.node('ShaderNodeMapRange'); feltm.inputs['To Min'].default_value = 0.88; feltm.inputs['To Max'].default_value = 1.10
    nb.link(felt.outputs['Fac'], feltm.inputs['Value'])
    m1 = nb.math('MULTIPLY', shade.outputs[0], aoc.outputs[0]); m2 = nb.math('MULTIPLY', m1.outputs[0], nzm.outputs[0]); m3 = nb.math('MULTIPLY', m2.outputs[0], lot.outputs[0])
    m4 = nb.math('MULTIPLY', m3.outputs[0], feltm.outputs[0])
    base_c = np.array(rgb_lin) * 0.92 * 0.88 + AGE_TINT * 0.12 * 0.88 if aged else np.array(rgb_lin)
    alb = nb.vmath('SCALE', (1.0, 1.0, 1.0) if WHITE else tuple(float(c) for c in base_c), None, m4.outputs[0])
    sh = white_shade(nb, NRM)
    uv, geo = board_uv(nb)
    lit = lit_terms(nb, uv, sh, NRM, noshadow=fuzz)         # the fuzz shell must not receive the shadow of the mesh it clothes (acne = the black speckle of v3 test renders)
    col = nb.vmath('MULTIPLY', alb.outputs[0], lit)
    ndv = nb.vmath('DOT_PRODUCT', NRM, geo.outputs['Incoming'])
    fr_ = nb.math('SUBTRACT', 1.0, ndv.outputs['Value'], clamp=True)
    fr3 = nb.math('POWER', fr_.outputs[0], 3.0)
    rimv = nb.math('MULTIPLY', fr3.outputs[0], rim)
    rimc = nb.vmath('MULTIPLY', lit, tuple(min(1.0, c * 1.6 + 0.12) for c in rgb_lin))
    rimc = nb.vmath('SCALE', rimc.outputs[0], None, rimv.outputs[0])
    tot = nb.vmath('ADD', col.outputs[0], rimc.outputs[0])
    _dbg = os.environ.get('WDBG')
    if _dbg == 'alb': tot = nb.vmath('SCALE', alb.outputs[0], None, nb.value(0.5).outputs[0])
    elif _dbg == 'lit': tot = nb.vmath('SCALE', lit, None, nb.value(0.3).outputs[0])
    em = nb.node('ShaderNodeEmission'); nb.link(tot.outputs[0], em.inputs['Color'])
    fd = fade_node(nb)
    if not fuzz:
        tr0 = nb.node('ShaderNodeBsdfTransparent'); mx0 = nb.node('ShaderNodeMixShader')
        nb.link(fd, mx0.inputs[0]); nb.link(tr0.outputs[0], mx0.inputs[1]); nb.link(em.outputs[0], mx0.inputs[2])
        nb.link(mx0.outputs[0], out.inputs['Surface'])
        m.blend_method = 'HASHED'; m.shadow_method = 'OPAQUE'
        return m
    # fibre halo: soft patchy fibre noise as hashed alpha, only toward grazing view angles (the pile seen edge-on), so face-on surfaces carry no shell speckle
    fn = nb.node('ShaderNodeTexNoise'); fn.inputs['Scale'].default_value = 34.0; fn.inputs['Detail'].default_value = 0.0
    nb.link(tc.outputs['Object'], fn.inputs['Vector'])
    fm = nb.node('ShaderNodeMapRange'); fm.inputs['From Min'].default_value = 0.30; fm.inputs['From Max'].default_value = 0.70; fm.inputs['To Max'].default_value = 1.0
    nb.link(fn.outputs['Fac'], fm.inputs['Value'])
    ndv_f = nb.vmath('DOT_PRODUCT', geo.outputs['Normal'], geo.outputs['Incoming'])
    gz_ = nb.math('SUBTRACT', 1.0, ndv_f.outputs['Value'], clamp=True)
    gz2 = nb.math('POWER', gz_.outputs[0], 1.6)
    fa0 = nb.math('MULTIPLY', fm.outputs[0], gz2.outputs[0])
    fa1 = nb.math('MULTIPLY', fa0.outputs[0], FUZZ_AMP)
    fa = nb.math('MULTIPLY', fa1.outputs[0], fd)
    tr = nb.node('ShaderNodeBsdfTransparent'); mx = nb.node('ShaderNodeMixShader')
    nb.link(fa.outputs[0], mx.inputs[0]); nb.link(tr.outputs[0], mx.inputs[1]); nb.link(em.outputs[0], mx.inputs[2])
    nb.link(mx.outputs[0], out.inputs['Surface'])
    m.blend_method = 'HASHED'; m.shadow_method = 'NONE'
    return m

def outline_material():
    m, nb, out = new_mat('outline')
    em = nb.node('ShaderNodeEmission'); c = srgb_lin('#2B1C10')
    sh = white_shade(nb)
    uv, geo = board_uv(nb)
    lit = lit_terms(nb, uv, sh)
    col = nb.vmath('MULTIPLY', lit, tuple(c))
    nb.link(col.outputs[0], em.inputs['Color'])
    tr0 = nb.node('ShaderNodeBsdfTransparent'); mx0 = nb.node('ShaderNodeMixShader')
    nb.link(fade_node(nb), mx0.inputs[0]); nb.link(tr0.outputs[0], mx0.inputs[1]); nb.link(em.outputs[0], mx0.inputs[2])
    nb.link(mx0.outputs[0], out.inputs['Surface'])
    m.use_backface_culling = True
    m.blend_method = 'HASHED'; m.shadow_method = 'NONE'
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
gts = nb.math('SUBTRACT'); nb.link(fval.outputs[0], gts.inputs[0]); nb.link(tR.outputs['Color'], gts.inputs[1])
gt = nb.math('MULTIPLY_ADD', gts.outputs[0], 1.0 / 3.0, 0.5, clamp=True)        # v3: the stitched icon fades into the footprint (B) over ~3 frames around the reveal, crossfading with the piece fading in
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
aot = nb.node('ShaderNodeTexImage'); aot.image = AOI; aot.extension = 'EXTEND'; aot.interpolation = 'Linear'; nb.link(uvn.outputs['UV'], aot.inputs['Vector'])
aos = nb.node('ShaderNodeSeparateColor'); nb.link(aot.outputs['Color'], aos.inputs[0])
aof = nb.math('MULTIPLY_ADD', aos.outputs[0], -0.55, 1.0)
mulc = nb.vmath('SCALE', mulc.outputs[0], None, aof.outputs[0])          # contact occlusion where a risen piece meets the cloth
# travelling glint on the couched gold (KK lobe on the strand tangent vs the half vector of each candle and the view, per pixel)
GLINT = nb.value(0.0); GLINT.name = 'GLINT'
mask = nb.node('ShaderNodeSeparateColor'); nb.link(tM.outputs['Color'], mask.inputs[0])
tvec = nb.node('ShaderNodeCombineXYZ')
tx = nb.math('MULTIPLY_ADD'); tx.inputs[1].default_value = 2.0; tx.inputs[2].default_value = -1.0; nb.link(mask.outputs[1], tx.inputs[0])
ty = nb.math('MULTIPLY_ADD'); ty.inputs[1].default_value = -2.0; ty.inputs[2].default_value = 1.0; nb.link(mask.outputs[2], ty.inputs[0])   # board y(down) -> Blender -y
nb.link(tx.outputs[0], tvec.inputs[0]); nb.link(ty.outputs[0], tvec.inputs[1])
geo_g = nb.node('ShaderNodeNewGeometry')
glint_sum = None
# travelling band: exp(-((s - s0)/w)^2), s = position . sweep direction (set per frame: s0)
gpos = nb.node('ShaderNodeSeparateXYZ'); nb.link(geo_g.outputs['Position'], gpos.inputs[0])
gsx = nb.math('MULTIPLY', gpos.outputs['X'], GLINT_DIR[0]); gsy = nb.math('MULTIPLY', gpos.outputs['Y'], GLINT_DIR[1])
gsp = nb.math('ADD', gsx.outputs[0], gsy.outputs[0])
GL_S0 = nb.value(-20.0)
gdf = nb.math('SUBTRACT', gsp.outputs[0], GL_S0.outputs[0]); gar = nb.math('DIVIDE', gdf.outputs[0], GLINT_W)
gsq = nb.math('MULTIPLY', gar.outputs[0], gar.outputs[0]); gng = nb.math('MULTIPLY', gsq.outputs[0], -1.0)
gband = nb.math('EXPONENT', gng.outputs[0]); gbw = nb.math('MULTIPLY_ADD', gband.outputs[0], 0.86, 0.14)
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
    w = nb.math('MULTIPLY', w.outputs[0], mask.outputs[0]); w = nb.math('MULTIPLY', w.outputs[0], GLINT.outputs[0]); w = nb.math('MULTIPLY', w.outputs[0], gbw.outputs[0])
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

# v3 felt palette: the game's piece colours pulled toward dyed wool (the white-plaster / candy-orange CG look of v2 is gone):
# walls are linen / oatmeal felt, roofs dusty madder and weathered slate, wood dull.  (sRGB hex; names not listed fall back to piece_palette)
FELT = {'plaster': '#C9BC9E', 'white': '#CFC3A8', 'wool': '#CFC3A8', 'stone': '#B2A78F', 'stone_dark': '#7B715F', 'cloth': '#A18D69', 'cloth_dark': '#4A4033',
        'roof': '#A25C40', 'roof_civic': '#9C5A42', 'roof_tile': '#A55E43', 'roof_tile_old': '#6A4034', 'roof_slate': '#4E5965', 'slate': '#364E66', 'slate_civic': '#34506C', 'rock': '#857A67', 'roof_lead': '#6F7677',
        'roof_thatch': '#AA8C58', 'roof_thatch_old': '#8C7A58', 'roof_shingle': '#645546', 'roof_moss': '#66694C', 'thatch': '#A68A56',
        'wood': '#68503A', 'wood_dark': '#43301E', 'plank': '#8E7752', 'window': '#2F2418', 'metal': '#9D9B90', 'gold': '#B08F46', 'lead': '#6F7677'}
FELT_ROUGH = {'roof': 0.14, 'roof_civic': 0.14, 'roof_tile': 0.14, 'roof_tile_old': 0.14, 'roof_slate': 0.12, 'slate': 0.12, 'metal': 0.12, 'gold': 0.14}
def felt_col(nm, realm):
    if nm in ('team', 'blazon', 'team_dark'): return pcol(nm, realm)
    return FELT.get(nm) or pcol(nm, realm)

def piece_mat(nm, realm, fuzz=False):
    k = (nm, realm, fuzz)
    if k not in MATS:
        rot = ROT.get(nm, 0.0)
        MATS[k] = wool_material(f'pm_{nm}_{realm}', srgb_lin(felt_col(nm, realm)), rot_deg=rot, rim=FELT_ROUGH.get(nm, 0.30), fuzz=fuzz)
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
    names = []
    for i, s_ in enumerate(o.material_slots):
        base = s_.material.name.split('.')[0] if s_.material else 'stone'
        if base == 'stone' and name in ('quarry', 'site'): base = 'rock'
        if base == 'roof_civic' and name == 'settle_3': base = 'slate_civic'        # Grandbois: blue slate spires as in the menu
        names.append(base)
        mesh.materials[i] = piece_mat(base, realm)
    n0 = len(mesh.materials)
    mesh.materials.append(OUTLINE_MAT)
    bpy.data.objects.remove(o)
    MESH[k] = (mesh, n0, names)
    return MESH[k]

def scaled_copy(mesh, s):
    me2 = mesh.copy()
    me2.transform(Matrix.Scale(s, 4))
    me2.update()
    return me2

def tree_mesh(sp, rad, ht, seed):
    """stuffed-felt conifer / broadleaf thicket, scale baked (game units), base at z=0.  v3: irregular tier radii, tilted and off-centre tiers, scalloped drooping
    skirts with per-vertex noise (no lathe-turned cones); broadleaf = a cluster of 5-7 lumpy flattened lobes (no cabbage balls)"""
    r = np.random.default_rng(seed)
    bm = bmesh.new()
    trunk_h = 0.10 * ht
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=6, radius1=rad * 0.20, radius2=rad * 0.15, depth=trunk_h * 1.4,
                          matrix=Matrix.Translation((0, 0, trunk_h * 0.7)))
    for f in list(bm.faces): f.material_index = 1
    if sp in ('spruce', 'fir'):
        n = int(r.integers(5, 8)) if sp == 'spruce' else int(r.integers(3, 5))
        crown_h = ht - trunk_h
        step = crown_h / (n + 0.45)
        cx = cy = 0.0
        lobes = int(r.integers(5, 9)); ph0 = r.uniform(0, 6.28)
        for k in range(n):
            y_a = trunk_h * 0.8 + k * step * 0.95 * r.uniform(0.93, 1.07)
            wk = rad * (1.0 - 0.62 * k / n) * r.uniform(0.80, 1.18)
            cx += r.normal(0, 0.010); cy += r.normal(0, 0.010)
            seg = int(r.integers(9, 13))
            geom = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=wk, radius2=wk * r.uniform(0.08, 0.2), depth=step * r.uniform(1.4, 1.8),
                                         matrix=Matrix.Translation((0, 0, step * 0.78)))
            tilt = Matrix.Rotation(r.normal(0, 0.07), 4, 'X') @ Matrix.Rotation(r.normal(0, 0.07), 4, 'Y')
            for v in geom['verts']:
                low = v.co.z < step * 0.2 + 0.0
                if low:                                              # scalloped, drooping, irregular skirt
                    ang = math.atan2(v.co.y, v.co.x)
                    sc_ = 1 + 0.14 * math.sin(ang * lobes + ph0 + k * 1.3) + r.normal(0, 0.05)
                    v.co.x *= sc_; v.co.y *= sc_
                    v.co.z -= 0.08 * step * (0.5 + 0.5 * math.sin(ang * 3 + k)) + abs(r.normal(0, 0.012))
                v.co = tilt @ v.co
                v.co += Vector((cx, cy, y_a))
    else:
        nl = int(r.integers(5, 8))
        for _ in range(nl):
            ox, oy = r.uniform(-0.75, 0.75), r.uniform(-0.45, 0.45)
            oz = r.uniform(0.40, 0.88); rr = r.uniform(0.40, 0.72)
            geom = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=rad * rr * 1.3,
                                              matrix=Matrix.Translation((ox * rad, oy * rad, trunk_h + (ht - trunk_h) * oz * 0.9)))
            for v in geom['verts']:
                v.co.z *= r.uniform(0.70, 0.9)
                v.co += Vector((r.normal(0, 0.016), r.normal(0, 0.016), r.normal(0, 0.012)))
    bm.normal_update()
    me_ = bpy.data.meshes.new(f'tree_{seed}')
    bm.to_mesh(me_); bm.free()
    for p_ in me_.polygons: p_.use_smooth = True
    return me_

TREE_MATS = {}
def tree_mats(sp, fuzz=False):
    k = (sp, fuzz)
    if k not in TREE_MATS:
        cl = {'spruce': '#2F4C34', 'fir': '#345540', 'round': '#42592F'}[sp]
        mc = wool_material(f'tree_{sp}', srgb_lin(cl), rot_deg=75.0, rim=0.22, nrm_strength=0.55, fuzz=fuzz, lot_amp=0.12, stripe=0.5)
        mt = wool_material('trunk', srgb_lin('#4A3420'), rot_deg=90.0, rim=0.1, fuzz=fuzz)
        TREE_MATS[k] = (mc, mt)
    return TREE_MATS[k]

CARD_POLY = {}
CARD_META = json.load(open(f'{E}/cards/cards_meta.json'))
def card_poly(nm):
    """outline polygon of the stitched card (from its alpha), in image-normalised (u, v up) coordinates"""
    if nm in CARD_POLY: return CARD_POLY[nm]
    import cv2
    a = cv2.imread(f'{E}/cards/{nm}_alb.png', cv2.IMREAD_UNCHANGED)
    al = (a[..., 3] > 127).astype(np.uint8)
    al = cv2.morphologyEx(al, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    cs, _ = cv2.findContours(al, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)
    c = cv2.approxPolyDP(c, 0.7, True)[:, 0, :].astype(np.float64)
    h, w = al.shape
    poly = [((x + 0.5) / w, 1.0 - (y + 0.5) / h) for x, y in c]
    area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    if area < 0: poly = poly[::-1]              # counter-clockwise in (u, v up)
    CARD_POLY[nm] = poly
    return poly

CARD_T = 0.022          # appliqued felt card: 0.6 mm thick
EDGE_MAT = None
def card_mesh(p):
    """v3: the stitched figure as an appliqued felt card with thickness (extruded outline, felt edge, cloth back), not a flat alpha sprite"""
    global EDGE_MAT
    nm = p['id']
    cm = CARD_META[nm]
    sU = 1.0 / (cm['sc'] * cm['ppu'])                    # game units per card-canvas pixel
    wC, hC, mgC = cm['W'] * sU, cm['H'] * sU, cm['mg'] * sU
    poly = card_poly(nm)
    me_ = bpy.data.meshes.new(f'card_{nm}')
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('uv')
    n = len(poly)
    fv = [bm.verts.new(((u - 0.5) * wC, 0.0, v * hC - mgC)) for u, v in poly]
    bv = [bm.verts.new(((u - 0.5) * wC, CARD_T, v * hC - mgC)) for u, v in poly]
    front = bm.faces.new(fv[::-1]); front.material_index = 0         # seen from -y (camera side): clockwise in (x, z up) after the reversal
    back = bm.faces.new(bv); back.material_index = 2
    for i in range(n):
        j = (i + 1) % n
        q = bm.faces.new((fv[i], fv[j], bv[j], bv[i])); q.material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f_ in bm.faces:
        if f_.material_index in (0, 2):
            for l_ in f_.loops:
                l_[uvl].uv = (l_.vert.co.x / wC + 0.5, (l_.vert.co.z + mgC) / hC)
    # ensure the front faces -y
    if front.normal.y > 0:
        for f_ in bm.faces: f_.normal_flip()
    bmesh.ops.triangulate(bm, faces=[f_ for f_ in bm.faces if len(f_.verts) > 4], quad_method='BEAUTY', ngon_method='EAR_CLIP')
    bm.to_mesh(me_); bm.free()
    for p_ in me_.polygons: p_.use_smooth = False
    m, nb_, out_ = new_mat(f'card_{nm}')
    ta = nb_.node('ShaderNodeTexImage'); ta.image = img(f'{E}/cards/{nm}_alb.png'); ta.interpolation = 'Linear'; ta.extension = 'EXTEND'
    tn = nb_.node('ShaderNodeTexImage'); tn.image = img(f'{E}/cards/{nm}_nrm.png', noncolor=True); tn.interpolation = 'Linear'; tn.extension = 'EXTEND'
    nmn = nb_.node('ShaderNodeNormalMap'); nmn.uv_map = 'uv'; nmn.inputs['Strength'].default_value = 1.6
    nb_.link(tn.outputs['Color'], nmn.inputs['Color'])
    sh = white_shade(nb_, nmn.outputs['Normal'])
    uvg, geo = board_uv(nb_)
    lit = lit_terms(nb_, uvg, sh, nmn.outputs['Normal'])
    col = nb_.vmath('MULTIPLY', ta.outputs['Color'], lit)
    ndv = nb_.vmath('DOT_PRODUCT', nmn.outputs['Normal'], geo.outputs['Incoming'])
    fr_ = nb_.math('SUBTRACT', 1.0, ndv.outputs['Value'], clamp=True); fr3 = nb_.math('POWER', fr_.outputs[0], 3.0); rimv = nb_.math('MULTIPLY', fr3.outputs[0], 0.18)
    rimc = nb_.vmath('SCALE', nb_.vmath('MULTIPLY', lit, ta.outputs['Color']).outputs[0], None, rimv.outputs[0])
    tot = nb_.vmath('ADD', col.outputs[0], rimc.outputs[0])
    em = nb_.node('ShaderNodeEmission'); nb_.link(tot.outputs[0], em.inputs['Color'])
    tr0 = nb_.node('ShaderNodeBsdfTransparent'); mx0 = nb_.node('ShaderNodeMixShader')
    gtc = nb_.math('GREATER_THAN', ta.outputs['Alpha'], 0.5)                  # holes of the cut-out (between arm and body) are real holes
    fdm = nb_.math('MULTIPLY', gtc.outputs[0], fade_node(nb_))
    nb_.link(fdm.outputs[0], mx0.inputs[0]); nb_.link(tr0.outputs[0], mx0.inputs[1]); nb_.link(em.outputs[0], mx0.inputs[2])
    nb_.link(mx0.outputs[0], out_.inputs['Surface'])
    m.blend_method = 'HASHED'; m.shadow_method = 'HASHED'
    if EDGE_MAT is None:
        EDGE_MAT = (wool_material('card_edge', srgb_lin('#4A3A28'), rot_deg=90.0, rim=0.2), wool_material('card_back', srgb_lin('#9C8A68'), rot_deg=0.0, rim=0.2))
        EDGE_MAT[1].use_backface_culling = True
    me_.materials.append(m); me_.materials.append(EDGE_MAT[0]); me_.materials.append(EDGE_MAT[1])
    return me_

TETHER_MATS = {}
HEX_T = {(h['q'], h['r']): h['t'] for h in LAYOUT['hexes']}
def tether_mat(terr):
    """the tether is the thread the piece's satin was stitched with: terrain dye, a touch toward unbleached linen (pulled threads read lighter at the fibre tips)"""
    if terr not in TETHER_MATS:
        import pal2
        hx = pal2.DYE.get(terr, pal2.DYE['plains'])[0].lstrip('#')
        c = np.array([int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)])
        lin = np.array([int(pal2.LINEN_BASE.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)])
        c = c * 0.50 + lin * 0.50
        c8 = '#%02X%02X%02X' % tuple(int(round(v * 255)) for v in c)
        TETHER_MATS[terr] = wool_material(f'tether_{terr}', srgb_lin(c8), rot_deg=0.0, rim=0.5, nrm_strength=0.6, scale=14.0)
    return TETHER_MATS[terr]

TH_R = 0.0098       # strand radius (two plied strands), BU
PCS = []
starts = AN['starts']

def add_fuzz(ob, me2, mats_fz, parent, th=FUZZ_TH):
    """fibre-halo shell: a copy of the mesh inflated by th with the hashed-alpha fibre material of every slot (soft silhouette, no razor edge)"""
    fm = me2.copy()
    for i, mt in enumerate(mats_fz): fm.materials[i] = mt
    fo = bpy.data.objects.new(ob.name + '_fz', fm); sc.collection.objects.link(fo); fo.parent = parent
    fo.location = ob.location; fo.rotation_euler = ob.rotation_euler
    md = fo.modifiers.new('fz', 'SOLIDIFY'); md.thickness = th; md.offset = 1.0; md.use_rim = False
    fo.visible_shadow = False
    return fo

for i, p in enumerate(PIECES):
    if NOPIECES or p.get('skip') or starts[i] is None: continue
    piv = bpy.data.objects.new(f'piv_{p["id"]}', None); sc.collection.objects.link(piv)
    scl = bpy.data.objects.new(f'scl_{p["id"]}', None); sc.collection.objects.link(scl); scl.parent = piv
    piv.location = (p['x'], -p['z_back'], 0.0)
    th = None; fz = None
    if p['kind'] in ('town', 'site', 'lumber', 'banner'):
        realm_ = p.get('realm') or 'gold'
        mesh, n0, nms = load_model(p['model'], realm_)
        me2 = scaled_copy(mesh, p['scale'])
        ob = bpy.data.objects.new(p['id'], me2); sc.collection.objects.link(ob); ob.parent = scl
        ob.location = (0, -(p['z'] - p['z_back']), 0)
        th = 0.0055 if p['kind'] == 'town' else 0.0036
        bev = ob.modifiers.new('bevel', 'BEVEL') if os.environ.get('NOBEVEL') != '1' else None
        if bev is None: bev = type('X', (), {})()
        bev.width = 0.020 if p['kind'] == 'town' else 0.012; bev.segments = 2; bev.limit_method = 'ANGLE'
        bev.angle_limit = math.radians(40); bev.harden_normals = False
        # (v3: the fibre shell stays on the organic pieces; on the flat-faced OBJ buildings it printed speckle, they rely on rounded bevels + the brown outline hull)
        if os.environ.get('FUZZ_OBJ') == '1' and not NOFUZZ: fz = add_fuzz(ob, me2, [piece_mat(nm_, realm_, True) for nm_ in nms], scl, 0.016 if p['kind'] == 'town' else 0.012)
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
        th = 0.0026
        if not NOFUZZ:
            mcf, mtf = tree_mats(p['sp'], True)
            fz = add_fuzz(ob, me2, [mcf, mtf], scl, 0.011)
    else:
        me2 = card_mesh(p)
        ob = bpy.data.objects.new(p['id'], me2); sc.collection.objects.link(ob); ob.parent = scl
        n0 = 3
    if th and os.environ.get('NOOUTLINE') != '1':
        mod = ob.modifiers.new('outline', 'SOLIDIFY'); mod.thickness = th; mod.offset = 1.0
        mod.use_flip_normals = True; mod.material_offset = n0; mod.use_rim = False
    cu = bpy.data.curves.new(f'teth_{p["id"]}', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = TH_R; cu.bevel_resolution = 2
    cu.materials.append(tether_mat(HEX_T.get(tuple(p['hex']), 'plains')))
    tob = bpy.data.objects.new(f'teth_{p["id"]}', cu); sc.collection.objects.link(tob)
    ob['fade'] = 0.0
    if fz is not None: fz['fade'] = 0.0
    PCS.append(dict(p=p, i=i, piv=piv, scl=scl, ob=ob, fz=fz, teth=tob, cu=cu, start=starts[i], T=AN['tethers'].get(p['id'])))
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

def paint_ao(f, poses):
    """contact occlusion map (1/4 board resolution): a soft dark skirt under every risen piece where it meets the cloth, growing as it stands up"""
    import cv2
    ao = np.zeros((H // 4, W // 4), np.float32)
    k = PPU / 4.0
    for pc, ang in poses:
        p = pc['p']
        if ang is None or ang > 80: continue
        sgain = float((1 - max(ang, 0.0) / 80.0) ** 0.8)
        if p['kind'] == 'tree': sgain *= 0.8
        elif p['kind'] == 'card': sgain *= 0.7
        if p['kind'] in ('town', 'site', 'lumber', 'banner'):
            bx0, bz0, bx1, bz1 = p['base']
            c = (int(((bx0 + bx1) / 2 - BX0) * k), int(((bz0 + bz1) / 2 - BZ0) * k)); ax = ((bx1 - bx0) / 2 * k + 3, (bz1 - bz0) / 2 * k + 3)
        elif p['kind'] == 'tree':
            c = (int((p['x'] - BX0) * k), int((p['z'] - BZ0) * k)); ax = (p['rad'] * 1.2 * k + 2, p['rad'] * 0.9 * k + 2)
        else:
            c = (int((p['x'] - BX0) * k), int((p['z'] - BZ0 + 0.02) * k)); ax = (p['w'] * 0.5 * k + 2, 0.07 * k + 2)
        x0_, y0_ = max(c[0] - int(ax[0]) - 3, 0), max(c[1] - int(ax[1]) - 3, 0)
        x1_, y1_ = min(c[0] + int(ax[0]) + 4, ao.shape[1]), min(c[1] + int(ax[1]) + 4, ao.shape[0])
        if x1_ <= x0_ or y1_ <= y0_: continue
        patch = np.zeros((y1_ - y0_, x1_ - x0_), np.float32)
        cv2.ellipse(patch, (c[0] - x0_, c[1] - y0_), (max(1, int(ax[0])), max(1, int(ax[1]))), 0, 0, 360, sgain, -1, cv2.LINE_AA)
        ao[y0_:y1_, x0_:x1_] = np.maximum(ao[y0_:y1_, x0_:x1_], patch)
    ao = cv2.GaussianBlur(ao, (0, 0), 2.0)
    arr = np.dstack([ao, ao, ao, np.ones_like(ao)])[::-1].astype(np.float32)
    AOI.pixels.foreach_set(arr.ravel()); AOI.update()

def idle(pc, f, ang):
    """hold life (f1767-1782 and after each piece settles): figures breathe and sway, trees stir, the banner flutters"""
    p = pc['p']; st = pc['start']
    D = anim.RISE_DUR.get(p['kind'], 12.0)
    u = min(1.0, max(0.0, (f - st - D) / 6.0))
    if u <= 0: return 0.0, 0.0
    ph = anim._h(pc['i'], 91) * 6.283
    if p['kind'] == 'card': return u * math.radians(1.1) * math.sin(f * 0.21 + ph), u * math.radians(0.7) * math.sin(f * 0.17 + ph * 1.7)
    if p['kind'] == 'banner': return u * math.radians(2.6) * math.sin(f * 0.26 + ph), u * math.radians(1.3) * math.sin(f * 0.19 + ph)
    if p['kind'] == 'tree': return u * math.radians(0.55) * math.sin(f * 0.13 + ph), u * math.radians(0.45) * math.sin(f * 0.11 + ph * 2.1)
    return 0.0, 0.0

def update_pieces(f, z_mm):
    poses = []
    for pc in PCS:
        p = pc['p']; st = pc['start']
        ang = anim.hinge_angle(p, st, f)
        poses.append((pc, ang))
        vis = ang is not None
        pc['ob'].hide_render = not vis
        if pc['fz'] is not None: pc['fz'].hide_render = not vis
        fv = float(smoothstep(0.0, 1.0, (f - st + 0.35) / 3.0)) if vis else 0.0
        pc['ob']['fade'] = fv
        if pc['fz'] is not None: pc['fz']['fade'] = fv
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
        sx_ = 1.0
        if p['kind'] == 'banner': sx_ = 0.30 + 0.70 * float(smoothstep(0.0, 1.0, 1 - max(ang, 0.0) / 78.0))      # the flag unfurls as the pole comes upright
        pc['scl'].scale = (sx_, max(sy, 0.02), hsc)
        ix, iy = idle(pc, f, ang)
        pc['piv'].rotation_euler = (-math.radians(ang) + ix, iy, 0)
        T = pc['T']; pc['teth'].hide_render = T is None
        if T is None: continue
        ft = anim.twos(f)
        for k, ((xl, yl), sf) in enumerate(zip(T['pts'], T['snap'])):
            hole = face_point(pc, xl, yl, 90.0, 0.0, p['k']); hole.z = ground_height(hole.x, -hole.y, z_mm) + 0.004
            anc = face_point(pc, xl, yl, ang, sy, hsc)
            rr = np.random.default_rng(pc['i'] * 100 + k)
            if ft < sf:
                # taut thread: lazy lateral wander + catenary sag that close as the piece lifts, two plies twisted round each other
                d = anc - hole; L_ = d.length
                if L_ < 1e-4: continue
                slack = max(0.0, 1 - (ft - st) / max(1, sf - st))
                tan = d.normalized()
                n1 = Vector((-d.y, d.x, 0.0))
                n1 = n1.normalized() if n1.length > 1e-5 else Vector((1, 0, 0))
                n2 = tan.cross(n1).normalized()
                ph1, ph2 = rr.uniform(0, 6.28), rr.uniform(0, 6.28)
                f1, f2 = rr.uniform(0.9, 1.5), rr.uniform(1.6, 2.4)
                amp = L_ * (0.022 + 0.07 * slack) * (0.7 + 0.6 * rr.random())
                tw_ph = rr.uniform(0, 6.28)
                N_ = 28
                cpts = []
                for t in np.linspace(0, 1, N_):
                    env = math.sin(math.pi * t) ** 0.8
                    sag = 0.14 * L_ * math.sin(math.pi * t) * (0.10 + 0.90 * slack)
                    off = n1 * (amp * env * math.sin(2 * math.pi * f1 * t + ph1)) + n2 * (amp * 0.6 * env * math.sin(2 * math.pi * f2 * t + ph2))
                    cpts.append(hole + d * t + off + Vector((0, 0, -sag)))
                for ply in (0, 1):
                    pts = []
                    for j_, t in enumerate(np.linspace(0, 1, N_)):
                        j0, j1 = max(j_ - 1, 0), min(j_ + 1, N_ - 1)
                        tg = (cpts[j1] - cpts[j0]).normalized()
                        nn = tg.cross(Vector((0, 0, 1)))
                        nn = nn.normalized() if nn.length > 1e-5 else n1
                        bb = tg.cross(nn).normalized()
                        th_ = 2 * math.pi * (t * L_ / 0.085) + tw_ph + math.pi * ply
                        pts.append(cpts[j_] + (nn * math.cos(th_) + bb * math.sin(th_)) * (TH_R * 0.82))
                    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
                    for j_, v in enumerate(pts): sp.points[j_].co = (v.x, v.y, v.z, 1)
                continue
            else:
                age = ft - sf
                if age > 8: continue
                # snapped: the cloth end whips back and curls into its hole (the snipped end that stays is part of the footprint), the piece end falls away
                l1 = (0.09 + 0.06 * rr.random()) * max(0.0, 1 - age / 7.0)
                ang0 = rr.uniform(0, 2 * math.pi)
                curl = min(1.0, age / 3.0)
                pts = []
                for t in np.linspace(0, 1, 5):
                    a_ = ang0 + curl * 2.6 * t
                    pts.append(hole + Vector((math.cos(a_) * l1 * t, math.sin(a_) * l1 * t, 0.006 + (1 - curl) * 0.025 * t)))
                if l1 > 0.004:
                    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
                    for j_, v in enumerate(pts): sp.points[j_].co = (v.x, v.y, v.z, 1)
                l2 = (0.09 + 0.06 * rr.random()) * max(0.0, 1 - age / 8.0)
                swing = math.sin(age * 1.4 + k) * math.exp(-age / 5.0) * 0.7
                pts = [anc, anc + Vector((math.sin(swing) * l2 * 0.5, -l2 * 0.35, -l2 * math.cos(swing) * 0.9))]
                pts = [pts[0], pts[0] * 0.5 + pts[1] * 0.5 + Vector((0, 0, 0.003)), pts[1]]
                if l2 < 0.004: continue
            sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
            for j_, v in enumerate(pts): sp.points[j_].co = (v.x, v.y, v.z, 1)
    return poses

# ------------------------------------------------------------------ per-frame light state
def set_light_state(f):
    gL = lm.gain('L', f); gR = lm.gain('R', f)
    if lm.NEUTRAL: gL = gR = 1.0
    for a_, b_ in GAINS:
        a_.outputs[0].default_value = gL; b_.outputs[0].default_value = gR
    # per-frame pool maps (pools widen slightly with the swell); the ground's flat reference keeps the base pools
    kL, kR, kF = lm.kmaps((H // 4, W // 4), 0, 0, 4, f)
    kF = lm.fill_map(kL, kR, gL, gR, f)
    cfv = tuple(float(v) for v in lm.fill_colour(f) * lm.FILL_I * lm.fill_gain(f))
    for nd in FILL_NODES: nd.inputs[0].default_value = cfv
    arr = np.dstack([kL, kR, kF, np.ones_like(kL)])[::-1].astype(np.float32)           # Blender images are bottom-up
    KT.pixels.foreach_set(arr.ravel()); KT.update()
    # glint: ramps in with the crane, narrow KK lobe, per-candle gain follows the candles
    ramp = float(smoothstep(1730.0, 1738.0, f) * (1 - smoothstep(1756.0, 1768.0, f)))     # the glint lives while the camera cranes (f1730-1766)
    GLINT.outputs[0].default_value = 0.0 if NOGLINT else GLINT_AMP * ramp
    # the band sweeps the board over f1734-1762 (west -> east): s0 from -18 to +20 board units along the sweep direction
    GL_S0.outputs[0].default_value = float(-18.0 + 38.0 * float(smoothstep(1732.0, 1764.0, f)))
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
    poses_ = update_pieces(f, z_mm)
    paint_ao(f, poses_)
    gL, gR = set_light_state(f)
    sc.frame_set(f)
    sc.render.filepath = f'{OUTD}/f{f:04d}.exr'
    bpy.ops.render.render(write_still=True)
    log('frame', f, '%.1fs' % (time.time() - t), 'gL %.3f gR %.3f' % (gL, gR))
log('done')
