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
from chron.color import light_colour, hex_lin, pal, lin2oklab
from chron.util import vnoise, sstep
from chron.qa.void import check_void
import candle_relight
from kingvoid import KingVoid
from loose import LooseEnds, HoleResidue
from crown import CrownSlip
from groundfix import GroundFix
from threads3d import ThreadSet
import voidfx as VFX

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


VIEW_OVERRIDE = None      # look-dev: render a window of the f669 frame at 100 % (dict cx_mm, cy_mm, px_per_mm)


def view_of(f, out_wh=(2560, 1440)):
    if VIEW_OVERRIDE is not None:
        return dict(VIEW_OVERRIDE)
    k = out_wh[0] / 2560.0
    s = F1_PX * zoom(f) * k
    X = throne_screen_x(f) * k
    cx = THRONE_X + (out_wh[0] / 2 - X) / s
    return dict(cx_mm=float(cx), cy_mm=FRAME_CY, px_per_mm=float(s))


# ------------------------------------------------------------------ light
def _E(name, default):
    return float(os.environ.get(name, default))


AZ_V, EL_V, CZ = _E('F669_AZ', 121.0), _E('F669_EL', 12.0), _E('F669_CZ', 80.0)
_DH = CZ / math.tan(math.radians(EL_V))
CANDLE0 = (VOID_C[0] + _DH * math.cos(math.radians(AZ_V)), VOID_C[1] - _DH * math.sin(math.radians(AZ_V)), CZ)
REF = math.sqrt(_DH ** 2 + CZ ** 2)
I0 = _E('F669_I0', 3.1)                # candle intensity at the void (before the pool)
GAMMA_PHYS = _E('F669_GAMMA', 0.45)    # fraction (in log) of the physical inverse-square falloff kept in the pool
# the pool is shaped by the candle's side: bright toward the upper-left (the candle), falling away to the lower-right
POOL = dict(cx=_E('F669_PCX', 277.0), cy=_E('F669_PCY', 170.0), rx_l=_E('F669_RXL', 105.0), rx_r=_E('F669_RXR', 88.0),
            ry_up=_E('F669_RYU', 88.0), ry_dn=_E('F669_RYD', 108.0), floor=_E('F669_FLOOR', 0.04), amp=_E('F669_AMP', 0.62))
NIGHT = hex_lin('#141325'); NIGHT = NIGHT / NIGHT.max()
FILL_I = _E('F669_FILL', 0.05)


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
    rx = np.where(x < p['cx'], p['rx_l'], p['rx_r'])
    d2 = ((x - p['cx']) / rx) ** 2 + ((y - p['cy']) / ry) ** 2
    return p['amp'] * (p['floor'] + (1 - p['floor']) * np.exp(-d2))


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
TIDES = [dict(c=(300.0, 420.0), rx=262.0, ry=176.0, seed=41, amp=0.045, w=1.0),
         dict(c=(118.0, 10.0), rx=150.0, ry=88.0, seed=43, amp=0.10, w=0.22)]


def tide_layer(m):
    H, W = m['h'].shape
    PX = m['PX']; ox, oy = m['origin_mm']
    xs = ox + np.arange(W, dtype=np.float32) / PX
    ys = oy + np.arange(H, dtype=np.float32) / PX
    X, Y = np.meshgrid(xs, ys)
    out = np.zeros((H, W), np.float32); edg = np.zeros((H, W), np.float32); bleach = np.zeros((H, W), np.float32)
    for t in TIDES:
        cx, cy = t['c']
        if cx + 1.5 * t['rx'] < xs[0] or cx - 1.5 * t['rx'] > xs[-1] or cy + 1.5 * t['ry'] < ys[0] or cy - 1.5 * t['ry'] > ys[-1]:
            continue
        nz = vnoise(ox, oy, H, W, PX, 22.0, t['seed'], 3)
        d = np.hypot((X - cx) / t['rx'], (Y - cy) / t['ry']) + t['amp'] * nz
        R = t['ry']
        inside = sstep(1.0, 0.86, d) * 0.34 + sstep(1.0, 0.97, d) * 0.20       # stained interior
        edge = np.exp(-((d - 1.0) * R / 1.7) ** 2)                              # the dried edge: darker, ~3 mm
        edge2 = 0.6 * np.exp(-((d - (1.0 - 11.0 / R)) * R / 1.2) ** 2)         # a lighter-banded inner ring
        wash = -0.35 * np.exp(-((d - (1.0 + 7.0 / R)) * R / 4.0) ** 2)          # a faint bleached margin just outside
        out = np.maximum(out, t['w'] * np.clip(inside + edge + edge2, 0, 1))
        bleach = np.maximum(bleach, -t['w'] * wash)
        edg = np.maximum(edg, t['w'] * np.clip(edge + 0.6 * edge2, 0, 1))
    return out, edg, bleach


# ------------------------------------------------------------------ assets (built once per process)
_ASSETS = {}


def assets():
    if not _ASSETS:
        t = time.time()
        G = MapSet(MAPS + '/p1_oath_ground')
        kv = KingVoid(G)
        res = HoleResidue(kv)
        kv._snaps.clear()                      # the residue needed the fully-stitched state once; free it
        gfix = GroundFix(G)
        crown = CrownSlip(GroupAnim(G, ['crown']), tip_ids=gfix.tips)
        print('[shot] tether holes ->', crown.snap_holes_to_linen(G).round(1).tolist())
        _ASSETS.update(G=G, kv=kv, loose=LooseEnds(kv), residue=res, crown=crown, gfix=gfix)
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
GOLD_CORD = hex_lin('#CFA04C')           # couched gold cord (wrapped Japan gold over a silk core)


EXPOSURE = _E('F669_EXPO', 1.55)
READ_KEYS = ['h', 'alb', 'T', 'mat', 'cov', 'age_fox', 'age_tide', 'age_fade']
LINEN_GAIN = np.array([_E('F669_LGR', 0.84), _E('F669_LGG', 0.80), _E('F669_LGB', 0.72)], np.float32)   # a century of light: the linen itself is darker / browner than the library's Act II
COOL_LIFT = _E('F669_COOL', 0.035)
SHADOW_D = _E('F669_SHD', 0.50)                                       # crown shadow density on the lit linen (about -0.9 EV)
SHADOW_TINT = np.array([1.0, 0.94, 0.80], np.float32)                 # cool: the warm candle is what the crown takes away


def age_amount(m, strip=512):
    """age amount map: 1.0 everywhere (Act II), a notch more on dyed wool (sat toward 0.7), and the king's royal purple
    (the banner) aged hard: purple leaves with the king.  (row strips: RAM)"""
    alb = m['alb']; mat = m['mat']
    H, W = mat.shape
    out = np.empty((H, W), np.float32)
    for r0 in range(0, H, strip):
        r1 = min(H, r0 + strip)
        lab = lin2oklab(alb[r0:r1])
        C = np.hypot(lab[..., 1], lab[..., 2])
        hue = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
        pur = np.clip(1 - np.abs(((hue - 322 + 180) % 360) - 180) / 55.0, 0, 1) * np.clip((C - 0.02) / 0.04, 0, 1)
        dyed = (mat[r0:r1] != 0)
        out[r0:r1] = np.where(dyed, 1.12 + 0.75 * pur, 1.0)
    return out


def lvl_hint(level, out_wh):
    """True when the frame is shaded from the 5 px/mm mip (L1): the weave there is attenuated with the screen scale; frames
    shaded from the 10 px/mm level (L0, antialiased by the Lanczos warp) carry the full enrichment, so one grade covers both."""
    return level == 1


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
    resolv = float(np.clip((view['px_per_mm'] - 2.6) / (5.2 - 2.6), 0.3, 1.0)) if lvl_hint(level, out_wh) else 1.0   # how much of the weave the frame can resolve

    def edit(m):
        if not os.environ.get('F669_NOPATCH'):
            A['gfix'].edit(m)
        kv.edit(u, ripple=RIPPLE, ripple_h=0.3)(m)
        if 'age_tide' in m:
            td, te, bl = tide_layer(m)
            m['age_tide'] = np.maximum(m['age_tide'].astype(np.float32), td)
            m['alb'] = (m['alb'] * (1 - 0.60 * te - 0.12 * td + 0.10 * bl)[..., None]).astype(np.float32)   # dried edge darker
        if not os.environ.get('F669_NOENRICH'):
            VFX.linen_enrich(m, strength=0.5 * resolv, relief=1.0 + 0.18 * resolv, wander_mm=0.17 * (0.5 + 0.5 * resolv))
        lm = (m['mat'] == 0)
        m['alb'] = np.where(lm[..., None], m['alb'] * LINEN_GAIN, m['alb']).astype(np.float32)

    # read the window ourselves with only the channels the relight uses (same 8 mm margin as frontal.render), so the
    # level-0 tile cache can be dropped before the relight
    x0v, y0v, wv, hv, sv = frontal.view_rect(view, out_wh)
    lvl = G.level_for(sv) if level is None else level
    M8 = 8.0
    win = G.read(x0v - M8, y0v - M8, x0v + wv + M8, y0v + hv + M8, lvl, keys=READ_KEYS)
    if free_tiles:
        G._tiles.clear()
    fr = frontal.render(win, view, light, out_wh=out_wh, age=age_amount, kmap=kmap_fn(f), edit=edit,
                        fib=fib, fib_seed=669, timing=tm)
    fr['level'] = lvl
    check_void(fr['lin'], fr['alpha'], name=f'f{f}')
    lin = fr['lin']
    t1 = time.time()
    # ------------------------------------------------------------------ crown slip
    lift = crown_lift(f)
    L_ = cr.layers(view, light, max(lift, 0.05), crown_turn(f) * lift / LIFT, pool_at(f), out_wh=out_wh, fib_seed=f)
    key_frac = 0.84
    # crown + tether shadow: a density on the lit cloth (the fill and the bounce stay), cool-tinted, applied before the
    # grade so weave and needle holes keep their contrast inside it
    sh = 1 - (1 - L_['shadow']) * (1 - 0.9 * L_['tether_shadow'])
    lin = lin * (1 - SHADOW_D * sh[..., None] * SHADOW_TINT[None, None, :])
    ao = L_['ao'] * (1 - L_['alpha'])                                  # soft occlusion under the lifted rim
    lin = lin * (1 - 0.36 * ao)[..., None]
    ctx = dict(x0=L_['x0'], y0=L_['y0'], s=L_['s'])
    cpos = light['candle']['pos_mm']
    lfn0 = thread_light_fn(f)
    shm = sh

    def lfn(P):                      # threads lying in the crown's shadow lose the candle too
        q = np.stack([(P[:, 0] - ctx['x0']) * ctx['s'], (P[:, 1] - ctx['y0']) * ctx['s']], 1).astype(int)
        qx = np.clip(q[:, 0], 0, shm.shape[1] - 1); qy = np.clip(q[:, 1], 0, shm.shape[0] - 1)
        occ = 1 - 1.5 * SHADOW_D * shm[qy, qx] * np.clip(1 - P[:, 2] / max(lift, 0.5), 0, 1)
        return lfn0(P) * np.clip(occ, 0.1, 1)[:, None]
    fill = NIGHT * FILL_I * I0
    # needle holes where the tethers enter the cloth (a pit, a puckered ring of displaced weave)
    if lift > 1.0:
        H_, W_ = lin.shape[:2]
        for hx, hy in cr.holes:
            X, Y = (hx - ctx['x0']) * ctx['s'], (hy - ctx['y0']) * ctx['s']
            r0 = int(max(5, 2.2 * ctx['s']))
            xa, xb, ya, yb = max(int(X) - r0, 0), min(int(X) + r0 + 1, W_), max(int(Y) - r0, 0), min(int(Y) + r0 + 1, H_)
            if xb <= xa or yb <= ya: continue
            yy, xx = np.mgrid[ya:yb, xa:xb].astype(np.float32)
            rr2 = (xx + 0.5 - X) ** 2 + (yy + 0.5 - Y) ** 2
            g = np.exp(-rr2 / (2 * (0.30 * ctx['s']) ** 2))
            ring = np.exp(-((np.sqrt(rr2) - 0.85 * ctx['s']) / (0.35 * ctx['s'])) ** 2)
            lin[ya:yb, xa:xb] *= (1 - 0.62 * g + 0.10 * ring)[..., None]
    tth = ThreadSet()
    for i, P in enumerate(L_['curves'] if lift > 1.0 else []):
        tth.add(P, 0.50, GOLD_CORD, kind=3, seed=i / 4.0, shadow=0.0, halo=0.0, dip_end=True)
    tth.render(lin, ctx, cpos, lfn, fill, shadow_strength=key_frac, fuzz=False)
    t2 = time.time()
    nlive = 0
    if threads:                      # loose ends and residue lie below the slip (z < lift): drawn before it
        ts = ThreadSet()
        nlive = lo.add_to(ts, f)
        A['residue'].add_to(ts, u)
        ts.render(lin, ctx, cpos, lfn, fill, shadow_strength=key_frac, fuzz=out_wh[0] >= 1900, fuzz_seed=f, flame_r_mm=6.0)
    a = L_['alpha'][..., None]
    lin = lin * (1 - a) + L_['rgb'] * a
    t3 = time.time()
    # cool night lift in the deepest shadows (Act II: the night fill, #141325, is what the dark parts of the cloth show)
    Yl = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    lin = lin + COOL_LIFT * NIGHT[None, None, :] * np.exp(-Yl / 0.045)[..., None]
    img = grade.grade(lin, exposure=exposure, act='II', seed=f)
    tm.update(base=t1 - t0, crown=t2 - t1, threads=t3 - t2, total=time.time() - t0, loose=nlive, u=u, view=view)
    out = dict(img=img, lin=lin, alpha=fr['alpha'], timing=tm, view=view, level=fr['level'])
    if debug:
        out.update(L=L_, sh=sh)
    return out
