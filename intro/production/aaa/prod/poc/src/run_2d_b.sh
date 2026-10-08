#!/bin/sh
set -e
cd /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/src
P=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc
export NUMBA_NUM_THREADS=3
rm -f $P/logs/chain2.log
python3 finalize.py $P/maps > $P/logs/finalize.log 2>&1
python3 cards_bake.py > $P/logs/cards.log 2>&1
python3 prep_eevee.py > $P/logs/prep.log 2>&1
echo FIN_DONE >> $P/logs/chain2.log
python3 r25_frames.py > $P/logs/r25_full.log 2>&1
echo R25_DONE >> $P/logs/chain2.log
