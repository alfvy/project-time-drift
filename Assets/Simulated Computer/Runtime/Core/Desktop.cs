using UnityEngine;
using UnityEngine.UIElements;

namespace SimPC.Computer
{
    /// <summary>
    /// Entry point of the simulated computer. Lives on the world-space UIDocument's GameObject,
    /// builds the shell (windows, taskbar, start menu) and collects apps from every <see cref="IAppProvider"/> next to it.
    /// </summary>
    [RequireComponent(typeof(UIDocument))]
    public sealed class Desktop : MonoBehaviour
    {
        [SerializeField] VisualTreeAsset windowTemplate;
        [SerializeField] string userName = "Player";

        public AppRegistry Apps { get; private set; }
        public WindowManager Windows { get; private set; }
        public Taskbar Taskbar { get; private set; }
        public StartMenu StartMenu { get; private set; }

        void OnEnable()
        {
            var root = GetComponent<UIDocument>().rootVisualElement;
            var desktop = root.Q<VisualElement>("desktop");
            if (desktop == null)
            {
                Debug.LogError("[Computer] Desktop.uxml is not assigned to the UIDocument.", this);
                return;
            }

            Apps = new AppRegistry();
            Windows = new WindowManager(desktop.Q<VisualElement>("window-layer"), windowTemplate);
            Taskbar = new Taskbar(desktop.Q<VisualElement>("taskbar"), Windows);
            StartMenu = new StartMenu(desktop, Apps, userName, app => Windows.Open(app));

            foreach (var provider in GetComponents<IAppProvider>())
                provider.RegisterApps(Apps);
        }
    }
}
