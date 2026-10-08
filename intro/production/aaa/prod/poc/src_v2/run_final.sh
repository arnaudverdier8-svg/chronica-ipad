#!/bin/sh
# final pass (assets + R25 frames already built by run_bake_chain.sh + r25_frames.py):
# Eevee 2560x1440 16 TAA for f1725 (zero-tilt swap still), f1726-1766 on ones, f1768-1782 on twos (hold, heal, candle swell settling), then COMP, encode, QA
# FRAMES=1740-1745 ./run_final.sh re-renders a sub-range (then comp/encode)
set -e
cd /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/src
P=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc
FR=${FRAMES:-1725,1726-1766,1768,1770,1772,1774,1776,1778,1780,1782}
PYTHONPATH=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/tools/py312 xvfb-run -a -s "-screen 0 1920x1080x24" blender -b --factory-startup -P bl_scene.py -- --res 2560 1440 --taa 16 --frames $FR --out $P/ev --save $P/src/poc_scene.blend > $P/logs/ev_final.log 2>&1
python3 comp.py > $P/logs/comp.log 2>&1
./encode.sh $P/frames $P/poc_cloth_to_board_2560x1440.mp4 14
python3 qa.py > $P/logs/qa.log 2>&1
echo FINAL_DONE >> $P/logs/run_final.log
