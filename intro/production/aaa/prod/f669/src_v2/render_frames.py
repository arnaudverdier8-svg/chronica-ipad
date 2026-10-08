"""Render selected frames of S09 at 1440p (full detail, L0): python3 render_frames.py OUTDIR f1 f2 ...  -> OUTDIR/f%03d_2560x1440.png + 1280 previews."""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
import shot
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
for f in [int(a) for a in sys.argv[2:]]:
    t = time.time()
    r = shot.render_frame(f)
    cv2.imwrite(os.path.join(out, f'f{f:03d}_2560x1440.png'), r['img'][..., ::-1])
    cv2.imwrite(os.path.join(out, f'f{f:03d}_1280.jpg'), cv2.resize(r['img'][..., ::-1], (1280, 720), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 93])
    print(f, 'frame %.1fs' % (time.time() - t), 'loose', r['timing']['loose'], 'u', round(r['timing']['u']), flush=True)
