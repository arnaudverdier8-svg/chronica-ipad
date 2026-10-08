# post.py - linear decode of Blender 'Standard' 16-bit PNG (rendered at exposure E_in) -> ACES fit -> CHRONICA grade -> sRGB 8-bit
# usage: python3 post.py in.png out.png [exposure_ev=0] [E_in=-1.5] [vignette=0.25]
import sys, numpy as np, cv2
SAT = 0.86
def dec(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def enc(c): c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)
def grade(lin, ev=0.0, vig=0.25):
    x = lin * (2 ** ev) * 0.85 * 1.6
    x = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    H, W = x.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)) / 1.4142
    x *= (1 - vig * r ** 2.2)[..., None]
    lum = (x * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    sh = np.clip(1 - lum / 0.25, 0, 1); hi = np.clip((lum - 0.6) / 0.4, 0, 1)
    x = x * (1 - 0.12 * sh) + 0.12 * sh * lum * np.array([0.88, 0.86, 1.08], np.float32)
    x = x * (1 - 0.10 * hi) + 0.10 * hi * x * np.array([1.04, 1.0, 0.94], np.float32)
    lum2 = (x * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    x = lum2 + (x - lum2) * SAT
    lo = dec(np.array([7, 7, 10], np.float32) / 255); hi_c = dec(np.array([243, 232, 208], np.float32) / 255)
    x = lo + x * (hi_c - lo)
    return enc(x)
if __name__ == '__main__':
    inp, out = sys.argv[1], sys.argv[2]
    ev = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    ein = float(sys.argv[4]) if len(sys.argv) > 4 else -1.5
    vig = float(sys.argv[5]) if len(sys.argv) > 5 else 0.25
    SAT = float(sys.argv[6]) if len(sys.argv) > 6 else 0.86
    im = cv2.imread(inp, cv2.IMREAD_UNCHANGED)[..., ::-1].astype(np.float32)
    im /= 65535.0 if im.max() > 255 else 255.0
    lin = dec(im) * 2 ** (-ein)
    o = grade(lin, ev, vig)
    cv2.imwrite(out, (o * 255 + 0.5).astype(np.uint8)[..., ::-1])
