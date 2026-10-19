using UnityEngine;
using UnityEditor;

public class ColliderUtils : Editor
{
    [MenuItem("Tools/Physics/Wrap Selection in Box")]
    public static void WrapInBox()
    {
        GameObject target = Selection.activeGameObject;
        if (target == null) return;

        // Reset or add Box Collider
        BoxCollider box = target.GetComponent<BoxCollider>();
        if (box == null) box = target.AddComponent<BoxCollider>();

        Bounds bounds = new Bounds(Vector3.zero, Vector3.zero);
        bool boundsInitialized = false;

        // Calculate bounds of all children
        Renderer[] renderers = target.GetComponentsInChildren<Renderer>();
        foreach (Renderer r in renderers)
        {
            if (!boundsInitialized)
            {
                bounds = r.bounds;
                boundsInitialized = true;
            }
            else
            {
                bounds.Encapsulate(r.bounds);
            }
        }

        if (boundsInitialized)
        {
            // Convert world bounds to local space
            box.center = target.transform.InverseTransformPoint(bounds.center);
            box.size = target.transform.InverseTransformVector(bounds.size);

            // Fix for negative scaling
            box.size = new Vector3(Mathf.Abs(box.size.x), Mathf.Abs(box.size.y), Mathf.Abs(box.size.z));
        }
    }
}