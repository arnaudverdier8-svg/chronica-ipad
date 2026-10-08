#!/bin/bash
# f899 full chain: bake war sheet -> export slips -> R25 plate passes -> Eevee passes -> COMP
# usage: run_all.sh TAG [EEVEE_SCALE] [TAA]   (steps can be skipped with SKIP="bake export plate eevee")
cd "$(dirname "$0")"
TAG=${1:-v}; SC=${2:-1.0}; TAA=${3:-32}
T=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/tools
has() { [[ " $SKIP " != *" $1 "* ]]; }
if has bake;   then nice -n 5 python3 src/scene_war.py --px 10 --out maps > logs/bake_$TAG.log 2>&1; fi
if has export; then nice -n 5 python3 src/export_slips.py > logs/export_$TAG.log 2>&1; fi
if has plate;  then nice -n 5 python3 src/render_plate.py > logs/plate_$TAG.log 2>&1; fi
if has eevee;  then mkdir -p work/ev_$TAG; NSTR=3.0 PYTHONPATH=$T/py312 nice -n 5 xvfb-run -a -s '-screen 0 1920x1080x24' blender -b --factory-startup -P src/eevee_scene.py -- work/ev_$TAG --scale $SC --taa $TAA > logs/eevee_$TAG.log 2>&1; fi
nice -n 5 python3 src/comp.py work/ev_$TAG out/f899_$TAG.png --tag _$TAG > logs/comp_$TAG.log 2>&1
echo "ALL DONE $TAG" >> logs/run_$TAG.log
