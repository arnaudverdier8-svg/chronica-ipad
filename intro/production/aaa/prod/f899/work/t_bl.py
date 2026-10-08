import bpy, sys, os
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
print('ENGINES', [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items])
sc.render.engine='BLENDER_EEVEE'
print(sc.eevee.bl_rna.properties.keys()[:60])
import numpy; print('numpy', numpy.__version__)
try:
    import cv2; print('cv2', cv2.__version__)
except Exception as e: print('nocv2', e)
