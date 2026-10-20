using UnityEngine;
using UnityEngine.UIElements;

namespace SimPC.Computer
{
    /// <summary>
    /// Unity 2021.3 has no world-space UI Toolkit, so the panel is rendered into a RenderTexture (see the PanelSettings
    /// asset) that is shown on this object's quad. This component maps the mouse pointer through that quad into panel
    /// coordinates so the EventSystem can click the UI.
    /// </summary>
    [RequireComponent(typeof(UIDocument), typeof(MeshCollider))]
    public sealed class ComputerScreen : MonoBehaviour
    {
        PanelSettings settings;
        MeshCollider screenCollider;

        /// <summary>The camera the pointer is cast from. While null the screen ignores the mouse entirely.</summary>
        public Camera PointerCamera { get; set; }

        void OnEnable()
        {
            settings = GetComponent<UIDocument>().panelSettings;
            screenCollider = GetComponent<MeshCollider>();
            if (settings != null) settings.SetScreenToPanelSpaceFunction(ScreenToPanel);
        }

        void OnDisable()
        {
            if (settings != null) settings.SetScreenToPanelSpaceFunction(null);
        }

        Vector2 ScreenToPanel(Vector2 screenPosition)
        {
            var miss = new Vector2(float.NaN, float.NaN);
            if (PointerCamera == null || settings.targetTexture == null) return miss;

            // UI Toolkit hands over screen positions with a top-left origin; cameras expect bottom-left.
            screenPosition.y = Screen.height - screenPosition.y;
            var ray = PointerCamera.ScreenPointToRay(screenPosition);
            if (!screenCollider.Raycast(ray, out var hit, float.MaxValue)) return miss;

            var uv = hit.textureCoord;
            var texture = settings.targetTexture;
            return new Vector2(uv.x * texture.width, (1f - uv.y) * texture.height);
        }
    }
}
