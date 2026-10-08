import cv2
r = R(cache='cache_strands.pkl')
img = r['img']
cv2.imwrite(os.path.join(W, 's2_strands.png'), img[..., ::-1])
c = img[150:440, 480:820]
cv2.imwrite(os.path.join(W, 's2_strands_x3.png'), cv2.resize(c, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)[..., ::-1][..., ::-1])
