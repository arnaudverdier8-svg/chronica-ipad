"""R25-L frontal lift (pipeline 8; storyboard S05/S09/S14): a record group rendered as its own shaded slip layer
(alpha from its own stitches), offset by parallax and scaled, with a PCSS-style shadow (penumbra 0.25 + 0.6 x lift mm,
offset lift / tan(el) along the light), contact AO at the attachment edge and 2D-lit tethers.
Camera within 10 deg of the cloth normal and lift <= 15 mm only (otherwise Eevee EV-DM/P)."""
import math
import numpy as np, cv2
from .record import replay, bbox_of
from .frontal import render, view_rect, OUT_WH
from .shade import light_vec
from .fibres import splat_thick, light_curves


class Slip:
    def __init__(self, ga):
        """ga: an anim.groupanim.GroupAnim for the slip's group (e.g. 'crown'); its stitches are rasterised on an
        empty base (no linen) so the slip has its own alpha."""
        self.ga = ga
        x0, y0, x1, y1 = ga.bbox
        H, W = y1 - y0, x1 - x0
        m = dict(h=np.full((H, W), -10.0, np.float32), alb=np.zeros((H, W, 3), np.float32), T=np.zeros((H, W, 2), np.float32),
                 mat=np.zeros((H, W), np.uint8), cov=np.zeros((H, W), np.float32), sid=np.zeros((H, W), np.int32),
                 sfr=np.zeros((H, W), np.float32), base=np.zeros((H, W), np.float32), stamp=np.zeros((H, W), np.int32), PX=ga.PX0)
        replay(m, ga.rec, ga.sel, x0, y0)
        a = (m['h'] > -5).astype(np.float32)
        a = cv2.morphologyEx(a, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        m['h'] = np.where(a > 0, np.maximum(m['h'], 0.0), -0.3).astype(np.float32)   # felt-edge floor
        m['alb'][a == 0] = m['alb'][a > 0].mean(0) if a.any() else 0.3
        m['T'][a == 0] = (1, 0)
        m['mat'][a == 0] = 1
        m['origin_mm'] = (x0 / ga.PX0, y0 / ga.PX0)
        m['inside'] = np.ones(a.shape, bool)
        self.m = m
        self.alpha = cv2.GaussianBlur(a, (0, 0), 0.6)
        self.centre_mm = ((x0 + x1) / 2 / ga.PX0, (y0 + y1) / 2 / ga.PX0)

    def layers(self, view, light, lift_mm, out_wh=OUT_WH, parallax_px_per_mm=0.45, scale=0.015, cam=None):
        """returns dict(rgb, alpha, shadow) screen layers (linear)."""
        x0, y0, w, h, s = view_rect(view, out_wh)
        fr = render(self.m, view, light, out_wh=out_wh, level=0, fib='auto', lod=True, cam=cam, margin_mm=0)
        PX = self.m['PX']; ox, oy = self.m['origin_mm']
        k = 1.0 + scale * min(1.0, lift_mm / 15.0)
        cxs, cys = (self.centre_mm[0] - x0) * s, (self.centre_mm[1] - y0) * s
        # parallax: away from the frame centre (camera above the frame centre)
        dx = (cxs - out_wh[0] / 2) / out_wh[0] * parallax_px_per_mm * lift_mm
        dy = (cys - out_wh[1] / 2) / out_wh[1] * parallax_px_per_mm * lift_mm
        M = np.array([[s / PX, 0, (ox - x0) * s], [0, s / PX, (oy - y0) * s]], np.float64)
        S = np.array([[k, 0, (1 - k) * cxs + dx], [0, k, (1 - k) * cys + dy], [0, 0, 1]])
        M2 = (S @ np.vstack([M, [0, 0, 1]]))[:2].astype(np.float32)
        alpha = cv2.warpAffine(self.alpha, M2, out_wh, flags=cv2.INTER_LINEAR, borderValue=0)
        Mi = cv2.invertAffineTransform(M2)
        # re-warp the shaded slip with the parallax/scale (render() warped it without)
        Minv0 = cv2.invertAffineTransform(M.astype(np.float32))
        A = np.vstack([M.astype(np.float64), [0, 0, 1]]) @ np.linalg.inv(np.vstack([M2.astype(np.float64), [0, 0, 1]]))
        rgb = cv2.warpAffine(fr['lin'], A[:2].astype(np.float32), out_wh, flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                             borderMode=cv2.BORDER_REPLICATE)
        # shadow (on the ground plane): unscaled footprint offset along -L by lift / tan(el), PCSS penumbra
        L = light_vec(light['az'], light['el'])
        l2 = L[:2] / (np.linalg.norm(L[:2]) + 1e-6); tan_el = L[2] / (np.linalg.norm(L[:2]) + 1e-6)
        off = lift_mm / max(tan_el, 0.05) * s
        Ms = M.astype(np.float32).copy(); Ms[0, 2] -= l2[0] * off; Ms[1, 2] -= l2[1] * off
        sh = cv2.warpAffine(self.alpha, Ms, out_wh, flags=cv2.INTER_LINEAR, borderValue=0)
        pen = (0.25 + 0.6 * lift_mm) * s * 0.5
        sh = cv2.GaussianBlur(sh, (0, 0), max(0.8, pen))
        return dict(rgb=rgb, alpha=alpha, shadow=sh, M=M2, s=s, x0=x0, y0=y0)

    def composite(self, ground_lin, L_, strength=0.62):
        out = ground_lin * (1 - strength * L_['shadow'][..., None])
        a = L_['alpha'][..., None]
        return out * (1 - a) + L_['rgb'] * a


def tethers(img, anchors_top_mm, anchors_ground_mm, lift_mm, view_ctx, light, col, radius_mm=0.18, sag_mm=1.5, alpha=1.0):
    """2D-lit tethers (bevelled curves in the parent strand colour) from slip anchor points (at height lift) to needle
    holes on the ground.  anchors_*: (n, 2) sheet mm."""
    s = view_ctx['s']; x0 = view_ctx['x0']; y0 = view_ctx['y0']
    K = 14
    t = np.linspace(0, 1, K)[None, :, None]
    A = np.asarray(anchors_top_mm, np.float32)[:, None, :]; B = np.asarray(anchors_ground_mm, np.float32)[:, None, :]
    xy = A * (1 - t) + B * t
    z = lift_mm * (1 - t[..., 0]) - sag_mm * np.sin(np.pi * t[..., 0]) * 0.3
    z = np.broadcast_to(z, xy.shape[:2])
    P = np.concatenate([xy, np.maximum(z, 0)[..., None]], -1).astype(np.float32)
    n = len(P)
    Lv = light_vec(light['az'], light['el'])
    key = np.asarray(light['key'], np.float32) * light['key_i']; fill = np.asarray(light['fill'], np.float32) * light['fill_i']
    C = light_curves(P, np.tile(np.asarray(col, np.float32), (n, 1)), Lv, key, fill)
    Q = np.stack([(P[..., 0] - x0) * s, (P[..., 1] - y0) * s], -1).astype(np.float32)
    R = np.full((n, K), radius_mm * s, np.float32)
    l2 = Lv[:2] / (np.linalg.norm(Lv[:2]) + 1e-6); tan_el = Lv[2] / (np.linalg.norm(Lv[:2]) + 1e-6)
    so = np.stack([-l2[0] * P[..., 2] / tan_el * s, -l2[1] * P[..., 2] / tan_el * s], -1).astype(np.float32)
    splat_thick(img, Q, R, C, np.full((n, K), alpha, np.float32), so, np.full((n, K), 0.35, np.float32), float(max(1.0, 0.2 * s)))
    return img
