"""Write <sheet>_ground/groups_mm.json: per group the stitched bbox + centre in SHEET mm, entry count, and the
needle-path unpick direction, for keyframe agents.   python3 bin/group_info.py p1_oath p3_death p6_ruin"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from chron.config import MAPS
from chron.maps import MapSet
from chron.record import bbox_of
for sheet in sys.argv[1:]:
    G = MapSet(os.path.join(MAPS, sheet + '_ground'))
    R = G.stitches(); gj = json.load(open(os.path.join(G.path, 'groups.json')))
    PX = float(R['PX']); out = {}
    for gi, name in enumerate(gj['groups']):
        if gi == 0: continue
        sel = R['order'][R['group'][R['order']] == gi]
        if len(sel) == 0: continue
        x0, y0, x1, y1 = bbox_of(R, sel, 0)
        out[name] = dict(entries=int(len(sel)), bbox_mm=[round(x0 / PX, 1), round(y0 / PX, 1), round(x1 / PX, 1), round(y1 / PX, 1)],
                         centre_mm=[round((x0 + x1) / 2 / PX, 1), round((y0 + y1) / 2 / PX, 1)], gpoly_id=gi)
    out['_note'] = ('sheet mm (origin sheet top-left; panel at (20,20) mm). Groups are absent from <sheet>_ground (ghost '
                    'only) and present in <sheet>. GroupAnim(ground, [name]) replays them exactly in needle order.')
    json.dump(out, open(os.path.join(G.path, 'groups_mm.json'), 'w'), indent=1)
    print(sheet, json.dumps({k: v for k, v in out.items() if k != '_note'}))
