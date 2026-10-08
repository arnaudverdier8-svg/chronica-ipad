"""look-dev daemon: builds the shot assets once, then executes work/v3/cmd_*.py files as they appear (modules threads3d / loose /
touchup / crown are reloaded before each one).  Each command may call R(...) for a cached-base re-render of a window.
Start:  nice -n 5 python3 devd.py &     Send:  write work/v3/cmd_007.py  ->  work/v3/cmd_007.done (or .err) appears."""
import os, sys, time, glob, importlib, traceback
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
import shot
W = os.path.join(HERE, '..', 'work', 'v3')
shot.assets()
print('[devd] ready', flush=True)
done = set()
G = dict(np=np, cv2=cv2, shot=shot, W=W, os=os)


def R(f=669, out_wh=(1280, 720), cx=300, cy=232, cache=None, mode='load', fuzz=True, level=0, **kw):
    s = shot.view_of(f)['px_per_mm']
    shot.VIEW_OVERRIDE = dict(cx_mm=cx, cy_mm=cy, px_per_mm=s)
    if cache:
        p = os.path.join(W, cache)
        os.environ['F669_CACHE'] = p
        os.environ['F669_CACHE_MODE'] = 'load' if (mode == 'load' and os.path.exists(p)) else 'save'
    else:
        os.environ.pop('F669_CACHE', None); os.environ.pop('F669_CACHE_MODE', None)
    t = time.time()
    r = shot.render_frame(f, out_wh=out_wh, level=level, threads=True, free_tiles=True, fuzz=fuzz, **kw)
    print('  render %.1fs' % (time.time() - t), flush=True)
    return r


G['R'] = R
while True:
    for c in sorted(glob.glob(os.path.join(W, 'cmd_*.py'))):
        if c in done: continue
        done.add(c)
        import ast
        tree = ast.parse(open(os.path.join(HERE, 'shot.py')).read())
        for node in tree.body:                      # hot-reload the functions of shot.py (module state such as _ASSETS is kept)
            if isinstance(node, ast.FunctionDef) and node.name not in ('assets',):
                exec(compile(ast.Module([node], []), 'shot.py', 'exec'), shot.__dict__)
        for mn in ('threads3d', 'loose', 'touchup', 'crown', 'voidfx'):
            try:
                mod = importlib.reload(sys.modules[mn])
            except Exception:
                traceback.print_exc()
        import threads3d, loose, touchup
        shot.ThreadSet = threads3d.ThreadSet
        shot.TU = touchup
        A = shot._ASSETS
        A['loose'].__class__ = loose.LooseEnds
        shot.LooseEnds = loose.LooseEnds
        try:
            exec(compile(open(c).read(), c, 'exec'), G)
            open(c[:-3] + '.done', 'w').write('ok')
        except Exception:
            open(c[:-3] + '.err', 'w').write(traceback.format_exc())
            traceback.print_exc()
        sys.stdout.flush()
    time.sleep(0.4)
