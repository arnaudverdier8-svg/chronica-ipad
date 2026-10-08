import __main__ as _m; R = _m.R
import cv2, time, importlib, sys
import threads3d as T
T.FUZZ.update(pile=16.0, fly=2.6, a_pile=0.62, a_fly=0.45, side=0.82)
import voidfx, kingvoid, loose
importlib.reload(voidfx); importlib.reload(kingvoid); importlib.reload(loose)
shot.VFX = voidfx
t = time.time()
A = shot._ASSETS
kv = kingvoid.KingVoid(A['G'], verbose=False)
res = loose.HoleResidue(kv); kv._snaps.clear()
A.update(kv=kv, loose=loose.LooseEnds(kv), residue=res)
print('  void rebuilt %.1fs' % (time.time() - t), flush=True)
r = R(cx=295, cy=190, cache='cache_void.pkl', mode='save')
cv2.imwrite(os.path.join(W, 'v1_void.png'), r['img'][..., ::-1])
