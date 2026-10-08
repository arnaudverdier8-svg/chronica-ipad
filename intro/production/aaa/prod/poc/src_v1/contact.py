"""contact sheet of chosen frames: python3 contact.py FRAMEDIR out.jpg f1 f2 ... (labels with the global frame)"""
import sys, cv2, numpy as np
d, out, fs = sys.argv[1], sys.argv[2], [int(v) for v in sys.argv[3:]]
tiles = []
for f in fs:
    im = cv2.imread(f'{d}/f{f:04d}.png')
    im = cv2.resize(im, (640, 360), interpolation=cv2.INTER_AREA)
    cv2.putText(im, f'f{f}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(im, f'f{f}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    tiles.append(im)
while len(tiles) % 3: tiles.append(np.zeros_like(tiles[0]))
rows = [np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]
cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
