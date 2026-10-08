"""rectify a game plate (zoom z, focus target tx,tz relative to Grandbois) onto the ground plane y; optional hex overlay.
python3 rectify2.py img zoom tx tz y out.png [ppu] [overlay 0/1] [x0 x1 z0 z1]"""
import sys, math, numpy as np, cv2
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from gamecam import *
img, zoom, tx, tz, Y, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
PPU = float(sys.argv[7]) if len(sys.argv) > 7 else 60
OV = int(sys.argv[8]) if len(sys.argv) > 8 else 1
X0, X1, Z0, Z1 = (float(v) for v in sys.argv[9:13]) if len(sys.argv) > 12 else (-16, 12, -10, 9)
src = cv2.imread(img)
H, W = src.shape[:2]
pitch, d = rig(zoom)
cam = Cam(np.array([tx, 0, tz]), pitch, d, 30, W, H)
xs = np.arange(X0, X1, 1 / PPU); zs = np.arange(Z0, Z1, 1 / PPU)
X, Z = np.meshgrid(xs, zs)
S, zc = cam.project(np.stack([X, np.full_like(X, Y), Z], -1))
o = cv2.remap(src, S[..., 0].astype(np.float32), S[..., 1].astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(40, 40, 40))
if OV:
    for q in range(-20, 20):
        for r in range(-12, 12):
            c = hex_world(q, r)
            if not (X0 - 1 < c[0] < X1 + 1 and Z0 - 1 < c[2] < Z1 + 1): continue
            pts = [((c[0] + math.cos(math.radians(60 * i - 30)) - X0) * PPU, (c[2] + math.sin(math.radians(60 * i - 30)) - Z0) * PPU) for i in range(6)]
            cv2.polylines(o, [np.array(pts, np.int32)], True, (0, 0, 255), 1, cv2.LINE_AA)
            cv2.putText(o, f'{q},{r}', (int((c[0] - X0) * PPU) - 14, int((c[2] - Z0) * PPU) + 4), cv2.FONT_HERSHEY_SIMPLEX, PPU / 160, (255, 255, 255), 1, cv2.LINE_AA)
cv2.imwrite(out, o)
