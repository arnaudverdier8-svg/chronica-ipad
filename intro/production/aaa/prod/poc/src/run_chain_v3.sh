#!/bin/sh
# v3 full bake chain: plan + bake + finalize + cards + eevee inputs (about 8 min)
set -e
cd /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/src
export NUMBA_NUM_THREADS=3
P=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc
python3 pieces_plan.py > $P/logs/plan.log 2>&1
python3 board_bake.py > $P/logs/bake_full.log 2>&1
python3 finalize.py $P/maps > $P/logs/finalize.log 2>&1
python3 cards_bake.py > $P/logs/cards.log 2>&1
python3 prep_eevee.py > $P/logs/prep.log 2>&1
echo CHAIN_V3_DONE >> $P/logs/chain.log
