S=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa; source $S/tools/env.sh
cd $S/rnd/hybridplane
export MAPSDIR=maps_v2 OUTTAG=_v3 SPOT=48 KEYD=0.85 KEY=68 FILL=3.4
KNIGHT_LIFT='{"lift": 7.0, "hscale": 1.25, "rx": -3.0, "ry": 2.0, "bend": 1.2, "rigid": 1.0}' bpy_env nice -n 5 $BPY_PY tools/scene.py oblique 2560 1440 16 0 0 2>&1 | grep --line-buffered -E "FRAME|Error|Trace"
cp renders/oblique_v3/oblique_0000.png renders/oblique_v3/oblique_lift.png
echo LIFT3_DONE
