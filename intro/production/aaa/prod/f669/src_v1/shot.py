"""S09 'Every lord looked at the empty chair' (f561-716) - shot description as functions of the frame number.

    render_frame(f, out_wh=(2560, 1440)) -> dict(img (uint8 sRGB), lin, alpha, timing, ...)

Camera (storyboard S09): locked 1.06x with 1 px/frame drift (throne at frame x 0.47 at f598), exponential push
1.06 -> 1.25x f637-669 landing on the void at frame x 0.47, then hold with 2 px/frame drift.
Light: ONE guttered 1900 K candle off the top-left of the panel, 12 deg at the throne, as a shadowed point practical
whose pool is shaped by the key-light pool (candle_relight.py); cool night fill at ~1:6.
Act: II (age 1.0: re-dye, tideline, foxing; goblets / stitched candles are needle-hole ghosts in p1_oath_ground).
Unpick f561-640 on twos (kingvoid.py, loose.py); crown slip 15 mm up on four gold tethers (crown.py)."""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
AAA = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(AAA, 'lib'))
sys.path.insert(0, HERE)
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, cv2
cv2.setNumThreads(2)
from chron.config import MAPS
from chron.maps import MapSet
from chron import frontal, shade, grade
from chron.anim.groupanim import GroupAnim
from chron.color import light_colour, hex_lin, pal
from chron.util import vnoise, sstep
from chron.qa.void import check_void
import candle_relight
from kingvoid import KingVoid
from loose import LooseEnds, HoleResidue
from crown import CrownSlip
from groundfix import GroundFix
from threads3d import ThreadSet

candle_relight.install()

F0, F_PUSH0, F_PUSH1, F_END = 561, 637, 669, 716
F1_PX = 4.65                       # 1.0x = F1 framing (panel width fills the frame)
THRONE_X = 294.5                   # sheet mm: panel x 0.527 at 1.06x puts this at frame x 0.47
FRAME_CY = 173.0
VOID_C = (297.0, 200.0)            # reference point of the 12 deg candle
LIFT = 15.0
RIPPLE = 260                        # entries ahead of the unpick front that have slackened (lifted relief)

# ------------------------------------------------------------------ camera
def zoom(f):
    if f <= F_PUSH0: return 1.06
    if f >= F_PUSH1: return 1.25
    t = (f - F_PUSH0) / (F_PUSH1 - F_PUSH0)
    e = t * t * (3 - 2 * t)
    return 1.06 * (1.25 / 1.06) ** e


def throne_screen_x(f, W=2560):
    """screen x (px at 2560 wide) of the throne axis."""
    X47 = 0.47 * W
    if f <= F_PUSH0:
        return X47 - (f - 598) * 1.0
    if f >= F_PUSH1:
        return X47 - (f - F_PUSH1) * 2.0
    t = (f - F_PUSH0) / (F_PUSH1 - F_PUSH0); e = t * t * (3 - 2 * t)
    return (X47 - (F_PUSH0 - 598)) * (1 - e) + X47 * e


def view_of(f, out_wh=(2560, 1440)):
    k = out_wh[0] / 2560.0
    s = F1_PX * zoom(f) * k
    X = throne_screen_x(f) * k
    cx = THRONE_X + (out_wh[0] / 2 - X) / s
    return dict(cx_mm=float(cx), cy_mm=FRAME_CY, px_per_mm=float(s))


# ------------------------------------------------------------------ light
AZ_V, EL_V, CZ = 108.0, 12.0, 70.0
_DH = CZ / math.tan(math.radians(EL_V))
CANDLE0 = (VOID_C[0] + _DH * math.cos(math.radians(AZ_V)), VOID_C[1] - _DH * math.sin(math.radians(AZ_V)), CZ)
REF = math.sqrt(_DH ** 2 + CZ ** 2)
I0 = 3.1                               # candle intensity at the void (before the pool)
GAMMA_PHYS = 0.3                      # fraction (in log) of the physical inverse-square falloff kept in the pool
POOL = dict(cx=297.0, cy=195.0, rx=95.0, ry_up=85.0, ry_dn=130.0, floor=0.0)
NIGHT = hex_lin('#141325'); NIGHT = NIGHT / NIGHT.max()
FILL_I = 0.045


def candle(f):
    t = f / 30.0
    flick = 1 + 0.022 * math.sin(2 * math.pi * 1.3 * t + 0.7) + 0.011 * math.sin(2 * math.pi * 2.1 * t + 2.1) \
        + 0.006 * math.sin(2 * math.pi * 7.7 * t + 0.3)
    x, y, z = CANDLE0
    x += 1.2 * math.sin(2 * math.pi * 0.9 * t + 1.0)
    y += 0.6 * math.sin(2 * math.pi * 0.7 * t)
    return dict(pos_mm=(x, y, z), K=1900, tint=0.45, i=I0 * flick, ref_mm=REF)


def light_of(f):
    c = candle(f)
    lt = shade.rig(az=AZ_V, el=EL_V, K=1900, key_i=c['i'] * 0.75, tint=0.45, fill=NIGHT, fill_i=FILL_I * I0,
                   points=[], k_env=0.35)
    lt['candle'] = c
    return lt


def pool_target(x, y):
    p = POOL
    ry = np.where(y < p['cy'], p['ry_up'], p['ry_dn'])
    d2 = ((x - p['cx']) / p['rx']) ** 2 + ((y - p['cy']) / ry) ** 2
    return p['floor'] + (1 - p['floor']) * np.exp(-d2)


def att(c, x, y, z=0.0):
    X, Y, Z = c['pos_mm']
    d2 = (X - x) ** 2 + (Y - y) ** 2 + (Z - z) ** 2
    return c['ref_mm'] ** 2 / d2


def kmap_fn(f):
    c = candle(f)
    def fn(m):
        H, W = m['h'].shape
        PX = m['PX']; ox, oy = m['origin_mm']
        xs = ox + np.arange(W, dtype=np.float32) / PX
        ys = oy + np.arange(H, dtype=np.float32) / PX
        X, Y = np.meshgrid(xs, ys)
        a = att(c, X, Y)
        return (pool_target(X, Y) * a ** (GAMMA_PHYS - 1.0)).astype(np.float32)
    return fn


def pool_at(f):
    c = candle(f)
    return lambda x, y: float(pool_target(x, y) * att(c, x, y, LIFT) ** (GAMMA_PHYS - 1.0))


def thread_light_fn(f):
    c = candle(f)
    col = light_colour(1900, 0.45) * c['i']
    def fn(P):
        a = att(c, P[:, 0], P[:, 1], P[:, 2])
        return (col[None, :] * (pool_target(P[:, 0], P[:, 1]) * a ** GAMMA_PHYS)[:, None]).astype(np.float32)
    return fn


# ------------------------------------------------------------------ tideline (a stain whose edge crosses the table cloth)
TIDES = [dict(c=(300.0, 420.0), rx=260.0, ry=175.0, seed=41, amp=0.035, w=1.0),
         dict(c=(118.0, 10.0), rx=150.0, ry=88.0, seed=43, amp=0.12, w=0.6)]


def tide_layer(m):
    H, W = m['h'].shape
    PX = m['PX']; ox, oy = m['origin_mm']
    xs = ox + np.arange(W, dtype=np.float32) / PX
    ys = oy + np.arange(H, dtype=np.float32) / PX
    X, Y = np.meshgrid(xs, ys)
    out = np.zeros((H, W), np.float32); edg = np.zeros((H, W), np.float32)
    for t in TIDES:
        cx, cy = t['c']
        if cx + 1.5 * t['rx'] < xs[0] or cx - 1.5 * t['rx'] > xs[-1] or cy + 1.5 * t['ry'] < ys[0] or cy - 1.5 * t['ry'] > ys[-1]:
            continue
        nz = vnoise(ox, oy, H, W, PX, 22.0, t['seed'], 3)
        d = np.hypot((X - cx) / t['rx'], (Y - cy) / t['ry']) + t['amp'] * nz
        R = t['ry']
        inside = sstep(1.0, 0.86, d) * 0.22 + sstep(1.0, 0.97, d) * 0.18
        edge = np.exp(-((d - 1.0) * R / 1.05) ** 2)
        edge2 = 0.45 * np.exp(-((d - (1.0 - 9.0 / R)) * R / 0.8) ** 2)
        out = np.maximum(out, t['w'] * np.clip(inside + edge + edge2, 0, 1))
        edg = np.maximum(edg, t['w'] * np.clip(edge + 0.6 * edge2, 0, 1))
    return out, edg


# ------------------------------------------------------------------ assets (built once per process)
_ASSETS = {}


def assets():
    if not _ASSETS:
        t = time.time()
        G = MapSet(MAPS + '/p1_oath_ground')
        kv = KingVoid(G)
        res = HoleResidue(kv)
        kv._snaps.clear()                      # the residue needed the fully-stitched state once; free it
        _ASSETS.update(G=G, kv=kv, loose=LooseEnds(kv), residue=res, crown=CrownSlip(GroupAnim(G, ['crown'])), gfix=GroundFix(G))
        print(f'[shot] assets {time.time() - t:.1f}s', flush=True)
    return _ASSETS


def crown_lift(f):
    """mm: the slip loses its support as the head is unpicked (f575-592) and rises to 15 mm on its tethers."""
    t = float(np.clip((f - 575) / 17.0, 0, 1))
    return LIFT * t * t * (3 - 2 * t)


def crown_turn(f):
    """degrees: settles from the lift (a slow pendulum) and turns very slightly through the gap."""
    t = (f - 640) / 30.0
    return 2.2 * math.sin(2 * math.pi * 0.21 * t + 0.6) * math.exp(-0.15 * max(t, 0)) + 1.1 * math.sin(2 * math.pi * 0.11 * t + 1.9)


GOLD = hex_lin('#E9BE6A')


EXPOSURE = 1.55
READ_KEYS = ['h', 'alb', 'T', 'mat', 'cov', 'age_fox', 'age_tide', 'age_fade', 'ghost']


def render_frame(f, out_wh=(2560, 1440), level=None, exposure=EXPOSURE, fib='auto', debug=False, threads=True,
                 free_tiles=None):
    """free_tiles: drop the MapSet's level-0 tile cache once the window has been read (keeps a 1440p L0 frame under
    ~3 GB peak; default on for single 1440p frames, set False when rendering many L0 frames in one process)."""
    if free_tiles is None:
        free_tiles = out_wh[0] >= 1900
    A = assets()
    G, kv, lo, cr = A['G'], A['kv'], A['loose'], A['crown']
    tm = {}
    t0 = time.time()
    view = view_of(f, out_wh)
    light = light_of(f)
    u = lo.u_of(f)

    def edit(m):
        A['gfix'].edit(m)
        kv.edit(u, ripple=RIPPLE, ripple_h=0.3)(m)
        if 'age_tide' in m:
            td, te = tide_layer(m)
            m['age_tide'] = np.maximum(m['age_tide'].astype(np.float32), td)
            m['alb'] = (m['alb'] * (1 - 0.36 * te - 0.10 * td)[..., None]).astype(np.float32)   # dried edge darker

    # read the window ourselves with only the channels the relight uses (same 8 mm margin as frontal.render), so the
    # level-0 tile cache can be dropped before the relight
    x0v, y0v, wv, hv, sv = frontal.view_rect(view, out_wh)
    lvl = G.level_for(sv) if level is None else level
    M8 = 8.0
    win = G.read(x0v - M8, y0v - M8, x0v + wv + M8, y0v + hv + M8, lvl, keys=READ_KEYS)
    if free_tiles:
        G._tiles.clear()
    fr = frontal.render(win, view, light, out_wh=out_wh, age=1.0, kmap=kmap_fn(f), edit=edit,
                        fib=fib, fib_seed=669, timing=tm)
    fr['level'] = lvl
    check_void(fr['lin'], fr['alpha'], name=f'f{f}')
    lin = fr['lin']
    t1 = time.time()
    # crown slip
    lift = crown_lift(f)
    L_ = cr.layers(view, light, max(lift, 0.05), crown_turn(f) * lift / LIFT, pool_at(f), out_wh=out_wh, fib_seed=f)
    key_frac = 0.84
    lin = lin * (1 - key_frac * L_['shadow'][..., None])
    ctx = dict(x0=L_['x0'], y0=L_['y0'], s=L_['s'])
    cpos = light['candle']['pos_mm']
    lfn0 = thread_light_fn(f)
    shm = L_['shadow']

    def lfn(P):                      # threads lying in the crown's shadow lose the candle too
        q = np.stack([(P[:, 0] - ctx['x0']) * ctx['s'], (P[:, 1] - ctx['y0']) * ctx['s']], 1).astype(int)
        qx = np.clip(q[:, 0], 0, shm.shape[1] - 1); qy = np.clip(q[:, 1], 0, shm.shape[0] - 1)
        occ = 1 - key_frac * shm[qy, qx] * np.clip(1 - P[:, 2] / max(lift, 0.5), 0, 1)
        return lfn0(P) * occ[:, None]
    fill = NIGHT * FILL_I * I0
    # needle holes where the tethers enter the cloth
    if lift > 1.0:
        H_, W_ = lin.shape[:2]
        for hx, hy in cr.holes:
            X, Y = (hx - ctx['x0']) * ctx['s'], (hy - ctx['y0']) * ctx['s']
            r0 = int(max(4, 1.5 * ctx['s']))
            xa, xb, ya, yb = max(int(X) - r0, 0), min(int(X) + r0 + 1, W_), max(int(Y) - r0, 0), min(int(Y) + r0 + 1, H_)
            if xb <= xa or yb <= ya: continue
            yy, xx = np.mgrid[ya:yb, xa:xb].astype(np.float32)
            g = np.exp(-((xx + 0.5 - X) ** 2 + (yy + 0.5 - Y) ** 2) / (2 * (0.32 * ctx['s']) ** 2))
            lin[ya:yb, xa:xb] *= (1 - 0.65 * g)[..., None]
    tth = ThreadSet()
    for i, P in enumerate(cr.tether_curves(L_, lift, seed=3) if lift > 1.0 else []):
        tth.add(P, 0.34, GOLD * 1.0, kind=1, pitch_mm=0.42, seed=i / 4.0, shadow=1.0)
    tth.render(lin, ctx, cpos, lfn, fill, shadow_strength=key_frac, fuzz=False)
    t2 = time.time()
    nlive = 0
    if threads:                      # loose ends and residue lie below the slip (z < lift): drawn before it
        ts = ThreadSet()
        nlive = lo.add_to(ts, f)
        A['residue'].add_to(ts, u)
        ts.render(lin, ctx, cpos, lfn, fill, shadow_strength=key_frac, fuzz=out_wh[0] >= 1900, fuzz_seed=f)
    a = L_['alpha'][..., None]
    lin = lin * (1 - a) + L_['rgb'] * a
    t3 = time.time()
    img = grade.grade(lin, exposure=exposure, act='II', seed=f)
    tm.update(base=t1 - t0, crown=t2 - t1, threads=t3 - t2, total=time.time() - t0, loose=nlive, u=u, view=view)
    out = dict(img=img, lin=lin, alpha=fr['alpha'], timing=tm, view=view, level=fr['level'])
    return out
