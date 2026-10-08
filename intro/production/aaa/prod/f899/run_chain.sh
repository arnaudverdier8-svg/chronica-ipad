#!/bin/bash
# f899 v3 render chain without the bake:  run_chain.sh TAG [EEVEE_SCALE] [TAA] [PLATE_SCALE]
cd "$(dirname "$0")"
TAG=${1:-v}; SC=${2:-1.0}; TAA=${3:-32}; PSC=${4:-1.0}
T=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/tools
mkdir -p logs work/ev_$TAG out
nice -n 5 python3 src/export_slips.py > logs/export_$TAG.log 2>&1
nice -n 5 python3 src/render_plate.py maps/war_ground $PSC > logs/plate_$TAG.log 2>&1
NSTR=3.0 PYTHONPATH=$T/py312 nice -n 5 xvfb-run -a -s '-screen 0 1920x1080x24' blender -b --factory-startup -P src/eevee_scene.py -- work/ev_$TAG --scale $SC --taa $TAA > logs/eevee_$TAG.log 2>&1
nice -n 5 python3 src/comp.py work/ev_$TAG out/f899_$TAG.png --tag _$TAG > logs/comp_$TAG.log 2>&1
echo "CHAIN DONE $TAG" >> logs/run_$TAG.log
