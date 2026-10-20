"""City layer of the Branson backdrop: roads, parking lots, cars, lamps, buildings.

All coordinates are Unity world (X east, Z north).  The layout (south -> north at x ~ 0):
    river | shore + boardwalk (a 5..11 m north of the near bank) | berm | boulevard | campus lots | hospital
East of the campus: Branson Landing shops, then downtown.  West: the 76-strip (hotels / theatres).
South bank: "Hollister" -- a Tudor-ish waterfront town.  North / south hills: scattered houses.
"""
import math
import numpy as np
from br_common import (F32, smoothstep, lerp, fbm, vnoise, hexlin, Acc, box, gable_roof, hip_roof, pyramid,
                       cylinder, cone, blob_template, ribbon, polyline_offsets, rot_y, orient_outward, prism_poly)
import br_world as W

FLOOR_H = 3.6

# --------------------------------------------------------------------------- occupancy (for trees)
CELL = 6.0
OCC_N = 384
OCC_ORIGIN = -OCC_N * CELL / 2.0
OCC = np.zeros((OCC_N, OCC_N), dtype=bool)
URBAN = np.zeros((OCC_N, OCC_N), dtype=np.float32)      # building density -> ground tint
HOUSES = []                                             # (x, z) of scattered houses (for yard trees)
STREAKS = []                                            # light sources that reflect in the river: (x, z, h_above_water, width, rgb, intensity)
WARM = np.array([1.0, 0.55, 0.22], dtype=F32)


def add_streak(x, z, h, width, color=None, intensity=0.6):
    STREAKS.append((float(x), float(z), float(h), float(width), WARM if color is None else np.asarray(color, dtype=F32)[:3], float(intensity)))


def reset():
    global OCC, URBAN
    HOUSES.clear()
    STREAKS.clear()
    OCC = np.zeros((OCC_N, OCC_N), dtype=bool)
    URBAN = np.zeros((OCC_N, OCC_N), dtype=np.float32)


def _idx(x, z):
    ix = np.floor((np.asarray(x, dtype=np.float64) - OCC_ORIGIN) / CELL).astype(np.int64)
    iz = np.floor((np.asarray(z, dtype=np.float64) - OCC_ORIGIN) / CELL).astype(np.int64)
    return ix, iz


def mark_circle(x, z, r, urban=0.0):
    r_c = int(math.ceil(r / CELL))
    ix, iz = _idx(x, z)
    ix, iz = int(ix), int(iz)
    for dz in range(-r_c, r_c + 1):
        for dx in range(-r_c, r_c + 1):
            jx, jz = ix + dx, iz + dz
            if 0 <= jx < OCC_N and 0 <= jz < OCC_N and (dx * dx + dz * dz) * CELL * CELL <= (r + CELL) ** 2:
                OCC[jz, jx] = True
                if urban > 0:
                    URBAN[jz, jx] = min(1.0, URBAN[jz, jx] + urban)


def mark_rect(cx, cz, sx, sz, margin=4.0, urban=0.0):
    mark_circle(cx, cz, math.hypot(sx, sz) / 2.0 + margin, urban)


def mark_line(pts_xz, half_width, urban=0.0):
    for p in pts_xz[::2]:
        mark_circle(p[0], p[1], half_width, urban)


def occupied(x, z):
    ix, iz = _idx(x, z)
    ok = (ix >= 0) & (ix < OCC_N) & (iz >= 0) & (iz < OCC_N)
    out = np.zeros(np.shape(ix), dtype=bool)
    out[ok] = OCC[iz[ok], ix[ok]]
    return out


def urban_mask(X, Z):
    """Blurred building density sampled at (X, Z) (bilinear)."""
    k = np.array([1, 2, 3, 2, 1], dtype=np.float32)
    k /= k.sum()
    g = URBAN.copy()
    for _ in range(2):
        g = np.apply_along_axis(lambda r: np.convolve(r, k, mode='same'), 0, g)
        g = np.apply_along_axis(lambda r: np.convolve(r, k, mode='same'), 1, g)
    fx = (np.asarray(X, dtype=np.float64) - OCC_ORIGIN) / CELL - 0.5
    fz = (np.asarray(Z, dtype=np.float64) - OCC_ORIGIN) / CELL - 0.5
    x0 = np.clip(np.floor(fx).astype(np.int64), 0, OCC_N - 2)
    z0 = np.clip(np.floor(fz).astype(np.int64), 0, OCC_N - 2)
    tx = np.clip(fx - x0, 0, 1)
    tz = np.clip(fz - z0, 0, 1)
    v = (g[z0, x0] * (1 - tx) * (1 - tz) + g[z0, x0 + 1] * tx * (1 - tz) +
         g[z0 + 1, x0] * (1 - tx) * tz + g[z0 + 1, x0 + 1] * tx * tz)
    return np.clip(v * 1.6, 0.0, 1.0)


# --------------------------------------------------------------------------- palettes (linear RGBA)
WALLS = [hexlin(h) for h in ('#8B3A2B', '#9A4A33', '#7C3427', '#B39A72', '#CFC6A6', '#8C8E90',
                             '#D8D6CC', '#5B6C80', '#A66B4A', '#6F7F5A', '#C4B28C', '#7D5A44')]
TUDOR = [hexlin(h) for h in ('#CFC6A6', '#D8D6CC', '#C9B98F', '#BFB59A')]
ROOFS = [hexlin(h) for h in ('#3B3B3F', '#7A3B28', '#4C5560', '#3F6B4A', '#262628', '#5B4636')]
SIGNS = [hexlin(h) for h in ('#FF3B30', '#2DA8FF', '#18D2B4', '#FFC21A', '#FF6BD6', '#8DFF3A')]
CARS = [hexlin(h) for h in ('#D9D9D6', '#B4B7BA', '#1B1D20', '#6E1F1F', '#1F3555', '#4B5057', '#8A8D90', '#2F4B3B')]
ASPHALT = hexlin('#34363A')
ASPHALT2 = hexlin('#3C3E43')
LINE_W = hexlin('#C9C6B8')
LINE_Y = hexlin('#C9A83A')
CONCRETE = hexlin('#8D8B84')
WOOD = hexlin('#7A5B3C')
POLE = hexlin('#2B2D30')
GLASS = hexlin('#141C24')
LAMP = hexlin('#FFC070')

_BLOB_P, _BLOB_T = blob_template()


def pick(rng, lst):
    return lst[int(rng.integers(len(lst)))].copy()


def hz(x, z):
    return W.height(np.asarray(x, dtype=np.float64), np.asarray(z, dtype=np.float64))


def road_z(x):
    """Boulevard centreline: hugs the shore just north of the berm, steps north where the shops are."""
    zn, _ = W.banks(x)
    return zn + 24.0 + 22.0 * smoothstep(60.0, 130.0, np.abs(x))


def shore_slope(x):
    zn1, _ = W.banks(np.asarray(x) + 5.0)
    zn0, _ = W.banks(np.asarray(x) - 5.0)
    return (zn1 - zn0) / 10.0


# --------------------------------------------------------------------------- primitives -> accumulators
def rect_pts(cx, cz, sx, sz, yaw):
    P = np.array([[-sx / 2, 0, -sz / 2], [sx / 2, 0, -sz / 2], [sx / 2, 0, sz / 2], [-sx / 2, 0, sz / 2], [0, 0, 0]], dtype=F32)
    return rot_y(P, yaw) + np.array([cx, 0, cz], dtype=F32)


def building(acc, cx, cz, sx, sz, h, yaw, wall, roof_col, roof='flat', rise=0.0, y_ground=None):
    if y_ground is None:
        p = rect_pts(cx, cz, sx, sz, yaw)
        y_ground = float(hz(p[:, 0], p[:, 2]).min())
    y0 = float(y_ground)
    wc = wall.copy()
    wc[3] = (y0 / FLOOR_H) % 1.0
    P, T = box(cx, y0 - 0.8, cz, sx, h + 0.8, sz, yaw)
    acc.add(P, T[:8], wc)
    rc = roof_col.copy()
    rc[3] = 0.0
    top = y0 + h
    if roof == 'flat':
        P, T = box(cx, top, cz, sx + 0.3, 0.5, sz + 0.3, yaw, bottom=False)
        acc.add(P, T, rc)
    elif roof == 'gable':
        P, T = gable_roof(cx, top, cz, sx, sz, rise, 0.4, yaw)
        acc.add(P, T, rc)
    elif roof == 'hip':
        P, T = hip_roof(cx, top, cz, sx, sz, rise, 0.4, yaw)
        acc.add(P, T, rc)
    return y0


def sign_box(acc_lights, rng, cx, cz, sx, sz, yaw, y, face=-1.0, w=None):
    """Emissive shop sign on the face looking along -Z (towards the river) of a yawed building."""
    w = w or rng.uniform(4.0, 8.0)
    col = pick(rng, SIGNS)
    col[3] = 1.0
    local = np.array([[0, 0, face * (sz / 2 + 0.2)]], dtype=F32)
    off = rot_y(local, yaw)[0]
    P, T = box(cx + off[0], y, cz + off[2], w, 0.9, 0.25, yaw)
    acc_lights.add(P, T, col)


def car(acc, cx, y0, cz, yaw, col):
    P, T = box(cx, y0 + 0.28, cz, 1.85, 0.72, 4.5, yaw, bottom=False)
    acc.add(P, T, col)
    cab = rot_y(np.array([[0, 0, -0.1]], dtype=F32), yaw)[0]
    roof = col.copy()
    roof[:3] *= 0.80
    P, T = box(cx + cab[0], y0 + 0.98, cz + cab[2], 1.62, 0.62, 2.4, yaw, bottom=False)
    acc.add(P, T, roof)


def lamp(acc_props, acc_lights, x, y0, z, h=6.5):
    P, T = box(x, y0, z, 0.12, h, 0.12)
    acc_props.add(P, T, POLE)
    s = 0.30
    Pb = _BLOB_P * s + np.array([x, y0 + h + 0.15, z], dtype=F32)
    c = LAMP.copy()
    c[3] = 1.0
    acc_lights.add(Pb, _BLOB_T, c, flat=False)


def road_ribbon(acc, pts_xz, width, color, lift=0.10):
    L, R = polyline_offsets(pts_xz, width / 2.0)

    def up(P2):
        y = hz(P2[:, 0], P2[:, 1]) + lift + 0.0012 * np.hypot(P2[:, 0] - 4.0, P2[:, 1] + 16.0)
        return np.stack([P2[:, 0], y, P2[:, 1]], axis=1)

    P, T = ribbon(up(L), up(R))
    acc.add(P, T, color, flat=False)


def dashes(acc, pts_xz, color, period=14.0, length=5.0, width=0.20, lift=0.16):
    pts = np.asarray(pts_xz, dtype=np.float64)
    seg = np.hypot(*np.diff(pts, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    s = np.arange(2.0, cum[-1] - length, period)
    for s0 in s:
        a = np.interp([s0, s0 + length], cum, pts[:, 0]), np.interp([s0, s0 + length], cum, pts[:, 1])
        p0 = np.array([a[0][0], a[1][0]])
        p1 = np.array([a[0][1], a[1][1]])
        d = p1 - p0
        n = np.array([-d[1], d[0]]) / max(np.hypot(*d), 1e-6) * width / 2
        quad = np.array([p0 + n, p0 - n, p1 - n, p1 + n])
        y = hz(quad[:, 0], quad[:, 1]) + lift + 0.0012 * np.hypot(quad[:, 0] - 4.0, quad[:, 1] + 16.0)
        P = np.stack([quad[:, 0], y, quad[:, 1]], axis=1).astype(F32)
        T = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
        a_, b_, c_ = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
        ny = np.cross(b_ - a_, c_ - a_)[:, 1]
        T[ny < 0] = T[ny < 0][:, [0, 2, 1]]
        acc.add(P, T, color)


def flat_quad(acc, x0, z0, x1, z1, y, color, yaw=0.0):
    P = np.array([[x0, y, z0], [x0, y, z1], [x1, y, z1], [x1, y, z0]], dtype=F32)
    T = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
    acc.add(P, T, color)


def parking_lot(acc_roads, acc_props, rng, x0, z0, x1, z1, aisle_along_x=True, occupancy=0.62):
    """Double-loaded surface lot with painted stalls and parked cars."""
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    y = float(hz(cx, cz)) + 0.10
    flat_quad(acc_roads, x0, z0, x1, z1, y, ASPHALT2)
    stall_w, stall_d = 2.75, 5.4
    yl = y + 0.05
    if aisle_along_x:
        n = int((x1 - x0 - 2) // stall_w)
        xs = x0 + 1 + np.arange(n + 1) * stall_w
        for row_z0 in (z0 + 0.4, z1 - 0.4 - stall_d):
            for xl in xs:
                flat_quad(acc_roads, xl - 0.06, row_z0, xl + 0.06, row_z0 + stall_d, yl, LINE_W)
            for k in range(n):
                if rng.random() < occupancy:
                    car(acc_props, xs[k] + stall_w / 2 + rng.normal(0, 0.12), y, row_z0 + stall_d / 2 + rng.normal(0, 0.2),
                        float(rng.choice([0.0, 180.0])) + rng.normal(0, 1.5), pick(rng, CARS))
    else:
        n = int((z1 - z0 - 2) // stall_w)
        zs_ = z0 + 1 + np.arange(n + 1) * stall_w
        for row_x0 in (x0 + 0.4, x1 - 0.4 - stall_d):
            for zl in zs_:
                flat_quad(acc_roads, row_x0, zl - 0.06, row_x0 + stall_d, zl + 0.06, yl, LINE_W)
            for k in range(n):
                if rng.random() < occupancy:
                    car(acc_props, row_x0 + stall_d / 2 + rng.normal(0, 0.2), y, zs_[k] + stall_w / 2 + rng.normal(0, 0.12),
                        float(rng.choice([90.0, 270.0])) + rng.normal(0, 1.5), pick(rng, CARS))
    mark_rect(cx, cz, x1 - x0, z1 - z0, 2.0, urban=0.9)


# --------------------------------------------------------------------------- campus
def build_campus(A, rng):
    R, P, L = A['BR_Roads'], A['BR_Props'], A['BR_Lights']
    # south lot (in front of the hospital), east + west + north lots, ring road
    parking_lot(R, P, rng, -36.0, -37.5, 46.0, -19.5, True, 0.70)
    parking_lot(R, P, rng, 29.0, -12.0, 55.0, 34.0, False, 0.60)
    parking_lot(R, P, rng, -47.0, -12.0, -21.0, 34.0, False, 0.55)
    parking_lot(R, P, rng, -34.0, 42.0, 48.0, 60.0, True, 0.55)
    # ring road: west leg, north leg, east leg (8 m wide) joined to the boulevard
    ring_w, ring_e, ring_n = -58.0, 66.0, 74.0
    zbw, zbe = float(road_z(ring_w)), float(road_z(ring_e))
    for pts in (np.array([[ring_w, zbw], [ring_w, ring_n]]), np.array([[ring_e, zbe], [ring_e, ring_n]]),
                np.array([[ring_w, ring_n], [ring_e, ring_n]])):
        n = max(2, int(np.hypot(*(pts[1] - pts[0])) / 6.0))
        c = np.stack([np.linspace(pts[0][0], pts[1][0], n), np.linspace(pts[0][1], pts[1][1], n)], axis=1)
        road_ribbon(R, c, 8.0, ASPHALT)
        dashes(R, c, LINE_Y)
        mark_line(c, 6.0, urban=0.7)
    # service stubs from the ring to each lot
    for (xa, za, xb, zb2) in ((-58.0, 6.0, -47.0, 6.0), (66.0, 6.0, 55.0, 6.0), (0.0, 74.0, 0.0, 60.0), (-58.0, -28.0, -36.0, -28.0), (66.0, -28.0, 46.0, -28.0)):
        n = max(2, int(math.hypot(xb - xa, zb2 - za) / 6.0))
        c = np.stack([np.linspace(xa, xb, n), np.linspace(za, zb2, n)], axis=1)
        road_ribbon(R, c, 7.0, ASPHALT)
    # apron / sidewalk strip along the south face of the hospital
    flat_quad(R, -16.0, -19.6, 25.0, -16.3, float(hz(4.0, -18.0)) + 0.08, CONCRETE)
    # lamps around the lots
    for x in (-34.0, -23.0, 25.0, 38.0):          # keep the middle of the lot clear: it is right in the window view
        lamp(P, L, x, float(hz(x, -28.5)) + 0.1, -28.5, 7.0)
    for z in np.arange(-6.0, 34.0, 20.0):
        lamp(P, L, 42.0, float(hz(42.0, z)) + 0.1, z, 7.0)
        lamp(P, L, -34.0, float(hz(-34.0, z)) + 0.1, z, 7.0)
    # tiny helipad north of the building (ground marking only)
    mark_rect(10.0, 52.0, 34.0, 22.0, 6.0, urban=0.0)


# --------------------------------------------------------------------------- boulevard, boardwalk, highway
def build_streets(A, rng):
    R, P, L = A['BR_Roads'], A['BR_Props'], A['BR_Lights']
    xs = np.arange(-720.0, 720.1, 6.0)
    c = np.stack([xs, road_z(xs)], axis=1)
    road_ribbon(R, c, 9.0, ASPHALT)
    dashes(R, c, LINE_Y)
    mark_line(c, 9.0, urban=0.55)
    # boardwalk (wood) 5 m wide along the near bank, a = 5.5..10.5
    zn, _ = W.banks(xs)
    bw = np.stack([xs, zn + 8.0], axis=1)
    road_ribbon(R, bw, 5.0, WOOD, lift=0.07)
    mark_line(bw, 7.0, urban=0.35)
    # lamps along the boardwalk (every 20 m) and the boulevard (every 30 m)
    for x in np.arange(-700.0, 700.0, 20.0):
        zb = float(W.banks(float(x))[0]) + 10.2
        lamp(P, L, x, float(hz(x, zb)) + 0.06, zb, 4.6)
    for x in np.arange(-700.0, 700.0, 30.0):
        if abs(x) < 40.0:
            continue
        zb = float(road_z(x)) - 5.4
        lamp(P, L, x, float(hz(x, zb)) + 0.06, zb, 6.2)
    # highway behind the city (z = +96), 12 m
    hx = np.arange(-720.0, 720.1, 8.0)
    hw = np.stack([hx, np.full_like(hx, 96.0)], axis=1)
    road_ribbon(R, hw, 12.0, ASPHALT)
    dashes(R, hw, LINE_W, 18.0, 6.0)
    mark_line(hw, 10.0, urban=0.3)
    # north-south streets: downtown (east) and strip (west)
    for xs_ in (150.0, 230.0, 310.0, 390.0, 470.0, 550.0, 630.0, -150.0, -235.0, -320.0, -405.0, -490.0, -575.0, -655.0):
        z0 = float(road_z(xs_))
        zz = np.arange(z0, 96.1, 6.0)
        c = np.stack([np.full_like(zz, xs_), zz], axis=1)
        road_ribbon(R, c, 7.0, ASPHALT)
        mark_line(c, 7.0, urban=0.45)
    # Hollister: waterfront street + a second street, both following the far bank
    for off, w in ((38.0, 8.0), (86.0, 7.0)):
        xs2 = np.arange(-700.0, 700.1, 6.0)
        zs_far = W.banks(xs2)[1]
        c = np.stack([xs2, zs_far - off], axis=1)
        road_ribbon(R, c, w, ASPHALT)
        mark_line(c, 7.0, urban=0.45)


# --------------------------------------------------------------------------- shops, downtown, strip, hollister
def _flat_ok(cx, cz, sx, sz, yaw, max_dy=2.5):
    p = rect_pts(cx, cz, sx, sz, yaw)
    h = hz(p[:, 0], p[:, 2])
    return float(h.max() - h.min()) < max_dy


def build_landing(A, rng):
    """Two-/three-storey brick shop rows along the shore east and west of the campus."""
    B, P, L = A['BR_Buildings'], A['BR_Props'], A['BR_Lights']
    for side in (1, -1):
        x = side * 76.0
        while abs(x) < 660.0:
            w = rng.uniform(15, 28)
            gap = rng.uniform(3.5, 9.0)
            xc = x + side * w / 2
            # leave plazas for the wheel (east) and fountain (west)
            if 150.0 < abs(xc) < 196.0:
                x += side * 46.0
                continue
            zn = float(W.banks(xc)[0])
            dep = rng.uniform(18, 24)
            yaw = -math.degrees(math.atan(float(shore_slope(xc))))
            zc = zn + 21.0 + dep / 2
            h = float(rng.choice([8.5, 10.0, 11.5, 13.0, 15.0]))
            roof = 'gable' if rng.random() < 0.35 else 'flat'
            wall = pick(rng, WALLS)
            y0 = building(B, xc, zc, w, dep, h, yaw, wall, pick(rng, ROOFS), roof, rise=3.4)
            mark_rect(xc, zc, w, dep, 6.0, urban=1.0)
            if rng.random() < 0.65:
                sign_box(L, rng, xc, zc, w, dep, yaw, y0 + 3.6)
            x += side * (w + gap)


def _street_clear(cx, hw, streets):
    return all(abs(cx - s) > hw + 5.0 for s in streets)


def build_downtown(A, rng):
    B, L = A['BR_Buildings'], A['BR_Lights']
    streets = [150.0, 230.0, 310.0, 390.0, 470.0, 550.0, 630.0]
    for cx in np.arange(130.0, 690.0, 26.0):
        for cz0 in np.arange(float(road_z(cx)) + 14.0, 88.0, 26.0):
            fall = 1.0 - smoothstep(450.0, 690.0, cx)
            if rng.random() > 0.78 * fall + 0.12:
                continue
            sx, sz = rng.uniform(13, 21), rng.uniform(13, 21)
            jx, jz = rng.uniform(-3, 3), rng.uniform(-3, 3)
            bx, bz = cx + jx, cz0 + jz
            if not _street_clear(bx, sx / 2, streets) or bz + sz / 2 > 90.0:
                continue
            core = np.exp(-((bx - 290.0) / 150.0) ** 2)
            h = float(rng.choice([6.5, 7.5, 9.0, 10.5, 12.0, 14.0])) + (rng.uniform(0, 14) if rng.random() < 0.28 * core else 0.0)
            roof = 'gable' if (h < 10.5 and rng.random() < 0.45) else 'flat'
            if not _flat_ok(bx, bz, sx, sz, 0.0):
                continue
            building(B, bx, bz, sx, sz, h, 0.0, pick(rng, WALLS), pick(rng, ROOFS), roof, rise=3.0)
            mark_rect(bx, bz, sx, sz, 5.0, urban=1.0)
    # a taller hotel cluster
    for (bx, bz, h) in ((262.0, 40.0, 33.0), (330.0, 62.0, 27.0), (372.0, 22.0, 24.0)):
        building(B, bx, bz, 24.0, 20.0, h, 0.0, hexlin('#9A8F7C'), ROOFS[0], 'flat')
        mark_rect(bx, bz, 24, 20, 6.0, urban=1.0)


def build_strip(A, rng):
    """West: big hotels, theatres and parking along the old 76-strip."""
    B, R, P, L = A['BR_Buildings'], A['BR_Roads'], A['BR_Props'], A['BR_Lights']
    streets = [-150.0, -235.0, -320.0, -405.0, -490.0, -575.0, -655.0]
    for cx in np.arange(-130.0, -700.0, -34.0):
        for cz0 in np.arange(float(road_z(cx)) + 16.0, 88.0, 34.0):
            fall = 1.0 - smoothstep(460.0, 700.0, -cx)
            if rng.random() > 0.72 * fall + 0.10:
                continue
            sx, sz = rng.uniform(20, 46), rng.uniform(16, 32)
            bx, bz = cx + rng.uniform(-4, 4), cz0 + rng.uniform(-4, 4)
            if not _street_clear(bx, sx / 2, streets) or bz + sz / 2 > 90.0:
                continue
            if not _flat_ok(bx, bz, sx, sz, 0.0):
                continue
            kind = rng.random()
            if kind < 0.28:      # hotel tower
                h = float(rng.uniform(18, 36))
                wall = pick(rng, WALLS)
            elif kind < 0.62:    # theatre box with a bright marquee
                h = float(rng.uniform(9, 14))
                wall = pick(rng, [hexlin('#6B4F8A'), hexlin('#2F6F8F'), hexlin('#9A3F4F'), hexlin('#B08A3E')])
            else:                # retail
                h = float(rng.uniform(6, 10))
                wall = pick(rng, WALLS)
            y0 = building(B, bx, bz, sx, sz, h, 0.0, wall, pick(rng, ROOFS), 'flat')
            mark_rect(bx, bz, sx, sz, 6.0, urban=1.0)
            if rng.random() < 0.7:
                sign_box(L, rng, bx, bz, sx, sz, 0.0, y0 + min(h - 2.0, 5.0), w=rng.uniform(8, 16))
    # Titanic-museum-style ship facade (landmark in the west window)
    tx, tz = -410.0, -6.0
    y = float(hz(tx, tz))
    hull = hexlin('#1B2430')
    deck = hexlin('#D9D3C0')
    P_, T_ = box(tx, y, tz, 12.0, 8.0, 58.0)
    B.add(P_, T_[:8], np.array([*hull[:3], 0.0], dtype=F32))
    B.add(*box(tx, y + 8.0, tz, 12.4, 0.5, 58.4, bottom=False), hull)
    P_, T_ = box(tx, y + 8.5, tz + 2.0, 9.5, 4.5, 40.0)
    B.add(P_, T_[:8], np.array([*deck[:3], ((y + 8.5) / FLOOR_H) % 1.0], dtype=F32))
    B.add(*box(tx, y + 13.0, tz + 2.0, 9.9, 0.4, 40.4, bottom=False), hexlin('#7A7567'))
    P_, T_ = prism_poly([(tx - 6.0, tz - 29.0), (tx + 6.0, tz - 29.0), (tx, tz - 38.0)], y, 8.0)   # bow, pointing south
    B.add(P_, T_, np.array([*hull[:3], 0.0], dtype=F32))
    for k in range(4):
        zf = tz + 10.0 - k * 7.0
        R_ = A['BR_Props']
        R_.add(*cylinder(tx, y + 13.4, zf, 1.5, 6.5, 10, 1.3), hexlin('#C9964F'))
        R_.add(*cylinder(tx, y + 19.2, zf, 1.32, 1.3, 10, 1.3), hexlin('#16181B'))
    # the iceberg out front
    for (dx, dz, s) in ((-9.0, -38.0, 7.0), (-14.0, -33.0, 5.0), (-5.0, -43.0, 4.5)):
        A['BR_Props'].add(*pyramid(tx + dx, y, tz + dz, s * 1.6, s * 1.3, s * 1.1, 20.0 * dx), hexlin('#BFD6E6'))
    mark_rect(tx, tz, 30, 90, 8.0, urban=1.0)


def build_hollister(A, rng):
    """South bank: Tudor-ish waterfront town, church steeple, marina docks."""
    B, R, P, L = A['BR_Buildings'], A['BR_Roads'], A['BR_Props'], A['BR_Lights']
    x = -690.0
    while x < 690.0:
        w = rng.uniform(11, 22)
        xc = x + w / 2
        zs_f = float(W.banks(xc)[1])
        for row, (a0, dep) in enumerate(((46.0, 17.0), (94.0, 15.0))):
            if rng.random() < (0.10 if row == 0 else 0.30):
                continue
            slope = (float(W.banks(xc + 5.0)[1]) - float(W.banks(xc - 5.0)[1])) / 10.0
            yaw = -math.degrees(math.atan(slope))
            zc = zs_f - a0 - dep / 2
            h = float(rng.choice([6.0, 7.5, 9.0, 10.5]))
            if not _flat_ok(xc, zc, w, dep, yaw):
                continue
            tud = pick(rng, TUDOR)
            y0 = building(B, xc, zc, w, dep, h, yaw, tud, hexlin('#3A2F2A') if rng.random() < 0.7 else pick(rng, ROOFS),
                          'gable', rise=rng.uniform(3.0, 4.6))
            mark_rect(xc, zc, w, dep, 5.0, urban=1.0)
            if row == 0 and rng.random() < 0.45:
                sign_box(L, rng, xc, zc, w, dep, yaw, y0 + 3.2, face=+1.0, w=rng.uniform(3.5, 6.0))
            if row == 0:
                add_streak(xc, zc + dep / 2, y0 + h * 0.5, w, None, 0.50)
        x += w + rng.uniform(2.5, 8.0)
    # church with steeple
    cx = -60.0
    zs_f = float(W.banks(cx)[1])
    cz = zs_f - 62.0
    building(B, cx, cz, 14.0, 26.0, 8.0, 0.0, hexlin('#C8C1AE'), hexlin('#3A2F2A'), 'gable', rise=5.0)
    P.add(*box(cx, float(hz(cx, cz - 15)) - 0.5, cz - 15.0, 5.0, 22.0, 5.0), hexlin('#C8C1AE'))
    P.add(*pyramid(cx, float(hz(cx, cz - 15)) + 21.5, cz - 15.0, 5.6, 5.6, 9.0), hexlin('#2C2B30'))
    # marina docks (floating piers) with moored boats
    for dx in (118.0, 150.0, 182.0):
        zs_f = float(W.banks(dx)[1])
        y = W.WATER_Y + 0.35
        P.add(*box(dx, y, zs_f + 17.0, 2.0, 0.3, 36.0), WOOD)
        for k in range(4):
            side = 1 if k % 2 == 0 else -1
            bz = zs_f + 6.0 + k * 9.0
            P.add(*box(dx + side * 3.4, y, bz, 2.2, 0.8, 6.0), hexlin('#D9D9D6') if k % 3 else hexlin('#3A5F8F'))
    # promenade lamps along the far shore (they reflect in the river as glittering streaks)
    for x in np.arange(-700.0, 700.0, 22.0):
        zl = float(W.banks(float(x))[1]) - 12.0
        yl = float(hz(x, zl)) + 0.06
        lamp(P, L, x, yl, zl, 4.5)
        add_streak(x, zl, yl + 4.7, 1.4, LAMP[:3], 0.95)


def build_houses(A, rng):
    """Scattered houses on the gentle slopes at the edge of the valley, north and south."""
    B, L = A['BR_Buildings'], A['BR_Lights']
    xs = np.arange(-700.0, 700.1, 36.0)
    count = 0
    for sector, (z_lo, z_hi) in (('north', (112.0, 560.0)), ('south', (-1000.0, -470.0))):
        for z in np.arange(z_lo, z_hi, 36.0):
            for x in xs:
                bx, bz = x + rng.uniform(-12, 12), z + rng.uniform(-12, 12)
                if abs(bx) > 690:
                    continue
                zn, zs = W.banks(np.array([bx]))
                d = float(W._valley_distance(np.array([bx]), np.array([bz]), zs)[0])
                if d < 6.0 or d > 420.0:
                    continue
                if fbm(np.array([bx / 170.0]), np.array([bz / 170.0]), 3, seed=64)[0] < 0.36:
                    continue
                yaw = rng.uniform(0, 360)
                sx, sz = rng.uniform(8, 12), rng.uniform(6.5, 9.5)
                if not _flat_ok(bx, bz, sx, sz, yaw, 3.6):
                    continue
                if occupied(np.array([bx]), np.array([bz]))[0]:
                    continue
                if float(W.height(np.float64(bx), np.float64(bz))) < 1.2:       # keep houses out of the river
                    continue
                wall = pick(rng, [hexlin('#CFC6A6'), hexlin('#B7A98B'), hexlin('#8C8E90'), hexlin('#A66B4A'), hexlin('#D8D6CC'), hexlin('#6F7F5A')])
                building(B, bx, bz, sx, sz, rng.uniform(4.2, 6.2), yaw, wall, pick(rng, ROOFS), 'gable', rise=rng.uniform(2.0, 3.0))
                mark_rect(bx, bz, sx, sz, 7.0, urban=0.5)
                HOUSES.append((bx, bz))
                count += 1
    return count


# --------------------------------------------------------------------------- driver
def build_city(seed=7):
    rng = np.random.default_rng(seed)
    reset()
    A = {k: Acc(k) for k in ('BR_Buildings', 'BR_Roads', 'BR_Props', 'BR_Lights')}
    build_streets(A, rng)
    build_campus(A, rng)
    build_landing(A, rng)
    build_downtown(A, rng)
    build_strip(A, rng)
    build_hollister(A, rng)
    nh = build_houses(A, rng)
    return A, dict(houses=nh)
