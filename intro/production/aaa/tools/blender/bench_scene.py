# Usage: blender -b -P bench_scene.py -- ENGINE W H SAMPLES F_START F_END OUTPREFIX [SUBDIV]
import bpy, sys, time, math, os
argv = sys.argv[sys.argv.index('--')+1:]
engine, W, H, S, FS, FE, OUT = argv[0], int(argv[1]), int(argv[2]), int(argv[3]), int(argv[4]), int(argv[5]), argv[6]
SUB = int(argv[7]) if len(argv) > 7 else 1024
t0 = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
# --- geometry: SUBxSUB grid, displaced by a high-frequency procedural texture
bpy.ops.mesh.primitive_grid_add(x_subdivisions=SUB, y_subdivisions=SUB, size=10)
plane = bpy.context.active_object
tex = bpy.data.textures.new('hf', type='CLOUDS'); tex.noise_scale = 0.05; tex.noise_depth = 4
mod = plane.modifiers.new('disp', 'DISPLACE'); mod.texture = tex; mod.strength = 0.25; mod.mid_level = 0.5
bpy.ops.object.shade_smooth()
# --- material: principled with noise-driven colour/roughness + bump
mat = bpy.data.materials.new('wool'); mat.use_nodes = True
nt = mat.node_tree; bsdf = nt.nodes['Principled BSDF']
noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 80; noise.inputs['Detail'].default_value = 6
ramp = nt.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.45, 0.12, 0.06, 1); ramp.color_ramp.elements[1].color = (0.85, 0.72, 0.45, 1)
bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.6
nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
nt.links.new(noise.outputs['Fac'], bump.inputs['Height'])
nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
bsdf.inputs['Roughness'].default_value = 0.8
plane.data.materials.append(mat)
# --- light: sun with soft shadows
ld = bpy.data.lights.new('sun', 'SUN'); ld.energy = 4; ld.angle = math.radians(6)
sun = bpy.data.objects.new('sun', ld); sc.collection.objects.link(sun); sun.rotation_euler = (math.radians(50), 0, math.radians(30))
# --- world
w = bpy.data.worlds.new('w'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.05, 0.05, 0.07, 1); sc.world = w
# --- camera animated (dolly) so every frame is a "real" frame
cd = bpy.data.cameras.new('cam'); cd.lens = 35
cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0, -7, 4); cam.rotation_euler = (math.radians(60), 0, 0); cam.keyframe_insert('location', frame=1)
cam.location = (1.5, -5, 3); cam.keyframe_insert('location', frame=60)
# --- render settings
sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
sc.render.fps = 30; sc.frame_start = FS; sc.frame_end = FE
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
sc.render.filepath = OUT
if engine == 'EEVEE':
    engines = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines else 'BLENDER_EEVEE'
    e = sc.eevee; e.taa_render_samples = S
    for k, v in [('use_gtao', True), ('gtao_distance', 0.5), ('use_soft_shadows', True), ('shadow_cascade_size', '2048')]:
        if hasattr(e, k): setattr(e, k, v)
    if hasattr(ld, 'use_soft_shadows'): pass
    print('BENCH engine', sc.render.engine, bpy.app.version_string, flush=True)
else:
    sc.render.engine = 'CYCLES'
    c = sc.cycles; c.device = 'CPU'; c.samples = S; c.use_adaptive_sampling = False
    c.use_denoising = bool(os.environ.get('DENOISE'))
    if c.use_denoising: c.denoiser = 'OPENIMAGEDENOISE'; c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    print('BENCH engine CYCLES', bpy.app.version_string, 'denoise', c.use_denoising, flush=True)
    sc.render.threads_mode = 'AUTO'
import os
if os.environ.get('SEED'): sc.cycles.seed = int(os.environ['SEED'])
if os.environ.get('BORDER'):
    x0,y0,x1,y1 = map(float, os.environ['BORDER'].split(','))
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_min_y, sc.render.border_max_x, sc.render.border_max_y = x0,y0,x1,y1
if os.environ.get('FLAT'):   # flat-shaded variant: no displacement, low-frequency colour -> noise is visible
    plane.modifiers.remove(mod); noise.inputs['Scale'].default_value = 3; bump.inputs['Strength'].default_value = 0.0
if os.environ.get('SOFT'):   # low-frequency variant: gentle relief, low-freq colour, bright sky -> MC noise dominates
    tex.noise_scale = 0.6; mod.strength = 0.3; noise.inputs['Scale'].default_value = 3; bump.inputs['Strength'].default_value = 0.1
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.4, 0.45, 0.55, 1); ld.angle = math.radians(25)
if os.environ.get('EXR'):
    sc.render.image_settings.file_format = 'OPEN_EXR_MULTILAYER'; sc.render.image_settings.color_depth = '32'
    if engine != 'EEVEE':
        try: sc.view_layers[0].cycles.denoising_store_passes = True
        except Exception as ex: print('BENCH no denoising passes', ex)
print(f'BENCH setup {time.time()-t0:.2f}s verts={len(plane.data.vertices)}', flush=True)
ft = {}
def pre(s, *a): ft['t'] = time.time()
def post(s, *a): print(f'BENCH frame {s.frame_current} {time.time()-ft["t"]:.2f}s', flush=True)
bpy.app.handlers.render_pre.append(pre); bpy.app.handlers.render_post.append(post)
t1 = time.time()
bpy.ops.render.render(animation=True)
print(f'BENCH total_render {time.time()-t1:.2f}s wall_total {time.time()-t0:.2f}s', flush=True)
