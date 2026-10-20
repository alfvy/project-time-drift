using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;

namespace SimPC.Computer
{
    /// <summary>Add this to the Desktop's GameObject to contribute apps.</summary>
    public interface IAppProvider
    {
        void RegisterApps(AppRegistry registry);
    }

    public sealed class AppRegistry
    {
        readonly List<ComputerApp> apps = new List<ComputerApp>();
        readonly Dictionary<string, ComputerApp> byId = new Dictionary<string, ComputerApp>();

        public IReadOnlyList<ComputerApp> Apps => apps;
        public event Action<ComputerApp> Registered;

        public void Register(ComputerApp app)
        {
            if (app == null) throw new ArgumentNullException(nameof(app));
            if (byId.ContainsKey(app.Id))
            {
                Debug.LogWarning($"[Computer] An app with id '{app.Id}' is already registered.");
                return;
            }
            byId.Add(app.Id, app);
            apps.Add(app);
            Registered?.Invoke(app);
        }

        public bool TryGet(string id, out ComputerApp app) => byId.TryGetValue(id, out app);

        /// <summary>Builds the small coloured badge (or texture) used in the start menu, taskbar and title bars.</summary>
        public static void ApplyIcon(VisualElement icon, ComputerApp app)
        {
            var letter = icon.Q<Label>(className: "app-icon__letter");
            if (app.Icon != null)
            {
                icon.style.backgroundImage = new StyleBackground(app.Icon);
                if (letter != null) letter.style.display = DisplayStyle.None;
                return;
            }
            icon.style.backgroundColor = app.IconColor;
            if (letter != null) letter.text = app.IconLetter;
        }
    }
}
