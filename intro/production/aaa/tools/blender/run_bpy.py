# run bench_scene.py inside the bpy module: python run_bpy.py ENGINE W H S FS FE OUT [SUB]
import sys, os
sys.argv = [sys.argv[0], '--'] + sys.argv[1:]
import bpy
exec(compile(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bench_scene.py')).read(), 'bench_scene.py', 'exec'))
