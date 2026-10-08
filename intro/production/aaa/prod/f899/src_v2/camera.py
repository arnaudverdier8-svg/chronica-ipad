"""f899 camera: 22-deg oblique over the war strip, 3-deg dutch, F1 framing (4.65 px/mm at the aim point), pinhole.
Sheet coordinates: x right, y down (mm), z up from the cloth.  Blender world: X = x, Y = -y, Z = z (1 BU = 1 mm).
Shared by the plate warp (numpy) and the Eevee scene."""
import math
import numpy as np

W, H = 2560, 1440
SENSOR_W = 36.0
CFG = dict(aim_mm=(300.0, 176.0), tilt_deg=22.0, roll_deg=3.0, dist_mm=900.0, px_per_mm=4.65, fstop=8.0, focus_mm=900.0)


def build(cfg=None):
    c = dict(CFG); c.update(cfg or {})
    tx, ty = c['aim_mm']; t = math.radians(c['tilt_deg']); D = c['dist_mm']
    T = np.array([tx, -ty, 0.0])                                  # Blender world (X, Y=-y, Z)
    # camera sits toward the bottom of the sheet (-Y in Blender), above the cloth
    C = T + D * np.array([0.0, -math.sin(t), math.cos(t)])
    f_axis = (T - C) / np.linalg.norm(T - C)                      # forward
    up_ref = np.array([0.0, 1.0, 0.0])                            # up the cloth (+Y_bl) = up in the frame
    right = np.cross(f_axis, up_ref); right /= np.linalg.norm(right)
    up = np.cross(right, f_axis)
    r = math.radians(c['roll_deg'])                               # dutch: positive = horizon rises to the right
    right2 = right * math.cos(r) + up * math.sin(r)
    up2 = -right * math.sin(r) + up * math.cos(r)
    # camera-to-world rotation columns: x = right, y = up, z = -forward (Blender camera looks down -Z)
    Rcw = np.stack([right2, up2, -f_axis], 1)
    f_px = c['px_per_mm'] * D
    focal_mm = SENSOR_W * f_px / W
    return dict(cfg=c, C=C, T=T, Rcw=Rcw, f_px=f_px, focal_mm=focal_mm, W=W, H=H, cx=W / 2, cy=H / 2)


def project(cam, P_blender):
    """world (Blender coords, n x 3) -> continuous image coords (u, v) [pixel (i,j) covers [i, i+1)] and depth (distance along the
    optical axis)."""
    P = np.asarray(P_blender, np.float64).reshape(-1, 3)
    Pc = (P - cam['C']) @ cam['Rcw']                              # camera coords: x right, y up, z = -depth
    z = -Pc[:, 2]
    u = cam['cx'] + cam['f_px'] * Pc[:, 0] / z
    v = cam['cy'] - cam['f_px'] * Pc[:, 1] / z
    return np.stack([u, v], 1), z


def sheet_to_world(xy_mm, z=0.0):
    xy = np.asarray(xy_mm, np.float64).reshape(-1, 2)
    return np.stack([xy[:, 0], -xy[:, 1], np.full(len(xy), z)], 1)


def plate_homography(cam, x0, y0, s):
    """cv2 homography mapping rectified plate pixels (centre-based cv2 coords; plate px p <-> sheet mm x0 + (p+.5)/s)
    to screen pixels (cv2 coords)."""
    src = np.array([[0, 0], [1000, 0], [1000, 600], [0, 600]], np.float64)
    mm = np.stack([x0 + (src[:, 0] + 0.5) / s, y0 + (src[:, 1] + 0.5) / s], 1)
    uv, _ = project(cam, sheet_to_world(mm))
    dst = (uv - 0.5).astype(np.float32)
    import cv2
    return cv2.getPerspectiveTransform(src.astype(np.float32), dst)


def ground_from_pixel(cam, uv):
    """screen continuous (u, v) -> sheet mm (x, y) on the cloth plane z = 0, plus depth."""
    uv = np.asarray(uv, np.float64).reshape(-1, 2)
    dc = np.stack([(uv[:, 0] - cam['cx']) / cam['f_px'], -(uv[:, 1] - cam['cy']) / cam['f_px'], -np.ones(len(uv))], 1)   # camera ray
    dw = dc @ cam['Rcw'].T
    tpar = -cam['C'][2] / dw[:, 2]
    P = cam['C'][None] + tpar[:, None] * dw
    z = tpar * (dc[:, 2] * -1)                                    # depth along the optical axis = t * |dc.z| (dc.z = -1)
    return np.stack([P[:, 0], -P[:, 1]], 1), z


if __name__ == '__main__':
    cam = build()
    print('focal mm', cam['focal_mm'], 'f_px', cam['f_px'], 'C', cam['C'])
    for (u, v) in [(0, 0), (2560, 0), (0, 1440), (2560, 1440), (1280, 720)]:
        xy, z = ground_from_pixel(cam, [[u, v]])
        print((u, v), '->', np.round(xy[0], 1), 'depth', round(float(z[0]), 1))
    # local scale (px/mm) along x at several rows
    for y in (0, 100, 176, 260, 345):
        a, _ = project(cam, sheet_to_world([[290, y], [310, y]]))
        b, _ = project(cam, sheet_to_world([[300, y - 10], [300, y + 10]]))
        print('y', y, 'sx', round(float(np.linalg.norm(a[1] - a[0]) / 20), 3), 'sy', round(float(np.linalg.norm(b[1] - b[0]) / 20), 3))
