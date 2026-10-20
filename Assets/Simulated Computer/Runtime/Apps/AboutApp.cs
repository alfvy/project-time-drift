using UnityEngine;
using UnityEngine.UIElements;

namespace SimPC.Computer
{
    public sealed class AboutApp : ComputerApp
    {
        public override string Id => "about";
        public override string Title => "About This Computer";
        public override string IconLetter => "i";
        public override Color IconColor => new Color32(56, 148, 56, 255);
        public override Vector2 DefaultSize => new Vector2(340, 200);
        public override bool SingleInstance => true;

        public override VisualElement CreateContent(ComputerWindow window)
        {
            var root = new VisualElement();
            root.AddToClassList("about");

            var name = new Label("SimPC");
            name.AddToClassList("about__name");
            root.Add(name);
            root.Add(new Label("Version 0.1"));
            root.Add(new Label("A tiny simulated computer."));
            return root;
        }
    }
}
