using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine.UIElements;

namespace SimPC.Computer
{
    /// <summary>One button per open window, plus the tray clock. The start button lives in <see cref="StartMenu"/>.</summary>
    public sealed class Taskbar
    {
        const string ActiveClass = "task-button--active";

        readonly WindowManager windows;
        readonly VisualElement taskList;
        readonly Label clock;
        readonly Dictionary<ComputerWindow, VisualElement> buttons = new Dictionary<ComputerWindow, VisualElement>();

        /// <summary>Swap this to show in-game time instead of the real clock.</summary>
        public Func<DateTime> TimeSource { get; set; } = () => DateTime.Now;

        public Taskbar(VisualElement root, WindowManager windows)
        {
            this.windows = windows;
            taskList = root.Q<VisualElement>("task-list");
            clock = root.Q<Label>("clock");

            windows.WindowOpened += AddButton;
            windows.WindowClosed += RemoveButton;
            windows.ActiveChanged += _ => RefreshActive();

            RefreshClock();
            clock.schedule.Execute(RefreshClock).Every(1000);
        }

        void AddButton(ComputerWindow window)
        {
            var button = new VisualElement();
            button.AddToClassList("task-button");

            var icon = new VisualElement();
            icon.AddToClassList("app-icon");
            icon.AddToClassList("app-icon--small");
            var letter = new Label { pickingMode = PickingMode.Ignore };
            letter.AddToClassList("app-icon__letter");
            icon.Add(letter);
            AppRegistry.ApplyIcon(icon, window.App);
            icon.pickingMode = PickingMode.Ignore;

            var label = new Label(window.Title) { pickingMode = PickingMode.Ignore };
            label.AddToClassList("task-button__label");
            window.TitleChanged += w => label.text = w.Title;

            button.Add(icon);
            button.Add(label);
            button.RegisterCallback<ClickEvent>(_ => windows.ToggleFromTaskbar(window));

            buttons[window] = button;
            taskList.Add(button);
        }

        void RemoveButton(ComputerWindow window)
        {
            if (!buttons.TryGetValue(window, out var button)) return;
            buttons.Remove(window);
            button.RemoveFromHierarchy();
        }

        void RefreshActive()
        {
            foreach (var pair in buttons)
                pair.Value.EnableInClassList(ActiveClass, pair.Key == windows.Active);
        }

        void RefreshClock() => clock.text = TimeSource().ToString("h:mm tt", CultureInfo.InvariantCulture);
    }
}
