"""World <-> strip geometry of the keyframe (world mm, origin at the frame centre, x right, y down)."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *

S_SCREEN = float(os.environ.get('F_SCREEN', '0.75'))     # screen px per mm (0.75 = the S18 hold framing; F_SCREEN=1.0 renders the tighter alternative)
OUT_W, OUT_H = 2560, 1440
WIN_W, WIN_H = OUT_W / S_SCREEN, OUT_H / S_SCREEN    # 3413.3 x 1920 mm

GEO = dict(
    uc=float(os.environ.get('F_UC', '1830')),           # strip u at world x = 0
    yc=float(os.environ.get('F_YC', '0.0')),             # world y of the strip's mid-line (v = Hs/2) at x = 0
    theta_deg=float(os.environ.get('F_THETA', '-3.0')),      # mean slope (negative: the right end is higher: dutch + the strip rising toward the glint)
    amp=20.0, lam=2700.0, phi=0.9,   # gentle S-bow of the cloth lying on the table
    Hs=400.0,
)


def centre_y(u, g=GEO):
    x = u - g['uc']
    return g['yc'] + math.tan(math.radians(g['theta_deg'])) * x + g['amp'] * np.sin(2 * math.pi * x / g['lam'] + g['phi'])


def centre_dy(u, g=GEO):
    x = u - g['uc']
    return math.tan(math.radians(g['theta_deg'])) + g['amp'] * 2 * math.pi / g['lam'] * np.cos(2 * math.pi * x / g['lam'] + g['phi'])


def world_to_strip(X, Y, g=GEO, iters=6):
    """world mm arrays -> strip (u, v) mm, and the local tangent angle (rad)."""
    u = X + g['uc']
    for _ in range(iters):
        sl = centre_dy(u, g)
        f = (X - (u - g['uc'])) + (Y - centre_y(u, g)) * sl
        u = u + f / (1 + sl * sl)
    sl = centre_dy(u, g)
    c = 1 / np.sqrt(1 + sl * sl)
    v = g['Hs'] / 2 + (Y - centre_y(u, g)) * c + (X - (u - g['uc'])) * (-sl * c)
    return u.astype(np.float32), v.astype(np.float32), np.arctan(sl).astype(np.float32)


def strip_to_world(u, v, g=GEO):
    sl = centre_dy(u, g); c = 1 / np.sqrt(1 + sl * sl)
    tx, ty = c, sl * c
    nx, ny = -sl * c, c
    return (u - g['uc']) + (v - g['Hs'] / 2) * nx, centre_y(u, g) + (v - g['Hs'] / 2) * ny
