"""Grade per style bible 2.4: black floor #07070A, white ceiling #F3E8D0, cool-violet shadows, warm highlights, faint grain.
usage: python3 post.py in.png out.png [grain=0.006] [seed]   (16-bit or 8-bit input; 8-bit output)
       python3 post.py --seq in_dir pattern out_dir           (all matching PNGs)
"""
import sys, os, glob, numpy as np, cv2

FLOOR = np.array([7, 7, 10], np.float32) / 255
CEIL = np.array([243, 232, 208], np.float32) / 255
SHAD = np.array([26, 22, 32], np.float32) / 255
WARM = np.array([255, 240, 214], np.float32) / 255

def grade(img, grain=0.006, seed=0):
    x = img[..., ::-1].astype(np.float32) / (65535.0 if img.dtype == np.uint16 else 255.0)
    luma = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    # shadows towards cool violet, highlights a hair warmer
    ws = np.clip(1 - luma / 0.35, 0, 1)[..., None] ** 2 * 0.15
    x = x * (1 - ws) + SHAD * ws
    wh = np.clip((luma - 0.6) / 0.4, 0, 1)[..., None] * 0.10
    x = x * (1 - wh) + x * WARM * wh
    # soft shoulder into the ceiling, floor lift
    x = 1 - np.exp(-x * 1.08) * 1.0 if False else x
    x = FLOOR + (CEIL - FLOOR) * np.clip(x, 0, 1)
    if grain > 0:
        r = np.random.default_rng(seed)
        n = r.standard_normal(x.shape[:2]).astype(np.float32)
        n = cv2.GaussianBlur(n, (0, 0), 0.6)
        x = x + (grain * n * (0.4 + 0.6 * np.sqrt(np.clip(luma, 0, 1))))[..., None]
    return (np.clip(x, 0, 1)[..., ::-1] * 255 + 0.5).astype(np.uint8)

if __name__ == '__main__':
    if sys.argv[1] == '--seq':
        ind, pat, outd = sys.argv[2], sys.argv[3], sys.argv[4]; os.makedirs(outd, exist_ok=True)
        for i, f in enumerate(sorted(glob.glob(os.path.join(ind, pat)))):
            cv2.imwrite(os.path.join(outd, os.path.basename(f)), grade(cv2.imread(f, cv2.IMREAD_UNCHANGED), 0.006, i))
    else:
        g = float(sys.argv[3]) if len(sys.argv) > 3 else 0.006
        cv2.imwrite(sys.argv[2], grade(cv2.imread(sys.argv[1], cv2.IMREAD_UNCHANGED), g, int(sys.argv[4]) if len(sys.argv) > 4 else 0))
