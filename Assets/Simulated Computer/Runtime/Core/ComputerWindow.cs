using System;
using UnityEngine;
using UnityEngine.UIElements;

namespace SimPC.Computer
{
    /// <summary>
    /// One window on the desktop: title bar chrome, dragging, resizing and a content area owned by an app.
    /// State changes (focus, minimize, maximize, close) go through the <see cref="WindowManager"/>.
    /// </summary>
    public sealed class ComputerWindow
    {
        const string ActiveClass = "window--active";
        const string MaximizedClass = "window--maximized";
        const float TitleBarHeight = 26f;
        const float MinVisibleWidth = 80f;

        public ComputerApp App { get; }
        public VisualElement Root { get; }
        public VisualElement Content { get; }

        public bool IsActive { get; private set; }
        public bool IsMinimized { get; private set; }
        public bool IsMaximized { get; private set; }

        public string Title
        {
            get => titleLabel.text;
            set
            {
                titleLabel.text = value;
                TitleChanged?.Invoke(this);
            }
        }

        public event Action<ComputerWindow> TitleChanged;
        public event Action<ComputerWindow> Closed;

        readonly WindowManager manager;
        readonly Label titleLabel;
        Rect restoreRect;

        internal ComputerWindow(ComputerApp app, WindowManager manager, VisualTreeAsset template, Vector2 position)
        {
            App = app;
            this.manager = manager;

            Root = template.Instantiate().Q<VisualElement>("window");
            Root.RemoveFromHierarchy();
            Root.style.left = position.x;
            Root.style.top = position.y;
            Root.style.width = app.DefaultSize.x;
            Root.style.height = app.DefaultSize.y;

            titleLabel = Root.Q<Label>("title");
            titleLabel.text = app.Title;
            Content = Root.Q<VisualElement>("content");
            AppRegistry.ApplyIcon(Root.Q<VisualElement>("icon"), app);

            var titleBar = Root.Q<VisualElement>("titlebar");
            var buttons = Root.Q<VisualElement>("buttons");

            Root.RegisterCallback<PointerDownEvent>(_ => manager.Focus(this), TrickleDown.TrickleDown);
            Root.Q<VisualElement>("btn-minimize").RegisterCallback<ClickEvent>(_ => manager.Minimize(this));
            Root.Q<VisualElement>("btn-maximize").RegisterCallback<ClickEvent>(_ => manager.ToggleMaximize(this));
            Root.Q<VisualElement>("btn-close").RegisterCallback<ClickEvent>(_ => manager.Close(this));

            titleBar.RegisterCallback<PointerDownEvent>(e =>
            {
                if (e.button == 0 && e.clickCount == 2 && !buttons.Contains((VisualElement)e.target))
                    manager.ToggleMaximize(this);
            });

            var dragStart = Vector2.zero;
            MakeDraggable(titleBar,
                canStart: e => !IsMaximized && !buttons.Contains((VisualElement)e.target),
                begin: () => dragStart = new Vector2(Root.resolvedStyle.left, Root.resolvedStyle.top),
                drag: delta => MoveTo(dragStart + delta));

            var sizeStart = Vector2.zero;
            MakeDraggable(Root.Q<VisualElement>("resize-grip"),
                canStart: _ => !IsMaximized,
                begin: () => sizeStart = new Vector2(Root.resolvedStyle.width, Root.resolvedStyle.height),
                drag: delta => ResizeTo(sizeStart + delta));

            Content.Add(app.CreateContent(this));
        }

        public void Close() => manager.Close(this);

        internal void NotifyClosed() => Closed?.Invoke(this);

        internal void SetActive(bool active)
        {
            IsActive = active;
            Root.EnableInClassList(ActiveClass, active);
        }

        internal void SetMinimized(bool minimized)
        {
            IsMinimized = minimized;
            Root.style.display = minimized ? DisplayStyle.None : DisplayStyle.Flex;
        }

        internal void SetMaximized(bool maximized)
        {
            if (maximized == IsMaximized) return;
            IsMaximized = maximized;
            Root.EnableInClassList(MaximizedClass, maximized);

            if (maximized)
            {
                restoreRect = new Rect(Root.resolvedStyle.left, Root.resolvedStyle.top,
                    Root.resolvedStyle.width, Root.resolvedStyle.height);
                Root.style.left = 0;
                Root.style.top = 0;
                Root.style.width = Length.Percent(100);
                Root.style.height = Length.Percent(100);
            }
            else
            {
                Root.style.left = restoreRect.x;
                Root.style.top = restoreRect.y;
                Root.style.width = restoreRect.width;
                Root.style.height = restoreRect.height;
            }
        }

        void MoveTo(Vector2 position)
        {
            var bounds = Root.parent?.layout ?? default;
            position.x = Mathf.Clamp(position.x, MinVisibleWidth - Root.resolvedStyle.width, bounds.width - MinVisibleWidth);
            position.y = Mathf.Clamp(position.y, 0f, Mathf.Max(0f, bounds.height - TitleBarHeight));
            Root.style.left = position.x;
            Root.style.top = position.y;
        }

        void ResizeTo(Vector2 size)
        {
            var bounds = Root.parent?.layout ?? default;
            size.x = Mathf.Clamp(size.x, App.MinSize.x, Mathf.Max(App.MinSize.x, bounds.width - Root.resolvedStyle.left));
            size.y = Mathf.Clamp(size.y, App.MinSize.y, Mathf.Max(App.MinSize.y, bounds.height - Root.resolvedStyle.top));
            Root.style.width = size.x;
            Root.style.height = size.y;
        }

        /// <summary>
        /// Pointer positions are in panel space, which for a world-space panel is not layout pixels.
        /// Converting through the parent's WorldToLocal keeps drag deltas in layout pixels.
        /// </summary>
        Vector2 ToLayer(Vector3 panelPosition) => Root.parent.WorldToLocal(panelPosition);

        void MakeDraggable(VisualElement handle, Func<PointerDownEvent, bool> canStart,
            Action begin, Action<Vector2> drag)
        {
            var pointer = -1;
            var origin = Vector2.zero;

            handle.RegisterCallback<PointerDownEvent>(e =>
            {
                if (e.button != 0 || pointer != -1 || !canStart(e)) return;
                pointer = e.pointerId;
                origin = ToLayer(e.position);
                begin();
                handle.CapturePointer(pointer);
                e.StopPropagation();
            });
            handle.RegisterCallback<PointerMoveEvent>(e =>
            {
                if (e.pointerId == pointer && handle.HasPointerCapture(pointer))
                    drag(ToLayer(e.position) - origin);
            });
            handle.RegisterCallback<PointerUpEvent>(e =>
            {
                if (e.pointerId != pointer) return;
                handle.ReleasePointer(pointer);
                pointer = -1;
            });
            handle.RegisterCallback<PointerCaptureOutEvent>(_ => pointer = -1);
        }
    }
}
