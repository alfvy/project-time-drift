"""Trees for the Branson backdrop: Ozark oak/hickory woodland in autumn colours, cedars, street and park trees.

Trees are instanced low-poly blobs (smooth shaded), merged per spatial tile so Unity can frustum-cull them.
Nothing taller than a few metres is placed in the *view corridor* in front of the hospital's south windows.
"""
import math
import numpy as np
from br_common import (F32, smoothstep, fbm, vnoise, hexlin, Acc, blob_template, cone, cylinder)
import br_world as W
import br_terrain as TR
import br_city as C

TILE = 520.0
CEDAR = hexlin('#1F3A22')
CEDAR2 = hexlin('#2B4A2A')
TRUNK = hexlin('#4A3A2A')
PARKGREEN = [hexlin(h) for h in ('#4F6B2A', '#6E7B38', '#8A7B2E', '#9B5A24', '#3F5E2B')]


def _blob(seg):
    P, T = blob_template(seg=seg, squash=1.0)
    y0, y1 = P[:, 1].min(), P[:, 1].max()
    P = P.copy()
    P[:, 1] = (P[:, 1] - y0) / (y1 - y0)
    P[:, 0] /= 0.92
    P[:, 2] /= 0.92
    return P.astype(F32), T, (0.60 + 0.40 * P[:, 1]).astype(F32)


def _trunk():
    P, T = cylinder(0.0, 0.0, 0.0, 1.0, 1.0, n=5, r_top=0.62, cap_top=False)
    return P, T, np.full(len(P), 0.55, dtype=F32)


def _cedar():
    P1, T1 = cone(0.0, 0.0, 0.0, 1.0, 0.70, n=6)
    P2, T2 = cone(0.0, 0.34, 0.0, 0.66, 0.66, n=6)
    P = np.vstack([P1, P2]).astype(F32)
    T = np.vstack([T1, T2 + len(P1)]).astype(np.int32)
    return P, T, (0.55 + 0.45 * np.clip(P[:, 1], 0, 1)).astype(F32)


BLOB6, BLOB4, TRUNK_T, CEDAR_T = _blob(6), _blob(4), _trunk(), _cedar()


def instances(tpl, pos, sx, sy, rot, colors):
    P0, T0, sh0 = tpl
    n, m = len(pos), len(P0)
    a = np.radians(rot)[:, None]
    x0 = P0[None, :, 0] * sx[:, None]
    z0 = P0[None, :, 2] * sx[:, None]
    X = x0 * np.cos(a) + z0 * np.sin(a) + pos[:, 0:1]
    Z = -x0 * np.sin(a) + z0 * np.cos(a) + pos[:, 2:3]
    Y = P0[None, :, 1] * sy[:, None] + pos[:, 1:2]
    P = np.stack([X, Y, Z], axis=2).reshape(-1, 3).astype(F32)
    col = colors[:, None, :3] * sh0[None, :, None]
    Cc = np.concatenate([col, np.zeros((n, m, 1))], axis=2).reshape(-1, 4).astype(F32)
    T = (T0[None, :, :] + (np.arange(n) * m)[:, None, None]).reshape(-1, 3).astype(np.int32)
    return P, T, Cc


def in_corridor(x, z):
    """Region in front of the south windows where nothing tall may stand (keeps the river visible)."""
    x = np.asarray(x)
    z = np.asarray(z)
    return (x > -115.0) & (x < 125.0) & (z > -100.0) & (z < 14.0)


class TreeSet:
    def __init__(self):
        self.tiles = {}

    def _acc(self, x, z):
        ix = int(np.floor((x + 1100.0) / TILE))
        iz = int(np.floor((z + 1100.0) / TILE))
        key = (ix, iz)
        if key not in self.tiles:
            self.tiles[key] = Acc("BR_Trees_%d_%d" % key)
        return self.tiles[key]

    def add(self, tpl, pos, sx, sy, rot, colors):
        if len(pos) == 0:
            return
        ix = np.floor((pos[:, 0] + 1100.0) / TILE).astype(int)
        iz = np.floor((pos[:, 2] + 1100.0) / TILE).astype(int)
        key = ix * 100 + iz
        for k in np.unique(key):
            m = key == k
            P, T, Cc = instances(tpl, pos[m], sx[m], sy[m], rot[m], colors[m])
            self._acc(pos[m][0, 0], pos[m][0, 2]).add(P, T, Cc, flat=False)

    def count(self):
        return sum(a.tri_count() for a in self.tiles.values())


def _ground(x, z, sink=0.35):
    return np.stack([x, W.height(x, z) - sink, z], axis=1)


def add_trees(ts, rng, x, z, height, radius, colors, kind='oak', near=True):
    """Add trees of one kind: oak = trunk + 1-2 blobs, cedar = stacked cones."""
    n = len(x)
    if n == 0:
        return
    pos = _ground(x, z)
    rot = rng.uniform(0, 360, n)
    if kind == 'cedar':
        ts.add(CEDAR_T, pos, radius * 1.0, height, rot, colors)
        return
    if near:
        th = height * 0.45
        ts.add(TRUNK_T, pos, np.maximum(radius * 0.09, 0.12), th, rot, np.tile(TRUNK[:3], (n, 1)))
        main = pos.copy()
        main[:, 1] += th * 0.55
        ts.add(BLOB6, main, radius, height * 0.78, rot, colors)
        sub = main.copy()
        ang = np.radians(rng.uniform(0, 360, n))
        sub[:, 0] += np.cos(ang) * radius * 0.45
        sub[:, 2] += np.sin(ang) * radius * 0.45
        sub[:, 1] += height * 0.16
        ts.add(BLOB6, sub, radius * 0.68, height * 0.62, rot + 40, colors * 0.94)
    else:
        main = pos.copy()
        main[:, 1] += height * 0.18
        ts.add(BLOB4, main, radius * 1.05, height * 0.95, rot, colors)


def scatter_forest(ts, rng):
    total = 0
    for (r0, r1, step, near) in ((0.0, 380.0, 9.0, True), (380.0, 1060.0, 17.0, False)):
        g = np.arange(-r1, r1 + 1e-6, step)
        gx, gz = np.meshgrid(g, g)
        gx = gx.ravel() + rng.uniform(-step / 2, step / 2, gx.size)
        gz = gz.ravel() + rng.uniform(-step / 2, step / 2, gz.size)
        r = np.hypot(gx - 4.0, gz)
        m = (r >= r0) & (r < r1) & (np.abs(gx) < 1100) & (np.abs(gz) < 1100)
        x, z, r = gx[m], gz[m], r[m]
        zn, zs = W.banks(x)
        d = W._valley_distance(x, z, zs)
        f = TR.forest_amount(x, z, d)
        keep = rng.random(len(x)) < np.clip(f * 1.05, 0, 1) ** 0.7
        keep &= ~C.occupied(x, z)
        keep &= ~in_corridor(x, z)
        keep &= W.height(x, z) > 1.0
        x, z, r = x[keep], z[keep], r[keep]
        n = len(x)
        far = 1.0 + 0.5 * smoothstep(300.0, 1000.0, r)
        height = rng.uniform(9.0, 16.0, n) * far
        radius = height * rng.uniform(0.30, 0.40, n)
        col = TR.canopy_color(x, z) * rng.uniform(0.82, 1.16, (n, 1))
        ced = rng.random(n) < 0.17
        add_trees(ts, rng, x[~ced], z[~ced], height[~ced], radius[~ced], col[~ced], 'oak', near)
        cc = np.tile(CEDAR[:3], (ced.sum(), 1)) * rng.uniform(0.8, 1.2, (ced.sum(), 1))
        add_trees(ts, rng, x[ced], z[ced], height[ced] * 0.85, radius[ced] * 0.62, cc, 'cedar', near)
        total += n
    return total


def streets_and_parks(ts, rng):
    n_total = 0
    # boulevard verge trees (north side) east and west of the campus
    xs = np.concatenate([np.arange(80.0, 660.0, 22.0), np.arange(-80.0, -660.0, -22.0)])
    xs = xs + rng.uniform(-3, 3, len(xs))
    zs_ = C.road_z(xs) + 7.5
    h = rng.uniform(5.0, 7.0, len(xs))
    keep = ~C.occupied(xs, zs_) | (rng.random(len(xs)) < 0.1)
    xs, zs_, h = xs[keep], zs_[keep], h[keep]
    col = np.array([PARKGREEN[i % len(PARKGREEN)][:3] for i in rng.integers(0, 5, len(xs))])
    add_trees(ts, rng, xs, zs_, h, h * 0.40, col * rng.uniform(0.85, 1.1, (len(xs), 1)), 'oak', True)
    n_total += len(xs)
    # trees along the north-south streets
    px, pz = [], []
    for sx_ in (150.0, 230.0, 310.0, 390.0, 470.0, 550.0, 630.0, -150.0, -235.0, -320.0, -405.0, -490.0, -575.0, -655.0):
        z0 = float(C.road_z(sx_)) + 12.0
        for z in np.arange(z0, 92.0, 17.0):
            for side in (-1, 1):
                px.append(sx_ + side * 6.4 + rng.uniform(-0.8, 0.8))
                pz.append(z + rng.uniform(-2, 2))
    px, pz = np.array(px), np.array(pz)
    keep = ~C.occupied(px, pz) | (rng.random(len(px)) < 0.25)
    px, pz = px[keep], pz[keep]
    h = rng.uniform(5.0, 7.5, len(px))
    col = np.array([PARKGREEN[i][:3] for i in rng.integers(0, 5, len(px))])
    add_trees(ts, rng, px, pz, h, h * 0.38, col, 'oak', True)
    n_total += len(px)
    # campus ornamentals: low (<= 4.5 m, below the windows' eye level), never in the south corridor
    cx_ = []
    cz_ = []
    for z in np.arange(-8.0, 72.0, 13.0):
        cx_ += [-53.0, 61.0]
        cz_ += [z, z]
    for x in np.arange(-30.0, 48.0, 14.0):
        cx_.append(x)
        cz_.append(66.0)
    cx_, cz_ = np.array(cx_), np.array(cz_)
    h = rng.uniform(3.2, 4.4, len(cx_))
    col = np.array([PARKGREEN[i][:3] for i in rng.integers(0, 5, len(cx_))])
    add_trees(ts, rng, cx_ + rng.uniform(-1, 1, len(cx_)), cz_ + rng.uniform(-1, 1, len(cz_)), h, h * 0.42, col, 'oak', True)
    n_total += len(cx_)
    # plazas east (wheel) and west (fountain): a few shade trees
    for cx0 in (172.0, -172.0):
        zc = float(W.banks(cx0)[0]) + 30.0
        k = 9
        a = rng.uniform(0, 2 * np.pi, k)
        r_ = rng.uniform(10, 22, k)
        x = cx0 + np.cos(a) * r_
        z = zc + np.sin(a) * r_ * 0.6
        h = rng.uniform(6.0, 9.0, k)
        col = np.array([PARKGREEN[i][:3] for i in rng.integers(0, 5, k)])
        add_trees(ts, rng, x, z, h, h * 0.40, col, 'oak', True)
        n_total += k
    # house yards
    if C.HOUSES:
        hs = np.array(C.HOUSES)
        k = len(hs) * 2
        idx = np.repeat(np.arange(len(hs)), 2)
        a = rng.uniform(0, 2 * np.pi, k)
        r_ = rng.uniform(8.0, 16.0, k)
        x, z = hs[idx, 0] + np.cos(a) * r_, hs[idx, 1] + np.sin(a) * r_
        keep = ~C.occupied(x, z) | (rng.random(k) < 0.3)
        x, z = x[keep], z[keep]
        h = rng.uniform(5.5, 9.5, len(x))
        col = TR.canopy_color(x, z) * rng.uniform(0.9, 1.15, (len(x), 1))
        add_trees(ts, rng, x, z, h, h * 0.38, col, 'oak', True)
        n_total += len(x)
    return n_total


def riverside(ts, rng):
    """Trees along the far (south) shore, on the islands, and a few clumps behind the marina."""
    n_total = 0
    xs = np.arange(-700.0, 700.0, 9.5) + rng.uniform(-3, 3, 148)
    zs_far = W.banks(xs)[1]
    off = rng.uniform(7.0, 30.0, len(xs))
    z = zs_far - off
    keep = (rng.random(len(xs)) < 0.62) & ~((xs > 105) & (xs < 200)) & ~C.occupied(xs, z) | (rng.random(len(xs)) < 0.06)
    xs, z, off = xs[keep], z[keep], off[keep]
    h = rng.uniform(8.0, 14.5, len(xs))
    col = TR.canopy_color(xs, z) * rng.uniform(0.85, 1.2, (len(xs), 1))
    add_trees(ts, rng, xs, z, h, h * 0.38, col, 'oak', False)
    n_total += len(xs)
    for (cx, cz, rx, rz, tilt, crest) in W.ISLANDS:
        k = int(rx / 5.0)
        a = rng.uniform(0, 2 * np.pi, k * 3)
        r_ = np.sqrt(rng.uniform(0, 1, k * 3)) * 0.36
        x = cx + np.cos(a) * r_ * rx
        z = cz + tilt * (x - cx) + np.sin(a) * r_ * rz
        ok = W.height(x, z) > 0.5
        x, z = x[ok][:k], z[ok][:k]
        h = rng.uniform(6.5, 11.5, len(x))
        col = TR.canopy_color(x, z) * rng.uniform(0.85, 1.2, (len(x), 1))
        add_trees(ts, rng, x, z, h, h * 0.40, col, 'oak', True)
        n_total += len(x)
    return n_total


def build_trees(seed=11):
    rng = np.random.default_rng(seed)
    ts = TreeSet()
    n = {}
    n['forest'] = scatter_forest(ts, rng)
    n['streets/parks'] = streets_and_parks(ts, rng)
    n['riverside'] = riverside(ts, rng)
    return ts, n
