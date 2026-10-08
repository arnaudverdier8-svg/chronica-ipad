import sys, numpy as np, cv2
def peak(path, x, y, n=256):
    im = cv2.imread(path)[..., ::-1].astype(np.float32) / 255
    g = im[y:y + n, x:x + n] @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    g = g - cv2.GaussianBlur(g, (0, 0), 5)
    w = np.outer(np.hanning(n), np.hanning(n)).astype(np.float32)
    F = np.abs(np.fft.fftshift(np.fft.fft2(g * w))) ** 2
    cy = cx = n // 2
    F[cy - 6:cy + 7, cx - 6:cx + 7] = 0
    tot = F.sum()
    # fraction of power in the top 0.2% of frequency bins (a lattice concentrates power in a few bins; irregular cloth does not)
    k = max(8, int(0.002 * F.size))
    top = np.sort(F.ravel())[-k:].sum() / tot
    return top
for p, (x, y) in [(a.split('@')[0], tuple(int(v) for v in a.split('@')[1].split(','))) for a in sys.argv[1:]]:
    print(p, (x, y), 'top-bin power fraction %.3f' % peak(p, x, y))
