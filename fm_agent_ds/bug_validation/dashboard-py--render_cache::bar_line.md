# Bug Report: render_cache::bar_line

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/dashboard-py/render_cache::bar_line.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When total_count summed across all tuples in rows equals zero, returns a dimmed Rich-markup string beginning with the right-aligned label (14 chars, left-padded with spaces) followed by the text '(no data)'.

---

### Actual Behavior

After a successful call to `bar_line`, no side effects occur and the function returns a string `result`. The return value satisfies one of two mutually exclusive conditions:

1. **No data case:** If the sum of all `total_count` values in `rows` is zero, then `result` equals the exact string `"[dim]{label:<14}(no data)[/]"`, where `{label:<14}` means the input `label` **left-aligned** in a field of width 14.

---

## Code Evidence

Line 4: `return f"[dim]{label:<14}(no data)[/]"`

The `:<` format specifier left-aligns the label, right-padding it with spaces. The specification requires right-alignment (`:>`), which would left-pad the label with spaces.

---

## Trigger Condition

The specification requires the label to be right-aligned (left-padded with spaces) in the no-data case, but the code left-aligns it (right-padded with spaces). For label='foo' and zero totals, the code outputs `"[dim]foo           (no data)[/]"` instead of the required `"[dim]           foo(no data)[/]"`.

---

## How to trigger the bug

The bug manifests when `bar_line` is called with rows whose `total_count` values sum to zero. In the dashboard, this occurs when `cache_window` contains entries with zero totals, causing `bar_line` to render the "no data" message for the "latest 10" and "latest 100" summaries.

### Inputs

| Parameter | Value |
|-----------|-------|
| `label` | `"latest 10"` |
| `rows` | `[(0, 0)]` (one tuple with cache_read=0, total=0) |

### Expected (spec-correct) Output

`"[dim]    latest 10(no data)[/]"` — label right-aligned in 14-char field (left-padded with 4 spaces)

### Actual (buggy) Output

`"[dim]latest 10     (no data)[/]"` — label left-aligned in 14-char field (right-padded with 4 spaces)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point `render_cache` from `dashboard.py`):

```python
from dashboard import render_cache

class MockState:
    pass

state = MockState()
state.totals = {"cache_read": 1}    # non-zero total_cr → enter normal path
state.opencode_token_totals = {}
state.cache_window = [(0, 0)]       # zero totals → bar_line no-data path
state.model_seen = None
state.cost_native = 0
state.opencode_cost = 0

panel = render_cache(state)
align = panel.renderable
text = align.renderable
content = text.plain

# actual (buggy) output: 'latest 10     (no data)'   — left-aligned
# expected (correct) output: '    latest 10(no data)' — right-aligned
assert "latest 10     (no data)" in content
```

---

## Probe Script

```python
"""Probe for dashboard-py--render_cache::bar_line
Bug: bar_line uses left-alignment (:<14) for label in no-data case,
     but spec requires right-alignment (:>14).
"""
import sys
import os

# Add repo root to sys.path so 'import dashboard' resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from dashboard import render_cache

    class MockState:
        pass

    state = MockState()
    state.totals = {"cache_read": 1}       # non-zero total_cr → enter normal path
    state.opencode_token_totals = {}
    state.cache_window = [(0, 0)]          # zero totals → bar_line no-data path
    state.model_seen = None                 # no price → no cost line appended
    state.cost_native = 0
    state.opencode_cost = 0

    # Call the public API that exercises bar_line
    panel = render_cache(state)

    # Extract plain text: Panel → Align → Text
    align = panel.renderable
    text = align.renderable
    content = text.plain

    # For label "latest 10" (length 10) in a 14-char field:
    #   Left-aligned  (buggy):    "latest 10     "  → 10 chars label + 4 spaces right-pad
    #   Right-aligned (spec):     "    latest 10"    → 4 spaces left-pad + 10 chars label
    #
    # The bar_line returns Rich markup: "[dim]latest 10     (no data)[/]"
    # After Text.from_markup, the content between tags is preserved literally.
    # So .plain should contain "latest 10     (no data)"

    # Find the dim-styled text for "latest 10"
    # We check the plain text for the bug pattern
    bug_pattern = "latest 10     (no data)"       # left-aligned (buggy)
    spec_pattern = "    latest 10(no data)"        # right-aligned (correct)

    if bug_pattern in content:
        print(f"CONFIRMED — bar_line left-aligns label in no-data case")
        print(f"actual:   {bug_pattern!r}")
        print(f"expected: {spec_pattern!r}")
        print(f"full content: {content!r}")
    elif spec_pattern in content:
        print(f"NOT CONFIRMED — bar_line right-aligns label, matching spec")
        print(f"output: {content!r}")
    else:
        print(f"NOT CONFIRMED — neither pattern found in output")
        print(f"output: {content!r}")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — bar_line left-aligns label in no-data case
actual:   'latest 10     (no data)'
expected: '    latest 10(no data)'
full content: 'latest 10     (no data)\nlatest 100    (no data)\noverall   100.0%  ████████████████████ 1 / 1\ncoverage = cache_read / (input + cache_write + cache_read)'
```
