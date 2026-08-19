# Bug Report: render_llm_status

**Source file:** `dashboard-py/render_llm_status.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a Rich Panel renderable with title 'LLM Calls' and cyan border-style. When state.llm_statuses is empty, the panel displays a vertically centered, dim-text message indicating that no LLM calls have occurred. When state.llm_statuses is non-empty, the panel displays three vertically stacked components: (a) a metrics line showing the number of recent status items (up to LLM_STATUS_WINDOW) and the percentage of those items whose resolved status label equals '200', formatted to one decimal place and colored green when 95%, yellow when 80%, and red when <80%; (b) a horizontal strip of colored symbols, one per status item from the trailing window of up to 50 items, where each symbol's color and shape are a deterministic function of that item's code and status values; (c) a table of the trailing up to 6 items in reverse chronological order, with columns for a timestamp, a source identifier, a color-coded status label, and a call description. The state argument is not mutated.

---

### Actual Behavior

The function returns a rich.panel.Panel with title="LLM Calls" and border_style="cyan". Let S = list(state.llm_statuses)[-LLM_STATUS_WINDOW:]. If S is empty, the Panel encloses a center-aligned Text displaying "(no LLM calls yet)" in dim style. If S is non-empty, the Panel encloses a Table.grid (expand=True) with two rows: the first row is a Text consisting of a markup line "recent {|S|}/{LLM_STATUS_WINDOW} calls" followed by a sparkline (a Text strip) of the last up to 50 items of S, each mapped via _llm_status_style(code, status) to a color and symbol; the second row is a Table with columns time, src, code, call, showing the last up to 6 items of S in reverse order. The function does not mutate any external state and requires that _llm_status_style is deterministic. No exceptions are raised if state.llm_statuses items contain the expected keys. Formally: post_condition(state, result)  isinstance(result, Panel)  result.title = "LLM Calls"  result.border_style = "cyan"  ( s  S, s has 'code' and 'status' keys)  ( (|S|=0  result.renderable = Align.center(Text.from_markup("[dim](no LLM calls yet)[/]"), vertical="middle"))  (|S|>0  result.renderable = Table.grid(expand=True) containing the sparkline Text and detail Table as described with exactly |S| and the specified derivations)).

---

## Code Evidence

Line 2: statuses = list(state.llm_statuses)[-LLM_STATUS_WINDOW:]
Line 19: for item in list(reversed(statuses[-6:]))

---

## Trigger Condition

When state.llm_statuses has more than LLM_STATUS_WINDOW items, the detail table only draws from the windowed statuses, thus it can show fewer than 6 items even if the full list has 6 or more. The specification requires the table to display the trailing up to 6 items from the entire status list, not only the metrics window.

---

## How to trigger the bug

The bug is structural: the detail table's items slice (`statuses[-6:]`) is applied to the **already-windowed** list (`[-LLM_STATUS_WINDOW:]`), coupling the table's row count to the metrics window size. When `LLM_STATUS_WINDOW < 6` and the full input list has ≥6 items, items are lost.

Normally `LLM_STATUS_WINDOW = 80` and the state's deque has `maxlen=80`, so the bug is latent. But the coupling is present in the code: the `[-6:]` slice operates on the windowed result, not on the original `state.llm_statuses`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `LLM_STATUS_WINDOW` (patched) | 5 |
| `state.llm_statuses` | list of 20 dicts, each with keys: code, status, time, source, label |
| Items | Indices 0–19, with code "200"/"500", status "success"/"error" |

### Expected (spec-correct) Output

The detail table should contain **6 rows** (the trailing up-to-6 items from the full 20-item list), in reverse chronological order (indices 19, 18, 17, 16, 15, 14).

### Actual (buggy) Output

The detail table contains only **5 rows** (indices 19, 18, 17, 16, 15), because the `[-LLM_STATUS_WINDOW:]` window first trimmed the list to only 5 items, then `[-6:]` retrieved all 5 (fewer than 6).

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import unittest.mock
from dashboard import render_llm_status

mock_items = [{"code": "200", "status": "success", "time": f"12:00:{i:02d}",
               "source": f"src-{i}", "label": f"call-{i}"} for i in range(20)]

class MockState:
    llm_statuses = mock_items

with unittest.mock.patch("dashboard.LLM_STATUS_WINDOW", 5):
    result = render_llm_status(MockState())

# result.renderable is a Table.grid with 2 rows
# row 1 (the detail table) has only 5 rows instead of 6
grid = result.renderable
detail_table = list(grid.columns[0].cells)[1]
assert len(detail_table.rows) == 5  # bug: should be 6
// actual (buggy) output: detail table has 5 rows
// expected (correct) output: detail table should have 6 rows
```

---

## Probe Script

```python
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
    #   statuses = list(state.llm_statuses)[-5:]   -> items 15-19 (5 items)
    #   for item in reversed(statuses[-6:])        -> items 15-19 reversed (5 items max)
    # Expected (spec-correct): the last 6 items from the full 20 -> items 14-19
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
```

### Probe Output

```
CONFIRMED — detail table shows 5 rows, spec requires up to 6 rows from the full list (20 items). Window (LLM_STATUS_WINDOW=5) limited to 5 items, detail table draws from windowed tail 5 rows, full list tail would provide 6 rows.
```
