using UnityEngine;

namespace SimPC.Computer
{
    /// <summary>Registers the built-in apps. Add your own provider component to ship more.</summary>
    public sealed class DefaultApps : MonoBehaviour, IAppProvider
    {
        /// <summary>Exposed so game code can read the entered data (see <see cref="SpreadsheetApp.Model"/>).</summary>
        public SpreadsheetApp Spreadsheet { get; } = new SpreadsheetApp();

        public void RegisterApps(AppRegistry registry)
        {
            registry.Register(Spreadsheet);
            registry.Register(new NotepadApp());
            registry.Register(new AboutApp());
        }
    }
}
