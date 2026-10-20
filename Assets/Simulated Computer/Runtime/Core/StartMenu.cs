using System;
using UnityEngine.UIElements;

namespace SimPC.Computer
{
    /// <summary>The start button and its pop-up app list. Closes on outside click or after launching an app.</summary>
    public sealed class StartMenu
    {
        const string OpenClass = "start-menu--open";
        const string PressedClass = "start-button--pressed";

        readonly VisualElement menu;
        readonly VisualElement startButton;
        readonly VisualElement appList;
        readonly AppRegistry registry;
        readonly Action<ComputerApp> launch;

        public bool IsOpen { get; private set; }

        public StartMenu(VisualElement desktop, AppRegistry registry, string userName, Action<ComputerApp> launch)
        {
            this.registry = registry;
            this.launch = launch;

            menu = desktop.Q<VisualElement>("start-menu");
            startButton = desktop.Q<VisualElement>("start-button");
            appList = desktop.Q<VisualElement>("start-menu-apps");
            desktop.Q<Label>("start-menu-user").text = userName;

            startButton.RegisterCallback<ClickEvent>(_ => SetOpen(!IsOpen));
            desktop.RegisterCallback<PointerDownEvent>(e =>
            {
                if (!IsOpen) return;
                var target = (VisualElement)e.target;
                if (!menu.Contains(target) && !startButton.Contains(target)) SetOpen(false);
            }, TrickleDown.TrickleDown);

            registry.Registered += _ => Rebuild();
            Rebuild();
        }

        public void SetOpen(bool open)
        {
            IsOpen = open;
            menu.EnableInClassList(OpenClass, open);
            startButton.EnableInClassList(PressedClass, open);
        }

        void Rebuild()
        {
            appList.Clear();
            foreach (var app in registry.Apps)
            {
                var captured = app;
                var item = new VisualElement();
                item.AddToClassList("start-menu__item");

                var icon = new VisualElement { pickingMode = PickingMode.Ignore };
                icon.AddToClassList("app-icon");
                var letter = new Label { pickingMode = PickingMode.Ignore };
                letter.AddToClassList("app-icon__letter");
                icon.Add(letter);
                AppRegistry.ApplyIcon(icon, captured);

                var label = new Label(captured.Title) { pickingMode = PickingMode.Ignore };
                label.AddToClassList("start-menu__item-label");

                item.Add(icon);
                item.Add(label);
                item.RegisterCallback<ClickEvent>(_ =>
                {
                    SetOpen(false);
                    launch(captured);
                });
                appList.Add(item);
            }
        }
    }
}
