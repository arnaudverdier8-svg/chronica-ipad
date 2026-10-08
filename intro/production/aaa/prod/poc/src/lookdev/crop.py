import sys, cv2
# usage: crop.py in.png out.png x0 y0 w h [scale]
a = cv2.imread(sys.argv[1]); x0,y0,w,h = [int(v) for v in sys.argv[3:7]]; s = float(sys.argv[7]) if len(sys.argv)>7 else 1
c = a[y0:y0+h, x0:x0+w]
if s != 1: c = cv2.resize(c, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC if s>1 else cv2.INTER_AREA)
cv2.imwrite(sys.argv[2], c)
