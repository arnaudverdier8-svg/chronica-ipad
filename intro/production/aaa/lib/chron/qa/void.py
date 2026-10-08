"""Gate G4: no void / background pixels.  Every renderer returns a coverage alpha (the warped 'inside the read window'
mask, BORDER_CONSTANT 0) - any output pixel not fully covered, or non-finite, or equal to a sentinel colour fails."""
import numpy as np


class VoidError(AssertionError):
    pass


def void_mask(img, alpha=None, sentinel=None, tol=1e-3):
    bad = ~np.isfinite(img).all(-1) if img.dtype.kind == 'f' else np.zeros(img.shape[:2], bool)
    if alpha is not None:
        bad |= alpha < 1 - tol
    if sentinel is not None:
        bad |= (np.abs(img.astype(np.float32) - np.asarray(sentinel, np.float32)).max(-1) < 1e-6)
    return bad


def check_void(img, alpha=None, sentinel=None, raise_=True, name=''):
    """returns (ok, n_bad).  raise_ -> VoidError when any void / background pixel exists."""
    bad = void_mask(img, alpha, sentinel)
    n = int(bad.sum())
    if n and raise_:
        ys, xs = np.nonzero(bad)
        raise VoidError(f'G4 void check failed {name}: {n} void pixels, bbox x{xs.min()}-{xs.max()} y{ys.min()}-{ys.max()}')
    return n == 0, n
