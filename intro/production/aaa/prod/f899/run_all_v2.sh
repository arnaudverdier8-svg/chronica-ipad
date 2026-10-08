#!/bin/bash
# f899 v2 full chain: bake war sheet -> export slips -> R25 plate passes -> Eevee passes -> COMP
# usage: run_all.sh TAG [EEVEE_SCALE] [TAA] [PLATE_SCALE]   (steps can be skipped with SKIP="bake export plate eevee comp")
cd "$(dirname "$0")"
TAG=${1:-v}; SC=${2:-1.0}; TAA=${3:-32}; PSC=${4:-1.0}
T=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/tools
has() { [[ " $SKIP " != *" $1 "* ]]; }
mkdir -p logs work/ev_$TAG out
if has bake;   then nice -n 5 python3 src_v2/scene_war.py --px 10 > logs/bake_$TAG.log 2>&1; fi
if has export; then nice -n 5 python3 src_v2/export_slips.py > logs/export_$TAG.log 2>&1; fi
if has plate;  then nice -n 5 python3 src_v2/render_plate.py maps_v2/war_ground $PSC > logs/plate_$TAG.log 2>&1; fi
if has eevee;  then NSTR=3.0 PYTHONPATH=$T/py312 nice -n 5 xvfb-run -a -s '-screen 0 1920x1080x24' blender -b --factory-startup -P src_v2/eevee_scene.py -- work/ev_$TAG --scale $SC --taa $TAA > logs/eevee_$TAG.log 2>&1; fi
if has comp;   then nice -n 5 python3 src_v2/comp.py work/ev_$TAG out/f899_$TAG.png --tag _$TAG > logs/comp_$TAG.log 2>&1; fi
echo "ALL DONE $TAG" >> logs/run_$TAG.log
