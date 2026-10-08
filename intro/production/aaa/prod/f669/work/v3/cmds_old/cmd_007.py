import __main__ as _m; R = _m.R
import cv2, numpy as np
import threads3d
orig = threads3d.ThreadSet.render
def patched(self, img, ctx, cpos, lfn, fill, **kw):
    if kw.get('flame_r_mm') == 6.0 and kw.get('contact_ao') is not None:
        kw['shadow_strength'] = 1.0
        kw['contact_ao'] = 0.0
    return orig(self, img, ctx, cpos, lfn, fill, **kw)
shot.ThreadSet.render = patched
r = R(cache='cache_strands.pkl')
cv2.imwrite(os.path.join(W, 's2b_strands.png'), r['img'][..., ::-1])
shot.ThreadSet.render = orig
