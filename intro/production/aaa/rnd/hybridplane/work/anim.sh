S=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa; source $S/tools/env.sh
cd $S/rnd/hybridplane
until grep -q STILLS_DONE work/stills.log; do sleep 5; done
bpy_env $BPY_PY tools/scene.py motion 1280 720 8 0 74 1 2>&1 | grep -E "FRAME|Error|Trace"
echo MOTION_DONE
bpy_env $BPY_PY tools/scene.py rise_oblique 1280 720 8 0 118 2 2>&1 | grep -E "FRAME|Error|Trace"
echo RISE_DONE
