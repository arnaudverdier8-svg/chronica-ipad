"""iteration contact sheet: python3 make_iter_sheet.py OUT.jpg label1=path1.png label2=path2.png ...  (each tile 960 x 540, 2 per row)"""
import sys
import cv2, numpy as np


def main():
    out = sys.argv[1]
    tiles = []
    for a in sys.argv[2:]:
        lab, path = a.split('=', 1)
        im = cv2.imread(path)
        t = cv2.resize(im, (960, 540), interpolation=cv2.INTER_AREA)
        cv2.putText(t, lab, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (10, 10, 10), 4, cv2.LINE_AA)
        cv2.putText(t, lab, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(t)
    rows = []
    for i in range(0, len(tiles), 2):
        r = tiles[i:i + 2]
        while len(r) < 2:
            r.append(np.zeros_like(r[0]))
        rows.append(np.hstack(r))
    cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print('->', out)


if __name__ == '__main__':
    main()
