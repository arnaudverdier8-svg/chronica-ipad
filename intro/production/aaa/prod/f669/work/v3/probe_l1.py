import sys, os
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src'); sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
import numpy as np, cv2, math
from chron.maps import MapSet
from chron.config import MAPS
from chron.color import lin2oklab
import touchup as TU
G = MapSet(MAPS + '/p1_oath_ground')
for lvl in (0, 1):
    m = G.read(465, 195, 505, 230, lvl, keys=['h', 'alb', 'mat'])
    PX = m['PX']; ox, oy = m['origin_mm']
    x0, y0, x1, y1 = TU.HORSE_BOX_MM
    a0, b0 = int((x0 - ox) * PX), int((y0 - oy) * PX); a1, b1 = int(math.ceil((x1 - ox) * PX)), int(math.ceil((y1 - oy) * PX))
    sub = m['alb'][b0:b1, a0:a1]; mat = m['mat'][b0:b1, a0:a1]
    lab = lin2oklab(sub); C = np.hypot(lab[..., 1], lab[..., 2])
    cream = ((lab[..., 0] > 0.60) & (C < 0.12) & (mat == 1)).astype(np.uint8)
    n, cc, st, _ = cv2.connectedComponentsWithStats(cream)
    print('level', lvl, 'PX', PX, 'cream px', cream.sum(), 'components', n - 1, 'largest', st[1:, cv2.CC_STAT_AREA].max() if n > 1 else 0, 'thresh', 3.0 * PX * PX)
    print('   L quantiles in box', np.quantile(lab[..., 0], [.5, .9, .99]).round(3), 'mat==1 frac', (mat == 1).mean().round(2))
    before = m['alb'].copy()
    TU.tone_emblem(m)
    print('   changed px', int((np.abs(m['alb'] - before).max(-1) > 1e-4).sum()))
