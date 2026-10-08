"""Bake a panel MapSet:  python3 bin/bake_panel.py p1_oath [--max-regions N] [--out DIR] [--focus x0 y0 x1 y1]
Writes <out>/<panel>/ and <panel>_ground/ (MapSet + stitches.npz + groups.json).  The bake goes to a temporary
directory first and is swapped in atomically, so readers never see a half-written sheet."""
import sys, os, argparse, time, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import cv2
cv2.setNumThreads(2)
from chron.motifs.panel import build_panel
from chron.config import HINTS, MAPS
ap = argparse.ArgumentParser()
ap.add_argument('panel'); ap.add_argument('--max-regions', type=int, default=None); ap.add_argument('--out', default=MAPS)
ap.add_argument('--focus', type=int, nargs=4, default=None)
a = ap.parse_args()
tmp = os.path.join(a.out, f'.tmp_{a.panel}_{os.getpid()}')
os.makedirs(tmp, exist_ok=True)
build_panel(os.path.join(HINTS, a.panel + '.json'), tmp, max_regions=a.max_regions, focus=a.focus)
for sheet in (a.panel, a.panel + '_ground'):
    dst = os.path.join(a.out, sheet); old = dst + f'.old_{os.getpid()}'
    if os.path.exists(dst):
        os.rename(dst, old)
    os.rename(os.path.join(tmp, sheet), dst)
    if os.path.exists(old):
        shutil.rmtree(old)
shutil.rmtree(tmp, ignore_errors=True)
print('swapped in', a.panel)
