"""Probe for dashboard-py--render_llm_status bug.

Bug claim: When state.llm_statuses has more than LLM_STATUS_WINDOW items,
the detail table only draws from the windowed statuses, thus it can show
fewer than 6 items even if the full list has 6 or more.

Test approach: monkey-patch LLM_STATUS_WINDOW to a small value (5), create
a mock state with >5 items, check if the detail table only shows 5 instead
of 6 items.
"""

import sys
import os
import unittest.mock

# Ensure the repo root is on sys.path so we can import dashboard
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from dashboard import render_llm_status, LLM_STATUS_WINDOW, _llm_status_style
except Exception as e:
    print(f'ERROR: failed to import dashboard module: {e}')
    sys.exit(1)


def run_probe():
    # Build mock items — each needs code, status, time, source, label keys.
    mock_items = []
    for i in range(20):
        mock_items.append({
            "code": "200" if i % 3 == 0 else "500",
            "status": "success" if i % 3 == 0 else "error",
            "time": f"12:00:{i:02d}",
            "source": f"src-{i}",
            "label": f"call-{i}",
        })

    class MockState:
        llm_statuses = mock_items

    state = MockState()

    # Monkey-patch LLM_STATUS_WINDOW to 5 to expose the windowing bug.
    with unittest.mock.patch("dashboard.LLM_STATUS_WINDOW", 5):
        result = render_llm_status(state)

    # result is a rich Panel. The renderable should be a Table.grid with 2 rows:
    # row 0 = metrics+sparkline Text, row 1 = detail Table.
    from rich.table import Table as RichTable
    from rich.panel import Panel

    if not isinstance(result, Panel):
        print(f"ERROR: expected rich.panel.Panel, got {type(result).__name__}")
        sys.exit(1)

    grid = result.renderable  # Should be Table.grid

    # grid is a Table.grid with 2 rows
    # grid.columns[0]._cells has the cells; each cell is a row
    if not hasattr(grid, 'columns') or not grid.columns:
        print("ERROR: grid has no columns")
        sys.exit(1)

    # The detail table is in row 1 (index 1) of the grid
    cells = list(grid.columns[0].cells)
    if len(cells) < 2:
        print(f"ERROR: expected at least 2 rows in grid, got {len(cells)}")
        sys.exit(1)

    detail_table = cells[1]  # Should be a Table

    if not isinstance(detail_table, RichTable):
        print(f"ERROR: expected detail_table to be rich.table.Table, got {type(detail_table).__name__}")
        sys.exit(1)

    actual_row_count = len(detail_table.rows)

    # Spec says the table should show "the trailing up to 6 items"
    # With 20 items and LLM_STATUS_WINDOW=5 (patched), the code does:
    #   statuses = list(state.llm_statuses)[-5:]   → items 15-19 (5 items)
    #   for item in reversed(statuses[-6:])        → items 15-19 reversed (5 items max)
    # Expected (spec-correct): the last 6 items from the full 20 → items 14-19
    spec_expected = min(6, len(mock_items))  # 6

    # Bug condition: the table shows fewer rows than spec_expected because
    # the detail table's [-6:] is applied AFTER the [-LLM_STATUS_WINDOW:]
    # windowing, so when LLM_STATUS_WINDOW < 6, we lose items.
    is_bug = (actual_row_count < spec_expected) and (len(mock_items) >= spec_expected)

    if is_bug:
        # Verify that the items in the table match the windowed tail, not the full tail
        windowed_tail = mock_items[-5:]  # LLM_STATUS_WINDOW=5
        # expected rows if windowed: reversed of [-6:] from windowed = reversed of entire window
        windowed_expected_count = min(6, len(windowed_tail))  # 5
        print(
            f"CONFIRMED — detail table shows {actual_row_count} rows, "
            f"spec requires up to {spec_expected} rows from the full list ({len(mock_items)} items). "
            f"Window (LLM_STATUS_WINDOW=5) limited to {len(windowed_tail)} items, "
            f"detail table draws from windowed tail {windowed_expected_count} rows, "
            f"full list tail would provide {spec_expected} rows."
        )
    else:
        print(
            f"NOT CONFIRMED — detail table shows {actual_row_count} rows, "
            f"spec requires up to {spec_expected} rows. "
            f"Window (LLM_STATUS_WINDOW=5), full list has {len(mock_items)} items."
        )


if __name__ == "__main__":
    run_probe()
