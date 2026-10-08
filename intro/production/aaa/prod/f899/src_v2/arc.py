"""The century's single pale daylight arc (f899-917), shared by the plate (albedo bleach, tarnish front) and COMP (cool light pool, slip bleach).

All coordinates are sheet mm (v2 sheet, x already includes the 30 mm shift).  The arc enters from the LEFT: a diagonal, ragged leading edge
x_edge(x, y) = x0 + slope * (y - y_ref) + rag * noise(y, x), a soft width, and everything left of it is lit pale (7500 K) and bleached (dyes
fade toward grey-white, linen toward ivory); the right two thirds stay in the hearth's warm, darker light.  `shot['arc']` holds the parameters.
"""
import numpy as np


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def rag(x, y):
    """analytic ragged-edge perturbation in about [-1, 1] (mostly a function of y: the edge wanders along its length)."""
    return (0.55 * np.sin(y / 17.3 + 1.1) + 0.30 * np.sin(y / 7.9 + 2.3 + x / 90.0) + 0.15 * np.sin(y / 3.7 + 0.4 + x / 40.0)).astype(np.float32)


def edge_x(x, y, A):
    dy = y - A['y_ref']
    return A['x0'] + A['slope'] * dy + A.get('curv', 0.0) * dy * dy + A['rag_mm'] * rag(x, y)


def weights(x, y, A):
    """(light, bleach) in [0, 1] for broadcastable sheet-mm arrays: light = the pale arc's pool (soft width w_mm); bleach = the dye / linen fade,
    whose front trails the light's edge by trail_mm (the light has just arrived, the cloth is still bleaching behind it)."""
    e = edge_x(x, y, A)
    light = 1.0 - smoothstep(e - 0.5 * A['w_mm'], e + 0.5 * A['w_mm'], x)
    bleach = 1.0 - smoothstep(e - A['trail_mm'] - 0.5 * A['bw_mm'], e - A['trail_mm'] + 0.5 * A['bw_mm'], x)
    return light.astype(np.float32), bleach.astype(np.float32)
