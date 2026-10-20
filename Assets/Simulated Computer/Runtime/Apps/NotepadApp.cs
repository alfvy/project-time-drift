using UnityEngine;
using UnityEngine.UIElements;

namespace SimPC.Computer
{
    public sealed class NotepadApp : ComputerApp
    {
        public override string Id => "notepad";
        public override string Title => "Notepad";
        public override string IconLetter => "N";
        public override Color IconColor => new Color32(70, 150, 220, 255);
        public override Vector2 DefaultSize => new Vector2(460, 320);

        public override VisualElement CreateContent(ComputerWindow window)
        {
            var root = new VisualElement();
            root.AddToClassList("notepad");

            var text = new TextField { multiline = true };
            text.AddToClassList("notepad__text");
            root.Add(text);
            return root;
        }
    }
}
