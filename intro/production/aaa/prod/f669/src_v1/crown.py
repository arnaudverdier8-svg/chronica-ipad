"""The crown slip (R25-L, S09): the baked 'crown' group as its own shaded layer, lifted 15 mm over its ghost, turning
very slightly on four gold tethers.

Differences from chron.lift.Slip.layers (which this reuses for the slip maps and alpha):
  * the slip is lit by the CANDLE at its real height above the slip (z - lift) and by the same key pool,
  * perspective parallax: scale about the frame centre by Hc / (Hc - lift) (camera 1200 mm above the frame centre),
  * a small rotation about the hanging axis (the crown 'turns very slightly on its tethers'),
  * the shadow is the slip alpha PROJECTED FROM THE CANDLE onto the cloth (S = C + (P - C) Cz / (Cz - lift)), so it
    is offset and enlarged physically, with a penumbra from the flame size,
  * four couched-gold tethers (threads3d, gold) from the crown's band and side points down to needle holes in the cloth."""
import math
import numpy as np, cv2
from chron.lift import Slip
from chron.frontal import render, view_rect
from chron.color import pal, hex_lin

CAM_H = 1200.0


class CrownSlip:
    def __init__(self, ga):
        self.slip = Slip(ga)
        self.m = self.slip.m
        # fill pin-holes between stitches inside the slip (the slip is backed: no see-through dots)
        a8 = (self.slip.alpha > 0.5).astype(np.uint8)
        ff = a8.copy(); msk = np.zeros((a8.shape[0] + 2, a8.shape[1] + 2), np.uint8)
        cv2.floodFill(ff, msk, (0, 0), 1)
        holes = (ff == 0)
        self.alpha = np.maximum(self.slip.alpha, cv2.GaussianBlur(holes.astype(np.float32), (0, 0), 0.6))
        x0, y0, x1, y1 = ga.bbox
        PX = ga.PX0
        a = self.alpha > 0.5
        ys, xs = np.nonzero(a)
        self.PX = PX
        self.origin = (x0 / PX, y0 / PX)
        # hanging axis = centroid of the slip
        self.c = (xs.mean() / PX + x0 / PX, ys.mean() / PX + y0 / PX)
        self.bb_mm = (xs.min() / PX + x0 / PX, ys.min() / PX + y0 / PX, xs.max() / PX + x0 / PX, ys.max() / PX + y0 / PX)
        bx0, by0, bx1, by1 = self.bb_mm
        # tether anchors on the slip (sheet mm, unrotated): lower band corners and the outer arch shoulders
        self.anc = np.array([[bx0 + 3.5, by1 - 2.2], [bx1 - 3.5, by1 - 2.2], [bx0 + 2.2, by0 + 15.0], [bx1 - 2.2, by0 + 15.5]], np.float32)
        # their needle holes in the cloth (where the slip's couching went through): the lower pair in the bare
        # linen of the void under the band, the upper pair just outside the arches
        self.holes = self.anc + np.array([[6.5, 12.5], [-5.5, 13.0], [-11.0, -4.0], [11.5, -2.5]], np.float32)

    def rot(self, P, theta):
        c, s = math.cos(theta), math.sin(theta)
        d = P - np.array(self.c, np.float32)
        return np.stack([self.c[0] + c * d[:, 0] - s * d[:, 1], self.c[1] + s * d[:, 0] + c * d[:, 1]], 1).astype(np.float32)

    def _sheet_to_screen(self, view, out_wh):
        x0, y0, w, h, s = view_rect(view, out_wh)
        return x0, y0, s

    def layers(self, view, light, lift_mm, theta_deg, pool_at, out_wh=(2560, 1440), flame_r_mm=3.0, fib_seed=0):
        x0, y0, w, h, s = view_rect(view, out_wh)
        th = math.radians(theta_deg)
        cand = light['candle']
        # the slip sees the candle (z - lift) and the key pool at its centre
        l2 = dict(light)
        c2 = dict(cand); c2['pos_mm'] = (cand['pos_mm'][0], cand['pos_mm'][1], cand['pos_mm'][2] - lift_mm)
        c2['i'] = cand['i'] * pool_at(self.c[0], self.c[1])
        l2['candle'] = c2
        fr = render(self.m, view, l2, out_wh=out_wh, level=0, fib='auto', fib_seed=fib_seed, lod=True, margin_mm=0)
        PX = self.PX; ox, oy = self.origin
        # sheet mm -> screen for the slip maps (as render() warped them)
        M = np.array([[s / PX, 0, (ox - x0) * s], [0, s / PX, (oy - y0) * s], [0, 0, 1]], np.float64)
        # rotation about the hanging axis (screen)
        cxs, cys = (self.c[0] - x0) * s, (self.c[1] - y0) * s
        c, sn = math.cos(th), math.sin(th)
        Rm = np.array([[c, -sn, cxs - c * cxs + sn * cys], [sn, c, cys - sn * cxs - c * cys], [0, 0, 1]])
        # perspective parallax: scale about the frame centre
        k = CAM_H / (CAM_H - lift_mm)
        fx, fy = out_wh[0] / 2, out_wh[1] / 2
        Sm = np.array([[k, 0, (1 - k) * fx], [0, k, (1 - k) * fy], [0, 0, 1]])
        A = Sm @ Rm                      # screen(unlifted) -> screen(lifted)
        alpha = cv2.warpAffine(self.alpha, (A @ M)[:2].astype(np.float32), out_wh, flags=cv2.INTER_LINEAR, borderValue=0)
        rgb = cv2.warpAffine(fr['lin'], A[:2].astype(np.float32), out_wh, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        # shadow: rotate in sheet mm, project from the candle onto the cloth
        Cx, Cy, Cz = cand['pos_mm']
        ks = Cz / (Cz - lift_mm)
        Psh = np.array([[ks, 0, Cx - ks * Cx], [0, ks, Cy - ks * Cy], [0, 0, 1]])          # sheet -> sheet
        Rs = np.array([[c, -sn, self.c[0] - c * self.c[0] + sn * self.c[1]], [sn, c, self.c[1] - sn * self.c[0] - c * self.c[1]], [0, 0, 1]])
        Ms = np.array([[s, 0, -x0 * s], [0, s, -y0 * s], [0, 0, 1]])                       # sheet -> screen
        Mslip = np.array([[1 / PX, 0, ox], [0, 1 / PX, oy], [0, 0, 1]])                    # slip px -> sheet
        Tsh = Ms @ Psh @ Rs @ Mslip
        sh = cv2.warpAffine(self.alpha, Tsh[:2].astype(np.float32), out_wh, flags=cv2.INTER_LINEAR, borderValue=0)
        pen_mm = flame_r_mm * lift_mm / (Cz - lift_mm) + 0.35
        sh = cv2.GaussianBlur(sh, (0, 0), max(0.8, pen_mm * s * 0.75))
        # tethers (sheet mm, rotated anchors at height lift)
        top = self.rot(self.anc, th)
        # a top anchor seen from the camera sits at its lifted screen position: express it back in sheet mm so the
        # thread renderer (orthographic) draws it where the lifted crown is
        top_scr = (np.c_[(top[:, 0] - x0) * s, (top[:, 1] - y0) * s, np.ones(4)] @ Sm.T)[:, :2]
        top_mm = np.stack([top_scr[:, 0] / s + x0, top_scr[:, 1] / s + y0], 1)
        return dict(rgb=rgb, alpha=alpha, shadow=sh, s=s, x0=x0, y0=y0, top_mm=top_mm, top_true=top, k=k)

    def tether_curves(self, L_, lift_mm, sag_mm=2.2, n=40, theta_deg=0.0, seed=0):
        """3D polylines (sheet mm) of the four tethers: from the crown anchor (height lift - 0.6, under the slip) to
        the needle hole (z 0), analytic sag; drawn at the lifted screen position near the top."""
        out = []
        rr = np.random.default_rng(seed)
        for i in range(4):
            A = L_['top_mm'][i]; At = L_['top_true'][i]; B = self.holes[i]
            t = np.linspace(0, 1, n)
            # blend the projected top position into the true one along the thread (parallax shrinks with height)
            ztop = lift_mm - 0.6
            z = ztop * (1 - t) - sag_mm * np.sin(np.pi * t) * (0.6 + 0.2 * rr.random())
            z = np.maximum(z, 0.0) + 0.25
            par = np.clip(z / max(ztop, 1e-3), 0, 1)[:, None]
            top = At * (1 - par) + A * par
            xy = top * (1 - t[:, None]) + B[None, :] * t[:, None]
            # tension wobble
            nrm = np.array([-(B - At)[1], (B - At)[0]]); nrm /= (np.linalg.norm(nrm) + 1e-6)
            xy = xy + nrm[None, :] * (0.25 * np.sin(np.pi * t * 2 + i) * np.sin(np.pi * t))[:, None]
            out.append(np.c_[xy, z].astype(np.float32))
        return out

    def composite(self, lin, L_, key_frac):
        """shadow (occludes the candle part of the light) then the slip over."""
        out = lin * (1 - key_frac * L_['shadow'][..., None])
        a = L_['alpha'][..., None]
        return out * (1 - a) + L_['rgb'] * a
