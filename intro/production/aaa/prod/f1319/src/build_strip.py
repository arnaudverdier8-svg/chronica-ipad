"""Build the S18 chronicle strip in strip-local coordinates (u along the length, v across), working density PX px/mm.
Sections (frieze order, SINE HEREDE strip omitted so that realm / oath / death / empty chair / war / ruin fit one frame):
  realm | T1 | p1 oath | T2 | p3 death | T3 | p1' (empty chair) | war (needle-hole field) | burn-through | p6 ruin | continuation
A continuous border band (flowers, lions, bars) runs above all of them; one continuous couched gold thread runs on its rule.
Output: work/strip_<PX>.npz  (h, alb, T, mat, cov, fox, tide, fade, ghost, + meta json)"""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
from chron.linen import make_linen
from chron.color import hex_lin, pal, lin2oklab, oklab2lin
from chron.util import vnoise, sstep, hash1
from chron.config import LINEN, WOOL, SILK, METAL, INK, CORD

PX = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
HS = 400.0           # strip height, mm
BAND = 78.0          # border band height, mm
DIV = 60.0           # tree divider width
KEYS = ('h', 'alb', 'T', 'mat', 'cov', 'fox', 'tide', 'fade', 'ghost')


def mm(x): return int(round(x * PX))


def load(n):
    z = np.load(f'{WORK}/panel_{n}_{PX:g}.npz')
    m = {}
    for k in z.files:
        v = z[k]
        m[k] = v.astype(np.float32) if v.dtype == np.float16 else v
    m['fox'] = m.pop('age_fox'); m['tide'] = m.pop('age_tide'); m['fade'] = m.pop('age_fade')
    m['PX'] = PX
    return m


def blank(Hpx, Wpx):
    return dict(h=np.zeros((Hpx, Wpx), np.float32), alb=np.zeros((Hpx, Wpx, 3), np.float32), T=np.zeros((Hpx, Wpx, 2), np.float32),
                mat=np.zeros((Hpx, Wpx), np.uint8), cov=np.zeros((Hpx, Wpx), np.float32), fox=np.zeros((Hpx, Wpx), np.float32),
                tide=np.zeros((Hpx, Wpx), np.float32), fade=np.full((Hpx, Wpx), 0.5, np.float32), ghost=np.zeros((Hpx, Wpx), np.float32))


def crop(m, x0, y0, x1, y1):
    return {k: (v[y0:y1, x0:x1] if isinstance(v, np.ndarray) and v.ndim >= 2 else v) for k, v in m.items()}


def paste(dst, src, x0, y0, mask=None):
    """copy src maps into dst at integer px (x0, y0) (clipped); mask HxW bool/float (default all)."""
    H, W = src['h'].shape
    X0, Y0 = max(x0, 0), max(y0, 0)
    X1, Y1 = min(x0 + W, dst['h'].shape[1]), min(y0 + H, dst['h'].shape[0])
    if X1 <= X0 or Y1 <= Y0: return
    sl_d = (slice(Y0, Y1), slice(X0, X1)); sl_s = (slice(Y0 - y0, Y1 - y0), slice(X0 - x0, X1 - x0))
    for k in KEYS:
        if k not in src: continue
        if mask is None:
            dst[k][sl_d] = src[k][sl_s]
        else:
            mk = mask[sl_s]
            d = dst[k][sl_d]
            d[mk] = src[k][sl_s][mk]


def flip_x(m):
    o = {k: (v[:, ::-1].copy() if isinstance(v, np.ndarray) and v.ndim >= 2 else v) for k, v in m.items()}
    o['T'][..., 0] *= -1
    return o


def reflect_pad_bottom(m, n):
    """extend a section downward by n px with a reflection (fields continue)."""
    out = {}
    for k, v in m.items():
        if isinstance(v, np.ndarray) and v.ndim >= 2:
            ext = v[-n - 1:-1][::-1].copy() if n < v.shape[0] else v[::-1][:n].copy()
            if k == 'T': ext[..., 1] *= -1
            out[k] = np.concatenate([v, ext], 0)
        else:
            out[k] = v
    return out


# ------------------------------------------------------------------------------------------------ gold thread
def erase_gold(S, v0, v1):
    """remove baked gold lines (mat 3) between rows v0..v1 mm and refill from plain linen rows (1..6 mm) of the same columns."""
    a, b = mm(v0), mm(v1)
    reg = S['mat'][a:b] == 3
    reg = cv2.dilate(reg.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    ra = np.arange(a, b)
    src_rows = mm(1.0) + (ra % max(1, mm(5.0)))
    for k in KEYS:
        if k in ('fox', 'tide', 'fade', 'ghost'): continue
        blk = S[k][src_rows]
        cur = S[k][a:b]
        cur[reg] = blk[reg]
    return S


def gold_thread(S, Ls, seed=11):
    """continuous 2-ply couched gold thread along the rule at v ~ 17 mm.  NOT painted into the strip maps (the thread must
    survive where the cloth frays away): returns dict(vc (mm, per px column), tarnish t (0 dull .. 1 bright), ties (list of u mm))."""
    W = S['h'].shape[1]
    r = np.random.default_rng(seed)
    uu = np.arange(W) / PX
    wob = np.zeros(W, np.float32)
    for sc, amp in ((420.0, 1.4), (110.0, 0.7), (28.0, 0.25)):
        g = r.standard_normal(int(Ls / sc) + 4)
        wob += amp * np.interp(uu / sc, np.arange(len(g)), g)
    vc = 16.8 + wob * 0.8
    t = np.interp(uu / 300.0, np.arange(int(Ls / 300) + 4), r.random(int(Ls / 300) + 4))
    t = np.clip(0.10 + 0.30 * t, 0, 1) * (0.7 + 0.3 * (0.5 + 0.5 * np.sin(uu / 37.0 + r.uniform(0, 6))))   # tarnished: dull #7A5A2A-ish
    t = np.maximum(t, np.clip((uu - 3250.0) / 170.0, 0, 1) ** 1.5 * 0.95)                                   # the survivor: bright from u ~ 3250 on
    ties = []
    u = 70.0
    while u < Ls:
        ties.append(u); u += r.uniform(22, 40)
    return dict(vc=vc.astype(np.float32), t=t.astype(np.float32), ties=np.array(ties, np.float32))


# ------------------------------------------------------------------------------------------------ tree divider
def tree_divider(Wmm, Hmm, seed=3, trunk_cols=('crimson', 'builders_ochre', 'woad_dark', 'heraldic_green'), charred=0.0):
    """stylised interlace tree (couched wool, outlined) on a transparent ground: banded trunk (house colours),
    S-curved branches with leaf tufts.  Returns maps + 'wool' coverage (0..1)."""
    SS = 4
    Wp, Hp = int(round(Wmm * PX)), int(round(Hmm * PX))
    W, H = Wp * SS, Hp * SS
    r = np.random.default_rng(seed)
    S_ = PX * SS
    trunk = np.zeros((H, W), np.uint8)
    brm = np.zeros((H, W), np.uint8)
    leafm = np.zeros((H, W), np.uint8)
    cx = Wmm / 2
    trunk_w = 14.0
    ytop = Hmm * 0.34
    cv2.rectangle(trunk, (int((cx - trunk_w / 2) * S_), int(ytop * S_)), (int((cx + trunk_w / 2) * S_), H - 1), 255, -1)
    for k, yf in enumerate((0.38, 0.52, 0.66)):
        y0 = Hmm * yf
        for side in (-1, 1):
            amp = Wmm * (0.40 + 0.06 * r.random())
            pts = []
            for t in np.linspace(0, 1, 28):
                x = cx + side * amp * np.sin(t * 1.7) * (0.30 + 0.70 * t)
                y = y0 - 62 * t * (1.15 - 0.30 * k) + 12 * np.sin(t * 6.0 + k + (0 if side < 0 else 1.7))
                pts.append((x, y))
            P = (np.array(pts, np.float32) * S_).astype(np.int32)
            cv2.polylines(brm, [P], False, 255, int(4.6 * S_), cv2.LINE_AA)
            for (x, y) in pts[-7:]:
                for _ in range(2):
                    lx, ly = x + r.normal(0, 3.5), y + r.normal(0, 3.5)
                    cv2.ellipse(leafm, (int(lx * S_), int(ly * S_)), (int(5.2 * S_), int(2.6 * S_)), float(r.uniform(0, 180)), 0, 360, 255, -1, cv2.LINE_AA)
    top = [(cx + 9 * np.sin(t * 9) * (1 - 0.3 * t), ytop - 95 * t) for t in np.linspace(0, 1, 32)]
    cv2.polylines(brm, [(np.array(top, np.float32) * S_).astype(np.int32)], False, 255, int(4.6 * S_), cv2.LINE_AA)
    for (x, y) in top[-6:]:
        cv2.ellipse(leafm, (int(x * S_), int(y * S_)), (int(5.2 * S_), int(2.6 * S_)), float(r.uniform(0, 180)), 0, 360, 255, -1, cv2.LINE_AA)
    wool_ss = np.maximum(np.maximum(trunk, brm), leafm)
    ring = cv2.morphologyEx(wool_ss, cv2.MORPH_GRADIENT, np.ones((int(1.6 * S_) | 1, int(1.6 * S_) | 1), np.uint8))   # blue-black outline
    dn = lambda a: cv2.resize(a.astype(np.float32) / 255.0, (Wp, Hp), interpolation=cv2.INTER_AREA)
    Tm, Bm, Lm, Wm, Rm = dn(trunk), dn(brm), dn(leafm), dn(wool_ss), dn(ring)
    D = blank(Hp, Wp)
    pc = [pal(c) for c in trunk_cols]
    band = np.zeros((Hp, Wp), np.int32)
    bh = int(round(24 * PX))
    for i, y in enumerate(range(int(ytop * PX), Hp, bh)):
        band[y:y + bh] = i % 4
    albT = np.zeros((Hp, Wp, 3), np.float32)
    for i in range(4):
        albT[band == i] = pc[i]
    albB = np.broadcast_to(pal('mustard') * 0.85, (Hp, Wp, 3))
    albL = np.broadcast_to(pal('olive'), (Hp, Wp, 3))
    col = np.where((Lm > 0.5)[..., None], albL, np.where((Bm > 0.5)[..., None], albB, np.where((Tm > 0.5)[..., None], albT, albB)))
    if charred > 0:
        col = col * (1 - charred) + pal('soot')[None, None] * charred
    inkc = pal('ink_blueblack')
    col = col * (1 - 0.8 * Rm[..., None]) + inkc * 0.8 * Rm[..., None]
    wool = np.clip(Wm * 1.2, 0, 1)
    D['alb'] = (col * wool[..., None]).astype(np.float32)
    dist = cv2.distanceTransform((wool > 0.5).astype(np.uint8), cv2.DIST_L2, 3) / PX
    D['h'] = ((0.30 + 0.55 * np.minimum(dist / 2.0, 1)) * wool + 0.25 * Rm).astype(np.float32)
    D['mat'] = np.where(wool > 0.5, WOOL, 0).astype(np.uint8)
    D['mat'][Rm > 0.5] = INK
    D['T'][..., 1] = 1.0
    D['cov'] = np.where(D['mat'] == WOOL, 1.0, np.where(D['mat'] == INK, 0.5, 0.0)).astype(np.float32)
    D['wool'] = wool
    return D


def composite_over(S, D, x0, y0):
    """paste the part of D with wool>0.5 (and alpha-blend albedo at the rim) over S at px (x0, y0)."""
    a = D['wool']
    H, W = a.shape
    X0, Y0 = max(x0, 0), max(y0, 0); X1, Y1 = min(x0 + W, S['h'].shape[1]), min(y0 + H, S['h'].shape[0])
    sl_s = (slice(Y0 - y0, Y1 - y0), slice(X0 - x0, X1 - x0)); sl_d = (slice(Y0, Y1), slice(X0, X1))
    al = a[sl_s]
    S['alb'][sl_d] = S['alb'][sl_d] * (1 - al[..., None]) + D['alb'][sl_s] * al[..., None] / np.maximum(al[..., None], 1e-3) * al[..., None]
    hard = al > 0.5
    for k in ('h', 'T', 'mat', 'cov'):
        d = S[k][sl_d]; d[hard] = D[k][sl_s][hard]
    S['ghost'][sl_d][hard] = 0


# ------------------------------------------------------------------------------------------------ assembly
def build():
    t0 = time.time()
    Ls = 4100.0
    Wc, Hc = mm(Ls), mm(HS)
    # analytic linen as the base (translation invariant weave), then everything pasted over it
    ln = make_linen(Hc, Wc, PX, 0.0, 0.0, seed=21)
    S = blank(Hc, Wc)
    for k in ('h', 'alb', 'T', 'mat', 'cov'):
        S[k] = ln[k].astype(np.float32) if k != 'mat' else ln[k]
    del ln
    # ---- border band tiles
    realm = load('realm'); war = load('war'); warg = load('warg')
    tiles = [('realm', 0, 574, False), ('war', 8, 572, True), ('realm', 4, 574, True), ('war', 8, 572, False), ('realm', 4, 574, False),
             ('war', 8, 572, True), ('realm', 4, 574, True), ('war', 8, 572, False), ('realm', 4, 574, False)]
    src = dict(realm=realm, war=war)
    u = 0
    bandrows = mm(BAND)
    for n, xa, xb, fl in tiles:
        t = crop(src[n], mm(xa), 0, mm(xb), bandrows)
        if fl: t = flip_x(t)
        paste(S, t, mm(u), 0)
        u += (xb - xa)
        if u >= Ls: break
    erase_gold(S, 8, 26)
    # ---- register sections
    reg0 = mm(BAND)
    regH = Hc - reg0

    def section_panel(n, x_mm, reflect=True):
        m = load(n)
        if n in ('realm', 'war', 'warg'):
            rr = crop(m, 0, reg0, m['h'].shape[1], m['h'].shape[0])
            need = regH - rr['h'].shape[0]
            if need > 0: rr = reflect_pad_bottom(rr, need)
            rr = crop(rr, 0, 0, rr['h'].shape[1], regH)
        else:      # 20 mm margin panels: sheet row r -> v = r + 60
            r0 = reg0 - mm(60.0)
            rr = crop(m, 0, r0, m['h'].shape[1], r0 + regH)
        paste(S, rr, mm(x_mm), reg0)
    pos = dict(realm=0.0, T1=600.0, p1=660.0, T2=1250.4, p3=1310.4, T3=1900.8, p1g=1960.8, warg=2551.2, p6=3151.2)
    section_panel('realm', pos['realm']); section_panel('p1', pos['p1']); section_panel('p3', pos['p3'])
    section_panel('p1g', pos['p1g']); section_panel('warg', pos['warg']); section_panel('p6', pos['p6'])
    # ---- tree dividers T1..T3 (+ charred T4 after the ruin)
    cols = ('crimson', 'builders_ochre', 'woad_dark', 'heraldic_green')
    for k, (nm, seed, ch, tc, fl) in enumerate((('T1', 3, 0.0, cols, False), ('T2', 5, 0.0, cols[::-1], True), ('T3', 8, 0.0, cols[2:] + cols[:2], True))):
        D = tree_divider(DIV, HS - BAND, seed=seed, charred=ch, trunk_cols=tc)      # v2: three different trees (mirrored / re-banded), not clones
        if fl:
            for kk in list(D.keys()):
                if isinstance(D[kk], np.ndarray) and D[kk].ndim >= 2: D[kk] = D[kk][:, ::-1].copy()
        composite_over(S, D, mm(pos[nm]), reg0)
    D = tree_divider(DIV, HS - BAND, seed=13, charred=0.7)
    composite_over(S, D, mm(3741.6), reg0)
    th = gold_thread(S, Ls)
    np.savez_compressed(f'{WORK}/thread_{PX:g}.npz', **th)
    np.savez_compressed(f'{WORK}/strip_raw_{PX:g}.npz', **{k: v for k, v in S.items() if isinstance(v, np.ndarray)})
    json.dump(dict(PX=PX, Ls=Ls, Hs=HS, BAND=BAND, pos=pos), open(f'{WORK}/strip_meta_{PX:g}.json', 'w'))
    print('built', S['h'].shape, f'{time.time()-t0:.1f}s')
    return S


if __name__ == '__main__':
    S = build()
