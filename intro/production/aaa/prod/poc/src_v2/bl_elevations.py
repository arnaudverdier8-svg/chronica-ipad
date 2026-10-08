"""Blender 4.0.2 (workbench): front-elevation material-ID renders of the game OBJs used as stitched icons.
xvfb-run -a -s "-screen 0 1920x1080x24" blender -b --factory-startup -P bl_elevations.py -- OUTDIR model1 model2 ..."""
import bpy, sys, json, os, math
argv = sys.argv[sys.argv.index('--') + 1:]
OUT, models = argv[0], argv[1:]
MOD = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/assets/models'
PPU = 330.0  # px per game unit (2x of 6 px/mm * 27.5 mm)
for name in models:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    bpy.ops.wm.obj_import(filepath=f'{MOD}/{name}.obj', forward_axis='NEGATIVE_Z', up_axis='Y')
    obs = [o for o in sc.objects if o.type == 'MESH']
    mats = []
    for o in obs:
        for s in o.material_slots:
            if s.material and s.material.name.split('.')[0] not in mats: mats.append(s.material.name.split('.')[0])
    # unique ID colour per material
    ids = {}
    for i, mn in enumerate(mats):
        c = ((i + 1) * 37 % 251 / 255.0, (i + 1) * 91 % 241 / 255.0, (i + 1) * 157 % 239 / 255.0)
        ids[mn] = [round(v * 255) for v in c]
    for m in bpy.data.materials:
        b = m.name.split('.')[0]
        if b in ids: m.diffuse_color = (ids[b][0] / 255, ids[b][1] / 255, ids[b][2] / 255, 1)
    xs = [(o.matrix_world @ v.co) for o in obs for v in o.data.vertices]
    xmin, xmax = min(v.x for v in xs), max(v.x for v in xs)
    zmin, zmax = min(v.z for v in xs), max(v.z for v in xs)
    ymin, ymax = min(v.y for v in xs), max(v.y for v in xs)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'
    w, h = xmax - xmin, zmax - zmin
    rw, rh = int(math.ceil(w * PPU)) + 8, int(math.ceil(h * PPU)) + 8
    cam.data.ortho_scale = max(rw, rh) / PPU
    cam.location = ((xmin + xmax) / 2, ymin - 10, (zmin + zmax) / 2)
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.clip_end = 100
    sc.render.resolution_x, sc.render.resolution_y = rw, rh
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'FLAT'; sc.display.shading.color_type = 'MATERIAL'
    sc.display.render_aa = 'OFF'
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.render.filepath = f'{OUT}/{name}_id.png'
    bpy.ops.render.render(write_still=True)
    # game coords: Blender x = gx, Blender y = -gz, z = gy
    json.dump(dict(model=name, ppu=PPU, ids=ids, w_px=rw, h_px=rh, x_min=xmin, x_max=xmax, y_max=zmax,
                   gz_front=-ymin, gz_back=-ymax, cx_px=((xmin + xmax) / 2), center_note='image centre = bbox centre'),
              open(f'{OUT}/{name}_id.json', 'w'), indent=1)
    print('done', name, rw, rh, mats)
