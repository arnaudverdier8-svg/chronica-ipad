"""Deterministic plan of every piece that rises out of the cloth (towns, quarries, lumber camps, trees, figure cards)
and of its stitched elevation icon / footprint. Pieces hinge up about their BACK-bottom edge (pop-up book): lying flat,
the depth-flattened front elevation lies on the cloth behind the piece (top of the icon toward -z = up on screen),
so the needle-hole footprint stays visible behind the risen piece.
All coordinates in game units (Grandbois = origin)."""
import json, math
import numpy as np
from common import *

MODELS = {m['name']: m for m in json.load(open(f'{A}/assets/models/models.json'))}
CARD_H = 0.84     # figure card height (game units) ~ 17 mm
CARD_STAND = 62.0  # final stand angle from the cloth (deg)


def _hash(*a):
    v = 2166136261
    for x in a:
        v = ((v ^ (int(x) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return v / 4294967295.0


def model_piece(pid, model, x, z, kind, realm=None, hexk=None, scale=1.0):
    mm = MODELS[model]
    bmin, bmax = mm['bbox_min'], mm['bbox_max']
    xmin, xmax = x + bmin[0] * scale, x + bmax[0] * scale
    zb, zf = z + bmin[2] * scale, z + bmax[2] * scale
    ht = bmax[1] * scale
    return dict(id=pid, kind=kind, model=model, x=x, z=z, scale=scale, realm=realm, hex=hexk,
                base=[xmin, zb, xmax, zf], z_back=zb, height=ht,
                icon=[xmin, zb - ht, xmax, zb])           # x0, z0(top), x1, z1(base line)


def tree_piece(pid, x, z, rad, ht, hexk):
    return dict(id=pid, kind='tree', x=x, z=z, rad=rad, height=ht, hex=hexk, base=[x - rad, z - rad, x + rad, z + rad],
                z_back=z - rad, icon=[x - rad, z - rad - ht, x + rad, z - rad])


def card_piece(pid, unit, realm, x, z, w, hexk, k):
    h = CARD_H
    return dict(id=pid, kind='card', unit=unit, realm=realm, x=x, z=z, w=w, height=h, hex=hexk, k=k,
                base=[x - w / 2, z - 0.03, x + w / 2, z + 0.03], z_back=z, icon=[x - w / 2, z - h, x + w / 2, z])


def overlap(a, b, pad=0.02):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def plan(layout):
    hexes = {(h['q'], h['r']): h for h in layout['hexes']}
    pieces = []
    occupied = []          # rectangles (icons + bases) already used

    def free(rects):
        return all(not overlap(r, o) for r in rects for o in occupied)

    def add(p, force=False):
        rects = [p['icon'], p['base']]
        if not force and not free(rects):
            return False
        pieces.append(p); occupied.extend(rects)
        return True
    # 1 towns (+ Grandbois banner)
    for t in layout['towns']:
        cx, cz = hex_center(t['q'], t['r'])
        add(model_piece(f"town_{t['name']}", t['model'], cx, cz, 'town', t['realm'], (t['q'], t['r']), 1.18), force=True)
        if t.get('banner'):
            # banner on a pole beside the keep (front-right), rises last
            add(model_piece(f"banner_{t['name']}", 'settle_banner', cx + 1.22, cz - 0.45, 'banner', t['realm'], (t['q'], t['r']), 0.62), force=True)
    # 2 figure groups (cards), in the front half of their hex
    from figures import card_aspect
    for g in layout['units']:
        cx, cz = hex_center(g['q'], g['r'])
        n = g['n']; asp = card_aspect(g['unit'], g['realm'])
        w = CARD_H * asp
        sp = w * 0.78
        town_here = any((t['q'], t['r']) == (g['q'], g['r']) for t in layout['towns'])
        zc = cz + (0.78 if town_here else 0.5)
        for k in range(n):
            x = cx + (k - (n - 1) / 2) * sp + 0.06 * (_hash(g['q'], g['r'], k) - 0.5)
            z = zc + 0.05 * ((k % 2) - 0.5)
            add(card_piece(f"card_{g['q']}_{g['r']}_{k}", g['unit'], g['realm'], x, z, w, (g['q'], g['r']), k), force=True)
    # 3 quarries
    for s in layout['sites']:
        cx, cz = hex_center(s['q'], s['r'])
        dz = -0.18 if any((u['q'], u['r']) == (s['q'], s['r']) for u in layout['units']) else 0.12
        add(model_piece(f"site_{s['q']}_{s['r']}", s['model'], cx - 0.05, cz + dz, 'site', None, (s['q'], s['r']), 1.35), force=True)
    # 4 forest hexes: a lumber camp + pines
    for (q, r), h in sorted(hexes.items()):
        if h['t'] != 'forest':
            continue
        cx, cz = hex_center(q, r)
        if any((t['q'], t['r']) == (q, r) for t in layout['towns']):
            continue
        add(model_piece(f'lumber_{q}_{r}', 'lumber', cx + 0.28 + 0.1 * (_hash(q, r, 1) - 0.5), cz + 0.32, 'lumber', None, (q, r), 1.45))
        # candidate pine spots (jittered), keep those that fit
        cands = [(-0.45, 0.38), (-0.12, 0.62), (0.52, -0.18), (-0.5, -0.12), (0.12, 0.05), (0.3, 0.62), (-0.22, 0.22), (0.62, 0.3)]
        nt = 0
        for i, (ox, oz) in enumerate(cands):
            j1, j2, j3 = _hash(q, r, i, 7), _hash(q, r, i, 11), _hash(q, r, i, 13)
            x = cx + ox + 0.08 * (j1 - 0.5); z = cz + oz + 0.08 * (j2 - 0.5)
            rad = 0.105 + 0.03 * j3; ht = 0.34 + 0.12 * j1
            p = tree_piece(f'tree_{q}_{r}_{i}', x, z, rad, ht, (q, r))
            if edge_dist(np.array(x), np.array(z - rad - ht), cx, cz) < 0.06 or edge_dist(np.array(x), np.array(z + rad), cx, cz) < 0.06:
                continue
            if add(p):
                nt += 1
            if nt >= 5:
                break
    return pieces


if __name__ == '__main__':
    L = json.load(open(f'{POC}/data/layout.json'))
    ps = plan(L)
    from collections import Counter
    print(len(ps), Counter(p['kind'] for p in ps))
    json.dump(ps, open(f'{POC}/data/pieces.json', 'w'), indent=0)
