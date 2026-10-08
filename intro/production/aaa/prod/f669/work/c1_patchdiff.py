import os, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
import shot, numpy as np, cv2
G = shot.MapSet(shot.MAPS + '/p1_oath_ground')
gf = shot.GroundFix(G)
p = gf.patches[1]; print(p['name'], p['bbox'])
x0, y0, x1, y1 = p['bbox']
b = G.read_px(x0, y0, x1, y1, 0, keys=['h', 'alb', 'ghost', 'mat'])
dh = np.abs(b['h'].astype(np.float32) - p['st']['h'].astype(np.float32)); da = np.abs(b['alb'].astype(np.float32) - p['st']['alb'].astype(np.float32)).max(-1)
print('h diff >0.02 frac', (dh > 0.02).mean(), 'alb diff >0.02 frac', (da > 0.02).mean())
gh = b['ghost'].astype(np.float32)
print('ghost frac', (gh > 0.5).mean())
# diff on linen pixels outside ghost
lin = (b['mat'] == 0) & (gh < 0.1)
print('linen outside ghost: h diff mean', dh[lin].mean(), 'alb diff mean', da[lin].mean())
lin2 = (b['mat'] == 0) & (gh > 0.5)
print('linen in ghost: h diff mean', dh[lin2].mean(), 'alb diff mean', da[lin2].mean(), ' alb baked mean', b['alb'][lin2].mean(0), 'patch', p['st']['alb'][lin2].astype(np.float32).mean(0))
print('baked h mean in ghost', b['h'][lin2].mean(), 'patch', p['st']['h'][lin2].astype(np.float32).mean(), '; outside ghost baked', b['h'][lin].mean(), 'patch', p['st']['h'][lin].astype(np.float32).mean())
from chron.color import lin2srgb
f = lambda x: (np.clip(lin2srgb(np.clip(x.astype(np.float32), 0, 1)), 0, 1) * 255).astype(np.uint8)[..., ::-1]
im = np.hstack([f(b['alb']), f(p['st']['alb']), np.repeat((np.clip(dh * 400, 0, 255)).astype(np.uint8)[..., None], 3, 2)])
cv2.imwrite('c1_patch.png', cv2.resize(im, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA))
print('--- stitched pixels (mat!=0 in both): ')
st = (b['mat'] != 0) & (p['st']['mat'] != 0)
print('n', st.sum(), 'alb diff mean', np.abs(b['alb'][st].astype(np.float32) - p['st']['alb'][st].astype(np.float32)).mean(), 'h diff mean', dh[st].mean())
# where the patch has stitched but baked not and vice versa
print('patch stitched only', ((p['st']['mat'] != 0) & (b['mat'] == 0)).sum(), 'baked stitched only', ((b['mat'] != 0) & (p['st']['mat'] == 0)).sum())
# stitched pixel brightness in/out of ghost polygon
for nm, mk in (('in ghost', st & (gh > 0.5)), ('out ghost', st & (gh < 0.1))):
    print(nm, mk.sum(), 'baked alb', b['alb'][mk].astype(np.float32).mean(0).round(3), 'patch alb', p['st']['alb'][mk].astype(np.float32).mean(0).round(3))
