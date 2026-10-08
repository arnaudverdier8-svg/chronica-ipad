"""Assemble deliverables: graded stills, motion mp4, knight-rise mp4 + contact sheet, maps overview.
python3 assemble.py [stills|motion|rise|maps|all]
"""
import sys, os, glob, subprocess, json, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from post import grade
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, 'renders'); OUT = ROOT
what = sys.argv[1] if len(sys.argv) > 1 else 'all'

def enc(frames, out, fps=30, hold=1):
    tmp = os.path.join(ROOT, 'work', 'enc_tmp'); os.makedirs(tmp, exist_ok=True)
    for f in glob.glob(os.path.join(tmp, '*.png')): os.remove(f)
    k = 0
    for i, f in enumerate(frames):
        g = grade(cv2.imread(f, cv2.IMREAD_UNCHANGED), 0.005, i)
        for _ in range(hold):
            cv2.imwrite(os.path.join(tmp, f'{k:05d}.png'), g); k += 1
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', os.path.join(tmp, '%05d.png'),
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], check=True)
    return k

if what in ('stills', 'all'):
    for src, dst in [('frontal_v2/frontal_0000.png', 'still_frontal_2560x1440.png'), ('oblique_v2/oblique_flat.png', 'still_oblique_2560x1440.png'),
                     ('oblique_v3/oblique_lift.png', 'still_oblique_knight_lifted_2560x1440.png')]:
        p = os.path.join(R, src)
        if os.path.exists(p):
            cv2.imwrite(os.path.join(OUT, dst), grade(cv2.imread(p, cv2.IMREAD_UNCHANGED), 0.005, 0)); print('wrote', dst)
if what in ('motion', 'all'):
    fr = sorted(glob.glob(os.path.join(R, 'motion', 'motion_*.png')))
    if fr: print('motion frames', enc(fr, os.path.join(OUT, 'motion_test_lightsweep_push_1280x720.mp4')))
if what in ('rise', 'all'):
    fr = sorted(glob.glob(os.path.join(R, 'rise_oblique', 'rise_oblique_*.png')))
    if fr:
        print('rise frames', enc(fr, os.path.join(OUT, 'knight_rise_1280x720_on_twos.mp4'), hold=2))
        pick = [fr[int(round(i))] for i in np.linspace(0, len(fr) - 1, 6)]
        ims = [cv2.resize(grade(cv2.imread(p, cv2.IMREAD_UNCHANGED), 0.0), (640, 360), interpolation=cv2.INTER_AREA) for p in pick]
        for im, p in zip(ims, pick):
            n = int(os.path.basename(p).split('_')[-1][:4])
            cv2.putText(im, f't={n / 30:.2f}s', (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (235, 225, 205), 2, cv2.LINE_AA)
        sheet = np.vstack([np.hstack(ims[0:3]), np.hstack(ims[3:6])])
        cv2.imwrite(os.path.join(OUT, 'knight_rise_contact_sheet.jpg'), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92])
if what in ('maps', 'all'):
    M = os.path.join(ROOT, os.environ.get('MAPSDIR', 'maps'))
    tiles = []
    for pre in ('king', 'knight'):
        a = cv2.imread(os.path.join(M, f'{pre}_albedo.png'), cv2.IMREAD_UNCHANGED)[..., :3]
        h = np.load(os.path.join(M, f'{pre}_height.npy')); h = np.clip(h / 2.2, 0, 1)
        n = cv2.imread(os.path.join(M, f'{pre}_normal8.png'))
        m = cv2.imread(os.path.join(M, f'{pre}_mat.png'), cv2.IMREAD_UNCHANGED)[..., :3]
        row = [cv2.resize(x if x.ndim == 3 else cv2.cvtColor((x * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR), (480, 500), interpolation=cv2.INTER_AREA) for x in (a, h, n, m)]
        tiles.append(np.hstack(row))
    sheet = np.vstack(tiles)
    for i, t in enumerate(['albedo (sRGB, cavity+fuzz baked)', 'height mm (mesh gets low-pass)', 'normal (high-pass strands)', 'R rough G metal B sheen']):
        cv2.putText(sheet, t, (8 + 480 * i, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 20, 230), 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(OUT, 'maps_overview.jpg'), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88]); print('maps overview')
