"""Hand-checked layout of the seed-4242 menu world (terrain read from the rectified demo plates
data/rect_combined.png + the menu first frame; settlements/units from the menu first frame where visible).
Writes data/layout.json. Axial (q,r) relative to Grandbois = (0,0)."""
import json, math, sys
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from gamecam import hex_world
P = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc'
T = {}
def row(r, q0, s):
    for i, c in enumerate(s.split()):
        T[(q0 + i, r)] = {'h': 'hills', 'p': 'plains', 'f': 'forest', 'F': 'farm', 'm': 'mountain', 'l': 'lake', 's': 'sea', 'q': 'quarry'}[c]
# r = -6 .. 2 (q from left); everything else is sea
row(-6, -6, 'h h m m m p h h f f F F')
row(-5, -7, 'F h h m m p m m h f f F')
row(-4, -8, 'p h h h h h m m h f f F')
row(-3, -8, 'p l l h p p h h h h h p')
row(-2, -9, 'p f l l p p F p F F F F')
row(-1, -9, 'f F F p h f f f f f F F')
row(0, -10, 'f p F F f f f f f q f f f')
row(1, -10, 'p p F f f f f f f f h f f')
row(2, -5, 'F f f f f f f')
# ownership (realm borders) - gold = Grandbois/Hautecouronne realm, red = Sablon/Vaugrise/Brumecourt realm
gold = {(0, -2), (1, -2), (2, -2), (-1, -1), (0, -1), (1, -1), (2, -1), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (3, 0),
        (-2, 1), (-1, 1), (0, 1), (1, 1), (2, 1), (3, 1), (-2, 2), (-1, 2), (0, 2), (1, 2), (2, 2)}
red_seeds = [(-6, -1), (-2, -2), (-4, 1)]
def hd(a, b): return (abs(a[0] - b[0]) + abs(a[0] + a[1] - b[0] - b[1]) + abs(a[1] - b[1])) // 2
red = set()
for k, t in T.items():
    if t in ('sea', 'lake') or k in gold: continue
    if min(hd(k, s) for s in red_seeds) <= 2: red.add(k)
red |= {(-1, -3), (-2, -3)}
hexes = []
for q in range(-26, 22):
    for r in range(-10, 10):
        c = hex_world(q, r)
        if not (-17.5 < c[0] < 13.5 and -10.5 < c[2] < 10.0): continue
        t = T.get((q, r), 'sea')
        hexes.append(dict(q=q, r=r, x=round(float(c[0]), 4), z=round(float(c[2]), 4), t=t,
                          realm='gold' if (q, r) in gold else ('red' if (q, r) in red else None)))
towns = [dict(name='Grandbois', q=0, r=0, model='settle_3', realm='gold', banner=True),
         dict(name='Hautecouronne', q=2, r=1, model='settle_1_1', realm='gold'),
         dict(name='Sablon', q=-6, r=-1, model='settle_2', realm='red'),
         dict(name='Vaugrise', q=-2, r=-2, model='settle_1', realm='red'),
         dict(name='Brumecourt', q=-4, r=1, model='settle_1_2', realm='red')]
sites = [dict(q=-1, r=0, model='quarry'), dict(q=0, r=1, model='quarry')]
units = [dict(q=-2, r=1, unit='engineer', n=2, realm='gold'), dict(q=0, r=1, unit='engineer', n=2, realm='gold'),
         dict(q=1, r=1, unit='engineer', n=2, realm='gold'), dict(q=2, r=1, unit='engineer', n=3, realm='gold'),
         dict(q=-2, r=2, unit='spearman', n=3, realm='gold'), dict(q=1, r=2, unit='spearman', n=3, realm='gold'),
         dict(q=-6, r=0, unit='spearman', n=2, realm='red'), dict(q=-4, r=-1, unit='engineer', n=2, realm='red'),
         dict(q=-3, r=1, unit='spearman', n=2, realm='red')]
json.dump(dict(unit_mm=27.5, hexes=hexes, towns=towns, sites=sites, units=units,
               river=[[-4.6, -4.2], [-4.9, -3.4], [-5.5, -3.0], [-6.6, -2.6], [-7.7, -2.55], [-8.6, -2.35], [-9.4, -2.2], [-10.0, -2.4]],
               note='terrain from rectified demo plates (zoom 11 + zoom 30, seed 4242); settlements match the menu first frame'),
          open(f'{P}/data/layout.json', 'w'), indent=0)
from collections import Counter
print(len(hexes), Counter(h['t'] for h in hexes), len(gold), len(red))
