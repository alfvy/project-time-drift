"""Landmarks and props: Ferris wheel, river bridge, piers, boats (pontoon, fishing, paddle-wheel showboat),
water tower, radio tower.   All Unity world coordinates."""
import math
import numpy as np
from br_common import (F32, smoothstep, hexlin, Acc, box, pyramid, cylinder, cone, blob_template, rot_y,
                       orient_outward, prism_poly)
import br_world as W
import br_city as C

_BLOB_P, _BLOB_T = blob_template()
STEEL = hexlin('#B4B8BF')
DARKSTEEL = hexlin('#3A3E45')
CONCRETE = hexlin('#8D8B84')
CONCRETE_D = hexlin('#6F6D68')
WOOD = hexlin('#7A5B3C')
WOOD_D = hexlin('#4F3B28')
WHITE = hexlin('#E4E2D8')
RED = hexlin('#8F2A22')
WHEEL_LIGHTS = [hexlin(h) for h in ('#FF4D4D', '#FFD24D', '#4DFFB0', '#4D9BFF', '#E64DFF')]
GONDOLAS = [hexlin(h) for h in ('#D94A3D', '#E0A830', '#3D8FD9', '#3DB57A', '#B65AD9')]


def hz(x, z):
    return float(W.height(np.float64(x), np.float64(z)))


def beam(p0, p1, t=0.3):
    p0 = np.asarray(p0, dtype=F32)
    p1 = np.asarray(p1, dtype=F32)
    u = p1 - p0
    L = float(np.linalg.norm(u))
    u = u / max(L, 1e-6)
    ref = np.array([0, 1, 0], dtype=F32)
    if abs(float(np.dot(u, ref))) > 0.95:
        ref = np.array([1, 0, 0], dtype=F32)
    v = np.cross(u, ref)
    v /= np.linalg.norm(v)
    w = np.cross(u, v)
    h = t / 2.0
    corners = []
    for p in (p0, p1):
        for sv, sw in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            corners.append(p + v * h * sv + w * h * sw)
    P = np.array(corners, dtype=F32)
    T = [[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7]]
    for i in range(4):
        j = (i + 1) % 4
        T += [[i, j, 4 + j], [i, 4 + j, 4 + i]]
    T = np.array(T, dtype=np.int32)
    return P, orient_outward(P, T, P.mean(axis=0))


def dot(acc_lights, x, y, z, r, col):
    c = col.copy()
    c[3] = 1.0
    acc_lights.add(_BLOB_P * r + np.array([x, y, z], dtype=F32), _BLOB_T, c, flat=False)


def lbox(acc, cx, y, cz, yaw, lx, ly, lz, sx, sy, sz, col, bottom=False):
    """Box placed in a yawed local frame: local offset (lx, ly, lz) from (cx, y, cz)."""
    off = rot_y(np.array([[lx, 0, lz]], dtype=F32), yaw)[0]
    P, T = box(cx + off[0], y + ly, cz + off[2], sx, sy, sz, yaw, bottom=bottom)
    acc.add(P, T, col)


# --------------------------------------------------------------------------- Ferris wheel
def ferris_wheel(A, rng, cx, cz, r=20.0, hub_h=24.0):
    P, L = A['BR_Props'], A['BR_Lights']
    y_base = hz(cx, cz)
    hub = np.array([cx, y_base + hub_h, cz], dtype=F32)
    N = 40
    ang = np.linspace(0, 2 * np.pi, N, endpoint=False)
    for zoff in (-1.7, 1.7):
        ring = [hub + np.array([r * math.cos(a), r * math.sin(a), zoff], dtype=F32) for a in ang]
        for i in range(N):
            P.add(*beam(ring[i], ring[(i + 1) % N], 0.45), STEEL)
            dot(L, *(ring[i] + np.array([0, 0, 0.35 * np.sign(zoff)], dtype=F32)), 0.42, WHEEL_LIGHTS[i % 5])
        for k in range(0, N, 2):
            P.add(*beam(hub + np.array([0, 0, zoff], dtype=F32), ring[k], 0.16), STEEL)
        inner = [hub + np.array([r * 0.55 * math.cos(a), r * 0.55 * math.sin(a), zoff], dtype=F32) for a in ang[::2]]
        for i in range(len(inner)):
            P.add(*beam(inner[i], inner[(i + 1) % len(inner)], 0.20), STEEL)
            dot(L, *(inner[i] + np.array([0, 0, 0.3 * np.sign(zoff)], dtype=F32)), 0.30, WHEEL_LIGHTS[(i + 2) % 5])
    for k in range(0, N, 2):
        a = ang[k]
        p = hub + np.array([r * math.cos(a), r * math.sin(a) - 1.45, 0], dtype=F32)
        P.add(*box(p[0], p[1], p[2], 2.3, 1.7, 2.1), GONDOLAS[(k // 2) % 5])
    P.add(*box(cx, hub[1] - 1.2, cz, 2.6, 2.4, 4.6), DARKSTEEL)
    for zoff in (-3.0, 3.0):
        P.add(*beam([cx - 13.5, y_base + 0.4, cz + zoff], hub + np.array([-0.5, 0, zoff * 0.55], dtype=F32), 0.9), DARKSTEEL)
        P.add(*beam([cx + 13.5, y_base + 0.4, cz + zoff], hub + np.array([0.5, 0, zoff * 0.55], dtype=F32), 0.9), DARKSTEEL)
    P.add(*box(cx, y_base - 0.2, cz, 36.0, 0.8, 9.0), CONCRETE_D)
    # a few lamps and a ticket booth
    P.add(*box(cx + 16.0, y_base, cz - 8.0, 5.0, 3.2, 4.0), hexlin('#A0443A'))


# --------------------------------------------------------------------------- bridge
def bridge(A, rng, x0=345.0, width=12.0, deck_h=11.5, thick=1.4):
    R, P, L = A['BR_Roads'], A['BR_Props'], A['BR_Lights']
    zn, zs = [float(v) for v in W.banks(x0)]
    zz = np.arange(96.0, zs - 72.0, -4.0)
    g_n = float(W.bench_y(x0))
    g_s = hz(x0, zs - 72.0)
    yN = g_n + (deck_h - g_n) * smoothstep(zn + 150.0, zn + 8.0, zz)
    yS = deck_h + (g_s - deck_h) * smoothstep(zs - 4.0, zs - 100.0, zz)
    y = np.where(zz > (zn + zs) / 2.0, yN, yS)
    hw = width / 2.0
    for i in range(len(zz) - 1):
        z0, z1, y0, y1 = zz[i], zz[i + 1], y[i], y[i + 1]
        V = np.array([[x0 - hw, y0, z0], [x0 + hw, y0, z0], [x0 + hw, y1, z1], [x0 - hw, y1, z1],
                      [x0 - hw, y0 - thick, z0], [x0 + hw, y0 - thick, z0], [x0 + hw, y1 - thick, z1], [x0 - hw, y1 - thick, z1]], dtype=F32)
        T = np.array([[0, 1, 2], [0, 2, 3],            # top
                      [4, 5, 6], [4, 6, 7],            # bottom
                      [0, 4, 7], [0, 7, 3],            # left
                      [1, 2, 6], [1, 6, 5]], dtype=np.int32)   # right
        T = orient_outward(V, T, V.mean(axis=0))
        R.add(V, T[:2], hexlin('#303236'))
        P.add(V, T[2:], CONCRETE)
        # railings
        for sx_ in (-1, 1):
            xx = x0 + sx_ * (hw - 0.15)
            P.add(*beam([xx, y0 + 1.05, z0], [xx, y1 + 1.05, z1], 0.14), STEEL)
            P.add(*beam([xx, y0 + 0.50, z0], [xx, y1 + 0.50, z1], 0.10), STEEL)
            if i % 2 == 0:
                P.add(*box(xx, y0, z0, 0.12, 1.1, 0.12), STEEL)
    # piers / columns every 28 m
    for k in range(0, len(zz), 7):
        z, yy = zz[k], y[k]
        base = hz(x0, z) - 0.6
        if yy - thick - base < 1.5:
            continue
        for sx_ in (-1, 1):
            P.add(*box(x0 + sx_ * 3.4, base, z, 2.2, yy - thick - base, 4.0), CONCRETE_D)
        P.add(*box(x0, yy - thick - 1.3, z, 11.0, 1.3, 4.6), CONCRETE)       # pier cap
    # lamps along the deck
    for k in range(3, len(zz), 8):
        sx_ = 1 if (k // 8) % 2 == 0 else -1
        C.lamp(P, L, x0 + sx_ * (hw - 0.6), float(y[k]), float(zz[k]), 6.5)
    # a short stretch of approach road up to the highway
    C.mark_line(np.stack([np.full(len(zz), x0), zz], axis=1), 12.0, urban=0.3)


# --------------------------------------------------------------------------- piers and boats
def pier(A, rng, x, a0=8.0, length=72.0, width=4.2, gazebo=True):
    P, L = A['BR_Props'], A['BR_Lights']
    zn = float(W.banks(x)[0])
    z_a = zn + a0
    z_b = z_a - length
    zm = (z_a + z_b) / 2
    yd = 1.35
    P.add(*box(x, yd - 0.28, zm, width, 0.28, length), WOOD)
    for z in np.arange(z_a - 2.0, z_b + 1.0, -6.0):
        for sx_ in (-1, 1):
            P.add(*box(x + sx_ * (width / 2 - 0.2), W.WATER_Y - 3.0, z, 0.32, yd + 3.0 - 0.28, 0.32), WOOD_D)
    for sx_ in (-1, 1):
        xx = x + sx_ * (width / 2 - 0.05)
        P.add(*box(xx, yd, zm, 0.10, 0.08, length), WOOD_D)
        for z in np.arange(z_a - 1.0, z_b, -3.0):
            P.add(*box(xx, yd, z, 0.10, 1.0, 0.10), WOOD_D)
    for z in np.arange(z_a - 8.0, z_b + 4.0, -14.0):
        C.lamp(P, L, x + (width / 2 - 0.4), yd, z, 3.4)
        C.lamp(P, L, x - (width / 2 - 0.4), yd, z - 7.0, 3.4)
        C.add_streak(x + (width / 2 - 0.4), z, yd + 3.6, 1.0, C.LAMP[:3], 0.8)
        C.add_streak(x - (width / 2 - 0.4), z - 7.0, yd + 3.6, 1.0, C.LAMP[:3], 0.8)
    if gazebo:
        gz = z_b - 4.0
        P.add(*box(x, yd - 0.28, gz, 8.0, 0.28, 8.0), WOOD)
        for sx_ in (-1, 1):
            for sz_ in (-1, 1):
                P.add(*box(x + sx_ * 3.4, yd, gz + sz_ * 3.4, 0.22, 3.2, 0.22), WOOD_D)
        P.add(*pyramid(x, yd + 3.2, gz, 9.2, 9.2, 2.6), hexlin('#5C3A2A'))
        dot(L, x, yd + 3.0, gz, 0.45, hexlin('#FFC070'))


def pontoon(A, cx, cz, yaw, col=None, y=0.0):
    P = A['BR_Props']
    col = col if col is not None else WHITE
    for sx_ in (-1.15, 1.15):
        lbox(P, cx, y, cz, yaw, sx_, -0.15, 0.0, 0.7, 0.8, 7.6, STEEL)
    lbox(P, cx, y, cz, yaw, 0.0, 0.62, 0.0, 3.0, 0.16, 7.0, hexlin('#9A9486'))
    lbox(P, cx, y, cz, yaw, 0.0, 2.2, 0.4, 2.9, 0.10, 4.4, col)
    for sx_ in (-1.3, 1.3):
        for sz_ in (-1.6, 2.2):
            lbox(P, cx, y, cz, yaw, sx_, 0.7, sz_, 0.07, 1.5, 0.07, STEEL)
    for sx_ in (-1.45, 1.45):
        lbox(P, cx, y, cz, yaw, sx_, 0.75, 0.0, 0.06, 0.07, 6.6, STEEL)


def fishing_boat(A, cx, cz, yaw, col=None, y=0.0):
    P = A['BR_Props']
    col = col if col is not None else hexlin('#D9D9D6')
    poly = [(cx - 0.95, cz - 3.0), (cx + 0.95, cz - 3.0), (cx + 1.15, cz + 1.4), (cx, cz + 3.5), (cx - 1.15, cz + 1.4)]
    V, T = prism_poly(poly, y - 0.15, 0.95, cap_top=True)
    V = rot_y(V, yaw, cx, cz)
    P.add(V, T, col)
    lbox(P, cx, y, cz, yaw, 0.0, 1.0, -0.6, 1.5, 0.9, 1.7, hexlin('#C9C6B8'))
    lbox(P, cx, y, cz, yaw, 0.0, 1.9, -0.6, 1.6, 0.12, 1.9, hexlin('#2B2D30'))


def showboat(A, rng, cx, cz, y=0.0, length=52.0):
    """Branson-Belle-style paddle-wheel showboat, long axis along X (stern/paddle at the west)."""
    P, B, L = A['BR_Props'], A['BR_Buildings'], A['BR_Lights']
    wc = hexlin('#E9E6DC')
    ph = lambda yy: (yy / C.FLOOR_H) % 1.0

    def deck(lx, ly, sx, sy, sz, col=wc):
        c = col.copy()
        c[3] = ph(y + ly)
        Pp, Tt = box(cx + lx, y + ly, cz, sx, sy, sz)
        B.add(Pp, Tt[:8], c)
        B.add(*box(cx + lx, y + ly + sy, cz, sx + 0.3, 0.25, sz + 0.3, bottom=False), hexlin('#D5D1C4'))

    P.add(*box(cx, y - 1.2, cz, length, 2.4, 11.0), hexlin('#2A3A55'))
    P.add(*box(cx, y + 1.2, cz, length - 1.0, 0.2, 11.4, bottom=False), hexlin('#B7B2A3'))
    deck(2.0, 1.4, length - 8.0, 3.2, 10.2)
    deck(2.0, 4.85, length - 14.0, 3.0, 8.8)
    deck(0.0, 8.05, length - 28.0, 2.8, 6.6)
    for dx in (-2.0, 6.0):
        P.add(*cylinder(cx + dx, y + 11.0, cz, 1.25, 6.5, 10, 1.0), RED)
        P.add(*cylinder(cx + dx, y + 17.3, cz, 1.0, 1.2, 10, 1.0), hexlin('#16181B'))
    # stern paddle wheel (axis along Z -> wheel disc in the XY plane)
    wx = cx - length / 2 - 3.2
    N = 14
    ring = [(wx + 4.6 * math.cos(2 * math.pi * i / N), y + 1.6 + 4.6 * math.sin(2 * math.pi * i / N)) for i in range(N)]
    for zoff in (-4.6, 4.6):
        for i in range(N):
            a, b = ring[i], ring[(i + 1) % N]
            P.add(*beam([a[0], a[1], cz + zoff], [b[0], b[1], cz + zoff], 0.3), RED)
    for i in range(N):
        a = ring[i]
        P.add(*beam([a[0], a[1], cz - 4.6], [a[0], a[1], cz + 4.6], 0.25), hexlin('#A8362B'))
        P.add(*beam([wx, y + 1.6, cz - 4.6], [a[0], a[1], cz - 4.6], 0.2), hexlin('#7E241D'))
        P.add(*beam([wx, y + 1.6, cz + 4.6], [a[0], a[1], cz + 4.6], 0.2), hexlin('#7E241D'))
    P.add(*box(wx, y + 0.8, cz, 1.2, 1.2, 11.5), DARKSTEEL)
    # lights along the decks
    for k, lx in enumerate(np.linspace(-length / 2 + 4, length / 2 - 4, 14)):
        dot(L, cx + lx, y + 4.7, cz - 5.3, 0.22, hexlin("#FFD9A0"))
        dot(L, cx + lx, y + 4.7, cz + 5.3, 0.22, hexlin("#FFD9A0"))
        if k % 2 == 0:
            C.add_streak(cx + lx, cz + 5.3, y + 4.7, 1.5, hexlin("#FFD9A0")[:3], 0.9)
    for lx in np.linspace(-length / 2 + 14, length / 2 - 14, 8):
        dot(L, cx + lx, y + 8.05, cz - 4.6, 0.2, hexlin('#FFE6B8'))
        dot(L, cx + lx, y + 8.05, cz + 4.6, 0.2, hexlin('#FFE6B8'))


# --------------------------------------------------------------------------- towers
def water_tower(A, cx, cz):
    P, L = A['BR_Props'], A['BR_Lights']
    y0 = hz(cx, cz)
    for sx_ in (-1, 1):
        for sz_ in (-1, 1):
            P.add(*beam([cx + sx_ * 4.2, y0 - 0.3, cz + sz_ * 4.2], [cx + sx_ * 2.8, y0 + 22.0, cz + sz_ * 2.8], 0.55), DARKSTEEL)
    P.add(*cylinder(cx, y0 + 22.0, cz, 5.2, 7.5, 14, 5.2), hexlin('#C9CBC9'))
    P.add(*cone(cx, y0 + 29.5, cz, 5.2, 3.2, 14), hexlin('#C9CBC9'))
    dot(L, cx, y0 + 33.0, cz, 0.45, hexlin('#FF3030'))
    C.mark_circle(cx, cz, 12.0)


def radio_tower(A, cx, cz, h=70.0):
    P, L = A['BR_Props'], A['BR_Lights']
    y0 = hz(cx, cz)
    for sx_ in (-1, 1):
        for sz_ in (-1, 1):
            P.add(*beam([cx + sx_ * 3.2, y0 - 0.5, cz + sz_ * 3.2], [cx + sx_ * 0.35, y0 + h, cz + sz_ * 0.35], 0.35), STEEL)
    for k in range(1, 9):
        t = k / 9.0
        r = 3.2 * (1 - t) + 0.35 * t
        yy = y0 + h * t
        for (a, b) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            P.add(*beam([cx + a[0] * r, yy, cz + a[1] * r], [cx + b[0] * r, yy, cz + b[1] * r], 0.16), STEEL)
    dot(L, cx, y0 + h + 0.8, cz, 0.7, hexlin('#FF2A2A'))
    dot(L, cx, y0 + h * 0.5, cz, 0.45, hexlin('#FF2A2A'))
    C.mark_circle(cx, cz, 10.0)


def fountain(A, rng, cx, cz, r=9.0):
    P, L = A['BR_Props'], A['BR_Lights']
    y0 = hz(cx, cz)
    P.add(*cylinder(cx, y0, cz, r, 0.7, 20, r, cap_top=False), CONCRETE)
    P.add(*cylinder(cx, y0 + 0.62, cz, r - 0.6, 0.06, 20, r - 0.6), hexlin('#4F7F8F'))
    for k in range(7):
        a = 2 * np.pi * k / 7
        h = rng.uniform(3.0, 6.0)
        px, pz = cx + math.cos(a) * 3.8, cz + math.sin(a) * 3.8
        P.add(*cone(px, y0 + 0.65, pz, 0.35, h, 5), hexlin('#D5E4EA'))
    P.add(*cone(cx, y0 + 0.65, cz, 0.55, 9.0, 6), hexlin('#E4F0F4'))
    for k in range(10):
        a = 2 * np.pi * k / 10
        dot(L, cx + math.cos(a) * (r - 0.3), y0 + 0.8, cz + math.sin(a) * (r - 0.3), 0.25, hexlin('#7FD8FF'))


# --------------------------------------------------------------------------- driver
def build_props(A, seed=21):
    rng = np.random.default_rng(seed)
    # wheel + fountain on the two shoreline plazas (east / west), pier + docks on the corridor axis
    zn_e = float(W.banks(172.0)[0])
    ferris_wheel(A, rng, 172.0, zn_e + 27.0)
    C.mark_rect(172.0, zn_e + 27.0, 40.0, 12.0, 4.0, urban=1.0)
    fountain(A, rng, -172.0, float(W.banks(-172.0)[0]) + 29.0)
    pier(A, rng, -30.0)
    pier(A, rng, 36.0, length=40.0, gazebo=False)
    bridge(A, rng, 345.0)
    # boats ------------------------------------------------------------------
    zc = lambda x: float((W.banks(x)[0] + W.banks(x)[1]) / 2.0)
    showboat(A, rng, -58.0, zc(-58.0) + 6.0, y=0.0)
    pontoon(A, -33.0, W.banks(-33.0)[0] - 76.0, 90.0, hexlin('#D8C7A0'))      # moored beside the pier
    pontoon(A, 26.0, zc(26.0) + 42.0, 76.0, hexlin('#2F5F8F'))
    pontoon(A, 96.0, zc(96.0) + 28.0, 112.0, hexlin('#9A3F2F'))
    pontoon(A, -128.0, zc(-128.0) - 18.0, 84.0, hexlin('#D8C7A0'))
    fishing_boat(A, 12.0, zc(12.0) + 70.0, 80.0)
    fishing_boat(A, -92.0, zc(-92.0) + 34.0, 100.0, hexlin('#3B6EA8'))
    fishing_boat(A, 61.0, W.banks(61.0)[0] - 30.0, 60.0, hexlin('#C9C6B8'))
    fishing_boat(A, 210.0, zc(210.0) - 4.0, 94.0, hexlin('#D9D9D6'))
    pontoon(A, 240.0, zc(240.0) + 38.0, 88.0, hexlin('#B9C7C9'))
    # towers on the hills -------------------------------------------------------
    water_tower(A, 210.0, 140.0)
    radio_tower(A, -250.0, 470.0)
    radio_tower(A, 520.0, -760.0, 55.0)
    return A
