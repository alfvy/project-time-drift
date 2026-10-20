using UnityEngine;
using UnityEngine.UIElements;

namespace SimPC.Computer
{
    /// <summary>
    /// A bare-bones data-entry spreadsheet. The app instance owns the <see cref="Model"/>, so what was typed
    /// survives closing and reopening the window.
    /// </summary>
    public sealed class SpreadsheetApp : ComputerApp
    {
        public SpreadsheetModel Model { get; }

        public SpreadsheetApp(SpreadsheetModel model = null)
        {
            Model = model ?? new SpreadsheetModel(40, 8);
        }

        public override string Id => "spreadsheet";
        public override string Title => "Spreadsheet";
        public override string IconLetter => "S";
        public override Color IconColor => new Color32(40, 140, 70, 255);
        public override Vector2 DefaultSize => new Vector2(560, 380);
        public override Vector2 MinSize => new Vector2(300, 200);
        public override bool SingleInstance => true;

        public override VisualElement CreateContent(ComputerWindow window) => new SpreadsheetView(Model);
    }
}
