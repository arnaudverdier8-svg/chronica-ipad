import sys, numpy as np, cv2
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from gamecam import *
A = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa'
src = cv2.imread(f'{A}/game/02_menu_first_frame_1920x1080.png')
cam = menu_cam()
PPU = 60.0
X0, X1, Z0, Z1 = -16, 10, -10, 6   # relative to Grandbois
xs = np.arange(X0, X1, 1 / PPU); zs = np.arange(Z0, Z1, 1 / PPU)
X, Z = np.meshgrid(xs, zs)
Y = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
Pw = np.stack([X, np.full_like(X, Y), Z], -1)
S, zc = cam.project(Pw)
mx = S[..., 0].astype(np.float32); my = S[..., 1].astype(np.float32)
out = cv2.remap(src, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(40, 40, 40))
# hex grid overlay around Grandbois (0,0)
for q in range(-14, 14):
    for r in range(-8, 8):
        c = hex_world(q, r)
        if not (X0 - 1 < c[0] < X1 + 1 and Z0 - 1 < c[2] < Z1 + 1): continue
        pts = []
        for i in range(6):
            a = math.radians(60 * i - 30)
            pts.append(((c[0] + math.cos(a) - X0) * PPU, (c[2] + math.sin(a) - Z0) * PPU))
        cv2.polylines(out, [np.array(pts, np.int32)], True, (0, 0, 255), 1, cv2.LINE_AA)
        cv2.putText(out, f'{q},{r}', (int((c[0] - X0) * PPU) - 18, int((c[2] - Z0) * PPU) + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)
cv2.imwrite(sys.argv[2] if len(sys.argv) > 2 else '/tmp/rect.jpg', out, [cv2.IMWRITE_JPEG_QUALITY, 90])
print(out.shape)
