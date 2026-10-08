#!/bin/sh
# full re-render: assets chain -> R25 2D frames (+) Eevee frames -> COMP -> encode
# usage: run_all.sh preview|final
set -e
MODE=${1:-preview}
cd /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/src
rm -f /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/calib.log
./run_prep_chain.sh
if [ "$MODE" = final ]; then RES="2560 1440"; TAA=16; EVO=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/ev; else RES="1280 720"; TAA=8; EVO=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/preview/ev720; fi
NUMBA_NUM_THREADS=2 python3 r25_frames.py > /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/r25_frames.log 2>&1 &
R25PID=$!
PYTHONPATH=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/tools/py312 xvfb-run -a -s "-screen 0 1920x1080x24" blender -b --factory-startup -P bl_scene.py -- --res $RES --taa $TAA --frames 1725-1766 --out $EVO --save /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/src/poc_scene.blend > /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/ev_$MODE.log 2>&1
wait $R25PID
if [ "$MODE" = final ]; then
  python3 comp.py > /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/comp.log 2>&1
  ./encode.sh /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/frames /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/poc_cloth_to_board_2560x1440.mp4 14
else
  python3 comp.py --preview > /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/comp_prev.log 2>&1
  ./encode.sh /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/preview/frames720 /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/preview/poc_preview_720.mp4 18
fi
echo ALL_DONE_$MODE >> /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/run_all.log
