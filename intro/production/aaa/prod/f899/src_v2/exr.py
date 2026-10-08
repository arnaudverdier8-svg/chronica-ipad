import sys, os, numpy as np
T = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/tools'
if T + '/pylib' not in sys.path:
    sys.path.insert(0, T + '/pylib')
import OpenEXR


def read(path):
    f = OpenEXR.File(path)
    ch = f.channels()
    if 'RGBA' in ch:
        return np.asarray(ch['RGBA'].pixels, np.float32)
    k = list(ch.keys())[0]
    return np.asarray(ch[k].pixels, np.float32)
