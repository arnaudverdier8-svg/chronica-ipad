import cv2, sys
# usage: crop.py img name x y w h [zoom]
img, name, x, y, w, h = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7])
z = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
im = cv2.imread(img)
c = im[y:y+h, x:x+w]
if z != 1.0:
    c = cv2.resize(c, None, fx=z, fy=z, interpolation=cv2.INTER_CUBIC if z > 1 else cv2.INTER_AREA)
cv2.imwrite('/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f91/_c/' + name + '.png', c)
