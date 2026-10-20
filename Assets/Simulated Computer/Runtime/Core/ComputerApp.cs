using UnityEngine;
using UnityEngine.UIElements;

namespace SimPC.Computer
{
    /// <summary>
    /// An application that can be launched from the start menu. Subclass it, build the window
    /// content in <see cref="CreateContent"/>, and register it through an <see cref="IAppProvider"/>.
    /// </summary>
    public abstract class ComputerApp
    {
        public abstract string Id { get; }
        public abstract string Title { get; }

        /// <summary>Letter shown on the icon badge when <see cref="Icon"/> is null.</summary>
        public virtual string IconLetter => string.IsNullOrEmpty(Title) ? "?" : Title.Substring(0, 1);
        public virtual Color IconColor => new Color32(0, 84, 227, 255);
        public virtual Texture2D Icon => null;

        public virtual Vector2 DefaultSize => new Vector2(420, 300);
        public virtual Vector2 MinSize => new Vector2(220, 140);

        /// <summary>When true, launching the app again focuses the open window instead of making a new one.</summary>
        public virtual bool SingleInstance => false;

        public abstract VisualElement CreateContent(ComputerWindow window);
    }
}
