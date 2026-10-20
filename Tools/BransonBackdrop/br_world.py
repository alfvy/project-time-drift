"""World definition for the Branson backdrop: river, banks, valley floor, hills.

Unity world coordinates (metres): X east, Z north, Y up.  The hospital sits at roughly
X -14..23, Z -16..34 with its ground floor slab at Y 2.49; the office windows look south (-Z).

Layout, south to north:
    forested Ozark ridges  ->  south-bank bench ("Hollister")  ->  WHITE RIVER  ->
    shore + boardwalk  ->  lawn / boulevard  ->  hospital campus  ->  north bench  ->  hills
"""
import numpy as np
from br_common import smoothstep, fbm, vnoise

# ----------------------------------------------------------------------------- key levels
WATER_Y = 0.0            # river surface
QUAY_H = 1.25            # boardwalk height above the water
PAD_Y = 2.45             # hospital campus ground (just under the 2.49 slab)
SBENCH_Y = 2.15          # south bank bench

# ----------------------------------------------------------------------------- river shape
NEAR0 = -72.0            # near (north) bank, z at x=0 before wiggles
FAR0 = -400.0           # far (south) bank


def _bend(x):
    """Whole-channel bend so the river curves away at both ends."""
    x = np.asarray(x, dtype=np.float64)
    east = -0.00019 * np.maximum(x - 240.0, 0.0) ** 2        # east end swings south
    west = 0.00013 * np.maximum(-x - 300.0, 0.0) ** 2        # west end swings north
    return east + west


def _bay(x):
    """Extra southward push of the far bank: a broad bay opposite the hospital (more open water in the view)."""
    x = np.asarray(x, dtype=np.float64)
    return 185.0 * np.exp(-(((x - 20.0) / 165.0) ** 2))


def banks(x):
    """(z_near, z_far) of the river banks for world x (vectorised)."""
    x = np.asarray(x, dtype=np.float64)
    bend = _bend(x)
    zn = NEAR0 + 9.0 * np.sin((x + 40.0) / 115.0) + 13.0 * np.sin((x - 90.0) / 240.0) + bend
    zs = (FAR0 + 24.0 * np.sin((x + 110.0) / 165.0) + 18.0 * np.sin((x - 70.0) / 310.0) + bend
          + 38.0 * np.exp(-(((x + 170.0) / 70.0) ** 2))         # a headland pushing into the river
          - _bay(x))
    # taper the channel closed at both ends of the valley
    f = smoothstep(980.0, 640.0, np.abs(x))
    zc = (zn + zs) * 0.5
    hw = (zn - zs) * 0.5 * f
    return zc + hw, zc - hw


ISLANDS = [  # cx, cz, rx, rz, yaw-ish tilt (z per x), height above water at crest
    (28.0, -192.0, 105.0, 24.0, 0.06, 1.9),
    (-215.0, -268.0, 60.0, 16.0, -0.04, 1.4),
    (-45.0, -338.0, 84.0, 20.0, -0.03, 1.5),
    (270.0, -236.0, 84.0, 20.0, 0.03, 1.6),
]
BED_DEPTH = 5.2
BANK_SLOPE = 15.0        # metres over which the bank drops to full depth


def bench_y(x):
    """North bench height: flat at the campus, gently varying farther along the valley."""
    x = np.asarray(x, dtype=np.float64)
    return PAD_Y + 1.1 * (vnoise(x / 320.0, 3.7, 5) - 0.5) * 2.0 * smoothstep(110.0, 420.0, np.abs(x))


def _valley_parts(x, z, zs):
    dn = np.maximum(z - 108.0, 0.0)
    ds = np.maximum((zs + _bay(x) - 120.0) - z, 0.0)       # hills start behind the un-bayed bank line
    dx = np.maximum(np.abs(x) - 640.0, 0.0)
    return dn, ds, dx


def _valley_distance(x, z, zs):
    """0 inside the valley floor; metres to its edge outside (north / south / lateral ends)."""
    dn, ds, dx = _valley_parts(x, z, zs)
    return np.sqrt(dn * dn + ds * ds + dx * dx)


def hills_shape(x, z):
    """Dimensionless Ozark relief in ~[0, 1]: broad ridges plus ridged crests plus roughness."""
    n1 = fbm(x / 540.0 + 2.1, z / 540.0 - 4.4, 4, seed=11)
    n2 = fbm(x / 210.0 - 8.0, z / 210.0 + 3.0, 3, seed=23)
    rid = 1.0 - np.abs(2.0 * fbm(x / 760.0 + 5.0, z / 760.0 + 9.0, 3, seed=41) - 1.0)
    h = 0.50 * n1 + 0.22 * n2 + 0.40 * rid ** 1.6
    return np.clip(h, 0.0, 1.4)


def height(x, z):
    """Terrain height (Y) at world (x, z); vectorised, float64."""
    x = np.asarray(x, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    zn, zs = banks(x)
    zc = (zn + zs) * 0.5
    inside = np.minimum(zn - z, z - zs)            # >0 inside the channel (metres to nearest bank)

    # --- channel bed (+ islands)
    bed = WATER_Y - BED_DEPTH * smoothstep(0.0, BANK_SLOPE, inside)
    for cx, cz, rx, rz, tilt, crest in ISLANDS:
        dxx = (x - cx) / rx
        dzz = (z - cz - tilt * (x - cx)) / rz
        r2 = dxx * dxx + dzz * dzz
        w = np.clip(1.0 - r2, 0.0, 1.0) ** 2
        bump = (WATER_Y - BED_DEPTH + (BED_DEPTH + crest) * w)
        bed = np.maximum(bed, np.where(w > 0, bump, -99.0))

    # --- north land: shore ramp -> quay -> lawn ramp -> bench
    a = z - zn
    # bank slope (a 0..5) -> boardwalk level (5..11) -> short berm (11..19) -> flat campus bench
    hn = (WATER_Y + QUAY_H * smoothstep(0.0, 5.0, a)
          + (bench_y(x) - WATER_Y - QUAY_H) * smoothstep(11.0, 19.0, a))
    # --- south land
    b = zs - z
    hs = (WATER_Y + QUAY_H * smoothstep(0.0, 10.0, b)
          + (SBENCH_Y - WATER_Y - QUAY_H) * smoothstep(10.0, 150.0, b))

    h = np.where(inside > 0.0, bed, np.where(z > zc, hn, hs))

    # --- hills rising out of the valley
    dn_, ds_, dx_ = _valley_parts(x, z, zs)
    d = np.sqrt(dn_ * dn_ + ds_ * ds_ + dx_ * dx_)
    amp = 185.0 * smoothstep(0.0, 600.0, d) ** 0.9
    # the river valley opens to the south: lower, softer ridges straight ahead of the hospital windows
    gap = 0.40 + 0.60 * smoothstep(170.0, 600.0, np.abs(x - 10.0))
    w_south = ds_ / np.maximum(d, 1e-6)
    amp = amp * ((1.0 - w_south) + w_south * gap)
    base = 8.0 * smoothstep(0.0, 120.0, d)
    land = smoothstep(-0.5, 16.0, -inside)                  # never lift the river bed
    h = h + (base + amp * hills_shape(x, z)) * land
    return h


def river_mask_info(x, z):
    """Helper values for shading: distance to nearest bank inside the channel, zn, zs."""
    zn, zs = banks(x)
    return np.minimum(zn - z, z - zs), zn, zs
