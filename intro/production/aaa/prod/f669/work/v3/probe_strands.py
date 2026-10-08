import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
import numpy as np
import shot
A = shot.assets(); lo = A['loose']
f = 669
for i, (ps, dur) in lo.stubborn.items():
    b = lo.blocks[i]
    c = lo.curve(b, f)
    P, soff = c
    arc = np.linalg.norm(np.diff(P[:, :2], axis=0), axis=1).sum()
    print('block', i, 'L', round(b['L'], 1), 'rad', round(b['rad'], 3), 'anchor', b['anchor'].round(1), 'pull', ps, dur,
          'curve pts', len(P), 'planar len', round(float(arc), 1), 'z range', P[:, 2].min().round(2), P[:, 2].max().round(2), 'soff', round(soff, 1),
          'alb_aged', b['alb_aged'].round(4), 'alb', b['alb'].round(3), 'kind', b['kind'])
