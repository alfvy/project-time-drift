"""Orchestrator: builds the Branson backdrop inside Blender and exports glb files for Unity.

Usage (Blender Python console / MCP):
    import sys; sys.path.insert(0, r"D:/explorations/project-time-drift/Tools/BransonBackdrop")
    import br_build; br_build.run("all")        # or "terrain" for just the ground + river

Coordinates: the generator works in Unity world space (X east, Z north).  Geometry is converted to
Blender axes only when it is written (see br_common.to_blender), so the exported glb lands in Unity
at the same coordinates with an identity transform.
"""
import os
import sys
import time
import importlib

import numpy as np
import bpy

TOOLS = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"D:/explorations/project-time-drift/Tools/BransonBackdrop"
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

# (re)load in dependency order so edits made between runs are always picked up
for _name in ("br_common", "br_world", "br_terrain", "br_city", "br_streaks", "br_flora", "br_props"):
    _mod = importlib.import_module(_name)
    importlib.reload(_mod)
    globals()[_name] = _mod
from br_common import make_blender_object, get_material

OUT_DIR = r"D:/explorations/project-time-drift/Assets/Models/Branson"
SCENE_NAME = "Branson Backdrop"


def _scene():
    sc = bpy.data.scenes.get(SCENE_NAME) or bpy.data.scenes.new(SCENE_NAME)
    if bpy.context.window is not None:
        bpy.context.window.scene = sc
    coll = sc.collection.children.get("Branson")
    if coll is None:
        coll = bpy.data.collections.new("Branson")
        sc.collection.children.link(coll)
    return sc, coll


def _clear():
    for ob in [o for o in bpy.data.objects if o.name.startswith("BR_")]:
        me = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)


def export(sc, names, filename):
    os.makedirs(OUT_DIR, exist_ok=True)
    for o in sc.objects:
        o.select_set(False)
    first = None
    for n in names:
        ob = bpy.data.objects[n]
        ob.select_set(True)
        first = first or ob
    bpy.context.view_layer.objects.active = first
    path = OUT_DIR + "/" + filename
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, use_active_scene=True,
        export_apply=False, export_yup=True, export_vertex_color='ACTIVE',
        export_active_vertex_color_when_no_material=True, export_materials='EXPORT',
        export_texcoords=False, export_cameras=False, export_lights=False, export_animations=False,
        export_extras=False, export_loglevel=40,
    )
    return path, os.path.getsize(path)


def _emit(coll, name, P, T, C, material, smooth=True):
    if len(T) == 0:
        return None
    make_blender_object(bpy, name, P, T, C, get_material(bpy, material), coll, smooth=smooth)
    return name


def _acc_obj(coll, acc, material=None, smooth=False):
    P, T, C = acc.arrays()
    return _emit(coll, acc.name, P, T, C, material or acc.name, smooth)


def run(stage="all"):
    orig = bpy.context.scene
    sc, coll = _scene()
    t0 = time.time()
    print("== Branson backdrop build: %s" % stage)
    try:
        _clear()
        files = {}
        info = None
        if stage in ("terrain",):
            info = None
        # ---------------------------------------------------------------- city + props + trees
        A = None
        streaks = None
        if stage == "all":
            t1 = time.time()
            A, cstats = br_city.build_city()
            br_props.build_props(A)
            streaks = br_streaks.build_streaks()
            print("  streaks      %d light reflections" % streaks[3])
            print("  city+props   %.1fs  houses=%d  tris: %s" % (time.time() - t1, cstats["houses"],
                  {k: v.tri_count() for k, v in A.items()}))
            t1 = time.time()
            ts, tstats = br_flora.build_trees()
            print("  trees        %.1fs  %s  tris=%d tiles=%d" % (time.time() - t1, tstats, ts.count(), len(ts.tiles)))
            br_terrain.URBAN_FN = br_city.urban_mask
        else:
            br_terrain.URBAN_FN = None
        # ---------------------------------------------------------------- terrain + water
        t1 = time.time()
        P, T, C, info = br_terrain.build_terrain()
        _emit(coll, "BR_Terrain", P, T, C, "BR_Terrain", smooth=True)
        Pw, Tw, Cw = br_terrain.build_water(info)
        _emit(coll, "BR_Water", Pw, Tw, Cw, "BR_Water", smooth=False)
        print("  terrain+water %.1fs  terrain tris=%d  water tris=%d" % (time.time() - t1, len(T), len(Tw)))
        files["Branson_Terrain.glb"] = ["BR_Terrain"]
        files["Branson_Water.glb"] = ["BR_Water"]
        if A is not None and streaks[3] > 0:
            _emit(coll, "BR_Streaks", streaks[0], streaks[1], streaks[2], "BR_Streaks", smooth=False)
            files["Branson_Water.glb"].append("BR_Streaks")
        if A is not None:
            names = [_acc_obj(coll, A["BR_Buildings"]), _acc_obj(coll, A["BR_Roads"])]
            files["Branson_City.glb"] = [n for n in names if n]
            names = [_acc_obj(coll, A["BR_Props"]), _acc_obj(coll, A["BR_Lights"])]
            files["Branson_Props.glb"] = [n for n in names if n]
            tn = []
            for key, acc in sorted(ts.tiles.items()):
                P_, T_, C_ = acc.arrays()
                n_ = _emit(coll, acc.name, P_, T_, C_, "BR_Trees", smooth=True)
                if n_:
                    tn.append(n_)
            files["Branson_Flora.glb"] = tn
        for fn, names in files.items():
            path, size = export(sc, names, fn)
            print("  exported %-22s %5.1f MB  (%d object%s)" % (fn, size / 1048576.0, len(names), "" if len(names) == 1 else "s"))
    finally:
        if bpy.context.window is not None and orig is not None and orig.name != SCENE_NAME:
            bpy.context.window.scene = orig
    print("== done in %.1fs" % (time.time() - t0))
