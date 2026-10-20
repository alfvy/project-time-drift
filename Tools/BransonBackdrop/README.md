# Branson backdrop generator

Procedural, non-playable **Branson, MO** scenery around the hospital: the White River (Lake Taneycomo) to the south,
a Branson-Landing-style waterfront with boardwalk, piers and a showboat, downtown + the "76 strip" to the east and
west, a Tudor-ish town on the far bank, and autumn-coloured Ozark hills with scattered houses.  It is deliberately
low-detail: everything is flat/smooth-shaded vertex-coloured geometry; windows, canopy texture, water and haze are
done in shaders.

Everything is built in Blender (Python) and exported as five `.glb` files into `Assets/Models/Branson/`;
`Assets/Editor/BransonBackdropAssembler.cs` turns them into the `Branson Backdrop` GameObject (and
`Assets/Prefabs/Branson Backdrop.prefab`) with the `Branson/*` materials.

## In Unity (`Tools > Branson Backdrop`)

| Menu item | What it does |
|---|---|
| **Rebuild In Open Scene (and save prefab)** | Replaces the `Branson Backdrop` object in the open scene from the `.glb` files, assigns materials, re-saves the prefab. Run it after re-exporting from Blender. |
| **Sync Sky From Scene Skybox** | Copies the scene skybox (texture / exposure / rotation) into the backdrop materials. Run it after you change the skybox. |
| **Select Backdrop Root** | Selects the root object. |

Materials live in `Assets/Materials/Branson/` (created once, never overwritten, so tweak them freely):

* `BR_*` (`Branson/Land`): `Exposure`, `Sun Influence`, ambient colours, **haze** (`Haze Density`, far fade), `Canopy` /
  `Procedural windows` toggles (`Lit Fraction`, `Lit Boost` = how many windows glow and how bright), `Emissive Boost` for lamps.
* `BR_Water` (`Branson/Water`): `Reflection Brightness`, `Reflection Tint`, `Ripple Strength`, `Flow`, `Sparkle`, colours.
* `BR_Streaks` (`Branson/Streak`): the glittering light reflections on the river. They are projected for a viewer at
  the south windows (they are separate objects, `Branson_Water > BR_Streaks`; disable them for other cameras).

The shaders sample the **scene skybox** for the haze colour and the water reflection, so the river and distant hills
always match whatever sky the scene shows. The look is currently tuned for the existing dusk skybox (exposure 0.28).

## Regenerating (Blender 4.2+ / 5.x)

In Blender's Scripting tab (or through the Unity MCP Blender bridge `run_python`):

```python
import sys; sys.path.insert(0, r"D:/explorations/project-time-drift/Tools/BransonBackdrop")
import br_build; br_build.run("all")      # "terrain" = ground + river only
```

then in Unity: `Tools > Branson Backdrop > Rebuild In Open Scene`. A run takes a few seconds and is deterministic
(seeded). The generator creates its own Blender scene called `Branson Backdrop` and switches back to your scene.

| File | Content |
|---|---|
| `br_world.py` | River banks, bay, islands, valley floor, hills -> `height(x, z)`. River level 0, campus ground 2.45. |
| `br_terrain.py` | Terrain + water meshes, autumn canopy colours. |
| `br_city.py` | Campus lots + cars, boulevard, boardwalk, Landing shops, downtown, strip, Titanic-style landmark, far-bank town, houses. |
| `br_flora.py` | Instanced low-poly trees (merged per tile). |
| `br_props.py` | Ferris wheel, bridge, piers, boats, showboat, towers, fountain. |
| `br_streaks.py` | River light reflections. |
| `br_build.py` | Orchestration + glb export. |

## Things worth knowing

* **Coordinates.** Everything is authored in *Unity world space* (X east, Z north; the hospital faces the river along -Z).
  UnityGLTF imports Blender `(x, y, z)` as Unity `(-x, z, -y)`, so `br_common.to_blender` applies the exact inverse
  (and flips winding) when writing meshes: the glb lands at the right place with an identity transform.
* **View corridor.** Nothing taller than a car stands in front of the south windows (`x -115..125, z -100..14`);
  the windows are 2 m x 1 m ribbons, so any tree or building there would hide the river.
* **URP Deferred.** The project renders in Deferred, so the Branson shaders use the forward-only pass tag
  `UniversalForwardOnly` (a plain `UniversalForward` pass would not draw).
* **Skybox brightness.** URP draws `Skybox/Panoramic` as `texture * linear(tint) * exposure` (no x4.59), and the
  backdrop samples it the same way.
* **Don't delete the material assets behind Unity's back** (e.g. from Explorer): the prefab keeps stale references
  and the backdrop renders magenta until the prefab is re-imported. Use the Rebuild menu item, which re-imports and verifies.
* The `.glb` importer is set to non-readable meshes, no colliders, to keep memory low. There are no colliders anywhere:
  the city is purely visual.
