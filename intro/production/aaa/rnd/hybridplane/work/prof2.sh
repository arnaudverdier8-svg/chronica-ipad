S=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa; source $S/tools/env.sh
cd $S/rnd/hybridplane
run(){ echo -n "$* : "; env "$@" bpy_env $BPY_PY tools/scene.py frontal 1280 720 4 0 1 2>&1 | grep FRAME | tr '\n' ' '; echo; }
run ANISO=FILTER_0 FASTGI=0 SHRAYS=1
run ANISO=FILTER_4 FASTGI=0 SHRAYS=1
run ANISO=FILTER_0 FASTGI=1 SHRAYS=1
