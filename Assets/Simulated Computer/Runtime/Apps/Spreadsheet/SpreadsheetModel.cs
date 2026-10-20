using System;
using System.Globalization;

namespace SimPC.Computer
{
    /// <summary>
    /// The data behind the spreadsheet: a fixed grid of text cells. The view only edits it through <see cref="Set"/>,
    /// so anything else (game logic, validation, saving) can read or watch the same model.
    /// </summary>
    public sealed class SpreadsheetModel
    {
        readonly string[,] cells;
        readonly string[] columnTitles;

        public int Rows { get; }
        public int Columns { get; }

        /// <summary>Raised with (row, column) after a cell's text actually changed.</summary>
        public event Action<int, int> CellChanged;

        /// <param name="columnTitles">Optional header names; missing ones fall back to A, B, C...</param>
        public SpreadsheetModel(int rows, int columns, string[] columnTitles = null)
        {
            if (rows < 1) throw new ArgumentOutOfRangeException(nameof(rows));
            if (columns < 1) throw new ArgumentOutOfRangeException(nameof(columns));

            Rows = rows;
            Columns = columns;
            cells = new string[rows, columns];
            this.columnTitles = new string[columns];
            for (var c = 0; c < columns; c++)
            {
                var custom = columnTitles != null && c < columnTitles.Length ? columnTitles[c] : null;
                this.columnTitles[c] = string.IsNullOrEmpty(custom) ? ColumnLetters(c) : custom;
            }
        }

        public string ColumnTitle(int column) => columnTitles[column];

        public string Get(int row, int column) => cells[row, column] ?? string.Empty;

        public void Set(int row, int column, string value)
        {
            value = value ?? string.Empty;
            if (cells[row, column] == value || (string.IsNullOrEmpty(cells[row, column]) && value.Length == 0)) return;
            cells[row, column] = value;
            CellChanged?.Invoke(row, column);
        }

        public bool TryGetNumber(int row, int column, out double number) =>
            double.TryParse(Get(row, column), NumberStyles.Float, CultureInfo.InvariantCulture, out number);

        /// <summary>"A1"-style address of a cell.</summary>
        public static string Address(int row, int column) => ColumnLetters(column) + (row + 1);

        public static string ColumnLetters(int column)
        {
            var letters = string.Empty;
            do
            {
                letters = (char)('A' + column % 26) + letters;
                column = column / 26 - 1;
            } while (column >= 0);
            return letters;
        }
    }
}
