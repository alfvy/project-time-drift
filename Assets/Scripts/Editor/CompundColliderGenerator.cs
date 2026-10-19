using UnityEngine;
using UnityEditor;
using System.Collections.Generic;
using System.Linq;

public class CompoundColliderGenerator : EditorWindow
{
    public GameObject targetObject;
    [Range(1, 15)] public int density = 5;
    public bool mergeColliders = true;

    [MenuItem("Tools/Physics/Optimized Compound Gen")]
    public static void ShowWindow() => GetWindow<CompoundColliderGenerator>("Phys Optimizer");

    void OnGUI()
    {
        targetObject = (GameObject)EditorGUILayout.ObjectField("Target Object", targetObject, typeof(GameObject), true);
        density = EditorGUILayout.IntSlider("Density", density, 1, 15);
        mergeColliders = EditorGUILayout.Toggle("Merge Adjacent", mergeColliders);

        if (GUILayout.Button("Generate & Optimize") && targetObject != null)
        {
            GenerateOptimized();
        }
    }

    void GenerateOptimized()
    {
        // 1. Prepare for Physics Checks
        // We need a MeshCollider temporarily to use Physics.OverlapBox accurately
        var existingColliders = targetObject.GetComponents<Collider>();
        foreach (var c in existingColliders) DestroyImmediate(c);

        MeshFilter[] filters = targetObject.GetComponentsInChildren<MeshFilter>();
        List<MeshCollider> temps = new List<MeshCollider>();
        foreach (var f in filters)
        {
            if (!f.GetComponent<MeshCollider>())
                temps.Add(f.gameObject.AddComponent<MeshCollider>());
        }

        // 2. Setup Grid
        Bounds worldBounds = filters[0].GetComponent<Renderer>().bounds;
        foreach (var f in filters) worldBounds.Encapsulate(f.GetComponent<Renderer>().bounds);

        Vector3 step = worldBounds.size / density;
        Vector3 globalScale = targetObject.transform.lossyScale;
        List<Bounds> activeCells = new List<Bounds>();

        // 3. Precision Intersection Check
        for (int x = 0; x < density; x++)
        {
            for (int y = 0; y < density; y++)
            {
                for (int z = 0; z < density; z++)
                {
                    Vector3 center = worldBounds.min + new Vector3(step.x * (x + 0.5f), step.y * (y + 0.5f), step.z * (z + 0.5f));
                    // Physics.CheckBox is the secret for true mesh intersection
                    if (Physics.CheckBox(center, step * 0.49f, Quaternion.identity, ~0, QueryTriggerInteraction.Ignore))
                    {
                        activeCells.Add(new Bounds(center, step));
                    }
                }
            }
        }

        // 4. Clean up temporary MeshColliders
        foreach (var t in temps) DestroyImmediate(t);

        // 5. Merging (Greedy X-Axis Merge)
        // A simple but effective optimization: merge along the X axis if they touch
        if (mergeColliders && activeCells.Count > 1)
        {
            activeCells = PerformMerge(activeCells, step);
        }

        // 6. Finalize Box Colliders
        foreach (var cell in activeCells)
        {
            BoxCollider box = targetObject.AddComponent<BoxCollider>();
            box.center = targetObject.transform.InverseTransformPoint(cell.center);
            box.size = new Vector3(
                cell.size.x / Mathf.Abs(globalScale.x),
                cell.size.y / Mathf.Abs(globalScale.y),
                cell.size.z / Mathf.Abs(globalScale.z)
            );
        }

        Debug.Log($"Created {activeCells.Count} optimized colliders.");
    }

    List<Bounds> PerformMerge(List<Bounds> cells, Vector3 step)
    {
        // Sort cells to make neighbor detection easier
        cells = cells.OrderBy(c => c.center.z).ThenBy(c => c.center.y).ThenBy(c => c.center.x).ToList();
        List<Bounds> merged = new List<Bounds>();

        while (cells.Count > 0)
        {
            Bounds current = cells[0];
            cells.RemoveAt(0);

            // Look for neighbors specifically on the X axis that have same Y and Z
            while (true)
            {
                int neighborIndex = cells.FindIndex(c =>
                    Mathf.Approximately(c.center.y, current.center.y) &&
                    Mathf.Approximately(c.center.z, current.center.z) &&
                    Mathf.Abs(c.center.x - current.center.x) <= step.x + 0.01f);

                if (neighborIndex != -1)
                {
                    Bounds neighbor = cells[neighborIndex];
                    // Combine them
                    float newMinX = Mathf.Min(current.min.x, neighbor.min.x);
                    float newMaxX = Mathf.Max(current.max.x, neighbor.max.x);
                    Vector3 newCenter = current.center;
                    newCenter.x = (newMinX + newMaxX) / 2f;
                    Vector3 newSize = current.size;
                    newSize.x = newMaxX - newMinX;

                    current.center = newCenter;
                    current.size = newSize;
                    cells.RemoveAt(neighborIndex);
                }
                else break;
            }
            merged.Add(current);
        }
        return merged;
    }
}