"""Reflection streaks: additive light smears on the river for lights that sit across / on the water.

A light of height h above the water at horizontal distance D from the office windows is seen reflected on
the water at the point where the sight line to its mirror image crosses the surface, i.e. at a fraction
f = H / (H + h) of the way to it (H = eye height above the water).  The smear is then stretched along the
sight line towards the viewer, like real glitter on rippled water, so on screen it hangs straight under
the light.  Vertex colour: rgb = light colour, a = intensity ramp (0 at the ends / edges); the
Branson/Streak shader breaks it up with moving noise.
"""
import numpy as np
from br_common import F32
import br_world as W
import br_city as C

EYE = (0.0, 8.1, -15.5)        # a point just inside the south windows (x, height above the water, z)
ROWS_T = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
ROWS_A = np.array([0.0, 1.0, 0.55, 0.24, 0.0])


def build_streaks():
    ex, eh, ez = EYE
    P, T, Col = [], [], []
    base = 0
    kept = 0
    for (x, z, h, w, rgb, inten) in C.STREAKS:
        D = ez - z
        if D < 25.0:
            continue
        hh = max(h - W.WATER_Y, 0.6)
        f = eh / (eh + hh)
        xc = ex + (x - ex) * f
        zc = ez - D * f
        if float(W.height(np.float64(xc), np.float64(zc))) > -0.4:
            continue                                   # reflection point is not on open water
        r = np.array([x - ex, z - ez], dtype=np.float64)
        rl = float(np.hypot(*r))
        back = -r / rl                                  # horizontal unit vector pointing back to the viewer
        perp = np.array([-back[1], back[0]])
        L = 0.50 * D * f + 14.0                         # streak length along the sight line
        half_w = np.maximum(w * f * 0.55, 0.45) * (0.8 + 1.3 * ROWS_T)
        for ri in range(5):
            along = (ROWS_T[ri] - 0.25) * L
            cx, cz = xc + back[0] * along, zc + back[1] * along
            dist = float(np.hypot(cx - ex, cz - ez))
            y = W.WATER_Y + 0.12 + 0.0007 * dist
            for c, sx in enumerate((-1.0, 0.0, 1.0)):
                P.append([cx + perp[0] * sx * half_w[ri], y, cz + perp[1] * sx * half_w[ri]])
                a = ROWS_A[ri] * inten * (1.0 if c == 1 else 0.0)
                Col.append([rgb[0], rgb[1], rgb[2], a])
        for ri in range(4):
            for c in range(2):
                a_ = base + ri * 3 + c
                T.append([a_, a_ + 4, a_ + 1])
                T.append([a_, a_ + 3, a_ + 4])
        base += 15
        kept += 1
    if not P:
        return np.zeros((0, 3), F32), np.zeros((0, 3), np.int32), np.zeros((0, 4), F32), 0
    return np.array(P, dtype=F32), np.array(T, dtype=np.int32), np.array(Col, dtype=F32), kept
