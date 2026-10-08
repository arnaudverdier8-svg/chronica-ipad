"""v2 plan of every piece that rises out of the cloth (towns, banner, quarries, lumber camps, trees, figure cards) and of its
stitched elevation icon / footprint. Pieces hinge about their BACK-bottom edge (pop-up book): lying flat, the foreshortened front
elevation lies on the cloth behind the piece (top toward -z = up on screen), so the footprint stays visible behind the risen piece.
The elevations are foreshortened (icons2.K_FORE) so each stays inside its own hex (critic 2); while a piece rises its height grows
from K to 1.  Only hexes the crane's camera can see get pieces.  All coordinates in game units (Grandbois = origin)."""
import json, math
import numpy as np
from common import *
import icons2
from icons2 import K_FORE, forest_trees, hut_slot, rng_of

MODELS = {m['name']: m for m in json.load(open(f'{A}/assets/models/models.json'))}
CARD_H = 0.84
CARD_STAND = 62.0


def _hash(*a):
    v = 2166136261
    for x in a:
        v = ((v ^ (int(x) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return v / 4294967295.0


def visible_hexes(layout, margin=1.25):
    """set of (q, r) whose centre lies inside the union of the camera footprints of the crane (pitch 90 .. menu) +- margin units"""
    from gamecam import Cam
    keep = set()
    cams = []
    for pitch in (90.0, 82.0, 74.0, PITCH_MENU):
        cams.append(Cam(np.array(TARGET, float), math.radians(pitch), DIST, FOV_V, 2560, 1440))
    for h in layout['hexes']:
        for cam in cams:
            ok = False
            for dx, dz in ((0, 0), (margin, 0), (-margin, 0), (0, margin), (0, -margin)):
                uv, zc = cam.project(np.array([[h['x'] + dx, 0.25, h['z'] + dz]]))
                if zc[0] > 0 and -80 <= uv[0, 0] <= 2640 and -120 <= uv[0, 1] <= 1560:
                    ok = True; break
            if ok:
                keep.add((h['q'], h['r'])); break
    return keep


def model_piece(pid, model, x, z, kind, realm=None, hexk=None, scale=1.0):
    mm = MODELS[model]
    bmin, bmax = mm['bbox_min'], mm['bbox_max']
    xmin, xmax = x + bmin[0] * scale, x + bmax[0] * scale
    zb, zf = z + bmin[2] * scale, z + bmax[2] * scale
    ht = bmax[1] * scale
    k = K_FORE[kind]
    return dict(id=pid, kind=kind, model=model, x=x, z=z, scale=scale, realm=realm, hex=hexk, k=k,
                base=[xmin, zb, xmax, zf], z_back=zb, height=ht, icon=[xmin, zb - ht * k, xmax, zb])


def tree_piece(pid, x, z, sp, rad, ht, hexk, seed):
    k = K_FORE['tree']
    return dict(id=pid, kind='tree', sp=sp, x=x, z=z, rad=rad, height=ht, hex=hexk, k=k, seed=seed,
                base=[x - rad, z - rad, x + rad, z + rad], z_back=z - rad, icon=[x - rad, z - rad - ht * k, x + rad, z - rad])


def card_piece(pid, unit, realm, x, z, w, hexk, k_):
    h = CARD_H; k = K_FORE['card']
    return dict(id=pid, kind='card', unit=unit, realm=realm, x=x, z=z, w=w, height=h, hex=hexk, k=k, ord=k_,
                base=[x - w / 2, z - 0.03, x + w / 2, z + 0.03], z_back=z, icon=[x - w / 2, z - h * k, x + w / 2, z])


def overlap(a, b, pad=0.02):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def plan(layout):
    hexes = {(h['q'], h['r']): h for h in layout['hexes']}
    vis = visible_hexes(layout)
    pieces = []
    occupied = []          # rectangles of non-tree pieces (icons + bases)

    def free(rects):
        return all(not overlap(r, o) for r in rects for o in occupied)

    def add(p, force=False):
        rects = [p['icon'], p['base']]
        if not force and not free(rects):
            return False
        pieces.append(p); occupied.extend(rects)
        return True
    from figures import card_aspect
    # 1 towns (+ Grandbois banner)
    for t in layout['towns']:
        if (t['q'], t['r']) not in vis: continue
        cx, cz = hex_center(t['q'], t['r'])
        add(model_piece(f"town_{t['name']}", t['model'], cx, cz, 'town', t['realm'], (t['q'], t['r']), 1.18), force=True)
        if t.get('banner'):
            add(model_piece(f"banner_{t['name']}", 'settle_banner', cx + 1.22, cz - 0.45, 'banner', t['realm'], (t['q'], t['r']), 0.62), force=True)
    # 2 figure groups (cards), in the front half of their hex
    for g in layout['units']:
        if (g['q'], g['r']) not in vis: continue
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
        if (s['q'], s['r']) not in vis: continue
        cx, cz = hex_center(s['q'], s['r'])
        dz = -0.18 if any((u['q'], u['r']) == (s['q'], s['r']) for u in layout['units']) else 0.12
        add(model_piece(f"site_{s['q']}_{s['r']}", s['model'], cx - 0.05, cz + dz, 'site', None, (s['q'], s['r']), 1.35), force=True)
    # 4 forest hexes: a hut + woodpile (lumber) in its slot, then the clusters of trees around the inside of the dashed ring
    for (q, r), h in sorted(hexes.items()):
        if h['t'] != 'forest' or (q, r) not in vis: continue
        cx, cz = hex_center(q, r)
        if any((t['q'], t['r']) == (q, r) for t in layout['towns']): continue
        hx, hz = hut_slot((cx, cz), (q, r))
        sc = 2.1 + 0.4 * _hash(q, r, 1)
        lum = model_piece(f'lumber_{q}_{r}', 'lumber', hx, hz, 'lumber', None, (q, r), sc)
        placed = add(lum)
        avoid = [(hx, hz - 0.1, 0.42)] if placed else []
        for u in layout['units']:
            if (u['q'], u['r']) == (q, r):
                avoid.append((cx, cz + 0.5, 0.55))
        trees = forest_trees((cx, cz), (q, r), avoid)
        for i, (x, z, sp, rd, ht) in enumerate(trees):
            p = tree_piece(f'tree_{q}_{r}_{i}', x, z, sp, rd, ht, (q, r), int(_hash(q, r, i, 3) * 1e6))
            # trees may overlap each other's icons but not the big pieces
            if all(not overlap(p['icon'], o) for o in occupied):
                pieces.append(p)
    return pieces


if __name__ == '__main__':
    L = json.load(open(f'{POC}/data/layout.json'))
    ps = plan(L)
    from collections import Counter
    print(len(ps), Counter(p['kind'] for p in ps))
    json.dump(ps, open(f'{POC}/data/pieces.json', 'w'), indent=0)
