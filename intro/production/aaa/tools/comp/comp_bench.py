# Benchmark a numpy/OpenCV 2.5D compositor at 2560x1440: Ken Burns warp + per-frame relighting of
# an embroidered panel from a precomputed normal map + overlay layer + grain, piped to ffmpeg x264.
# usage: python3 comp_bench.py PANEL.png OUT.mp4 NFRAMES [preset]
import sys, time, subprocess, numpy as np, cv2
src, out, N = sys.argv[1], sys.argv[2], int(sys.argv[3]); preset = sys.argv[4] if len(sys.argv) > 4 else 'medium'
W, H = 2560, 1440
cv2.setNumThreads(4)
t0 = time.time()
alb = cv2.imread(src, cv2.IMREAD_COLOR).astype(np.float32) / 255.0
# upscale panel to 2x output so pans/zooms stay sharp (precompute once)
alb = cv2.resize(alb, (alb.shape[1] * 2, alb.shape[0] * 2), interpolation=cv2.INTER_CUBIC)
lum = cv2.cvtColor(alb, cv2.COLOR_BGR2GRAY)
# pseudo thread relief: luminance + fine directional stitch pattern
yy, xx = np.mgrid[0:lum.shape[0], 0:lum.shape[1]].astype(np.float32)
height = cv2.GaussianBlur(lum, (0, 0), 2.0) * 0.6 + 0.4 * (0.5 + 0.5 * np.sin((xx * 0.9 + yy * 0.5) * 0.9))
gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3)
nrm = np.dstack([-gx * 2, -gy * 2, np.ones_like(gx)]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
del xx, yy, gx, gy, height
print(f'precompute {time.time()-t0:.2f}s  source {alb.shape[1]}x{alb.shape[0]}', flush=True)
rng = np.random.default_rng(1)
grain = [rng.normal(0, 0.012, (H, W, 1)).astype(np.float32) for _ in range(4)]
vy, vx = np.mgrid[0:H, 0:W].astype(np.float32)
vign = (1 - 0.35 * (((vx - W / 2) / W) ** 2 + ((vy - H / 2) / H) ** 2) * 2.2)[..., None].astype(np.float32)
ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', '30', '-i', '-',
                       '-c:v', 'libx264', '-preset', preset, '-crf', '14', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709',
                       '-color_primaries', 'bt709', '-color_trc', 'bt709', out], stdin=subprocess.PIPE)
tw = tl = tg = tp = 0
t1 = time.time()
for f in range(N):
    u = f / max(1, N - 1)
    a = time.time()
    s = 0.62 + 0.06 * u                             # zoom
    cx, cy = alb.shape[1] * (0.4 + 0.2 * u), alb.shape[0] * 0.5
    M = np.float32([[1 / s * W / alb.shape[1] * s / (W / alb.shape[1]) * (W / (alb.shape[1] * s)), 0, 0], [0, 0, 0]])
    sc = W / (alb.shape[1] * s)
    M = np.float32([[sc, 0, W / 2 - cx * sc], [0, sc, H / 2 - cy * sc]])
    A = cv2.warpAffine(alb, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    Nn = cv2.warpAffine(nrm, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    b = time.time(); tw += b - a
    ang = 2.2 + 1.2 * u                              # raking light sweeps across the cloth
    L = np.array([np.cos(ang), np.sin(ang), 0.45], np.float32); L /= np.linalg.norm(L)
    shade = np.clip(Nn @ L, 0, 1)[..., None]
    img = A * (0.35 + 0.9 * shade)
    c = time.time(); tl += c - b
    img = img * vign + grain[f % 4]
    d = time.time(); tg += d - c
    ff.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
    tp += time.time() - d
ff.stdin.close(); ff.wait()
tot = time.time() - t1
print(f'frames={N} total={tot:.2f}s per_frame={tot/N:.3f}s | warp={tw/N:.3f} light={tl/N:.3f} grain/vign={tg/N:.3f} pipe+encode(wait)={tp/N:.3f}', flush=True)
