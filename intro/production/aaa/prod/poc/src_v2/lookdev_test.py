import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r25render import *
D = sys.argv[1]
z = np.load(f'{D}/bake_final.npz'); mk = np.load(f'{D}/masks.npz')
m = {k: z[k] for k in z.files}; m['base'] = mk['base']; m['PX'] = PX
m['h'] = m['h'].astype(np.float32); m['alb'] = m['alb'].astype(np.float32)
# window around Grandbois: world x -3.2..3.2, z -2.2..2.4
u0, v0 = int((-3.4 - BX0) * PPU), int((-2.4 - BZ0) * PPU); u1, v1 = int((3.6 - BX0) * PPU), int((2.6 - BZ0) * PPU)
t = time.time()
rad = shade_window(m, (u0, v0, u1, v1))
print('shade', time.time() - t, rad.shape)
view, s = topdown_view()
# 1:1 screen-scale crop: scale map window by s
sc = s
img = cv2.resize(cv2.GaussianBlur(rad, (0, 0), 0.42 / sc * 0.8), None, fx=sc, fy=sc, interpolation=cv2.INTER_LINEAR)
out = grade(img)
cv2.imwrite(sys.argv[2], cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
crop = grade(rad[int(1.2 * PPU):int(1.2 * PPU) + 900, int(2.2 * PPU):int(2.2 * PPU) + 1400])
cv2.imwrite(sys.argv[2].replace('.png', '_mapres.png'), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
