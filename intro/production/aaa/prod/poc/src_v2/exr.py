"""EXR io via the OpenEXR 3.5 python bindings in aaa/tools/pylib."""
import sys, numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/tools/pylib')
import OpenEXR


def write_exr(path, img, half=True):
    img = np.ascontiguousarray(img.astype(np.float16 if half else np.float32))
    name = {1: 'Y', 3: 'RGB', 4: 'RGBA'}[1 if img.ndim == 2 else img.shape[2]]
    hdr = {'compression': OpenEXR.ZIP_COMPRESSION, 'type': OpenEXR.scanlineimage}
    with OpenEXR.File(hdr, {name: img}) as f:
        f.write(path)


def read_exr(path):
    with OpenEXR.File(path, separate_channels=False) as f:
        ch = f.channels()
        for k in ('RGBA', 'RGB', 'Y'):
            if k in ch: return np.array(ch[k].pixels, np.float32)
        # Blender multilayer/named channels
        ks = sorted(ch.keys())
        return {k: np.array(ch[k].pixels, np.float32) for k in ks}
