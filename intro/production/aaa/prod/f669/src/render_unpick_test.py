"""2 s unpick test (S09 f600-660) at 1280x720, 30 fps, on the real audio slice.  Run:  nice -n 5 python3 render_unpick_test.py
Frames -> ../out/unpick_test_720p/f%03d.png, movie -> ../out/f669_unpick_test_f600-660_720p.mp4, contact sheet."""
import os, sys, time, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
import shot
OUT = os.path.join(HERE, '..', 'out'); SEQ = os.path.join(OUT, 'unpick_test_720p')
os.makedirs(SEQ, exist_ok=True)
F0, F1 = int(os.environ.get('F0', 600)), int(os.environ.get('F1', 660))
WAV = os.path.join(shot.AAA, 'audio', 'audio_master_1984f_s16.wav')
log = []
for f in range(F0, F1 + 1):
    p = os.path.join(SEQ, f'f{f:03d}.png')
    if os.path.exists(p) and not os.environ.get('FORCE'):
        continue
    t = time.time()
    r = shot.render_frame(f, out_wh=(1280, 720), level=1)          # level fixed for the whole shot (no mip pop)
    cv2.imwrite(p, r['img'][..., ::-1])
    tm = r['timing']
    log.append(dict(f=f, s=round(time.time() - t, 2), loose=tm['loose'], u=round(tm['u']), zoom=round(shot.zoom(f), 4)))
    print(log[-1], flush=True)
json.dump(log, open(os.path.join(SEQ, 'render_log.json'), 'a'), indent=0)
# audio slice: frame f <-> sample f * 1470 @ 44.1 kHz
aud = os.path.join(SEQ, 'audio.wav')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', WAV, '-af', f'atrim=start_sample={F0 * 1470}:end_sample={(F1 + 1) * 1470},asetpts=PTS-STARTPTS', aud], check=True)
mp4 = os.path.join(OUT, f'f669_unpick_test_f{F0}-{F1}_720p.mp4')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '30', '-start_number', str(F0), '-i', os.path.join(SEQ, 'f%03d.png'),
                '-i', aud, '-c:v', 'libx264', '-crf', '14', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                '-shortest', mp4], check=True)
# contact sheet (every 6th frame)
sel = list(range(F0, F1 + 1, 6))[:10]
ims = [cv2.resize(cv2.imread(os.path.join(SEQ, f'f{f:03d}.png')), (512, 288), interpolation=cv2.INTER_AREA) for f in sel]
for im, f in zip(ims, sel):
    cv2.putText(im, f'f{f}', (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(im, f'f{f}', (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (235, 225, 205), 1, cv2.LINE_AA)
while len(ims) % 2: ims.append(np.zeros_like(ims[0]))
rows = [np.hstack(ims[i:i + 2]) for i in range(0, len(ims), 2)]
cv2.imwrite(os.path.join(OUT, 'f669_unpick_test_sheet.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
print('wrote', mp4)
