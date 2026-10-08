"""Derive the extra layers the compositor needs from panel 1 (the oath):
crown.png (cut-out of the king's crown) and p1_empty.png (the empty throne)."""
import os, math
import numpy as np, cv2

D = os.path.dirname(os.path.abspath(__file__)) + '/'
p1 = cv2.imread(D + 'panels/p1_oath.jpg')
S = 2  # layout below was measured on a half-size preview

# --- crown cut-out via GrabCut, dropping the king's white hair
x0, y0, x1, y1 = 1250, 416, 1506, 604
mask = np.zeros(p1.shape[:2], np.uint8); bgd = np.zeros((1, 65)); fgd = np.zeros((1, 65))
cv2.grabCut(p1, mask, (x0, y0, x1 - x0, y1 - y0), bgd, fgd, 6, cv2.GC_INIT_WITH_RECT)
m = np.where((mask == 1) | (mask == 3), 255, 0).astype(np.uint8)
crop = p1[y0:y1, x0:x1]; mc = m[y0:y1, x0:x1]
hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
mc[(hsv[..., 1] < 70) & (hsv[..., 2] > 150)] = 0
mc = cv2.morphologyEx(mc, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
n, lab, st, _ = cv2.connectedComponentsWithStats(mc)
big = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]); mc = np.where(lab == big, 255, 0).astype(np.uint8)
cv2.imwrite(D + 'crown.png', np.dstack([crop, cv2.GaussianBlur(mc, (3, 3), 0)]))

# --- empty throne: inpaint the crown area, hide the king's hands, stitch an indigo void
e = p1.copy()
cm = np.zeros(p1.shape[:2], np.uint8)
cv2.fillPoly(cm, [np.array([(626, 206), (752, 206), (762, 296), (616, 296)], np.int32) * S], 255)
e = cv2.inpaint(e, cm, 9, cv2.INPAINT_TELEA)
patch = p1[1190:1300, 1316:1430]
for cx in (1215, 1268, 1492):
    e = cv2.seamlessClone(patch, e, 255 * np.ones(patch.shape[:2], np.uint8), (cx, 1245), cv2.NORMAL_CLONE)
arch = [(606 + (778 - 606) * (0.5 - 0.5 * math.cos(a)), 300 - 34 * math.sin(a)) for a in np.linspace(0, math.pi, 24)]
poly = [(606, 384)] + arch + [(778, 384), (840, 384), (848, 520), (842, 600), (543, 600), (536, 520), (544, 384)]
poly = (np.array(poly) * S).astype(np.int32)
km = np.zeros(p1.shape[:2], np.uint8); cv2.fillPoly(km, [poly], 255)
rng = np.random.default_rng(3)
void = np.zeros_like(p1, np.float32) + np.array([40, 20, 16], np.float32)
for _ in range(11000):
    x = int(rng.uniform(1060, 1700)); y = int(rng.uniform(500, 1210)); L = rng.uniform(30, 70)
    c = np.array([58, 28, 20]) * rng.uniform(0.6, 1.25)
    cv2.line(void, (x, y), (int(x + L), int(y + rng.normal(0, 3))), (c * 0.6).tolist(), 9, cv2.LINE_AA)
    cv2.line(void, (x, y - 1), (int(x + L), int(y - 1 + rng.normal(0, 2))), c.tolist(), 4, cv2.LINE_AA)
kmf = cv2.GaussianBlur(km, (7, 7), 0).astype(np.float32)[..., None] / 255
e = e.astype(np.float32) * (1 - kmf) + void * kmf
G1, G2 = (38, 110, 160), (90, 180, 225)
def gold(pts, closed=False, w=8):
    pts = (np.array(pts) * S).astype(np.int32)
    cv2.polylines(e, [pts], closed, (20, 40, 60), w + 5, cv2.LINE_AA)
    cv2.polylines(e, [pts], closed, G1, w, cv2.LINE_AA)
    cv2.polylines(e, [pts], closed, G2, max(2, w // 3), cv2.LINE_AA)
gold(np.array(poly) / S, True, 9)
inner = [(630 + (754 - 630) * (0.5 - 0.5 * math.cos(a)), 330 - 26 * math.sin(a)) for a in np.linspace(0, math.pi, 20)]
gold([(630, 470)] + inner + [(754, 470)], False, 6)
gold([(585, 470), (800, 470)], False, 7); gold([(585, 470), (575, 520), (810, 520), (800, 470)], True, 6)
gold([(595, 520), (595, 598)], False, 6); gold([(790, 520), (790, 598)], False, 6)
cv2.imwrite(D + 'p1_empty.png', np.clip(e, 0, 255).astype(np.uint8))
print('ok')
