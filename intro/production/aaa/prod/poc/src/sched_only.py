"""recompute maps/schedule.npz only (replay.schedule), without re-replaying the states (fast look-dev of the stitch-on timing)"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from replay import load, schedule
import numpy as np
D = f'{POC}/maps'
L = json.load(open(f'{POC}/data/layout.json')); PIECES = json.load(open(f'{POC}/data/pieces.json'))
R, canvas, masks, hexmap = load(D)
rec = R['record']
st, en, rev, info = schedule(R, L, PIECES)
order = np.lexsort((np.arange(len(rec)), en)); order = order[en[order] < 1e5]
np.savez_compressed(f'{D}/schedule.npz', st=st, en=en, rev=rev, order=order, t0_h=info['t0_h'], dur_h=info['dur_h'])
print('ok', len(order), float(en[order].max()))
