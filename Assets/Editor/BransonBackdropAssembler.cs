#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

/// <summary>
/// Assembles the "Branson Backdrop" (the non-playable Branson, MO scenery around the hospital) from the
/// glb files exported by Tools/BransonBackdrop (Blender), assigns the Branson/* materials, and saves the
/// result as Assets/Prefabs/Branson Backdrop.prefab.   Menu: Tools > Branson Backdrop.
/// </summary>
public static class BransonBackdropAssembler
{
    public const string RootName = "Branson Backdrop";
    const string ModelDir = "Assets/Models/Branson";
    const string MatDir = "Assets/Materials/Branson";
    const string PrefabPath = "Assets/Prefabs/Branson Backdrop.prefab";

    // mesh-name prefix  ->  material key
    static readonly (string prefix, string key)[] MeshToMaterial =
    {
        ("BR_Water", "BR_Water"),
        ("BR_Streak", "BR_Streaks"),
        ("BR_Terrain", "BR_Terrain"),
        ("BR_Building", "BR_Buildings"),
        ("BR_Road", "BR_Roads"),
        ("BR_Tree", "BR_Trees"),
        ("BR_Light", "BR_Lights"),
        ("BR_Prop", "BR_Props"),
    };

    static Material GetOrCreateMaterial(string key)
    {
        string path = $"{MatDir}/{key}.mat";
        var existing = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (existing != null) return existing;

        if (!AssetDatabase.IsValidFolder(MatDir))
        {
            if (!AssetDatabase.IsValidFolder("Assets/Materials")) AssetDatabase.CreateFolder("Assets", "Materials");
            AssetDatabase.CreateFolder("Assets/Materials", "Branson");
        }

        Shader shader = Shader.Find(key == "BR_Water" ? "Branson/Water" : key == "BR_Streaks" ? "Branson/Streak" : "Branson/Land");
        if (shader == null) throw new Exception($"Shader for {key} not found - has it been imported / compiled?");
        var m = new Material(shader) { name = key };
        ApplyDefaults(m, key);
        AssetDatabase.CreateAsset(m, path);
        return m;
    }

    // Colour properties are authored in linear terms here; Color material properties are treated as sRGB
    // by Unity in a linear project, so convert before storing.
    static Color Lin(float r, float g, float b, float a = 1f) => new Color(r, g, b, a).gamma;

    static void ApplyDefaults(Material m, string key)
    {
        if (m.HasProperty("_AmbientSky")) m.SetColor("_AmbientSky", Lin(0.040f, 0.062f, 0.090f));
        if (m.HasProperty("_AmbientGround")) m.SetColor("_AmbientGround", Lin(0.014f, 0.016f, 0.018f));
        if (m.HasProperty("_HazeFloor")) m.SetColor("_HazeFloor", Lin(0.008f, 0.016f, 0.022f));
        if (m.HasProperty("_WindowGlow")) m.SetColor("_WindowGlow", Lin(1.0f, 0.50f, 0.14f));
        if (m.HasProperty("_WindowDark")) m.SetColor("_WindowDark", Lin(0.010f, 0.018f, 0.026f));
        if (m.HasProperty("_DeepColor")) m.SetColor("_DeepColor", Lin(0.005f, 0.017f, 0.026f));
        if (m.HasProperty("_ShallowColor")) m.SetColor("_ShallowColor", Lin(0.030f, 0.070f, 0.072f));
        if (m.HasProperty("_FoamColor")) m.SetColor("_FoamColor", Lin(0.10f, 0.12f, 0.12f));
        if (m.HasProperty("_SparkleColor")) m.SetColor("_SparkleColor", Lin(1.0f, 0.82f, 0.55f));
        switch (key)
        {
            case "BR_Terrain":
                m.SetFloat("_Canopy", 1f); m.EnableKeyword("_CANOPY");
                break;
            case "BR_Buildings":
                m.SetFloat("_Windows", 1f); m.EnableKeyword("_WINDOWS");
                break;
            case "BR_Lights":
                m.SetFloat("_EmissiveAlpha", 1f); m.EnableKeyword("_EMISSIVE_ALPHA");
                break;
        }
    }

    // Copies the scene skybox (Skybox/Panoramic) parameters into the materials that sample it, so haze and
    // water reflections always match whatever sky the scene currently shows.
    static void SyncSky(Material m)
    {
        var sky = RenderSettings.skybox;
        if (sky == null || !m.HasProperty("_SkyTex")) return;
        if (sky.HasProperty("_MainTex")) m.SetTexture("_SkyTex", sky.GetTexture("_MainTex"));
        m.SetFloat("_SkyExposure", sky.HasProperty("_Exposure") ? sky.GetFloat("_Exposure") : 1f);
        m.SetFloat("_SkyRotation", sky.HasProperty("_Rotation") ? sky.GetFloat("_Rotation") : 0f);
        // Measured against screenshots of the real skybox: URP 12 (Linear) draws Skybox/Panoramic as
        // texture * linear(tint) * exposure -- the built-in shader's x4.59 "colour space double" does not
        // show up -- so the sky sampled by the backdrop uses the same factor.
        Color tint = sky.HasProperty("_Tint") ? sky.GetColor("_Tint") : Color.gray;
        Color lt = QualitySettings.activeColorSpace == ColorSpace.Linear ? tint.linear : tint;
        m.SetVector("_SkyTint", new Vector4(lt.r, lt.g, lt.b, 1f));
        EditorUtility.SetDirty(m);
    }

    static string StripSuffix(string n)
    {
        int dot = n.LastIndexOf('.');
        return dot > 0 && int.TryParse(n.Substring(dot + 1), out _) ? n.Substring(0, dot) : n;
    }

    static string MaterialKeyFor(MeshRenderer r)
    {
        var mf = r.GetComponent<MeshFilter>();
        foreach (string name in new[] { mf && mf.sharedMesh ? mf.sharedMesh.name : "", r.gameObject.name })
        {
            string n = StripSuffix(name);
            foreach (var (prefix, key) in MeshToMaterial)
                if (n.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) return key;
        }
        return null;
    }

    static GameObject FindRoot()
    {
        for (int i = 0; i < UnityEngine.SceneManagement.SceneManager.sceneCount; i++)
        {
            var sc = UnityEngine.SceneManagement.SceneManager.GetSceneAt(i);
            if (!sc.isLoaded) continue;
            foreach (var go in sc.GetRootGameObjects())
                if (go.name == RootName) return go;
        }
        return null;
    }

    static int CountMissingMaterials(GameObject root)
    {
        int missing = 0;
        foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
        {
            var m = r.sharedMaterials;
            if (m.Length == 0 || m.Any(x => x == null)) missing++;
        }
        return missing;
    }

    [MenuItem("Tools/Branson Backdrop/Rebuild In Open Scene (and save prefab)")]
    public static void Rebuild()
    {
        AssetDatabase.Refresh();
        var old = FindRoot();
        if (old != null) UnityEngine.Object.DestroyImmediate(old);

        var root = new GameObject(RootName);
        root.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);

        var glbs = Directory.GetFiles(ModelDir, "Branson_*.glb").Select(p => p.Replace('\\', '/')).OrderBy(p => p).ToList();
        int meshes = 0, tris = 0, unmapped = 0;
        foreach (string path in glbs)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (asset == null) { Debug.LogWarning($"[Branson] could not load {path}"); continue; }
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(asset);
            PrefabUtility.UnpackPrefabInstance(inst, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            inst.name = Path.GetFileNameWithoutExtension(path);
            inst.transform.SetParent(root.transform, false);
            foreach (var r in inst.GetComponentsInChildren<MeshRenderer>(true))
            {
                string key = MaterialKeyFor(r);
                if (key == null) { unmapped++; Debug.LogWarning($"[Branson] no material rule for '{r.name}' ({path})"); continue; }
                var mat = GetOrCreateMaterial(key);
                SyncSky(mat);
                r.sharedMaterials = Enumerable.Repeat(mat, Math.Max(1, r.sharedMaterials.Length)).ToArray();
                r.shadowCastingMode = ShadowCastingMode.Off;
                r.receiveShadows = false;
                r.lightProbeUsage = LightProbeUsage.Off;
                r.reflectionProbeUsage = ReflectionProbeUsage.Off;
                r.motionVectorGenerationMode = MotionVectorGenerationMode.ForceNoMotion;
                r.allowOcclusionWhenDynamic = false;
                var mf = r.GetComponent<MeshFilter>();
                if (mf && mf.sharedMesh)
                {
                    meshes++;
                    for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) tris += (int)(mf.sharedMesh.GetIndexCount(s) / 3);
                }
            }
        }

        if (!AssetDatabase.IsValidFolder("Assets/Prefabs")) AssetDatabase.CreateFolder("Assets", "Prefabs");
        PrefabUtility.SaveAsPrefabAssetAndConnect(root, PrefabPath, InteractionMode.AutomatedAction);
        AssetDatabase.SaveAssets();
        // re-import so the prefab asset resolves the (possibly just created) materials, then verify the scene instance
        AssetDatabase.ImportAsset(PrefabPath, ImportAssetOptions.ForceUpdate);
        int missing = CountMissingMaterials(root);
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(root.scene);
        string msg = $"[Branson] assembled {glbs.Count} glb(s): {meshes} mesh(es), {tris:N0} triangles, {unmapped} unmapped, {missing} renderer(s) with missing materials. Prefab: {PrefabPath}";
        if (missing > 0) Debug.LogError(msg + "  -> run Tools/Branson Backdrop/Rebuild again after Unity finishes importing.");
        else Debug.Log(msg);
    }

    [MenuItem("Tools/Branson Backdrop/Sync Sky From Scene Skybox")]
    public static void SyncSkyMenu()
    {
        int n = 0;
        foreach (string guid in AssetDatabase.FindAssets("t:Material", new[] { MatDir }))
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(guid));
            if (m != null && m.HasProperty("_SkyTex")) { SyncSky(m); n++; }
        }
        AssetDatabase.SaveAssets();
        Debug.Log($"[Branson] synced the sky (haze colour + river reflection) of {n} material(s) from skybox '{(RenderSettings.skybox ? RenderSettings.skybox.name : "none")}'.");
    }

    [MenuItem("Tools/Branson Backdrop/Select Backdrop Root")]
    public static void SelectRoot()
    {
        var r = FindRoot();
        if (r != null) Selection.activeGameObject = r;
    }
}
#endif
