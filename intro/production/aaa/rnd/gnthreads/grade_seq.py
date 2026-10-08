# grade_seq.py indir prefix outdir [ev] -> graded PNGs (uses post.grade)
import sys, os, glob, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post
ind, pre, outd = sys.argv[1], sys.argv[2], sys.argv[3]
ev = float(sys.argv[4]) if len(sys.argv) > 4 else 0.3
os.makedirs(outd, exist_ok=True)
for f in sorted(glob.glob(os.path.join(ind, pre + '*.png'))):
    im = cv2.imread(f, cv2.IMREAD_UNCHANGED)[..., ::-1].astype(np.float32)
    im /= 65535.0 if im.dtype == np.float32 and im.max() > 255 else 255.0
    lin = post.dec(im) * 2 ** 1.5
    o = post.grade(lin, ev, 0.25)
    cv2.imwrite(os.path.join(outd, os.path.basename(f)), (o * 255 + 0.5).astype(np.uint8)[..., ::-1])
print('graded', outd)
