"""f1319 (S18 'edges') keyframe: full pipeline.  usage: render_f1319.py PX tag"""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from world import *
from thread_gold import paint_gold
from threads import gen_threads, gen_stray, draw_threads
from quilts import make_quilt, place_quilt
from post import glint_point, add_glint, bloom
import layout

PX = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
tag = sys.argv[2] if len(sys.argv) > 2 else 'v7'
EXPOSURE = float(os.environ.get('F_EXPOSURE', '1.0'))
t0 = time.time()
z = np.load(f'{WORK}/strip_final_{PX:g}.npz')
S = {k: z[k] for k in z.files}
th = dict(np.load(f'{WORK}/thread_{PX:g}.npz')); info = dict(np.load(f'{WORK}/strip_info_{PX:g}.npz'))
m = compose(PX, S)
paint_gold(m, PX, th, info)
from geometry import strip_to_world
for (name, u, v, ang, mpp, flip, gain) in layout.QUILTS:
    cx, cy = strip_to_world(np.array([u], np.float32), np.array([v], np.float32))
    q = make_quilt(name, mpp, ang, flip, PX, gain=gain)
    place_quilt(m, q, float(cx[0]), float(cy[0]), PX)
x0, y0, Wpx, Hpx = world_grid(PX)
km = pool(PX, x0, y0, Wpx, Hpx)
light = rig_last_light()
img, vis = render(m, light, PX, km)
thr = gen_threads(S, info, PX) + gen_stray(info, PX)
occ = to_screen(m.get('solid', np.zeros(m['h'].shape, np.float32)), m, PX)
img, _ = draw_threads(img, thr, light, pool_xy, occlude=occ)
GLINT_U = float(os.environ.get('F_GLINT_U', '3415'))
gx, gy, gang = glint_point(th, info, GLINT_U)
print('glint at world mm', gx, gy, 'screen px', (gx + WIN_W / 2) * S_SCREEN, (gy + WIN_H / 2) * S_SCREEN)
img = add_glint(img, gx, gy, gang, peak=float(os.environ.get('F_GLINT', '12.0')))
img = bloom(img)
np.save(f'{WORK}/lin_{tag}.npy', img.astype(np.float16))
g = grade.grade(img, exposure=EXPOSURE, act='III', seed=1319)
cv2.imwrite(f'{WORK}/peek/{tag}.png', g[..., ::-1])
if os.environ.get('F_FINAL') == '1':
    g16 = grade.grade(img, exposure=EXPOSURE, act='III', seed=1319, out_u16=True)
    cv2.imwrite(f'{OUT}/keyframe_f1319_2560x1440.png', g16[..., ::-1])
    cv2.imwrite(f'{OUT}/keyframe_f1319_2560x1440_8bit.png', g[..., ::-1])
print('done', f'{time.time()-t0:.0f}s', 'mean lum', float(img.mean()))
