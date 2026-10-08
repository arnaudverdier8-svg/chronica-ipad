#!/bin/bash
# Reproduce the f1319 keyframe from the baked MapSets (deterministic; ~5 min on 2 cores, peak RSS ~3.0 GB at 1.5 px/mm).
# The war sheets come from aaa/prod/f899/maps; their 5 px/mm mip was cached in work/panel_war*_1.5.npz so the frame does not depend on that
# directory staying unchanged (delete work/panel_*_1.5.npz to re-read the sheets).
set -e
cd "$(dirname "$0")"
export NUMBA_NUM_THREADS=2
nice -n 5 python3 src/prep_panels.py 1.5        # resample the 5 px/mm mip of every sheet to the working density   (~25 s)
nice -n 5 python3 src/build_strip.py 1.5        # border band + register sections + dividers + thread centre-line   (~12 s)
nice -n 5 python3 src/finish_strip.py 1.5       # ageing, grime, burn-through, mends, folds, frayed boundary         (~35 s)
F_FINAL=1 nice -n 5 python3 src/render_f1319.py 1.5 final    # table + quilts + thread + relight + fringe + glint + grade (~50 s)
python3 src/make_crops.py
nice -n 5 python3 src/check_falloff.py          # -2.5 EV proof
