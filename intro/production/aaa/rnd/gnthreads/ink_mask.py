# ink_mask.py - combine knight imprint + M1 underdrawing into one linen overlay mask (16 px/mm, 300x180 mm)
import numpy as np, cv2, os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); W_ = os.path.join(HERE, 'work')
KX, KY = -63.0, 0.0           # king offset
R, LW, LH = 16, 300, 180
imp = cv2.imread(os.path.join(W_, 'linen_imprint.png'), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
ud = np.load(os.path.join(W_, 'm1_underdrawing.npy'))
info = json.load(open(os.path.join(W_, 'm1_info.json')))
w, h = int(round(info['w_mm'] * R)), int(round(info['h_mm'] * R))
udr = cv2.resize(ud, (w, h), interpolation=cv2.INTER_LINEAR)
udr = cv2.erode(udr, np.ones((4, 4), np.float32))          # ~0.35 mm ink lines
udr = cv2.GaussianBlur(udr, (0, 0), 0.7) * 0.7
x0 = int(round((KX - info['w_mm'] / 2 + LW / 2) * R)); y0 = int(round((LH / 2 - (KY + info['h_mm'] / 2)) * R))
m = imp.copy()
m[y0:y0 + h, x0:x0 + w] = np.maximum(m[y0:y0 + h, x0:x0 + w], udr)
cv2.imwrite(os.path.join(W_, 'linen_ink.png'), np.clip(m * 255, 0, 255).astype(np.uint8))
print('ok', m.shape)
