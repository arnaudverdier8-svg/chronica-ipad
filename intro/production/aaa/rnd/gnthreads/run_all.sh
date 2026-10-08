#!/bin/bash
# sequential renders (one Blender at a time to leave cores for other agents)
cd /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/rnd/gnthreads
T=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/tools
for c in "$@"; do
  echo "=== $c $(date +%T)"
  PYTHONPATH=$T/py312 nice -n 5 xvfb-run -a -s "-screen 0 2600x1500x24" blender -b --factory-startup -P scene.py -- cfg/$c.json 2>&1 | grep -E "RENDERED|Error|Traceback|ALL DONE"
done
echo "=== finished $(date +%T)"
