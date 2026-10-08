import bpy
sc=bpy.context.scene
print('engines',[i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items])
print('eevee props',[p.identifier for p in sc.eevee.bl_rna.properties][:200])
m=bpy.data.materials.new('x'); m.use_nodes=True
b=m.node_tree.nodes['Principled BSDF']; print('bsdf inputs',[i.name for i in b.inputs])
print('mat props',[p.identifier for p in m.bl_rna.properties if 'displace' in p.identifier or 'blend' in p.identifier or 'surface' in p.identifier or 'shadow' in p.identifier or 'thick' in p.identifier])
ld=bpy.data.lights.new('s','SUN'); print('light props',[p.identifier for p in ld.bl_rna.properties])
print(hasattr(bpy.data,'hair_curves'))
