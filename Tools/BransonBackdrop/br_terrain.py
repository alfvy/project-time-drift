"""Terrain + river-surface meshes for the Branson backdrop."""
import numpy as np
from br_common import (F32, smoothstep, lerp, fbm, vnoise, hexlin, Acc)
import br_world as W

PAL = dict(
    lawn_a=hexlin('#56682D'), lawn_b=hexlin('#6E7B38'), dry=hexlin('#7C7A43'),
    shore=hexlin('#8F8A76'), riprap=hexlin('#69665A'), bed=hexlin('#2C3A36'),
    forest_dark=hexlin('#2A4426'), forest_olive=hexlin('#56672A'),
    rust=hexlin('#8F3B1B'), orange=hexlin('#B2641F'), gold=hexlin('#C79B2C'), brown=hexlin('#5C4326'),
    rock=hexlin('#7A7468'), urban_a=hexlin('#6E6C64'), urban_b=hexlin('#7A766B'),
)

# optional hook set by the build script:  callable (X, Z) -> 0..1 urban density, tints the ground under towns
URBAN_FN = None


def graded_axis(lo, hi, d_lo, d_hi, step, growth):
    dense = np.arange(d_lo, d_hi + 1e-6, step)
    right, s = [d_hi], step
    while right[-1] < hi:
        s *= growth
        right.append(right[-1] + s)
    left, s = [d_lo], step
    while left[-1] > lo:
        s *= growth
        left.append(left[-1] - s)
    return np.concatenate([np.array(left[:0:-1]), dense, np.array(right[1:])])


def make_grid():
    xs = graded_axis(-1150.0, 1150.0, -300.0, 300.0, 3.0, 1.045)
    zs = graded_axis(-1150.0, 1150.0, -350.0, 130.0, 3.0, 1.05)
    return xs, zs


def canopy_color(X, Z):
    """Autumn Ozark canopy colour (linear RGB, Nx3): shared by the terrain carpet and single trees."""
    X = np.asarray(X, dtype=np.float64)
    Z = np.asarray(Z, dtype=np.float64)
    big = fbm(X / 300.0 + 4, Z / 300.0 - 2, 3, seed=31)
    s = (smoothstep(0.36, 0.70, big) * 0.88)[:, None]
    t1 = fbm(X / 90.0, Z / 90.0, 3, seed=33)[:, None]
    green = PAL['forest_dark'] * (1 - t1) + PAL['forest_olive'] * t1
    t2 = fbm(X / 75.0 + 3, Z / 75.0 + 1, 3, seed=35)[:, None]
    warm = PAL['rust'] * (1 - t2) + PAL['orange'] * t2
    gold = (smoothstep(0.60, 0.82, fbm(X / 48.0 - 5, Z / 48.0 + 8, 3, seed=37)) * 0.75)[:, None]
    warm = lerp(warm, PAL['gold'], gold)
    brown = (smoothstep(0.66, 0.85, fbm(X / 40.0 + 2, Z / 40.0 - 6, 3, seed=39)) * 0.6)[:, None]
    warm = lerp(warm, PAL['brown'], brown)
    return lerp(green, warm, s)[:, :3]


def forest_amount(X, Z, d):
    """0..1 woodland cover from distance out of the valley (d) and clearing noise."""
    meadow = smoothstep(0.62, 0.80, fbm(np.asarray(X) / 170.0 + 20, np.asarray(Z) / 170.0, 3, seed=52))
    return smoothstep(10.0, 170.0, d) * (1.0 - 0.85 * meadow * (1.0 - smoothstep(260.0, 560.0, d)))


def terrain_colors(X, Z, H, slope):
    """Linear RGBA per vertex.  Alpha = canopy mask (drives the procedural canopy texture)."""
    inside, zn, zs = W.river_mask_info(X, Z)
    d = W._valley_distance(X, Z, zs)

    t = fbm(X / 55.0, Z / 55.0, 3, seed=5)[:, None]
    lawn = PAL['lawn_a'] * (1 - t) + PAL['lawn_b'] * t
    dry = smoothstep(0.55, 0.8, fbm(X / 140.0 + 9, Z / 140.0 - 3, 3, seed=8))[:, None] * 0.6
    lawn = lerp(lawn, PAL['dry'], dry)

    canopy = np.concatenate([canopy_color(X, Z), np.ones((len(X), 1), dtype=F32)], axis=1)
    forest = forest_amount(X, Z, d)
    col = lerp(lawn, canopy, forest[:, None])

    rock = smoothstep(0.80, 1.35, slope) * smoothstep(40.0, 130.0, d)
    col = lerp(col, PAL['rock'], (rock * 0.75)[:, None])
    alpha = forest * (1.0 - rock)

    # towns tint the ground grey-brown
    if URBAN_FN is not None:
        um = URBAN_FN(X, Z)
        tu = fbm(X / 30.0, Z / 30.0, 2, seed=77)[:, None]
        urban = PAL['urban_a'] * (1 - tu) + PAL['urban_b'] * tu
        col = lerp(col, urban, (um * 0.85)[:, None])
        alpha = alpha * (1.0 - um)

    # shoreline: gravel / riprap strip along both banks, dark bed under water
    dl = -inside                                    # metres outside the channel (>0 on land)
    shore = (1.0 - smoothstep(0.0, 11.0, dl)) * (dl > -0.5)
    rip = smoothstep(0.45, 0.7, vnoise(X / 9.0, Z / 9.0, 71))[:, None]
    shore_col = PAL['shore'] * (1 - rip) + PAL['riprap'] * rip
    col = lerp(col, shore_col, shore[:, None] * 0.95)
    alpha = alpha * (1.0 - shore)
    bedm = smoothstep(-0.2, 1.5, inside)
    col = lerp(col, PAL['bed'], bedm[:, None])
    alpha = alpha * (1.0 - bedm)

    return np.concatenate([col[:, :3], alpha[:, None]], axis=1).astype(F32)


def grid_triangles(nx, nz):
    """Two upward-facing triangles per cell, same diagonal everywhere (matches the water mesh)."""
    ii, jj = np.meshgrid(np.arange(nx - 1), np.arange(nz - 1))      # shapes (nz-1, nx-1)
    v00 = (jj * nx + ii).ravel()
    v10 = v00 + 1
    v01 = v00 + nx
    v11 = v01 + 1
    T = np.empty((len(v00) * 2, 3), dtype=np.int32)
    T[0::2] = np.stack([v00, v01, v11], axis=1)
    T[1::2] = np.stack([v00, v11, v10], axis=1)
    return T, ii.ravel(), jj.ravel()


def build_terrain():
    xs, zs = make_grid()
    nx, nz = len(xs), len(zs)
    X, Z = np.meshgrid(xs, zs)                       # (nz, nx)
    H = W.height(X, Z)
    dzdx = np.gradient(H, xs, axis=1)
    dzdz = np.gradient(H, zs, axis=0)
    slope = np.hypot(dzdx, dzdz)
    C = terrain_colors(X.ravel(), Z.ravel(), H.ravel(), slope.ravel())
    P = np.stack([X.ravel(), H.ravel(), Z.ravel()], axis=1).astype(F32)
    T, ci, cj = grid_triangles(nx, nz)
    info = dict(xs=xs, zs=zs, H=H, nx=nx, nz=nz)
    return P, T, C, info


def build_water(info):
    xs, zs, H = info['xs'], info['zs'], info['H']
    nx, nz = info['nx'], info['nz']
    cmin = np.minimum.reduce([H[:-1, :-1], H[1:, :-1], H[:-1, 1:], H[1:, 1:]])
    sel = cmin < (W.WATER_Y - 0.02)                 # (nz-1, nx-1)
    T_all, ci, cj = grid_triangles(nx, nz)
    cell_sel = sel[cj, ci]
    tri_sel = np.repeat(cell_sel, 2)
    T = T_all[tri_sel]
    used = np.unique(T.ravel())
    remap = -np.ones(nx * nz, dtype=np.int64)
    remap[used] = np.arange(len(used))
    T = remap[T].astype(np.int32)
    X, Z = np.meshgrid(xs, zs)
    Xu, Zu, Hu = X.ravel()[used], Z.ravel()[used], H.ravel()[used]
    P = np.stack([Xu, np.full(len(used), W.WATER_Y), Zu], axis=1).astype(F32)
    depth = W.WATER_Y - Hu
    inside, zn, zsb = W.river_mask_info(Xu, Zu)
    # R: signed depth remapped (-2 .. +8 m -> 0 .. 1), G: far-shore darkness, B: open-water factor
    r = np.clip((depth + 2.0) / 10.0, 0.0, 1.0)
    g = np.exp(-np.clip(Zu - zsb, 0.0, None) / 70.0) * (inside > -2.0)
    b = smoothstep(0.0, 45.0, inside)
    C = np.stack([r, g, b, np.ones_like(r)], axis=1).astype(F32)
    return P, T, C
