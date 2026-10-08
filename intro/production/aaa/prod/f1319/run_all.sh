#!/bin/bash
# Reproduce the f1319 keyframe (v2) from the baked MapSets (deterministic; ~4 min on 2 cores, peak RSS 3.0 GB at 1.5 px/mm).
# The war sheets come from aaa/prod/f899/maps; their 5 px/mm mip was cached in work/panel_war*_1.5.npz so the frame does not depend on that
# directory staying unchanged (delete work/panel_*_1.5.npz to re-read the sheets).
# v1 (first delivery) is kept: *_v1 files, src_v1/ (its sources), run_all_v1.sh.  v2 outputs carry the work-file suffix _v2 (F_TAG).
set -e
cd "$(dirname "$0")"
export NUMBA_NUM_THREADS=2
nice -n 5 python3 src/prep_panels.py 1.5        # resample the 5 px/mm mip of every sheet to the working density   (~25 s; skipped if work/panel_*_1.5.npz exist)
nice -n 5 python3 src/build_strip.py 1.5        # border band + register sections + 3 different dividers + thread centre-line   (~14 s)
nice -n 5 python3 src/finish_strip.py 1.5       # ageing, oatmeal grade, stitch-row detail, wrinkles, burn hole, comb edge, bites (~55 s, 2.1 GB)
# the delivered frame (S18 hold framing, 0.75 px/mm):
F_FINAL=1 F_EXPOSURE=0.92 nice -n 5 python3 src/render_f1319.py 1.5 final               # table + quilts + thread + relight + fringe + glint + grade (~50 s, 3.0 GB)
python3 src/make_crops.py
nice -n 5 python3 src/check_falloff.py          # -2.5 EV proof
# optional alternative framing (1.0 px/mm, window 2560 x 1440 mm, centred on u 2030: oath ... war ... burn hole):
F_SCREEN=1.0 F_UC=2030 F_SURV0=3010 F_GLINT_U=3160 F_EDGE=560 F_OUTNAME=keyframe_f1319_alt_1.0pxmm_2560x1440 F_FINAL=1 F_EXPOSURE=0.92 nice -n 5 python3 src/render_f1319.py 1.5 alt
