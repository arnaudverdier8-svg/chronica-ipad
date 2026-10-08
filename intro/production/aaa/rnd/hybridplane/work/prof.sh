S=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa; source $S/tools/env.sh
cd $S/rnd/hybridplane
for v in "A 1" "B 4"; do set -- $v
  bpy_env $BPY_PY tools/scene.py frontal 1280 720 $2 0 2 2>&1 | grep FRAME | tr '\n' ' '; echo " taa=$2"
done
