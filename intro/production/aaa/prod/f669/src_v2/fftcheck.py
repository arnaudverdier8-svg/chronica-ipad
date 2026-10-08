"""periodicity of the weave: FFT peak / mean of a 512x512 luma window (Hann) in the void, and in the neighbouring linen."""
import sys, numpy as np, cv2
def peak(path, x, y, n=512):
    im = cv2.imread(path)[..., ::-1].astype(np.float32) / 255
    g = im[y:y + n, x:x + n] @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    g = g - cv2.GaussianBlur(g, (0, 0), 6)
    w = np.outer(np.hanning(n), np.hanning(n)).astype(np.float32)
    F = np.abs(np.fft.fftshift(np.fft.fft2(g * w)))
    cy = cx = n // 2
    F[cy - 10:cy + 11, cx - 10:cx + 11] = 0           # DC / low freq
    return float(F.max() / F[F > 0].mean())
if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(p.split('/')[-3:], 'void %.1f' % peak(p, 1120, 760), 'linen-left %.1f' % peak(p, 80, 440))
