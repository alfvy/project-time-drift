using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;

namespace SimPC.Computer
{
    /// <summary>Owns every open window: creation, z-order, focus and minimize/maximize/close.</summary>
    public sealed class WindowManager
    {
        const float CascadeStep = 28f;
        const int CascadeCount = 8;

        readonly VisualElement layer;
        readonly VisualTreeAsset windowTemplate;
        readonly List<ComputerWindow> windows = new List<ComputerWindow>();
        int opened;

        public IReadOnlyList<ComputerWindow> Windows => windows;
        public ComputerWindow Active { get; private set; }

        public event Action<ComputerWindow> WindowOpened;
        public event Action<ComputerWindow> WindowClosed;
        public event Action<ComputerWindow> WindowStateChanged;
        public event Action<ComputerWindow> ActiveChanged;

        public WindowManager(VisualElement layer, VisualTreeAsset windowTemplate)
        {
            this.layer = layer;
            this.windowTemplate = windowTemplate;
        }

        public ComputerWindow Open(ComputerApp app)
        {
            if (app.SingleInstance)
            {
                var existing = windows.Find(w => w.App == app);
                if (existing != null)
                {
                    Restore(existing);
                    return existing;
                }
            }

            var offset = 24f + CascadeStep * (opened++ % CascadeCount);
            var window = new ComputerWindow(app, this, windowTemplate, new Vector2(offset, offset));
            windows.Add(window);
            layer.Add(window.Root);
            WindowOpened?.Invoke(window);
            Focus(window);
            return window;
        }

        public void Close(ComputerWindow window)
        {
            if (!windows.Remove(window)) return;
            window.Root.RemoveFromHierarchy();
            window.NotifyClosed();
            WindowClosed?.Invoke(window);
            if (Active != window) return;

            window.SetActive(false);
            Active = null;
            FocusTopmost();
        }

        public void Focus(ComputerWindow window)
        {
            if (window.IsMinimized) window.SetMinimized(false);
            window.Root.BringToFront();
            if (Active == window) return;

            Active?.SetActive(false);
            Active = window;
            window.SetActive(true);
            ActiveChanged?.Invoke(window);
        }

        public void Minimize(ComputerWindow window)
        {
            window.SetMinimized(true);
            WindowStateChanged?.Invoke(window);
            if (Active == window)
            {
                window.SetActive(false);
                Active = null;
                FocusTopmost();
            }
        }

        public void Restore(ComputerWindow window)
        {
            window.SetMinimized(false);
            WindowStateChanged?.Invoke(window);
            Focus(window);
        }

        public void ToggleMaximize(ComputerWindow window)
        {
            window.SetMaximized(!window.IsMaximized);
            WindowStateChanged?.Invoke(window);
        }

        /// <summary>Taskbar button behaviour: restore if hidden, minimize if already active, otherwise focus.</summary>
        public void ToggleFromTaskbar(ComputerWindow window)
        {
            if (window.IsMinimized) Restore(window);
            else if (window == Active) Minimize(window);
            else Focus(window);
        }

        void FocusTopmost()
        {
            ComputerWindow top = null;
            var topIndex = -1;
            foreach (var w in windows)
            {
                if (w.IsMinimized) continue;
                var index = layer.IndexOf(w.Root);
                if (index > topIndex)
                {
                    top = w;
                    topIndex = index;
                }
            }
            if (top != null) Focus(top);
            else ActiveChanged?.Invoke(null);
        }
    }
}
