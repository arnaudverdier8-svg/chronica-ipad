# Probe Geometry Nodes features in Blender 4.0.2 relevant to procedural embroidery threads.
# blender -b --factory-startup -P gn_probe.py -- OUT.png
import bpy, sys, time, math
OUT = sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
# list every geometry node type available
types = sorted({n for n in dir(bpy.types) if n.startswith('GeometryNode')})
want = ['GeometryNodeCurveToMesh','GeometryNodeInstanceOnPoints','GeometryNodeRepeatInput','GeometryNodeRepeatOutput',
        'GeometryNodeSampleCurve','GeometryNodeSimulationInput','GeometryNodeResampleCurve','GeometryNodeCurvePrimitiveLine',
        'GeometryNodeCurvePrimitiveCircle','GeometryNodeSetCurveRadius','GeometryNodeRealizeInstances','GeometryNodeTrimCurve',
        'GeometryNodeMeshToCurve','GeometryNodeSetPosition','GeometryNodeStoreNamedAttribute','GeometryNodeDistributePointsOnFaces',
        'GeometryNodeSampleIndex','GeometryNodeIndexOfNearest','GeometryNodeCurveSpiral','GeometryNodeFilletCurve',
        'GeometryNodeInputImage','GeometryNodeImageTexture','GeometryNodeImageInfo','GeometryNodeBake','GeometryNodeIndexSwitch',
        'GeometryNodePoints','GeometryNodeCurveOfPoint','GeometryNodePointsToCurves','GeometryNodeSetCurveTilt','GeometryNodeSplineParameter',
        'GeometryNodeTranslateInstances','GeometryNodeRotateInstances','GeometryNodeScaleInstances','GeometryNodeMeshLine','GeometryNodeMeshGrid']
print('GNPROBE total GeometryNode* types:', len(types))
for w in want: print('GNPROBE', w, 'YES' if w in types else 'NO')

ng = bpy.data.node_groups.new('threads', 'GeometryNodeTree')
ng.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
ng.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
N = ng.nodes; L = ng.links.new
gin = N.new('NodeGroupInput'); gout = N.new('NodeGroupOutput')
# --- one "stitch" curve: line resampled, then a Repeat zone that adds iterative wobble (thread twist)
line = N.new('GeometryNodeCurvePrimitiveLine'); line.inputs['End'].default_value = (0.0, 0.0, 0.0)
line.inputs['Start'].default_value = (-0.5, 0, 0); line.inputs['End'].default_value = (0.5, 0, 0)
res = N.new('GeometryNodeResampleCurve'); res.inputs['Count'].default_value = 24
L(line.outputs['Curve'], res.inputs['Curve'])
rin = N.new('GeometryNodeRepeatInput'); rout = N.new('GeometryNodeRepeatOutput'); rin.pair_with_output(rout)
rin.inputs['Iterations'].default_value = 4
L(res.outputs['Curve'], rin.inputs['Geometry'])
setp = N.new('GeometryNodeSetPosition'); noise = N.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 3
vm = N.new('ShaderNodeVectorMath'); vm.operation = 'SCALE'; vm.inputs['Scale'].default_value = 0.01
sub = N.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = (0.5, 0.5, 0.5)
L(noise.outputs['Color'], sub.inputs[0]); L(sub.outputs['Vector'], vm.inputs[0]); L(vm.outputs['Vector'], setp.inputs['Offset'])
L(rin.outputs['Geometry'], setp.inputs['Geometry']); L(setp.outputs['Geometry'], rout.inputs['Geometry'])
# arc the stitch (raise middle) using spline parameter
sp = N.new('GeometryNodeSplineParameter'); m = N.new('ShaderNodeMath'); m.operation = 'PINGPONG'; m.inputs[1].default_value = 0.5
m2 = N.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; m2.inputs[1].default_value = 0.12
cxyz = N.new('ShaderNodeCombineXYZ'); setz = N.new('GeometryNodeSetPosition')
L(sp.outputs['Factor'], m.inputs[0]); L(m.outputs['Value'], m2.inputs[0]); L(m2.outputs['Value'], cxyz.inputs['Z']); L(cxyz.outputs['Vector'], setz.inputs['Offset'])
L(rout.outputs['Geometry'], setz.inputs['Geometry'])
# --- Curve to Mesh with a small circle profile -> wool thread tube
prof = N.new('GeometryNodeCurvePrimitiveCircle'); prof.inputs['Resolution'].default_value = 6; prof.inputs['Radius'].default_value = 0.035
c2m = N.new('GeometryNodeCurveToMesh'); L(setz.outputs['Geometry'], c2m.inputs['Curve']); L(prof.outputs['Curve'], c2m.inputs['Profile Curve'])
# --- guide path: a spiral; Sample Curve gives positions/tangents; we instead resample to points and Instance on Points
spiral = N.new('GeometryNodeCurveSpiral'); spiral.inputs['Rotations'].default_value = 3; spiral.inputs['Start Radius'].default_value = 1
spiral.inputs['End Radius'].default_value = 3; spiral.inputs['Height'].default_value = 0
rs2 = N.new('GeometryNodeResampleCurve'); rs2.inputs['Count'].default_value = 160; L(spiral.outputs['Curve'], rs2.inputs['Curve'])
c2p = N.new('GeometryNodeCurveToPoints'); c2p.mode = 'EVALUATED'; L(rs2.outputs['Curve'], c2p.inputs['Curve'])
iop = N.new('GeometryNodeInstanceOnPoints'); L(c2p.outputs['Points'], iop.inputs['Points']); L(c2m.outputs['Mesh'], iop.inputs['Instance'])
# rotate stitches across the path: Align to tangent -> use rotation output of Curve to Points, plus 90deg about Z
L(c2p.outputs['Rotation'], iop.inputs['Rotation'])
# --- Sample Curve: place a marker at 50% along the spiral (proves Sample Curve)
scv = N.new('GeometryNodeSampleCurve'); scv.mode = 'FACTOR'; L(spiral.outputs['Curve'], scv.inputs['Curves'])
scv.inputs['Factor'].default_value = 0.5
ico = N.new('GeometryNodeMeshIcoSphere'); ico.inputs['Radius'].default_value = 0.2
tr = N.new('GeometryNodeTransform'); L(ico.outputs['Mesh'], tr.inputs['Geometry']); L(scv.outputs['Position'], tr.inputs['Translation'])
real = N.new('GeometryNodeRealizeInstances'); L(iop.outputs['Instances'], real.inputs['Geometry'])
join = N.new('GeometryNodeJoinGeometry'); L(real.outputs['Geometry'], join.inputs['Geometry']); L(tr.outputs['Geometry'], join.inputs['Geometry'])
L(join.outputs['Geometry'], gout.inputs['Geometry'])
# host object
me = bpy.data.meshes.new('host'); ob = bpy.data.objects.new('threads', me); sc.collection.objects.link(ob)
mod = ob.modifiers.new('gn', 'NODES'); mod.node_group = ng
t = time.time(); dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg); m = ev.to_mesh()
print(f'GNPROBE evaluated verts={len(m.vertices)} faces={len(m.polygons)} in {time.time()-t:.3f}s')
ev.to_mesh_clear()
# quick Eevee preview render 640x360
mat = bpy.data.materials.new('wool'); mat.use_nodes = True; mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.55, 0.12, 0.05, 1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
sm = N.new('GeometryNodeSetMaterial'); sm.inputs['Material'].default_value = mat
ng.links.new(join.outputs['Geometry'], sm.inputs['Geometry']); ng.links.new(sm.outputs['Geometry'], gout.inputs['Geometry'])
ld = bpy.data.lights.new('sun', 'SUN'); ld.energy = 4; ld.angle = 0.1; so = bpy.data.objects.new('sun', ld); sc.collection.objects.link(so); so.rotation_euler = (0.7, 0.2, 0.5)
w = bpy.data.worlds.new('w'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.75, 0.68, 0.52, 1); sc.world = w
cd = bpy.data.cameras.new('c'); cd.type = 'ORTHO'; cd.ortho_scale = 8.5; co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); co.location = (0, 0, 10); sc.camera = co
sc.render.engine = 'BLENDER_EEVEE'; sc.eevee.taa_render_samples = 8; sc.eevee.use_gtao = True; sc.eevee.use_soft_shadows = True
sc.render.resolution_x = 640; sc.render.resolution_y = 360; sc.render.filepath = OUT
t = time.time(); bpy.ops.render.render(write_still=True); print(f'GNPROBE render {time.time()-t:.2f}s')
