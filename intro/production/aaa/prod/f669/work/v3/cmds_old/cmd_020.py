import __main__ as _m; R = _m.R
import cv2
# crown window, cached (base is independent of the metal pass)
r = R(cx=296, cy=135, cache='cache_crown.pkl', mode='save')
cv2.imwrite(os.path.join(W, 'c0_crown.png'), r['img'][..., ::-1])
