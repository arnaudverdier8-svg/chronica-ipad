# python3.12 esrgan_test.py IN.png OUTPREFIX  (Real-ESRGAN via ncnn on lavapipe CPU Vulkan)
import sys, time, os
from PIL import Image
from realesrgan_ncnn_py import Realesrgan
src = Image.open(sys.argv[1]).convert('RGB')
crop = src.crop((1180, 300, 1180 + 256, 300 + 256))   # king's face region
crop.save(sys.argv[2] + 'in.png')
for mid, name in [(0, 'x2_animevideov3'), (4, 'x4plus')]:
    try:
        t = time.time(); r = Realesrgan(gpuid=0, model=mid); t1 = time.time()
        out = r.process_pil(crop); dt = time.time() - t1
        out.save(sys.argv[2] + name + '.png'); print(f'{name}: init {t1-t:.2f}s process {dt:.2f}s out {out.size}', flush=True)
    except Exception as ex:
        print(name, 'FAILED', ex, flush=True)
