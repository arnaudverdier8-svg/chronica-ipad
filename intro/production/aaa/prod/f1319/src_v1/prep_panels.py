"""Resample the baked MapSets to the strip working density (default 1.0 px/mm) and cache them as npz."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
from chron.maps import MapSet

PXT = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
names = sys.argv[2:] or list(SHEETS)
for n in names:
    t0 = time.time()
    ms = MapSet(SHEETS[n])
    m = ms.full(1)                       # 5 px/mm
    r = resample_maps(m, 5.0, PXT)
    del m
    np.savez_compressed(f'{WORK}/panel_{n}_{PXT:g}.npz', **{k: (v.astype(np.float16) if v.dtype == np.float32 and k != 'T' else v) for k, v in r.items() if k != 'PX'})
    print(n, r['h'].shape, f'{time.time()-t0:.1f}s', flush=True)
