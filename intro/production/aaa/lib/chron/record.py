"""Stitch RECORD utilities: exact replay of any subset (in any order) into a working-maps window, bounding boxes,
needle-path ordering (gate G8) and the birth map.

Record arrays (stitches.npz): P (sum n_pts, 2) canvas px at level 0 | off (n+1) | typ (0 stitch, 1 squeeze event) |
fpar (n,14) | ipar (n,3: matid, seed, sid) | region | kind | group | unit | order (n: needle-path rank, -1 for none) |
plus group_names (json in the manifest)."""
import numpy as np
from .strands import replay_kernel
from .stitch import K_LAID, K_SPLIT, K_BAR, K_TIE, K_STEM, K_METAL, K_MTIE, K_CORD, K_CTIE, K_SATIN, K_SQUEEZE


def blank_like(m):
    """working maps for replay: copies of h/alb/T/mat/cov plus sid/sfr/base/stamp."""
    H, W = m['h'].shape
    o = {k: m[k].copy() for k in ('h', 'alb', 'T', 'mat', 'cov')}
    o['h'] = o['h'].astype(np.float32); o['alb'] = o['alb'].astype(np.float32); o['T'] = o['T'].astype(np.float32)
    o['cov'] = o['cov'].astype(np.float32)
    o['sid'] = (m['sid'].astype(np.int32).copy() if 'sid' in m else np.zeros((H, W), np.int32))
    o['sfr'] = np.zeros((H, W), np.float32)
    o['base'] = (m['base'].astype(np.float32).copy() if 'base' in m else
                 m['pad'].astype(np.float32).copy() if 'pad' in m else np.zeros((H, W), np.float32))
    o['stamp'] = np.zeros((H, W), np.int32)
    o['PX'] = m['PX']
    for k in ('origin_mm', 'inside'):
        if k in m: o[k] = m[k]
    return o


def replay(m, rec, idx, ox_px=0.0, oy_px=0.0, grow=None, hmul=None, PX=None):
    """rasterise record entries idx (in that order) into maps m whose pixel (0,0) is canvas level-0 px (ox_px, oy_px).
    If m is a mip (m['PX'] < record PX) the record is scaled on the fly."""
    idx = np.ascontiguousarray(np.asarray(idx, np.int64))
    if len(idx) == 0: return m
    g = np.ones(len(idx), np.float32) if grow is None else np.ascontiguousarray(grow, np.float32)
    hm = np.ones(len(idx), np.float32) if hmul is None else np.ascontiguousarray(hmul, np.float32)
    recPX = float(rec.get('PX', m['PX'])) if PX is None else PX
    s = m['PX'] / recPX
    P = rec['P'] if s == 1 else (rec['P'] * s).astype(np.float32)
    fpar = rec['fpar']
    if s != 1:
        fpar = fpar.copy(); sq = rec['typ'] == 1
        fpar[sq, 0] *= s
    replay_kernel(m['h'], m['alb'], m['T'], m['mat'], m['cov'], m['sid'], m['sfr'], m['base'], m['stamp'], idx,
                  rec['typ'], rec['off'], P, fpar, rec['ipar'], float(ox_px * s), float(oy_px * s), float(m['PX']), g, hm)
    return m


def bbox_of(rec, idx, pad_px=0):
    """(x0, y0, x1, y1) canvas level-0 px of a set of entries (incl. stitch radius)."""
    idx = np.asarray(idx)
    if len(idx) == 0: return None
    xs0, ys0, xs1, ys1 = [], [], [], []
    PX = float(rec.get('PX', 10.0))
    for k in idx:
        p = rec['P'][rec['off'][k]:rec['off'][k + 1]]
        r = rec['fpar'][k, 0] * PX if rec['typ'][k] == 0 else rec['fpar'][k, 0] * 2.5
        xs0.append(p[:, 0].min() - r); ys0.append(p[:, 1].min() - r); xs1.append(p[:, 0].max() + r); ys1.append(p[:, 1].max() + r)
    return (int(np.floor(min(xs0))) - pad_px, int(np.floor(min(ys0))) - pad_px, int(np.ceil(max(xs1))) + pad_px + 1,
            int(np.ceil(max(ys1))) + pad_px + 1)


def endpoints(rec, k):
    p = rec['P'][rec['off'][k]:rec['off'][k + 1]]
    return p[0], p[-1]


def mid(rec, k):
    p = rec['P'][rec['off'][k]:rec['off'][k + 1]]
    return p[len(p) // 2]


# ---------------------------------------------------------------- needle-path ordering
FILL_KINDS = (K_LAID, K_SPLIT, K_SATIN, K_METAL)
OUTLINE_REGION = 65535        # region id given to stem outlines / tituli (stitched after the fills of a group)


def _boustro(rec, ids, axis_deg=None):
    """laid work: strands side by side across the shape, alternating direction (a needle walking across)."""
    if len(ids) == 0: return [], []
    ids = np.asarray(ids)
    ends = np.concatenate([rec['P'][rec['off'][ids]], rec['P'][rec['off'][ids + 1] - 1]], 1).astype(np.float32)
    d = ends[:, 2:] - ends[:, :2]
    if axis_deg is None:
        a2 = np.arctan2(d[:, 1], d[:, 0]) * 2
        ang = 0.5 * np.arctan2(np.sin(a2).mean(), np.cos(a2).mean())
    else:
        ang = np.radians(axis_deg)
    nrm = np.array([-np.sin(ang), np.cos(ang)], np.float32)
    c = 0.5 * (ends[:, :2] + ends[:, 2:])
    key = c @ nrm
    o = np.argsort(key, kind='stable')
    flip = np.zeros(len(ids), bool)
    tdir = np.array([np.cos(ang), np.sin(ang)], np.float32)
    for j, i in enumerate(o):
        forward = (d[i] @ tdir) >= 0
        want = (j % 2 == 0)
        flip[i] = forward != want
    return list(ids[o]), list(flip[o])


def needle_order(rec, groups_order, policy=None, sweep=None):
    """returns (order array of entry indices, flip flags).  groups_order: list of group ids in stitching order.
    policy[g]: 'region' (default: region by region, nearest-neighbour between regions from the top-left; inside a region
    laid strands boustrophedon -> metal -> couching units (squeeze, bar, its ties) along the region's long axis;
    outlines (region OUTLINE_REGION) after all fills of the group, in path order) or 'sweep' (bottom->top bands of
    sweep[g] mm; inside a band fills then outlines; all couching units LAST, so that an unpick, which runs the order
    backwards, releases the couching first and then takes the strands top to bottom)."""
    policy = policy or {}
    sweep = sweep or {}
    n = len(rec['typ'])
    kind, unit, region, group = rec['kind'], rec['unit'], rec['region'], rec['group']
    off = rec['off']; P = rec['P']
    midi = (off[:-1] + off[1:]) // 2
    mids = P[np.clip(midi, 0, len(P) - 1)] if n else np.zeros((0, 2), np.float32)
    bar_units = np.unique(unit[kind == K_BAR])
    in_couch_all = np.isin(unit, bar_units) & (unit >= 0) & np.isin(kind, (K_BAR, K_TIE, K_SQUEEZE))
    order, flips = [], []

    def emit_units(ks_all):
        ukeys = {}
        for k in ks_all:
            ukeys.setdefault(int(unit[k]), []).append(int(k))
        return ukeys

    def unit_seq(ukeys, us):
        o = []
        for u in us:
            o += sorted(ukeys[u], key=lambda k: (0 if kind[k] == K_SQUEEZE else 1 if kind[k] == K_BAR else 2, k))
        return o

    for g in groups_order:
        gi = np.nonzero(group == g)[0]
        if len(gi) == 0: continue
        pol = policy.get(g, 'region')
        ic = in_couch_all[gi]
        if pol == 'sweep':
            band = sweep.get(g, 8.0) * float(rec.get('PX', 10.0))
            body = gi[~ic]
            yb = np.floor(mids[body, 1] / band)
            isout = np.isin(kind[body], (K_STEM, K_CORD, K_CTIE, K_MTIE)).astype(np.int32)
            for b in sorted(np.unique(yb))[::-1]:
                for o_ in (0, 1):
                    sel = body[(yb == b) & (isout == o_)]
                    if o_ == 0:
                        ids, fl = _boustro(rec, sel)
                        order += ids; flips += fl
                    else:
                        sel = np.sort(sel)
                        order += list(sel); flips += [False] * len(sel)
            ukeys = emit_units(gi[ic])
            us = sorted(ukeys, key=lambda u: -np.mean(mids[ukeys[u], 1]))
            seq = unit_seq(ukeys, us)
            order += seq; flips += [False] * len(seq)
            continue
        srt = gi[np.argsort(region[gi], kind='stable')]
        regs, starts = np.unique(region[srt], return_index=True)
        ends = list(starts[1:]) + [len(srt)]
        blocks = {int(r): srt[a:b] for r, a, b in zip(regs, starts, ends)}
        cen = {r: mids[blocks[r]].mean(0) for r in blocks}
        left = set(blocks) - {OUTLINE_REGION}; cur = np.array([0, 0], np.float32); seq = []
        while left:
            r = min(left, key=lambda q: float(np.sum((cen[q] - cur) ** 2)))
            seq.append(r); left.discard(r); cur = cen[r]
        if OUTLINE_REGION in blocks:
            seq.append(OUTLINE_REGION)
        for r in seq:
            ri = blocks[r]
            ric = in_couch_all[ri]
            fills = ri[np.isin(kind[ri], (K_LAID, K_SPLIT, K_SATIN)) & ~ric]
            ids, fl = _boustro(rec, fills)
            order += ids; flips += fl
            metal = ri[np.isin(kind[ri], (K_METAL, K_MTIE)) & ~ric]
            order += list(np.sort(metal)); flips += [False] * len(metal)
            ukeys = emit_units(ri[ric])
            if ukeys:
                us = list(ukeys)
                cc = np.array([mids[ukeys[u]].mean(0) for u in us], np.float32)
                if len(cc) > 2:
                    w, v = np.linalg.eigh(np.cov(cc.T))
                    proj = cc @ v[:, -1]
                else:
                    proj = cc[:, 0]
                s_ = unit_seq(ukeys, [us[j] for j in np.argsort(proj)])
                order += s_; flips += [False] * len(s_)
            rest = ri[~np.isin(kind[ri], (K_LAID, K_SPLIT, K_SATIN, K_METAL, K_MTIE)) & ~ric]
            rest = np.sort(rest)
            order += list(rest); flips += [False] * len(rest)
    seen = np.zeros(n, bool)
    if order: seen[np.array(order, np.int64)] = True
    miss = np.nonzero(~seen)[0]
    order += list(miss); flips += [False] * len(miss)
    return np.array(order, np.int64), np.array(flips, bool)


def apply_flips(rec, order, flips):
    """reverse the polylines of flipped strands in place (so growth starts at the needle's entry end)."""
    for k, f in zip(order, flips):
        if f and rec['typ'][k] == 0:
            a, b = rec['off'][k], rec['off'][k + 1]
            rec['P'][a:b] = rec['P'][a:b][::-1].copy()
