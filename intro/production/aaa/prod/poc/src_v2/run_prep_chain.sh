#!/bin/sh
# full asset chain: layout -> R25 bake -> wavefront replay final states + radiance -> Eevee inputs -> lighting calibration
set -e
cd /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/src
export NUMBA_NUM_THREADS=3
python3 board_bake.py > /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/bake_full.log 2>&1
python3 finalize.py /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/maps > /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/finalize.log 2>&1
python3 prep_eevee.py > /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/prep.log 2>&1
rm -f /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/data/eevee/ref.json
PYTHONPATH=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/tools/py312 xvfb-run -a -s "-screen 0 1920x1080x24" blender -b --factory-startup -P bl_scene.py -- --res 320 180 --taa 4 --frames 1725 --calib --nopieces --out /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/preview/calib > /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/calib.log 2>&1
python3 -c "
import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/src')
from exr import read_exr; import numpy as np, json
a=read_exr('/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/preview/calib/f1725.exr'); c=a[40:140,60:260,:3].reshape(-1,3); med=np.median(c,0); print('ref',med)
json.dump(dict(ref=[float(v) for v in med]), open('/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/data/eevee/ref.json','w'))
" >> /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/calib.log
echo CHAIN_DONE >> /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/logs/calib.log
