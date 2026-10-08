import bpy, sys, os, math
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=640; sc.render.resolution_y=360
sc.eevee.taa_render_samples=8
sc.view_settings.view_transform='Standard'
# plane
bpy.ops.mesh.primitive_plane_add(size=1000)
pl=bpy.context.object
m=bpy.data.materials.new('w'); m.use_nodes=True
b=m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value=(1,1,1,1); b.inputs['Specular IOR Level'].default_value=0.0; b.inputs['Roughness'].default_value=1
pl.data.materials.append(m)
# sun straight down, strength 1
bpy.ops.object.light_add(type='SUN'); s=bpy.context.object; s.data.energy=1.0; s.rotation_euler=(0,0,0)
# camera top-down
cam=bpy.data.cameras.new('c'); co=bpy.data.objects.new('c',cam); sc.collection.objects.link(co); sc.camera=co
co.location=(0,0,500); co.rotation_euler=(0,0,0)
sc.world=bpy.data.worlds.new('w'); sc.world.use_nodes=True; sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.0
sc.use_nodes=True
nt=sc.node_tree; N=nt.nodes; L=nt.links
for n in list(N): N.remove(n)
rl=N.new('CompositorNodeRLayers'); fo=N.new('CompositorNodeOutputFile')
fo.base_path=os.path.abspath('work/t'); fo.format.file_format='OPEN_EXR'; fo.format.color_depth='32'
fo.file_slots[0].path='cal_img_'
sc.view_layers[0].use_pass_z=True
fo.file_slots.new('cal_z_')
L.new(rl.outputs['Image'],fo.inputs[0]); L.new(rl.outputs['Depth'],fo.inputs[1])
sc.frame_set(1)
bpy.ops.render.render(write_still=False)
print('DONE')
