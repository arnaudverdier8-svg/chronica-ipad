#!/bin/sh
# chain (plan, bake, finalize, cards, eevee inputs) then the 2D R25 frames at full resolution
set -e
cd /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/src
P=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc
rm -f $P/logs/chain.log
./run_chain_v3.sh
export NUMBA_NUM_THREADS=3
python3 r25_frames.py > $P/logs/r25_full.log 2>&1
echo R25_DONE >> $P/logs/chain.log
