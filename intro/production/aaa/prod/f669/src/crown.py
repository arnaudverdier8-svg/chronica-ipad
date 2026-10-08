"""The crown slip (R25-L, S09), v2: the baked 'crown' group PLUS the side prongs the bake's tent polygon left stitched in
the ground, as its own shaded layer, lifted 15 mm over its ghost, turning very slightly on four gold tethers.

  * slip maps built here (not chron.lift.Slip): pin-holes between stitches are filled in the maps (not just the alpha),
    so no hollow squares appear in the crown;
  * lit by the CANDLE at its real height above the slip; perspective parallax; small rotation on its tethers;
  * SHADOW = the slip alpha projected from an EXTENDED candle: N source samples over the flame (ellipsoid, 3 mm radius
    x 4 mm half height), each an exact projection S = C_i + (P - C_i) Cz_i / (Cz_i - lift); the penumbra therefore grows
    with the caster-to-receiver distance (crisp at the tether feet, soft at the crown), is elongated along the light
    axis (12 deg), and keeps the crown's silhouette (finial, prongs, band);
  * four TETHER shadows computed the same way (a tether is a caster from z = 0 at its foot to z = lift);
  * soft contact occlusion under the crown rim (a lifted card shades the cloth under it);
  * four couched-gold tethers (twisted gold cord) from the crown's real silhouette to needle holes in the cloth."""
import math
import numpy as np, cv2
from chron.record import replay, bbox_of
from chron.frontal import render, view_rect
from chron.color import pal, hex_lin

CAM_H = 1200.0


class CrownSlip:
    def __init__(self, ga, tip_ids=None):
        R = ga.rec
        PX = ga.PX0
        ids = np.asarray(ga.sel, np.int64)
        if tip_ids is not None and len(tip_ids):
            ids = np.concatenate([ids, np.asarray(tip_ids, np.int64)])
        order = R['order']
        ids = order[np.isin(order, ids)]                          # needle order
        b = bbox_of(R, ids, 4)
        x0, y0, x1, y1 = b
        x0 -= x0 % 8; y0 -= y0 % 8; x1 += (-x1) % 8; y1 += (-y1) % 8
        H, W = y1 - y0, x1 - x0
        m = dict(h=np.full((H, W), -10.0, np.float32), alb=np.zeros((H, W, 3), np.float32), T=np.zeros((H, W, 2), np.float32),
                 mat=np.zeros((H, W), np.uint8), cov=np.zeros((H, W), np.float32), sid=np.zeros((H, W), np.int32),
                 sfr=np.zeros((H, W), np.float32), base=np.zeros((H, W), np.float32), stamp=np.zeros((H, W), np.int32), PX=PX)
        replay(m, R, ids, x0, y0)
        st = (m['h'] > -5)
        a = cv2.morphologyEx(st.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        # fill the pin-holes: interior zeros of the closed mask
        ff = a.copy(); msk = np.zeros((H + 2, W + 2), np.uint8)
        cv2.floodFill(ff, msk, (0, 0), 2)
        holes = (ff == 0)
        solid = ((a > 0) | holes)
        # normalized-convolution fill of the maps in the closed gaps and holes (colour + height of the neighbouring wool)
        fillm = solid & ~st
        w0 = st.astype(np.float32)
        wb = cv2.GaussianBlur(w0, (0, 0), 2.2) + 1e-4
        for k, ch in (('h', 1), ('alb', 3)):
            v = m[k] * (w0[..., None] if ch == 3 else w0)
            fv = cv2.GaussianBlur(v, (0, 0), 2.2) / (wb[..., None] if ch == 3 else wb)
            m[k] = np.where(fillm[..., None] if ch == 3 else fillm, fv, m[k]).astype(np.float32)
        m['T'][fillm] = (1, 0); m['mat'][fillm] = 1
        m['h'] = np.where(solid, np.maximum(m['h'], 0.0), -0.3).astype(np.float32)
        out = ~solid
        m['alb'][out] = m['alb'][solid].mean(0) if solid.any() else 0.3
        m['T'][out] = (1, 0)
        m['mat'][out] = 1
        m['origin_mm'] = (x0 / PX, y0 / PX)
        m['inside'] = np.ones((H, W), bool)
        self.m = m
        self.PX = PX
        self.origin = (x0 / PX, y0 / PX)
        self.alpha = cv2.GaussianBlur(solid.astype(np.float32), (0, 0), 0.6)
        self.solid = solid
        ys, xs = np.nonzero(solid)
        self.c = (xs.mean() / PX + x0 / PX, ys.mean() / PX + y0 / PX)
        self.bb_mm = (xs.min() / PX + x0 / PX, ys.min() / PX + y0 / PX, xs.max() / PX + x0 / PX, ys.max() / PX + y0 / PX)
        self._anchors()

    def snap_holes_to_linen(self, ground, search_mm=11.0):
        """move each tether's needle hole onto BARE linen (the upper pair would otherwise end on the throne's embroidery):
        the bare-linen pixel (5 px/mm ground mip, 1.4 mm clear all round) nearest to the nominal hole position."""
        x0, y0 = self.holes.min(0) - search_mm - 4; x1, y1 = self.holes.max(0) + search_mm + 4
        m = ground.read(x0, y0, x1, y1, 1, keys=['mat'])
        PX = m['PX']; ox, oy = m['origin_mm']
        bare = (m['mat'] == 0).astype(np.uint8)
        bare = cv2.erode(bare, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(2.8 * PX) | 1,) * 2))
        out = self.holes.copy()
        for i, h in enumerate(self.holes):
            ys, xs = np.nonzero(bare)
            P = np.stack([xs / PX + ox, ys / PX + oy], 1)
            d = np.hypot(P[:, 0] - h[0], P[:, 1] - h[1])
            ok = d < search_mm
            if ok.any():
                j = np.argmin(np.where(ok, d, 1e9))
                out[i] = P[j]
        self.holes = out.astype(np.float32)
        return out

    def _anchors(self):
        """tether anchors on the crown's real silhouette (sheet mm, unrotated) and their needle holes in the cloth."""
        PX = self.PX; ox, oy = self.origin
        solid = self.solid
        rows = np.nonzero(solid.any(1))[0]
        y_top, y_bot = rows.min(), rows.max()
        def row_extent(y):
            xs = np.nonzero(solid[int(y)])[0]
            return xs.min(), xs.max()
        # lower pair: the band's bottom corners (2.5 mm above the lowest row, 2.2 mm in from the extent)
        yl = y_bot - 2.5 * PX
        xa, xb = row_extent(yl)
        low = [((xa + 2.2 * PX) / PX + ox, yl / PX + oy), ((xb - 2.2 * PX) / PX + ox, yl / PX + oy)]
        # upper pair: the outermost points of the prongs / shoulders between 30 % and 62 % of the height
        hh = y_bot - y_top
        ys = np.arange(int(y_top + 0.30 * hh), int(y_top + 0.62 * hh))
        ext = np.array([row_extent(y) for y in ys])
        il = int(np.argmin(ext[:, 0])); ir = int(np.argmax(ext[:, 1]))
        up = [((ext[il, 0] + 1.6 * PX) / PX + ox, ys[il] / PX + oy), ((ext[ir, 1] - 1.6 * PX) / PX + ox, ys[ir] / PX + oy)]
        self.anc = np.array([low[0], low[1], up[0], up[1]], np.float32)
        # needle holes: the lower pair on the bare linen under the band (down and slightly in), the upper pair out
        # beside the prongs (the cloth beside the arch)
        self.holes = self.anc + np.array([[5.5, 14.0], [-5.5, 14.5], [-7.5, 1.5], [7.5, 2.0]], np.float32)

    def rot(self, P, theta):
        c, s = math.cos(theta), math.sin(theta)
        d = P - np.array(self.c, np.float32)
        return np.stack([self.c[0] + c * d[:, 0] - s * d[:, 1], self.c[1] + s * d[:, 0] + c * d[:, 1]], 1).astype(np.float32)

    # ----------------------------------------------------------------------------------------- layers
    def layers(self, view, light, lift_mm, theta_deg, pool_at, out_wh=(2560, 1440), fib_seed=0, src_h=2.2, src_r=3.7,
               n_samples=40, tether_curves=None, tether_r_mm=0.6):
        x0, y0, w, h, s = view_rect(view, out_wh)
        th = math.radians(theta_deg)
        cand = light['candle']
        l2 = dict(light)
        c2 = dict(cand); c2['pos_mm'] = (cand['pos_mm'][0], cand['pos_mm'][1], cand['pos_mm'][2] - lift_mm)
        c2['i'] = cand['i'] * pool_at(self.c[0], self.c[1])
        l2['candle'] = c2
        fr = render(self.m, view, l2, out_wh=out_wh, level=0, fib='auto', fib_seed=fib_seed, lod=True, margin_mm=0)
        PX = self.PX; ox, oy = self.origin
        M = np.array([[s / PX, 0, (ox - x0) * s], [0, s / PX, (oy - y0) * s], [0, 0, 1]], np.float64)
        cxs, cys = (self.c[0] - x0) * s, (self.c[1] - y0) * s
        c, sn = math.cos(th), math.sin(th)
        Rm = np.array([[c, -sn, cxs - c * cxs + sn * cys], [sn, c, cys - sn * cxs - c * cys], [0, 0, 1]])
        k = CAM_H / (CAM_H - lift_mm)
        fx, fy = out_wh[0] / 2, out_wh[1] / 2
        Sm = np.array([[k, 0, (1 - k) * fx], [0, k, (1 - k) * fy], [0, 0, 1]])
        A = Sm @ Rm
        alpha = cv2.warpAffine(self.alpha, (A @ M)[:2].astype(np.float32), out_wh, flags=cv2.INTER_LINEAR, borderValue=0)
        rgb = cv2.warpAffine(fr['lin'], A[:2].astype(np.float32), out_wh, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        metal = cv2.warpAffine((self.m['mat'] == 3).astype(np.float32), (A @ M)[:2].astype(np.float32), out_wh, flags=cv2.INTER_LINEAR, borderValue=0)
        # ---- cast shadow of the crown from an extended candle ------------------------------------------------------
        Cx, Cy, Cz = cand['pos_mm']
        Rs = np.array([[c, -sn, self.c[0] - c * self.c[0] + sn * self.c[1]], [sn, c, self.c[1] - sn * self.c[0] - c * self.c[1]], [0, 0, 1]])
        Ms = np.array([[s, 0, -x0 * s], [0, s, -y0 * s], [0, 0, 1]])
        Mslip = np.array([[1 / PX, 0, ox], [0, 1 / PX, oy], [0, 0, 1]])
        a_src = cv2.GaussianBlur(self.solid.astype(np.float32), (0, 0), 0.9)
        samples = self._samples(n_samples, src_r, src_h)
        acc = np.zeros((out_wh[1], out_wh[0]), np.float32)
        for dx, dy, dz in samples:
            cx_, cy_, cz_ = Cx + dx, Cy + dy, Cz + dz
            ks = cz_ / (cz_ - lift_mm)
            Psh = np.array([[ks, 0, cx_ - ks * cx_], [0, ks, cy_ - ks * cy_], [0, 0, 1]])
            T = Ms @ Psh @ Rs @ Mslip
            acc += cv2.warpAffine(a_src, T[:2].astype(np.float32), out_wh, flags=cv2.INTER_LINEAR, borderValue=0)
        sh = acc / len(samples)
        # ---- tethers: anchors in the screen/sheet frames, curves, and their cast shadows ---------------------------------
        top = self.rot(self.anc, th)
        top_scr = (np.c_[(top[:, 0] - x0) * s, (top[:, 1] - y0) * s, np.ones(4)] @ Sm.T)[:, :2]
        top_mm = np.stack([top_scr[:, 0] / s + x0, top_scr[:, 1] / s + y0], 1)
        out = dict(rgb=rgb, alpha=alpha, metal=metal, shadow=sh, s=s, x0=x0, y0=y0, top_mm=top_mm, top_true=top, k=k, A=A)
        curves = self.tether_curves(out, lift_mm) if tether_curves is None else tether_curves
        out['curves'] = curves
        tsh = np.zeros_like(sh)
        thick = max(1.0, 2 * tether_r_mm * s)
        for dx, dy, dz in samples[::2]:
            cx_, cy_, cz_ = Cx + dx, Cy + dy, Cz + dz
            buf = np.zeros_like(sh)
            for P in curves:
                z = np.clip(P[:, 2] + 0.0, 0, cz_ - 1)
                kk = cz_ / (cz_ - z)
                S_ = np.stack([cx_ + (P[:, 0] - cx_) * kk, cy_ + (P[:, 1] - cy_) * kk], 1)
                q = np.stack([(S_[:, 0] - x0) * s, (S_[:, 1] - y0) * s], 1)
                cv2.polylines(buf, [np.round(q * 8).astype(np.int32)], False, 1.0, int(round(thick)), cv2.LINE_AA, shift=3)
            tsh += buf
        tsh /= max(1, len(samples[::2]))
        out['tether_shadow'] = tsh
        # ---- contact occlusion of the cloth under the lifted rim ---------------------------------------------------------
        ao = cv2.warpAffine(a_src, (Ms @ Mslip)[:2].astype(np.float32), out_wh, flags=cv2.INTER_LINEAR, borderValue=0)
        ao = np.roll(ao, int(round(1.8 * s)), axis=0)
        out['ao'] = cv2.GaussianBlur(ao, (0, 0), 2.0 * s)
        return out

    @staticmethod
    def _samples(n, r, hz):
        """n points over the flame (ellipsoid: radius r mm horizontally, +-hz mm vertically), low-discrepancy."""
        pts = []
        for i in range(n):
            u = (i + 0.5) / n
            rad = r * math.sqrt(u)
            phi = i * 2.399963
            z = hz * (((i * 0.6180339887) % 1.0) * 2 - 1)
            pts.append((rad * math.cos(phi), rad * math.sin(phi), z))
        return pts

    def tether_curves(self, L_, lift_mm, sag_mm=4.2, n=44, seed=0):
        """3D polylines (sheet mm) of the four tethers: from the crown anchor (height lift - 0.8, under the slip) to the
        needle hole (z 0): a slight catenary (taut cords with a small sag), lateral tension wobble."""
        out = []
        rr = np.random.default_rng(seed)
        for i in range(4):
            A = L_['top_mm'][i]; At = L_['top_true'][i]; B = self.holes[i]
            t = np.linspace(0, 1, n)
            ztop = lift_mm - 0.8
            z = ztop * (1 - t) - sag_mm * np.sin(np.pi * t) * (0.55 + 0.25 * rr.random()) * min(1.0, lift_mm / 15.0)
            z = np.maximum(z, 0.0) + 0.22
            par = np.clip(z / max(ztop, 1e-3), 0, 1)[:, None]
            top = At * (1 - par) + A * par
            xy = top * (1 - t[:, None]) + B[None, :] * t[:, None]
            nrm = np.array([-(B - At)[1], (B - At)[0]]); nrm /= (np.linalg.norm(nrm) + 1e-6)
            xy = xy + nrm[None, :] * (0.55 * np.sin(np.pi * t * 2 + i * 1.7) * np.sin(np.pi * t))[:, None]
            out.append(np.c_[xy, z].astype(np.float32))
        return out
