"""Shared helpers for the Branson backdrop generator (runs inside Blender's Python).

Everything is authored in *Unity world coordinates* (X east, Y up, Z north; the hospital's
south face looks down -Z at the river).  Geometry is converted to Blender axes only when it
is written into a Blender mesh (see `to_blender`), because UnityGLTF's importer maps
Blender (x, y, z) -> Unity (-x, z, -y).  `to_blender` is the exact inverse, so the glb comes
out in Unity at the coordinates used here with an identity root transform.
"""
import math
import numpy as np

F32 = np.float32


# --------------------------------------------------------------------------- colour
def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(F32)


def hexlin(h, a=1.0):
    """'#RRGGBB' (sRGB) -> linear RGBA float32 array."""
    h = h.lstrip('#')
    rgb = np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=np.float64)
    return np.concatenate([srgb_to_linear(rgb), [a]]).astype(F32)


# --------------------------------------------------------------------------- math
def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def _rnd(ix, iz, seed):
    h = (ix * 73856093) ^ (iz * 19349663) ^ (np.int64(seed) * 83492791)
    h = (h ^ (h >> 13)) * 1274126177
    h = (h ^ (h >> 16)) & 0x7FFFFFFF
    return (h & 0xFFFFFF).astype(np.float64) / float(0x1000000)


def vnoise(x, z, seed=0):
    """Smooth value noise in [0, 1)."""
    x = np.asarray(x, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    xi = np.floor(x).astype(np.int64)
    zi = np.floor(z).astype(np.int64)
    xf = x - xi
    zf = z - zi
    u = xf * xf * xf * (xf * (xf * 6 - 15) + 10)
    v = zf * zf * zf * (zf * (zf * 6 - 15) + 10)
    a = _rnd(xi, zi, seed)
    b = _rnd(xi + 1, zi, seed)
    c = _rnd(xi, zi + 1, seed)
    d = _rnd(xi + 1, zi + 1, seed)
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v


def fbm(x, z, octaves=5, lac=2.0, gain=0.5, seed=0):
    """Fractal value noise, normalised to roughly [0, 1]; domain is rotated per octave."""
    x = np.asarray(x, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    amp, tot, norm = 1.0, 0.0, 0.0
    ca, sa = math.cos(0.62), math.sin(0.62)
    for o in range(octaves):
        tot = tot + amp * vnoise(x, z, seed + 17 * o)
        norm += amp
        x, z = (x * ca - z * sa) * lac + 11.3, (x * sa + z * ca) * lac - 7.7
        amp *= gain
    return tot / norm


def rng(seed):
    return np.random.default_rng(seed)


# --------------------------------------------------------------------------- transforms
def rot_y(P, yaw_deg, cx=0.0, cz=0.0):
    """Rotate points about the vertical axis through (cx, cz).  yaw 0 keeps +X as +X."""
    P = np.array(P, dtype=F32, copy=True)
    a = math.radians(yaw_deg)
    c, s = math.cos(a), math.sin(a)
    x = P[:, 0] - cx
    z = P[:, 2] - cz
    P[:, 0] = x * c + z * s + cx
    P[:, 2] = -x * s + z * c + cz
    return P


def orient_outward(P, T, center=None):
    """Flip triangles so that numeric cross(b-a, c-a) points away from `center` (convex bodies)."""
    P = np.asarray(P, dtype=F32)
    T = np.array(T, dtype=np.int32, copy=True)
    if center is None:
        center = P.mean(axis=0)
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    n = np.cross(b - a, c - a)
    t = (a + b + c) / 3.0
    flip = (n * (t - center)).sum(axis=1) < 0
    T[flip] = T[flip][:, [0, 2, 1]]
    return T


# --------------------------------------------------------------------------- primitives
_BOX_T = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 4, 7], [0, 7, 3],
                   [1, 2, 6], [1, 6, 5], [0, 1, 5], [0, 5, 4], [3, 7, 6], [3, 6, 2]], dtype=np.int32)
_BOX_T_NOBOTTOM = np.delete(_BOX_T, [8, 9], axis=0)


def box(cx, y0, cz, sx, sy, sz, yaw=0.0, bottom=True):
    hx, hz = sx / 2.0, sz / 2.0
    P = np.array([[-hx, 0, -hz], [hx, 0, -hz], [hx, sy, -hz], [-hx, sy, -hz],
                  [-hx, 0, hz], [hx, 0, hz], [hx, sy, hz], [-hx, sy, hz]], dtype=F32)
    if yaw:
        P = rot_y(P, yaw)
    P += np.array([cx, y0, cz], dtype=F32)
    return P, (_BOX_T if bottom else _BOX_T_NOBOTTOM).copy()


def box_corners(P0, P1):
    """Axis-aligned box from min/max corner."""
    (x0, y0, z0), (x1, y1, z1) = P0, P1
    return box((x0 + x1) / 2, y0, (z0 + z1) / 2, abs(x1 - x0), y1 - y0, abs(z1 - z0))


def gable_roof(cx, y0, cz, sx, sz, rise, overhang=0.35, yaw=0.0, along_x=None):
    """Triangular-prism roof sitting at y0 over an sx*sz footprint (no bottom face)."""
    if along_x is None:
        along_x = sx >= sz
    hx, hz = sx / 2.0 + overhang, sz / 2.0 + overhang
    if along_x:
        P = np.array([[-hx, 0, -hz], [hx, 0, -hz], [hx, 0, hz], [-hx, 0, hz], [-hx, rise, 0], [hx, rise, 0]], dtype=F32)
        T = np.array([[0, 1, 5], [0, 5, 4], [3, 4, 5], [3, 5, 2], [0, 4, 3], [1, 2, 5]], dtype=np.int32)
    else:
        P = np.array([[-hx, 0, -hz], [hx, 0, -hz], [hx, 0, hz], [-hx, 0, hz], [0, rise, -hz], [0, rise, hz]], dtype=F32)
        T = np.array([[0, 4, 3], [4, 5, 3], [1, 2, 5], [1, 5, 4], [0, 1, 4], [3, 5, 2]], dtype=np.int32)
    if yaw:
        P = rot_y(P, yaw)
    P += np.array([cx, y0, cz], dtype=F32)
    return P, orient_outward(P, T)


def hip_roof(cx, y0, cz, sx, sz, rise, overhang=0.3, yaw=0.0, ridge_frac=0.25):
    """Hipped roof: a low pyramid-ish frustum with a short ridge."""
    hx, hz = sx / 2.0 + overhang, sz / 2.0 + overhang
    if sx >= sz:
        r = max((hx - hz) * (1 - ridge_frac), 0.06)
        P = np.array([[-hx, 0, -hz], [hx, 0, -hz], [hx, 0, hz], [-hx, 0, hz],
                      [-r, rise, 0], [r, rise, 0]], dtype=F32)
        T = np.array([[0, 1, 5], [0, 5, 4], [3, 4, 5], [3, 5, 2], [0, 4, 3], [1, 2, 5]], dtype=np.int32)
    else:
        r = max((hz - hx) * (1 - ridge_frac), 0.06)
        P = np.array([[-hx, 0, -hz], [hx, 0, -hz], [hx, 0, hz], [-hx, 0, hz],
                      [0, rise, -r], [0, rise, r]], dtype=F32)
        T = np.array([[0, 4, 3], [4, 5, 3], [1, 2, 5], [1, 5, 4], [0, 1, 4], [3, 5, 2]], dtype=np.int32)
    if yaw:
        P = rot_y(P, yaw)
    P += np.array([cx, y0, cz], dtype=F32)
    return P, orient_outward(P, T)


def pyramid(cx, y0, cz, sx, sz, h, yaw=0.0):
    P = np.array([[-sx / 2, 0, -sz / 2], [sx / 2, 0, -sz / 2], [sx / 2, 0, sz / 2], [-sx / 2, 0, sz / 2], [0, h, 0]], dtype=F32)
    T = np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4], [0, 2, 1], [0, 3, 2]], dtype=np.int32)
    if yaw:
        P = rot_y(P, yaw)
    P += np.array([cx, y0, cz], dtype=F32)
    return P, orient_outward(P, T)


def cylinder(cx, y0, cz, r, h, n=8, r_top=None, cap_top=True, cap_bottom=False, rot=0.0):
    """Vertical (possibly tapered) n-gon prism."""
    r_top = r if r_top is None else r_top
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False) + math.radians(rot)
    cs, sn = np.cos(ang), np.sin(ang)
    bot = np.stack([cx + r * cs, np.full(n, y0), cz + r * sn], axis=1)
    top = np.stack([cx + r_top * cs, np.full(n, y0 + h), cz + r_top * sn], axis=1)
    P = np.concatenate([bot, top], axis=0).astype(F32)
    T = []
    for i in range(n):
        j = (i + 1) % n
        T += [[i, n + i, n + j], [i, n + j, j]]
    extra = []
    if cap_top:
        P = np.vstack([P, [[cx, y0 + h, cz]]]).astype(F32)
        c = len(P) - 1
        for i in range(n):
            T.append([n + i, c, n + (i + 1) % n])
    if cap_bottom:
        P = np.vstack([P, [[cx, y0, cz]]]).astype(F32)
        c = len(P) - 1
        for i in range(n):
            T.append([i, (i + 1) % n, c])
    T = np.array(T, dtype=np.int32)
    return P, orient_outward(P, T, np.array([cx, y0 + h / 2.0, cz], dtype=F32))


def cone(cx, y0, cz, r, h, n=7, rot=0.0, cap_bottom=False):
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False) + math.radians(rot)
    ring = np.stack([cx + r * np.cos(ang), np.full(n, y0), cz + r * np.sin(ang)], axis=1)
    P = np.vstack([ring, [[cx, y0 + h, cz]]]).astype(F32)
    T = [[i, n, (i + 1) % n] for i in range(n)]
    if cap_bottom:
        P = np.vstack([P, [[cx, y0, cz]]]).astype(F32)
        T += [[i, (i + 1) % n, n + 1] for i in range(n)]
    T = np.array(T, dtype=np.int32)
    return P, orient_outward(P, T, np.array([cx, y0 + h * 0.33, cz], dtype=F32))


def blob_template(seg=6, squash=0.82):
    """Unit low-poly 'canopy' blob: apex, two rings, bottom apex -> smooth-shaded when welded."""
    ang = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    ang2 = ang + np.pi / seg
    r1, y1 = 0.92, 0.38
    r2, y2 = 0.92, -0.18
    ring1 = np.stack([r1 * np.cos(ang), np.full(seg, y1), r1 * np.sin(ang)], axis=1)
    ring2 = np.stack([r2 * np.cos(ang2), np.full(seg, y2), r2 * np.sin(ang2)], axis=1)
    P = np.vstack([[[0, 1.0, 0]], ring1, ring2, [[0, -0.62, 0]]]).astype(F32)
    P[:, 1] *= squash
    top, bot = 0, 1 + 2 * seg
    T = []
    for i in range(seg):
        j = (i + 1) % seg
        a1, b1 = 1 + i, 1 + j
        a2, b2 = 1 + seg + i, 1 + seg + j
        T.append([top, a1, b1])
        # band between ring1 and ring2 (ring2 offset by half a step)
        T.append([a1, a2, b1])
        T.append([b1, a2, 1 + seg + ((i + 1) % seg)])
        T.append([a2, bot, 1 + seg + ((i + 1) % seg)])
    T = np.array(T, dtype=np.int32)
    return P, orient_outward(P, T, np.array([0, 0.1, 0], dtype=F32))


def quad(p0, p1, p2, p3):
    """One quad (4 points in order) as two triangles, oriented by the caller's winding."""
    P = np.array([p0, p1, p2, p3], dtype=F32)
    T = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
    return P, T


def ribbon(left, right, up=True):
    """Triangle strip between two polylines (Nx3 each).  Winding gives an upward normal."""
    left = np.asarray(left, dtype=F32)
    right = np.asarray(right, dtype=F32)
    n = len(left)
    P = np.vstack([left, right])
    T = []
    for i in range(n - 1):
        l0, l1, r0, r1 = i, i + 1, n + i, n + i + 1
        T += [[l0, l1, r1], [l0, r1, r0]]
    T = np.array(T, dtype=np.int32)
    # make normals point up (or down)
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    ny = np.cross(b - a, c - a)[:, 1]
    flip = (ny < 0) if up else (ny > 0)
    T[flip] = T[flip][:, [0, 2, 1]]
    return P, T


def polyline_offsets(xz, half_width):
    """Left/right offset polylines (Nx2) for a centre polyline (Nx2), mitred by averaging normals."""
    xz = np.asarray(xz, dtype=np.float64)
    d = np.gradient(xz, axis=0)
    ln = np.linalg.norm(d, axis=1, keepdims=True)
    ln[ln == 0] = 1
    d = d / ln
    nrm = np.stack([-d[:, 1], d[:, 0]], axis=1)
    hw = np.asarray(half_width, dtype=np.float64)
    if hw.ndim == 0:
        hw = np.full(len(xz), float(hw))
    return xz + nrm * hw[:, None], xz - nrm * hw[:, None]


# --------------------------------------------------------------------------- accumulation
class Acc:
    """Accumulates triangles + vertex colours.  Meshes added with flat=True are un-welded so
    they shade flat; smooth meshes keep their shared vertices."""

    def __init__(self, name):
        self.name = name
        self.P, self.C, self.T = [], [], []
        self.n = 0

    @staticmethod
    def _col(C, n):
        C = np.asarray(C, dtype=F32)
        if C.ndim == 1:
            C = np.tile(C, (n, 1))
        if C.shape[1] == 3:
            C = np.hstack([C, np.ones((len(C), 1), dtype=F32)])
        return C

    def add(self, P, T, C, flat=True):
        P = np.asarray(P, dtype=F32).reshape(-1, 3)
        T = np.asarray(T, dtype=np.int32).reshape(-1, 3)
        if len(T) == 0:
            return
        C = self._col(C, len(P))
        if flat:
            P2 = P[T].reshape(-1, 3)
            C2 = C[T].reshape(-1, 4)
            T2 = np.arange(len(P2), dtype=np.int32).reshape(-1, 3)
            P, C, T = P2, C2, T2
        self.P.append(P)
        self.C.append(C)
        self.T.append(T + self.n)
        self.n += len(P)

    def add_many(self, parts, C, flat=True):
        for P, T in parts:
            self.add(P, T, C, flat)

    def arrays(self):
        if not self.P:
            return (np.zeros((0, 3), F32), np.zeros((0, 3), np.int32), np.zeros((0, 4), F32))
        return np.vstack(self.P), np.vstack(self.T), np.vstack(self.C)

    def tri_count(self):
        return int(sum(len(t) for t in self.T))


# --------------------------------------------------------------------------- Blender output
def to_blender(P, T):
    """Unity world -> Blender (inverse of UnityGLTF's import map); winding flipped for the reflection."""
    P = np.asarray(P, dtype=F32)
    B = np.stack([-P[:, 0], -P[:, 2], P[:, 1]], axis=1).astype(F32)
    return B, np.asarray(T, dtype=np.int32)[:, [0, 2, 1]].copy()


def make_blender_object(bpy, name, P, T, C, material=None, collection=None, smooth=True):
    B, Tb = to_blender(P, T)
    me = bpy.data.meshes.new(name)
    nV, nF = len(B), len(Tb)
    me.vertices.add(nV)
    me.vertices.foreach_set('co', B.ravel())
    me.loops.add(nF * 3)
    me.loops.foreach_set('vertex_index', Tb.ravel())
    me.polygons.add(nF)
    me.polygons.foreach_set('loop_start', np.arange(0, nF * 3, 3, dtype=np.int32))
    me.polygons.foreach_set('loop_total', np.full(nF, 3, dtype=np.int32))
    me.polygons.foreach_set('use_smooth', np.full(nF, smooth, dtype=bool))
    me.update(calc_edges=True)
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', np.asarray(C, dtype=F32).ravel())
    if material is not None:
        me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    (collection.objects if collection is not None else bpy.context.scene.collection.objects).link(ob)
    return ob


def get_material(bpy, name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    return m


def prism_poly(poly_xz, y0, h, cap_top=True, cap_bottom=False):
    """Vertical prism over a *convex* polygon (list of (x, z))."""
    poly = np.asarray(poly_xz, dtype=F32)
    n = len(poly)
    bot = np.column_stack([poly[:, 0], np.full(n, y0), poly[:, 1]])
    top = np.column_stack([poly[:, 0], np.full(n, y0 + h), poly[:, 1]])
    P = np.vstack([bot, top]).astype(F32)
    T = []
    for i in range(n):
        j = (i + 1) % n
        T += [[i, n + i, n + j], [i, n + j, j]]
    if cap_top:
        for i in range(1, n - 1):
            T.append([n, n + i, n + i + 1])
    if cap_bottom:
        for i in range(1, n - 1):
            T.append([0, i, i + 1])
    T = np.array(T, dtype=np.int32)
    return P, orient_outward(P, T, P.mean(axis=0))
