# Bug Report: render_llm_status

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/dashboard-py/render_llm_status.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a Rich Panel renderable titled "LLM Calls" with a cyan border
    style
  - When state.llm_statuses yields no items: the panel body contains a
    vertically centered, dimmed "(no LLM calls yet)" message
  - When state.llm_statuses yields one or more items:
    - The panel body opens with a summary line reporting the count of
      status entries considered (capped at LLM_STATUS_WINDOW) and the
      percentage of entries whose code maps to a 200-class label,
      color-coded green when the percentage is 95% or above, yellow when
      it is 80% or above but below 95%, and red when it is below 80%
    - Below the summary, a single-line strip of colored block characters
      represents the most recent status entries, with each character's
      color determined by the entry's code and status via
      _llm_status_style
    - Below the strip, a table lists at most the 6 most recent entries
      in reverse chronological order with columns: time, source, the
      colored HTTP status code label, and a display label
  - The returned renderable performs no I/O and is suitable for
    composition into a terminal layout

---

### Actual Behavior

The function returns a Rich Panel object `result` with `result.title == 'LLM Calls'` and `result.border_style == 'cyan'`. Let `statuses = list(state.llm_statuses)[-LLM_STATUS_WINDOW:]`. If `len(statuses) == 0`, then `result.renderable` is an `Align.center` containing a `Text` with markup `'[dim](no LLM calls yet)[/]'` and `vertical='middle'`. Otherwise, `result.renderable` is a `Table.grid` with `expand=True`, containing two rows. The first row is a `Text` object consisting of: (a) a strip of symbols for the last `min(len(statuses), 50)` items, where for each item the symbol is `''` if `_llm_status_style(item['code'], item['status'])[1] == '200'`, else `''` if the returned color is `'yellow'`, else `''`, each appended with the corresponding style color; and (b) a markup text line showing `'recent total/LLM_STATUS_WINDOW calls  '` followed by the success rate percentage (computed as `ok / total * 100` where `total = len(statuses)` and `ok = count of items where _llm_status_style(item['code'], item['status'])[1] == '200'`) formatted to one decimal place and colored `'green'` if rate  95, `'yellow'` if rate  80, else `'red'`, then `'% 200'`. The second row is a `Table` with columns `'time'`, `'src'`, `'code'`, `'call'`, showing the last `min(len(statuses), 6)` items in reverse order; each row contains respectively `item.get('time')` or empty string, `item.get('source')` or `'?'`, a markup string `f'[{color}]{label}[/]'` using the output of `_llm_status_style`, and `item.get('label')` or empty string. The function has no side effects on `state` or external state.

---

## Code Evidence

Line 10: for item in statuses[-50:]:

---

## Trigger Condition

The specification requires that the single-line strip of colored block characters represents the most recent status entries, meaning all entries considered (capped at LLM_STATUS_WINDOW). The code arbitrarily limits the strip to the last 50 entries, so if LLM_STATUS_WINDOW exceeds 50, not all recent entries are represented.

---

## How to trigger the bug

The function `render_llm_status` in `dashboard.py` limits the status strip to the last 50 entries via `statuses[-50:]` on line 647, even though `LLM_STATUS_WINDOW = 80` on line 45 permits up to 80 entries. When more than 50 status entries exist, the strip shows only 50 symbols instead of representing all entries in the window.

### Inputs

| Parameter | Value |
|-----------|-------|
| `state.llm_statuses` | List of 70 dicts, each with `{"code": 200, "status": "success", "time": "12:00", "source": "src", "label": "call_<i>"}` |

### Expected (spec-correct) Output

70 block characters (`■`) in the strip — one for each entry in the window.

### Actual (buggy) Output

50 block characters (`■`) in the strip — the code slices to `statuses[-50:]` regardless of window size.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import dashboard

class MockState:
    pass

state = MockState()
state.llm_statuses = [
    {"code": 200, "status": "success", "time": "12:00", "source": "src", "label": f"call_{i}"}
    for i in range(70)  # more than 50, fewer than LLM_STATUS_WINDOW (80)
]

result = dashboard.render_llm_status(state)

# The returned Panel's strip contains only 50 ■ symbols instead of 70
# actual (buggy) output: 50 strip symbols
# expected (correct) output: 70 strip symbols
```

---

## Probe Script

```python
import sys
import os
import io

# Ensure the repo root is on sys.path so `import dashboard` resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import dashboard
    from rich.console import Console

    # Create 70 mock status entries (more than 50, fewer than LLM_STATUS_WINDOW=80)
    class MockState:
        pass

    state = MockState()
    state.llm_statuses = [
        {"code": 200, "status": "success", "time": "12:00", "source": "src", "label": f"call_{i}"}
        for i in range(70)
    ]

    result = dashboard.render_llm_status(state)

    # Render the Panel to plain text so we can count strip symbols
    f = io.StringIO()
    console = Console(file=f, no_color=True, force_terminal=False)
    console.print(result)
    output = f.getvalue()

    # Each 200-code entry produces a "■" symbol in the strip
    symbol_count = output.count("\u25a0")
    expected = 70  # spec: strip should show ALL entries in window (capped at LLM_STATUS_WINDOW=80)

    passed = symbol_count != expected
    if passed:
        print(f"CONFIRMED \u2014 strip shows {symbol_count} symbols for {len(state.llm_statuses)} entries, expected {expected}")
    else:
        print(f"NOT CONFIRMED \u2014 strip shows {symbol_count} symbols, matched expected {expected}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — strip shows 50 symbols for 70 entries, expected 70
```
