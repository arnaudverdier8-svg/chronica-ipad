"""f899 Eevee scene (Blender 4.0.2, EEVEE legacy, xvfb): the standing slips (displaced meshes with felt backing), snapped thread tethers,
a white diffuse shadow-catcher plane, the real f899 camera, the hearth sun (2200 K, from the bottom edge), the pale daylight arc sun
(from the left) and a dusk fill world.  1 BU = 1 mm.  Renders every (kind, light) pass to linear EXR:

  slips_<light>.exr       slips + tethers only, transparent film (premultiplied RGBA) + Z
  plane_<light>.exr       white plane + slips + tethers (receives their shadows)
  planeclean_<light>.exr  white plane only (unshadowed reference)         light in {hearth, cool, fill}

    xvfb-run -a blender -b --factory-startup -P eevee_scene.py -- OUT_DIR [--scale 1.0] [--taa 32] [--only slips_hearth,...]
"""
import sys, os, json, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import bpy
from mathutils import Matrix, Vector
import camera as CAM

T0 = time.time()
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0]
opt = dict(scale=1.0, taa=32, only=None, slips=None, border=None, interp=os.environ.get('SLIP_INTERP', 'Linear'), aniso=os.environ.get('ANISO', 'FILTER_16'), nstr=float(os.environ.get('NSTR', '2.2')))
i = 1
while i < len(argv):
    if argv[i] == '--scale': opt['scale'] = float(argv[i + 1]); i += 2
    elif argv[i] == '--taa': opt['taa'] = int(argv[i + 1]); i += 2
    elif argv[i] == '--only': opt['only'] = argv[i + 1].split(','); i += 2
    elif argv[i] == '--slips': opt['slips'] = argv[i + 1].split(','); i += 2
    elif argv[i] == '--border': opt['border'] = [float(v) for v in argv[i + 1:i + 5]]; i += 5
    else: i += 1
ROOT = os.path.dirname(HERE)
SLIPDIR = os.path.join(ROOT, 'blend', 'slips_v2')
shot = json.load(open(os.path.join(ROOT, 'shot_f899_v2.json')))
ex = json.load(open(os.path.join(SLIPDIR, 'slips_export.json')))
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 0.001; sc.unit_settings.length_unit = 'MILLIMETERS'
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x = int(CAM.W * opt['scale']); sc.render.resolution_y = int(CAM.H * opt['scale']); sc.render.resolution_percentage = 100
E = sc.eevee
E.taa_render_samples = opt['taa']; E.taa_samples = 4
E.use_soft_shadows = True; E.shadow_cascade_size = '4096'; E.shadow_cube_size = '2048'; E.use_shadow_high_bitdepth = True
E.use_gtao = True; E.gtao_distance = 10.0; E.gtao_factor = 1.25; E.use_gtao_bent_normals = True; E.use_gtao_bounce = False
E.use_ssr = False; E.use_bloom = False; E.use_motion_blur = False
sc.render.filter_size = 0.85
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0.0; sc.view_settings.gamma = 1.0
sc.display_settings.display_device = 'sRGB'
sc.render.use_motion_blur = False
try:
    bpy.context.preferences.system.anisotropic_filter = opt['aniso']
except Exception as e:
    print('aniso', e)
if opt['border']:
    b = opt['border']; sc.render.use_border = True; sc.render.use_crop_to_border = False
    sc.render.border_min_x, sc.render.border_min_y, sc.render.border_max_x, sc.render.border_max_y = b[0], b[1], b[2], b[3]

# ------------------------------------------------------------------ camera
cam = CAM.build(shot['camera'])
cd = bpy.data.cameras.new('cam'); cd.sensor_width = CAM.SENSOR_W; cd.sensor_fit = 'HORIZONTAL'; cd.lens = cam['focal_mm']
cd.clip_start = 100.0; cd.clip_end = 6000.0; cd.dof.use_dof = False
co = bpy.data.objects.new('cam', cd); sc.collection.objects.link(co); sc.camera = co
Mw = np.eye(4); Mw[:3, :3] = cam['Rcw']; Mw[:3, 3] = cam['C']
co.matrix_world = Matrix(Mw.tolist())

# ------------------------------------------------------------------ lights
def light_colour_rgb(K, tint):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(ROOT)), 'lib'))
    from chron.color import light_colour
    return np.asarray(light_colour(K, tint), np.float32)


def sun(name, az, el, K, tint, strength, angle_deg):
    ld = bpy.data.lights.new(name, 'SUN')
    c = light_colour_rgb(K, tint); c = c / c.max()
    ld.color = tuple(float(v) for v in c)
    ld.energy = float(strength) * math.pi
    ld.angle = math.radians(angle_deg)
    ld.use_contact_shadow = True; ld.contact_shadow_distance = 5.0; ld.contact_shadow_thickness = 0.6
    ld.shadow_cascade_count = 4; ld.shadow_cascade_max_distance = 1800.0; ld.shadow_cascade_exponent = 0.8; ld.shadow_buffer_bias = 0.6
    ob = bpy.data.objects.new(name, ld); sc.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    Lv = np.array([math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)])       # toward the light, Blender coords
    z = Lv / np.linalg.norm(Lv)
    x = np.cross(np.array([0, 0, 1.0]), z); x /= np.linalg.norm(x)
    y = np.cross(z, x)
    M = np.eye(4); M[:3, 0] = x; M[:3, 1] = y; M[:3, 2] = z
    ob.matrix_world = Matrix(M.tolist())
    return ob, c


H_, C_ = shot['hearth'], shot['cool']
sun_h, col_h = sun('hearth', H_['az'], H_['el'], H_['K'], H_['tint'], H_['key_i'], H_.get('angle', 4.5))
sun_c, col_c = sun('cool', C_['az'], C_['el'], C_['K'], C_['tint'], C_['key_i'], C_.get('angle', 1.6))
if C_.get('rgb'):
    cc_ = np.array(C_['rgb'], np.float32); cc_ = cc_ / cc_.max(); col_c = cc_
    sun_c.data.color = tuple(float(v) for v in cc_)
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
wbg = world.node_tree.nodes['Background']
fcol = light_colour_rgb(shot['fill']['K'], 0.1); fcol = fcol / fcol.max()
wbg.inputs['Color'].default_value = (float(fcol[0]), float(fcol[1]), float(fcol[2]), 1.0)
wbg.inputs['Strength'].default_value = 0.0

# ------------------------------------------------------------------ helpers
def load_img(path, nonc=False, linear=False):
    im = bpy.data.images.load(path, check_existing=True)
    if nonc:
        im.colorspace_settings.name = 'Non-Color'
    elif linear:
        im.colorspace_settings.name = 'Linear Rec.709'
    return im


def mesh_obj(name, co_, quads, uv=None, midx=None, vcol=None, smooth=None, autosmooth=60.0):
    me = bpy.data.meshes.new(name)
    me.from_pydata(co_.tolist(), [], quads.tolist())
    if uv is not None:
        uvl = me.uv_layers.new(name='uv')
        uvl.data.foreach_set('uv', uv[quads.ravel()].astype(np.float32).ravel())
    if midx is not None:
        me.polygons.foreach_set('material_index', midx.astype(np.int32))
    if smooth is None:
        me.polygons.foreach_set('use_smooth', np.ones(len(quads), bool))
    else:
        me.polygons.foreach_set('use_smooth', smooth)
    if vcol is not None:
        ca = me.color_attributes.new('edge', 'FLOAT_COLOR', 'POINT')
        rgba = np.concatenate([vcol, np.ones((len(vcol), 1), np.float32)], 1)
        ca.data.foreach_set('color', rgba.ravel())
    try:
        me.use_auto_smooth = True; me.auto_smooth_angle = math.radians(autosmooth)
    except Exception:
        pass
    me.update()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    return ob


def slip_material(g):
    m = bpy.data.materials.new('slip_' + g); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']
    uvn = N.new('ShaderNodeUVMap'); uvn.uv_map = 'uv'
    ta = N.new('ShaderNodeTexImage'); ta.image = load_img(os.path.join(SLIPDIR, f'{g}_alb.png'), linear=True); ta.interpolation = opt['interp']; ta.extension = 'EXTEND'
    tn = N.new('ShaderNodeTexImage'); tn.image = load_img(os.path.join(SLIPDIR, f'{g}_nrm.png'), nonc=True); tn.interpolation = opt['interp']; tn.extension = 'EXTEND'
    tm = N.new('ShaderNodeTexImage'); tm.image = load_img(os.path.join(SLIPDIR, f'{g}_mat.png'), nonc=True); tm.interpolation = 'Linear'; tm.extension = 'EXTEND'
    for t in (ta, tn, tm):
        L.new(uvn.outputs['UV'], t.inputs['Vector'])
    L.new(ta.outputs['Color'], b.inputs['Base Color'])
    nm = N.new('ShaderNodeNormalMap'); nm.uv_map = 'uv'; nm.inputs['Strength'].default_value = opt['nstr']
    L.new(tn.outputs['Color'], nm.inputs['Color']); L.new(nm.outputs['Normal'], b.inputs['Normal'])
    sep = N.new('ShaderNodeSeparateColor'); L.new(tm.outputs['Color'], sep.inputs['Color'])
    L.new(sep.outputs['Red'], b.inputs['Roughness']); L.new(sep.outputs['Green'], b.inputs['Metallic']); L.new(sep.outputs['Blue'], b.inputs['Sheen Weight'])
    b.inputs['Sheen Roughness'].default_value = 0.42
    b.inputs['Specular IOR Level'].default_value = 0.25
    b.inputs['IOR'].default_value = 1.45
    # tint of the sheen follows the albedo
    L.new(ta.outputs['Color'], b.inputs['Sheen Tint'])
    return m


def felt_material():
    m = bpy.data.materials.new('felt'); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']
    va = N.new('ShaderNodeVertexColor'); va.layer_name = 'edge'
    L.new(va.outputs['Color'], b.inputs['Base Color'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 5.0; nz.inputs['Detail'].default_value = 8.0
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.6; bump.inputs['Distance'].default_value = 0.2
    tc = N.new('ShaderNodeTexCoord')
    L.new(tc.outputs['Object'], nz.inputs['Vector']); L.new(nz.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.78; b.inputs['Sheen Weight'].default_value = 0.45; b.inputs['Specular IOR Level'].default_value = 0.30
    return m


def tether_material():
    m = bpy.data.materials.new('tether'); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']
    va = N.new('ShaderNodeVertexColor'); va.layer_name = 'edge'
    L.new(va.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.48; b.inputs['Sheen Weight'].default_value = 0.8; b.inputs['Sheen Roughness'].default_value = 0.35; b.inputs['Specular IOR Level'].default_value = 0.55
    return m


def white_material(alb=0.8):
    m = bpy.data.materials.new('white'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (alb, alb, alb, 1.0); b.inputs['Roughness'].default_value = 1.0; b.inputs['Specular IOR Level'].default_value = 0.0
    return m


# ------------------------------------------------------------------ scene objects
slip_objs = []
fm = felt_material()
for s in ex['slips']:
    g = s['group']
    if opt['slips'] and g not in opt['slips']:
        continue
    z = np.load(os.path.join(SLIPDIR, f'{g}_mesh.npz'))
    smooth = np.zeros(len(z['quads']), bool); smooth[:int((z['midx'] == 0).sum())] = True
    ob = mesh_obj('slip_' + g, z['co'], z['quads'], z['uv'], z['midx'], z['vcol'], smooth=smooth)
    ob.data.materials.append(slip_material(g)); ob.data.materials.append(fm)
    ob.matrix_world = Matrix(np.array(s['matrix']).tolist())
    slip_objs.append(ob)
zt = np.load(os.path.join(SLIPDIR, 'tethers.npz'))
teth = mesh_obj('tethers', zt['V'], zt['Q'], None, None, zt['C'])
teth.data.materials.append(tether_material())
# shadow-catcher plane
pl = bpy.data.meshes.new('plane')
PW, PH = 2600.0, 1800.0
pl.from_pydata([(-1000, -1100, 0), (1600, -1100, 0), (1600, 700, 0), (-1000, 700, 0)], [], [(0, 1, 2, 3)])
plane = bpy.data.objects.new('plane', pl); sc.collection.objects.link(plane)
plane.data.materials.append(white_material())

# ------------------------------------------------------------------ compositor file outputs
sc.use_nodes = True
nt = sc.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
rl = nt.nodes.new('CompositorNodeRLayers')
fo = nt.nodes.new('CompositorNodeOutputFile')
fo.base_path = OUT
fo.format.file_format = 'OPEN_EXR'; fo.format.color_depth = '32'; fo.format.exr_codec = 'ZIP'
fo.file_slots[0].path = 'img_'
fo.file_slots.new('z_')
nt.links.new(rl.outputs['Image'], fo.inputs[0])
sc.view_layers[0].use_pass_z = True
nt.links.new(rl.outputs['Depth'], fo.inputs[1])

json.dump(dict(hearth=dict(col=[float(v) for v in col_h], strength=float(H_['key_i'])), cool=dict(col=[float(v) for v in col_c], strength=float(C_['key_i'])),
                fill=dict(col=[float(v) for v in fcol], strength=float(shot['fill']['i']))), open(os.path.join(OUT, 'render_meta.json'), 'w'))
RUNS = [(k, l) for k in ('slips', 'plane', 'planeclean') for l in ('hearth', 'cool', 'fill')]
if opt['only']:
    RUNS = [r for r in RUNS if f'{r[0]}_{r[1]}' in opt['only']]
fill_i = shot['fill']['i']
for kind, light in RUNS:
    sun_h.hide_render = light != 'hearth'; sun_c.hide_render = light != 'cool'
    wbg.inputs['Strength'].default_value = fill_i if light == 'fill' else 0.0
    for ob in slip_objs + [teth]:
        ob.hide_render = (kind == 'planeclean')
    plane.hide_render = (kind == 'slips')
    sc.render.film_transparent = (kind == 'slips')
    name = f'{kind}_{light}'
    fo.file_slots[0].path = f'{name}_img_'; fo.file_slots[1].path = f'{name}_z_'
    t1 = time.time()
    sc.frame_set(1)
    bpy.ops.render.render(write_still=False)
    print(f'RENDERED {name} {time.time() - t1:.1f}s (total {time.time() - T0:.1f}s)', flush=True)
print('ALL DONE', time.time() - T0)
