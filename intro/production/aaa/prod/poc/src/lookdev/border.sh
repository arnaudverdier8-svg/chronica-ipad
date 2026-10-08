#!/bin/sh
# usage: border.sh TAG FRAME x0 y0 x1 y1 [ENV=VAL ...]   -> v3/b_TAG.png  (full-res 2560x1440 camera, border crop, TAA 8)
TAG=$1; F=$2; X0=$3; Y0=$4; X1=$5; Y1=$6; shift 6
P=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc
cd $P/src
env "$@" PYTHONPATH=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/tools/py312 nice -n 5 xvfb-run -a -s "-screen 0 1920x1080x24" blender -b --factory-startup -P bl_scene.py -- --res 2560 1440 --taa 8 --frames $F --out $P/preview/ev_b_$TAG --border $X0 $Y0 $X1 $Y1 > $P/logs/ev_b_$TAG.log 2>&1
python3 /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/v3/ev2.py $P/preview/ev_b_$TAG/f$F.exr /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/v3/b_$TAG.png
