import cv2
r = R(f=561, cx=297, cy=205, mode='save', cache=None)
cv2.imwrite(os.path.join(W, 'robe_f561.png'), r['img'][..., ::-1])
