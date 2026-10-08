"""Decode the workbench material-ID elevation renders (data/elev/*_id.png) into a material-name label image."""
import json, numpy as np, cv2
P = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc'


def _enc(c):
    c = np.asarray(c, np.float64) / 255
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055) * 255


def load_elev(name):
    im = cv2.imread(f'{P}/data/elev/{name}_id.png', cv2.IMREAD_UNCHANGED)
    J = json.load(open(f'{P}/data/elev/{name}_id.json'))
    names = list(J['ids'].keys())
    ref = np.array([_enc(J['ids'][n]) for n in names], np.float32)        # RGB
    rgb = im[..., 2::-1].astype(np.float32)
    d = np.linalg.norm(rgb[..., None, :] - ref[None, None], axis=-1)
    lab = np.argmin(d, -1).astype(np.int32)
    lab[(im[..., 3] < 128) | (d.min(-1) > 20)] = -1
    return lab, names, J
