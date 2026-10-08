"""Chronica intro: 3D embroidered map (video time 35.0s -> 54.4s).
Run: blender -b -P map_scene.py -- [--test f1,f2,...] [--res 1920] [--samples N] [--out DIR]"""
import os, bpy, bmesh, math, json, random, sys
from mathutils import Vector, Euler

D = os.path.dirname(os.path.abspath(__file__)) + '/'
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    return args[args.index(name) + 1] if name in args else default

FPS = 24
T0 = 35.0
def F(t):  # video time -> scene frame
    return int(round((t - T0) * FPS)) + 1

MAPW, MAPH = 16.0, 9.0
def UV(u, v, z=0.0):
    return Vector(((u - 0.5) * MAPW, (0.5 - v) * MAPH, z))

layout = json.load(open(D + 'map_layout.json'))
random.seed(4)

# ---------------- scene reset ----------------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, F(54.4)
ENGINE = arg('--engine', 'EEVEE')
sc.render.engine = 'BLENDER_EEVEE' if ENGINE == 'EEVEE' else 'CYCLES'
ee = sc.eevee
ee.taa_render_samples = int(arg('--samples', 32))
ee.use_gtao = True; ee.gtao_distance = 0.35; ee.gtao_factor = 1.2
ee.use_soft_shadows = True
ee.shadow_cube_size = '512'; ee.shadow_cascade_size = '2048'
ee.use_bloom = True; ee.bloom_threshold = 1.2; ee.bloom_intensity = 0.03
ee.use_ssr = False
sc.cycles.device = 'CPU'
sc.cycles.samples = int(arg('--samples', 24))
sc.cycles.use_denoising = False
try:
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
except Exception:
    pass
sc.cycles.max_bounces = 4
sc.cycles.diffuse_bounces = 2
sc.cycles.glossy_bounces = 1
sc.cycles.transmission_bounces = 1
sc.cycles.transparent_max_bounces = 8
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.05
resx = int(arg('--res', 1920))
sc.render.resolution_x, sc.render.resolution_y = resx, int(resx * 9 / 16)
sc.render.film_transparent = False
sc.view_settings.view_transform = 'Filmic'
sc.view_settings.look = 'Medium High Contrast'
sc.render.image_settings.file_format = 'JPEG'
sc.render.image_settings.quality = 93

world = bpy.data.worlds.new('W'); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.012, 0.011, 0.016, 1); bg.inputs[1].default_value = 1.0

# ---------------- material helpers ----------------
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    return m, nt, bsdf

def setin(bsdf, name, val):
    if name in bsdf.inputs:
        bsdf.inputs[name].default_value = val

# Edge darkness: shared value animated over time; factor from world position.
dark_ctrl = bpy.data.objects.new('DarkCtrl', None); sc.collection.objects.link(dark_ctrl)
dark_ctrl['thr'] = 1.6
def edge_dark_group():
    g = bpy.data.node_groups.new('EdgeDark', 'ShaderNodeTree')
    g.interface.new_socket('Fac', in_out='OUTPUT', socket_type='NodeSocketFloat')
    n = g.nodes; l = g.links
    gout = n.new('NodeGroupOutput')
    geo = n.new('ShaderNodeNewGeometry')
    sep = n.new('ShaderNodeSeparateXYZ'); l.new(geo.outputs['Position'], sep.inputs[0])
    ax = n.new('ShaderNodeMath'); ax.operation = 'DIVIDE'; ax.inputs[1].default_value = MAPW / 2; l.new(sep.outputs[0], ax.inputs[0])
    ay = n.new('ShaderNodeMath'); ay.operation = 'DIVIDE'; ay.inputs[1].default_value = MAPH / 2; l.new(sep.outputs[1], ay.inputs[0])
    px = n.new('ShaderNodeMath'); px.operation = 'POWER'; px.inputs[1].default_value = 4; l.new(ax.outputs[0], px.inputs[0])
    py = n.new('ShaderNodeMath'); py.operation = 'POWER'; py.inputs[1].default_value = 4; l.new(ay.outputs[0], py.inputs[0])
    s = n.new('ShaderNodeMath'); s.operation = 'ADD'; l.new(px.outputs[0], s.inputs[0]); l.new(py.outputs[0], s.inputs[1])
    r = n.new('ShaderNodeMath'); r.operation = 'POWER'; r.inputs[1].default_value = 0.25; l.new(s.outputs[0], r.inputs[0])
    tex = n.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = 0.6; tex.inputs['Detail'].default_value = 4
    l.new(geo.outputs['Position'], tex.inputs['Vector'])
    nm = n.new('ShaderNodeMath'); nm.operation = 'MULTIPLY_ADD'; nm.inputs[1].default_value = 0.35; nm.inputs[2].default_value = -0.17
    l.new(tex.outputs['Fac'], nm.inputs[0])
    d2 = n.new('ShaderNodeMath'); d2.operation = 'ADD'; l.new(r.outputs[0], d2.inputs[0]); l.new(nm.outputs[0], d2.inputs[1])
    thr = n.new('ShaderNodeValue'); thr.name = 'THR'; thr.outputs[0].default_value = 1.6
    lo = n.new('ShaderNodeMath'); lo.operation = 'SUBTRACT'; lo.inputs[1].default_value = 0.22; l.new(thr.outputs[0], lo.inputs[0])
    mr = n.new('ShaderNodeMapRange'); mr.interpolation_type = 'SMOOTHSTEP'
    l.new(d2.outputs[0], mr.inputs['Value']); l.new(lo.outputs[0], mr.inputs['From Min']); l.new(thr.outputs[0], mr.inputs['From Max'])
    l.new(mr.outputs[0], gout.inputs[0])
    return g
EDGE = edge_dark_group()
sc['dark_thr'] = 1.6

DARK = (0.012, 0.012, 0.022, 1)
def add_dark(nt, color_socket, bsdf):
    """Insert edge-darkness between color_socket and bsdf base color."""
    gn = nt.nodes.new('ShaderNodeGroup'); gn.node_tree = EDGE
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    nt.links.new(gn.outputs[0], mix.inputs['Factor'])
    nt.links.new(color_socket, mix.inputs[6])
    mix.inputs[7].default_value = (0.05, 0.05, 0.09, 1)
    nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
    if 'Sheen Tint' in bsdf.inputs:
        nt.links.new(mix.outputs[2], bsdf.inputs['Sheen Tint'])
    return mix

def img(path, nonColor=False):
    im = bpy.data.images.load(path)
    if nonColor:
        im.colorspace_settings.name = 'Non-Color'
    return im

# ---------------- table + map ----------------
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.03)); table = bpy.context.object
table.scale = (60, 60, 1)
m, nt, b = new_mat('Table')
wave = nt.nodes.new('ShaderNodeTexWave'); wave.inputs['Scale'].default_value = 0.35; wave.inputs['Distortion'].default_value = 6; wave.inputs['Detail'].default_value = 3
ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (0.035, 0.018, 0.010, 1); ramp.color_ramp.elements[1].color = (0.10, 0.052, 0.026, 1)
nt.links.new(wave.outputs['Fac'], ramp.inputs[0])
add_dark(nt, ramp.outputs[0], b)
setin(b, 'Roughness', 0.45)
table.data.materials.append(m)

bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0)); mp = bpy.context.object; mp.name = 'Map'
mp.scale = (MAPW, MAPH, 1)
bpy.ops.object.transform_apply(scale=True)
m, nt, b = new_mat('MapMat')
ti = nt.nodes.new('ShaderNodeTexImage'); ti.image = img(D + 'map_albedo.png'); ti.interpolation = 'Cubic'
th = nt.nodes.new('ShaderNodeTexImage'); th.image = img(D + 'map_height.png', True); th.interpolation = 'Cubic'
bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.9; bump.inputs['Distance'].default_value = 0.012
nt.links.new(th.outputs['Color'], bump.inputs['Height']); nt.links.new(bump.outputs[0], b.inputs['Normal'])
add_dark(nt, ti.outputs['Color'], b)
setin(b, 'Roughness', 0.82); setin(b, 'Sheen Weight', 0.6); setin(b, 'Sheen Roughness', 0.4)
mp.data.materials.append(m)
# thin cloth edge thickness
sol = mp.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.03; sol.offset = -1

# ---------------- wool / felt materials ----------------
def wool(name, color, knot=True, scale=40.0, rough=0.9, stripes=False):
    m, nt, b = new_mat(name)
    rgb = nt.nodes.new('ShaderNodeRGB'); rgb.outputs[0].default_value = color
    # per-object colour jitter
    oi = nt.nodes.new('ShaderNodeObjectInfo')
    hsv = nt.nodes.new('ShaderNodeHueSaturation'); hsv.inputs['Saturation'].default_value = 1.0
    jit = nt.nodes.new('ShaderNodeMath'); jit.operation = 'MULTIPLY_ADD'; jit.inputs[1].default_value = 0.35; jit.inputs[2].default_value = 0.82
    nt.links.new(oi.outputs['Random'], jit.inputs[0]); nt.links.new(jit.outputs[0], hsv.inputs['Value'])
    nt.links.new(rgb.outputs[0], hsv.inputs['Color'])
    if stripes:
        tex = nt.nodes.new('ShaderNodeTexWave'); tex.wave_type = 'BANDS'; tex.inputs['Scale'].default_value = scale; tex.inputs['Distortion'].default_value = 1.5
        h = tex.outputs['Fac']
    elif knot:
        tex = nt.nodes.new('ShaderNodeTexVoronoi'); tex.feature = 'SMOOTH_F1' if hasattr(tex, 'feature') else 'F1'
        tex.inputs['Scale'].default_value = scale
        h = tex.outputs['Distance']
    else:
        tex = nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = scale; tex.inputs['Detail'].default_value = 8
        h = tex.outputs['Fac']
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.8 if not knot else 1.0
    bump.inputs['Distance'].default_value = 0.02
    if knot and not stripes:
        bump.invert = True
    nt.links.new(h, bump.inputs['Height']); nt.links.new(bump.outputs[0], b.inputs['Normal'])
    # darken crevices
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 0.55
    nt.links.new(hsv.outputs[0], mul.inputs[6])
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = (1, 1, 1, 1); cr.color_ramp.elements[1].color = (0.35, 0.35, 0.35, 1)
    nt.links.new(h, cr.inputs[0]); nt.links.new(cr.outputs[0], mul.inputs[7])
    add_dark(nt, mul.outputs[2], b)
    setin(b, 'Roughness', rough); setin(b, 'Sheen Weight', 0.8); setin(b, 'Sheen Roughness', 0.35)
    return m

M_LEAF = [wool('leaf%d' % i, c, True, 26) for i, c in enumerate([(0.05, 0.16, 0.04, 1), (0.08, 0.22, 0.05, 1), (0.12, 0.26, 0.06, 1), (0.03, 0.11, 0.05, 1)])]
M_TRUNK = wool('trunk', (0.16, 0.08, 0.03, 1), False, 60, stripes=True)
M_MOUNT = wool('mount', (0.30, 0.27, 0.24, 1), False, 22, stripes=True)
M_SNOW = wool('snow', (0.85, 0.83, 0.78, 1), False, 26, stripes=True)
M_WOOD = wool('wood', (0.24, 0.12, 0.05, 1), False, 30, stripes=True, rough=0.5)
M_WALL = wool('wall', (0.78, 0.70, 0.55, 1), False, 50)
M_ROOFS = [wool('roof%d' % i, c, False, 30, stripes=True) for i, c in enumerate([(0.45, 0.07, 0.05, 1), (0.10, 0.16, 0.42, 1), (0.55, 0.36, 0.08, 1), (0.30, 0.15, 0.08, 1)])]
def gold_mat():
    m, nt, b = new_mat('gold')
    setin(b, 'Base Color', (0.75, 0.52, 0.16, 1)); setin(b, 'Metallic', 0.85); setin(b, 'Roughness', 0.35)
    return m
M_GOLD = gold_mat()

def link(o, col=None):
    (col or sc.collection).objects.link(o)
    return o

def key(o, path, frame, value, idx=-1):
    if idx >= 0:
        getattr(o, path)[idx] = value
        o.keyframe_insert(path, index=idx, frame=frame)
    else:
        setattr(o, path, value)
        o.keyframe_insert(path, frame=frame)

def pop_in(o, f0, dur=8, s1=1.0, over=1.18):
    o.scale = (0.001,) * 3; o.keyframe_insert('scale', frame=1)
    o.keyframe_insert('scale', frame=f0)
    o.scale = (s1 * over,) * 3; o.keyframe_insert('scale', frame=f0 + int(dur * 0.65))
    o.scale = (s1,) * 3; o.keyframe_insert('scale', frame=f0 + dur)

# ---------------- trees ----------------
def make_tree_mesh(kind):
    bm = bmesh.new()
    if kind == 'oak':
        for (x, y, z, r) in [(0, 0, 0.30, 0.17), (0.09, 0.03, 0.24, 0.12), (-0.08, -0.04, 0.25, 0.12), (0.02, -0.08, 0.36, 0.11), (-0.03, 0.08, 0.38, 0.10)]:
            bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r, matrix=__import__('mathutils').Matrix.Translation((x, y, z)))
    else:  # pine: stacked cones
        for i, (z, r) in enumerate([(0.18, 0.15), (0.30, 0.12), (0.42, 0.08)]):
            bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=r, radius2=0.0, depth=0.18, matrix=__import__('mathutils').Matrix.Translation((0, 0, z)))
    me = bpy.data.meshes.new(kind + '_crown'); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me
TREE_MESH = {'oak': make_tree_mesh('oak'), 'pine': make_tree_mesh('pine')}
bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.035, radius2=0.025, depth=0.2, matrix=__import__('mathutils').Matrix.Translation((0, 0, 0.1)))
TRUNK_MESH = bpy.data.meshes.new('trunk'); bm.to_mesh(TRUNK_MESH); bm.free()
TRUNK_MESH.materials.append(M_TRUNK)

trees_col = bpy.data.collections.new('Trees'); sc.collection.children.link(trees_col)
def tree(pos, scale=1.0, kind=None, grow=None):
    kind = kind or random.choice(['oak', 'oak', 'pine'])
    root = bpy.data.objects.new('tree', None); link(root, trees_col)
    root.location = pos; root.rotation_euler = (0, 0, random.uniform(0, 6.28))
    t = bpy.data.objects.new('trunk', TRUNK_MESH); link(t, trees_col); t.parent = root
    c = bpy.data.objects.new('crown', TREE_MESH[kind]); link(c, trees_col); c.parent = root
    c.data.materials.clear() if False else None
    c.active_material = None
    mat = random.choice(M_LEAF)
    if not c.data.materials:
        c.data.materials.append(mat)
    c.material_slots[0].link = 'OBJECT'; c.material_slots[0].material = mat
    s = scale * random.uniform(0.8, 1.25)
    if grow is None:
        root.scale = (s,) * 3
    else:
        pop_in(root, grow, dur=10, s1=s, over=1.12)
    return root

kind_small = layout['kind_small']
def kind_at(u, v):
    return kind_small[min(287, int(v * 288))][min(511, int(u * 512))]

# forests: dense trees inside ellipses
for (fu, fv, fw, fh) in layout['forests']:
    n = int(fw * fh * 9000)
    for _ in range(n):
        a = random.uniform(0, 6.28); r = math.sqrt(random.random())
        u = fu + math.cos(a) * fw * r; v = fv + math.sin(a) * fh * r
        if kind_at(u, v) in (1, 2):
            continue
        tree(UV(u, v), 1.0)
# scattered trees
for _ in range(70):
    u, v = random.uniform(0.04, 0.96), random.uniform(0.05, 0.95)
    if kind_at(u, v) == 0 and abs(u - 0.5) + abs(v - 0.5) > 0.12:
        tree(UV(u, v), 0.8)
# trees that swallow the east road (35.3s -> 37.6s), ordered west to east
road_e = layout['roads']['e']
grow_pts = [p for p in road_e if 0.63 < p[0] < 0.93]
for i, (u, v) in enumerate(grow_pts[::2]):
    for k in range(2):
        uu = u + random.uniform(-0.006, 0.006); vv = v + random.uniform(-0.012, 0.012)
        tree(UV(uu, vv), 0.95, grow=F(35.3 + 2.2 * (uu - 0.63) / 0.30 + random.uniform(0, 0.2)))

# ---------------- mountains ----------------
mu, mv, mw, mh = layout['mountains']
for i in range(9):
    u = mu + random.uniform(-mw, mw) * 0.9; v = mv + random.uniform(-mh, mh) * 0.85
    hgt = random.uniform(0.7, 1.4)
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=hgt * 0.85, radius2=0.04, depth=hgt, location=UV(u, v, hgt / 2 - 0.02))
    mo = bpy.context.object
    bpy.ops.object.shade_smooth()
    mod = mo.modifiers.new('sub', 'SUBSURF'); mod.levels = 2; mod.render_levels = 2
    dm = mo.modifiers.new('disp', 'DISPLACE'); tx = bpy.data.textures.new('mt%d' % i, 'CLOUDS'); tx.noise_scale = 0.4; dm.texture = tx; dm.strength = 0.12
    mo.data.materials.append(M_MOUNT)
    # snow cap
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=hgt * 0.26, radius2=0.02, depth=hgt * 0.3, location=UV(u, v, hgt * 0.86 - 0.02))
    cap = bpy.context.object; bpy.ops.object.shade_smooth(); cap.data.materials.append(M_SNOW)
    cm = cap.modifiers.new('sub', 'SUBSURF'); cm.levels = 1

# ---------------- figurines (game unit portraits) ----------------
cam_data = bpy.data.cameras.new('Cam'); cam = bpy.data.objects.new('Cam', cam_data); link(cam); sc.camera = cam
def portrait_mat(name, path, halo=False):
    m, nt, b = new_mat(name)
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(path); t.interpolation = 'Cubic'
    if halo:
        setin(b, 'Base Color', (0.01, 0.008, 0.006, 1))
    else:
        add_dark(nt, t.outputs['Color'], b)
    nt.links.new(t.outputs['Alpha'], b.inputs['Alpha'])
    setin(b, 'Roughness', 0.8); setin(b, 'Sheen Weight', 0.7)
    tb = nt.nodes.new('ShaderNodeBump'); tb.inputs['Strength'].default_value = 0.35
    bw = nt.nodes.new('ShaderNodeRGBToBW'); nt.links.new(t.outputs['Color'], bw.inputs[0]); nt.links.new(bw.outputs[0], tb.inputs['Height'])
    nt.links.new(tb.outputs[0], b.inputs['Normal'])
    m.blend_method = 'HASHED'; m.shadow_method = 'HASHED'
    return m

def standee(path, pos, h=0.55, halo=True, base=True, name='fig'):
    root = bpy.data.objects.new(name, None); link(root); root.location = pos
    for k, (scale, off, hal) in enumerate([(1.0, 0.0, False), (1.07, 0.008, True)] if halo else [(1.0, 0.0, False)]):
        bpy.ops.mesh.primitive_plane_add(size=1)
        p = bpy.context.object
        im = bpy.data.images.load(path, check_existing=True)
        asp = im.size[0] / im.size[1]
        p.scale = (h * asp * scale, h * scale, 1); p.rotation_euler = (math.pi / 2, 0, 0)
        bpy.ops.object.transform_apply(scale=True, rotation=True)
        p.location = (0, off, h * 0.5 + 0.05 - (h * (scale - 1) * 0.5))
        p.parent = root
        p.data.materials.append(portrait_mat(name + ('_halo' if hal else ''), path, hal))
    if base:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=h * 0.38, depth=0.05, location=(0, 0, 0.025))
        bs = bpy.context.object; bs.parent = root; bs.data.materials.append(M_WOOD)
        bpy.ops.object.shade_smooth()
        bpy.ops.mesh.primitive_torus_add(major_radius=h * 0.38, minor_radius=0.008, location=(0, 0, 0.05))
        rim = bpy.context.object; rim.parent = root; rim.data.materials.append(M_GOLD)
    c = root.constraints.new('LOCKED_TRACK'); c.target = cam; c.track_axis = 'TRACK_NEGATIVE_Y'; c.lock_axis = 'LOCK_Z'
    return root

TEX = D + 'tex/'
FIGS = [
    ('unit_engineer', 0.30, 0.30), ('unit_man_at_arms', 0.38, 0.21), ('unit_knight', 0.24, 0.40),
    ('unit_legionary', 0.66, 0.33), ('unit_spearman', 0.73, 0.40), ('unit_knight', 0.60, 0.18),
    ('unit_mercenary', 0.40, 0.66), ('unit_archer', 0.33, 0.60), ('unit_spearman', 0.44, 0.78),
    ('unit_horse_archer', 0.64, 0.72), ('unit_scout', 0.58, 0.62), ('unit_archer', 0.70, 0.84),
]
figs = []
for i, (n, u, v) in enumerate(FIGS):
    f = standee(TEX + n + '.png', UV(u, v), 0.62, name='fig%d' % i)
    figs.append(f)
    # gentle idle bob, offset per figure
    f0 = 1 + i * 3
    for k in range(0, 480, 24):
        f.location.z = 0.0; f.keyframe_insert('location', index=2, frame=f0 + k)
        f.location.z = 0.035; f.keyframe_insert('location', index=2, frame=f0 + k + 12)
# figures turn their backs on each other at "forgot what lay beyond" (38.3s)? keep facing camera.

# ---------------- realm banners ----------------
def banner(crest, cloth_rgb, pos, height=1.6, w=0.62, rise=None, name='banner', crest_path=True):
    root = bpy.data.objects.new(name, None); link(root); root.location = pos
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.022, depth=height, location=(0, 0, height / 2))
    pole = bpy.context.object; pole.parent = root; pole.data.materials.append(M_GOLD)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(0, 0, height + 0.03)); fin = bpy.context.object; fin.parent = root; fin.data.materials.append(M_GOLD)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.012, depth=w + 0.1, location=(w / 2, 0, height - 0.03), rotation=(0, math.pi / 2, 0))
    bar = bpy.context.object; bar.parent = root; bar.data.materials.append(M_GOLD)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=24, y_subdivisions=30, size=1)
    cl = bpy.context.object
    cl.scale = (w, w * 1.35, 1); cl.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    cl.location = (w / 2 + 0.02, 0, height - 0.05 - w * 0.675)
    cl.parent = root
    wv = cl.modifiers.new('wave', 'WAVE'); wv.use_normal = False; wv.use_y = False; wv.use_x = True
    wv.height = 0.035; wv.width = 0.35; wv.speed = 0.06; wv.narrowness = 1.2; wv.start_position_x = -0.3
    wv.use_normal = True
    cl.modifiers.new('sub', 'SUBSURF').levels = 1
    m, nt, b = new_mat(name + '_cloth')
    base = nt.nodes.new('ShaderNodeRGB'); base.outputs[0].default_value = cloth_rgb
    out_col = base.outputs[0]
    if crest:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(crest); t.extension = 'CLIP'
        mapn = nt.nodes.new('ShaderNodeMapping'); mapn.inputs['Scale'].default_value = (1.25, 0.93, 1); mapn.inputs['Location'].default_value = (-0.12, 0.02, 0)
        tc = nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(tc.outputs['UV'], mapn.inputs[0]); nt.links.new(mapn.outputs[0], t.inputs[0])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        nt.links.new(t.outputs['Alpha'], mx.inputs['Factor']); nt.links.new(base.outputs[0], mx.inputs[6]); nt.links.new(t.outputs['Color'], mx.inputs[7])
        out_col = mx.outputs[2]
    # gold border via UV distance
    tc2 = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc2.outputs['UV'], sep.inputs[0])
    def edge(socket):
        a = nt.nodes.new('ShaderNodeMath'); a.operation = 'PINGPONG'; a.inputs[1].default_value = 0.5; nt.links.new(socket, a.inputs[0]); return a
    ex, ey = edge(sep.outputs[0]), edge(sep.outputs[1])
    mn = nt.nodes.new('ShaderNodeMath'); mn.operation = 'MINIMUM'; nt.links.new(ex.outputs[0], mn.inputs[0]); nt.links.new(ey.outputs[0], mn.inputs[1])
    lt = nt.nodes.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 0.045; nt.links.new(mn.outputs[0], lt.inputs[0])
    mg = nt.nodes.new('ShaderNodeMix'); mg.data_type = 'RGBA'; mg.inputs[7].default_value = (0.8, 0.56, 0.18, 1)
    nt.links.new(lt.outputs[0], mg.inputs['Factor']); nt.links.new(out_col, mg.inputs[6])
    add_dark(nt, mg.outputs[2], b)
    noise = nt.nodes.new('ShaderNodeTexWave'); noise.inputs['Scale'].default_value = 90; bumpn = nt.nodes.new('ShaderNodeBump'); bumpn.inputs['Strength'].default_value = 0.25
    nt.links.new(noise.outputs['Fac'], bumpn.inputs['Height']); nt.links.new(bumpn.outputs[0], b.inputs['Normal'])
    setin(b, 'Roughness', 0.85); setin(b, 'Sheen Weight', 0.9)
    cl.data.materials.append(m)
    # base
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.12, depth=0.06, location=(0, 0, 0.03)); bb = bpy.context.object; bb.parent = root; bb.data.materials.append(M_WOOD)
    if rise is not None:
        root.location.z = -height - 0.2; root.keyframe_insert('location', index=2, frame=1)
        root.keyframe_insert('location', index=2, frame=rise)
        root.location.z = 0.0; root.keyframe_insert('location', index=2, frame=rise + 16)
    return root

REALMS = [('crest_builders', (0.55, 0.36, 0.06, 1), 0.22, 0.27), ('crest_legion', (0.42, 0.05, 0.04, 1), 0.78, 0.36),
          ('crest_merchants', (0.06, 0.13, 0.42, 1), 0.36, 0.71), ('crest_nomads', (0.05, 0.26, 0.12, 1), 0.70, 0.62)]
for i, (c, rgb, u, v) in enumerate(REALMS):
    banner(TEX + c + '.png', rgb, UV(u, v), 1.55, 0.6, rise=F(46.3 + i * 0.5), name='realm%d' % i)

# "One banner": cream banner dropped into the centre at 51.1s
ob = banner(None, (0.80, 0.72, 0.56, 1), UV(0.5, 0.5), 1.25, 0.5, name='onebanner')
ob.location.z = 14.0; ob.keyframe_insert('location', index=2, frame=1); ob.keyframe_insert('location', index=2, frame=F(50.85))
ob.location.z = -0.06; ob.keyframe_insert('location', index=2, frame=F(51.2))
ob.location.z = 0.0; ob.keyframe_insert('location', index=2, frame=F(51.45))

# ---------------- village (pops at 52.3s) ----------------
def house(pos, rot, w, d, h, roofm, f0):
    root = bpy.data.objects.new('house', None); link(root); root.location = pos; root.rotation_euler = (0, 0, rot)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, h / 2)); wb = bpy.context.object; wb.scale = (w, d, h); wb.parent = root; wb.data.materials.append(M_WALL)
    bv = wb.modifiers.new('bev', 'BEVEL'); bv.width = 0.012; bv.segments = 2
    hw, hd, rh = w * 0.58, d * 0.62, d * 0.55
    verts = [(-hw, -hd, h), (hw, -hd, h), (hw, hd, h), (-hw, hd, h), (-hw, 0, h + rh), (hw, 0, h + rh)]
    faces = [(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)]
    rme = bpy.data.meshes.new('roof'); rme.from_pydata(verts, [], faces); rme.update()
    rf = bpy.data.objects.new('roof', rme); link(rf); rf.parent = root; rf.data.materials.append(roofm)
    bv2 = rf.modifiers.new('bev', 'BEVEL'); bv2.width = 0.01; bv2.segments = 2
    # door
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -d / 2 - 0.002, h * 0.3)); dr = bpy.context.object; dr.scale = (w * 0.18, 0.01, h * 0.55); dr.parent = root; dr.data.materials.append(M_WOOD)
    pop_in(root, f0, dur=9)
    return root
vill = [(0.475, 0.465, 0.3), (0.53, 0.462, -0.2), (0.455, 0.53, 0.5), (0.545, 0.535, -0.4), (0.50, 0.565, 0.1), (0.425, 0.50, 1.4), (0.578, 0.50, -1.3), (0.505, 0.43, 0.0)]
for i, (u, v, r) in enumerate(vill):
    house(UV(u, v), r, random.uniform(0.24, 0.32), random.uniform(0.2, 0.26), random.uniform(0.16, 0.22), random.choice(M_ROOFS), F(52.25 + i * 0.09))

# ---------------- dark quilted clouds creeping from the edges (41.8s ->) ----------------
def cloud_mat(path):
    m, nt, b = new_mat('cloud_' + path.split('/')[-1])
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(path)
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
    mx.inputs[7].default_value = (0.035, 0.035, 0.06, 1)
    nt.links.new(t.outputs['Color'], mx.inputs[6]); nt.links.new(mx.outputs[2], b.inputs['Base Color'])
    nt.links.new(mx.outputs[2], b.inputs['Sheen Tint'])
    nt.links.new(t.outputs['Alpha'], b.inputs['Alpha'])
    bw = nt.nodes.new('ShaderNodeRGBToBW'); bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.6
    nt.links.new(t.outputs['Color'], bw.inputs[0]); nt.links.new(bw.outputs[0], bp.inputs['Height']); nt.links.new(bp.outputs[0], b.inputs['Normal'])
    setin(b, 'Roughness', 0.9); setin(b, 'Sheen Weight', 0.5)
    m.blend_method = 'HASHED'; m.shadow_method = 'HASHED'
    return m
CLOUDM = [cloud_mat(TEX + 'cloud_puff_%d.png' % i) for i in range(1, 9)]
for i in range(46):
    # positions along the map perimeter
    side = i % 4; s = random.uniform(-1, 1)
    if side == 0: x, y = s * MAPW / 2, MAPH / 2 + random.uniform(-0.3, 0.5)
    elif side == 1: x, y = s * MAPW / 2, -MAPH / 2 - random.uniform(-0.3, 0.5)
    elif side == 2: x, y = -MAPW / 2 - random.uniform(-0.3, 0.5), s * MAPH / 2
    else: x, y = MAPW / 2 + random.uniform(-0.3, 0.5), s * MAPH / 2
    bpy.ops.mesh.primitive_plane_add(size=1)
    c = bpy.context.object
    sz = random.uniform(1.4, 2.4)
    c.scale = (sz, sz * 0.7, 1); c.rotation_euler = (0, 0, random.uniform(-0.4, 0.4))
    c.data.materials.append(random.choice(CLOUDM))
    inward = Vector((-x, -y, 0)).normalized()
    start = Vector((x, y, 0.06 + i * 0.002)) - inward * 2.2
    end = Vector((x, y, 0.06 + i * 0.002)) + inward * random.uniform(0.2, 1.4)
    c.location = start; c.keyframe_insert('location', frame=F(41.6 + random.uniform(0, 0.8)))
    c.location = end; c.keyframe_insert('location', frame=F(45.0 + random.uniform(0, 1.0)))

# edge-darkness threshold keyframes (view-layer custom property)
thv = EDGE.nodes['THR'].outputs[0]
for fr, val in [(1, 1.6), (F(41.7), 1.6), (F(45.2), 0.84), (F(54.4), 0.80)]:
    thv.default_value = val; thv.keyframe_insert('default_value', frame=fr)

# ---------------- lights ----------------
sun_d = bpy.data.lights.new('Sun', 'SUN'); sun_d.energy = 3.2; sun_d.color = (1.0, 0.86, 0.66); sun_d.angle = math.radians(4)
sun = bpy.data.objects.new('Sun', sun_d); link(sun); sun.rotation_euler = (math.radians(58), 0, math.radians(-38))
fill_d = bpy.data.lights.new('Fill', 'AREA'); fill_d.energy = 900; fill_d.use_shadow = False; fill_d.size = 10; fill_d.color = (0.55, 0.65, 1.0)
fill = bpy.data.objects.new('Fill', fill_d); link(fill); fill.location = (-6, 8, 9); fill.rotation_euler = (math.radians(-40), math.radians(-30), 0)
for (x, y) in [(-9, -5.5), (9, -5.5), (-9, 5.5), (9, 5.5)]:
    cd = bpy.data.lights.new('Candle', 'POINT'); cd.energy = 110; cd.use_shadow = False; cd.color = (1.0, 0.62, 0.30); cd.shadow_soft_size = 0.4
    co = bpy.data.objects.new('Candle', cd); link(co); co.location = (x, y, 1.6)

# ---------------- camera ----------------
cam_data.lens = 32; cam_data.sensor_width = 36
cam_data.dof.use_dof = True; cam_data.dof.aperture_fstop = 1.4
focus = bpy.data.objects.new('Focus', None); link(focus); cam_data.dof.focus_object = focus
aim = bpy.data.objects.new('Aim', None); link(aim)
tc = cam.constraints.new('TRACK_TO'); tc.target = aim; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'

def shot(t, cam_pos, aim_pos, focus_pos=None, lens=None, fstop=None):
    f = F(t)
    cam.location = cam_pos; cam.keyframe_insert('location', frame=f)
    aim.location = aim_pos; aim.keyframe_insert('location', frame=f)
    focus.location = focus_pos or aim_pos; focus.keyframe_insert('location', frame=f)
    if lens:
        cam_data.lens = lens; cam_data.keyframe_insert('lens', frame=f)
    if fstop:
        cam_data.dof.aperture_fstop = fstop; cam_data.dof.keyframe_insert('aperture_fstop', frame=f)

# A: low along the east road while the forest swallows it
r0, r1 = UV(0.60, 0.53), UV(0.88, 0.585)
shot(35.0, r0 + Vector((-0.4, -1.9, 1.35)), r0 + Vector((1.5, 0.15, 0.0)), r0 + Vector((1.3, 0.0, 0.0)), 26, 2.4)
shot(37.7, r0 + Vector((1.6, -2.0, 1.55)), r1 + Vector((-0.4, 0.1, 0.0)), r0 + Vector((2.9, 0.1, 0.0)), 26, 2.4)
# B: rise and pull back to the whole map
shot(40.2, Vector((3.0, -6.0, 4.2)), Vector((0.6, 0.2, 0)), Vector((0.6, 0.0, 0)), 28, 3.0)
shot(42.0, Vector((0.6, -9.6, 8.6)), Vector((0.0, 0.3, 0)), Vector((0.0, -0.4, 0)), 30, 5.6)
shot(45.4, Vector((-0.4, -9.0, 8.0)), Vector((0.0, 0.3, 0)), Vector((0.0, -0.3, 0)), 30, 5.6)
# C: slow orbit while realm banners rise
shot(47.0, Vector((-4.6, -7.4, 5.6)), Vector((0.0, 0.2, 0.4)), Vector((-0.6, -0.4, 0.4)), 32, 4.0)
shot(50.2, Vector((-1.6, -5.6, 3.4)), Vector((0.0, 0.0, 0.5)), Vector((0.0, 0.0, 0.4)), 34, 3.0)
# D: push into the centre: one banner, one village
shot(51.2, Vector((-0.6, -3.4, 1.9)), UV(0.5, 0.5, 0.7), UV(0.5, 0.5, 0.4), 36, 2.2)
shot(53.0, Vector((0.25, -2.4, 1.35)), UV(0.5, 0.5, 0.55), UV(0.5, 0.5, 0.3), 36, 2.0)
shot(54.4, Vector((0.35, -1.6, 1.05)), UV(0.5, 0.5, 0.75), UV(0.5, 0.5, 0.6), 36, 2.0)

for o in (cam, aim, focus):
    if o.animation_data and o.animation_data.action:
        for fc in o.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'
                kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'

bpy.ops.wm.save_as_mainfile(filepath=D + 'map_scene.blend')

out = arg('--out', D + 'render/')
test = arg('--test', '')
sc.render.filepath = out + 'f_'
if test:
    for fr in [int(x) for x in test.split(',')]:
        sc.frame_set(fr)
        sc.render.filepath = out + 'test_%04d.jpg' % fr
        bpy.ops.render.render(write_still=True)
elif '--anim' in args:
    sc.frame_start = int(arg('--from', 1)); sc.frame_end = int(arg('--to', sc.frame_end))
    sc.render.filepath = out + 'f_####'
    bpy.ops.render.render(animation=True)
print('DONE')
