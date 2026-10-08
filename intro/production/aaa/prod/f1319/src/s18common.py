"""Shared paths / constants / helpers for the f1319 (S18 'edges') keyframe."""
import os, sys, math, json, time
AAA = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa'
OUT = AAA + '/prod/f1319'
WORK = OUT + '/work'
SRC = OUT + '/src'
sys.path.insert(0, AAA + '/lib')
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, cv2
cv2.setNumThreads(2)

SHEETS = dict(realm=AAA + '/cache/maps/k1_realm', p1=AAA + '/cache/maps/p1_oath', p1g=AAA + '/cache/maps/p1_oath_ground',
              p3=AAA + '/cache/maps/p3_death', p6=AAA + '/cache/maps/p6_ruin',
              war=AAA + '/prod/f899/maps/war', warg=AAA + '/prod/f899/maps/war_ground')

TAG = os.environ.get('F_TAG', '_v2')          # v2 outputs carry this suffix (v1 files are kept untouched)

CHANNELS = ('h', 'alb', 'T', 'mat', 'cov', 'age_fox', 'age_tide', 'age_fade', 'ghost', 'ud', 'holes')


def resample_maps(m, PX_from, PX_to, keys=CHANNELS):
    """area resample a working-maps dict (float32 / uint8) from PX_from to PX_to px/mm (downscale or mild upscale).
    T: doubled-angle average; mat: class fractions (metal x1.6 so thin threads survive); everything else INTER_AREA."""
    f = PX_to / PX_from
    H, W = m['h'].shape
    H2, W2 = int(round(H * f)), int(round(W * f))
    out = {}
    interp = cv2.INTER_AREA if f < 1 else cv2.INTER_LINEAR
    for k in keys:
        if k not in m: continue
        v = m[k]
        if k == 'T':
            v = np.asarray(v, np.float32)
            a = np.arctan2(v[..., 1], v[..., 0]) * 2
            c = cv2.resize(np.cos(a).astype(np.float32), (W2, H2), interpolation=interp)
            s = cv2.resize(np.sin(a).astype(np.float32), (W2, H2), interpolation=interp)
            a2 = 0.5 * np.arctan2(s, c)
            out[k] = np.dstack([np.cos(a2), np.sin(a2)]).astype(np.float32)
        elif k == 'mat':
            best = np.full((H2, W2), -1, np.float32); o = np.zeros((H2, W2), np.uint8)
            for i in np.unique(v):
                c = cv2.resize((v == i).astype(np.float32), (W2, H2), interpolation=interp)
                if i == 3: c = c * 1.6
                sel = c > best; o[sel] = i; best[sel] = c[sel]
            out[k] = o
        else:
            out[k] = cv2.resize(np.asarray(v, np.float32), (W2, H2), interpolation=interp)
    out['PX'] = float(PX_to)
    return out


def srgb_hex(h):
    from chron.color import hex_lin
    return hex_lin(h)
