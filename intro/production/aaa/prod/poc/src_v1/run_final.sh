#!/bin/sh
# final pass (assets + R25 frames already built by run_all.sh / run_prep_chain.sh + r25_frames.py):
# Eevee 2560x1440 16 TAA for f1725 (zero-tilt swap still) + f1726-1766, then COMP, encode, QA
set -e
cd /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/src
PYTHONPATH=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/tools/py312 xvfb-run -a -s "-screen 0 1920x1080x24" blender -b --factory-startup -P bl_scene.py -- --res 2560 1440 --taa 16 --frames ${FRAMES:-1725-1766} --out /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/ev --save /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/src/poc_scene.blend > /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/ev_final.log 2>&1
python3 comp.py > /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/comp.log 2>&1
./encode.sh /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/frames /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/poc_cloth_to_board_2560x1440.mp4 14
python3 qa.py > /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/qa.log 2>&1
echo FINAL_DONE >> /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/run_final.log
