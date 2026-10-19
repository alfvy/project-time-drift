using UnityEngine;
using UnityEditor;
using System.IO;
using UnityEngine.SceneManagement;

public class LightCookieGenerator : EditorWindow
{
    public Light targetLight;
    public int resolution = 512;
    public Shader depthShader;

    [MenuItem("Tools/Light Cookie Creator")]
    public static void ShowWindow() => GetWindow<LightCookieGenerator>("Cookie Creator");

    void OnEnable()
    {
        if (depthShader == null) depthShader = Shader.Find("Hidden/DepthCookie");
    }

    void OnGUI()
    {
        targetLight = (Light)EditorGUILayout.ObjectField("Target Light", targetLight, typeof(Light), true);
        resolution = EditorGUILayout.IntField("Resolution", resolution);
        depthShader = (Shader)EditorGUILayout.ObjectField("Depth Shader", depthShader, typeof(Shader), false);

        if (GUILayout.Button("Capture Depth Cookie") && targetLight != null)
        {
            if (targetLight.type == LightType.Spot) CaptureSpotCookie();
            else if (targetLight.type == LightType.Point) CapturePointCookie();
            else Debug.LogError("Please use a Spot or Point light.");
        }
    }

    // --- SPOT LIGHT (2D PNG) ---
    void CaptureSpotCookie()
    {
        targetLight.cookie = null;
        string path = GetSavePath(".png");
        GameObject camGO = CreateCookieCam();
        Camera cam = camGO.GetComponent<Camera>();

        RenderTexture rt = RenderTexture.GetTemporary(resolution, resolution, 24);
        cam.targetTexture = rt;
        cam.RenderWithShader(depthShader, "RenderType");

        RenderTexture.active = rt;
        Texture2D tex = new Texture2D(resolution, resolution, TextureFormat.R8, false); // R8 is enough for depth
        tex.ReadPixels(new Rect(0, 0, resolution, resolution), 0, 0);
        tex.Apply();

        File.WriteAllBytes(path, tex.EncodeToPNG());
        AssetDatabase.Refresh();

        // Configure Importer
        TextureImporter importer = AssetImporter.GetAtPath(path) as TextureImporter;
        if (importer != null)
        {
            importer.textureType = TextureImporterType.Cookie;
            importer.alphaSource = TextureImporterAlphaSource.FromGrayScale;
            importer.SaveAndReimport();
        }

        targetLight.cookie = AssetDatabase.LoadAssetAtPath<Texture>(path);
        Cleanup(camGO, rt);
    }

    // --- POINT LIGHT (Cubemap Asset) ---
    void CapturePointCookie()
    {
        targetLight.cookie = null;
        string path = GetSavePath(".cubemap");
        GameObject camGO = CreateCookieCam();
        Camera cam = camGO.GetComponent<Camera>();
        cam.fieldOfView = 90f; // Required for cubemap tiling

        // Use a RenderToCubemap approach with our depth shader
        Cubemap cb = new Cubemap(resolution, TextureFormat.R8, false);

        // We have to manually set the replacement shader for the cubemap render
        cam.SetReplacementShader(depthShader, "RenderType");
        cam.RenderToCubemap(cb);
        cam.ResetReplacementShader();

        // Save as a native Unity asset
        AssetDatabase.CreateAsset(cb, path);
        AssetDatabase.SaveAssets();

        targetLight.cookie = AssetDatabase.LoadAssetAtPath<Texture>(path);
        Cleanup(camGO, null);
    }

    // --- HELPERS ---
    GameObject CreateCookieCam()
    {
        GameObject go = new GameObject("TempCookieCam");
        Camera cam = go.AddComponent<Camera>();
        cam.transform.position = targetLight.transform.position;
        cam.transform.rotation = targetLight.transform.rotation;
        cam.farClipPlane = targetLight.range;
        cam.nearClipPlane = 0.01f;
        cam.aspect = 1f;
        cam.backgroundColor = Color.white;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.enabled = false;
        if (targetLight.type == LightType.Spot) cam.fieldOfView = targetLight.spotAngle;
        return go;
    }

    string GetSavePath(string extension)
    {
        string dir = "Assets/Textures/Light Cookies";
        if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
        return $"{dir}/{SceneManager.GetActiveScene().name}-{targetLight.gameObject.name}{extension}";
    }

    void Cleanup(GameObject camGO, RenderTexture rt)
    {
        if (rt != null) RenderTexture.ReleaseTemporary(rt);
        DestroyImmediate(camGO);
        AssetDatabase.Refresh();
        Debug.Log("Cookie Generated Successfully.");
    }
}