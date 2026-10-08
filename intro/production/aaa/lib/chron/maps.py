"""MapSet: the asset contract (pipeline section 3).  Tiled float16 npz at level 0 (2048 px tiles + 64 px overlap),
mips at 1/2, 1/4, 1/8 density, manifest.json, stitches.npz.  read() returns float32 working maps for any window in
sheet mm; anything outside the sheet is padded with the SAME analytic linen (seamless, never void: gate G4).

channels (level 0):  h f16 mm | alb f16x3 linear | T f16x2 | mat u8 | cov u8 (x255) | sid i32 | reg u16 | grp u8 |
                     birth f16 | optional float16 layers (age_fox, age_tide, age_fade, ud, holes, ...)."""
import os, json, glob, hashlib, time
import numpy as np, cv2
from .linen import make_linen

CORE = ('h', 'alb', 'T', 'mat', 'cov', 'sid', 'reg', 'grp', 'birth')
DT = dict(h=np.float16, alb=np.float16, T=np.float16, mat=np.uint8, cov=np.uint8, sid=np.int32, reg=np.uint16, grp=np.uint8,
          birth=np.float16)


def _to_disk(k, v):
    if k == 'cov':
        return np.clip(np.asarray(v, np.float32) * 255 + 0.5, 0, 255).astype(np.uint8)
    return np.asarray(v).astype(DT.get(k, np.float16))


def _from_disk(k, v):
    if k == 'cov':
        return v.astype(np.float32) / 255.0
    if v.dtype == np.float16:
        return v.astype(np.float32)
    if k in ('sid', 'reg', 'grp'):
        return v.astype(np.int32)
    return v


def downsample_key(k, v, f=2):
    """area mip of one channel by integer factor f (T: doubled-angle average; mat: majority; ids: point-sampled)."""
    H, W = v.shape[:2]
    H2, W2 = H // f, W // f
    v = v[:H2 * f, :W2 * f]
    if k == 'T':
        v = np.asarray(v, np.float32)
        a = np.arctan2(v[..., 1], v[..., 0]) * 2
        c = cv2.resize(np.cos(a).astype(np.float32), (W2, H2), interpolation=cv2.INTER_AREA)
        s = cv2.resize(np.sin(a).astype(np.float32), (W2, H2), interpolation=cv2.INTER_AREA)
        a2 = 0.5 * np.arctan2(s, c)
        return np.dstack([np.cos(a2), np.sin(a2)]).astype(np.float32)
    if k == 'mat':
        best = np.zeros((H2, W2), np.float32) - 1; out = np.zeros((H2, W2), np.uint8)
        for i in np.unique(v):
            c = cv2.resize((v == i).astype(np.float32), (W2, H2), interpolation=cv2.INTER_AREA)
            if i == 3: c = c * 1.6          # keep thin metal threads alive in mips
            sel = c > best; out[sel] = i; best[sel] = c[sel]
        return out
    if k in ('sid', 'reg', 'grp', 'gpoly'):
        return v[f // 2::f, f // 2::f][:H2, :W2].copy()
    return cv2.resize(np.asarray(v, np.float32), (W2, H2), interpolation=cv2.INTER_AREA)


def downsample(maps, f=2):
    """area mip of a working maps dict by integer factor f."""
    out = {}
    for k, v in maps.items():
        out[k] = downsample_key(k, v, f) if isinstance(v, np.ndarray) and v.ndim >= 2 else v
    out['PX'] = maps['PX'] / f
    return out


class MapSet:
    def __init__(self, path):
        self.path = path
        self.man = json.load(open(os.path.join(path, 'manifest.json')))
        self.PX = float(self.man['PX'])
        self.W, self.H = self.man['size_px']
        self.size_mm = tuple(self.man['size_mm'])
        self.tile = self.man['tile']; self.ov = self.man['overlap']
        self.channels = self.man['channels']
        self.linen_seed = self.man.get('linen_seed', 0)
        self._mips = {}
        self._tiles = {}

    # ------------------------------------------------------------------ writing
    @staticmethod
    def write(path, maps, meta=None, nlevels=4, tile=2048, overlap=64, extra_layers=None, verbose=True):
        """maps: working dict at level 0 (h, alb, T, mat, cov, sid, reg, grp, birth, PX) + extra_layers {name: HxW float}."""
        t0 = time.time()
        os.makedirs(os.path.join(path, 'L0'), exist_ok=True)
        for f in glob.glob(os.path.join(path, 'L0', '*.npz')):
            os.remove(f)
        H, W = maps['h'].shape
        PX = float(maps['PX'])
        chans = [k for k in CORE if k in maps] + list((extra_layers or {}).keys())
        src = dict(maps); src.update(extra_layers or {})
        nr, nc = (H + tile - 1) // tile, (W + tile - 1) // tile
        for r in range(nr):
            for c in range(nc):
                y0, x0 = max(r * tile - overlap, 0), max(c * tile - overlap, 0)
                y1, x1 = min((r + 1) * tile + overlap, H), min((c + 1) * tile + overlap, W)
                np.savez_compressed(os.path.join(path, 'L0', f'tile_{r:02d}_{c:02d}.npz'),
                                    **{k: _to_disk(k, src[k][y0:y1, x0:x1]) for k in chans},
                                    win=np.array([x0, y0, x1, y1], np.int32))
        # mips
        levels = [dict(level=0, PX=PX, W=W, H=H)]
        cur = None
        for lv in range(1, nlevels):
            if cur is None:
                cur = {k: downsample_key(k, src[k], 2) for k in chans}
                cur['PX'] = PX / 2
            else:
                cur = downsample(cur, 2)
            Hl, Wl = cur['h'].shape
            np.savez_compressed(os.path.join(path, f'L{lv}.npz'), **{k: _to_disk(k, cur[k]) for k in chans})
            levels.append(dict(level=lv, PX=cur['PX'], W=Wl, H=Hl))
        man = dict(sheet=os.path.basename(path.rstrip('/')), PX=PX, size_px=[W, H], size_mm=[W / PX, H / PX], tile=tile,
                   overlap=overlap, grid=[nr, nc], levels=levels, channels=chans, written=time.strftime('%Y-%m-%d %H:%M:%S'))
        man.update(meta or {})
        json.dump(man, open(os.path.join(path, 'manifest.json'), 'w'), indent=1)
        if verbose:
            print(f'MapSet.write {path}: {W}x{H} @ {PX} px/mm, {nr}x{nc} tiles, {nlevels} levels, {time.time() - t0:.1f}s')

    # ------------------------------------------------------------------ reading
    def level_for(self, screen_px_per_mm, max_ratio=1.4):
        """coarsest level whose density is >= screen density (the 1.0-1.4x shading rule; level 0 if magnifying)."""
        best = 0
        for lv in self.man['levels']:
            if lv['PX'] >= screen_px_per_mm * 0.999:
                best = lv['level']
        return best

    def _mip(self, lv):
        if lv not in self._mips:
            z = np.load(os.path.join(self.path, f'L{lv}.npz'))
            self._mips[lv] = {k: _from_disk(k, z[k]) for k in z.files}
        return self._mips[lv]

    def _tile(self, r, c):
        key = (r, c)
        if key not in self._tiles:
            z = np.load(os.path.join(self.path, 'L0', f'tile_{r:02d}_{c:02d}.npz'))
            self._tiles[key] = {k: z[k] for k in z.files}
            if len(self._tiles) > 6:
                self._tiles.pop(next(iter(self._tiles)))
        return self._tiles[key]

    def read_px(self, x0, y0, x1, y1, level=0, keys=None, pad=True):
        """window in level px (may extend outside the sheet).  Returns working maps dict (float32 / ints)."""
        lv = self.man['levels'][level]
        PX = lv['PX']; Wl, Hl = lv['W'], lv['H']
        keys = [k for k in (keys or self.channels) if k in self.channels]
        w, h = x1 - x0, y1 - y0
        out = {}
        ix0, iy0, ix1, iy1 = max(x0, 0), max(y0, 0), min(x1, Wl), min(y1, Hl)
        if level == 0:
            T = self.tile
            for k in keys:
                out[k] = None
            for r in range(iy0 // T, (iy1 - 1) // T + 1 if iy1 > iy0 else 0):
                for c in range(ix0 // T, (ix1 - 1) // T + 1 if ix1 > ix0 else 0):
                    tl = self._tile(r, c)
                    tx0, ty0 = tl['win'][0], tl['win'][1]
                    cx0, cy0 = max(c * T, ix0), max(r * T, iy0)
                    cx1, cy1 = min((c + 1) * T, ix1), min((r + 1) * T, iy1)
                    if cx1 <= cx0 or cy1 <= cy0: continue
                    for k in keys:
                        v = _from_disk(k, tl[k][cy0 - ty0:cy1 - ty0, cx0 - tx0:cx1 - tx0])
                        if out[k] is None:
                            out[k] = np.zeros((h, w) + v.shape[2:], v.dtype)
                        out[k][cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0] = v
        else:
            mp = self._mip(level)
            for k in keys:
                v = mp[k]
                o = np.zeros((h, w) + v.shape[2:], v.dtype)
                if ix1 > ix0 and iy1 > iy0:
                    o[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0] = v[iy0:iy1, ix0:ix1]
                out[k] = o
        for k in keys:
            if out[k] is None:
                v = _from_disk(k, np.zeros((1, 1) + ((3,) if k == 'alb' else (2,) if k == 'T' else ()), DT.get(k, np.float16)))
                out[k] = np.zeros((h, w) + v.shape[2:], v.dtype)
        inside = np.zeros((h, w), bool)
        if ix1 > ix0 and iy1 > iy0:
            inside[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0] = True
        valid = inside.copy()
        if pad and not inside.all():
            valid[:] = True
            f = int(round(self.PX / PX))
            ln = make_linen(h * f, w * f, self.PX, x0 * f / self.PX, y0 * f / self.PX, seed=self.linen_seed)
            if f > 1:
                ln = downsample(ln, f)
            o = ~inside
            for k in ('h', 'alb', 'T', 'mat', 'cov'):
                if k in out:
                    out[k][o] = ln[k][o]
            for k in keys:
                if k not in ('h', 'alb', 'T', 'mat', 'cov'):
                    out[k][o] = 0
        out['PX'] = PX
        out['origin_mm'] = (x0 / PX, y0 / PX)
        out['inside'] = inside
        out['valid'] = valid
        return out

    def read(self, x0_mm, y0_mm, x1_mm, y1_mm, level=0, keys=None, pad=True):
        PX = self.man['levels'][level]['PX']
        return self.read_px(int(np.floor(x0_mm * PX)), int(np.floor(y0_mm * PX)), int(np.ceil(x1_mm * PX)), int(np.ceil(y1_mm * PX)),
                            level, keys, pad)

    def full(self, level=0, keys=None):
        lv = self.man['levels'][level]
        return self.read_px(0, 0, lv['W'], lv['H'], level, keys, pad=False)

    def stitches(self):
        p = os.path.join(self.path, 'stitches.npz')
        return dict(np.load(p, allow_pickle=False)) if os.path.exists(p) else None

    def extra(self, name):
        p = os.path.join(self.path, name)
        return dict(np.load(p, allow_pickle=False))


def code_hash(files):
    h = hashlib.sha1()
    for f in sorted(files):
        h.update(open(f, 'rb').read())
    return h.hexdigest()[:12]
