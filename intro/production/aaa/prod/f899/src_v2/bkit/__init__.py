"""bkit: the procedural Bayeux kit (CHRONICA intro).  Builds R25 MapSets (the asset contract of aaa/lib) from vector
elements: hillock bands, paired-line rivers, couched roads, ploughed strips, interlace trees, borders with diagonal-bar
compartments and vignette beasts, towns re-stitched from game-model elevations, pennants, crowns, couched metal
threads, hems, nail holes, underdrawing.

Uses the hardened library read-only (aaa/lib/chron): stitch primitives, RECORD, needle order, exact replay, MapSet.
"""
import os, sys
KIT = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/kit'   # (f899 copy: elevations stay in the shared kit)
AAA = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa'
LIB = os.path.join(AAA, 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import cv2
cv2.setNumThreads(2)
