# Denoise a Blender multilayer EXR (Combined + Denoising Albedo/Normal) with pyoidn (OIDN 2.5 CPU).
# PYTHONPATH=<tools>/pylib python3 oidn_denoise.py noisy.exr ref.exr outprefix
import sys, time, numpy as np, OpenEXR, pyoidn
def load(p):
    f = OpenEXR.File(p); ch = f.channels(); return {k: np.asarray(v.pixels) for k, v in ch.items()}
def rgb(d, layer):
    keys = [k for k in d if k.startswith(layer)]
    if not keys: return None
    if layer in d and d[layer].ndim == 3: return np.ascontiguousarray(d[layer][..., :3].astype(np.float32))
    comp = 'XYZ' if f'{layer}.X' in d else 'RGB'
    return np.ascontiguousarray(np.stack([d[f'{layer}.{c}'] for c in comp], -1).astype(np.float32))
n = load(sys.argv[1]); r = load(sys.argv[2])
print('channels:', sorted(n.keys())[:20])
color = rgb(n, 'ViewLayer.Combined'); alb = rgb(n, 'ViewLayer.Denoising Albedo'); nor = rgb(n, 'ViewLayer.Denoising Normal'); ref = rgb(r, 'ViewLayer.Combined')
out = np.zeros_like(color)
dev = pyoidn.Device(pyoidn.OIDN_DEVICE_TYPE_CPU); dev.commit()
for name, aux in [('plain', None), ('albedo+normal', (alb, nor))]:
    flt = pyoidn.Filter(dev, pyoidn.OIDN_FILTER_TYPE_RT)
    flt.set_image(pyoidn.OIDN_IMAGE_COLOR, color, pyoidn.OIDN_FORMAT_FLOAT3)
    if aux is not None and aux[0] is not None:
        flt.set_image(pyoidn.OIDN_IMAGE_ALBEDO, aux[0], pyoidn.OIDN_FORMAT_FLOAT3)
        flt.set_image(pyoidn.OIDN_IMAGE_NORMAL, aux[1], pyoidn.OIDN_FORMAT_FLOAT3)
    flt.set_image(pyoidn.OIDN_IMAGE_OUTPUT, out, pyoidn.OIDN_FORMAT_FLOAT3)
    flt.set_bool('hdr', True); flt.commit()
    t = time.time(); flt.execute(); dt = time.time() - t
    err = dev.get_error()
    s = lambda x: np.clip(np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.maximum(x, 0), 1 / 2.4) - 0.055), 0, 1) * 255
    rm = lambda a: np.sqrt(((s(a) - s(ref)) ** 2).mean())
    print(f'{name}: {color.shape[1]}x{color.shape[0]} denoise {dt*1000:.0f} ms err={err} | RMSE(sRGB 8-bit) noisy={rm(color):.2f} denoised={rm(out):.2f}')
    np.save(sys.argv[3] + name.replace('+', '_') + '.npy', out)
    flt.release()
from PIL import Image
s8 = lambda x: Image.fromarray(np.clip(np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.maximum(x, 0), 1 / 2.4) - 0.055) * 255, 0, 255).astype(np.uint8)[::-1])
w = np.concatenate([color, out, ref], 1); s8(w).resize((w.shape[1] * 2, w.shape[0] * 2), Image.NEAREST).save(sys.argv[3] + 'cmp.png')
