import sys, cv2, numpy as np
# usage: peek.py out.jpg width cols frame_dir f1 f2 ...   (frames as f%04d.png in frame_dir)
out, wd, cols, d = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
fs = [int(a) for a in sys.argv[5:]]
tiles = []
for f in fs:
    im = cv2.imread(f'{d}/f{f:04d}.png')
    h = int(im.shape[0] * wd / im.shape[1])
    im = cv2.resize(im, (wd, h), interpolation=cv2.INTER_AREA)
    cv2.putText(im, f'f{f}', (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    tiles.append(im)
while len(tiles) % cols: tiles.append(np.zeros_like(tiles[0]))
rows = [np.concatenate(tiles[i:i + cols], 1) for i in range(0, len(tiles), cols)]
cv2.imwrite(out, np.concatenate(rows, 0), [cv2.IMWRITE_JPEG_QUALITY, 90])
