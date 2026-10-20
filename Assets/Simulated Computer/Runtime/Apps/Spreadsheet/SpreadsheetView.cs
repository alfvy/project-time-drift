using System;
using UnityEngine;
using UnityEngine.UIElements;

namespace SimPC.Computer
{
    /// <summary>
    /// Grid view for a <see cref="SpreadsheetModel"/>. One cell is selected at a time; a single shared text field is
    /// moved over the selected cell for editing, so the grid stays cheap however many cells it has.
    ///
    /// Keys: arrows / Tab move, typing starts an edit, Enter or F2 edits the current text, Delete clears.
    /// While editing: Enter commits and moves down, Tab commits and moves right, Esc cancels.
    /// </summary>
    public sealed class SpreadsheetView : VisualElement
    {
        const float RowHeight = 22f;
        const float HeaderHeight = 22f;
        const float RowHeaderWidth = 40f;
        const string SelectedClass = "sheet__cell--selected";
        const string ActiveHeadClass = "sheet__head--active";

        readonly SpreadsheetModel model;
        readonly float columnWidth;
        readonly Label[,] cells;
        readonly Label[] columnHeads;
        readonly Label[] rowHeads;
        readonly ScrollView scroll;
        readonly TextField editor;
        readonly Label address;
        readonly Label preview;

        int row;
        int column;
        int tabAnchor = -1;
        bool editing;

        public int SelectedRow => row;
        public int SelectedColumn => column;
        public bool IsEditing => editing;
        public event Action<int, int> SelectionChanged;

        public SpreadsheetView(SpreadsheetModel model, float columnWidth = 96f)
        {
            this.model = model;
            this.columnWidth = columnWidth;
            cells = new Label[model.Rows, model.Columns];
            columnHeads = new Label[model.Columns];
            rowHeads = new Label[model.Rows];

            AddToClassList("sheet");
            focusable = true;
            RegisterCallback<KeyDownEvent>(OnKeyDown);

            // Top bar: address of the selected cell and its full text.
            var bar = new VisualElement();
            bar.AddToClassList("sheet__bar");
            address = new Label();
            address.AddToClassList("sheet__address");
            preview = new Label();
            preview.AddToClassList("sheet__preview");
            bar.Add(address);
            bar.Add(preview);
            Add(bar);

            scroll = new ScrollView(ScrollViewMode.VerticalAndHorizontal);
            scroll.AddToClassList("sheet__scroll");
            Add(scroll);

            BuildGrid();

            editor = new TextField();
            editor.AddToClassList("sheet__editor");
            editor.style.display = DisplayStyle.None;
            editor.RegisterCallback<KeyDownEvent>(OnEditorKeyDown, TrickleDown.TrickleDown);
            editor.RegisterCallback<FocusOutEvent>(_ =>
            {
                if (editing) CommitEdit(false);
            });
            scroll.contentContainer.Add(editor);

            model.CellChanged += OnCellChanged;
            RegisterCallback<DetachFromPanelEvent>(_ => model.CellChanged -= OnCellChanged);

            Select(0, 0);
        }

        void BuildGrid()
        {
            var header = NewRow();
            var corner = new Label();
            corner.AddToClassList("sheet__corner");
            corner.style.width = RowHeaderWidth;
            header.Add(corner);
            for (var c = 0; c < model.Columns; c++)
            {
                var head = new Label(model.ColumnTitle(c));
                head.AddToClassList("sheet__colhead");
                head.style.width = columnWidth;
                columnHeads[c] = head;
                header.Add(head);
            }
            scroll.Add(header);

            for (var r = 0; r < model.Rows; r++)
            {
                var line = NewRow();
                var rowHead = new Label((r + 1).ToString());
                rowHead.AddToClassList("sheet__rowhead");
                rowHead.style.width = RowHeaderWidth;
                rowHeads[r] = rowHead;
                line.Add(rowHead);

                for (var c = 0; c < model.Columns; c++)
                {
                    var cell = new Label(model.Get(r, c));
                    cell.AddToClassList("sheet__cell");
                    cell.style.width = columnWidth;
                    var cellRow = r;
                    var cellColumn = c;
                    cell.RegisterCallback<PointerDownEvent>(e =>
                    {
                        if (e.button != 0) return;
                        if (editing) CommitEdit(false);
                        Select(cellRow, cellColumn);
                        Focus();
                        if (e.clickCount == 2) BeginEdit(null);
                    });
                    cells[r, c] = cell;
                    line.Add(cell);
                }
                scroll.Add(line);
            }
        }

        static VisualElement NewRow()
        {
            var line = new VisualElement();
            line.AddToClassList("sheet__row");
            return line;
        }

        // ---- selection -------------------------------------------------------------------------------------

        public void Select(int newRow, int newColumn) => Select(newRow, newColumn, false);

        /// <param name="keepTabAnchor">Tab keeps the anchor so Enter can return to the column the row was started in.</param>
        void Select(int newRow, int newColumn, bool keepTabAnchor)
        {
            if (!keepTabAnchor) tabAnchor = -1;
            newRow = Mathf.Clamp(newRow, 0, model.Rows - 1);
            newColumn = Mathf.Clamp(newColumn, 0, model.Columns - 1);

            cells[row, column].RemoveFromClassList(SelectedClass);
            rowHeads[row].RemoveFromClassList(ActiveHeadClass);
            columnHeads[column].RemoveFromClassList(ActiveHeadClass);

            row = newRow;
            column = newColumn;

            cells[row, column].AddToClassList(SelectedClass);
            rowHeads[row].AddToClassList(ActiveHeadClass);
            columnHeads[column].AddToClassList(ActiveHeadClass);
            RefreshBar();
            scroll.ScrollTo(cells[row, column]);
            SelectionChanged?.Invoke(row, column);
        }

        void Move(int dRow, int dColumn) => Select(row + dRow, column + dColumn, false);

        /// <summary>Tab across a row; the first Tab remembers where the row started.</summary>
        void TabMove(int dColumn)
        {
            var anchor = tabAnchor >= 0 ? tabAnchor : column;
            Select(row, column + dColumn, true);
            tabAnchor = anchor;
        }

        /// <summary>Enter after tabbing across a row goes to the row below, back at the column the row started in.</summary>
        void EnterMove(int dRow)
        {
            var targetColumn = tabAnchor >= 0 ? tabAnchor : column;
            Select(row + dRow, targetColumn, false);
        }

        void RefreshBar()
        {
            address.text = SpreadsheetModel.Address(row, column);
            preview.text = model.Get(row, column);
        }

        void OnCellChanged(int r, int c)
        {
            cells[r, c].text = model.Get(r, c);
            if (r == row && c == column) RefreshBar();
        }

        // ---- editing ---------------------------------------------------------------------------------------

        /// <summary>Starts editing the selected cell. Pass null to keep its text, or text to replace it.</summary>
        void BeginEdit(string replacement)
        {
            if (editing) return;
            editing = true;

            editor.style.left = RowHeaderWidth + column * columnWidth;
            editor.style.top = HeaderHeight + row * RowHeight;
            editor.style.width = columnWidth;
            editor.style.height = RowHeight;
            editor.style.display = DisplayStyle.Flex;
            editor.SetValueWithoutNotify(replacement ?? model.Get(row, column));
            editor.Focus();
            editor.schedule.Execute(() =>
            {
                if (editing) editor.SelectRange(editor.value.Length, editor.value.Length);
            });
        }

        void CommitEdit(bool refocus)
        {
            if (!editing) return;
            editing = false;
            model.Set(row, column, editor.value);
            editor.style.display = DisplayStyle.None;
            if (refocus) Focus();
        }

        void CancelEdit()
        {
            if (!editing) return;
            editing = false;
            editor.style.display = DisplayStyle.None;
            Focus();
        }

        // ---- keyboard --------------------------------------------------------------------------------------

        void OnEditorKeyDown(KeyDownEvent e)
        {
            switch (e.keyCode)
            {
                case KeyCode.Return:
                case KeyCode.KeypadEnter:
                    CommitEdit(true);
                    EnterMove(e.shiftKey ? -1 : 1);
                    break;
                case KeyCode.Tab:
                    CommitEdit(true);
                    TabMove(e.shiftKey ? -1 : 1);
                    break;
                case KeyCode.DownArrow:
                    CommitEdit(true);
                    Move(1, 0);
                    break;
                case KeyCode.UpArrow:
                    CommitEdit(true);
                    Move(-1, 0);
                    break;
                case KeyCode.Escape:
                    CancelEdit();
                    break;
                default:
                    return;
            }
            Swallow(e);
        }

        void OnKeyDown(KeyDownEvent e)
        {
            if (editing) return;

            switch (e.keyCode)
            {
                case KeyCode.UpArrow: Move(-1, 0); break;
                case KeyCode.DownArrow: Move(1, 0); break;
                case KeyCode.LeftArrow: Move(0, -1); break;
                case KeyCode.RightArrow: Move(0, 1); break;
                case KeyCode.Tab: TabMove(e.shiftKey ? -1 : 1); break;
                case KeyCode.Home: Select(row, 0); break;
                case KeyCode.End: Select(row, model.Columns - 1); break;
                case KeyCode.Return:
                case KeyCode.KeypadEnter:
                case KeyCode.F2:
                    BeginEdit(null);
                    break;
                case KeyCode.Delete:
                case KeyCode.Backspace:
                    model.Set(row, column, string.Empty);
                    break;
                default:
                    // Typed characters arrive as KeyDown events with no key code.
                    if (e.keyCode == KeyCode.None && e.character >= ' ' && !char.IsControl(e.character) && !e.ctrlKey && !e.commandKey)
                    {
                        BeginEdit(e.character.ToString());
                        break;
                    }
                    return;
            }
            Swallow(e);
        }

        static void Swallow(KeyDownEvent e)
        {
            e.StopPropagation();
            e.PreventDefault();
        }
    }
}
