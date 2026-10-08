#!/bin/sh
# 720p preview of the whole move: R25 2D states at half scale (every frame), Eevee 1280x720 6 TAA (f1725, f1726-1782), COMP --preview, QA --preview
set -e
cd /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/src
P=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc
export NUMBA_NUM_THREADS=3
mkdir -p $P/preview
if [ -z "$SKIP_R25" ]; then python3 r25_frames.py --scale 0.5 > $P/logs/prev_r25.log 2>&1; fi
FR=${FRAMES:-1725,1726-1782}
PYTHONPATH=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/tools/py312 xvfb-run -a -s "-screen 0 1920x1080x24" blender -b --factory-startup -P bl_scene.py -- --res 1280 720 --taa ${TAA:-6} --frames $FR --out $P/preview/ev720 > $P/logs/prev_ev.log 2>&1
python3 comp.py --preview > $P/logs/prev_comp.log 2>&1
python3 qa.py --preview > $P/logs/prev_qa.log 2>&1
echo PREVIEW_DONE >> $P/logs/prev_chain.log
